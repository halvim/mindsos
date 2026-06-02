# WSD Subsystem — Consolidated Architecture

**Date:** 2026-04-29
**Status:** Architectural specification. No code written.
**Supersedes:** `WSD_DESIGN_HANDOFF.md` (2026-04-26 pre-design notes).
**Companion documents:**
- `coordinated_change_L1_intergraph_and_layers.md` — L1 Core extensions required.
- `coordinated_change_L2_lexicon_layers_and_role_graphs.md` — L2 Knowledge schema work.
- `coordinated_change_L3_capacities_and_monitors.md` — L3 Capacity additions.
- `coordinated_change_L4_intelligence_and_als.md` — L4 Intelligence design.
- `coordinated_change_L0_user_settings.md` — L0 Server settings extension.

---

## 0. How to use this document

This is the canonical architecture spec for the WSD subsystem in MindsOS, produced from a multi-session design conversation (2026-04-29). It is the source of truth for the layer-specific coordinated-change documents listed above; if those documents and this one disagree, this document wins until updated.

Reading order for someone new:

1. §1 (goal) — what success looks like, what we explicitly do not aim for.
2. §2 (overview) — one-page architecture summary.
3. §3 (SCMS) — the core runtime mechanism.
4. §4 (ALS) — the learning subsystem.
5. §5 (lexicon empirical layer) — the data side.
6. §6 (task lifecycle) — how a task flows through the system.
7. §7 (v1 deliverables).
8. §8 (open questions).
9. §9 (reading order to layer-specific docs).

---

## 1. Goal — calibrated coverage, not 100% accuracy

The system aims to produce **calibrated multi-candidate sense distributions** for every content word in input text:

- For each content word: emit either (a) a confident sense pick or (b) a multi-candidate distribution that an oracle would agree is correctly ambiguous.
- "Calibrated" means: when the system reports `confidence=0.9`, it is right 90% of the time. When it reports a `[0.5, 0.4, 0.1]` distribution, the top two candidates contain the correct sense ~90% of the time.
- 100% single-sense accuracy is not the target. Human inter-annotator agreement on fine-grained WordNet senses is ~70–80%. Aiming higher than IAA pushes the system to overcommit on legitimately-ambiguous inputs, contradicting the architecture's multi-candidate mandate.

Calibration is the validation target throughout the system — for evaluation, for training loss, for audit gates.

### What the WSD subsystem is *not*

- Not a meaning-extractor — sense disambiguation is one stage of comprehension, not the whole.
- Not a task-pattern enumerator — task-patterns emerge from successful task completions and are admin-extensible; v1 ships with admin-authored sub-shape recognizers.
- Not a synthesis machine — the system does not invent new senses, new lemmas, or new capacities.

### Calibrated honesty as a system-wide principle

The same honesty principle that drives multi-candidate WSD output applies at the task level:

- **Sense level**: when correlations and FOL coherence don't decisively prefer one sense, multi-candidate output is preserved.
- **Task level**: when no path exists in the L3 capacity graph from task input to task goal, the system answers "I don't know how to do this" — recorded as a capacity gap for admin review, not fabricated.

---

## 2. Architecture overview

```
                           Task arrives
                                │
                                ▼
                    ┌─────────────────────────┐
                    │ Phase 1: interpret task │ (probabilistic — task-shape, task-goal)
                    └─────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │ Phase 2: determine path │ (translate goal → DataStates,
                    │                         │  check path exists, lookup or
                    │                         │  generate pipeline, validate)
                    └─────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │ Phase 3: execute (loop) │
                    │   - run step            │
                    │   - replan (dual role)  │ ← SCMS runs continuously inside
                    │   - record evidence     │   for any text-handling step
                    └─────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │ Phase 4: verify goal    │ (probabilistic — achieved?)
                    └─────────────────────────┘
                                │
                            ┌───┴───┐
                            │       │
                       (success)  (failure)
                            │       │
                            ▼       ▼
              ┌────────────────┐  ┌────────────────────────┐
              │ Phase 5:       │  │ Phase 6: failure       │
              │ outcome        │  │ diagnosis (blame       │
              │ consolidation  │  │ attribution)           │
              └────────────────┘  └────────────────────────┘
                            │       │
                            └───┬───┘
                                ▼
                    ┌─────────────────────────┐
                    │ Signals → ALS staging   │ (live evidence accumulates)
                    └─────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │ Dream-time aggregation  │
                    │ + audit + apply (ALS)   │
                    └─────────────────────────┘
```

Two long-lived subsystems sit alongside this lifecycle:

- **SCMS (Sense Confidence Monitoring Subsystem)** — runs continuously during text-handling phases. Coupled monitors (WSD/FOL/frame-match/retrieval/cross-word) refine sense distributions via BSP turn-based execution.
- **ALS (Audited Learning Subsystem)** — runs across dream cycles. Trains parameters of probabilistic capacities using consolidated memories with admin-gated promotion.

Persistent state lives in:

- **L2 lexicon graph** — theoretical layer (from OEWN) + empirical layer (from corpus mining). Single graph, schema-declared layers.
- **L2 task-patterns** — admin-authored sub-shape recognizers + system-discovered emergent patterns.
- **L2 promoted-pipelines** — pipeline confidences per (task-shape, pipeline) tuple.
- **L2 memories** — consolidated MMs from completed tasks.
- **L2 problem-trace** — failure diagnostics.
- **L2 capacity-gaps** — unsolvable task shapes (admin queue).
- **L2 parameter-staging (Local)** — live evidence pending dream-time aggregation.
- **L2 pending-promotions (Local + Global)** — audit queue for proposed parameter updates.
- **L2 learned-parameters** — versioned parameter snapshots for trainable subsystems.
- **L0 user_settings** — per-user training preferences (which parameter families to learn, priority, audit policy override).

---

## 3. SCMS — Sense Confidence Monitoring Subsystem

The SCMS is the canonical mechanism for any sense confidence in MindsOS. It runs whenever a text-handling task is in flight.

### 3.1 Components

**Single-shot init capacities (L3):**

- **`wsd-init`** — reads parsed-text DataState + lexicon empirical layer + `learned-parameters` (via context). Emits initial per-word `DS_SENSE_DISTRIBUTIONS` with calibrated confidences. Multi-candidate by default per Decision 1.
- **`fol-init`** — depends on `wsd-init`'s output. Builds initial FOL state with assumption-tagged statements. Minimizes assumptions per ATMS-style ledger dynamics. Emits `DS_FOL_STATE`.

**Continuous Monitors (L3, descriptive-only nodes; L4 owns lifecycle):**

- **`wsd-update`** — Monitor. Subscribes to: `fol-update`, `frame-match`, `retrieval`, `cross-word`. Refines sense distributions when subscribed signals fire.
- **`fol-update`** — Monitor. Subscribes to: `wsd-update`. Refines FOL state when assumption-elevation events occur. State-change-driven (only emits on actual statement set or epistemic-tag change).
- **`frame-match`** — Monitor. Subscribes to: `wsd-update`. (v1 stub; full design later.)
- **`retrieval`** — Monitor. Subscribes to: relevant context. (v1 stub.)
- **`cross-word`** — Monitor. Subscribes to: `wsd-update`, `fol-update`. (v1 stub.)

### 3.2 Init phase ordering

Strict ordering, not symmetric:

1. **`wsd-init`** runs first. No FOL dependency. Reads lexicon empirical layer + parsed-text DataState.
2. **`fol-init`** runs second. Requires `wsd-init`'s output — FOL cannot construct propositions without typed senses.

After init, control passes to the BSP turn-based update loop.

### 3.3 BSP turn-based execution

L4-orchestrated. Each turn has four phases:

- **Phase 1 — RESOLVE.** For each Monitor with pending signals, L4 invokes the **MSUR pipeline** (multi-source update resolver). MSUR partitions signals into independent / reinforcing / contradictory groups, branches contradictories into assumption threads, scores threads via the Monitor's chosen evaluator method, picks the winning thread, emits losing-thread distinguishing assumptions as `hypothesised` to the MSUR ledger. Returns a resolved_signal.
- **Phase 2 — APPLY.** Each Monitor invokes its `update_state` capacity to apply the resolved_signal.
- **Phase 3 — BROADCAST.** Each Monitor whose state changed emits to its subscribers (L4 routes the messages).
- **Phase 4 — RECEIVE.** Each subscribed Monitor queues incoming signals for next turn's Phase 1.

**Convergence = pair-wise quiescence.** A turn that produces zero Phase-3 broadcasts means no Monitor has anything new to say. The system has extracted what it can from current evidence. L4 detects this state.

**No global compute budget.** L4's task-lifecycle (timeouts, abort, downstream demand) handles runaway as a system-level concern.

### 3.4 MSUR pipeline (L4)

Composed of L3 capacities. Inputs: pending_signals, current_state, evaluator_method_iri, combination_method_iri, comparator_method_iri.

Pipeline steps:

1. `signal_partition` (L3) — classify signal pairs into independent / reinforcing / contradictory.
2. Apply independent signals (hardcoded in pipeline).
3. Apply reinforcing groups via the chosen `combination_method_iri` (L3 method library: `combination.bayesian | combination.weighted_avg | combination.log_pool | combination.max_pool | ...`).
4. Branch contradictory groups into assumption threads (hardcoded).
5. For each thread, invoke `evaluator_method_iri` (L3 method library: `evaluator.entropy_decrease | evaluator.statement_reconciliation | evaluator.coherence_score | ...`) to score.
6. Apply `comparator_method_iri` (L3 method library: `comparator.max | comparator.weighted_sum | comparator.pareto | comparator.lexicographic | ...`) to pick winning thread.
7. Emit losing threads' distinguishing assumptions as `hypothesised` entries in MSUR ledger (per-task, lives in MM).
8. Return resolved_signal to caller.

### 3.5 Monitor declaration contract

Each refinement Monitor declares as L3 graph-node properties:

- `state_datastate_iri` — its working state's DataState shape.
- `update_state_iri` — its L3 update_state capacity.
- `evaluator_method_iri` — one method from `evaluator.*` library.
- `combination_method_iri` — one method from `combination.*` library.
- `comparator_method_iri` — one method from `comparator.*` library.
- `subscribes_to` — list of upstream Monitor IRIs.
- `emits_to` — list of downstream subscriber IRIs.

L4 reads these declarations and orchestrates Monitor execution accordingly.

### 3.6 v1 Monitor instantiation

| Monitor | Evaluator | Combination | Comparator | Subscribes to |
|---|---|---|---|---|
| `wsd-update` | `entropy_decrease` | `bayesian` | `max` | `fol-update`, `frame-match`, `retrieval`, `cross-word` |
| `fol-update` | `statement_reconciliation` | `bayesian` | `max` | `wsd-update` |
| `frame-match` | TBD | TBD | TBD | `wsd-update` |
| `retrieval` | TBD | TBD | TBD | (context) |
| `cross-word` | TBD | TBD | TBD | `wsd-update`, `fol-update` |

### 3.7 MSUR ledger

Per-task, lives in L5 MM during execution. Holds assumption threads with epistemic tags (`assumed | hypothesised | retracted` etc.). Separate from FOL ledger (analogous machinery, distinct state). Persistence beyond task completion is v2.

### 3.8 Convergence and lifecycle

- **Convergence:** pair-wise quiescence detected as a turn with zero Phase-3 broadcasts.
- **Task-end signal:** L4 evaluates the *sufficient-predicate* declared on the active task-pattern. If senses are sufficient for the next task step, consolidate. If insufficient, L4 adds information to the MM (retrieval, HITL, alternative refiners), triggering SCMS re-engagement from current state.
- **Lifecycle ownership:** L4 owns Monitor start/stop. Monitors are descriptive nodes in L3; their execution lifecycle is L4's responsibility (resolves L3 ADR-014's "residents descriptive-only" position).

---

## 4. ALS — Audited Learning Subsystem

ALS is the system-wide trainable-parameter learning infrastructure. It replaces the originally-proposed coherence loop (per L4 §4.3 / Push 3 recommendation accepted).

### 4.1 What ALS trains

Any subsystem with parameters whose values affect probabilistic decisions can register with ALS. v1 registered subsystems include:

- WSD candidate-scorer parameters
- FOL rule confidences and assumption-resolution thresholds
- SCMS Monitor evaluator/combination/comparator method parameters (when they have learnable internals)
- Pipeline-finding parameters (path-finding strategy preferences, exploration policy)
- Task-shape recognition priors
- Goal verification thresholds
- Class generalization materialization policy
- Per-hierarchy weights for class generalization fusion

### 4.2 Subsystem registration contract

Each subsystem registers with ALS by declaring:

- `parameter_set_iri` — which records in `learned-parameters` it owns.
- `signal_sources` — list of `(source_iri, weight)` pairs from the signal-source library (S1 self-distillation, S2 gold anchor, S3 FOL disagreement, S4 ensemble agreement, S5 HITL feedback, S6 task outcome, S7 active learning, S8 replan divergence).
- `update_mechanisms` — per-parameter mapping of `parameter_iri → mechanism_iri` from L3 update mechanism library (M2 Bayesian, M3 EMA, M4 Beta posterior; M1 gradient descent deferred to v2 pending blob storage per FOL #8).
- `validation_methods` — list of validators (V1 gold accuracy, V2 calibration ECE/Brier, V3 distribution drift; V5 versioning is automatic).
- `audit_policy` — `auto-apply` | `batched-summary` | `individual-review`.
- `eligible_audit_scopes` — subset of `{local, global}`.

### 4.3 Two tracks

**Track A — `sense-correlations` priority updates.** Empirical-layer edge counts and metric values mined from consolidated memories. Auto-apply audit policy (low-risk; wrong correlations just slow disambiguation slightly, don't produce wrong answers). Updated continuously via dream-time mining.

**Track B — Scorer parameter updates.** Per-subsystem trainable parameters (WSD scorer weights, FOL rule confidences, etc.). Individual-review or batched-summary audit policy (high-risk — wrong parameters produce systematically wrong outputs). Goes through full ALS pipeline.

### 4.4 Live + dream hybrid timing (T3)

- **Live phase.** As tasks complete, evidence rows are written to `parameter-staging` (Local L2 role-graph). One row per (parameter_iri, signal_source, evidence_pointer, blame_weight, timestamp).
- **Dream phase.** Maintenance dream pulls from `parameter-staging`, aggregates per-parameter using the subsystem's chosen mechanism, runs validators, writes proposed updates to `pending-promotions` (Local).
- **Audit phase.** Per audit policy: auto-apply, or batched-summary admin review, or individual review by user (Local) / system admin (Global).
- **Apply phase.** On approval, versioned write to `learned-parameters` using existing `ParameterSnapshot` `SUPERSEDES` machinery.

### 4.5 Local → Global promotion

Periodically (admin-triggered), a Global training cycle aggregates approved Local updates across users, validates the same way, queues for Global admin review, applies on approval. Same machinery, different scope.

### 4.6 Phase 6 — Failure diagnosis (blame attribution)

Runs only when failure is detected (Phase 4 returns false, or external signal contradicts a consolidated outcome).

Components:

- `analyze_failure_provenance` — walk the provenance chain. Distribute blame using inverse-confidence + replan-divergence + hard-failure-isolation heuristics. Returns weighted attribution across probabilistic steps in the failed run.
- `cross_validate_failure` — optional. Run an alternative pipeline on the same input. If alternative succeeds → blame Phase 2 (pipeline selection wrong); if both fail → blame Phase 1 (interpretation wrong).
- `request_human_diagnostic` — optional. HITL when auto-attribution confidence is low.
- `route_to_als` — emit per-parameter-set signals weighted by blame to ALS staging.

Blame-weighted signals are the contract change ALS signals carry: `(parameter_set_iri, signal_source, blame_weight, evidence_pointer)`.

### 4.7 Audit policies and user-as-Local-admin

- **`auto-apply`** — no admin review. Validation passes → write directly. v1 default for Track A (`sense-correlations` priority updates).
- **`batched-summary`** — admin sees aggregate diff per dream cycle, approves whole batch. Reasonable v1 default for many parameter classes.
- **`individual-review`** — admin reviews each proposed update. v1 default for high-risk parameters.

At Local scope, the user *is* the admin. Audit UI must be accessible to end users for Local approvals. At Global scope, system admin approves.

User can override the declared policy to **more-conservative** (e.g., subsystem says `batched-summary`; user wants `individual-review` for their Local). Cannot override to less-conservative.

### 4.8 User training preferences (lives in L0 server, not L2)

Per-user preferences declare which parameter families this user wants their Local system to learn:

- Master switch: `training_enabled`.
- Per `parameter_set_iri`: `enabled` (bool), `priority` (`low | normal | high`), `audit_policy_override` (more-conservative-only).
- Notes / rationale.

Lives in L0 server's `user_settings` table (per the L0 coordinated-change handoff).

ALS reads at the start of every dream training cycle. Disabled subsystems get no signal collection from this user.

---

## 5. Lexicon empirical layer

The lexicon graph holds two layers in v1:

- **`theoretical` layer** — definitional relationships from curated lexical resources (OEWN/WordNet): `HYPERNYM_OF`, `HYPONYM_OF`, `SYNSET_MEMBER`, `ANTONYM_OF`, `MERONYM_OF`, etc.
- **`empirical` layer** — observed-from-corpus relationships: co-occurrence, predicate-argument, frame-element, class-restriction.

Both layers live in the same lexicon graph; layer membership is declared at schema level (per L1 coordinated-change handoff Change 2 — schema-declared layers).

### 5.1 Empirical-layer edge types

- **Co-occurrence sub-types:** `COOCCURS_SAMESENT`, `COOCCURS_DEPARC`, `COOCCURS_SAMECLAUSE`, `COOCCURS_SAMEFRAME`.
- **Predicate-argument sub-types:** `SUBJECT_OF`, `DOBJECT_OF`, `IOBJECT_OF`, `OBL_OF`.
- **Frame-element sub-types:** `AGENT_OF`, `PATIENT_OF`, `THEME_OF`, `INSTRUMENT_OF`, `LOCATION_OF`, `TIME_OF`.
- **Class-restriction sub-types:** `IS_VALID_FILLER_FOR` (for VerbNet class-level generalizations).

### 5.2 Edge properties (empirical layer)

- `evidence_count` — observation count.
- `metric:resnik_strength`, `metric:pmi_strength`, `metric:conditional_prob`, ... — multiple metric values stored per edge (one property per applicable metric).
- `confidence` — Beta-posterior reliability of the strength estimates.
- `domain_tag` — domain label (general / news / biomedical / ...).
- `first_observed`, `last_observed` — temporal bounds.
- `source_corpus_iris` — provenance.

### 5.3 Multi-metric per edge

Each metric is an L3 capacity in a method library:

- `metric.resnik_selectional_association`
- `metric.pmi`
- `metric.conditional_probability`
- `metric.lin_selectional_association` (v2)
- `metric.bert_likelihood` (v2+, gated on FOL #8 blob storage)

Edges store multiple metric values as separate properties. Readers (WSD scorer, FOL update, etc.) pick which metric to query.

### 5.4 Per-dataset independent importers

v1 importer set:

- `SemCorImporter` — co-occurrence + predicate-argument layers. Brown corpus parses + WordNet sense IDs. Gold quality, ~25k sense-tagged tokens.
- `OntoNotesImporter` — predicate-argument (PropBank → SemLink → FrameNet roles → WordNet senses) + co-occurrence + frame-element layers. ~2.5M words. Gold quality, multi-genre.
- `FrameNetImporter` (extended) — frame-element layer directly. ~200k annotated examples.
- `VerbNetImporter` — predicate-argument + class-restriction layers. ~6,200 verbs in ~270 classes. Lexical resource (not corpus).
- `SemLinkImporter` — alignment graph (bridge). Doesn't generate empirical edges directly.
- `GlossTagImporter` — co-occurrence layer (down-weighted). Dictionary text caveat per WSD design.

Held-out (not for training):

- SemEval-2007/2013/2015/2017 verb subset.
- MASC random sample.

Deferred to v2+:

- OMSTI, UMBC WebBase, NomBank, biomedical corpora.

**Importer independence:** each importer runs standalone; no cross-importer calls. Shared utility libraries (`sense_iri_align`, `class_generalize`, `metric_compute`, `mwe_segment`) are stateless helpers. Operational prerequisites enforced fail-fast (importer raises if SemLink missing for alignment).

### 5.5 Class generalization architecture (expandable + learnable)

Five-mechanism stack:

**Mechanism 1 — Pluggable hierarchy registry.** Each class hierarchy is its own L2 ontology graph. Adding a new hierarchy = importing it + registering it.

**Mechanism 2 — Per-hierarchy L3 ancestor-walk capacity.** `class.ancestors_dolce`, `class.ancestors_wordnet_hypernym`, `class.ancestors_verbnet`, `class.ancestors_framenet`. New hierarchy = new capacity.

**Mechanism 3 — Cross-system mappings as InterGraphEdges.** WordNet↔DOLCE, VerbNet↔DOLCE, etc. Hand-curated in v1. Uses the new `InterGraphEdge` L1 primitive (per L1 coordinated-change handoff).

**Mechanism 4 — Learnable materialization policy** (in `learned-parameters` via ALS). Per-(predicate-class, role) tuple, the system learns which hierarchy levels are most informative. Default: DOLCE all levels mandatory; WordNet/VerbNet/FrameNet lazy. Adapts based on observed query-pattern utility.

**Mechanism 5 — Learnable per-hierarchy weights** (in `learned-parameters` via ALS). Per-task-pattern, per-hierarchy weights for fusing class-level contributions. Default: equal weights. Adapts based on outcome utility (S6).

v1 hierarchies registered: DOLCE, WordNet hypernym, VerbNet, FrameNet inheritance.

Cross-system mappings v1: hand-curated subset (DOLCE↔WordNet, ~10–20% coverage).

Hierarchy registration is **admin-only** in v1 — dream-time discovery of new hierarchies deferred to v2+.

### 5.6 Negative evidence

Implicit via Resnik class smoothing. No separate negative-edge schema.

Phase-6 failure attribution is the only explicit negative channel: when failure analysis attributes blame to a specific empirical-layer edge, ALS demotes its `confidence` and `correlation_strength`.

### 5.7 MWE handling

MWEs are nodes in lexicon graph (FrameNet's MWE lexical units already exist as nodes; WordNet collocations also). Existing edge types and layers work over them. Bootstrap-only detection in v1; runtime MWE detector deferred to v2.

MWE nodes participate in:

- Theoretical layer edges (hypernym, etc.) — same as any sense.
- Empirical layer edges — same as any sense.

No new schema layer for MWEs (option (b) in MWE design discussion).

### 5.8 Read patterns

Subsystems reading the empirical layer use schema-aware helpers from L1's layer mechanism:

- `iter_layer_edges("empirical", from_node=sense_X, edge_type="SUBJECT_OF")` — typed traversal.
- `count_layer_edges("empirical")` — layer-level statistics.

WSD scorer uses empirical layer for correlation-aware confidence. FOL update uses both empirical and theoretical (fuses for assumption resolution). Other subsystems pick appropriate layers.

### 5.9 Update mechanics

Dream-time consolidation:

1. Walk consolidated memories' inference traces.
2. Identify empirical-layer edges that were used.
3. For each used edge: increment evidence_count, recompute metric values (Resnik / PMI / etc.) with smoothing, update last_observed.
4. For genuinely-new correlations observed: create new edge with initial low confidence.
5. For Phase-6-attributed contradictions: demote confidence on the contradicted edge.
6. Single dream-time correlation-mining capacity consolidates evidence from all subsystems' inference traces; writes once. Avoids cross-subsystem write conflicts.
7. Read-only during task execution; writes only during dream-time.

---

## 6. Task lifecycle (six phases)

### Phase 0 — Arrival
- `task_input` (input DataState).
- `session_context` (from L0, including user_settings).

### Phase 1 — Task interpretation (probabilistic)

- `recognize_task_shape(task_input) → (task_shape, confidence)` — match input against `L2.task-patterns` admin-authored sub-shape recognizers + emergent patterns.
- `derive_task_goal(task_shape, task_input) → (task_goal, confidence)` — derive what end state must be reached.

### Phase 2 — Pipeline determination

- `translate_goal_to_datastates(task_goal) → (target_datastates, confidence)` — probabilistic.
- `check_path_exists(start_state, target_datastates) → bool` — deterministic graph reachability.
- If no path → write to `capacity-gaps`; return "I don't know."
- `lookup_known_pipeline(task_shape, target_datastates) → list[(pipeline, match_confidence)]`.
- `generate_pipeline(start_state, target_datastates, generation_policy) → (pipeline, confidence)` — probabilistic, runs L3 path-finding.
- `select_pipeline(known, generated, exploration_policy) → pipeline` — probabilistic, explore-vs-exploit.
- `validate_pipeline(pipeline, target_datastates) → (plausible, confidence)` — probabilistic, uses capacity preconditions/effects.

### Phase 3 — Pipeline execution (per step)

- `execute_step(state, capacity, params) → new_state` — deterministic per capacity.
- `replan(current_state, target_datastates, remaining) → (next_step, divergence, confidence)` — **dual role**: forward goal-orientation check + reflective pipeline-quality validation. Probabilistic.
- `record_replan(replan_event) → void` — log to MM's replan history (feeds S8 signal).
- `handle_step_failure(failed_step, current_state) → action` — probabilistic.
- `detect_mid_execution_gap(current_state, remaining) → bool` — deterministic.

SCMS runs continuously inside any text-handling step.

### Phase 4 — Goal verification (probabilistic)

- `check_goal_state_match(current_state, target_datastates) → (matches, confidence)`.
- `verify_goal_achievement(current_state, task_goal, replan_history) → (achieved, confidence, achievement_quality)`.
- `external_validation(achievement, task_input, current_state) → external_signal | none` — optional HITL/gold/downstream.

### Phase 5 — Outcome processing

- `consolidate_outcome(...) → outcome_record`.
- `consolidate_mm_to_memory(...) → memory_record` — write final MM to `L2.memories`.
- `flag_capacity_gap(...) → void` — if applicable.
- `emit_signals_to_als(outcome) → list[signal_event]` — route to ALS staging.

### Phase 6 — Failure diagnosis (only on failure or contradicted outcome)

- `analyze_failure_provenance(outcome_record) → list[(parameter_set, blame_weight)]`.
- `cross_validate_failure(...)` — optional.
- `request_human_diagnostic(...)` — optional HITL.
- `record_diagnostic_outcome(...)`.
- `route_to_als(blame_weights) → ALS_update_signals`.

---

## 7. v1 deliverables

### L1 (per `coordinated_change_L1_intergraph_and_layers.md`)

- `InterGraphEdge` primitive (cross-graph node-to-node edge type).
- Schema-declared layer mechanism (`Schema.add_layer`, `Schema.iter_layer_edges`, etc.).

### L2 (per `coordinated_change_L2_lexicon_layers_and_role_graphs.md`)

- Lexicon schema gains `theoretical` and `empirical` layer declarations.
- New importers: `SemCorImporter`, `OntoNotesImporter`, `VerbNetImporter`, `SemLinkImporter`, `GlossTagImporter`.
- Extended `FrameNetImporter` to populate empirical-layer frame-element edges.
- New role-graphs: `parameter-staging` (Local), `pending-promotions` (Local + Global), `capacity-gaps` (Global, admin-visible).
- Removed from spec: `sense-correlations` as separate role-graph (now empirical layer of lexicon); single `learned-parameters` role-graph (split per FOL #4 if accepted; otherwise single).
- task-patterns: schema for sub-shape recognizers + emergent patterns; admin-authored v1 set.
- promoted-pipelines: confidence updates as ALS subsystem.
- Cross-system mappings as InterGraphEdges (DOLCE↔WordNet hand-curated subset).

### L3 (per `coordinated_change_L3_capacities_and_monitors.md`)

- New L3 capacities:
  - SCMS init capacities: `wsd-init`, `fol-init`.
  - SCMS Monitors: `wsd-update`, `fol-update`, `frame-match` (stub), `retrieval` (stub), `cross-word` (stub).
  - Per-Monitor `update_state` capacities.
  - MSUR helper: `signal_partition`.
  - Method libraries: `evaluator.*` (entropy_decrease, statement_reconciliation, ...), `combination.*` (bayesian, weighted_avg, log_pool, ...), `comparator.*` (max, weighted_sum, pareto, ...).
  - Metric library: `metric.resnik_selectional_association`, `metric.pmi`, `metric.conditional_probability`.
  - Class ancestor-walk: `class.ancestors_dolce`, `class.ancestors_wordnet_hypernym`, `class.ancestors_verbnet`, `class.ancestors_framenet`.
  - Failure-diagnosis: `analyze_failure_provenance`, `cross_validate_failure`, `request_human_diagnostic`.
  - ALS signal-source capacities: `signal:self_distillation`, `signal:gold_anchor`, `signal:fol_disagreement`, `signal:ensemble_agreement`, `signal:task_outcome`, `signal:replan_divergence`.
  - Update mechanism library: `mechanism.bayesian_update`, `mechanism.ema`, `mechanism.beta_posterior`.
- L3 ADR-014 resolution: Monitors descriptive-only, L4 owns lifecycle.
- L4 Push 2 acceptance: action contracts (`precondition_iri`, `effect_iri`) on L3 capacity registrations.
- Monitor declaration shape: `state_datastate_iri`, `update_state_iri`, `evaluator_method_iri`, `combination_method_iri`, `comparator_method_iri`, `subscribes_to`, `emits_to`.

### L4 (per `coordinated_change_L4_intelligence_and_als.md`)

- ALS as coherence-loop replacement (Push 3 accepted).
- MSUR pipeline (admin-authored, ships v1).
- SCMS BSP turn pipeline.
- Six-phase task lifecycle.
- Replan-check dual-role spec (forward + reflective).
- S8 (replan-divergence) added to signal-source library.
- Pipeline-finding registered as ALS-trainable subsystem.
- Capacity-gap admin queue surfaced in admin tooling.
- Three audit policies (auto-apply / batched-summary / individual-review) with user-can-override-more-conservative semantics.

### L0 (per `coordinated_change_L0_user_settings.md`)

- New `user_settings` table in `server.db` for training preferences.
- Settings exposed via `Session` to L4.

### Bootstrap-time deliverables (admin-actionable)

- v1 admin-authored task-patterns set: sub-shape recognizers (`sense-disambiguation-needed`, `coreference-resolution-needed`, `frame-fitting-needed`, `question-decomposition-needed`, `constraint-translation-needed`, `novel-lemma-encountered`, `cross-realm-bridge-needed`, `logical-coherence-required`, ...).
- Hand-curated DOLCE↔WordNet cross-system mappings (subset).
- Held-out gold sets (SemEval verb subset + MASC sample) for validation.

---

## 8. Open WSD-internal questions

Detail-level items still TBD (not blockers for layer-coordinated work, but needed before code):

- **Loss function final form.** Recommended: KL-divergence + ambiguity-weighted (round-5 pushback 2D).
- **Self-training oracle anchor specifics.** Recommended: composite of S1 (self-distillation) + S2 (gold) + S3 (FOL-disagreement) + S4 (ensemble) per round-5 pushback 1.
- **Confidence container dataclasses.** Concrete fields for `SenseCandidate` and `SenseDistribution` DataStates.
- **wsd-init's input DataState shape** — exact structure of L2-enriched parsed-text output.
- **Convergence-improvement metrics per subsystem** — formal definition of "improved" for `wsd-update` (entropy decrease threshold? top-k change?), `fol-update` (boolean state change), and TBD subsystems (`frame-match`, `retrieval`, `cross-word`).
- **Sufficient-predicate per task-pattern** — what counts as "senses are sufficient for next task step" for each admin-authored task-pattern.
- **Failure-diagnosis blame heuristic constants** — concrete coefficients for inverse-confidence × replan-divergence × hard-failure-isolation.
- **ALS update mechanism choices** — which mechanism (M2/M3/M4) per parameter for each registered subsystem.
- **Bootstrap importer concrete schemas** — per-importer EdgeType definitions, validation rules.

---

## 9. Reading order — layer-specific docs

For implementation:

1. **L1 first** — `coordinated_change_L1_intergraph_and_layers.md`. Foundational primitives must land before L2 schema work.
2. **L0 in parallel** — `coordinated_change_L0_user_settings.md`. Independent of L1; can ship simultaneously.
3. **L2 second** — `coordinated_change_L2_lexicon_layers_and_role_graphs.md`. Depends on L1 schema-layers.
4. **L3 third** — `coordinated_change_L3_capacities_and_monitors.md`. Depends on L2 schema being available.
5. **L4 fourth** — `coordinated_change_L4_intelligence_and_als.md`. Depends on L3 capacities.

Within each layer, the coordinated-change doc lists internal phasing recommendations.

---

## 10. What this design does NOT include

To be explicit about scope:

- **No multi-domain ontology support in v1.** Single foundational ontology (DOLCE). Multi-domain (medical, legal, technical) deferred to v3+.
- **No ontology learning in v1.** No relation induction, no automatic class hierarchy discovery. Hand-curated only.
- **No neural scorer in v1.** M1 (gradient descent) deferred until FOL #8 (blob storage) lands. Bayesian / EMA / Beta-posterior mechanisms only.
- **No HITL UX in v1.** Active learning (S7) and HITL diagnostic capabilities are deferred until UX work happens.
- **No pipeline-variant capacity synthesis.** L4 doesn't compose new L3 capacities by combining existing ones. Path-finding only.
- **No structural pipeline mutation mid-run beyond replan.**
- **No cross-user federated learning in v1.** Local + admin-triggered Global only.
- **No pause-and-resume in v1.** Per L4 Push 5 — abort-on-logout in v1.

---

## 11. Calibration as the validation target — recap

Throughout the system:

- **Validation** uses calibration metrics (ECE, Brier score, NLL) on held-out gold.
- **Training loss** is KL-divergence with ambiguity-weighting.
- **Audit gates** include calibration regression checks.
- **Drift detection** uses calibration as the leading indicator.

Better-calibrated outputs are the design goal at every level. Higher single-sense accuracy is a *derived* benefit, not the goal.

---

## 12. Decision log — chat outcomes

Decisions made during the 2026-04-29 design conversation:

1. Calibrated coverage replaces "100% accuracy" as the goal.
2. Multi-candidate output mandatory for WSD (Decision 1).
3. WSD decomposed into family of L3 capacities + L4 pipeline (Decision 2).
4. Coherence loop cut from v1; ALS substitutes (Push 3 accepted).
5. Task-patterns are emergent + admin-authored; many ship in v1.
6. Single lexicon graph with schema layers; no separate `sense-correlations` role-graph.
7. Per-dataset independent importers with shared utility libraries.
8. Multi-metric per edge (Resnik + PMI + conditional in v1).
9. Hybrid class generalization: DOLCE mandatory + WordNet lazy + learnable materialization policy.
10. Negative evidence implicit via Resnik smoothing + Phase-6 attribution.
11. MWE handling as node-type concern, bootstrap-only detection.
12. SCMS BSP turn-based execution with MSUR.
13. Pair-wise quiescence as convergence model.
14. Replan dual-role: forward goal-check + reflective pipeline-validity-check.
15. Six-phase task lifecycle including Phase 6 failure diagnosis.
16. Blame-weighted signal flow to ALS.
17. Three audit policies with user-can-override-more-conservative.
18. User-as-Local-admin; user training preferences in L0 user_settings.
19. Pluggable expandable+learnable class generalization (5-mechanism stack).
20. v1 cuts: no multi-domain, no neural scorer, no HITL UX, no capacity synthesis, no pause-and-resume.

---

**End of architecture.**

Update with date and new decision-log entries when this design evolves.
