---
title: RemovalImpact report on remove_graph
status: Accepted
date: 2026-04-27
layer: L1
amends: [0034]
---

# ADR-0135: `RemovalImpact` report on `remove_graph`

**Status:** Accepted (Phase 10 — 2026-05-16; signature + behaviour per §Revisions amendments 1-3 below)

**Date:** 2026-04-27

**Amends:** ADR-0034 (Core never validates refs — narrowed; cross-graph XRefs become detectable on graph removal).

**Related:** ADR-0128 (XRef primitive — supplies the iteration surface), ADR-0118 (release migration handler — consumer of the report).

## Context

`Metagraph.remove_graph(graph_id)` deletes a graph from a metagraph. Today it doesn't tell the caller anything about cross-graph references that pointed into the removed graph. `ref:*` properties on nodes in *other* graphs become dangling silently.

With ADR-0128's XRef primitive, cross-metagraph references are first-class. Removing a graph that's the target of XRefs needs a defined behaviour — at minimum, surfacing what would break.

The pivot's release-archival flow (deferred to v2 per PIVOT §2 row 6c, "atom delete") will eventually need this; v1 doesn't archive nodes but does need to surface dangling-XRef detection for the audit gate.

## Decision

`Metagraph.remove_graph` returns a `RemovalImpact` report and accepts a `force` flag.

```python
@dataclass
class RemovalImpact:
    incoming_xrefs: list[XRef]            # XRefs pointing into the removed graph
    incoming_ref_properties: list[tuple[str, str]]  # (source_node_id, property_key) for ref:* strings pointing into removed graph
    proceeded: bool                        # True if removal actually completed
    blocked_reason: str | None             # set when proceeded=False


@dataclass
class Metagraph:
    def remove_graph(
        self,
        graph_id: str,
        *,
        force: bool = False,
        cascade: bool = False,
    ) -> RemovalImpact: ...
```

**Behaviour:**

1. Build the impact report **before** any removal:
   - `incoming_xrefs`: all XRefs in the metagraph (and across registered cross-metagraph sources, if resolvable) whose `target_id` is a node id inside the graph being removed. Indexed lookup via ADR-0128's `(target_metagraph_id, target_id)` index — cheap.
   - `incoming_ref_properties`: scan property strings in *other* graphs in this metagraph for `ref:<role>` keys whose value is a node id inside the graph being removed. O(N) over other graphs; documented as more expensive than XRef lookup. (This is exactly the cost difference that motivated XRef per ADR-0128.)
2. **If `incoming_xrefs` or `incoming_ref_properties` is non-empty AND `force=False`:**
   - Return `RemovalImpact(proceeded=False, blocked_reason="dangling-refs", ...)`. Removal does NOT happen.
3. **If `incoming_xrefs` is non-empty AND `force=True`:**
   - Stamp `target_stale=True` on each affected XRef.
   - Proceed with removal.
   - Return `RemovalImpact(proceeded=True, ...)` listing the affected XRefs.
4. **If `incoming_ref_properties` is non-empty AND `force=True`:**
   - Property strings are NOT stamped (no equivalent of `target_stale` for property keys; would require modifying every node).
   - The caller is responsible for cleanup. The report enumerates them.
   - Proceed with removal.
   - Return `RemovalImpact(proceeded=True, ...)` listing the affected properties.
5. **If both `force=True` AND `cascade=True`:**
   - Same as `force=True` plus: existing tombstone behaviour (ADR-0024) records the removed graph's nodes and edges; the metagraph's other graphs aren't recursively affected.

**Default = report-only.** Callers who don't pass `force` get a useful report and the removal doesn't happen. KL/pivot decide policy: redirect via auto-upgrade migration, mark stale, hard-block.

### Caller-side policy

The pivot's release migration handler (per ADR-0118 §3 + `mindsos_server/migration.py`) doesn't typically remove graphs — releases archive via deprecation, not removal. When archival eventually lands (pivot v2):

```python
# Release archival pseudocode (v2):
impact = mg.remove_graph(old_role_graph_id, force=False)
if impact.incoming_xrefs:
    # Trigger auto-upgrade to redirect to canonical
    for xref in impact.incoming_xrefs:
        rewrite_xref_target(xref, new_target_id=...)
    # Now safe to force-remove:
    mg.remove_graph(old_role_graph_id, force=True)
elif impact.incoming_ref_properties:
    # Caller-side property cleanup; v2 KL handler responsibility.
    ...
```

In v1, `remove_graph` is rarely called on graphs with non-empty incoming refs. The mechanism exists for: KL test cleanup, admin-initiated archival in `mindsos-server fsck --repair` (v2), and pivot v2 archival.

## Rationale

ADR-0034 said Core never validates refs. This ADR narrows that contract: Core doesn't validate refs *at write time* (still true) but does *report* them at structural-change time (graph removal). The report-only default keeps existing behaviour minimal-impact while giving callers actionable information.

XRef makes this cheap (indexed lookup); property-string scanning is the expensive case but is also opt-in by usage — KL's main ref pattern (Local→Global) uses XRef post-redesign, so the property-string scan applies only to legacy intra-metagraph refs.

