---
title: Optimistic concurrency on Global writes
status: Accepted
date: 2026-04-27
accepted_date: 2026-05-13
layer: L1
amends: [0036]
---

# ADR-0127: Optimistic concurrency on Global writes (`_version` property)

**Status:** Accepted (Phase 07 — M3 A inline flip 2026-05-13)

**Date:** 2026-04-27 · **Accepted:** 2026-05-13

**Amends:** ADR-0036 (no multi-writer concurrency control — narrowed; OCC introduced for Global writes; Local writes stay single-writer enforced by per-user mutex).

## Context

ADR-0036 documented "no multi-writer concurrency control" with the rationale that the Server Layer enforces serialisation via `GLOBAL_PROMOTE_LOCK` plus per-user mutexes. The pivot (ADR-0118) renames `GLOBAL_PROMOTE_LOCK` to `RELEASE_SHIP_LOCK` and uses it only at release-ship — ordinary `propose_for_promotion` calls do NOT hold a global lock.

Result: under the pivot, multiple admins can simultaneously call `propose_for_promotion` for different user drafts. They write to different `mindsos_pending_global_<role>` graphs but all of them touch the same `pending_mutations` SQLite table and may eventually mutate overlapping nodes when admin proposes are aggregated for release.

Per-user Locals stay single-writer (enforced by per-user mutex). The new gap is **Global** (and pending-Global) writes.

## Decision

Add `_version: int` as a Core-reserved property on every node and edge. Writes to **Global** graphs use optimistic concurrency:

```cypher
// Update node with optimistic concurrency:
MATCH (n:Node {id: $id, _version: $expected_version})
SET n += $props, n._version = $expected_version + 1
RETURN n
```

If the MATCH returns zero rows, the conditional write failed (someone else wrote first). The Repository raises `OptimisticConcurrencyConflict(node_id, expected_version, actual_version)`. Caller's typical response is **read current state, retry**.

**Scope:**

- **Global writes** use OCC. Includes pending-Global graphs (pivot).
- **Local writes** stay single-writer (per-user mutex enforces; OCC adds no value over a held lock).
- **WAL writes** (per ADR-0122) skip OCC — WAL is append-only by construction.
- **Reconstruction** (`_restore_*` factories per ADR-0031) skips OCC — load path bypasses write path.

**`_version` semantics:**

- `int`, monotonically increasing per node/edge.
- Set to `1` on initial create (via `add_*` methods).
- Incremented on every `update_*` and `remove_*` operation.
- **Reserved property name** in Core. User properties cannot be named `_version`. Joins the existing reserved set (per ADR-0032).
- Survives `MetagraphSnapshot` (per ADR-0027) — snapshot deep-copies `_version` along with other properties.

**Repository API (Phase 07 P28 B amendment — L1 vs L0/L2 split):**

```python
# L1 mechanism: bump always; OCC check opt-in via expected_version.
GraphRepository.update_node_properties(
    graph_id: str,
    node_id: str,
    properties: dict,
    *,
    expected_version: int | None = None,  # opt-in; None ⇒ no OCC predicate, just bump.
) -> int  # returns new version
```

* **L1 mechanism (this ADR, Phase 07 P7 C):** `_version` ALWAYS bumps on the update path. When `expected_version is not None`, the MATCH carries `_version: $expected_version`; zero rows ⇒ `OptimisticConcurrencyConflict`. When `expected_version is None`, the predicate is omitted; bump happens unconditionally (last-write-wins at L1).
* **L0/L2 policy wrapper (per Phase 07 P28 B + P84 B):** Global-write repositories at L0/L2 wrap L1 with a policy that REQUIRES `expected_version` for Global writes and raises `MissingExpectedVersionError` when callers omit it. The exception class lives at L0/L2 next to its raiser, **not in `mindsos_core/exceptions.py`** (Phase 07 P84 B — exception ships with its raiser).

For Local writes, the L0/L2 wrapper passes through; `expected_version` is ignored (single-writer assumption enforced by per-user mutex).

**Retry pattern (caller-side):**

```python
for attempt in range(MAX_RETRIES):
    node = repo.get_node(graph_id, node_id)
    new_props = compute_new_props(node)
    try:
        repo.update_node_properties(
            graph_id, node_id, new_props,
            expected_version=node._version,
        )
        break
    except OptimisticConcurrencyConflict:
        continue  # re-read, retry
else:
    raise OptimisticConcurrencyExhausted(...)
```

`MAX_RETRIES = 5` default; configurable per `FalkorConfig(occ_max_retries=...)`. Beyond the retry count, the caller raises and the operation fails. ADR-0115's audit gate logs OCC retry counts as a metric.

## Rationale

Per-user mutexes solve single-user concurrency. The pivot's `RELEASE_SHIP_LOCK` solves the all-or-nothing release. **Global pre-release writes** (admin curation, multiple admins editing pending-Global) sit in the gap: not single-user, not release-ship.

OCC is the lightest-weight pattern that addresses this gap. It costs:

