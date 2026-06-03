---
last_confirmed_phase: 14a
---

# User-Local authoring (L2)

This page describes the lifecycle path for **user-originated content**
that lands in a user's Local metagraph. It's one of three sibling paths
indexed by [knowledge-lifecycle.md](knowledge-lifecycle.md); see also
[admin-global-shipping.md](admin-global-shipping.md) and
[promotion-bridge.md](promotion-bridge.md).

> Several ADRs cited below are still **Proposed**. This page amends
> (`last_confirmed_phase` flip) as each ADR's consumer phase ships.

## What gets written via this path

Two role-graphs are **Local-only** per
[ADR-0044](../decisions/adr/0044-memories-move-to-local-per-user.md)
(Accepted) and the upper-layer role design (legacy spec at
`_source_backup/docs_legacy_full/DESIGN_UPPER_LAYER_ROLES.md` §4.2,
outside the published docs tree):

- `episodic_memories` — autobiographical; this user's record of completed tasks (Episode per-task entries + Memory clustering composites; Phase 39 rename per ADR-0044 §am-3).
- `capacity-state` — per-user snapshots of L3 resident state.

Three more role-graphs admit **Local drafts** (with the canonical
version living in Global; promotion is the bridge):

- `concepts` — user-drafted concept additions before promotion.
- `lexicon` — user-drafted entries before promotion.
- `alignment:<role-a>:<role-b>` — user-drafted alignments per pair.

Local-only roles never reach Global except via Promotion (see
[promotion-bridge.md](promotion-bridge.md)). Draft-then-promote roles
use Local as a staging area; the canonical version is admin-curated +
release-shipped.

## The write path (after Phase 25 / 33 / 34 / 35 land)

```
L4 orchestrator decides "consolidate this Mental Model into a memory"
  └→ invokes L3 capacity capacity:consolidate:mm (ADR-0145)
       └→ capacity acquires kl.writeable(session, role='episodic_memories', scope='local')
            └→ returns KLWriteHandle (ADR-0143; never mutates)
            └→ handle.mint_iri('Memory', ...) → episodic-memories-1:memory:<user_id>:<memory_id>
            └→ handle.validate_node(...) — KL semantic validators (ADR-0139)
            └→ handle.graph().add_node(...) — L1 mutation primitive
            └→ returns WriteResult | ProblemTraceRecord (ADR-0146)
```

This path is **not implemented yet.** It is specified by the chain
ADR-0138 / 0143 / 0145 / 0146 / 0147 (all Proposed) plus ADR-0139
(Proposed; lands in Phase 36). Each ADR flips Accepted as its consumer
phase ships.

The line: L1 owns mutation; L3 capacities are translations of L1
methods for specific uses; L2 (KL) stops translating (per
[ADR-0138](../decisions/adr/0138-kl-drops-write-api.md)). KL retains
only data + accessors + validators after Phase 33-35 land.

## Capabilities required

- `CAN_WRITE_LOCAL_MEMORIES` (per ADR-0145 `capacity:consolidate`).
- `CAN_WRITE_LOCAL_CAPACITY_STATE` (per `capacity:state`).
- `CAN_AUTHOR_DRAFTS` (per `capacity:author` for `concepts` / `lexicon`
  / `alignment` drafts).
- `CAN_PROPOSE_MUTATION` (per `capacity:promote` — entry-point to the
  promotion bridge; see [promotion-bridge.md](promotion-bridge.md)).

All capabilities are session-scoped; Server (Phase 18+) issues sessions
per ADR-0002 / ADR-0019.

## Failure semantics

Per
[ADR-0146](../decisions/adr/0146-l3-symmetric-write-invocation-contract.md),
write capacities return `WriteResult | ProblemTraceRecord` — they never
raise for business-logic failure. Failure modes:

- `CAPABILITY_DENIED` — session lacks the required cap.
- `VALIDATION_FAILED` — KL semantic validator rejected the write.
- `L1_REJECTED` — L1 structural violation (schema, XRef integrity,
  reserved property key, duplicate id).
- `OCC_RETRIED_OUT` — optimistic concurrency control exhausted retries
  per ADR-0127.

L1 primitives raising for **programmer error** (wrong types, wrong
graph) propagate as Python exceptions and crash the invocation; this is
intentional per ADR-0146 §"Failure-mode table". The line:
business-logic failure → record; programmer error → exception.

## Schema strictness

Per [ADR-0149](../decisions/adr/0149-l2-role-schemas-strict-false-and-tightening-rule.md)
(Accepted): all 9 L2 role-graph schemas ship at `strict=False` until a
per-role tightening ADR amendment runs (`strict_support.py` inventory
output + 2-week-no-edit observation + ADR amendment naming the flip).
The 2-week rule applies symmetrically to Local-authored content;
expect typo-class write defects until each role tightens.

## What does NOT go through this path

- **Importer-driven Global content.** Admin importers write Global
  directly. See [admin-global-shipping.md](admin-global-shipping.md).
- **Bootstrap of the role-graphs themselves.** Bootstrap is Phase 14's
  scope; see `docs/concepts/global-local.md` (forthcoming).
- **`promote()` / direct cross-user writes.** The shipped `promote()`
  deletes per
  [ADR-0141](../decisions/adr/0141-delete-shipped-promote.md)
  (Proposed); the bridge replacement is in
  [promotion-bridge.md](promotion-bridge.md).

## References

Accepted:

- [ADR-0017](../decisions/adr/0017-schema-strictness-opt-in.md) —
  schema strictness per-schema.
- [ADR-0044](../decisions/adr/0044-memories-move-to-local-per-user.md)
  — memories Local-per-user.
- [ADR-0045](../decisions/adr/0045-per-role-iri-builders.md) —
  per-role IRI builders.
- [ADR-0149](../decisions/adr/0149-l2-role-schemas-strict-false-and-tightening-rule.md)
  — L2 schemas strict=False with 2-week tightening rule.
- [ADR-0150](../decisions/adr/0150-l2-knowledge-lifecycle.md) —
  closed role-set.

Proposed (this page amends as they ship):

- [ADR-0138](../decisions/adr/0138-kl-drops-write-api.md) — KL drops
  write API.
- [ADR-0139](../decisions/adr/0139-hybrid-invariant-home.md) — hybrid
  invariant home.
- [ADR-0143](../decisions/adr/0143-kl-write-handle-pattern.md) —
  `KLWriteHandle` pattern.
- [ADR-0145](../decisions/adr/0145-l3-per-target-write-capacity-categories.md)
  — write categories.
- [ADR-0146](../decisions/adr/0146-l3-symmetric-write-invocation-contract.md)
  — symmetric write contract.
- [ADR-0147](../decisions/adr/0147-l3-per-flow-write-capacity-build-pattern.md)
  — per-flow build pattern.
