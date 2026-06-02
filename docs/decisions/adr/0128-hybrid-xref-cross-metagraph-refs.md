---
title: Hybrid cross-graph refs — XRef primitive + ref-string convention
status: Proposed
date: 2026-04-27
layer: L1
amends: [0016, 0034]
---

# ADR-0128: Hybrid cross-graph refs — `XRef` primitive + `ref:<role>` strings

**Status:** Proposed

**Date:** 2026-04-27

**Amends:** ADR-0016 (`ref:<role>` property prefix — retained for intra-metagraph), ADR-0034 (Core never validates refs — narrowed; XRefs are validated, ref-strings remain unvalidated).

**Related:** ADR-0118 (per-user transactional promotion — auto-upgrade contract), `docs/concepts/references.md` (ref auto-upgrade documentation), ADR-0122 (WAL — XRef writes use WAL).

## Context

Today, all cross-graph references are properties on nodes whose key starts with `ref:` (per ADR-0016). Core doesn't validate targets (per ADR-0034). Every higher layer reimplements integrity:

- KL has `_check_global_target_exists` for one direction (Local → Global) and one role pair.
- Pivot's auto-upgrade contract (per `docs/concepts/references.md` + ADR-0118) says cross-graph refs auto-upgrade by node id when a Global node bumps version. The current implementation walks property scans to find refs to rewrite — every node's properties checked for keys starting with `ref:`.
- Pivot's lazy migration (`mindsos_server/migration.py`) walks property scans on every user's Local at session-start.

**Problem:** Property-string scans are O(N nodes × M properties). With the auto-upgrade contract, every release-migration walks every Local's nodes. At scale this is the dominant cost.

The L1 redesign session evaluated: status quo, diagnostic helper only, first-class XRef everywhere, and hybrid (XRef for cross-metagraph, strings for intra). Hybrid won.

## Decision

Two ref mechanisms by scope:

### 1. Intra-metagraph: `ref:<role>` strings (status quo, ADR-0016 retained)

Properties on nodes within the same metagraph keyed `ref:<role>`. Core iterates them via `iter_ref_properties(props)`. Core does not validate. KL invariants (per ADR-0048) cover the validation it needs. No change.

**Why retained:** intra-metagraph refs don't auto-upgrade. The KL versioning model (active-pointer + side-by-side graphs) handles intra-metagraph version changes already. The string convention is cheap, well-understood, and adequate.

### 2. Cross-metagraph: first-class `XRef` primitive (new)

A new Core primitive for cross-metagraph references (Local → Global, Local → Other-Local, etc.):

```python
@dataclass(frozen=True)
class XRef:
    xref_id: str                      # UUID
    source_metagraph_id: str
    source_id: str                    # node/edge/hyperedge id in source metagraph
    target_metagraph_id: str
    target_role: str                  # role of the target graph
    target_id: str                    # node/edge/hyperedge id in target metagraph
    ref_type: str                     # SPECIALISES, INSTANCE_OF, etc. (KL's REF_TYPES vocab)
    properties: dict[str, Any] = field(default_factory=dict)
```

**Storage:**

- XRef rows persist in **the source metagraph** as `:XRef` nodes anchored to the source element via a `:HAS_XREF` edge.
- Indexes (per ADR-0123): on `(source_id)` for forward walks (give me all XRefs originating from this node), on `(target_metagraph_id, target_id)` for reverse walks (give me all XRefs pointing at this target).

**Public API (Core):**

```python
# On Metagraph:
mg.add_xref(
    source: Node | Edge | HyperEdge,
    target_metagraph_id: str,
    target_role: str,
    target_id: str,
    ref_type: str,
    properties: dict | None = None,
) -> XRef

mg.iter_xrefs(
    *,
    source_id: str | None = None,           # forward
    target_metagraph_id: str | None = None,  # reverse
    target_id: str | None = None,            # reverse
    ref_type: str | None = None,
) -> Iterator[XRef]

mg.remove_xref(xref_id: str) -> None
```

**Validation (departs from ADR-0034 for XRefs only):**

