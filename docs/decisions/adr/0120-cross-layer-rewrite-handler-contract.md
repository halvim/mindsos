---
title: Cross-layer rewrite handler contract (v1 contract only; impl deferred)
status: Deferred
date: 2026-05-22
layer: L0 / cross-layer
amends: []
related: [0114, 0118, 0125]
---

# ADR-0120: Cross-layer rewrite handler contract (v1 contract only)

**Status:** Deferred (contract drafted 2026-05-22 — Phase 24 draft; contract only at P24; first KL implementation at Phase 25 alongside lazy migration; Capacity implementation at L3 ship phase; L4 / L5 implementations are v2.)

**Date:** 2026-05-22

**Related:** [ADR-0114](0114-release-manifest-and-version-db-schema.md) (`manifest_json.rewrite_map` source); [ADR-0118](0118-per-user-transactional-promotion.md) (release-ship + lazy-migration architecture this contract serves); [ADR-0125](0125-lazy-local-hydration-with-lru-eviction.md) (per-user lazy hydration which lazy migration extends); `PIVOT_V1_SCOPE_2026-04-26.md` §6.B.1 (cross-layer ref breakage problem this addresses) + §7.3 (lazy migration mechanism) + §7.4 (multi-Local rollback semantics).

## Context

ADR-0118 §"Decision" §3 prescribes lazy per-user migration: at
session start, each user's Local checks `last_synced_release_id <
current_release_id` and applies the rewrite map of every release
between. The rewrite map content shape is set by ADR-0114 §3
(`manifest_json.rewrite_map: dict[source_local_node_id, canonical_
global_node_id]`).

But the migration step itself — "apply this rewrite map to a user's
Local" — is layer-specific:

- **KL (mindsos_knowledge)** owns role-graph nodes and intra-Local
  edges. KL's rewrite handler must update `ref:<role>` properties
  and XRef rows that point at frozen-then-promoted draft IDs to
  point at the canonical Global IDs instead.
- **Capacity (mindsos_capacity, L3 unshipped)** owns capacity-state
  + problem-trace graphs. Capacity's rewrite handler must update
  cross-layer refs from capacity-state nodes back to L2 promoted
  Global nodes.
- **L4 / L5 (unshipped)** own promoted-pipelines + memories +
  mental-model instances. Their handlers are v2 per PIVOT §6.B.4 +
  §6.B.7.

PIVOT §6.B.1 + §6.B.3 establish the ref auto-upgrade contract at
the data-plane level (refs resolve by node id; bumps auto-upgrade).
This ADR establishes the **migration-time handler contract** that
each layer implements to apply the data-plane shift atomically per
user.

Phase 24 ships only the contract — no consumer at P24. Phase 25
ships the KL implementation alongside the lazy-migration code path.

## Decision

Each layer that participates in user-Local state ships a single
function with the contract:

```python
def apply_rewrite_map(
    local_metagraph: Metagraph,
    rewrite_map: Mapping[str, str],  # source_local_node_id → canonical_global_node_id
    release_id: int,
    *,
    audit_writer: AuditWriterProtocol,
) -> RewriteResult: ...
```

### 1. Contract obligations

A conforming `apply_rewrite_map` implementation MUST:

1. **Be idempotent.** Applying the same rewrite_map twice is a no-
   op the second time. Implementations achieve this by checking
   that source IDs in the rewrite_map still exist in the Local
   before applying; an already-rewritten Local will have no
   matching source IDs and skip cleanly.
2. **Be atomic per user.** Either all rewrites in the map apply, or
   none. Layers achieve atomicity via their own substrate (KL: WAL
   graph per ADR-0122; Capacity: idempotent MERGE per ADR-0023).
   Cross-layer atomicity is NOT required — each layer's
   `apply_rewrite_map` runs independently.
3. **Delete the source node from the user's Local.** PIVOT §7.4
   move-semantics. The frozen draft becomes the canonical promoted
   node; the user's Local copy is removed (refs are rewritten
   first).
4. **Rewrite all refs whose target is in `rewrite_map.keys()`.**
   This includes `ref:<role>` properties on nodes/edges in the
   Local, XRef rows that target the source IDs, and (for L3+)
   cross-layer back-refs.
5. **Emit `EVT_MIGRATION_APPLIED` audit row** with payload `{
   user_id, release_id, layer, rewrite_count, source_ids_processed }`
   on success.
6. **Raise `MigrationFailedError(user_id, release_id, layer,
   cause)` + emit `EVT_MIGRATION_FAILED`** on any failure. The
   user's Local stays at `last_synced_release_id < release_id`;
   migration retries at next session start.

### 2. `RewriteResult` shape

```python
@dataclass(frozen=True)
class RewriteResult:
    user_id: str
    release_id: int
    layer: Literal["knowledge", "capacity", "intelligence", "mental_model"]
    rewrite_count: int                     # how many refs were rewritten
    source_ids_processed: list[str]        # which source IDs were found and removed
    source_ids_not_found: list[str]        # source IDs in rewrite_map but absent from Local (no-op idempotent path)
    audit_event_id: int
