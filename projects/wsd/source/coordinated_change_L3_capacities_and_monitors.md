# Coordinated Change Handoff — L3 Capacity: New Capacities, Method Libraries, Monitor Lifecycle Resolution

**Date:** 2026-04-29
**Origin:** WSD subsystem design conversation (Word Sense Disambiguation project, Henrique Alvim).
**Purpose:** Surface L3 Capacity Layer additions required by the WSD subsystem architecture.
**Status:** Pre-implementation. Architectural specification only.
**Depends on:** L1 Core (`coordinated_change_L1_intergraph_and_layers.md`), L2 Knowledge (`coordinated_change_L2_lexicon_layers_and_role_graphs.md`).

---

## 0. How to use this document

Upload to the L3 design chat. Self-contained — does not require WSD-design-chat context. The L3 chat should:

1. Read §1 (motivation) and §2 (summary) to orient.
2. Read §3–§8 for each new capacity / capacity family / contract change.
3. Read §9 (coordinated implications) for ripple effects across other layers.
4. Read §10 (open questions) before designing internals.
5. Read §11 (phasing) for sequencing.
6. Read §12 (what this does NOT change) to bound scope.

L3 owns: capacity declarations, IRI conventions, registration/discovery, Monitor lifecycle (subject to resolution per §6 below). This handoff specifies *what* needs to land; *how* (capacity body internals, persistence shapes) is L3's call.

---

## 1. Why this handoff exists

The WSD subsystem requires substantial L3 additions:

  - **SCMS init capacities and Monitors** (`wsd-init`, `wsd-update`, `fol-init`, `fol-update`, plus stubs for `frame-match`, `retrieval`, `cross-word`).
  - **Per-Monitor `update_state` capacities** for each refinement subsystem.
  - **MSUR helper capacities** (`signal_partition`).
  - **Three new method libraries** (`evaluator.*`, `combination.*`, `comparator.*`) for SCMS Monitor declarations.
  - **Metric library** (`metric.resnik_selectional_association`, `metric.pmi`, `metric.conditional_probability`).
  - **Class ancestor-walk capacity per registered hierarchy** (`class.ancestors_dolce`, `class.ancestors_wordnet_hypernym`, `class.ancestors_verbnet`, `class.ancestors_framenet`).
  - **Failure-diagnosis capacities** (`analyze_failure_provenance`, `cross_validate_failure`, `request_human_diagnostic`).
  - **ALS signal-source capacities** (S1 self-distillation, S2 gold anchor, S3 FOL disagreement, S4 ensemble agreement, S6 task outcome, S8 replan divergence).
  - **Update mechanism library** (`mechanism.bayesian_update`, `mechanism.ema`, `mechanism.beta_posterior`).
  - **L3 ADR-014 resolution:** Monitors descriptive-only; L4 owns lifecycle.
  - **L4 Push 2 acceptance:** action contracts (`precondition_iri`, `effect_iri`) on L3 capacity registrations.
  - **Monitor declaration shape extension** for SCMS Monitors.

---

## 2. Summary of changes

| # | Change | Section | Priority |
|---|---|---|---|
| 1 | SCMS init capacities (single-shot) | §3.1 | High |
| 2 | SCMS Monitors (descriptive + L4-orchestrated) | §3.2 | High |
| 3 | Per-Monitor `update_state` capacities | §3.3 | High |
| 4 | MSUR helper: `signal_partition` | §4 | High |
| 5 | Method library: `evaluator.*` | §5.1 | High |
| 6 | Method library: `combination.*` | §5.2 | High |
| 7 | Method library: `comparator.*` | §5.3 | High |
| 8 | Method library: `metric.*` | §5.4 | High |
| 9 | Method library: `class.ancestors_*` per hierarchy | §5.5 | Medium |
| 10 | ALS signal-source capacities | §6 | High |
| 11 | Update mechanism library: `mechanism.*` | §7 | High |
| 12 | Failure-diagnosis capacities | §8 | High |
| 13 | L3 ADR-014 resolution: descriptive Monitors, L4 owns lifecycle | §9 | High |
| 14 | L4 Push 2 acceptance: action contracts on registrations | §10 | High |
| 15 | Monitor declaration shape extension | §11 | High |
| 16 | Shared utility capacities for L2 importers | §12 | Medium |

---

## 3. SCMS capacities

### 3.1 Init capacities (single-shot)

