# MindsOS — Layer Content and Responsibilities

**Purpose.** One-glance reference for what lives in each layer of MindsOS and what each layer is responsible for. Read this before any cross-layer discussion. Flag anything you disagree with and we'll correct it.

**Scope.** Six layers: L0 (Server), L1 (Core), L2 (Knowledge), L3 (Intellectual Capacity), L4 (Intelligence), L5 (Mental Model). L0 is sometimes excluded from the "five layers of intelligence" framing; it is included here because it governs writes across L1–L4.

**Sources.** `mindsos_server_handoff.md`, `mindsos_core_handoff.md`, `mindsos_knowledge_handoff.md`, `mindsos_capacity_handoff.md` + ADRs 001–024, `layer4_intelligence_design_notes.md`, `layer5_mental_model_design_notes.md`, this project's own `fol_capacity_handoff.md` + review + design plan.

---

## L0 — Server Architecture

**Alias.** The "server layer" / "auth layer".

**Content.**
- Session registry (active sessions, their user IDs, their granted capabilities).
- Capability vocabulary (e.g., `CAN_WRITE_GLOBAL`, `CAN_WRITE_CANONICAL` — the latter currently a proposed ADR).
- Password / token schemes (ADRs 003, 005).
- Capability enforcement middleware for writes into any higher layer.

**Responsibility.**
- Authentication (who is the user) and authorisation (what capabilities they have).
- Gating every write that targets L2 or L3's Global metagraph behind a capability check.
- Providing a stable `SessionProtocol` that the write APIs of L1/L2/L3 consume (ADR-018).
- Bootstrap carve-out: allowing `session=None` writes during first-boot admin setup (ADR-021).

**Does NOT own.**
- Any domain data, any knowledge content, any reasoning state.
- Task execution, pipeline selection, inference, or learning.

**Who writes.** Only L0 itself (session creation, capability grants). Higher layers never modify L0 state directly.

**Key invariants.**
- Every write method on any higher layer accepts `session: SessionProtocol` (ADR-018) or is a bootstrap carve-out.
- Capability grants are stamped at session creation and do not change mid-session.
- L0 knows nothing about what the capabilities gate — it only checks presence.

---

## L1 — Core

**Alias.** The "core elements" layer / "graph substrate".

**Content.**
- The `Graph` primitive: nodes, edges, hyperedges.
- The `Metagraph` primitive: graphs-as-nodes, meta-edges, meta-hyperedges — a graph whose elements are themselves graphs.
- Persistence adapters: in-memory (default, testable), FalkorDB (one graph per Local metagraph per ADR-017), Core-adapter split via `LocalPersisterProtocol` (ADR-011).
- Snapshot / rollback primitives (ADR-007).
- Versioning of role-graphs: `register_version_graph`, `activate_version` — versions coexist; activation flips the live pointer.

**Responsibility.**
- Providing a stable, layer-agnostic graph abstraction for every higher layer to build on.
- Persistence: round-tripping metagraphs to disk / FalkorDB and back.
- Structural integrity: edges reference real nodes, hyperedges are well-formed, ref types are consistent.
- Version management: side-by-side versions of a role-graph with a single-active-version pointer.

**Does NOT own.**
- Any semantic meaning attached to nodes (that's L2's job).
- Any notion of "knowledge" or "rule" — L1 just has nodes-and-edges.
- Inference, task state, session awareness.

**Who writes.** L2 writes L1 via L2's importer APIs; L3's datastate/capacity registry writes L1 via L3's registration APIs; L0 never writes L1 directly.

**Key invariants.**
- Graphs are pure data structures; operations on them are pure functions.
- Snapshots are immutable; rollback restores a snapshot verbatim.
- Ref-type vocabulary is shared across layers (`SPECIALISES`, `INSTANCE_OF`, `RENAMES`, `EXTENDS`, `CONTRADICTS`, `PROXY` — ADR-008 / L3 I5).

---

## L2 — Knowledge

**Alias.** The "knowledge layer" (KL).

**Content.** A metagraph of role-graphs. Each role-graph is itself a graph serving a specific knowledge role. The current committed set:

| Role-graph | Content |
|---|---|
| `ontology` | DOLCE foundational ontology + domain extensions (legal, biomedical, etc.). Categories, relations, axiom templates. Every predicate carries `is_time_variant: bool`. |
| `lexicon` | WordNet-aligned sense inventory with DOLCE category mappings (OEWN importer). |
| `concepts` | Domain concepts (FrameNet importer + user-added). |
| `fol-rules` | Rules as first-class nodes. Pre-populated with equality axioms, DOLCE-derived sort-discipline rules, native DOLCE axioms translated into rule form, commonsense rules. Grows as the system ingests canonical/authoritative text. |
| `memories` | Frozen Mental Models from completed tasks (L5 consolidation target). |
| `problem-trace` | Anomaly-only records drained from L3 (ADR-015). |
| `promoted-pipelines` | Reusable pipeline sequences L4 has promoted from repeat success. |
| `task-patterns` | Recurring task shapes L4 has identified. |
| `capacity-state` | Any persistent-but-versioned state a capacity family's *parameters* need (e.g., learned scoring weights — never L3-state, L4-sourced). |
| `sense-correlations` | Co-occurrence statistics between lemma senses, learned from consolidated memories. |
| `wsd-model` | WSD sense-ranking model parameters (currently tentative). |
| `commonsense-causation` (proposed, per FOL Example 5) | Causal-pattern predicates and rules. |
| `commonsense-physics` (proposed, per FOL Example 6) | Motion, transport, containment rules. |
| `alignments` | Cross-graph mappings (e.g., WordNet ↔ DOLCE). |

**Responsibility.**
- Holding stable, versioned knowledge — ontologies, lexica, rules, concepts, promoted pipelines, consolidated memories, learned parameters.
- Importers (DolceImporter, OewnImporter, FrameNetImporter, AlignmentsImporter) that bring external sources into canonical role-graph form with provenance.
- Side-by-side versioning with active-version pointers (L1 primitive, L2 policy).
- Exposing `MetagraphView` for read-side access that respects the active version.
- Adjudicating Global (shared) vs. Local (per-user) knowledge.

