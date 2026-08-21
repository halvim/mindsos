---
title: Superseded decisions
tag: shipped
teaser: ADRs that have been replaced by later decisions.
---

# Superseded decisions

When an ADR's context changes or a later decision replaces it, the old ADR is marked **Superseded** with a link to the new one. The old text stays intact for historical reference.

When an ADR becomes superseded:

1. Keep the original ADR file with its original number and text.
2. Change its `status:` front-matter line to `status: Superseded`.
3. Add a line like `superseded_by: ADR-NNNN` to link the replacement.
4. The reader can see the old reasoning, the old decision date, and the new decision that replaced it.

## Effective supersessions

These supersessions are **in effect** — the superseding ADR's code has shipped. Each original ADR's front-matter is `status: Superseded`; the prose Status line names the replacement.

| Original | Superseded by | Effective | Notes |
|----------|---------------|-----------|-------|
| [0049](adr/0049-similarity-report-before-promotion.md) | [0115](adr/0115-release-ship-audit-gate.md) + [0144](adr/0144-similarity-at-release-ship-audit-gate.md) | Phase 24 | Gate-on-`promote()` replaced by the release-ship audit gate. |
| [0053](adr/0053-promote-per-candidate-atomic-rollback.md) | [0118](adr/0118-per-user-transactional-promotion.md) + [0129](adr/0129-metagraph-snapshot-narrowed-to-release-ship.md) | Phase 24 | Per-candidate atomic rollback replaced by per-role atomic ship + admin rerun. |
| [0056](adr/0056-promotion-result-preserves-input-order.md) | [0114](adr/0114-release-manifest-and-version-db-schema.md) + [0118](adr/0118-per-user-transactional-promotion.md) | Phase 24 | `PromotionResult` order semantic replaced by the `manifest_json.included_mutation_ids` contract. |
| [0069](adr/0069-type-compat-auto-discovery.md) | [0156](adr/0156-l3-bipartite-topology-reframe.md) | Phase 42 | TYPE_COMPAT auto-discovery + `discovery.py` retired for explicit bipartite PRODUCES/CONSUMES edges. |
| [0073](adr/0073-residents-descriptive.md) | [0155](adr/0155-monitor-lifecycle-relocated-from-l3-to-l4.md) | Phase 41 | Resident event-loop relocated from L3 to L4 (`KIND_RESIDENT` → `KIND_MONITOR`). Note: ADR-0155 is itself later amended by [0188](adr/0188-submind-construct-and-two-output-model.md) (SubMind reflex construct). |
| [0086](adr/0086-auto-discovery-with-admin-override.md) | [0156](adr/0156-l3-bipartite-topology-reframe.md) | Phase 42 | TYPE_COMPAT substrate + `add_type_compat` + `rediscover_all` retired. |
| [0033](adr/0033-property-bag-on-metagraph-deferred.md) | [0130](adr/0130-property-bag-on-metagraph-graph.md) | L1 redesign | The deferred property-bag lands as typed `properties` on `Metagraph` / `Graph`. |
| [0101](adr/0101-l4-per-session-orchestrator.md) | [0171](adr/0171-six-phase-task-lifecycle.md) | Phase 47 | Design-phase L4 tenancy menu; the shipped orchestrator is per-session, worker-per-task. |
| [0103](adr/0103-l4-attention-priority-queue.md) | [0163](adr/0163-l4-priority-tier-executor.md) | Phase 46 | Four-tier priority queue shipped as the priority-tier Executor + `attention_score`. |
| [0104](adr/0104-l4-replan-always-on.md) | [0173](adr/0173-replan-check-dispatch-and-invalidation.md) | Phase 47 | Always-on replan shipped as replan-check dispatch. |
| [0105](adr/0105-l4-replan-atomicity-discard.md) | [0173](adr/0173-replan-check-dispatch-and-invalidation.md) | Phase 47 | Discard-and-regenerate replan atomicity shipped with 0173. |
| [0106](adr/0106-l4-planning-ownership.md) | [0172](adr/0172-phase-1-five-step-task-interpretation.md) | Phase 47 | Planning-ownership (L4 orchestrates; planning is an L3 capacity) shipped via the v0 planning catalog. |

The remaining design-phase L4 menu ADRs (0102, 0107–0112) plus 0082/0083 were **not** carried into v1 as specced and are marked **Deferred** on their own files (revisit post-v1 / WSD); the live L4/L5 architecture is [ADRs 0163–0181](summary/intelligence.md).

## Supersessions in flight

These supersessions have been **proposed** by later ADRs and become effective when the superseding ADR's code lands and a user-facing doc reflects the decision (per `about.md`).

