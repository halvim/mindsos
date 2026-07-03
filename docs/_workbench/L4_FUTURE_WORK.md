# L4 Intelligence — Future Discussions & Work

**Date:** 2026-05-28
**Status:** Living index. Most L4 substance is in `CHAT_A_L4_BASELINE.md` and Chat A is the resolution venue. This doc tracks **post-Chat-A** L4 v2+ work + items routed away from Chat A.

---

## 1. v2+ follow-ups (post Chat A v1 ship)

| # | Item | Source | Owner chat |
|---|---|---|---|
| L4-1 | **Cross-layer rewrite handler** for L4 multi-tenant — when alice's draft node is promoted, L4 process-state refs to drafts must be rewritten (R0-PB-10 pick (b) defers this) | L4 handoff §11 (2026-04-26); R0-PB-10 | L4-v2 follow-up chat |
| L4-2 | **Pause-and-resume** — Push 5 deferred to post-v1 | Push 5; WSD §3.3 ACCEPT | L4-v2 chat |
| L4-3 | Predicate distillation — Push 7 dropped from v1 and v2 unless re-justified | Push 7 | Re-evaluated only if v3 surfaces need |
| L4-4 | Coherence dream intent — Push 3 cut from v1; ALS substitutes; revisit if v2 surfaces need for GAN-analogous training | Push 3 + WSD §3.1 | v2 evaluation |
| L4-6 | **Phase-loop as L3 orchestration capacity** — v1 has one phase-loop (six-phase) in L4 substrate. If v2+ wants alternative phase-loops (e.g., WSD §A.8 simplified execution mode promoted to first-class), phase-loop becomes L3 orchestration capacity and L4 picks via pipeline-finder. | Chat A R1 L4-vs-L3 boundary | v2 evaluation |
| L4-7 | **`decision.preempt_target` L3 capacity** — v1 hardcoded "lowest-priority running" cancel-target selection. v2 can promote to learnable L3 capability. | Chat A R1 D32 cancel-target | v2 evaluation |
| L4-8 | **Unsupervised improvement avenue (Push 3 cut)** — coherence dream loop cut from v1; ALS validators are supervised (gold accuracy). Dream-exploration intent partly covers. Watch if v1 shows missing unsupervised improvement matters. | Chat A R2 Push 3 | v2 evaluation |
| L4-9 | **Push 7 predicate distillation reconsider (FOL-chat-watch)** — distillation dropped in Chat A. FOL hasn't issued explicit drop verdict, only ACCEPT-recommend at HANDOFF_latest level. FOL chat may re-litigate. | Chat A R2 Push 7 | FOL design chat |
| L4-10 | **Pattern-conflict admin alert mechanism** — ALS dream-aggregate surfaces when 2+ task-patterns match same input at high confidence; admin merges/splits. | Chat A R3 teaching | WSD installation |
| L4-11 | **TaskOutcome schema (3-valued decision + DontKnowReason)** — `answer | dont_know | uncertain_answer` + 4 dont-know categories + mapping_confidence + output_confidence + suggested_action; full schema in CHAT_A_DECISIONS.md R3 extensions. | Chat A R3 "I don't know" | WSD installation |
| L4-12 | **Per-task-pattern mapping-confidence threshold** — declared at registration; ALS subsystem #4 refines via observation; global default 0.7. | Chat A R3 | WSD installation |
| L4-13 | **Multi-pattern conflict policy per-task-pattern** — when 2+ patterns match at comparable confidence, pattern declares response strategy (multi-output / pick higher / HITL / admin). | Chat A R3 UNRESOLVED_AMBIGUITY | WSD installation |
| L4-14 | **ALS subsystem `applies_after` field + topological apply ordering** — dependency edges between subsystems (e.g., mapping #4 applies after hint extraction #10). | Chat A R3 PB-R3-17 | WSD installation |
| L4-15 | **Phase 1 refactored 5-step control flow spec** — receive → process → extract_hints → derive_goal → map_to_task_pattern; hint set persisted on MM. | Chat A R3 Phase 1 refactor | WSD installation |
| L4-16 | **ALS subsystem #10 registration** — Hint extraction calibration; Track B batched-summary; depends on signal.task_outcome + signal.gold_anchor + signal.hitl. | Chat A R3 D32.5c + hint system | WSD installation |
| L4-17 | **Phase 6 cross-validation budget parameter** — `phase6_cross_validation_budget` (default K=2; validate top-K-blame segments only). Admin-tunable. | Chat A R4 D13 + D21 | WSD installation |
| L4-18 | **Dream priority schema (config-level, audit-tracked)** — typed structured object: `kind ∈ {goal | metric | path-variant | cycle-weight}` + target + priority_value + owner + expires_at. Per-user config + admin Global defaults. | Chat A R4 D18 | L0 chat + WSD installation |
| L4-19 | **Async Phase 6 v2 watch item** — v1 syncs Phase 6 on Phase 4 false; async Phase 6 (HITL contradiction after consolidation) deferred. | Chat A R4 PB-R4-9 | v2 evaluation |
| L4-20 | **Phase 6 blame ALS subsystem v2 candidate** — heuristic coefficients hardcoded v1 in `phase6.attribute_blame`; v2 may promote to ALS subsystem #11. | Chat A R4 PB-R4-12 | v2 evaluation |
| L4-21 | **FOL #1 L5-first watch item** — WSD writes evidence directly to L2 `parameter-staging` during exec; FOL prefers MM-first then migrate. Watch for FOL chat reopen. | Chat A R5 D26 PB-R5-1 | FOL chat |
| L4-22 | **Cross-task SCMS context v2** — v1 SCMS lifecycle is per-task (per D42); cross-task conversation memory defers v2. | Chat A R5 D42 | v2 evaluation |
| L4-23 | **Automatic domain detection v2** — v1 uses hint-driven + admin-declared domain per task-pattern; automatic detection v2. | Chat A R5 D43 | v2 evaluation |
| L4-24 | **L1/L3 reframe sequencing — prereq for WSD installation** — D36/D38/D46/D48 routed; reframe chat must complete before WSD installation begins (or at minimum the capacity-as-hyperedge + monitor-lifecycle reframes ratified). | Chat A R6 routing | Coordination |

---

## 2. Items routed away from Chat A

| # | Item | Source | Owner chat |
|---|---|---|---|
| L4-5 | **Capacities-as-hyperedges** + **monitor lifecycle ownership** reframes — routed to L1/L3 reframe chat per user Q2 | WSD C-L3-1 + C-L3-2 | L1/L3 reframe chat |

---

## 3. Open questions for Chat A R0

These are the meta-decisions Chat A must clear at R0 before R1 substance. Full list in `CHAT_A_L4_BASELINE.md` §11.

| # | Question | Status |
|---|---|---|
| L4-Q1 | Should D32 (concurrency model) be R1 of Chat A in isolation? | User said "need more info" — answered in main response per Q3 |
| L4-Q2 | R0-PB-9 vs WSD ALS reconciliation | User said "need more info" — answered per Q4 |
| L4-Q3 | WSD-ALS vs FOL-plural-strategies — pick or coexist | User said "need more info" — answered per Q5 |
| L4-Q4 | L4 v1 LOC budget | User answered: no budget |
| L4-Q5 | WSD's 9 pending L4 ADRs — triage individually or batch-accept | Chat A R-round structure decides |

---

## 4. Chat A → downstream chat outputs expected

This doc lists what Chat A is expected to produce so future chats know what they inherit.

| Output | Consumer |
|---|---|
| Revised `docs/dev/l4_intelligence_design_notes.md` with picks on 40 decisions | All downstream chats |
| `docs/_workbench/CHAT_A_SETTLEMENT.md` per-decision rationale | Chat B (L5), Chat C (plan), WSD installation, FOL installation, skill-acquisition |
| Triage of WSD `pending_adrs/L4_intelligence.md` 9 ADRs (ratify / defer / reject) | WSD installation chat |
| L4 write-API-to-L5 contract | Chat B (input) |
| L4 concurrency model decision | All layers (cascades) |
| List of new L2 role-graphs L4 needs (sense-correlations, learned-parameters, parameter-staging, pending-promotions, capacity-gaps) | L2 chat / Chat C plan |
| List of new L3 capacities L4 needs (signal sources, mechanism.*, method libraries) | L3 chat / WSD installation |

---

## 5. Chat C closure routing (2026-06-02)

Chat C plan-authoring closed 2026-06-02 (`confirmation_docs/POST_PHASE_38_PHASE_MAP.md`). Routing of L4 items:

| Item | Routed to | Notes |
|---|---|---|
| L4-1 (cross-layer rewrite handler for L4 multi-tenant) | **L4-v2 follow-up chat** | Opens after Phase 49 confirmed. |
| L4-2 (pause-and-resume) | **L4-v2 follow-up chat** | Push 5 deferred per Chat A R2. |
| L4-3 (predicate distillation) | **DROPPED** unless re-justified | Push 7 cut. |
| L4-4 (coherence dream intent re-evaluation) | **L4-v2 evaluation** | Push 3 cut from v1. |
| L4-6 (phase-loop as L3 orchestration capacity) | **L4-v2 evaluation** | If alt phase-loops emerge. |
| L4-7 (`decision.preempt_target` L3 capacity) | **L4-v2 evaluation** | v1 hardcoded "lowest-priority running." |
| L4-8 (unsupervised improvement avenue) | **L4-v2 evaluation** | Push 3 cut consequence. |
| L4-9 (Push 7 distillation reconsider) | **FOL_INSTALLATION_CHAT** | FOL may re-litigate. |
| L4-10 (pattern-conflict admin alert mechanism) | **WSD_INSTALLATION_CHAT** | ALS dream-aggregate surfaces. |
| L4-11 (TaskOutcome schema 3-valued decision) | **WSD_INSTALLATION_CHAT** | Authoring + integration. |
| L4-12 (per-task-pattern mapping-confidence threshold) | **Absorbed into L2-26** (now `mapping_confidence_threshold` field on TaskPattern; Phase 43) + WSD_INSTALLATION_CHAT for ALS subsystem #4 refinement. | — |
| L4-13 (multi-pattern conflict policy) | **WSD_INSTALLATION_CHAT** | UNRESOLVED_AMBIGUITY handler. |
| L4-14 (ALS `applies_after` topological ordering) | **WSD_INSTALLATION_CHAT** | ALS family scope. |
| L4-15 (Phase 1 5-step control flow spec) | **Phase 47** | L4 orchestrator ships the control flow; concrete capacities (`process.*`, `derive_goal`, etc.) ship in WSD installation. |
| L4-16 (ALS subsystem #10 registration) | **WSD_INSTALLATION_CHAT** | Hint extraction calibration. |
| L4-17 (Phase 6 cross-validation budget) | **WSD_INSTALLATION_CHAT** | Admin-tunable parameter. |
| L4-18 (dream priority schema config-level) | **WSD_INSTALLATION_CHAT** (admin config) + L0 admin-config absorbed per PB-T | — |
| L4-19 (async Phase 6 v2 watch) | **L4-v2 evaluation** | — |
| L4-20 (Phase 6 blame ALS subsystem candidate) | **L4-v2 evaluation** | — |
| L4-21 (FOL #1 L5-first watch item) | **FOL_INSTALLATION_CHAT** | — |
| L4-22 (cross-task SCMS context v2) | **L4-v2 evaluation** | — |
| L4-23 (automatic domain detection v2) | **L4-v2 evaluation** | — |
| L4-24 (L1/L3 reframe sequencing prereq) | **CLOSED** | Reframe chat closed 2026-06-01; Chat C resolved Phase 39-42 sequencing. |

---

## 6. Phase-1 interpretation seam + user-clarification (design converged 2026-07-02; core-owned, arc-driven)

A standalone **core** deliverable that brings forward the REAL Phase-1 "understand the
request" families **plus** a user-clarification mechanism — both currently shipped only as
v0 placeholders (`mindsos_capacity/builtins/phase1_v0.py`; `hint.global`→`{}`,
`decision.map_to_task_pattern`→`task-pattern:v0:trivial`). Driven by **arc-solver (mOS-AS)**
as the first consumer. **Core-owned per RULES §8** — the Phase-1 seam and the
hint/map/clarification mechanics are reusable core, consumed by arc-solver / WSD / FOL alike;
no consumer owns them. This **reattributes the core-mechanism half of L4-11 / L4-15 / L4-16
from "WSD installation" to core** (WSD still owns its own hint grammar + ALS calibration *as a
consumer*, not the mechanism). Design NOT yet drafted as ADRs or built. Full record: memory
`l4-phase1-seam-clarification-design`.

ADRs drafted 2026-07-02 (Proposed, design-only): **ADR-0195** (Feature A — seam)
+ **ADR-0196** (Feature B — `needs_input`). Two **decoupled** features (each shippable
independently):

**Feature A — pluggable interpretation seam.** A `Phase1Profile` bound at `L4Dispatcher`
construction, with one optional slot per Phase-1 step (`process` / `hint` / `derive_goal` /
`map`), each `None` → the shipped v0 placeholder. A real consumer supplies `hint` + `map`
(the only generic default is v0→trivial; no generic hints→pattern matcher at v1) and registers
its capacities / DataStates / task-patterns into its **Local** scope; core v0 + generic bodies
stay Global. Hints = **opaque dict + per-consumer schema** (NOT a core typed HintSet); a
`reference_kind` field sets the input DataState **type** so the shipped bipartite
`find_pipeline` (ADR-0156) composes `[resolve? → solve]` — no map-routing. `map` returns a
real registered `ROLE_TASK_PATTERNS` IRI + confidence (light resolve-check; never-trip
threshold hook).

**Feature B — user clarification.** `needs_input` modeled as a capacity **verdict** (sibling
to `dont_know`, reuses the existing dont-know propagation; works at any phase / any capacity).
Gate scope (block-whole-pipeline vs block-only-the-dependent-tail) is **emergent** from where
the clarified value enters the produces/consumes DAG — **no manual blocking flag**. Surfaced as
a **non-terminal `pending_confirmation` field** on `TaskOutcome` (the three terminal statuses +
consolidation are untouched; **no consolidation on that turn**). Payload contract =
`{question, missing DataState, choices: {label → ready-to-resubmit task_input}}`. **v1 wait
model = stateless re-submit** (caller folds the answer into a fresh request).

**MM-ownership principle (user, 2026-07-02): a PENDING (awaiting-input) task's state belongs
to that task's Mental Model.** Consequences:

- No separate global pending registry — parked tasks **are** suspended MMs (indexed by task id).
- The **continuation** model (deferred, below) = **retain + resume the specific task's MM**;
  the answer is injected into that MM and the lifecycle re-enters. This adds a new MM
  disposition **"awaiting-input / suspended"** alongside `active → consolidated (retained,
  Chat B D'1) → retired`. That is an **L5 MM-lifecycle addition** (see
  `L5_FUTURE_WORK.md` L5-NEW-19).
- **v1 stateless re-submit does NOT retain the MM** (it discards it; the re-submit builds a
  fresh MM) — so **v1 needs no L5 change**; MM-ownership + the new disposition land **only**
  with the deferred continuation.

**Near-term build scope (when ADRs are drafted):** two ADRs — ADR-A (interpretation seam) then
ADR-B (`needs_input` verdict + non-terminal outcome + re-submit contract), independently
shippable; `resolve` runs INSIDE interpretation as a `Phase1Profile` slot (interpret returns
`id8`-or-`needs_input`), so `needs_input` surfaces from the standalone interpret call —
`execution.run` halt+bubble (shared with `dont_know`) is the GENERAL/full-lifecycle path, **not
arc-blocking** (see §6.2, defer with L4-25); verify Local-only capacity registration + Local
`task-patterns` writes; version bump. arc-solver is the integration test (owns no core
component).

### 6.1 Deferred future-work rows

| # | Item | Routed to | Notes |
|---|---|---|---|
| L4-25 | **In-memory continuation for non-blocking clarification** — retain + resume the task's MM, run independent DAG branches while awaiting the answer, inject the answer, complete the dependent tail. | **L4-v2 follow-up** (realizes L4-2 pause-and-resume via MM retention) | Needs a re-entrant lifecycle at the clarification point + answer-injection API + parked-MM index + the "awaiting-input" MM disposition (L5-NEW-19). **Durable** variant blocked on the node-value→Falkor gap (PB-RT / L0-26); the **in-memory** variant is feasible independently. User pick 2026-07-02: v1 = re-submit, continuation **designed-not-built**. |
| L4-26 | **Generic hints→task-pattern matcher / multi-pattern disambiguation** — v1 requires each consumer to supply its own `map` body; a registry-driven matcher with `mapping_confidence` disambiguation across many patterns. | **L4-v2 / relates L4-13** | arc has one solve pattern; WSD/FOL will have many. |
| L4-27 | **`needs_input` in the TaskOutcome schema** — reconcile with L4-11 (`answer \| dont_know \| uncertain_answer`). `needs_input` is a **recoverable-by-user, non-terminal** disposition distinct from `uncertain_answer`. | **Folded into ADR-B** | — |
| L4-28 | **Clarification-turn audit trail** — v1's `needs_input` turn writes no Episode (no consolidation) → no durable record of the ask/answer. | **watch** | Revisit if audit needs it (a lightweight interaction-episode); reopens the MM-dict→Falkor flush question. |

### 6.2 arc-solver consumer confirmation (2026-07-02)

arc-solver (mOS-AS) confirmed the plan as first consumer (4 yes + 1 arc-Local policy).
Refinements folded into ADR scope:

- **Interpretation-only adoption.** arc adopts the seam for INTERPRETATION ONLY
  (`hint → map → [resolve?] → id8`). arc does NOT run `run_lifecycle` and needs NO core
  planning/execution catalogs — the arc-solve pipeline stays arc-authored (bespoke driver).
  The seam feeds `id8` into arc-solve's intake; that is the only coupling. **Consequences:**
  (i) the interpret surface must be callable STANDALONE (returns an interpretation result OR
  `needs_input`), decoupled from `run_lifecycle`; (ii) `resolve` runs INSIDE interpretation (a
  `Phase1Profile` slot), NOT as a core-executed pipeline step, so `needs_input` surfaces from
  the interpret call and the `execution.run` halt+bubble propagation is the general/full-
  lifecycle path, deferred (L4-25), not arc-blocking; (iii) interpretation-only means arc opts
  out of core MM / consolidation / Episode — no core L5 audit trail for arc runs (arc's choice).
- **Two hard constraints for the ADRs:**
  - (a) **Dispatcher-level body binding, no metagraph scope-mix (ADR-A).** `Phase1Profile`
    binds bodies at the DISPATCHER level (a selection over Global-v0 fallback), NOT by
    co-registering Global-DataStates + Local-capacities in one metagraph — the latter trips the
    existing scope-mix guard ("mixed Global-ds + Local-caps raises", already bit `arc_instance`).
    ADR-A states this explicitly in the seam contract.
  - (b) **`needs_input` trigger caller-controlled (ADR-B).** Core must NOT hardcode WHEN
    `needs_input` fires. The cold-start-only policy (fire while an arc-Local "ordering-
    established" marker is absent; the first confirm sets it; silent thereafter) is arc-Local
    policy inside the `resolve` body. Core ships the mechanism, not the trigger.
- **"Known" ≠ "enumeration exists."** The enumeration convention (train-split, 1-based) is
  authored Local L2 data; "ordering known" means the arc-Local marker is SET, not that
  enumeration data exists. Keep the two distinct in ADR-B.
- **`find_pipeline` soundness:** `[resolve → solve]` is linear + single-input → within the
  locked sound envelope (the unsound case is multi-input fold caps, N/A here). Noted for ADR-A.
- **Payload:** `choices:{label → task_input}` suffices — arc renders question + one candidate
  (`"#8 → 05f2a901" ⇒ {"text":"solve task 05f2a901"}`) + cancel. Keep the map shape
  (future-proofs ambiguous train-vs-eval indexing; pinned train-only now).

Loop CLOSED 2026-07-02 — nothing blocks ADR-A or ADR-B.

---

*End of L4_FUTURE_WORK.md. Last updated 2026-07-02 (added §6 Phase-1 seam + clarification + §6.2 arc-solver confirmation).*