**Does NOT own.**
- Any ephemeral / per-task state (L5's job).
- Inference, learning, or decision-making (L3/L4).
- The FOL ledger (it's per-task; lives in L5; only consolidated ledgers are retained in `memories`).

**Who writes.**
- Importers (at import time, session-gated).
- L3 write API for structural additions like new `TYPE_COMPAT` edges (ADR-010 — stamped `discovered_automatically=True`).
- L4 for: promoted pipelines, task patterns, memories consolidation, learned parameters into `capacity-state` / `wsd-model` / `sense-correlations`.
- Canonical-role ingestions reaching through L3's write-intent mechanism.

**Key invariants.**
- Role-graphs are versioned; multiple versions coexist; reads respect the active pointer.
- Importers produce provenance-stamped nodes with stable IRIs.
- Writing L2 requires a `SessionProtocol` and, for Global writes, `CAN_WRITE_GLOBAL` (ADR-019); writing authoritative-role content additionally requires `CAN_WRITE_CANONICAL` (proposed).

---

## L3 — Intellectual Capacity

**Alias.** The "capacity layer" / `mindsos_capacity` package / historical `falkormg_capacity`.

**Content.** A dual metagraph (one Global, one Local per user, ADR-002) of:
- **Capacity nodes** — pure functions registered by IRI `capacity:<category>:<name>` (ADR-007).
- **DataState nodes** — structural type descriptors (`ShapeDescriptor` with only `kind`, `elem`, `fields`, `opaque_tag` — I2).
- **Monitor nodes** — descriptive resident subscriptions (never start their own threads — ADR-014).
- **Adapter nodes** — integration handles to external systems.
- **CONSTRAINT edges** — admin-authored invariants, five kinds, intra-category only (ADR-011).
- **TYPE_COMPAT edges** — auto-discovered connectivity between DataStates (ADR-010).

**The twelve capacity categories** (ADR-006): PERCEPTION, COMPREHENSION, DERIVATION, DECOMPOSITION, COMBINATION, PATH_FINDING, RETRIEVAL, SCORING, TRACE, SIGNALLING, INTERACTION, LEARNING_METHODS. (The FOL family also uses a VALIDATION category at design-plan level — confirm whether VALIDATION is a thirteenth or folds into one of the twelve.)

**Responsibility.**
- Hosting the fixed repertoire of abilities the system can call — pure, stateless, deterministic functions.
- Exposing the `invoke()` API that runs a capacity with inputs + optional immutable `context` and returns an `InvocationResult` (ADR-013 — never raises for impl errors; anomalies become `ProblemTraceRecord`s).
- Registering capacity/DataState declarations with IRI collision checking (I3).
- Pipeline-finding as BFS over TYPE_COMPAT, ignoring constraints (ADR-012). Note: *pipeline generation* as a first-class L3 capacity is Proposed (ADR-023).
- Enforcing I1 (pure functions) and I2 (structural-only DataStates) at registration time.

**Does NOT own.**
- Any learned state (that's L4).
- Any per-task state (that's L5).
- Any orchestration / pipeline dispatch (that's L4 until ADR-023 lands).
- Any threaded event loops (ADR-014).
- Any task decomposition, budget enforcement, or persistence orchestration (scoped out).

**Who writes.** L3's own write API for capacity/datastate/monitor registration, under `SessionProtocol` gating (ADR-018). Global writes require `CAN_WRITE_GLOBAL` (ADR-019). L4 invokes capacities but does not mutate L3's registry at call time.

**Key invariants (I1–I13).**
- I1: every Capacity is a pure function of its declared inputs + an immutable `context`.
- I2: `ShapeDescriptor` carries only structural fields — no weights, no confidence, no semantic class.
- I3: IRIs are fixed at declaration; collisions raise.
- I4: Local capacities either carry both `ref_to_global` + `ref_type`, or neither.
- I9: `invoke()` never raises for impl errors; they become trace records.
- I11: trace sink is anomaly-only — no records for successful invocations.
- I13: L3 must not import from L0 (`mindsos_server`).

---

## L4 — Intelligence

**Alias.** The "intelligence layer".

**Content.**
- **Process memory** (ephemeral, dies with the process): current-task state, in-flight pipelines, active ledgers' handles.
- **Three-tier memory model**: L2 long-term + L4 process + L5 working. L4 owns the process tier and orchestrates the other two.
- Confidence values tracked per `promoted-pipelines` record (L4-level, not per-node).
- `context` population machinery: L4 builds the `context` dict handed into every `invoke()` call (currently session fields per ADR-022; broader schema is open concern D3).

**Responsibility.**
- **Pipeline selection and execution.** Given a task, pick a pipeline (from `promoted-pipelines` or by BFS over TYPE_COMPAT) and run it through `cl.invoke()` calls.
- **Learned choice among L3 strategies.** Every "parametric-over-strategy" L3 capacity family (priority rules, consistency backends, abduction strategies, ingestion combiners, tense schemes, etc.) has L4 picking which strategy to run.
- **Writing L5.** L4 is the *only* writer to the per-task Mental Model (L5 design §1.2). Neither L3 capacities nor users write L5 directly.
- **Consolidation.** On task completion: freeze the MM, write it into L2 `memories` as a versioned record.
- **Dreaming / self-improvement.** Background tasks that replay consolidated memories, invoke alternative L3 pipelines on them, observe outcomes, update confidence on `promoted-pipelines` and parameters on `capacity-state` / `wsd-model` / `sense-correlations`. This is where the **Coherence Loop** lives (see `fol_open_decisions_2026_04_23.md` §1).
- **Confidence tracking.** Per promoted pipeline, derived from observed success-rate on similar tasks.
- **Handling anomalies drained from L3's problem-trace** (ADR-015).

**Does NOT own.**
- Any fixed algorithms — those are L3 (I1).
- The graph substrate — that's L1.
- Stored knowledge — that's L2.
- User auth — that's L0.

**Who writes.**
- Writes L5 freely (only writer).
- Writes L2: promoted-pipelines, task-patterns, memories, capacity-state, sense-correlations, wsd-model, problem-trace reductions, role-graph version activations.
- Does not write L3 (the registry is structural and fixed at registration time).

**Key invariants.**
- L4 is the only writer to L5.
- Every strategy choice that depends on learned confidence lives in L4, not L3.
- L4's process memory is ephemeral — nothing persists across process restarts unless it was consolidated to L2.

---

## L5 — Mental Model

**Alias.** The "mental model layer" / "working memory" / per-task MM.

**Content.** One Mental Model metagraph per running task. Contents vary by task type; for a FOL-using task it holds:
- **Ledger** — observed + inferred + assumed + hypothesised + retracted statements, with tags, provenance, dependency graph. (See `fol_capacity_design_plan.md` §3 for the full DataState shape.)
- **Sense distributions** — per lemma, current candidate senses and priors.
- **Open gaps** — under-determined predicates the system hasn't filled yet.
- **Recent validation results** — which assumptions were promoted/retracted in the last pass.
- **Pending revisions** — candidate revision plans not yet applied.
- **Task metadata** — task type, goal, outcome classification, decision points.
- **References to L2 nodes** — via `ref:global_<role>` links.

**Responsibility.**
- Being the single source of truth for everything ephemeral about the current task.
- Preserving causal/temporal order of state changes within a task.
- Providing the frozen-MM payload that consolidation writes to `L2.memories`.

**Does NOT own.**
- Any cross-task state. (Two tasks have two separate L5 instances.)
- Any knowledge worth keeping long-term without consolidation.
- Any learned parameters — those promote to L2 only via dreaming.
- Retrieval of memories — that's an L3 retrieval-category capacity reading `L2.memories`.

**Who writes.** Only L4. (L5 §1.2 commitment.)

**Key invariants.**
- One MM per task; never shared across tasks at run time.
- MM is retained by default on task completion (consolidated into L2 `memories` as a versioned graph).
- Retrieval of past MMs is through L3 capacities reading `L2.memories`, not through L5 itself.
- Pause/resume: L5 state is persisted and rehydrated; on resume, validation passes re-run against current L2 to catch knowledge drift.

---

## Cross-layer flow — a request's path through the layers

For the operational-role query "can the landlord terminate?" walked in Example 3:

```
User → L0 (session / authorisation gate — operational role, no CAN_WRITE_CANONICAL needed)
     → L4 (decides: this is a FOL-query task; picks pipeline; builds context)
     → L3 (executes a sequence of capacity:trace:classify_ingestion_role.* →
            capacity:comprehension:compose_statement_from_parse →
            capacity:retrieval:lookup_rules_by_predicate →
            capacity:derivation:unify →
            capacity:derivation:instantiate_universal →
            capacity:combination:populate_negative_closure →
            capacity:derivation:entails.bounded …)
     → L2 (read-only consultation of ontology, lexicon, fol-rules)
     → L5 (L4 writes observed facts + abduced assumption to the task's ledger)
     → L1 (all graphs live here under the hood)
     → L0 again for any write the pipeline emits
     → verdict returned up the stack to the user
```

For the canonical-role ingestion of the law:

```
User → L0 (verifies the session holds CAN_WRITE_CANONICAL — proposed)
     → L4 (dispatches canonical-ingestion pipeline)
     → L3 (translation pipeline as above, ending in a DS_WRITE_INTENT targeting
           L2.fol-rules)
     → L4 (receives the write intent, checks required capability, executes)
     → L2 (new rule_L001 inserted; version activated)
     → L1 (persisted)
     → ack back to the user
```

---

## Verification checklist for you

Read each row. Disagreements flag as "DISAGREE: ..." next to the row and we'll revise.

- [ ] L0's job is purely auth/capability-gating; no domain knowledge lives there.
- [ ] L1 is graphs-as-data-structures; it doesn't know what a "rule" or a "concept" is.
- [ ] L2 holds every long-term role-graph, versioned, readable by every higher layer.
- [ ] `fol-rules` is a single role-graph inside L2, and it's pre-populated with foundational axioms before any domain content arrives.
- [ ] L3 holds pure, stateless functions. No learned state at this layer.
- [ ] L3's twelve categories are the current structural vocabulary (plus validation if we add it as thirteenth).
- [ ] L4 owns all learned behaviour: pipeline selection, confidence tracking, parameter updates, dreaming.
- [ ] L4 is the only writer to L5. (Neither users nor L3 write L5 directly.)
- [ ] L5 is per-task working memory, consolidated to L2 `memories` on completion.
- [ ] The Coherence Loop (discussed in the open-decisions doc) lives in L4, not L3 — because it maintains population state across training rounds.
- [ ] Ingestion-role classification has a *detection* step in L3 (pure) and a *combination policy* picked by L4.
- [ ] Writes to L2 that bring in authoritative content need `CAN_WRITE_CANONICAL` (proposed capability; must be filed before implementation).

---

*End of layer summary.*
