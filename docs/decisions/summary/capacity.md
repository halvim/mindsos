---
title: L3 Capacity decisions
tag: shipped
teaser: All architectural decisions affecting the Intellectual Capacity Layer (fixed abilities).
next: decisions/summary/intelligence.md
---

# L3 Capacity decisions

Layer 3 is the repertoire of *fixed*, deterministic abilities the system has. It is a dual metagraph (Global + per-user Local) of capacity graphs grouped by functional category (perception, comprehension, derivation, retrieval, scoring, etc.). These decisions lock in the distinction between fixed and learned, the discovery machinery, the resident/reactive split, and the Server Layer seam.

## Accepted decisions

| ADR # | Title | Summary |
|-------|-------|---------|
| [0060](../adr/0060-l3-fixed-not-learned.md) | L3 holds only fixed functions; learned state lives in L4 | Pure functions plus immutable context; no updates after registration |
| [0061](../adr/0061-dual-metagraph-global-local.md) | Dual metagraph (Global + per-user Local) mirrors KL | Local capacities may carry `ref:global_capacity`; on collision, Local wins |
| [0062](../adr/0062-three-node-types-capacity-monitor-adapter.md) | Three node types: Capacity, Monitor, Adapter | One registration path; three invocation verbs (`invoke`, `start_resident`, adapter-insertion) |
| [0063](../adr/0063-datastates-purely-structural.md) | DataStates carry only a structural ShapeDescriptor | Deterministic auto-discovery via structural matching; semantic depth implicit in operators |
| [0064](../adr/0064-one-shared-datastates-graph.md) | One shared `capacity:datastates` graph per metagraph | Avoids duplication; TYPE_COMPAT edges are intra-graph or cross-graph MetaEdges |
| [0065](../adr/0065-twelve-functional-categories.md) | Twelve functional categories as the node-graph partition | Readable partition keeps discovery fast; extension is one file edit |
| [0066](../adr/0066-capacity-iri-form.md) | IRI form: `capacity:<category>:<name>` and `datastate:<name>` | Stable, human-readable, parseable; set at declaration time, never rewritten |
| [0067](../adr/0067-ref-types-shared-with-kl.md) | `REF_TYPES` vocabulary is shared verbatim with KL | One mental model across layers; extension is high-friction (intentional) |
| [0068](../adr/0068-constraint-kind-property-key.md) | `constraint_kind` is the property key, not `kind` | Avoids collision with Core's reserved `kind` key |
| [0069](../adr/0069-type-compat-auto-discovery.md) | TYPE_COMPAT edges are auto-discovered and stamped | **Superseded by ADR-0156** (Phase 42): replaced by explicit bipartite `PRODUCES`/`CONSUMES` IntergraphEdges emitted at `register_capacity` time |
| [0070](../adr/0070-five-constraint-kinds.md) | Five admin-authored CONSTRAINT kinds; intra-category in the slice | `MUTUALLY_EXCLUSIVE`, `MANDATORY_BEFORE`, `RATE_LIMIT`, `REQUIRES_APPROVAL`, `REQUIRES_L2_VERSION` |
| [0071](../adr/0071-pipeline-finder-bfs.md) | Pipeline-finder is BFS over TYPE_COMPAT; ignores constraints | Deterministic default; L4 applies constraints post-hoc (policy belongs above) |
| [0072](../adr/0072-invoke-never-raises.md) | `invoke()` never raises for implementation errors | Returns `InvocationResult(failed=True, exception=...)`; raises only for invariant bugs |
| [0073](../adr/0073-residents-descriptive.md) | Residents are descriptive; L3 contains no event loop | **Superseded by [0155](../adr/0155-monitor-lifecycle-relocated-from-l3-to-l4.md) (Phase 41).** Was: `start_resident` builds a `ResidentSubscription`; L4 dispatches. Monitor lifecycle now relocated to L4 substrate; L3 ships `Monitor` + `cl.iter_monitors()`. |
| [0074](../adr/0074-problem-trace-anomaly-only.md) | Problem-trace is in-memory, anomaly-only, drained by L4 | Bounded memory; signal-dense; L4 chooses cadence of persistence |
| [0075](../adr/0075-in-memory-first-facade.md) | In-memory-first facade, Core-adapter agnostic persistence | Tests run without FalkorDB; server layers on persistence via Core adapters |
| [0076](../adr/0076-local-graph-naming.md) | One FalkorDB graph per Local metagraph: `mindsos_capacity_local_<slug>` | Hard per-user isolation at storage layer; slug mapping is lossy (user_id preserved) |
| [0077](../adr/0077-l3-session-write-api.md) | Write API takes `session: SessionProtocol` | Aligns with L2; provenance flows for free; `CAN_WRITE_GLOBAL` gate has a home |
| [0078](../adr/0078-l3-capability-local-copy.md) | Local copy of `CAN_WRITE_GLOBAL` + parity test | Layer isolation preserved; drift caught at test time |
| [0079](../adr/0079-l3-session-compat-shim.md) | Backward-compat shim with `DeprecationWarning` during migration | Legacy `user_id:` accepted and wrapped in `_LocalTestSession`; warnings emitted |
| [0080](../adr/0080-l3-bootstrap-carveout.md) | Bootstrap carve-out: `session=None` Global writes still allowed | Chicken-and-egg for bootstrap; tighten once production flows are session-bearing |
| [0081](../adr/0081-l3-session-context-threading.md) | `invoke`/`start_resident` thread `session_user_id` into `context` | Capacity impls get consistent provenance source without parsing sessions |
| [0084](../adr/0084-l3-capacities-fixed-not-learned.md) | Functional-category as primary axis for graphs | Fast, readable partition aligns with L4's task decomposition strategy |
| [0085](../adr/0085-multi-graph-membership.md) | Capacities can belong to multiple graphs; one home, additional memberships | Flexible organisation; one registration path, multiple membership options |
| [0086](../adr/0086-auto-discovery-with-admin-override.md) | Auto-discovery of type-compat edges with admin manual override | **Superseded by ADR-0156** (Phase 42): `add_type_compat` + bulk rediscover retired with the TYPE_COMPAT substrate |
| [0087](../adr/0087-richness-annotation-implicit.md) | Richness annotation in DataState type system is implicit | Auto-discovery stays deterministic; semantic depth encoded in operator choice |
| [0088](../adr/0088-fine-grained-residents.md) | Resident capacity granularity is fine-grained, matching reactive capacities | Residents compose naturally; L4 retains full control over signal handling |
| [0089](../adr/0089-three-tier-memory.md) | Session persistence for residents via three-tier memory model | L4 process memory / L5 working memory / L2 long-term; triage is an L4 intelligence |
| [0090](../adr/0090-teaching-growth-model.md) | Teaching - humans add capacities; system grows via promotion and membership | Atomic capacity addition is deliberate; effective repertoire grows via paths and learning |
| [0091](../adr/0091-dreaming-bootstraps-l4.md) | Bootstrapping L4's pipeline-finder via dreaming | System dreams during idle cycles; maintenance, exploration, retry as normal tasks |
| [0092](../adr/0092-constraint-edges-admin-proposed.md) | Constraint edges are admin-authored; L4 may propose | Admin approval gates learning signals; keeps constraint graph inspectable |
| [0093](../adr/0093-datastate-synthesis-humans-only.md) | DataState synthesis - humans only for DataState creation | System grows effective repertoire via promoted paths, not new DataStates |
| [0094](../adr/0094-confidence-pipeline-level.md) | Confidence storage - pipeline-level on promoted-pipelines records | Per-pipeline, per-task-type; no per-capacity scores; L3 nodes stay fixed |
| [0095](../adr/0095-trace-scope-mm-plus-thin.md) | Trace system scope - Mental Model as success trace, thin problem-trace | MM captures successful execution; problem-trace covers only anomalies |
| [0096](../adr/0096-failure-recording-in-mm.md) | Failure recording inside an MM via ref:problem_trace pointer | MM records failed step as normal NodeInstance; problem-trace reference holds diagnostics |
| [0097](../adr/0097-retrieval-category-memories.md) | Retrieval of memories via new capacity:retrieval category | Fixed search capacities over `memories`; L4 picks among them with learned confidence |
| [0098](../adr/0098-mental-model-retention-default.md) | Mental Model retention - retained by default into memories | Default maximizes learnability; opt-out available for privacy/storage concerns |
| [0099](../adr/0099-resident-state-persistence-dynamic.md) | Resident state persistence policy - activity-based dynamic snapshots | Snapshot cadence proportional to state-delta rate; per-resident overrides available |
| [0100](../adr/0100-resident-watches-first-input.md) | Resident granularity - watches input DataState of first pipeline node | Residents compose naturally with reactive pipelines at same scale |

