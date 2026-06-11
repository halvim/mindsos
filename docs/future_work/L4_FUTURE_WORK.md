# L4 Intelligence — Future Discussions & Work

**Date:** 2026-05-28 (last verified 2026-06-11)
**Status:** Living index of **L4 v2+ work**. ⚠️ **Historical framing notice:** §3 and §4 below were written pre-Chat-A and describe Chat A as the live resolution venue. **Chat A closed 2026-05-28** and the L4 substrate has since SHIPPED — `mindsos_intelligence` package landed Phase 46, orchestrator six-phase lifecycle + L4Dispatcher Phase 47, dream-cycle + crash-recovery Phase 48 (all confirmed). The v2+ backlog in §1/§2 remains live; §3/§4 are retained only as a closed-chat record.

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

## 3. Open questions for Chat A R0 — ✅ RESOLVED (Chat A closed 2026-05-28)

**Historical record.** These were meta-decisions Chat A had to clear at R0; all were resolved when Chat A closed. Full list in `CHAT_A_L4_BASELINE.md` §11.

| # | Question | Status |
|---|---|---|
| L4-Q1 | Should D32 (concurrency model) be R1 of Chat A in isolation? | User said "need more info" — answered in main response per Q3 |
| L4-Q2 | R0-PB-9 vs WSD ALS reconciliation | User said "need more info" — answered per Q4 |
| L4-Q3 | WSD-ALS vs FOL-plural-strategies — pick or coexist | User said "need more info" — answered per Q5 |
| L4-Q4 | L4 v1 LOC budget | User answered: no budget |
| L4-Q5 | WSD's 9 pending L4 ADRs — triage individually or batch-accept | Chat A R-round structure decides |

---

## 4. Chat A → downstream chat outputs expected — ✅ PRODUCED (Chat A closed 2026-05-28)

**Historical record.** All listed outputs were produced and consumed downstream. ⚠️ Note: `sense-correlations` below was subsequently **WITHDRAWN** as a standalone L2 role-graph (L2_CHAT_DECISIONS D-L2-2 — data lives in the lexicon empirical layer).

| Output | Consumer |
|---|---|
| Revised `docs/dev/l4_intelligence_design_notes.md` with picks on 40 decisions | All downstream chats |
| `docs/_workbench/CHAT_A_SETTLEMENT.md` per-decision rationale | Chat B (L5), Chat C (plan), WSD installation, FOL installation, skill-acquisition |
| Triage of WSD `pending_adrs/L4_intelligence.md` 9 ADRs (ratify / defer / reject) | WSD installation chat |
| L4 write-API-to-L5 contract | Chat B (input) |
| L4 concurrency model decision | All layers (cascades) |
| List of new L2 role-graphs L4 needs (~~sense-correlations~~ **withdrawn**, learned-parameters, parameter-staging, pending-promotions, capacity-gaps) | L2 chat / Chat C plan |
| List of new L3 capacities L4 needs (signal sources, mechanism.*, method libraries) | L3 chat / WSD installation |

---

## 5. Chat C closure routing (2026-06-02)

Chat C plan-authoring closed 2026-06-02 (`confirmation_docs/POST_PHASE_38_PHASE_MAP.md`). Routing of L4 items:

| Item | Routed to | Notes |
|---|---|---|
| L4-1 (cross-layer rewrite handler for L4 multi-tenant) | **L4-v2 follow-up chat** | Phase 49 confirmed 2026-06-09 — gating prereq cleared; chat now openable. |
| L4-2 (pause-and-resume) | **L4-v2 follow-up chat** | Push 5 deferred per Chat A R2. |
| L4-3 (predicate distillation) | **DROPPED** unless re-justified | Push 7 cut. |
| L4-4 (coherence dream intent re-evaluation) | **L4-v2 evaluation** | Push 3 cut from v1. |
| L4-6 (phase-loop as L3 orchestration capacity) | **L4-v2 evaluation** | If alt phase-loops emerge. |
| L4-7 (`decision.preempt_target` L3 capacity) | **L4-v2 evaluation** | v1 hardcoded "lowest-priority running." |
| L4-8 (unsupervised improvement avenue) | **L4-v2 evaluation** | Push 3 cut consequence. |
| L4-9 (Push 7 distillation reconsider) | **FOL_INSTALLATION_CHAT** | FOL may re-litigate. |
| L4-10 (pattern-conflict admin alert mechanism) | **WSD_INSTALLATION_CHAT** | ALS dream-aggregate surfaces. |
| L4-11 (TaskOutcome schema 3-valued decision) | **WSD_INSTALLATION_CHAT** | Authoring + integration. |
| L4-12 (per-task-pattern mapping-confidence threshold) | **Field SHIPPED Phase 43** (`mapping_confidence_threshold` on TaskPattern, `mindsos_knowledge/schemas/task_patterns.py`); ALS subsystem #4 refinement still **open** → WSD_INSTALLATION_CHAT. | — |
| L4-13 (multi-pattern conflict policy) | **WSD_INSTALLATION_CHAT** | UNRESOLVED_AMBIGUITY handler. |
| L4-14 (ALS `applies_after` topological ordering) | **WSD_INSTALLATION_CHAT** | ALS family scope. |
| L4-15 (Phase 1 5-step control flow spec) | **SHIPPED Phase 47** (`mindsos_intelligence/builtins/phase1_v0.py` + orchestrator `phase_1`) | Control flow shipped; concrete capacities (`process.*`, `derive_goal`, etc.) still ship in WSD installation. |
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

*End of L4_FUTURE_WORK.md. Last updated 2026-06-02 post Chat C plan-authoring closure; staleness pass 2026-06-11 (header + §3/§4 historical notices; L4-12/L4-15 shipped Phases 43/47).*
