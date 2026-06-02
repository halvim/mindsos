# L4 Intelligence Layer — Updates from WSD Goal-Finalization

**For:** Resuming the L4 Intelligence design chat with goal-finalization decisions loaded.
**Source:** `WSD_GOAL_FINALIZATION_OUTPUT.md` (project root). All items here are PROPOSED — ratification happens in the L4 design chat.

## How to use this file

Paste this file into the L4 design chat as loading context. Then work through:
- **§A** — ADRs to formalize.
- **§B** — schema / code changes to land in L4 modules.
- **§C** — interfaces L4 must expose to other layers.
- **§D** — open sub-questions to resolve before implementation.

---

## §A — Required ADRs

### A.1 — Promotion-rule auto-selection logic with admin override

L3 ships six promotion-rule capacities A–F (L3-PROPOSAL-4). L4 picks per case; admin can override.

v1 default heuristic (conservative):

- If multiple non-dominated candidates exist on the metric set → pick **B (Pareto-frontier)**.
- If a single candidate clearly dominates incumbent on all primary metrics → pick **A (single-metric threshold)** with calibration metric primary.
- If sample volume is sufficient (≥ N candidates measured against ≥ K tasks) → promote to **D (statistical-significance)**.
- If shadow-deployment infrastructure is available and the path is high-traffic → pick **E**.
- For high-stakes or first-time-in-domain promotions → default to **F (admin-discretionary)**.

Admin override per case via minimal UI; override logged with rationale; may inform future auto-selection (post-v1 learning).

### A.2 — Dream priority schema (4 kinds)

End-users edit dream priorities; priorities are typed structured objects:

- `kind`: one of `goal`, `metric`, `path-variant`, `cycle-weight`.
- `target`: depends on kind.
  - `goal` — task pattern or DS endpoint to optimize against.
  - `metric` — metric ID + direction (maximize/minimize).
  - `path-variant` — path ID or path family to generate variants of.
  - `cycle-weight` — fraction of dream cycles allocated to this priority.
- `priority_value`: numeric weight relative to other priorities.
- `owner`: user (Local) or admin (Global).
- `expires_at` (optional): time-bounded priorities.

Multiple priorities coexist; dream scheduler weights them when allocating cycles.

### A.3 — Per-level independent dream scheduling

Under value-typed paths-of-paths (per L2-PROPOSAL-1), dream improvements at one composition level do not auto-propagate to higher levels. L4's dream scheduler:

- Maintains a "dream coverage" view across composition levels.
- Allocates cycles across levels per user/admin priorities.
- After a sub-path is improved, can flag dependent paths as candidates for next-cycle recomposition (advisory, not automatic — admin or user opts in to recompose).

### A.4 — Data-gap vs capacity-gap classifier

UC-WSD-14 distinguishes:

- **Data gap** — capacity exists but lacks training (similar inputs in past produced confident output; this case is an outlier; markers absent).
- **Capacity gap** — no operation exists for this concept type (capacity emits `unhandled_inputs`; similar inputs all produced same marker over multiple runs).

L4 invokes the classifier (itself an L3 capacity) at Phase 6, consuming (failure provenance, capacity-output markers, similar-input outcome history) → (gap-kind: data | capacity, supporting evidence).

ALS staging and capacity-gap admin queue partition by classifier output.

### A.5 — Phase 6 path-segment blame attribution

Under capacity-graph + paths-as-edge-sequences, blame attribution is at path-segment granularity (specific capacity-edges in the executed path):

- Walk the executed path; per-segment provenance includes confidence, replan-divergence, output markers.
- Heuristic blame share: `(1 - confidence) × (1 + divergence)` per segment.
- **Cross-validation by sub-path substitution:** L4 substitutes individual capacity-edges along the path with alternatives from the L3 capacity graph; re-runs; observes whether failure resolves. Substitution that fixes the failure localizes blame.
- Routes signals to the offending capacity's ALS lane only — no cross-contamination of unrelated capacities.

### A.6 — SCMS as L3 orchestration capacity invoked by L4

SCMS is an L3 capacity-edge:

- Source DS: initial sense candidates + initial FOL atoms + initial frame elements (composite or hyperedge).
- Target DS: refined versions after pair-wise quiescence.
- Internal behavior: BSP turn execution, monitor invocation, MSUR resolution (all L3 sub-capacities composed inside).

L4 invokes SCMS as a single capacity edge in NLU paths.

### A.7 — Migration phase orchestration (pipeline eligibility + aggregate monitoring)

DS-modification migration (per L1-PROPOSAL-3) splits responsibility:

- **Capacity-level (L3):** consuming capacities emit per-invocation `conflict-marker`; path executor reads `DS.fallback` and uses predecessor form for that invocation.
- **L4-level (this proposal):**
  - **Pipeline eligibility for coexistence-DSes.** At pipeline-run start, L4 inspects whether any DS in the pipeline's edge sequence is in coexistence; consults rollout policy (admin-set; e.g. "10% of qualifying runs use DS2', 90% use DS2"); decides which version this run targets. Logged.
  - **Aggregate fallback monitoring.** L4 aggregates `conflict-marker` frequency, ECE drift, FOL-contradiction-rate, gold-set drift, downstream task failure rate across rollout. Surfaces aggregate metrics in admin UI.
  - **Phase transition decisions.** When aggregate fallback frequency stays below threshold for N cycles or M tasks, L4 proposes Phase 3 deprecation. When fallback frequency exceeds rollback threshold, L4 proposes rollback. Admin approves either.

Capacity-level + L4-level decisions are explicitly **complementary**, not competing.