`add_xref` validates that the target exists at write time IF a `target_metagraph` is in scope (e.g., the server has the target's Local installed). Core's contract:

- If `target_metagraph` is **resolvable** (passed explicitly or available via a registry hook), validate. Raise `XRefIntegrityError` if target missing.
- If `target_metagraph` is **not resolvable**, accept the write. The XRef is "soft" — it stamps an id without confirming existence. Pivot's migration handler is the consumer that exercises soft XRefs.

This is a deliberate split from ADR-0034. Property-based refs (intra-metagraph) stay unvalidated; XRefs (cross-metagraph) opt into write-time validation when target is in scope. The two mechanisms have different cost profiles — XRef validation is O(1) lookup via index; property-scan validation would be O(N).

### Migration

One-time migration job at server start:

```python
# Pseudocode:
for mg in installed_metagraphs:
    for graph in mg.graphs:
        for node in graph.iter_nodes():
            for key, value in node.properties.items():
                if key.startswith("ref:global_"):
                    role = key[len("ref:global_"):]
                    # Migrate to XRef:
                    mg.add_xref(
                        source=node,
                        target_metagraph_id=GLOBAL_METAGRAPH_ID,
                        target_role=role,
                        target_id=value,
                        ref_type=node.properties.get("ref_type", "SPECIALISES"),
                    )
                    # Remove the property:
                    del node.properties[key]
                    if "ref_type" in node.properties:
                        del node.properties["ref_type"]
```

Idempotent (running twice is a no-op once existing XRefs match). Runs once per metagraph; tracked via a property `mg.properties["xref:migrated_from_strings_at"]` (per ADR-0130's property bag).

`ref:<role>` (intra-metagraph) is **NOT** migrated. Stays as property strings.

### Auto-upgrade integration

Pivot's auto-upgrade walks XRefs at release-migration time:

```python
# Pseudocode for pivot's migrate_user_to_latest_release:
for rewrite_old_id, rewrite_new_id in release.rewrite_map.items():
    for xref in mg.iter_xrefs(target_id=rewrite_old_id, target_metagraph_id=GLOBAL):
        # Update XRef target:
        mg.remove_xref(xref.xref_id)
        mg.add_xref(
            source=xref.source(),
            target_metagraph_id=GLOBAL,
            target_role=xref.target_role,
            target_id=rewrite_new_id,
            ref_type=xref.ref_type,
            properties=xref.properties,
        )
```

This is an indexed-lookup pattern (O(K log N) where K = rewrite map size) instead of property scan (O(N total nodes)). The migration handler in `mindsos_server/migration.py` switches from property scans to `iter_xrefs` calls when this ADR ships.

## Rationale

The split is justified by usage profile:

- **Intra-metagraph refs** are read-frequently, write-rarely, and never auto-upgrade. Property strings work fine; making them first-class buys nothing.
- **Cross-metagraph refs** are the auto-upgrade integration point. Indexed lookup is dramatically cheaper than property scan; the cost difference grows linearly with user count and node count.

XRef-everywhere was considered. Rejected because intra-metagraph refs don't need the indexed lookup — KL's role-graph traversal handles them via Cypher edges within the graph, which is already efficient.

The departure from ADR-0034 for XRefs (write-time validation when target resolvable) is the correctness payoff: KL's `_check_global_target_exists` becomes a Core operation, and dangling cross-metagraph refs become impossible at write.

## Consequences

**Good:**

- Pivot's auto-upgrade migration becomes O(K log N) instead of O(N).
- KL drops `_check_global_target_exists` (Core enforces).
- KL invariants I1 and I7 (per ADR-0048) become Core-enforced for cross-metagraph specifically.
- L4 ref-walking (currently a property-scan) becomes indexed.
- L5 instances that hold cross-metagraph refs gain the same indexed-lookup performance.

**Tradeoffs:**

- New Core primitive (XRef) plus persistence (`:XRef` nodes, `:HAS_XREF` edges) plus loader updates. ~250 LOC + tests.
- Two ref mechanisms means two mental models. Documentation must be clear about when to use which.
- Migration of existing `ref:global_*` properties to XRef rows. One-time job; idempotent; bounded.
- XRef writes use WAL (per ADR-0122) for safety. Adds one round-trip vs property write.

**Coordinated changes:**

- `mindsos_core/models/xref.py` (new) — XRef dataclass.
- `mindsos_core/models/metagraph.py` — `add_xref`, `iter_xrefs`, `remove_xref`.
- `mindsos_core/persistence/xref_repository.py` (new).
- `mindsos_core/reconstruction/xref_loader.py` (new).
- `mindsos_core/exceptions.py` — `XRefIntegrityError`.
- KL: `add_local_node(ref_to_global=...)` calls `mg.add_xref(...)` instead of writing properties. Existing KL invariant tests pass through.
- `mindsos_server/migration.py` — switches from property scans to `iter_xrefs`.
- One-time migration job in `mindsos_core/persistence/xref_migration.py`.
- `docs/concepts/references.md` — restructure to explain the hybrid model.
- `docs/api/core/xref.md` (new).

## Alternatives considered

1. **Status quo (`ref:<role>` strings everywhere).** Rejected — auto-upgrade migration is O(N); pivot's release model amplifies the cost; KL's per-write `_check_global_target_exists` doesn't generalize.
2. **First-class `XRef` everywhere (intra and cross).** Rejected — intra-metagraph refs don't auto-upgrade and are already efficiently traversed via Cypher; XRef-everywhere doubles persistence surface for no measured benefit.
3. **Diagnostic helper only (`Metagraph.verify_refs()`).** Rejected — addresses ADR-0034's deferred work but doesn't help auto-upgrade migration cost. Useful as a separate scan helper but not a substitute for first-class XRef.
4. **`XRef` as edge in target metagraph instead of source.** Rejected — auto-upgrade walks "find all refs into this target," which is the reverse direction; storing in source matches the typical write pattern (KL's `add_local_node(ref_to_global=...)` writes from the source side).
5. **Full-OWL-style RDF triples for refs.** Rejected — overkill; no use case demands the expressiveness; persistence cost is high.

## Implementation references

- New: `mindsos_core/models/xref.py`, `persistence/xref_repository.py`, `reconstruction/xref_loader.py`, `persistence/xref_migration.py`.
- Modified: `models/metagraph.py` (XRef methods), `exceptions.py` (XRefIntegrityError).
- KL: `mindsos_knowledge/knowledge_layer.py` (add_local_node uses XRef), `mindsos_knowledge/views.py` (follow_ref uses XRef).
- Pivot: `mindsos_server/migration.py` (uses iter_xrefs).
- Docs: `docs/concepts/references.md`, `docs/api/core/xref.md`.
- Tests: `tests/unit/core/test_xref.py`, `tests/integration/test_xref_migration.py`.

ADR moves from Proposed to Accepted when XRef lands in Core, KL adopts it for cross-metagraph refs, and `docs/concepts/references.md` documents the hybrid model.

**Phase 09 disposition (2026-05-15):** Phase 09 ships the L1 surface — `XRef` dataclass, `Metagraph.add_xref` / `iter_xrefs` / `remove_xref`, `XRefRepository` (WAL-wrapped), `XRefLoader` (clear-first), `attach_xref_loader` after-load observer, programmatic `migrate_in_memory` callable, `xref-list` read-only CLI verb, state-file v=4 (`xrefs[]` array), 4 new `:XRef` indexes, per-Client WAL replayers (`xref_add` + `xref_remove`). The hybrid model is documented at `docs/concepts/references.md`. **Status stays Proposed** until Phase 14 — the L2 consumer (`MetagraphView.follow_ref` walking XRefs + legacy `ref:global_*` fallback per ADR-0142 commitment 2) lands in P14 and validates the contract; flip to Accepted then. Holding-pattern matches the M1 reasoning for ADR-0142.

## Revisions

1. **2026-05-15 (Phase 09 RR-4).** XRef equality assertions are `id-set + per-id 8-field check`. Per Phase 09 P53, `target_stale` + `deprecated_at` deferred until setters ship; equality lives at 8 fields.

2. **2026-05-15 (Phase 09 RR-3 + RR-12).** Property-bag flag prefix `xref:` reserved for L1-internal migration state (e.g. `xref:migrated_at`). Phase 09 `xref-list` CLI verb gives an indexed read path without loading the metagraph.

3. **2026-05-16 (Phase 10 PX2 + M14 + O1).** XRef restores `target_stale: bool` + `deprecated_at: datetime | None` (P53 reversal); XRef quartet API ships (`mark_xref_stale` / `unmark_xref_stale` / `deprecate_xref` / `undeprecate_xref`). Reverse-dangling cleanup means **setter exists for upper layers to call**; the firing trigger (Server first-start hook on archived-target detection) is deferred to Phase 18+. State-file v=5 + `xref-list --json` carry the 10-field shape (M24 + RR-19). Status remains Proposed until Phase 14 acceptance.

## Revisions

Five amendments dated 2026-05-15 (Phase 09 row lock + design log RR-9 + P58 amendment-3 rewrite):

1. **`add_xref(source_id: str, ...)`** — source is a stable id, not a `Node`/`Edge`/`HyperEdge` object. The Phase 09 implementation takes `source_id` as a kw-only `str`; persistence + reconstruction round-trip the id only.
2. **Anchor edge name is `:XREF_OF`** (links the `:XRef` row to its source `:Metagraph` anchor, NOT to the source element). The original prose `:HAS_XREF` (element-anchored) was a draft; the v3 baseline + repository docstring + Phase 09 ship `:XREF_OF`. Lifecycle role (forward-cascade on Metagraph removal); reverse lookup goes through the property index alone.
3. **Phase 09 dataclass deviates from v3 by dropping `target_stale` + `deprecated_at`.** Both fields + their setters ship together in Phase 10 alongside the soft-delete substrate (ADR-0133); shipping inert fields without setters in Phase 09 was rejected as a state-file injection trap.
4. **Migration flag key is `mg.properties["xref:migrated_at"]`.** Renames v3's `server:xref_migrated_at` (wrong namespace — `server:` implies Server-set but the L1 migration code itself sets it) and ADR-0128 prose's draft `xref:migrated_from_strings_at` (verbose). The `xref:` namespace is added to ADR-0130's namespacing convention by Phase 09.
5. **Validation is opt-in via `add_xref(target_metagraph: Metagraph | None = None, ...)` kwarg.** When `target_metagraph` is supplied, the target id must exist under the named role; otherwise `XRefIntegrityError(PersistenceError)`. When absent, the XRef is "soft" — Core accepts the write. Validation runs BEFORE the WAL entry opens (P59) so rejected writes never resurrect on `recover()`. Server-side registry-hook resolver path deferred to Phase 18+.
