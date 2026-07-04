---
title: Architectural Decision Records — MindsOS
teaser: The numbered log of load-bearing decisions across all layers.
---

# Architectural Decision Records — MindsOS

This directory is the single source of truth for all load-bearing architectural decisions in MindsOS. Every ADR is numbered globally and covers decisions across all layers: the Server Layer (ADR-0001–0013), Layer 1 Core (ADR-0014–0037), Layer 2 Knowledge (ADR-0038–0059), Layer 3 Capacity (ADR-0060–0083), L3 design questions (ADR-0084–0100), and Layer 4 Intelligence (ADR-0101–0112).

ADRs follow a lightweight Nygard/MADR-style format: **Context**, **Decision**, **Consequences**, and **Alternatives considered**. Each ADR is numbered, dated, and marked with a status: **Accepted** (shipped and load-bearing), **Proposed** (agreed but not yet implemented), **Deferred** (acknowledged but not scheduled), or **Superseded** (replaced by another ADR).

## Full Index

| # | Title | Status | Layer | Aliases |
|---|-------|--------|-------|---------|
| [0001](0001-dedicated-server-layer.md) | Introduce a dedicated Server Layer above the domain stack | Accepted | Server | — |
| [0002](0002-session-and-capability-model.md) | Session-plus-capability authorization model | Accepted | Server | — |
| [0003](0003-password-and-token-scheme.md) | argon2id password hashing + opaque session tokens | Accepted | Server | — |
| [0004](0004-split-persistence.md) | SQLite for server state, FalkorDB for graphs | Accepted | Server | — |
| [0005](0005-refuse-concurrent-login.md) | Refuse concurrent login; provide kill-session escape valves | Accepted | Server | — |
| [0006](0006-promotion-locking.md) | Per-user RLocks + GLOBAL_PROMOTE_LOCK in lexicographic order | Accepted | Server | — |
| [0007](0007-metagraph-snapshot-rollback.md) | In-memory MetagraphSnapshot for promotion rollback | Accepted *(supersession proposed by 0118)* | Server | — |
| [0008](0008-cross-user-reads-no-flush.md) | Admin cross-user reads never flush (I-S3) | Accepted | Server | — |
| [0009](0009-similarity-report-freshness.md) | Similarity-report freshness via content hash | Accepted | Server | — |
| [0010](0010-layer-isolation.md) | KL does not import server (I-S1); L3 accepts SessionProtocol | Accepted | Cross-layer | — |
| [0011](0011-local-persister-protocol.md) | LocalPersister protocol with session-scoped hydrate/flush | Accepted | Server | — |
| [0012](0012-bootstrap-and-last-admin.md) | Bootstrap and reset-admin CLIs + last-admin protection | Accepted | Server | — |
| [0013](0013-audit-and-test-shim.md) | Universal audit logging and Session.for_testing() shim | Accepted | Server | — |
| [0014](0014-layer-boundary-core-only.md) | Layer boundary — Core owns primitives only | Accepted | L1 | core-ADR-001 |
| [0015](0015-instancing-model.md) | Instancing model: reference + overrides at any granularity | Accepted | L1 | core-ADR-002 |
| [0016](0016-cross-graph-references-via-property-prefix.md) | Cross-graph references via ref: property prefix | Accepted | L1 | core-ADR-003 |
| [0017](0017-schema-strictness-opt-in.md) | Schema strictness is opt-in | Accepted | L1 | core-ADR-004 |
| [0018](0018-single-mindsos-core-package.md) | Single mindsos_core package | Accepted | L1 | core-ADR-005 |
| [0019](0019-materialisation-is-lazy.md) | Materialisation is lazy | Accepted | L1 | core-ADR-006 |
| [0020](0020-metagraph-wide-shared-identity-registry.md) | Metagraph-wide shared identity registry | Accepted | L1 | core-ADR-007 |
| [0021](0021-cypher-rel-type-validation.md) | Cypher rel type validation | Accepted | L1 | core-ADR-008 |
| [0022](0022-batched-writes-via-unwind.md) | Batched writes via UNWIND | Accepted | L1 | core-ADR-009 |
| [0023](0023-two-step-writes-merge-then-set.md) | Two-step writes: merge then set | Accepted | L1 | core-ADR-010 |
| [0024](0024-deletes-leave-tombstone-anchored-removed.md) | Deletes leave tombstone anchored :removed | Accepted | L1 | core-ADR-011 |
| [0025](0025-instance-overrides-via-ov-prefix.md) | Instance overrides via ov: prefix | Accepted | L1 | core-ADR-012 |
| [0026](0026-composite-overrides-bundle-only.md) | Composite overrides bundle-only | Accepted | L1 | core-ADR-013 |
| [0027](0027-metagraph-snapshot-restore-in-place.md) | Metagraph snapshot restore in place | Accepted | L1 | core-ADR-014 |
| [0028](0028-metagraph-snapshot-not-serialisable.md) | Metagraph snapshot not serialisable | Accepted | L1 | core-ADR-015 |
| [0029](0029-piggyback-metadata-via-metagraph-settings.md) | Piggyback metadata via metagraph settings | Accepted | L1 | core-ADR-016 |
| [0030](0030-client-protocol-minimal-sync.md) | Client protocol minimal sync | Accepted | L1 | core-ADR-017 |
| [0031](0031-reconstruction-via-private-factories.md) | Reconstruction via private factories | Accepted | L1 | core-ADR-018 |
| [0032](0032-reserved-property-keys-metagraph-wide.md) | Reserved property keys metagraph-wide | Accepted | L1 | core-ADR-019 |
| [0033](0033-property-bag-on-metagraph-deferred.md) | Property bag on metagraph deferred | Superseded | L1 | core-ADR-020 |
| [0034](0034-core-never-validates-refs.md) | Core never validates refs | Accepted | L1 | core-ADR-021 |
| [0035](0035-uuid-generation-non-deterministic.md) | UUID generation non-deterministic | Accepted | L1 | core-ADR-022 |
| [0036](0036-no-multi-writer-concurrency-control.md) | No multi-writer concurrency control | Accepted | L1 | core-ADR-023 |
| [0037](0037-instancing-vocabulary-in-core.md) | Instancing vocabulary in core | Accepted | L1 | core-ADR-024 |
| [0038](0038-session-write-api.md) | Session-based write API replaces bare user_id string | Accepted | L2 | kl-ADR-001 |
| [0039](0039-transitional-str-shim-deprecation.md) | Transitional str shim with deprecation | Accepted | L2 | kl-ADR-002 |
| [0040](0040-session-protocol-duck-typing.md) | Session protocol duck typing | Accepted | L2 | kl-ADR-003 |
| [0041](0041-duplicate-capability-constants-parity-test.md) | Duplicate capability constants + parity test | Accepted | L2 | kl-ADR-004 |
| [0042](0042-kl-install-extract-hooks.md) | KL install/extract hooks for server lifecycle | Accepted | L2 | kl-ADR-005 |
| [0043](0043-kl-in-memory-only-server-owns-io.md) | KL in-memory only; server owns I/O | Accepted | L2 | kl-ADR-006 |
| [0044](0044-memories-move-to-local-per-user.md) | Memories move to Local per-user | Accepted | L2 | kl-ADR-007 |
| [0045](0045-per-role-iri-builders.md) | Per-role IRI builders | Accepted | L2 | kl-ADR-008 |
| [0046](0046-admin-enforcement-capability-based.md) | Admin enforcement capability-based | Accepted | L2 | kl-ADR-009 |
| [0047](0047-ref-types-open-vocabulary.md) | REF_TYPES open vocabulary | Accepted | L2 | kl-ADR-010 |
| [0048](0048-proxy-pattern-handles-all-local-global.md) | Proxy pattern handles all local/global | Accepted | L2 | kl-ADR-011 |
| [0049](0049-similarity-report-before-promotion.md) | Similarity report before promotion | Accepted | L2 | kl-ADR-012 |
| [0050](0050-server-owns-promotion-orchestration.md) | Server owns promotion orchestration | Accepted | L2 | kl-ADR-013 |
| [0051](0051-promoted-ref-type-marks-surviving-draft.md) | Promoted ref type marks surviving draft | Accepted | L2 | kl-ADR-014 |
| [0052](0052-report-id-deterministic-content-hash.md) | Report ID deterministic content hash | Accepted | L2 | kl-ADR-015 |
| [0053](0053-promote-per-candidate-atomic-rollback.md) | Promote per-candidate atomic rollback | Accepted | L2 | kl-ADR-016 |
| [0054](0054-promotion-validation-error.md) | Promotion validation error | Accepted | L2 | kl-ADR-017 |
| [0055](0055-baseline-similarity-heuristic-crude.md) | Baseline similarity heuristic crude | Accepted | L2 | kl-ADR-018 |
| [0056](0056-promotion-result-preserves-input-order.md) | Promotion result preserves input order | Accepted | L2 | kl-ADR-019 |
| [0057](0057-property-inventory-admin-run.md) | Property inventory admin run | Accepted | L2 | kl-ADR-020 |
| [0060](0060-l3-fixed-not-learned.md) | L3 holds only fixed functions; learned state lives in L4 | Accepted | L3 | capacity-ADR-001 |
| [0061](0061-dual-metagraph-global-local.md) | Dual metagraph (Global + per-user Local) mirrors KL | Accepted | L3 | capacity-ADR-002 |
| [0062](0062-three-node-types-capacity-monitor-adapter.md) | Three node types: Capacity, Monitor, Adapter | Accepted | L3 | capacity-ADR-003 |
| [0063](0063-datastates-purely-structural.md) | DataStates carry only a structural ShapeDescriptor | Accepted | L3 | capacity-ADR-004 |
| [0064](0064-one-shared-datastates-graph.md) | One shared capacity:datastates graph per metagraph | Accepted | L3 | capacity-ADR-005 |
| [0065](0065-twelve-functional-categories.md) | Twelve functional categories as the node-graph partition | Accepted | L3 | capacity-ADR-006 |
| [0066](0066-capacity-iri-form.md) | IRI form: capacity:<category>:<name> and datastate:<name> | Accepted | L3 | capacity-ADR-007 |
| [0067](0067-ref-types-shared-with-kl.md) | REF_TYPES vocabulary is shared verbatim with KL | Accepted | L3 | capacity-ADR-008 |
| [0068](0068-constraint-kind-property-key.md) | constraint_kind is the property key, not kind | Accepted | L3 | capacity-ADR-009 |
| [0069](0069-type-compat-auto-discovery.md) | TYPE_COMPAT edges are auto-discovered and stamped | Accepted | L3 | capacity-ADR-010 |
| [0070](0070-five-constraint-kinds.md) | Five admin-authored CONSTRAINT kinds; intra-category in slice | Accepted | L3 | capacity-ADR-011 |
| [0071](0071-pipeline-finder-bfs.md) | Pipeline-finder is BFS over TYPE_COMPAT; ignores constraints | Accepted | L3 | capacity-ADR-012 |
| [0072](0072-invoke-never-raises.md) | invoke() never raises for implementation errors | Accepted | L3 | capacity-ADR-013 |
| [0073](0073-residents-descriptive.md) | Residents are descriptive; L3 contains no event loop | Accepted | L3 | capacity-ADR-014 |
| [0074](0074-problem-trace-anomaly-only.md) | Problem-trace is in-memory, anomaly-only, drained by L4 | Accepted | L3 | capacity-ADR-015 |
| [0075](0075-in-memory-first-facade.md) | In-memory-first facade, Core-adapter agnostic persistence | Accepted | L3 | capacity-ADR-016 |
| [0076](0076-local-graph-naming.md) | One FalkorDB graph per Local metagraph: mindsos_capacity_local_<slug> | Accepted | L3 | capacity-ADR-017 |
| [0077](0077-l3-session-write-api.md) | Write API takes session: SessionProtocol | Accepted | L3 | capacity-ADR-018 |
| [0078](0078-l3-capability-local-copy.md) | Local copy of CAN_WRITE_GLOBAL + parity test | Accepted | L3 | capacity-ADR-019 |
| [0079](0079-l3-session-compat-shim.md) | Backward-compat shim with DeprecationWarning during migration | Accepted | L3 | capacity-ADR-020 |
| [0080](0080-l3-bootstrap-carveout.md) | Bootstrap carve-out: session=None Global writes still allowed | Accepted | L3 | capacity-ADR-021 |
| [0081](0081-l3-session-context-threading.md) | invoke/start_resident thread session_user_id into context | Accepted | L3 | capacity-ADR-022 |
| [0082](0082-pipeline-generation-capacity.md) | Pipeline generation is itself a category of capacity in L3 | Deferred | L3 | capacity-ADR-023 |
| [0083](0083-pipeline-promotion-transitive.md) | Promoting a pipeline transitively requires promoting its Local-capacity dependencies | Deferred | L3 | capacity-ADR-024 |
| [0084](0084-l3-capacities-fixed-not-learned.md) | L3 - Functional-category as primary axis for graphs | Accepted | L3 | L3-Q1 |
| [0085](0085-multi-graph-membership.md) | Capacities can belong to multiple graphs | Accepted | L3 | L3-Q2 |
| [0086](0086-auto-discovery-with-admin-override.md) | Auto-discovery of type-compat edges with admin override | Accepted | L3 | L3-Q3 |
| [0087](0087-richness-annotation-implicit.md) | Richness annotation in DataState type system is implicit | Accepted | L3 | L3-Q4 |
| [0088](0088-fine-grained-residents.md) | Resident capacity granularity is fine-grained | Accepted | L3 | L3-Q5 |
| [0089](0089-three-tier-memory.md) | Session persistence for residents via three-tier memory model | Accepted | L3 | L3-Q6 |
| [0090](0090-teaching-growth-model.md) | Teaching - humans add capacities; system grows via promotion | Accepted | L3 | L3-Q7 |
| [0091](0091-dreaming-bootstraps-l4.md) | Bootstrapping L4's pipeline-finder via dreaming | Accepted | L3 | L3-Q8 |
| [0092](0092-constraint-edges-admin-proposed.md) | Constraint edges are admin-authored; L4 may propose | Accepted | L3 | L3-Q9 |
| [0093](0093-datastate-synthesis-humans-only.md) | DataState synthesis - humans only | Accepted | L3 | L3-Q10 |
| [0094](0094-confidence-pipeline-level.md) | Confidence storage - pipeline-level on promoted-pipelines records | Accepted | L3 | L3-Q12 |
| [0095](0095-trace-scope-mm-plus-thin.md) | Trace system scope - Mental Model as success trace | Accepted | L3 | L3-Q13 |
| [0096](0096-failure-recording-in-mm.md) | Failure recording inside an MM via ref:problem_trace | Accepted | L3 | L3-Q14 |
| [0097](0097-retrieval-category-memories.md) | Retrieval of memories via new capacity:retrieval category | Accepted | L3 | L3-Q15 |
| [0098](0098-mental-model-retention-default.md) | Mental Model retention - retained by default into memories | Accepted | L3 | L3-Q16 |
| [0099](0099-resident-state-persistence-dynamic.md) | Resident state persistence policy - activity-based dynamic snapshots | Accepted | L3 | L3-Q17 |
| [0100](0100-resident-watches-first-input.md) | Resident granularity - watches first pipeline input | Accepted | L3 | L3-Q18 |
| [0101](0101-l4-per-session-orchestrator.md) | One IntelligenceLayer per live user session | Superseded | L4 | L4-tenancy |
| [0102](0102-l4-policy-as-meta-pipelines.md) | All decision-point policies composed from L3 capacities | Deferred | L4 | L4-policy |
| [0103](0103-l4-attention-priority-queue.md) | Orchestrator attention mechanism - priority queue | Superseded | L4 | L4-attention |
| [0104](0104-l4-replan-always-on.md) | Replan trigger - always-on at every step boundary | Superseded | L4 | L4-replan |
| [0105](0105-l4-replan-atomicity-discard.md) | Replan atomicity - discard remaining plan; regenerate | Superseded | L4 | L4-replan-atomicity |
| [0106](0106-l4-planning-ownership.md) | Planning ownership - L4 orchestrates; algorithms are L3 | Superseded | L4 | L4-planning |
| [0107](0107-l4-six-planner-menu.md) | Planner menu - six loadable planning algorithms | Deferred | L4 | L4-planners |
| [0108](0108-l4-planner-selection-learned.md) | Planner selection is learned per task shape | Deferred | L4 | L4-planner-selection |
| [0109](0109-l4-cost-estimators-as-capacities.md) | Cost estimators are L3 capacities, not static properties | Deferred | L4 | L4-cost |
| [0110](0110-l4-coherence-dream.md) | Coherence dream intent - GAN-like generator vs critic | Deferred | L4 | L4-coherence |
| [0111](0111-l4-promotion-dependency-graph.md) | Promotion dependency graph - Local capacities block Global | Deferred | L4 | L4-promotion-deps |
| [0112](0112-l4-pause-and-resume.md) | Pause-and-resume support for voluntary logout | Deferred | L4 | L4-pause |
| [0118](0118-per-user-transactional-promotion.md) | Per-user transactional promotion + release-boundary atomicity | Proposed | Server | — |
| [0121](0121-substrate-falkordb-for-graphs-sqlite-for-non-graph.md) | Substrate — FalkorDB for graphs, SQLite for non-graph state | Accepted | L1 | L1-redesign-M1 |
| [0122](0122-wal-graph-for-multi-statement-write-safety.md) | WAL graph for multi-statement write safety | Proposed | L1 | L1-redesign-W1 |
| [0123](0123-indexes-and-verify-integrity.md) | Indexes + persist-time check + per-layer verify_integrity | Proposed | L1 | L1-redesign-W2 |
| [0124](0124-streaming-loader-iter-load-and-refresh.md) | Streaming loader: iter_load and MetagraphLoader.refresh | Proposed | L1 | L1-redesign-W3 |
| [0125](0125-lazy-local-hydration-with-lru-eviction.md) | Lazy Local hydration with LRU eviction | Deferred | Server | L1-redesign-W4 |
| [0126](0126-async-client-via-thread-pool-wrapper.md) | AsyncClient Protocol via asyncio.to_thread | Proposed | L1 | L1-redesign-W5 |
| [0127](0127-optimistic-concurrency-on-global-writes.md) | Optimistic concurrency on Global writes (`_version` property) | Proposed | L1 | L1-redesign-W6 |
| [0128](0128-hybrid-xref-cross-metagraph-refs.md) | Hybrid cross-graph refs — XRef primitive + ref-string convention | Accepted | L1 | L1-redesign-M2 |
| [0129](0129-metagraph-snapshot-narrowed-to-release-ship.md) | MetagraphSnapshot scope narrowed to release-ship | Accepted | L1 | L1-redesign-M4 |
| [0130](0130-property-bag-on-metagraph-graph.md) | Property bag on Metagraph and Graph | Proposed | L1 | L1-redesign-M5 |
| [0131](0131-pluggable-id-strategy.md) | Pluggable IdStrategy on Metagraph | Accepted | L1 | L1-redesign-M6 |
| [0132](0132-instancing-moved-to-mindsos-instances.md) | Instancing vocabulary moved to mindsos_instances package | Accepted | L1 | L1-redesign-M7 |
| [0133](0133-soft-delete-via-deprecated-disputed-properties.md) | Soft-delete via deprecated_at / disputed_at properties | Proposed | L1 | L1-redesign-M9-N1 |
| [0134](0134-schema-migration-scanner.md) | Schema migration scanner + loader warning | Proposed | L1 | L1-redesign-M11 |
| [0135](0135-removal-impact-on-remove-graph.md) | RemovalImpact report on remove_graph | Proposed | L1 | L1-redesign-M10 |
| [0136](0136-server-as-orthogonal-layer.md) | Server is orthogonal to the domain stack, not Layer 0 | Accepted | Cross-layer | L1-redesign-H2 |
| [0137](0137-user-facing-request-promotion.md) | User-facing request_promotion API | Deferred | Server | L1-redesign-N6 |