### A.8 — Six-phase task lifecycle (existing handoff scope, retained)

L4 owns the six-phase lifecycle:

1. Task interpretation (`recognize_task_shape`, `derive_task_goal`).
2. Pipeline determination (`translate_goal_to_datastates`, `check_path_exists`, `lookup_known_pipeline`, `select_pipeline`, `validate_pipeline`).
3. Pipeline execution (with replan steps + SCMS BSP turns when applicable).
4. Goal verification (`check_goal_state_match`, `verify_goal_achievement`).
5. Outcome consolidation (`consolidate_outcome`, `consolidate_mm_to_memory`, `emit_signals_to_als`).
6. Failure diagnosis (Phase 6 — `analyze_failure_provenance`, `cross_validate_failure`, `route_to_als`).

Plus a simplified execution mode for v1 testing (admin invokes a path directly with given input; path runs; audit captured) alongside the full lifecycle.

### A.9 — ALS full pipeline orchestration

L4 orchestrates ALS with all six signal sources:

- S1 self-distillation
- S2 gold anchor
- S3 FOL disagreement
- S4 ensemble agreement
- S6 task outcome
- S8 replan divergence

Plus dream-fan-out (multiple variants per cycle, each maximizing different metrics) + multi-metric validation gates + admin-panel review + versioned apply.

---

## §B — Required schema / code changes in L4 modules

### B.1 — L4 promotion-rule selector

- Module: promotion-rule auto-selector.
- Inputs: (promotion-candidate context, available rules, current admin policy preferences).
- Output: chosen rule capacity ID.
- Default heuristic implementation per A.1.
- Admin-override hook (via L0 admin UI); logs rationale.

### B.2 — Dream scheduler

- Reads dream-priority schema from L2.
- Allocates cycles across composition levels + priorities.
- Per-cycle: pick path(s) to dream over; generate variants (capacity substitutions); validate against multi-metric gates; stage in `pending-promotions` for admin panel.
- Per-level coverage tracking.

### B.3 — Data-vs-capacity-gap classifier invocation

- L4 invokes the classifier (L3 capacity) at Phase 6.
- Routes results: data-gap → ALS staging; capacity-gap → admin capacity-gap queue (L0 surface).

### B.4 — Phase 6 path-segment blame implementation

- Walk executed path → compute per-segment blame share.
- Cross-validation: substitute alternative capacity-edges from L3 registry; re-run; localize blame.
- Cross-validation budget management (TBD per A.5 / §D).
- Signal routing partitioned by capacity ID.

### B.5 — SCMS invocation

- L4 invokes SCMS as a single capacity-edge in NLU paths.
- Inputs: composite DS of (initial senses, initial FOL atoms, initial frame elements).
- Outputs: refined versions.

### B.6 — Migration phase orchestrator

- At pipeline-run start: coexistence-DS lookup; version decision per rollout policy.
- Aggregate metrics tracking for fallback frequency + drift.
- Phase-transition proposal generation; admin approval flow at L0.

### B.7 — Six-phase task lifecycle implementation

- Each phase as a sequence of L3 capacity invocations.
- Replan hooks at each phase boundary.
- Phase 6 triggered on goal-verification failure or external contradiction.
- Simplified execution mode: bypass interpretation/determination phases; run a chosen pipeline directly on admin-supplied input.

### B.8 — ALS pipeline orchestration

- Six signal-source aggregation in `parameter-staging`.
- Dream-cycle scheduler invokes recomposition; produces variant fan-out.
- Multi-metric validation gates: V1 (gold-set anti-regression), V2 (calibration anti-regression), additional anti-regression checks per metric.
- Admin-panel data preparation: per-variant metric matrix + changed-example diffs.
- Versioned apply on admin selection; SUPERSEDES edges written.

---

## §C — Interfaces L4 exposes to other layers

- **To L0:** admin panel data feeds (dream variants, capacity-gap reports, contradiction queue, audit views); admin override + decision rationale write-back.
- **To L3:** invoke capacities via path executor; access promotion-rule capacities; access SCMS orchestration capacity.
- **To L2:** read/write `learned-parameters`, `memories`, `task-patterns`, `promoted-pipelines`, `capacity-state`, `problem-trace`, `sense-correlations`, `world-axioms`.
- **To L1:** path-executor invocation with reproducibility.
- **To L5 (post-v1):** mental-model handoff for working-memory persistence per task.

---

## §D — Open sub-questions for L4 design chat

1. Promotion-rule auto-selection heuristic specifics — concrete thresholds for each branch.
2. Dream-priority conflict resolution — two priorities targeting competing metrics.
3. Default dream priorities — what does the system dream when no user has set anything.
4. Per-level dream scheduling default policy — depth-first vs breadth-first.
5. Capacity-gap classifier mixed-case handling (partial data + partial capacity gap).
6. Cross-validation budget for Phase 6 — substitution doubles compute; per-task or per-cycle limit.
7. Alternative-sub-path registry — minimum 2 alternatives per v1 NLU capacity for cross-validation.
8. Concrete migration rollout policies — random sampling / traffic-based / capability-flag-driven.
9. Aggregate metric thresholds — rollback-threshold and deprecation-threshold values.
10. Sticky-vs-mutable per-pipeline-run version choice during migration coexistence.
11. ALS multi-metric validation gate parameters (V1 / V2 thresholds).
12. Decision-precedent retrieval (UC-13) — similarity function over admin decisions.
13. Six-phase lifecycle vs simplified execution mode — when to use which from the admin UI.

---

**End of L4 updates.**