**`wsd-init`** (capacity IRI: `capacity:wsd:init`)

- **Inputs:** parsed-text DataState (TBD shape; produced by upstream `text.*` capacities — tokenize, lemma, POS-tag, dependency-parse).
- **Reads:** lexicon graph (empirical layer + theoretical layer) + `learned-parameters` via context threading.
- **Outputs:** `DS_SENSE_DISTRIBUTIONS` — per-word multi-candidate sense distributions with calibrated confidences.
- **Determinism:** fixed function of inputs + active learned parameters; per L3 ADR-001 (capacities are fixed). Parameter updates happen via L2's `learned-parameters` graph, not capacity self-modification.
- **Action contract** (per §10 below):
  - `precondition_iri`: parsed-text DataState exists, at least one content word present.
  - `effect_iri`: `DS_SENSE_DISTRIBUTIONS` produced, sum-to-1 per word, multi-candidate where ambiguity exists.

**`fol-init`** (capacity IRI: `capacity:fol:init`)

- **Inputs:** `DS_SENSE_DISTRIBUTIONS` (from wsd-init).
- **Reads:** `fol-rules` (existing FOL role-graph), lexicon empirical + theoretical layers, `learned-parameters` via context.
- **Outputs:** `DS_FOL_STATE` — initial FOL state with assumption-tagged statements; minimizes assumption count per ATMS-style ledger dynamics.
- **Determinism:** same as wsd-init.
- **Strict ordering:** must run *after* wsd-init in pipeline composition. L4 enforces order.
- **Action contract:**
  - `precondition_iri`: `DS_SENSE_DISTRIBUTIONS` exists.
  - `effect_iri`: `DS_FOL_STATE` produced, assumption count minimized given input distributions.

### 3.2 SCMS Monitors (descriptive nodes; L4-orchestrated)

Five Monitors in v1, three are stubs:

- **`wsd-update`** (capacity IRI: `capacity:wsd:update`) — L3 Monitor node.
- **`fol-update`** (capacity IRI: `capacity:fol:update`) — L3 Monitor node.
- **`frame-match`** (capacity IRI: `capacity:frame:match`) — L3 Monitor node, v1 stub.
- **`retrieval`** (capacity IRI: `capacity:retrieval:scms`) — L3 Monitor node, v1 stub.
- **`cross-word`** (capacity IRI: `capacity:wsd:cross_word`) — L3 Monitor node, v1 stub.

**Monitors are descriptive nodes only.** L4 owns their lifecycle (start at task begin, stop at consolidation/abort) and their per-turn execution. This resolves L3 ADR-014's "residents descriptive only" position (per §9 below).

Each Monitor's declaration carries (per §11 below):

  - `state_datastate_iri`
  - `update_state_iri` (its L3 update_state capacity)
  - `evaluator_method_iri` (one method from `evaluator.*` library)
  - `combination_method_iri` (one method from `combination.*` library)
  - `comparator_method_iri` (one method from `comparator.*` library)
  - `subscribes_to: list[capacity_iri]`
  - `emits_to: list[capacity_iri]`

v1 instantiation:

| Monitor | state DataState | evaluator | combination | comparator | subscribes_to |
|---|---|---|---|---|---|
| `wsd-update` | `DS_SENSE_DISTRIBUTIONS` | `evaluator.entropy_decrease` | `combination.bayesian` | `comparator.max` | `fol-update`, `frame-match`, `retrieval`, `cross-word` |
| `fol-update` | `DS_FOL_STATE` | `evaluator.statement_reconciliation` | `combination.bayesian` | `comparator.max` | `wsd-update` |
| `frame-match` | `DS_FRAME_MATCHES` (TBD) | TBD | TBD | TBD | `wsd-update` |
| `retrieval` | `DS_RETRIEVAL_RESULTS` (TBD) | TBD | TBD | TBD | (context-driven) |
| `cross-word` | `DS_WORD_CONSTRAINTS` (TBD) | TBD | TBD | TBD | `wsd-update`, `fol-update` |

### 3.3 Per-Monitor `update_state` capacities

Each refinement Monitor ships with its own `update_state` capacity. Inputs: `(current_state, resolved_signal)`. Outputs: `new_state`.

- `capacity:wsd:update_state` — applies a resolved sense-distribution update.
- `capacity:fol:update_state` — applies a resolved FOL-state update (statement set, epistemic tags).
- `capacity:frame:update_state` — v1 stub.
- `capacity:retrieval:update_state` — v1 stub.
- `capacity:wsd:cross_word_update_state` — v1 stub.