- One extra column on every node/edge anchor row (`_version` int).
- One extra MATCH predicate per write (cheap with the ADR-0123 indexes).
- A retry loop in callers (boilerplate; capturable in a Repository decorator).

Pessimistic locking at graph level was an alternative; rejected because long-running operations would block other admins, and the lock state lives in process memory (incompatible with future multi-process deployment).

## Consequences

**Good:**

- Concurrent admin curation of pending-Global is safe; conflicts surface as `OptimisticConcurrencyConflict` instead of silent last-write-wins.
- The pivot's audit log (per ADR-0115) gains conflict-rate metrics — visibility into how often admins step on each other.
- Compatible with future multi-process deployment; OCC is process-agnostic where pessimistic locks aren't.

**Tradeoffs:**

- Every Global write reads-then-writes (one extra round-trip per write). Mitigation: batched MERGE via UNWIND (per ADR-0022) reads the version inline; cost is one column read, not a separate query.
- Retry loop boilerplate. Mitigation: `Repository.update_with_retry(...)` helper that wraps the loop. Caller still needs to pass a `compute_new_props` callable.
- `_version` joins the reserved property set. Trivial reservation but documented.
- OCC doesn't help across multi-statement operations. A multi-statement op with OCC on each statement can still see partial inconsistency mid-op. The WAL graph (ADR-0122) is the answer there.

**Coordinated changes:**

- `mindsos_core/models/node.py`, `models/edge.py`, etc. — `_version: int = 1` field; `_version` added to `RESERVED_PROPERTY_KEYS` (ADR-0032).
- `mindsos_core/persistence/graph_repository.py` — `expected_version` parameter; `OptimisticConcurrencyConflict` exception.
- `mindsos_core/persistence/integrity.py` (ADR-0123) — verify_invariants checks `_version` is monotone per node history (where history is available).
- `mindsos_server/promotion_v2.py` (per ADR-0118 slice) — admin propose flow uses OCC on pending-Global writes.
- New exception types in `mindsos_core/exceptions.py`.

## Alternatives considered

1. **Per-graph pessimistic lock.** Rejected — long-running operations block; in-process locks don't scale to multi-process; doesn't compose with FalkorDB's connection model.
2. **`modified_at` timestamp instead of `_version` int.** Rejected — clock skew (especially in multi-process deployment) breaks ordering. Integer counter is unambiguous.
3. **OCC on Local writes too.** Rejected — per-user mutex already serialises; OCC adds round-trip cost without correctness benefit.
4. **No OCC; rely on `RELEASE_SHIP_LOCK` for everything.** Rejected — the pivot explicitly does NOT hold the global lock during `propose_for_promotion`. Re-introducing a lock contradicts the pivot's scale goal.
5. **CRDT approach.** Rejected — complexity cost dwarfs the use case; admin-edit conflicts are rare and human-resolvable.

## Implementation references

- `mindsos_core/models/{node, edge (Edge+HyperEdge), metagraph (MetaEdge+MetaHyperEdge), intergraph_edge, intergraph_hyperedge}.py` — `_version: int = 1` field on all 7 core element types (Phase 07 P10 A amended P26 A — Node included; Phase 03 stripped it from the slim).
- `mindsos_instances/models/element_instance.py` — `_version` field on `ElementInstance` + `CompositeInstance` (Phase 07 P11 A — cross-package).
- `mindsos_core/schema/validation.py` — **NO EDIT** at Phase 07 (`_version` already reserved at line 54 since Phase 04 per P38 A strike).
- `mindsos_core/persistence/graph_repository.py` — OCC predicate in update path; bump-always; zero-row MATCH raises `OptimisticConcurrencyConflict`.
- `mindsos_core/exceptions.py` — Phase 07 P21 A amended P84 B: ships **4 exceptions only** at L1 (`PersistenceError`, `IntegrityCheckError`, `OptimisticConcurrencyConflict`, `OptimisticConcurrencyExhausted`). **`MissingExpectedVersionError` ships at L0/L2** with the Global-policy wrapper (next to its raiser); not at L1.
- `mindsos_server/promotion_v2.py` — uses OCC on pending-Global (post-slice integration with KL).
- `docs/dev/internals/core.md` — OCC section.
- Tests: Phase 07 `tests/phase_07/test_occ_unit.py` (P66 A unit) + `tests/phase_07/test_client_falkor_integration.py::test_occ_conflict_against_live` (P66 A integration).

**Acceptance criteria (Phase 07 P27 C amendment):** *Accepted when L1 mechanism ships + `docs/dev/internals/core.md` documents the pattern; consumer integration (KL `propose_for_promotion`, server `release_update`) tracked separately.* Met by Phase 07: `_version` field on 9 dataclasses; OCC predicate in `GraphRepository.update_*_properties`; `OptimisticConcurrencyConflict` raised on zero-row MATCH; `docs/dev/internals/core.md` "Persistence layer" §OCC documents the pattern.
