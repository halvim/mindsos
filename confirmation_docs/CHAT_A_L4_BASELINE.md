# Chat A — L4 Design-Resolution Baseline

**Date compiled:** 2026-05-28 (updated for B2 framing + Q5 resolution + UC absorption)
**Status:** Pre-Chat-A baseline. Lists what is settled, what is contested, what WSD + FOL propose, and the unresolved decisions Chat A inherits.
**Required reading before Chat A opens:** This document + the source files cited inline.

---

## B2 framing — use cases as stress-test narratives, not pass/fail tests

Per user pick (2026-05-28), Chat A treats two case sets as **stress-test narratives**:

- `projects/wsd/source/WSD_USE_CASES.md` — 16 WSD architectural stress tests (UC-WSD-1 through UC-WSD-16).
- `docs/dev/use_cases_text_realm.md` — 7 NLU + code + cross-realm cases (UC-NLU-1/2/3, UC-CODE-1/2/3, UC-X-1) + 4 dreaming pipelines.

**These are NOT pass/fail tests.** They are concrete scenarios used for:
1. **Grounding picks.** "When you pick X for Decision D, here's the UC scenario where it matters — does your pick break it?"
2. **Negative-space mapping.** "These UCs assume Y. If Chat A rejects Y, name explicitly which UCs no longer apply."

Picks may invalidate UCs; Chat A documents which.

## Q5 resolution (2026-05-28)

- WSD's ALS adopted as L4 v1 architecture.
- FOL pushback #2 (plural strategies — gradient descent / ES / GA / Bayesian opt / REINFORCE as separate L3 capacities) **registered for FOL design chat**, not Chat A. ALS's `update_mechanisms` field anticipates this family expansion later.
- v1 mechanisms = WSD's stated set (ema, bayesian_update, beta_posterior). FOL strategies are L3 capacity-family expansion in v2+ under FOL installation.

---

## 0. How to use this document

This is the consolidated L4 baseline distilled from:
- `docs/dev/l4_intelligence_design_notes.md` (the 2026-04-21 design notes — pre-critique).
- 12 L4 ADRs (0091, 0098, 0101–0112) — all `Proposed`, none `Accepted` except 0091 + 0098 (which are L3-tagged).
- `HANDOFF.md` §3 — settled vs contested summary as of 2026-05-28.
- `projects/wsd/source/coordinated_change_L4_intelligence_and_als.md` — WSD's L4 ratification picks + new architecture proposals.
- `projects/wsd/source/pending_adrs/L4_intelligence.md` — 9 §A pending ADRs.
- `projects/fol/source/HANDOFF_latest.md` §2-3 — FOL's settled vs contested + 13 pushbacks.
- `projects/fol/ANALYSIS.md` + `projects/wsd/ANALYSIS.md` — sister-project intake triage.

Chat A inherits everything here as background; it does not re-derive.

---

## 1. Settled — Chat A inherits, doesn't re-litigate

These are positions that hold under skeptical pass and are confirmed by both the original L4 design notes AND the post-critique HANDOFF.md §3.1.

### 1.1 Lifecycle and tenancy
- One `IntelligenceLayer` instance per live user session.
- Owned by server's per-user context.
- Constructor: `IntelligenceLayer(session, knowledge=kl, capacity=cl)`.
- Methods: `start()`, `stop(mode="pause"|"abort")`, `enqueue(task)`.
- **No Global L4.** All learned state lives in L2 (Global + Local split).
- Per ADR-0101.

### 1.2 Layer isolation
- L4 has no upward imports.
- L4 is sole writer to L5.
- L4 is sole writer to the five upper-layer L2 role-graphs: `memories`, `promoted-pipelines`, `task-patterns`, `problem-trace`, `capacity-state`.
- Per ADR-0010.

### 1.3 Confidence topology
- Pipeline-level confidence on `promoted-pipelines` records, keyed by `(pipeline, task_type)`.
- Per-run output confidence on MM root composite.
- **No per-capacity confidence anywhere.** Violates L3 fixed-not-learned (ADR-0084).
- Per ADR-0094.

### 1.4 Plan-runs first-class
- `PlanRun` is a `CompositeInstance` inside the MM with `status`, timestamps, `triggered_by`.
- MM root holds `current_plan_run_id`.
- Replan = new plan-run (transition `running → aborted_for_replan` + spawn fresh).

### 1.5 Capacities are fixed
- No internal versioning.
- IRI presence in active Global L3 is the entire dependency check.
- Per ADR-0084.

### 1.6 Promotion topology
- Local pipeline using Local capacities cannot be Global-promoted until deps are also promoted.
- `PromotionProposal` builder shape settled.
- Per ADR-0111.

### 1.7 L3 surface L4 consumes
- `cl.invoke()`, `cl.start_resident()`, `cl.stop_resident()`, `cl.active_subscriptions()`, `cl.problem_trace`, `cl.iter_constraints()`.
- CONSTRAINT edges to respect at dispatch: `MUTUALLY_EXCLUSIVE`, `MANDATORY_BEFORE`, `REQUIRES_APPROVAL`, `RATE_LIMIT`, `REQUIRES_L2_VERSION`.

