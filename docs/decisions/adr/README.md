---
title: Architectural Decision Records — MindsOS
teaser: The numbered log of load-bearing decisions across all layers.
---

# Architectural Decision Records — MindsOS

This directory is the single source of truth for all load-bearing architectural decisions in MindsOS. Every ADR is numbered globally and covers decisions across all layers: the Server Layer (ADR-0001–0013), Layer 1 Core (ADR-0014–0037), Layer 2 Knowledge (ADR-0038–0059), Layer 3 Capacity (ADR-0060–0083), L3 design questions (ADR-0084–0100), Layer 4 Intelligence (ADR-0101–0112), the Server Layer pivot and L1 redesign (ADR-0114–0144), Layer 2 Knowledge v2 (ADR-0145–0161), L4/L5 substrate (ADR-0162–0190), perception and interpretation (ADR-0191–0200), the abstraction-level model (ADR-0201–0206), origin records + member refusal (ADR-0207–0209), and LLM communication (ADR-0210).

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
| [0007](0007-metagraph-snapshot-rollback.md) | In-memory MetagraphSnapshot for promotion rollback | Superseded | Server | — |
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
| [0037](0037-instancing-vocabulary-in-core.md) | Instancing vocabulary in core | Superseded by [ADR-0132](0132-instancing-moved-to-mindsos-instances.md) | L1 | core-ADR-024 |
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
| [0049](0049-similarity-report-before-promotion.md) | Similarity report before promotion | Superseded by [ADR-0115](0115-release-ship-audit-gate.md) | L2 | kl-ADR-012 |
| [0050](0050-server-owns-promotion-orchestration.md) | Server owns promotion orchestration | Accepted | L2 | kl-ADR-013 |
| [0051](0051-promoted-ref-type-marks-surviving-draft.md) | Promoted ref type marks surviving draft | Accepted | L2 | kl-ADR-014 |
| [0052](0052-report-id-deterministic-content-hash.md) | Report ID deterministic content hash | Accepted | L2 | kl-ADR-015 |
| [0053](0053-promote-per-candidate-atomic-rollback.md) | Promote per-candidate atomic rollback | Superseded by [ADR-0118](0118-per-user-transactional-promotion.md) | L2 | kl-ADR-016 |
| [0054](0054-promotion-validation-error.md) | Promotion validation error | Accepted | L2 | kl-ADR-017 |
| [0055](0055-baseline-similarity-heuristic-crude.md) | Baseline similarity heuristic crude | Accepted | L2 | kl-ADR-018 |
| [0056](0056-promotion-result-preserves-input-order.md) | Promotion result preserves input order | Superseded by [ADR-0114](0114-release-manifest-and-version-db-schema.md) | L2 | kl-ADR-019 |
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
| [0069](0069-type-compat-auto-discovery.md) | TYPE_COMPAT edges are auto-discovered and stamped | Superseded by [ADR-0156](0156-l3-bipartite-topology-reframe.md) | L3 | capacity-ADR-010 |
| [0070](0070-five-constraint-kinds.md) | Five admin-authored CONSTRAINT kinds; intra-category in slice | Accepted | L3 | capacity-ADR-011 |
| [0071](0071-pipeline-finder-bfs.md) | Pipeline-finder is BFS over TYPE_COMPAT; ignores constraints | Accepted | L3 | capacity-ADR-012 |
| [0072](0072-invoke-never-raises.md) | invoke() never raises for implementation errors | Accepted | L3 | capacity-ADR-013 |
| [0073](0073-residents-descriptive.md) | Residents are descriptive; L3 contains no event loop | Superseded by [ADR-0155](0155-monitor-lifecycle-relocated-from-l3-to-l4.md) | L3 | capacity-ADR-014 |
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
| [0086](0086-auto-discovery-with-admin-override.md) | Auto-discovery of type-compat edges with admin override | Superseded by [ADR-0156](0156-l3-bipartite-topology-reframe.md) | L3 | L3-Q3 |
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
| [0114](0114-release-manifest-and-version-db-schema.md) | Release manifest + version DB schema (v1 narrow — pending_mutations + releases only) | Accepted | L0 | — |
| [0115](0115-release-ship-audit-gate.md) | Release-ship audit gate + impact report (v1 narrow — ReleaseSummary + SimilarityWarning only) | Accepted | L0 | — |
| [0118](0118-per-user-transactional-promotion.md) | Per-user transactional promotion + release-boundary atomicity | Accepted | Server | — |
| [0120](0120-cross-layer-rewrite-handler-contract.md) | Cross-layer rewrite handler contract (v1 contract only; impl deferred) | Deferred | L0 / cross-layer | — |
| [0121](0121-substrate-falkordb-for-graphs-sqlite-for-non-graph.md) | Substrate — FalkorDB for graphs, SQLite for non-graph state | Accepted | L1 | L1-redesign-M1 |
| [0122](0122-wal-graph-for-multi-statement-write-safety.md) | WAL graph for multi-statement write safety | Accepted | L1 | L1-redesign-W1 |
| [0123](0123-indexes-and-verify-integrity.md) | Indexes + persist-time check + per-layer verify_integrity | Accepted | L1 | L1-redesign-W2 |
| [0124](0124-streaming-loader-iter-load-and-refresh.md) | Streaming loader: iter_load and MetagraphLoader.refresh | Accepted | L1 | L1-redesign-W3 |
| [0125](0125-lazy-local-hydration-with-lru-eviction.md) | Lazy Local hydration with LRU eviction | Deferred | Server | L1-redesign-W4 |
| [0126](0126-async-client-via-thread-pool-wrapper.md) | AsyncClient Protocol via asyncio.to_thread | Accepted | L1 | L1-redesign-W5 |
| [0127](0127-optimistic-concurrency-on-global-writes.md) | Optimistic concurrency on Global writes (`_version` property) | Accepted | L1 | L1-redesign-W6 |
| [0128](0128-hybrid-xref-cross-metagraph-refs.md) | Hybrid cross-graph refs — XRef primitive + ref-string convention | Accepted | L1 | L1-redesign-M2 |
| [0129](0129-metagraph-snapshot-narrowed-to-release-ship.md) | MetagraphSnapshot scope narrowed to release-ship | Accepted | L1 | L1-redesign-M4 |
| [0130](0130-property-bag-on-metagraph-graph.md) | Property bag on Metagraph and Graph | Accepted | L1 | L1-redesign-M5 |
| [0131](0131-pluggable-id-strategy.md) | Pluggable IdStrategy on Metagraph | Accepted | L1 | L1-redesign-M6 |
| [0132](0132-instancing-moved-to-mindsos-instances.md) | Instancing vocabulary moved to mindsos_instances package | Accepted | L1 | L1-redesign-M7 |
| [0133](0133-soft-delete-via-deprecated-disputed-properties.md) | Soft-delete via deprecated_at / disputed_at properties | Accepted | L1 | L1-redesign-M9-N1 |
| [0134](0134-schema-migration-scanner.md) | Schema migration scanner + loader warning | Accepted | L1 | L1-redesign-M11 |
| [0135](0135-removal-impact-on-remove-graph.md) | RemovalImpact report on remove_graph | Accepted | L1 | L1-redesign-M10 |
| [0136](0136-server-as-orthogonal-layer.md) | Server is orthogonal to the domain stack, not Layer 0 | Accepted | Cross-layer | L1-redesign-H2 |
| [0137](0137-user-facing-request-promotion.md) | User-facing request_promotion API | Deferred | Server | L1-redesign-N6 |
| [0138](0138-kl-drops-write-api.md) | KL drops its write API; writes relocate to L3 capacities | Accepted | L2 | — |
| [0139](0139-hybrid-invariant-home.md) | Hybrid invariant home — L1 structural, KL semantic | Accepted | L2 | — |
| [0140](0140-server-owns-admin-operations.md) | Server owns bootstrap and admin operations | Accepted | L0 | — |
| [0141](0141-delete-shipped-promote.md) | Delete shipped KL.promote(); ADR-0118 path is canonical | Accepted | L2 | — |
| [0142](0142-xref-cutover-for-ref-global.md) | XRef cutover for ref:global_<role> user data | Accepted | L2 | — |
| [0143](0143-kl-write-handle-pattern.md) | KLWriteHandle pattern for L3 write capacities | Accepted | L2 | — |
| [0144](0144-similarity-at-release-ship-audit-gate.md) | Similarity heuristic at release-ship audit gate; restore spec | Accepted | L0 | — |
| [0145](0145-l3-per-target-write-capacity-categories.md) | L3 per-target write capacity categories | Accepted | L3 | — |
| [0146](0146-l3-symmetric-write-invocation-contract.md) | L3 symmetric write invocation contract | Accepted | L3 | — |
| [0147](0147-l3-per-flow-write-capacity-build-pattern.md) | Per-flow build pattern for L3 write capacities | Accepted | L3 | — |
| [0148](0148-nary-intergraph-primitive.md) | N-ary IntergraphEdge / IntergraphHyperEdge primitive | Accepted | L1 | — |
| [0149](0149-l2-role-schemas-strict-false-and-tightening-rule.md) | L2 role-graph schemas ship at strict=False with a 2-week tightening rule | Accepted | L2 | — |
| [0150](0150-l2-knowledge-lifecycle.md) | L2 role-set closure (Flavor B rejection) | Accepted | L2 | — |
| [0151](0151-l2-storage-tiers.md) | L2 storage tiers — inline, Falkor large-property, blob_ref | Accepted | L2 | — |
| [0152](0152-l2-role-graph-schema-v2.md) | L2 role-graph schema v2 — promoted-pipelines, task-patterns, new role-graphs, episodic_memories | Accepted | L2 | — |
| [0153](0153-l2-mutation-discipline.md) | Per-role-graph mutation discipline + per-field content/metadata partition | Accepted | L2 | — |
| [0154](0154-alignment-naming-canonical.md) | Alignment role-graph canonical form is alignment:<a>:<b> | Accepted | L2 | — |
| [0155](0155-monitor-lifecycle-relocated-from-l3-to-l4.md) | Monitor lifecycle relocated from L3 to L4 substrate | Accepted | L3 | reframe-D36, L3-2 |
| [0156](0156-l3-bipartite-topology-reframe.md) | L3 capacity-to-DataState topology reframed as explicit bipartite | Accepted | L3 | reframe-D38, L3-1, phase-27-reframe |
| [0157](0157-family-specific-dontknow-contracts.md) | L3 capacity dont-know contracts are family-specific, not universal | Accepted | L3 | reframe-D46, L3-22, L3-35 |
| [0158](0158-datastate-naming-convention-and-realms.md) | DataState naming convention with realm sub-namespace | Accepted | L3 | reframe-D48, L3-24, datastate-taxonomy |
| [0159](0159-capacity-registration-contract-v2.md) | Capacity registration contract v2 — concurrent / inline / action contracts / reads_mm / typed CapacityContext | Accepted | L3 | L3-3, L3-34, L3-47, registration-contract-v2 |
| [0160](0160-l0-persister-impls.md) | L0 FalkorDBLocalPersister (native); SQLite + MetagraphDump deferred | Accepted | L0 | — |
| [0161](0161-kl-version-read-and-retire.md) | KL version-pinned read + retire-version lazy-inline hook | Accepted | L2 | — |
| [0162](0162-l3-dream-family.md) | L3 dream family — 3 v1 dream capacities + execution-policy contracts | Accepted | L3 | — |
| [0163](0163-l4-priority-tier-executor.md) | L4 priority-tier Executor + attention_score | Accepted | L4 | — |
| [0164](0164-mm-rwlock-granularity.md) | MM RWLock — per-active-MM, root granularity, writer-preferred | Accepted | L4 | — |
| [0165](0165-three-sub-mm-composition.md) | Three-sub-MM composition + thin root + no-shadow-state invariant | Accepted | L4 | — |
| [0166](0166-mm-resolution-and-instantiation.md) | MM resolution + instantiation layer | Accepted | L4 | — |
| [0167](0167-cooperative-cancellation-contract.md) | Cooperative cancellation framework | Accepted | L4 | — |
| [0168](0168-monitor-subscription-registry.md) | MonitorSubscriptionRegistry — L4-side Monitor lifecycle | Accepted | L4 | — |
| [0169](0169-tier-enum-home-and-signal-triage.md) | TierEnum home (L3) + signal-triage worker thread placement | Accepted | L3+L4 | — |
| [0170](0170-write-body-session-gating-boundary.md) | Write-body capability gating — boundary resolution (ADR-0146 / ADR-0159) | Accepted | L4 | — |
| [0171](0171-six-phase-task-lifecycle.md) | Six-phase task lifecycle — orchestrator, worker-per-task, simplified mode | Accepted | L4 | — |
| [0172-am1](0172-amendment-1-step5-execution.md) | Phase 3-5 execution wiring (out-of-CR Step 5) | Accepted | L4 | — |
| [0172](0172-phase-1-five-step-task-interpretation.md) | Phase-1 five-step task interpretation + Method δ + v0 catalog discipline | Accepted | L4 | — |
| [0173](0173-replan-check-dispatch-and-invalidation.md) | Replan-check dispatch + invalidate-at-and-below + ReplanRecord sparsity | Accepted | L4 | — |
| [0174](0174-sufficient-predicate-and-phase6-blame-dispatch.md) | Sufficient-predicate evaluator + Phase-6 BlameVerdict dispatch | Accepted | L4 | — |
| [0175](0175-invoke-capacity-context-flip-and-write-gate.md) | invoke→CapacityContext flip + write-body capability gate enforcement | Accepted | L4 | — |
| [0176](0176-mm-consolidation-write-path.md) | MM consolidation write path — L4 freeze+assemble, L3 Episode write, Memory materialize | Accepted | L5 | — |
| [0177](0177-d-prime-1-retention-lazy-inline-on-retire.md) | D'1 retention model — version-pinned refs + lazy inline-on-retire (full KL stack) | Accepted | L5 | — |
| [0178](0178-dream-live-re-execution-driver.md) | Dream live re-execution driver — timer hookup, episode task_input re-run, ALS provenance | Accepted | L4 | — |
| [0179](0179-crash-recovery-checkpoint-and-startup-scan.md) | Crash recovery — D-B50 checkpoint trigger set + tombstone marker + startup scan | Accepted | L4 | — |
| [0180](0180-write-capability-on-context-scope-aware-gate.md) | Write-half close — pre-authorized writeable capability on CapacityContext + scope-aware call-time gate | Accepted | L4 | — |
| [0181](0181-falkor-index-strategy-cross-sub-mm-queries.md) | Falkor index strategy for cross-sub-MM hyperedge queries | Accepted | L0 | — |
| [0182](0182-node-value-serialization-contract.md) | Node-value serialization contract for structured values | Accepted | L0 | — |
| [0183](0183-skill-bundle-install-lifecycle.md) | Skill-bundle and install-lifecycle contract | Accepted | server | — |
| [0184](0184-composite-capacity-promotion-seam.md) | Composite-capacity promotion — two-half target-applier seam (design-only) | Deferred | Cross-layer | CC-3 |
| [0185](0185-capacity-reactivation-contract.md) | Capacity re-activation contract (descriptor-of-record + factory registry) | Accepted | L3 | F9-A |
| [0186](0186-durable-local-persistence-lifecycle.md) | Durable Local-persistence lifecycle (FalkorDBLocalPersister + load_or_mint_local) | Accepted | Server | F9-B |
| [0187](0187-reset-run-state-boundary.md) | Reset boundary — role-scoped reset_run_state vs hard delete | Accepted | Server | F9-C |
| [0188](0188-submind-construct-and-two-output-model.md) | SubMind (Mindlet) construct + Signal/Reflex two-output model | Accepted | L4 | submind, mindlet |
| [0189](0189-submind-priority-and-arbitration.md) | SubMind priority model + L4 arbitration (severity/tier/score, resource-contention preempt-vs-reconcile, unsatisfiable-need policy) | Accepted | L4 | — |
| [0190](0190-submind-endowment-and-role-graph.md) | SubMind endowment lifecycle + subminds L2 role-graph | Accepted | L2 | — |
| [0191](0191-two-axis-perception-confidence.md) | Two-axis perception confidence (grounding + decision) + per-capacity calibration | Proposed | L3/L4 | — |
| [0192](0192-perception-atom-layer.md) | Perception atom layer — geometry/signal realms + the introduce-atom primitive | Proposed | L3 | — |
| [0193](0193-grounding-control-loop.md) | Grounding control loop — irreducibility/request-atom signal + top-down descent trigger | Proposed | L3/L4 | — |
| [0194](0194-recursive-recognizers-and-reuse-promotion.md) | Recursive scale-relative recognizers + reuse-driven promotion | Proposed | L3/L2 | — |
| [0195](0195-phase1-interpretation-seam.md) | Phase-1 interpretation seam — pluggable Phase1Profile | Accepted | L4 | Feature-A, phase1-seam |
| [0196](0196-needs-input-clarification.md) | needs_input verdict — non-terminal user-clarification | Accepted | L4 | Feature-B, needs_input, clarification |
| [0197](0197-modality-aware-input-ingress.md) | Modality-aware input ingress for the Phase-1 interpretation seam | Accepted | L4 | intelligence-ADR-modality-ingress |
| [0198](0198-same-type-operand-arity.md) | Same-type operand arity on the capacity registration + invoke input contract (Form B) | Accepted | L3 | Part-5, 5a, C1, operand-arity |
| [0199](0199-group-member-datastate-attribute.md) | Group / member DataState registration attribute (typed L3→L4 iteration seam) | Accepted | L3 | C4, group-member, datastate-group |
| [0200](0200-reads-mm-gates-body-read-handle.md) | reads_mm gates the body-facing MM read handle (truthful invoke read contract) | Accepted | L3 | C3, truthful-read-contract, reads-mm-enforcement |
| [0201-am1](0201-amendment-1-slice2.md) | Slice 2 capacity writer (built) | Accepted | L5 | — |
| [0201-am2](0201-amendment-2-slice-a.md) | per-run capacity graph + no run_ref default (Slice A) | Accepted | L5 | — |
| [0201-am3](0201-amendment-3-slice-3.md) | knowledge-MM writer + DQ-1 provenance XRef (Slice 3) | Accepted | L5 | — |
| [0201-am4](0201-amendment-4-run-manifest.md) | the run manifest, and where it is minted | Accepted | L5 | — |
| [0201-am5](0201-amendment-5-fold-manifest-correlation.md) | the fold manifest carries the member correlation; the empty domain is a stop | Accepted | L5 | member_graph_ids, empty_domain, Decision Records |
| [0201-am6](0201-amendment-6-partial-results.md) | partial results — a member stops in place; a truncated domain is a stop | Accepted | L5 | partial_domain, stopped, conceded, Decision Records |
| [0201-am7](0201-amendment-7-declared-retry.md) | bounded member retry becomes a declared capacity property; the fatal set is never retried | Accepted | L5 | retryable, MEMBER_RETRY_CAP, LLM seam |
| [0201](0201-capacity-mm-instance-vocabulary.md) | ADR-0201 — capacity-MM instance vocabulary + minting (DQ-2) | Accepted | L5 | — |
| [0202](0202-per-task-chain-graphs-persist.md) | ADR-0202 — per-task chain graphs, persisted at consolidation (DQ-8) | Proposed | L5 | — |
| [0203](0203-learned-pipelines-local-persistence.md) | ADR-0203 — Learned pipelines get a first-class Local persistence surface | Accepted | L2 | — |
| [0204](0204-reduction-capability-family.md) | Reduction capability family (L4-support) — argmin / argmax / top_k / bottom_k / majority_vote | Accepted | L4-support | reduction-family, argmax, top_k, bottom_k, majority-vote, CR-reduction |
| [0205](0205-abstraction-levels.md) | Abstraction levels — one graph at several resolutions | Accepted | L3 | — |
| [0206](0206-planning-decomposition-confidence.md) | Planning as a loop — milestones, decomposition, and confidence | Proposed | L4 | — |
| [0207](0207-origin-records.md) | Origin records — where a value came from, for any producer | Proposed | L3 | origin, origin_v0, provenance-record, Decision Records |
| [0208](0208-policy-lookup-and-criterion.md) | Reading a stored authority as of a date — the policy lookup and the criterion it feeds | Proposed | L3 | policy lookup, as-of, policies role, Decision Records |
| [0209](0209-member-level-in-band-refusal.md) | Member-level in-band refusal (shape (a)) — the type declares, the reducer decodes, plan construction enforces | Accepted | L3 | refusal_capable, decodes_refusals, shape (a), Decision Records |
| [0210](0210-llm-communication-layering.md) | LLM communication as a cross-layer core capability — L0 holds the credential, `mindsos_llm` holds the wire, L3 mints one capacity per reading | Accepted | cross-layer | mindsos_llm, adapters, credential levels, vendor registry, replay |

!!! note "ADRs 0058, 0059, 0113, 0116, 0117, 0119 — numbers not in use"
    ADR-0117 (compositional metaedge) was **Withdrawn** in Phase 05a; the concept became the `compositional` flag on `IntergraphEdge` / `IntergraphHyperEdge` (see `confirmation_docs/INTERGRAPH_EDGES_DESIGN.md`, the canonical source for both primitives). The Server Layer pivot shipped 0114, 0115, 0118 and 0120. The remaining numbers (0058, 0059, 0113, 0116, 0119) were reserved and never drafted; they are not re-used.

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