!!! note "ADRs 0113–0117, 0119–0120 reserved"
    Numbers 0113 through 0120 are reserved for the [Server Layer pivot](../proposed.md#server-layer-pivot--2026-04-26) (mutation model, release manifest + version DB, audit gate, edge soft-delete, compositional metaedge immutability, per-user transactional promotion, composition-signature dedup, cross-layer rewrite handler contract). ADR-0118 is drafted; the remaining seven are pending. See `docs/HANDOFF_SERVER_PIVOT_2026-04-26.md` for the drafting plan.

!!! note "ADRs 0121–0137 — L1 redesign (2026-04-27)"
    Seventeen ADRs drafted in the L1 Core redesign pass. They formalise the substrate commitment (0121), six FalkorDB-weakness mitigations (0122–0127), the hybrid XRef model (0128), MetagraphSnapshot scope narrowing (0129), property bag (0130), pluggable IdStrategy (0131), instancing-package move (0132), soft-delete representation (0133), schema migration scanner (0134), removal-impact reporting (0135), server orthogonal placement (0136), and user-facing promotion request (0137). See `docs/HANDOFF_L1_REDESIGN_2026-04-27.md` for the migration plan.

## Per-layer summary pages

Start with the summary page for your layer:

- [L1 Core decisions](../summary/core.md)
- [L2 Knowledge decisions](../summary/knowledge.md)
- [L3 Capacity decisions](../summary/capacity.md)
- [L4 Intelligence decisions](../summary/intelligence.md)
- [Server decisions](../summary/server.md)
- [Cross-layer decisions](../summary/cross-layer.md)

## Open questions

See [Proposed / deferred decisions](../proposed.md) for design questions that have been acknowledged but not yet scheduled.

## Related design documents

- [About ADRs](../about.md) — what an ADR is, the format we use, how to propose one.
- [Superseded decisions](../superseded.md) — ADRs that have been replaced.
- `docs/DESIGN_SERVER_AUTH.md` — full 17-section server design.
- `dev/handoffs/<layer>.md` — public API contracts for each layer.