Action contracts on each (per §10):

  - precondition: current_state matches expected DataState shape.
  - effect: new_state differs from current_state by exactly the resolved_signal's content.

---

## 4. MSUR helper capacity

### `signal_partition` (capacity IRI: `capacity:agglomeration:signal_partition`)

- **Inputs:** `(pending_signals, current_state)`.
- **Outputs:** `(independent_signals, reinforcing_groups, contradictory_groups)`.
- **Predicate (v1):**
  - **Independent:** signals affecting disjoint targets.
  - **Reinforcing:** signals affecting the same target with same modal-direction shifts.
  - **Contradictory:** signals affecting the same target with different modal-direction shifts.

Single canonical implementation in v1; may grow variants (different contradiction predicates) later.

The other MSUR pipeline steps (apply_independent, branch_instantiate, hypothesis_tag_emit, thread iteration loop, broadcast trigger) are hardcoded in the L4 MSUR pipeline (per WSD architecture §3.4 and L3 decomposition Option B from the design). Not L3 capacities.

---

## 5. Method libraries

Each library is a family of L3 capacities. Subsystems (Monitors and registered ALS subsystems) declare which method to use by IRI. v1 ships with the methods listed; new methods added as new L3 capacities.

### 5.1 `evaluator.*` library

Goal evaluator methods for SCMS Monitors (per Monitor's `evaluator_method_iri` declaration). Stateless. Inputs: a state. Outputs: a scalar score.

- **`evaluator.entropy_decrease`** (`capacity:scoring:evaluator.entropy_decrease`) — total joint entropy across per-word sense distributions; lower is better.
- **`evaluator.statement_reconciliation`** (`capacity:scoring:evaluator.statement_reconciliation`) — discrete statement-set or epistemic-tag-set change count; higher is better.
- **`evaluator.coherence_score`** (`capacity:scoring:evaluator.coherence_score`) — TBD; for frame-match / retrieval Monitors when designed.
- Future: extensible — new evaluator = new L3 capacity.

### 5.2 `combination.*` library

Combination methods for reinforcing-group aggregation in MSUR. Stateless. Inputs: list of update signals + current state. Outputs: combined signal.

- **`combination.bayesian`** (`capacity:agglomeration:combination.bayesian`) — Bayesian update assuming independence.
- **`combination.weighted_avg`** (`capacity:agglomeration:combination.weighted_avg`) — weighted arithmetic mean.
- **`combination.log_pool`** (`capacity:agglomeration:combination.log_pool`) — log-linear pooling.
- **`combination.max_pool`** (`capacity:agglomeration:combination.max_pool`) — max across signals.
- Future: extensible.

### 5.3 `comparator.*` library

Comparator methods for thread selection in MSUR. Stateless. Inputs: list of `(thread_state, score)`. Outputs: winning thread.

- **`comparator.max`** (`capacity:agglomeration:comparator.max`) — highest score wins.
- **`comparator.weighted_sum`** (`capacity:agglomeration:comparator.weighted_sum`) — sum scores across multiple metrics if multi-metric scoring.
- **`comparator.pareto`** (`capacity:agglomeration:comparator.pareto`) — return non-dominated thread set if multi-objective.
- **`comparator.lexicographic`** (`capacity:agglomeration:comparator.lexicographic`) — ranked by primary metric, ties broken by secondary.
- Future: extensible.

### 5.4 `metric.*` library — for empirical-layer edge values

Each metric is an L3 capacity. Inputs: `(observation_count, class_priors, contextual_data)`. Outputs: scalar metric value.

- **`metric.resnik_selectional_association`** (`capacity:scoring:metric.resnik_selectional_association`) — information-theoretic selectional association per Resnik 1996.
- **`metric.pmi`** (`capacity:scoring:metric.pmi`) — pointwise mutual information.
- **`metric.conditional_probability`** (`capacity:scoring:metric.conditional_probability`) — `P(b|a)`. Cheap; per WSD handoff §8.1 known to be biased — useful for sanity comparison.
- **Deferred to v2:**
  - `metric.lin_selectional_association` — Lin's refinement.
  - `metric.bert_likelihood` — neural; gated on FOL #8 blob storage.

Each empirical-layer edge stores multiple metric values as separate properties (per L2 handoff §3.3 — `metric_resnik_strength`, `metric_pmi_strength`, etc.). Importers and dream miners run one or more metric capacities per edge; readers pick which to query.

### 5.5 `class.ancestors_*` library — per registered hierarchy

Per WSD architecture §5.5 (Mechanism 2 of the class-generalization stack). Each registered class hierarchy ships its own ancestor-walk capacity:

- **`class.ancestors_dolce`** (`capacity:knowledge:class.ancestors_dolce`) — DOLCE class ancestors. Reads from L2 ontology graph (DOLCE).
- **`class.ancestors_wordnet_hypernym`** (`capacity:knowledge:class.ancestors_wordnet_hypernym`) — WordNet hypernym tree ancestors. Reads from L2 lexicon graph theoretical layer.
- **`class.ancestors_verbnet`** (`capacity:knowledge:class.ancestors_verbnet`) — VerbNet class hierarchy ancestors. Reads from L2 ontology or lexicon (depending on where VerbNet imports — open).
- **`class.ancestors_framenet`** (`capacity:knowledge:class.ancestors_framenet`) — FrameNet inheritance hierarchy. Reads from L2 concepts graph.

Each is a stateless L3 capacity. Inputs: sense_iri. Outputs: ordered list of ancestor class IRIs from leaf to root.

New hierarchy = new capacity. Registration is admin-only in v1 (per WSD architecture §5.5).

---

## 6. ALS signal-source capacities

Each signal source for ALS is an L3 capacity that emits training-evidence rows. Stateless. Inputs: outcome-related data. Outputs: list of evidence rows for staging.

- **`signal:self_distillation`** (`capacity:als:signal.self_distillation`) — emits S1 evidence: final consolidated sense distributions as KL targets for upstream init parameters.
- **`signal:gold_anchor`** (`capacity:als:signal.gold_anchor`) — emits S2 evidence: gold-set comparison evidence.
- **`signal:fol_disagreement`** (`capacity:als:signal.fol_disagreement`) — emits S3 evidence: when FOL detects contradictions in chosen sense set, demote evidence.
- **`signal:ensemble_agreement`** (`capacity:als:signal.ensemble_agreement`) — emits S4 evidence: when k of N independent scorer strategies agree at high confidence, training-eligible.
- **`signal:hitl_feedback`** (`capacity:als:signal.hitl_feedback`) — emits S5 evidence (deferred until UX exists).
- **`signal:task_outcome`** (`capacity:als:signal.task_outcome`) — emits S6 evidence: task succeeded / failed flag.
- **`signal:active_learning`** (`capacity:als:signal.active_learning`) — emits S7 evidence (deferred).
- **`signal:replan_divergence`** (`capacity:als:signal.replan_divergence`) — emits S8 evidence: pipeline-quality divergence detected by replan-check (per WSD architecture §6, Phase 3).

Each registered ALS subsystem subscribes to a subset of these (per its registration declaration). v1 active: S1, S2, S3, S4, S6, S8.

---

## 7. Update mechanism library — `mechanism.*`

L3 capacities implementing parameter-update strategies. Inputs: `(parameter_current_value, evidence_rows)`. Outputs: proposed new parameter value.

- **`mechanism.bayesian_update`** (`capacity:als:mechanism.bayesian_update`) — Bayesian conjugate update.
- **`mechanism.ema`** (`capacity:als:mechanism.ema`) — exponentially-weighted moving average.
- **`mechanism.beta_posterior`** (`capacity:als:mechanism.beta_posterior`) — Beta-posterior on success/failure observations.

Deferred to v2:

  - `mechanism.gradient_descent` — for neural parameters, gated on FOL #8 blob storage.
  - `mechanism.evolutionary_strategies` — for combinatorial structures.
  - `mechanism.bayesian_optimization` — for expensive fitness functions.
  - `mechanism.reinforce` — for policy generators.

Each ALS-registered subsystem declares per-parameter mapping: `parameter_iri → mechanism_iri`.

---

## 8. Failure-diagnosis capacities

Per WSD architecture §6 (Phase 6).

### 8.1 `analyze_failure_provenance`

- **IRI:** `capacity:diagnosis:analyze_failure_provenance`.
- **Inputs:** outcome record (failed task), provenance chain (per-step confidences, replan divergences, hard-failure indicators).
- **Outputs:** `list[(parameter_set_iri, blame_weight)]`.
- **Heuristic (v1):** blame proportional to `(1 - confidence) × (1 + divergence) × hard_failure_indicator`, normalized across all probabilistic steps in the run.
- **Determinism:** fixed function; no learned state internally. (The blame heuristic *coefficients* could be parameters in `learned-parameters` if we want the heuristic itself to learn; deferred to v2.)

### 8.2 `cross_validate_failure`

- **IRI:** `capacity:diagnosis:cross_validate_failure`.
- **Inputs:** `task_input`, `alternative_pipeline`.
- **Outputs:** comparison record (alternative outcome).
- **Optional;** runs only when compute budget allows + admin policy permits.

### 8.3 `request_human_diagnostic`

- **IRI:** `capacity:diagnosis:request_human_diagnostic`.
- **Inputs:** failure summary.
- **Outputs:** diagnostic signal (HITL response) or `None` if HITL unavailable.
- **Deferred to v2** unless UX work happens earlier.

---

## 9. L3 ADR-014 resolution — Monitors descriptive-only, L4 owns lifecycle

Per L3 capacity handoff §5 (current state, contested), ADR-014 describes Monitors as "descriptive only" but is contested against an alternative "Mini-minds (Monitors) start with the orchestrator" framing.

The WSD architecture (per WSD_ARCHITECTURE.md §3.5) settles on **descriptive-only with L4 owning lifecycle**:

  - L3 Monitor nodes carry their declarations (`state_datastate_iri`, `update_state_iri`, `subscribes_to`, etc.).
  - L3 does **not** start, stop, or schedule Monitors.
  - L4 reads Monitor declarations from L3 and orchestrates them: starts at task begin, stops at consolidation/abort, runs BSP turns invoking MSUR + update_state per Monitor.

**Action item for L3:**

  - Update ADR-014 status from "contested" to "settled (descriptive-only; L4 owns lifecycle)".
  - Document that Monitor declarations are read-only at L3 boundary; any state changes during execution live in L5 MM, not L3 graph.

---

## 10. L4 Push 2 acceptance — action contracts on L3 capacity registrations

Per L4 intelligence handoff (current) §4.2 / Push 2 (currently contested), the recommendation is to use action contracts (capacity-declared preconditions and effects) rather than per-plan generated predicates.

The WSD architecture **accepts Push 2**: every L3 capacity registration gains optional fields:

  - `precondition_iri: str | None` — IRI of a `capacity:signalling.*` predicate that must hold for invocation.
  - `effect_iri: str | None` — IRI of a `capacity:signalling.*` predicate that holds after invocation.

Both fields point to predicate-shaped capacities in a `capacity:signalling.*` family (TBD — coordinated change inside L3).

**Action items for L3:**

  - Extend `_CapacityBase` registration shape to include `precondition_iri` and `effect_iri` (both optional in v1; required for capacities used in pipelines that need replan-check validation).
  - Spec the `capacity:signalling.*` predicate family — predicate capacities take a state and return bool + diagnostic info.
  - Backward compatibility: existing registered capacities default to `precondition_iri=None` and `effect_iri=None` (skip contract checks).

This is required for replan-check's reflective role (per WSD architecture §6, Phase 3 — replan validates step expectations against actual state).

---

## 11. Monitor declaration shape extension

Per WSD architecture §3.5, the L3 Monitor node type gains fields beyond the existing `subscribes_to` / `emits` (per L3 handoff §3 — three node types: Capacity, Monitor, Adapter):

```python
@dataclass
class SCMSMonitorDeclaration(MonitorDeclaration):
    state_datastate_iri: str          # working state shape
    update_state_iri: str              # L3 capacity that applies resolved signal
    evaluator_method_iri: str          # from evaluator.* library
    combination_method_iri: str        # from combination.* library
    comparator_method_iri: str         # from comparator.* library
    # subscribes_to and emits_to inherited from MonitorDeclaration
```

These fields are populated at registration time. L4 reads them when orchestrating BSP turns.

**Backward compatibility:** existing Monitors (per the L3 vertical slice — the few Monitors shipped) retain their existing declaration shape. SCMS Monitors are a specialization of MonitorDeclaration; if L3 uses inheritance, this is non-breaking. If L3 uses a flat declaration, the new fields are optional with defaults.

---

## 12. Shared utility capacities (called by L2 importers)

Per L2 handoff §4.7, importers call into shared utility libraries that may be implemented as L3 capacities:

- **`sense_iri_align`** (`capacity:knowledge:sense_iri_align`) — converts cross-inventory sense IDs to canonical OEWN IRIs via SemLink graph. Reads SemLink role-graph.
- **`class_generalize`** (`capacity:knowledge:class_generalize`) — wraps the per-hierarchy `class.ancestors_*` capacities; computes ancestors in target hierarchy.
- **`metric_compute`** (`capacity:knowledge:metric_compute`) — dispatcher that invokes appropriate `metric.*` capacity given metric_type input.
- **`mwe_segment`** (`capacity:knowledge:mwe_segment`) — recognizes MWEs from FrameNet MWE lexical units + WordNet collocations. Reads lexicon graph.

These are L3 capacities by convention (matches MindsOS pattern of L3 holding fixed algorithms). L3 chat may opt to make some library functions instead — judgment call.

---

## 13. Coordinated implications across other layers

### L0 — Server

  - **`user_settings` table** read by L4 (which then conditions ALS subsystem-running per user). L3 doesn't read settings directly.

### L1 — Core

  - **`InterGraphEdge` primitive** used by class-generalization cross-system mappings; L3 ancestor-walk capacities traverse these edges when walking cross-system.
  - **Schema layer mechanism** used by L3 read patterns when querying lexicon (e.g., `iter_layer_edges("empirical")` per L1 handoff Change 2).

### L2 — Knowledge

  - **All capacities listed in this handoff are read-only over L2** (with one exception: ALS dream-time mining writes to `parameter-staging`, but that's L4-orchestrated, not direct L3-write).
  - **Shared utility capacities** (§12) are core machinery for L2 importers.
  - **Monitor declarations** read from L3 graph; L3 graph schema must support the extended Monitor shape.

### L4 — Intelligence

  - **L4 owns Monitor lifecycle** per §9. SCMS BSP turn pipeline composes L3 capacities listed here.
  - **MSUR pipeline** (L4) composes `signal_partition` + selected `combination.*` + `branch_instantiate` (hardcoded) + selected `evaluator.*` + selected `comparator.*` + `hypothesis_tag_emit` (hardcoded).
  - **ALS** (L4) composes `signal:*` capacities + `mechanism.*` capacities + validation capacities + `audit.*` capacities.
  - **Failure diagnosis pipeline** (L4) composes `analyze_failure_provenance` + optional `cross_validate_failure` + optional `request_human_diagnostic`.
  - **Action contracts** read by L4's replan-check at step boundaries.

### L5 — Mental Model

  - MSUR ledger lives in L5 MM during task execution; L3 capacities populate it via standard MM-instantiation patterns.
  - No L3 changes for L5 specifically.

---

## 14. Open questions for L3 chat

  1. **`capacity:signalling.*` predicate family shape** (per §10) — what's the input/output contract for predicate capacities? Booleans + diagnostic info is the obvious choice; structural shape needs spec.

  2. **MSUR helpers as L3 vs hardcoded in L4 pipeline** — current spec has `signal_partition` as L3, but `apply_independent`, `branch_instantiate`, `hypothesis_tag_emit` hardcoded in L4 MSUR pipeline. L3 chat may push back if it prefers all helpers as L3 capacities. The current decomposition (Option B from earlier design) is a tradeoff: variant-rich pieces (combination, comparator, evaluator) as method libraries; mechanical pieces hardcoded. L3 chat confirms or adjusts.

  3. **DataState shapes for v1 stub Monitors** — `frame-match`, `retrieval`, `cross-word` Monitors need their state DataStates designed. Defer to detail design, or spec basics now?

  4. **Shared utility capacities vs library functions** (per §12). Probably L3 capacities for consistency, but library functions are defensible.

  5. **Method library extensibility patterns** — admin adds new evaluator / combination / comparator / metric capacities. Discoverability mechanism (registry, naming convention, schema-validated)?

  6. **Action contract enforcement** — L4 calls precondition before invocation, effect after. What happens on contract violation? Hard error? Soft signal? Configurable?

  7. **ALS signal-source weighting per subsystem** — registration declares `signal_sources: list[(source_iri, weight)]`. Are weights themselves learnable (via ALS recursively)? Probably yes long-term; defer mechanism to v2.

  8. **Capacity IRI naming conventions** — proposed IRIs use `capacity:<category>:<name>` per L3 handoff. New categories surfaced here:
     - `capacity:agglomeration.*` (MSUR helpers, combination, comparator)
     - `capacity:scoring.*` (evaluator, metric)
     - `capacity:diagnosis.*` (failure diagnosis)
     - `capacity:als.*` (ALS signal sources, mechanisms)
     - `capacity:knowledge.*` (shared utilities for importers)
     - `capacity:wsd.*`, `capacity:fol.*`, `capacity:frame.*`, `capacity:retrieval.*` (subsystem-specific)
     L3 chat confirms or restructures.

  9. **Monitor instantiation for stub subsystems** — `frame-match`, `retrieval`, `cross-word` v1 stubs: do they actually run in v1 (with no-op behavior) or are they declared but inactive? Recommend declared-but-inactive: their declarations exist; SCMS BSP turn skips them when their `update_state` is null.

---

## 15. Phasing recommendation

  1. **Phase A — Method libraries + basic capacities.** Method library skeletons (evaluator, combination, comparator, metric, class-ancestors). At least one method per library to unblock SCMS Monitor instantiation. ~1-2 weeks of work.
  2. **Phase B — SCMS init capacities + active Monitors.** `wsd-init`, `fol-init`, `wsd-update`, `fol-update`, their `update_state` capacities. Stubs for `frame-match`, `retrieval`, `cross-word`.
  3. **Phase C — MSUR helper + L3 ADR-014 resolution + Monitor declaration extension.** Lays groundwork for L4 BSP turn pipeline.
  4. **Phase D — Action contracts.** L4 Push 2 acceptance; existing capacities annotated with preconditions/effects where relevant.
  5. **Phase E — ALS signal sources + update mechanism library.** Required by L4's ALS implementation.
  6. **Phase F — Failure-diagnosis capacities.** Required by L4's Phase 6 implementation.
  7. **Phase G — Shared utility capacities.** Required by L2 importers (can be in parallel with Phase B onward).

Phases A and G can ship in parallel. Phases C / D are short, can be combined. Phases E / F can be combined.

---

## 16. What this does NOT change

  - **L3 vertical slice already shipped is preserved.** Existing `text.*` capacities (tokenize, sentence_split, etc.), `pathfinding.*`, etc. retain semantics.
  - **L3 ADR-001 (capacities are fixed) is preserved.** All new capacities respect this — parameter learning happens via L2 `learned-parameters` read through context, not capacity self-modification.
  - **L3 ADR-006 (12 functional categories) is partially extended.** New categories surface (`agglomeration`, `diagnosis`, `als`, `knowledge` for shared utilities). L3 chat may renumber or rename to fit existing taxonomy.
  - **Existing CapacityLayer facade preserved.** All new capacities register through standard `CapacityLayer.add_capacity()` etc.
  - **Per-user FalkorDB graph naming preserved.**
  - **Session-based write API preserved.**
  - **REF_TYPES unchanged.**

---

## 17. Summary checklist for the L3 chat

When this handoff is implemented, L3 should have:

  - [ ] SCMS init capacities (`wsd-init`, `fol-init`).
  - [ ] SCMS Monitors declared (`wsd-update`, `fol-update`, plus stubs).
  - [ ] Per-Monitor `update_state` capacities.
  - [ ] MSUR helper `signal_partition`.
  - [ ] Method library `evaluator.*` (entropy_decrease + statement_reconciliation in v1).
  - [ ] Method library `combination.*` (bayesian + weighted_avg + log_pool + max_pool).
  - [ ] Method library `comparator.*` (max + weighted_sum + pareto + lexicographic).
  - [ ] Method library `metric.*` (resnik + pmi + conditional_probability).
  - [ ] Method library `class.ancestors_*` per registered hierarchy.
  - [ ] ALS signal-source capacities (S1, S2, S3, S4, S6, S8 in v1).
  - [ ] Update mechanism library `mechanism.*` (bayesian_update + ema + beta_posterior).
  - [ ] Failure-diagnosis capacities.
  - [ ] L3 ADR-014 marked settled (descriptive-only Monitors).
  - [ ] L4 Push 2 accepted: `precondition_iri` and `effect_iri` fields on capacity registration.
  - [ ] Extended Monitor declaration shape for SCMS Monitors.
  - [ ] Shared utility capacities for L2 importers.
  - [ ] `capacity:signalling.*` predicate family spec.

---

**End of handoff.**

When L3 design settles these changes, please update this document or write a follow-up handoff so the WSD design chat can absorb the final API.