The `force` flag forces an explicit decision. Removing a graph with incoming refs without `force=True` is nearly always a bug; making it opt-in means the bug can't happen by accident.

## Consequences

**Good:**

- Audit gate (per ADR-0115) can call `remove_graph(force=False)` as a dry-run to surface impact in `ImpactReport`.
- `mindsos-server fsck` (per ADR-0123) gains a structured pre-remove check.
- KL gains a clean "what breaks if I remove this version-graph?" tool.
- v2's pivot archival has a Core primitive to build on.

**Tradeoffs:**

- `incoming_ref_properties` scan is O(N) over other graphs in the metagraph. Cost is unavoidable until property-string refs are migrated to XRefs (ADR-0128's migration handles the bulk).
- Two failure modes (XRefs vs property strings) means callers branch on both. Documented.
- Default `force=False` means existing tests that called `remove_graph` and didn't pass force will continue working only if the graph has no incoming refs. Tests that constructed dangling-ref scenarios pre-redesign need updates.
- `target_stale=True` flag on XRefs is a new convention; readers (KL views) should respect it (filter out or surface).

**Coordinated changes:**

- `mindsos_core/models/metagraph.py` — `remove_graph` signature + impact computation.
- `mindsos_core/models/xref.py` — `target_stale` field on XRef.
- `mindsos_core/exceptions.py` — `RemoveGraphBlockedError` (raised when `force=False` and impact non-empty AND caller chose strict mode).
- KL: tests that exercise graph removal updated.
- Pivot ADR-0115: audit gate uses `remove_graph(force=False)` dry-run.
- ADR-0024 (tombstone) — unchanged; `remove_graph` still tombstones the removed graph's contents per existing pattern.
- Tests: `tests/unit/core/test_remove_graph_impact.py`.
- Documentation: `docs/api/core/metagraph.md` (remove_graph section), `docs/dev/internals/core.md` (impact report pattern).

## Alternatives considered

1. **Status quo (silent removal; dangling refs become operational hazard).** Rejected — silent data loss; pivot's audit gate has no input.
2. **Block removal whenever incoming refs exist.** Rejected — too rigid; admins occasionally need to force-remove.
3. **Stamp `ref_stale=True` on property keys.** Rejected — would require mutating every node carrying the ref; expensive; conflicts with ADR-0033's filter pattern (which filters on edge properties, not refs).
4. **Defer to KL** (Core unaware; KL implements remove-graph-with-impact). Rejected — XRef is a Core primitive (per ADR-0128); the impact computation belongs at the same layer that defines the primitive.
5. **Atomic redirect** (auto-rewrite XRefs to a new target on removal). Rejected for v1 — couples Core to redirection semantics that belong in higher layers (KL knows what to redirect to via release manifests; Core doesn't). Caller does the redirect; Core supplies the report.

## Implementation references

- `mindsos_core/models/metagraph.py` — `remove_graph` signature.
- `mindsos_core/models/xref.py` — `target_stale` field.
- `mindsos_core/exceptions.py` — `RemoveGraphBlockedError`.
- Tests: `tests/unit/core/test_remove_graph_impact.py`.
- Documentation: `docs/api/core/metagraph.md`, `docs/dev/internals/core.md`.

ADR moves from Proposed to Accepted when `remove_graph` returns `RemovalImpact`, KL exercises the impact report in at least one test, and `docs/api/core/metagraph.md` documents the report shape.

## Revisions

1. **2026-05-16 (Phase 10 — P67 cascade default restored).** Signature is `remove_graph(graph_id, *, cascade=True, force=False) -> RemovalImpact`. The `cascade` default flips from this ADR's original `False` to `True` matching the v3 baseline (auto-cascade incident MetaEdges/MetaHyperEdges). Rationale: v3 verbatim contract preserves the existing call-shape; opt-out (`cascade=False`) raises `RemoveGraphBlockedError(INCIDENT_META_EDGES_CASCADE_FALSE)` when incident meta-edges exist.

2. **2026-05-16 (Phase 10 — PA1 raise-on-block).** When `force=False` AND impact non-empty, `remove_graph` **raises** `RemoveGraphBlockedError` (carrying `.impact`) rather than returning `RemovalImpact(proceeded=False, ...)` per the original Decision step 2. Rationale: raise is API-friendlier — callers cannot silently miss `proceeded=False`. The `proceeded` field on `RemovalImpact` is retained for the success-path return.

3. **2026-05-16 (Phase 10 — P75 unified exception + P81 cascade-vs-force independence).** Two block paths collapse to a single exception class with a `BlockedReason` enum: `DANGLING_REFS` (force gate) and `INCIDENT_META_EDGES_CASCADE_FALSE` (cascade gate). Per P81, the cascade gate raises **regardless of `force`** — `force=True` overrides only the dangling-refs gate, not the cascade gate (v3 verbatim). The in-memory `_xrefs_by_target` compound index drives impact computation per PB-5a; cross-metagraph reverse-dangling cleanup is the upper-layer setter `mark_xref_stale` (ADR-0128 §Revisions amendment-3) with the firing trigger deferred to Server first-start (Phase 18+).