### 1.8 L4 → L5 → L2 memory pattern
- L4 writes to L5 continuously during a task (not just at end).
- Retention is the default on task completion.
- Consolidation: L4 freezes MM → writes to L2 `memories` role-graph → releases L5 live instance.
- Failure recording: thin `problem-trace` entry via `capacity:trace` + `ref:problem_trace` pointer on MM root.
- Per ADR-0098, ADR-0096.

### 1.9 L2/L3/L4/L5 contract
- L3 capacities READ L2 freely.
- L3 capacities never WRITE L2 directly. **Only L4 writes L2.**
- L3 capacities never modify L3.
- L4 modifies its own state (learned confidences, strategy preferences, promoted-path library) and writes L2.
- L5 is populated exclusively by L4.

---

## 2. The 7 critique pushes (contested) + WSD + FOL picks

The 2026-04-25 critique of the 2026-04-22 L4 architecture produced 7 pushes. The original architecture is captured in ADRs 0101–0112. WSD has explicit ACCEPT picks on 6 of 7. FOL has independent recommendations on #1, #2, #5.

### Push 1 — Meta-pipeline-everywhere
**Original (ADR-0102):** 6 default meta-pipelines composed of L3 capacities — planning, signal-triage, replan-check, confidence-composition, promotion-proposer, attention-score.
**Critique:** Collapse to 2 (planning + per-run confidence-composition); hardcode the other 4 in L4 Python.
**WSD pick (§3.5):** PARTIAL ACCEPT. Hardcode attention-score composition, signal triage, replan-check predicate dispatch, promotion-proposer dependency walking, quiescence detection, sufficient-predicate evaluation. Keep MSUR + SCMS BSP turn as L4 pipelines (admin-authored, ship v1). **Net: still 2 admin-authored L4 pipelines but with much specific scope.**
**FOL pick:** Not directly addressed.
**Chat A decision needed:** Accept WSD's PARTIAL or take a different position?

### Push 2 — Replan-check predicate
**Original (ADR-0104):** Hand-wavy fast-path / deep-check distinction.
**Critique:** Use capacity-contract predicates (`precondition_iri` + `effect_iri` on L3 capacity registrations).
**WSD pick (§3.2):** ACCEPT. Action contracts on L3.
**FOL pick:** ACCEPT-recommend.
**Chat A decision needed:** Ratify. But: this changes the L3 capacity registration contract — L3 needs a Phase-30+ amendment. Coordinate with L3.