| Original | Status | Superseded by | Notes |
|----------|--------|---------------|-------|
| [0007](adr/0007-metagraph-snapshot-rollback.md) | Accepted *(supersession proposed)* | [0118](adr/0118-per-user-transactional-promotion.md) | Cross-user atomic promotion model replaced by per-user transactional + release-boundary atomicity. The `MetagraphSnapshot` machinery itself is retained; only its use for cross-user rollback is superseded. ADR-0129 documents the narrowed scope. |
| [0029](adr/0029-piggyback-metadata-via-metagraph-settings.md) | Accepted *(supersession proposed)* | [0130](adr/0130-property-bag-on-metagraph-graph.md) | `:MetagraphSettings` JSON-singleton interim mechanism replaced by typed `properties: Dict` on `Metagraph` / `Graph`. Existing settings migrate on first load. |
| [0037](adr/0037-instancing-vocabulary-in-core.md) | Accepted *(supersession proposed)* | [0132](adr/0132-instancing-moved-to-mindsos-instances.md) | Instancing vocabulary moves out of Core to a sibling `mindsos_instances` package. |

## Amendments in flight

These ADRs are not superseded but are *amended* — the original decision stands, with the later ADR narrowing or extending its scope.

| Original | Status | Amended by | Notes |
|----------|--------|-----------|-------|
| [0027](adr/0027-metagraph-snapshot-restore-in-place.md) | Accepted | [0129](adr/0129-metagraph-snapshot-narrowed-to-release-ship.md) | Mutate-in-place contract retained; caller-side use narrowed to release-ship. |
| [0028](adr/0028-metagraph-snapshot-not-serialisable.md) | Accepted | [0129](adr/0129-metagraph-snapshot-narrowed-to-release-ship.md) | Not-serialisable contract retained; usage scope narrowed. |
| [0030](adr/0030-client-protocol-minimal-sync.md) | Accepted | [0126](adr/0126-async-client-via-thread-pool-wrapper.md) | Sync Client minimal surface retained; `AsyncClient` parallel Protocol added. |
| [0034](adr/0034-core-never-validates-refs.md) | Accepted | [0128](adr/0128-hybrid-xref-cross-metagraph-refs.md) | `ref:<role>` strings stay unvalidated; XRefs gain write-time validation when target is resolvable. |
| [0035](adr/0035-uuid-generation-non-deterministic.md) | Accepted | [0131](adr/0131-pluggable-id-strategy.md) | UUID4 stays default; `IdStrategy` Protocol enables opt-in alternatives. |
| [0036](adr/0036-no-multi-writer-concurrency-control.md) | Accepted | [0127](adr/0127-optimistic-concurrency-on-global-writes.md) | Per-user Locals stay single-writer; Global writes use OCC via `_version`. |
| [0001](adr/0001-dedicated-server-layer.md) | Accepted | [0136](adr/0136-server-as-orthogonal-layer.md) | Server-as-separate-package decision unchanged; placement clarified from "Layer 0" to "orthogonal." |
| [0006](adr/0006-promotion-locking.md) | Accepted | [0118](adr/0118-per-user-transactional-promotion.md) | Per-user mutex retained; `GLOBAL_PROMOTE_LOCK` renamed `RELEASE_SHIP_LOCK` and used only at release-ship. |
| [0016](adr/0016-cross-graph-references-via-property-prefix.md) | Accepted | [0128](adr/0128-hybrid-xref-cross-metagraph-refs.md) | `ref:<role>` retained for intra-metagraph; XRef takes over cross-metagraph. |
| [0083](adr/0083-pipeline-promotion-transitive.md) | Proposed | [0118](adr/0118-per-user-transactional-promotion.md) | Capacity-layer ADR-0083 (transitive promotion of pipeline dependencies, formerly capacity-ADR-024) is superseded by the unified release manifest. |
| [0172](adr/0172-phase-1-five-step-task-interpretation.md) | Accepted | [0206](adr/0206-planning-decomposition-confidence.md) | The five-step interpretation flow and the v0 catalog stand as **shipped**. ADR-0206 §3 drops `derive_goal` and makes planning a loop, §4 retires `MAX_DEPTH`, §8 deletes the thirteen `placeholder=True` capacities — but ADR-0206 is **Proposed and unbuilt**, so 0172 stays Accepted and flips only when CORE-C4 lands. Clause-by-clause + the flip list: ADR-0172 §amendment-2. |

---

**Related:** [About ADRs](about.md) | [Full ADR log](adr/README.md)