## Proposed decisions

| ADR # | Title | Summary |
|-------|-------|---------|
| [0082](../adr/0082-pipeline-generation-capacity.md) | Pipeline generation is itself a category of capacity in L3 | Procedures that assemble pipelines are fixed functions; should live in L3 |
| [0083](../adr/0083-pipeline-promotion-transitive.md) | Promoting a pipeline transitively requires promoting its Local-capacity dependencies | Admin tool walks capability IRIs; refuses promotion until all Local deps are promoted |

## L3 write side (2026-04-27)

The 2026-04-27 L2 redesign relocates KL's write API into L3 as named capacities. These three ADRs lock the L3 write-side contract; the actual capacities are built per-flow (per ADR-0147) as L4 design closes each flow.

| ADR # | Title | Status | Summary |
|-------|-------|--------|---------|
| [0145](../adr/0145-l3-per-target-write-capacity-categories.md) | L3 per-target write capacity categories | Proposed | Five new categories: `capacity:consolidate`, `capacity:trace` (write side), `capacity:promote`, `capacity:author`, `capacity:state`. No umbrella `capacity:write` |
| [0146](../adr/0146-l3-symmetric-write-invocation-contract.md) | L3 symmetric write invocation contract | Proposed | `WriteResult \| ProblemTraceRecord` return; capability check at entry + handle methods; L1 errors caught and wrapped; programmer errors propagate |
| [0147](../adr/0147-l3-per-flow-write-capacity-build-pattern.md) | Per-flow build pattern for L3 write capacities | Proposed | Each capacity built when its L4 flow closes design; KL `DeprecationWarning`s stay until relocation lands per-flow |

See `docs/HANDOFF_L3_WRITE_DESIGN_2026-04-27.md` for the full L3 write-side handoff and the 6 minimum capacities for L4 v1.

---

**Next:** [L4 Intelligence decisions](intelligence.md) — orchestration, learning, and confidence (design-phase).