```

### 3. Per-layer implementation phasing

| Layer | Handler module | Ship phase | Status at P24 |
|---|---|---|---|
| KL | `mindsos_knowledge/migration.py::apply_rewrite_map` | Phase 25 | NOT shipped — contract only |
| Capacity | `mindsos_capacity/migration.py::apply_rewrite_map` | L3 ship phase (33-35) | NOT shipped |
| L4 (Intelligence) | TBD | v2 | NOT shipped |
| L5 (Mental Model) | TBD | v2 | NOT shipped |

At Phase 24 ship: this ADR ships as Proposed; no module ships;
contract is documentary anchor for Phase 25's KL implementation.

### 4. Lazy migration orchestration (Phase 25 substrate)

`MindsOSServer.start_session(user_id)` (Phase 25 first-ship) walks:

```python
last_synced = read_user_metadata(user_id).last_synced_release_id  # NULL → 0
current = max_release_id_status_shipped()                          # may equal last_synced

if last_synced < current:
    for release_id in range(last_synced + 1, current + 1):
        if releases[release_id].status != "SHIPPED":
            continue                                               # skip FAILED
        rewrite_map = releases[release_id].manifest_json["rewrite_map"]
        if not rewrite_map:                                        # empty at admin-direct
            continue
        for layer_handler in installed_layer_handlers(user_id):
            layer_handler.apply_rewrite_map(
                local_metagraph=user_local_for(user_id, layer_handler.layer),
                rewrite_map=rewrite_map,
                release_id=release_id,
                audit_writer=audit_writer_for(user_id),
            )
    update_user_metadata(user_id, last_synced_release_id=current)