### Push 3 — Coherence dream loop
**Original (ADR-0110):** GAN-analogous 4th dream intent (generator vs critic).
**Critique:** Cut from v1; ship 3 intents only (maintenance, exploration, retry).
**WSD pick (§3.1):** ACCEPT cut + substitute with ALS (Audited Learning Subsystem). See §3 below.
**FOL pick (pushback #2):** Coherence Loop = plural strategies (gradient descent / ES / GA / BO / REINFORCE), each its own L3 capacity. L4 picks based on parameter-space shape. **Different from WSD's ALS substitute.**
**Chat A decision needed:** Cut Push 3. But WSD and FOL disagree on the REPLACEMENT. Chat A picks ALS or plural strategies or both.

### Push 4 — Per-plan assumption/expectation
**Original (filed as future-plan Entries 2+3 candidates for v1).**
**Critique:** Reframe as action contracts on L3 capacities; drop per-plan generation.
**WSD pick:** Subsumed under Push 2 / Push 7.
**Chat A decision needed:** Drop, subsumed by Push 2.

### Push 5 — Pause-and-resume
**Original (ADR-0112):** In v1 scope (~300 LOC).
**Critique:** Defer to post-v1; abort-on-logout in v1.
**WSD pick (§3.3):** ACCEPT defer. v1 ships `mode="abort"` only. `stop(mode="pause"|"abort")` signature settled; v1 server only invokes `mode="abort"`.
**FOL pick:** ACCEPT-recommend.
**Chat A decision needed:** Ratify defer.

### Push 6 — Four-tier preemption
**Original (ADR-0103):** Tiers (CRITICAL > FOREGROUND > BACKGROUND > DREAM) + learnable coefficients (sunk_cost_bonus, interruption_cost).
**Critique:** Keep tiers; hardcode preemption (FIFO + hysteresis).
**WSD pick (§3.4):** ACCEPT. `capacity:scoring` family doesn't need `sunk_cost_bonus` or `interruption_cost` capacities.
**Chat A decision needed:** Ratify.

### Push 7 — Predicate distillation
**Original:** Proposed mechanism.
**Critique:** Drop entirely; LLM verdicts not stable enough to distill.
**WSD pick (§3.6):** ACCEPT drop. No `predicate-corpus` role-graph, no distillation dream intent.
**Chat A decision needed:** Ratify drop.

### Push 8 (unlisted) — Signal-thread correctness hazard
**Concern:** Single-threaded orchestrator + synchronous L3 invocations means CRITICAL signals are invisible during long-running L3 calls.
**Options:**
- (a) Weaken CRITICAL semantics ("high-priority at next yield").
- (b) Add signal-triage worker thread (~100 LOC + test).
**WSD pick:** Not addressed. ADR-0103 cost section notes "no true parallelism (v1 scope; ThreadPoolExecutor deferred to v1.5)."
**Chat A decision needed:** Pick (a) or (b) explicitly. Today's implicit pick is (a) by silence; should be made explicit.

---

## 3. WSD's L4 architectural additions (NOT just push resolutions)

WSD's `coordinated_change_L4_intelligence_and_als.md` proposes substantial new L4 machinery beyond the 7 pushes. **These are the load-bearing scope decisions for Chat A.**

### 3.1 ALS — Audited Learning Subsystem
**Purpose:** System-wide trainable-parameter learning infrastructure. Replaces the coherence loop.
**Subsystem registration contract (per §4.2):** parameter_set_iri, signal_sources (list of `signal:*` L3 capacities + weights), update_mechanisms (per-parameter mapping to `mechanism.*` L3 capacities), validation_methods (V1 gold accuracy, V2 calibration ECE/Brier, V3 drift), audit_policy (`auto-apply | batched-summary | individual-review`), eligible_audit_scopes (subset of `{local, global}`).
**v1 registered subsystems (per §4.3):** 9 listed — WSD candidate-scorer, FOL rule confidences, `promoted-pipelines` confidence updates, pipeline-finding parameters, task-shape recognition priors, goal verification thresholds, class generalization materialization policy, per-hierarchy class-generalization weights, `sense-correlations` Track A.
**Two-track training (§4.4):** Track A low-risk auto-applied; Track B high-risk through live-stage → dream-aggregate → validate → audit-queue → apply.
**Local → Global promotion (§4.5):** Admin-triggered aggregate cycle.
**User-as-Local-admin (§4.6):** L4 reads per-user training preferences from L0 `user_settings` at start of every dream cycle.
**Three audit policies (§4.7):** `auto-apply` / `batched-summary` / `individual-review`. User can override declared policy to more-conservative but not less-conservative.
**Storage:** new L2 role-graphs — `parameter-staging` (Local), `pending-promotions` (Local + Global). Existing `learned-parameters` for converged snapshots.

**Chat A decision:** Adopt ALS as L4 v1 architecture? If yes, this absorbs Push 3's "what replaces coherence loop" question. If no, what replaces it?

### 3.2 MSUR pipeline — Multi-Source Update Resolver
**Purpose:** L4 pipeline that resolves multiple incoming signals into a single update, with branching for contradictions.
**Inputs (§5.2):** `(current_state, pending_signals, evaluator_method_iri, combination_method_iri, comparator_method_iri)`. **Outputs:** `(resolved_signal, hypothesised_emissions)`.
**Steps (§5.2):** signal_partition → apply independent signals → apply reinforcing groups via combination_method → branch contradictory groups → evaluator per thread → comparator → emit hypothesised_emissions for losers → return resolved_signal.
**No branch budget in v1 (§5.3).**
**MSUR ledger lives in L5 MM during execution (§5.4); persistence beyond task completion is v2.**

**Chat A decision:** Ratify MSUR as L4 v1 pipeline? Or defer?

### 3.3 SCMS BSP turn pipeline
**Purpose:** L4 pipeline driving the continuous Sense Confidence Monitoring Subsystem.
**Per-turn structure (§6.2):** Phase 1 RESOLVE (per Monitor, L4 reads Monitor's declaration + invokes MSUR pipeline) → Phase 2 APPLY (invoke Monitor's update_state, write new_state to MM) → Phase 3 BROADCAST (route new state to subscribers) → Phase 4 RECEIVE (queue incoming signals) → Quiescence check (zero broadcasts = quiescence flag).
**SCMS lifecycle (§6.3):** L4 owns Monitor lifecycle (start when text-handling task begins, run until quiescence, stop on success/failure).
**Convergence (§6.4):** Pair-wise quiescence + system-wide quiescence + L4 evaluates sufficient-predicate after quiescence.
**No SCMS compute budget (§6.5).** L4's task-lifecycle handles runaway.

**Chat A decision:** Ratify SCMS as L4 v1 pipeline? Note this depends on the C-L3-2 monitor-lifecycle-ownership reframe (Phase 31 shipped L3-owned residents; WSD wants L4-owned monitor lifecycle).

### 3.4 Six-phase task lifecycle
**Replaces the 3-step task-to-pipeline flow (per L4 design notes 2026-04-23) with 6 phases:**
- Phase 0 Arrival — `task_input` + `session_context`.
- Phase 1 Task interpretation — `recognize_task_shape`, `derive_task_goal`.
- Phase 2 Pipeline determination — `translate_goal_to_datastates`, `check_path_exists`, `lookup_known_pipeline`, `generate_pipeline`, `select_pipeline`, `validate_pipeline`.
- Phase 3 Pipeline execution — `execute_step`, `replan`, `record_replan`, `handle_step_failure`, `detect_mid_execution_gap`. SCMS runs continuously inside text-handling steps.
- Phase 4 Goal verification — `check_goal_state_match`, `verify_goal_achievement`, `external_validation`.
- Phase 5 Outcome processing — `consolidate_outcome`, `consolidate_mm_to_memory`, `flag_capacity_gap`, `emit_signals_to_als`.
- Phase 6 Failure diagnosis (new) — `analyze_failure_provenance`, `cross_validate_failure`, `request_human_diagnostic`, `record_diagnostic_outcome`, `route_to_als`.

**Chat A decision:** Adopt six-phase lifecycle? Replace the 3-step flow? Keep both with a "simplified execution mode" for v1 testing (per WSD pending_adrs §A.8)?

### 3.5 Phase 6 — Failure diagnosis
**New L4 responsibility.** Runs only when Phase 4 returns false or external signal contradicts after consolidation.
**Uses inverse-confidence + replan-divergence + hard-failure-isolation heuristic.**
**Routes blame-weighted signals to ALS per-parameter-set.**
**Cross-validation by sub-path substitution (per WSD pending_adrs §A.5):** L4 substitutes individual capacity-edges with alternatives from L3 graph; re-runs; observes whether failure resolves.

**Chat A decision:** Adopt Phase 6 as v1? Per WSD §12 phasing, Phase G (Phase 6) depends on ALS skeleton (Phase B). v1 vs v2 disposition.

### 3.6 Replan-check dual-role spec (refines Push 2)
**Forward role:** goal-orientation check at every step boundary.
**Reflective role:** pipeline-quality validation using L3 capacity action contracts (`precondition_iri`, `effect_iri`).
**Replan record (§8.3):** `pre_state` + `expected_post_state` + `actual_post_state` + `divergence_magnitude` + `divergence_threshold_at_decision_time` + `decision` + `affected_capacity_iris`.
**Feeds S8 signal source.**

**Chat A decision:** Ratify dual-role + record schema.

### 3.7 New signal source S8 — Replan-divergence
**Pipeline-related ALS subsystems subscribe to S8.**

**Chat A decision:** Ratify if ALS is adopted.

### 3.8 `capacity-gaps` admin queue integration
**New L2 role-graph (Global).** L4 writes in Phase 2 (no path exists) + Phase 3 (mid-execution gap).
**Admin actions:** teach new capacity, add adapter, mark out-of-scope.

**Chat A decision:** Ratify if Phase-6/six-phase lifecycle adopted.

---

## 4. WSD's 9 pending L4 ADRs (need ratification or deferral)

From `projects/wsd/source/pending_adrs/L4_intelligence.md` §A:

| # | ADR | Notes |
|---|---|---|
| A.1 | Promotion-rule auto-selection with admin override | L3 ships 6 promotion-rule capacities A–F; L4 picks per case via heuristic; admin can override. Depends on L3-PROPOSAL-4 (not shipped). |
| A.2 | Dream priority schema (4 kinds) | End-user-edited priorities: `goal | metric | path-variant | cycle-weight`. New L2 schema. |
| A.3 | Per-level independent dream scheduling | Dream improvements at one composition level don't auto-propagate. Coverage tracking + dependent-path flagging. Depends on L2-PROPOSAL-1 (value-typed paths-of-paths). |
| A.4 | Data-gap vs capacity-gap classifier | L4 invokes L3 classifier at Phase 6; partitions ALS staging vs admin gap queue. |
| A.5 | Phase 6 path-segment blame attribution | Per-segment provenance + cross-validation by sub-path substitution. |
| A.6 | SCMS as L3 orchestration capacity invoked by L4 | SCMS becomes a single L3 capacity-edge in NLU paths. Internal BSP turn + MSUR composed inside. **Conflicts slightly with §3.3 above where SCMS is presented as L4-pipeline-owned.** |
| A.7 | Migration phase orchestration | L4 + L3 split for DS-modification migration (rollout policy, aggregate metrics, phase transition proposals). |
| A.8 | Six-phase task lifecycle (existing scope, retained) | Per §3.4 above. |
| A.9 | ALS full pipeline orchestration | Per §3.1 above. |

**Chat A triage needed:** ratify / defer-with-condition / reject each.

---

## 5. FOL's L4-relevant pushbacks

From `projects/fol/source/HANDOFF_latest.md` §3:

| # | Pushback | Severity | Chat A implication |
|---|---|---|---|
| 1 | Live training abandoned (dreaming-only) — REINSTATE live + dreaming | High | Affects ALS Track A/B design. Live writes never reach L2 directly (accumulate in L5, migrate after corroborating dream pass). |
| 2 | Coherence Loop as GA — REFRAME as oracle-supervised iterative learning with plural strategies | High | Conflicts with WSD's ALS substitute. Chat A picks. |
| 4 | Single `learned-parameters` role-graph — SPLIT into `learned-scalars` / `learned-policies` / `learned-models` | Medium | L2 role-graph design decision; affects ALS storage. |
| 5 | L5 holds populations — Add `training-runs` role-graph with checkpointed durability | Medium | Affects whether long training runs live in L5 or a separate L2 role-graph. **Coordinate with Chat B.** |
| 8 | No model-artefact storage story — Pick external blob store + IRI manifest pattern (S3/MinIO + content-addressed hashes) | High | L0/L2 infrastructure decision. Affects ALS Track B for large model artefacts. |
| 9 | `context` threading hand-waved — Typed `CapacityContext` schema | Medium | L3 + L4 contract decision. |
| 12 | No multi-user concurrency model specified | **High — must-decide-soon** | Chat A: single-process / multi-process / distributed. Constrains prover backends, `learned-parameters` write semantics, L4 process-memory placement. |
| 13 | Coherence Loop scope drift | Low | Process item. |

**Chat A decision on each.** Pushback #12 is load-bearing — affects everything below.

---

## 6. Inherited R0 picks from L4_L5_PLAN_NEXT_CHAT_PROMPT.md

From the 11-PB slate, the ones in Chat A scope:

- **R0-PB-1 (Plan vs design-resolution).** Pick (b) — Chat A IS the design-resolution-first chat. Plan-authoring is Chat C.
- **R0-PB-4 (FOL placement).** Pick (b) inherited — L4/L5 plan ships without FOL phases; settle 2 FOL-implied role-graphs (sense-correlations + learned-parameters).
- **R0-PB-9 (`sense-correlations` + `learned-parameters` disposition).** Pick (c) inherited — defer both. BUT: WSD ALS proposal absorbs both into v1. Chat A must reconcile: pick (c) defer OR pick (a) ship both per WSD. R0-PB-9(c) and WSD ALS are incompatible.
- **R0-PB-10 (Single-tenant vs multi-tenant L4 scope).** Pick (b) inherited — L4 v1 single-tenant only; L4-v2 rewrite handler in sibling follow-up.

---

## 7. L3/L4 boundary issues that must be resolved in Chat A

These are not from the 7 pushes but were surfaced by WSD's architectural proposals:

### 7.1 Monitor lifecycle ownership
- Phase 31 shipped `CapacityLayer.start_resident()` / `stop_resident()` / `_subscriptions` — **L3 owns resident lifecycle**.
- WSD `coordinated_change_L3` §9 + ANALYSIS-PB-A5 want **L4 to own Monitor lifecycle**.
- Supersession required, not addition. Affects Phase 31 ship.

### 7.2 Action contracts on L3 capacities
- Push 2 + WSD §3.2 + FOL #2 all ACCEPT.
- Capacity registration contract changes: optional `precondition_iri` + `effect_iri` fields.
- Affects all shipped L3 capacities + the registration API.

### 7.3 Capacities-as-hyperedges (WSD C-L3-1)
- WSD wants capacities-as-hyperedges with DataStates as nodes.
- Phase 27 shipped capacities-as-nodes.
- Architectural reframe; may exceed Chat A scope.
- **Suggested route: Chat A.5 or separate L1/L3 reframe chat.**

### 7.4 Method libraries (WSD coordinated_change_L3)
- WSD proposes 5 new method libraries: `evaluator.*`, `combination.*`, `comparator.*`, `metric.*`, `class.ancestors_*`.
- New L3 capacity families.
- Chat A decision: ratify families (vocabulary) without committing to all method capacities.

### 7.5 Signal sources S1–S8
- WSD `coordinated_change_L3` proposes 8 signal-source L3 capacities (S1 self-distillation, S2 gold anchor, S3 FOL disagreement, S4 ensemble agreement, S5 HITL, S6 task outcome, S7 reserved, S8 replan divergence).
- New L3 capacity family.
- Chat A decision: ratify family with v1 subset (which Si's ship v1) and which are deferred.

---

## 8. Compiled list of Chat A decisions

Comprehensive list. Chat A must produce a pick for each.

### Push resolutions (7)
- D1. Push 1 — meta-pipeline-everywhere disposition.
- D2. Push 2 — replan-check predicate via action contracts.
- D3. Push 3 — coherence dream loop cut + replacement choice (ALS vs plural strategies vs both).
- D4. Push 4 — per-plan assumption/expectation drop.
- D5. Push 5 — pause-and-resume defer.
- D6. Push 6 — four-tier preemption hardcoded.
- D7. Push 7 — predicate distillation drop.

### Push 8 (unlisted)
- D8. CRITICAL signal semantics: weak ("at next yield") or worker-thread.

### WSD L4 architecture (8)
- D9. ALS adopt or defer (load-bearing).
- D10. MSUR pipeline v1 ship.
- D11. SCMS BSP turn pipeline v1 ship.
- D12. Six-phase task lifecycle adopt (full or simplified).
- D13. Phase 6 failure diagnosis v1 or v2.
- D14. Replan-check dual-role + record schema.
- D15. S8 replan-divergence signal source.
- D16. `capacity-gaps` admin queue v1.

### WSD pending L4 ADRs (9)
- D17. Promotion-rule auto-selection with admin override.
- D18. Dream priority schema (4 kinds).
- D19. Per-level independent dream scheduling.
- D20. Data-gap vs capacity-gap classifier.
- D21. Phase 6 path-segment blame attribution.
- D22. SCMS as L3-orchestration-capacity OR L4-pipeline (reconcile §3.3 vs §A.6).
- D23. Migration phase orchestration.
- D24. Six-phase task lifecycle (existing scope, retained).
- D25. ALS full pipeline orchestration.

### FOL pushbacks (8)
- D26. Pushback #1 — Live training reinstate or stay dreaming-only.
- D27. Pushback #2 — Plural strategies (Coherence Loop reframe).
- D28. Pushback #4 — `learned-parameters` split into 3 or stay single.
- D29. Pushback #5 — `training-runs` role-graph.
- D30. Pushback #8 — Model-artefact storage (external blob store + manifest).
- D31. Pushback #9 — Typed `CapacityContext` schema.
- D32. Pushback #12 — Concurrency model. **Load-bearing.**
- D33. Pushback #13 — Process item.

### Inherited from R0 slate
- D34. R0-PB-9 reconciliation — `sense-correlations` + `learned-parameters` disposition. **Resolved 2026-05-28 per Q4: ship both as B (R0-PB-9 (a)) — WSD ALS adoption forces this.**
- D35. R0-PB-10 — single-tenant L4 v1 confirmation.

### L3/L4 boundary
- D36. Monitor lifecycle ownership (L3 vs L4) — Phase 31 supersession decision. **Routed to L1/L3 reframe chat per user Q2 — Chat A confirms direction only.**
- D37. Action contracts on L3 capacity registrations (subsumed under D2).
- D38. Capacities-as-hyperedges architectural reframe. **Routed to L1/L3 reframe chat per user Q2.**
- D39. Method libraries vocabulary ratification.
- D40. Signal sources S1–S8 v1 subset.

### D41–D49 — Surfaced by UC absorption (2026-05-28)

- D41. **Sufficient-predicate flexibility** per task-pattern — `verify_goal_achievement` must distinguish "honest preserved ambiguity (success)" from "uncertain (failure)." UC-WSD-3 forces.
- D42. **Document-scope SCMS** — what is "the document"? Per-sentence, per-paragraph, per-input. Monitor lifecycle is per-document, not per-task. UC-WSD-2 + UC-WSD-5 force.
- D43. **Multi-domain handling** — `domain_tag` on lexicon edges + per-domain class-generalization weights + V3 drift alarm. UC-WSD-10 forces. **L2 schema dependency.**
- D44. **Decision-precedent retrieval** — similarity function over admin decisions (metric-snapshot similarity + variant-change similarity). UC-WSD-13 forces. New L3 retrieval capacity.
- D45. **Per-segment provenance during execution** — `(confidence, replan-divergence, output-marker)` per executed path-segment on the MM. UC-WSD-15 forces. New MM schema.
- D46. **`unhandled_inputs` marker contract** on every L3 capacity. UC-WSD-14 forces. **Routed to L3 reframe chat per Q2 (changes universal L3 contract).**
- D47. **Path-mutability decision** — mutable-with-version-history vs immutable-with-successor-IDs. UC-WSD-16 forces. **Routed to L2 chat (promoted-pipelines schema decision).**
- D48. **DataState taxonomy expansion** — DS_FRAME_INSTANCES, DS_FOL_ATOMS, DS_NLU_FULL_ANNOTATION + code-realm DataStates from UC-NLU/CODE/X. UC-WSD-11 + UC-X-1 force. **Routed to L3 chat.**
- D49. **Calibration target as system-wide non-functional commitment** — ECE measured on gold set; V1+V2+V3 ALS validators mandatory. Every UC mentions calibrated output. Chat A makes explicit.

### D50 — Cross-realm DataState design

- D50. **Cross-realm NLU↔code DataState bridge** — UC-X-1 question-decompose → code-search-spec. Does one DataState bridge cleanly, or does it need a dedicated `code_search_spec` DataState + adapter? Force-tested by UC-X-1.

**Total: 50 decisions for Chat A** (D38 + D46 + D47 + D48 routed to L1/L2/L3 reframe chats per user Q2; Chat A confirms direction without ratifying the supersession).

---

## 9. Open meta-questions about Chat A itself

Original 5 meta-Qs; 4 of them now resolved by user picks.

1. **50 decisions is a lot for one chat.** Recommend clustering into rounds:
   - R1: **D32 (concurrency model)** — load-bearing for everything below. R1 in isolation per Q3 pick B (single-process multi-threaded).
   - R2: D1–D8 (7 pushes + Push 8 signal-thread).
   - R3: D9 (ALS adopt — already resolved Q5 = adopt) + D49 (calibration target as system-wide).
   - R4: D10–D16, D17–D25 (WSD architecture + pending ADRs).
   - R5: D26–D31, D34–D35, D39–D45, D50 (FOL pushbacks + remaining boundary + UC-surfaced + cross-realm).
   - R6 (confirm-only): D36, D38, D46, D47, D48 (routed-to-reframe-chats; Chat A confirms direction).
2. ~~D38 (capacities-as-hyperedges) may be out of scope.~~ **Resolved: routed to L1/L3 reframe chat per Q2.**
3. **D9 (ALS) is the single biggest scope-expansion decision.** ~~If accepted, scope balloons.~~ **Resolved Q5 = adopted.**
4. ~~R0-PB-9 vs WSD ALS conflict.~~ **Resolved Q4 = ship both per ALS adoption.**
5. ~~WSD architectural reframes may not belong in Chat A.~~ **Resolved: D36 + D38 + D46 + D47 + D48 routed to L1/L2/L3 reframe chats per Q2.**

## 9.5 UC-to-decision mapping (B2 grounding)

Each decision below is annotated with the UCs that stress-test it. "—" = infrastructure decision, no UC test.

| Decision | Stress-tested by |
|---|---|
| D1 Push 1 meta-pipeline | UC-WSD-6 (admin-authored MSUR/SCMS as L4 pipelines) |
| D2 Push 2 action contracts | UC-WSD-2/5 (replan reflective role uses precondition/effect) |
| D3 Push 3 coherence-loop cut | UC-WSD-6/7/12 (ALS substitutes) |
| D4 Push 4 per-plan assumption drop | — (subsumed by D2) |
| D5 Push 5 pause-and-resume defer | — (infrastructure) |
| D6 Push 6 four-tier preemption hardcode | — (infrastructure) |
| D7 Push 7 distillation drop | — (no UC depends on it) |
| D8 Push 8 signal-thread semantics | UC-WSD-5/11 (long SCMS runs, CRITICAL signals during prover/Frame execution) |
| D9 ALS adopt | UC-WSD-6/7/8/10/12/13 |
| D10 MSUR v1 | UC-WSD-2/3/5 |
| D11 SCMS BSP turn v1 | UC-WSD-2/3/5/11 |
| D12 Six-phase lifecycle | All UC-WSD; UC-NLU-1/2/3; UC-CODE-1/2/3; UC-X-1 |
| D13 Phase 6 v1 | UC-WSD-6/9/14/15 |
| D14 Replan-check dual-role | UC-WSD-2/5 |
| D15 S8 replan-divergence | UC-WSD-6 (ALS signal source) |
| D16 capacity-gaps v1 | UC-WSD-4/14; UC-NLU-1 (fallthrough to user) |
| D17 Promotion-rule auto-selection | UC-WSD-6/13 |
| D18 Dream priority schema | UC-WSD-12 |
| D19 Per-level dream scheduling | UC-WSD-16 + Dream-4 (analogy) |
| D20 Data-vs-capacity-gap classifier | UC-WSD-14 |
| D21 Phase 6 path-segment blame | UC-WSD-6/9/15 |
| D22 SCMS as L3 cap or L4 pipeline | UC-WSD-11 (composed NLU path) |
| D23 Migration phase orchestration | — (admin process; UC-tested indirectly via UC-WSD-13 promotion) |
| D24 Six-phase retained | — (same as D12) |
| D25 ALS full pipeline | UC-WSD-6/12 |
| D26 FOL #1 live training | — (FOL chat) |
| D27 FOL #2 plural strategies | — (FOL chat — Q5 registered) |
| D28 FOL #4 learned-params split | UC-WSD-6/12 (ALS storage) |
| D29 FOL #5 training-runs role-graph | — (Chat B if L5-bound) |
| D30 FOL #8 blob store | — (L0 infrastructure; UC-WSD-12 implied if neural models in dream variants) |
| D31 FOL #9 typed context | UC-WSD-11 (cross-capacity DataState handoff) |
| D32 Concurrency model | UC-WSD-5/11 (parallel SCMS + Frame execution) |
| D33 FOL #13 process | — |
| D34 sense-correlations + learned-params | UC-WSD-1/2/7/10 |
| D35 Single-tenant L4 v1 | — (deferred to v2) |
| D36 Monitor lifecycle (routed) | UC-WSD-2/3/5/11 (where Monitors fire) |
| D37 Action contracts | (subsumed D2) |
| D38 Capacities-as-hyperedges (routed) | — (architectural; affects all) |
| D39 Method libraries | UC-WSD-2 (combination.bayesian); UC-WSD-3 (comparator.max) |
| D40 S1–S8 v1 subset | UC-WSD-6/9/10/12 (signal-source coverage) |
| **D41 Sufficient-predicate flexibility** | UC-WSD-3 (preserved ambiguity as success) |
| **D42 Document-scope SCMS** | UC-WSD-2/5 (cross-sentence Monitors) |
| **D43 Multi-domain handling** | UC-WSD-10 |
| **D44 Decision-precedent retrieval** | UC-WSD-13 |
| **D45 Per-segment provenance** | UC-WSD-15 |
| **D46 unhandled_inputs contract (routed)** | UC-WSD-14 |
| **D47 Path-mutability (routed)** | UC-WSD-16 |
| **D48 DataState taxonomy expansion (routed)** | UC-WSD-11; UC-NLU-1/2; UC-CODE-1/2/3; UC-X-1 |
| **D49 Calibration target system-wide** | All UC-WSD; UC-NLU-1/2/3 (confidence outputs) |
| **D50 Cross-realm DataState bridge** | UC-X-1 |

---

## 10. Skeptical-reviewer pushbacks against the baseline

These are concerns about the baseline itself, surfaced before Chat A opens.

### PB-A — "Inherit WSD ACCEPT picks" silently absorbs WSD's L4 architecture
HANDOFF.md §3.3 describes WSD as having "explicit ACCEPT picks on 6 of 7" pushes. That's true but elides that WSD's coordinated_change_L4 ALSO proposes ALS + MSUR + SCMS + six-phase lifecycle + Phase 6 + S8 + audit policies. These are not push resolutions; they are new architecture. Chat A must ratify them in their own right, not absorb-by-implication.

### PB-B — Coherence loop "replacement" is contested between WSD and FOL
WSD substitutes ALS (system-wide audited parameter learning).
FOL pushback #2 substitutes plural strategies (gradient descent / ES / GA / BO / REINFORCE as separate L3 capacities, L4 picks).
**These are different mechanisms.** WSD's ALS is closer to "Track B audit infrastructure"; FOL's plural strategies is closer to "L3 capacity family for learning algorithms." They are NOT alternatives — they could coexist. But neither sister project says so explicitly. Chat A must reconcile.

### PB-C — Six-phase lifecycle conflicts with the 3-step flow documented in L4 design notes
L4 design notes (2026-04-23) document a 3-step task-to-pipeline flow: task-patterns → promoted-pipelines → adapt-or-generate. WSD's six-phase lifecycle is a different shape. Adopting six-phase supersedes the 3-step. The 3-step is already in `docs/dev/l4_intelligence_design_notes.md` and FOL §B6 + §B11 depend on it. If Chat A adopts six-phase, all 3-step references downstream need updating.

### PB-D — D32 (concurrency model) gates everything else but is buried
FOL pushback #12 is rated "High — must-decide-soon." Chat A should resolve D32 FIRST in R1 because:
- Prover backends (in-process vs subprocess) are FOL-load-bearing.
- `learned-parameters` write semantics differ under multi-process.
- L4 process-memory placement constrains MSUR ledger persistence.
- The Push 8 signal-thread question (D8) is a child of D32.
Recommend explicit R1 = D32 only, before anything else.

### PB-E — Per-user `IntelligenceLayer` (settled §1.1) plus single-process (likely D32 pick) means ALS is per-user
ALS Track A/B + Local/Global cycles assume a per-user collection model. Settled §1.1 already gives this. But ALS's `pending-promotions` Global cycle (§4.5) implies cross-user aggregation. Where does that aggregation run if L4 is per-user-session and there's no Global L4? **Implicit answer:** in the admin promotion machinery (L0 + admin tools). Should be made explicit.

### PB-F — Phase 31 monitor-lifecycle ownership is shipped code
Phase 31 already shipped `start_resident` / `stop_resident` on `CapacityLayer`. WSD C-L3-2 wants L4-owned. **Supersession means code changes**, not design changes. Either the WSD design is wrong (use what shipped) or Phase 31 needs amendment. Don't gloss this.

### PB-G — Action contracts on L3 (Push 2) changes the registration contract retroactively
Adding `precondition_iri` + `effect_iri` to L3 capacity registration changes Phase 27-33's shipped contract. Either all shipped L3 capacities need migration (adding these fields, possibly with null defaults) or the new fields are opt-in (back-compat). Either way: L3 code-touch is required, not just L4.

### PB-H — FOL pushback #4 (learned-parameters split) supersedes WSD ALS storage assumption
WSD's ALS treats `learned-parameters` as a single role-graph (§4.8). FOL pushback #4 says split into 3 (`learned-scalars` / `learned-policies` / `learned-models`). If split, WSD's ALS subsystem registration contract needs `parameter_set_iri` to encode which of the 3 role-graphs holds the parameters. **Reconciliation point.** Either WSD design absorbs FOL #4, or FOL #4 is rejected.

### PB-I — D38 (capacities-as-hyperedges) cascades to L1
WSD wants capacities-as-hyperedges; that requires L1 hyperedge primitive support (Phase 03+ shipped HyperEdge, so the primitive exists, but capacity-as-hyperedge semantics may need extension). This is L1 + L3 architectural — wrong scope for Chat A.

---

## 11. Chat A starting questions — RESOLVED 2026-05-28

All 6 starting questions resolved during pre-Chat-A scoping. Captured here for the record:

| Q | Question | Resolution |
|---|---|---|
| Q1 | Include WSD's L4 architectural additions? | **YES** — ALS / MSUR / SCMS / six-phase / Phase 6 in Chat A scope. |
| Q2 | Include architectural reframes (capacities-as-hyperedges, monitor lifecycle)? | **NO** — route to L1/L3 reframe chat. Chat A confirms direction only. |
| Q3 | D32 (concurrency model) R1 isolated? | **YES** — pick **B (single-process, multi-threaded with worker pool + signal-triage worker)**. R1 of Chat A confirms. |
| Q4 | R0-PB-9 vs WSD ALS conflict? | **Ship both** (R0-PB-9 (a)) per ALS adoption. `sense-correlations` + `learned-parameters` ship as L2 role-graphs in v1. FOL #4 split cascade handled in D28. |
| Q5 | WSD-ALS vs FOL-plural-strategies? | **ALS adopted; FOL plural-strategies registered for FOL design chat.** v1 mechanisms = ema, bayesian_update, beta_posterior. FOL strategies are L3 family expansion later. |
| Q6 | L4 v1 LOC budget? | **No budget** — use as many LOC as necessary. v1/v2 cuts driven by architectural cohesion, not LOC count. |

---

*End of CHAT_A_L4_BASELINE.md.*
