# ADR-0007: In-memory `MetagraphSnapshot` for promotion rollback

- **Status:** Superseded by [ADR-0118](0118-per-user-transactional-promotion.md) (2026-05-22 — Phase 24 ship; ADR-0118 + ADR-0129 §am2 close the supersession in code)
- **Date:** 2026-04-22 (accepted), 2026-05-22 (superseded)
- **Related:** ADR-0006, [ADR-0118](0118-per-user-transactional-promotion.md) (superseding ADR), [ADR-0129](0129-metagraph-snapshot-narrowed-to-release-ship.md) §am2 (snapshot vestigial in `release_update`; module retained as defensive Core primitive with zero v1 consumer)

!!! warning "Superseded"
    The 2026-04-25 architectural review identified load-bearing problems with the multi-author atomic promotion model this ADR supports (phantom-promotion bug, FalkorDB drift on partial flush failure, scale wall via `GLOBAL_PROMOTE_LOCK`). The 2026-04-26 design pivot (`docs/PIVOT_V1_SCOPE_2026-04-26.md`) replaced the model with per-user transactional promotion + release-boundary atomicity ([ADR-0118](0118-per-user-transactional-promotion.md), Accepted at Phase 24 ship 2026-05-22).

    Phase 24 ship (2026-05-22) closed the supersession-in-progress promise: `release_update` ships in `mindsos_server/release.py`; per-user `propose_for_promotion` ships in `mindsos_admin/promotion.py`. The architectural premise this ADR codifies (cross-user atomic multi-Local rollback via in-memory `MetagraphSnapshot`) is replaced.

    The `MetagraphSnapshot` machinery itself is **retained as a defensive Core primitive** per ADR-0129 §am2 — but `release_update` does NOT use it (Phase 24 design log PB-7(a) probe demonstrated snapshot is vestigial in halvim's `release_update` given ADR-0125 lazy hydration + `MetagraphRepository.persist` write-through semantics). Zero v1 consumers; module preserved against future feature need (undo / branching / time-travel debugging).

    ADR-0027 (Metagraph snapshot restore in place, L1) remains Accepted as the substrate contract — even with zero v1 consumers, the contract is the right shape if a future consumer arrives.

## Context

`promote()` mutates the Global Metagraph and every author's Local in a single logical operation. If the downstream flush of any Local to FalkorDB fails, we must restore *every* touched metagraph to its pre-promotion state and surface a `FlushFailedError` — partial success is not acceptable because downstream layers (Capacity, Intelligence) walk refs across Locals and Global and would see dangling `ref:global_*` on a Local whose target node vanished on retry.

KL's metagraph objects hold `IdentityRegistry` references that other parts of the system (installed Locals map, open `KnowledgeLayer` handles, views returned from earlier reads) close over. A rollback that *replaced* the metagraph object would leave every such reference dangling.

## Decision

Introduce a Core-layer helper, `mindsos_core.metagraph_snapshot.MetagraphSnapshot`, with two operations:

- `MetagraphSnapshot.of(mg) -> MetagraphSnapshot` — captures nodes, edges, hyperedges, graph-of-graphs topology, and attribute state deeply enough to reconstruct the metagraph's state.
- `snap.restore_into(mg) -> None` — **mutates `mg` in place**: removes what was added since the snapshot, re-inserts what was removed, restores mutated properties. The `Graph` and `Metagraph` object identities are preserved; the shared `IdentityRegistry` continues to resolve existing references.

The promotion orchestrator takes a snapshot of the Global and of every touched Local *before* calling `KL.promote` and *before* any flush. On any failure during flush, it calls `restore_into` on each snapshot (best-effort; logged on failure), audits `PROMOTION_FAILED`, and raises `FlushFailedError`.

## Rationale

- **Identity preservation is non-negotiable.** Replacing the metagraph object would invalidate every reference held by installed Locals, views, KL itself, and the server's install records. In-place restore is the only model that keeps those references valid.
- **In-memory snapshot is cheap.** Promotions touch a bounded number of nodes (candidates + attribution edges); Locals are user-sized, not planet-sized. The RAM cost is modest compared to forking FalkorDB-side transactions.
- **No cross-store transaction needed.** FalkorDB writes happen only during `LocalPersister.save` calls *after* in-memory promotion succeeds. If any save fails, we restore in-memory state and the FalkorDB side of saved Locals may be ahead of the in-memory state by that session — but the next successful flush reconciles, and in the meantime the in-memory state is the source of truth.
- **Core-layer placement.** Snapshot is a generic metagraph capability; placing it in Core means upper layers (e.g., a future "undo" feature in Capacity) can use it without breaking layering.

## Consequences

- Core grows a new module. The developer guide documents that Core must not gain other primitives to support promotion — snapshot is the only additive hook.
- Rollback is best-effort at the logging level: if `restore_into` itself throws (truly unexpected), we log loudly and let the server continue. Tests cover the normal path exhaustively.
- A snapshot holds references to node/edge objects; if any of those objects are mutated *in place* between snapshot and restore without going through mutation APIs we track, the restored state will reflect the late mutation. Convention: promotions never pass user code between snapshot and restore.
- The contract `restore_into` mutates in-place is load-bearing and tested — the test fixture captures `id(metagraph)` before snapshot and asserts it's unchanged after restore.

## Alternatives considered

1. **`copy.deepcopy` the metagraph.** Rejected — would replace the object, breaking identity-based references; also O(N) on unrelated state.
2. **Serialize to bytes and re-parse.** Rejected — slow, identity-destroying, and requires a serializer we don't otherwise need.
3. **FalkorDB-side transactions around promotion.** Rejected — KL is in-memory at runtime by design; coupling to a storage engine's transactional semantics at this layer contradicts ADR-0001.
4. **Write-ahead log, replay on recovery.** Overkill for a local-first tool; also doesn't solve the in-memory rollback problem during a single promote call.