```

Cross-layer atomicity is **not** required: each layer's handler
runs independently. If KL's handler succeeds and Capacity's fails,
the user's Local is in mixed state for `release_id`; next session
retries Capacity (idempotent — KL's already-applied rewrites are
no-ops on the second pass). `last_synced_release_id` is updated
only when **all** layer handlers for that release succeed.

Failure-per-user contains to that user per ADR-0118 §"Decision" §3.

## Rationale

- **One contract, many implementations** — layers know their own
  ref shapes (KL has `ref:<role>` properties + XRef; Capacity has
  cross-layer back-refs); a single shared implementation would
  either be over-generic (slow + complex) or under-specific
  (misses layer-specific invariants).
- **Atomicity per layer per user is the right granularity.** Cross-
  layer atomicity would require a distributed transaction across
  KL's WAL graph + Capacity's substrate; v1 has no such primitive
  and the failure mode (mixed state, retry-able) is acceptable.
- **Idempotency is structural.** Source-ID-presence check is the
  natural guard; layers don't need extra "have I applied this
  release" tracking because the rewrite_map's source IDs are
  themselves the marker.
- **Contract at P24, impl at P25** — the contract anchors the
  `rewrite_map` shape from ADR-0114; Phase 25 implements without
  re-deciding shape.

## Consequences

**Good:**

- Phase 25 KL implementation has a locked contract to follow; no
  shape re-decisions.
- L3 / L4 / L5 implementations slot in additively without
  retrofitting the contract.
- Per-user failure containment matches ADR-0118 §"Decision" §3
  guarantee.
- Empty rewrite_map (admin-direct ATOM at P24) is the no-op fast
  path: the for-loop body is a single `if not rewrite_map: continue`.

**Tradeoffs:**

- Mixed-state user (KL applied, Capacity not) is real until next
  session retries. Documented as expected; users won't notice if
  Capacity isn't touched in their session.
- Migration runs at user pace, not release pace. A user offline
  for 10 releases catches up at next login (10 sequential apply_
  rewrite_map calls). Acceptable per ADR-0118 §"Consequences"
  "user pace, not admin pace."
- `audit_writer` parameter couples the contract to ADR-0013's
  audit machinery; alternative would be returning audit events to
  the orchestrator. Direct injection is simpler.
- L4 / L5 are v2 — early L4 ref designs must respect this
  contract (Phase 14a §3 PB-G2 promotion-bridge.md docs the
  Proposed-ADRs maturity banner).

**Coordinated changes (Phase 24 ship — contract only):**

- This ADR file ships at `/Layered Intelligence/docs/decisions/adr/`.
- `mindsos_knowledge/` — no Phase 24 changes; module ships at Phase
  25.
- `mindsos_admin/promotion.py` — no consumer interaction at P24
  (admin-direct rewrite_map is empty per ADR-0114 §3).

**Coordinated changes (Phase 25 ship — KL impl):**

- `mindsos_knowledge/migration.py` — `apply_rewrite_map` ships.
- `mindsos_server/orchestrator.py` (Phase 25 module) — `start_session`
  walks releases + dispatches to layer handlers.
- `mindsos_server/audit.py` — `EVT_MIGRATION_APPLIED` +
  `EVT_MIGRATION_FAILED` constants (deferred from P24 per Phase 24
  design log PB-11(a)).
- `tests_kl/integration/test_apply_rewrite_map.py` — KL impl tests.

## Alternatives considered

1. **Single shared `apply_rewrite_map` in `mindsos_server`.**
   Rejected — server doesn't know layer-specific ref shapes;
   would have to import every layer's persistence module +
   reimplement layer-specific logic. Layer-owned implementation
   is the right granularity.
2. **Cross-layer atomic migration via distributed transaction.**
   Rejected — no v1 primitive exists; failure mode (mixed state,
   idempotent retry) is acceptable; complexity cost > benefit.
3. **Eager migration at release_update (admin-paced).** Rejected by
   ADR-0118 §"Alternatives" #4 — blocks admin command linearly
   with user count; hostile to offline users. Lazy is structural.
4. **Migration tracked per layer per user separately.** Rejected —
   adds a 2D tracking table (user × layer × last_synced_release);
   the per-user `last_synced_release_id` + idempotent handler
   pattern subsumes the use case at simpler shape.
5. **Migration handler returns events to orchestrator instead of
   calling audit_writer.** Considered — would isolate handlers
   from audit coupling. Rejected for v1: direct injection is
   simpler; Phase 25 may revisit if a second audit consumer
   surfaces.

## Implementation references

- This ADR (contract anchor at P24).
- Phase 24 ships no consumer or implementation.
- Phase 25 ships `mindsos_knowledge/migration.py` +
  `mindsos_server/orchestrator.py` consumer.
- Future phases ship `mindsos_capacity/migration.py` (L3 phase) +
  L4 / L5 handlers (v2).

ADR moves Proposed → Accepted when (a) at least one layer's
`apply_rewrite_map` ships, (b) `MindsOSServer.start_session` calls
it during lazy migration, (c) `EVT_MIGRATION_APPLIED` /
`EVT_MIGRATION_FAILED` audit events ship. All three first-fire at
Phase 25.
