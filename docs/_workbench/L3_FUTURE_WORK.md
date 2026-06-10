# L3 Capacity — Future Discussions & Work

**Date:** 2026-06-01 (updated post L1/L3 reframe chat closure)
**Status:** Living index.

---

## 1. WSD-driven architectural reframes (routed here per user Q2)

| # | Item | Source | Owner chat / Status |
|---|---|---|---|
| ~~L3-1~~ | ~~**Capacities-as-hyperedges**~~ | WSD C-L3-1 | **CLOSED 2026-06-01 — ADR-0156 picks bipartite (Option A); not hyperedge. Phase X3 ship.** |
| ~~L3-2~~ | ~~**Monitor lifecycle ownership**~~ | WSD C-L3-2 | **CLOSED 2026-06-01 — ADR-0155 retires L3-side lifecycle plumbing. Phase X2 ship.** |

---

## 2. Capacity registration contract changes

| # | Item | Source | Owner chat |
|---|---|---|---|
| ~~L3-3~~ | ~~**Action contracts**~~ | Push 2; WSD §3.2 | **CLOSED 2026-06-01 — folded into ADR-0159 (`precondition_iri` + `effect_iri` fields)** |
| L3-4 | Typed `CapacityContext` schema with named accessors per capacity family | FOL pushback #9 | **PARTIAL — base ratified in ADR-0159 (9 fields + 4 Protocols); per-family extensions are downstream chat scope** |
| L3-5 | Capacity-level performance characterization (latency profile, applicability conditions, failure modes) — separate from confidence | FOL pushback #10 | Future L3 chat |
| ~~L3-22~~ | ~~**`unhandled_inputs` marker contract** — universal L3 contract change~~ | UC-WSD-14; CHAT_A_L4_BASELINE D46 | **CLOSED 2026-06-01 — ADR-0157 reverses universal; family-specific via 5-shape catalog. Phase X1 ship.** |
| L3-23 | **Alternative-sub-path registry per capacity type** — minimum 2 alternatives per v1 NLU capacity for Phase 6 cross-validation by substitution | UC-WSD-15; WSD `pending_adrs/L4_intelligence.md` §A.5 | WSD installation chat |
| ~~L3-24~~ | ~~**DataState taxonomy expansion**~~ | UC-WSD-11; UC-NLU-1/2/3; UC-CODE-1/2/3; CHAT_A_L4_BASELINE D48 | **CLOSED 2026-06-01 — ADR-0158 ratifies naming convention + 9 reserved v1 realms; concrete catalog deferred to WSD/code-skill/adapter chats. Phase X1 ship.** |
| L3-25 | **Decision-precedent retrieval** L3 capacity — similarity function over admin decisions (metric-snapshot similarity + variant-change similarity) | UC-WSD-13; CHAT_A_L4_BASELINE D44 | WSD installation chat |
| L3-26 | **Constraint-satisfaction over L2** as first-class path-finding capacity | UC-NLU-3 | L3 follow-up |
| L3-27 | **Abductive hypothesis generation** as own functional category vs implicit in `derivation:*` | UC-NLU-2; `use_cases_text_realm.md` Gaps §4 | L3 follow-up |
| L3-28 | **Code-realm capacity family** — `code.ast_parse`, `code.identifier_split`, `code.call_graph_walk`, `code.side_effect_detect`, `code.module_find`, `code.symbol_resolve`, etc. | UC-CODE-1/2/3; UC-X-1 | Code-skill installation chat (future) |
| L3-29 | **Structural-isomorphism** as shared `structural:*` capacity (vs per-realm) — Dream-4 analogy uses cross-realm | UC-CODE-3; `use_cases_text_realm.md` Gaps §7 | L3 follow-up |
| L3-30 | **Patch-generation capacity family** — `generation.code_*` for UC-CODE-2 minimal patch suggestion | UC-CODE-2; `use_cases_text_realm.md` Gaps §6 | Code-skill installation chat |
| L3-31 | **Side-effect analysis** placement — `code.*` or shared `analysis.*`? | UC-CODE-1; `use_cases_text_realm.md` Gaps §5 | L3 follow-up |
| ~~L3-32~~ | ~~**Phase 27–33 thread-safety audit**~~ | Chat A R1 D32.4 cascade | **CLOSED 2026-06-01 — absorbed into ADR-0156 Phase 27 audit deliverable (`confirmation_docs/PHASE_27_DONT_KNOW_AUDIT.md`). Phase X3 ship R0.** |
| L3-33 | **New L3 decision/scoring capacity family** — ~15-20 new capacities | Chat A R1 L4-vs-L3 boundary; Push 1 PARTIAL-ACCEPT-4 | WSD installation chat (catalog); ratified family contracts in L1/L3 reframe chat 2026-06-01 |
| ~~L3-34~~ | ~~**Capacity registration contract — `concurrent` + `inline` flags**~~ | Chat A R1 D32.4 + L4-vs-L3 boundary | **CLOSED 2026-06-01 — ADR-0159 ships 5 new `_CapacityBase` fields (`concurrent`, `inline`, `max_latency_ms`, `precondition_iri`, `effect_iri`, `reads_mm`). Phase X3 ship.** |
| ~~L3-35~~ | ~~**L3 capacity non-DataState return values**~~ | Chat A R1 L4-vs-L3 boundary | **CLOSED 2026-06-01 — ADR-0157 5-shape family rule catalog absorbs (OPTIONAL_RETURN / VERDICT / VALIDATION_RESULT / NO_DONT_KNOW). Phase X1 ship.** |
| L3-36 | **Predicate L3 capacity family** — 5–10 reusable predicates | Chat A R2 Push 2 | **Family contract RATIFIED 2026-06-01 (NO_DONT_KNOW, `inline=True`, `max_latency_ms ≤ 5`); concrete catalog deferred to WSD installation chat** |
| L3-37 | **ALS L3 capacity family** — `als.aggregate_subsystem` (orchestration meta-capacity) + ALS mechanism family (`mechanism.bayesian_update`, `mechanism.ema`, `mechanism.beta_posterior`) + ALS validator family (renamed: `validate.gold_accuracy`, `validate.calibration_ece`, `validate.distribution_drift`). | Chat A R3 D9.6 + D49 | WSD installation chat |
| L3-38 | **`pattern.extract_task_shape` capacity** — Method 4 enabler; observes pipeline execution + extracts task-shape features for admin-confirmed task-pattern registration. | Chat A R3 teaching methods | WSD installation |
| L3-39 | **`decision.classify_dont_know_reason` capacity** — replaces 2-way data-vs-capacity-gap classifier; 4-way + ambiguity: `NO_MATCHING_PATTERN`, `LOW_MAPPING_CONFIDENCE`, `PIPELINE_UNAVAILABLE`, `UNRESOLVED_AMBIGUITY`. | Chat A R3 "I don't know" + R4 D20 retirement | WSD installation |
| L3-40 | **Shape-indexing for fast Phase 1 pattern matching** — perf optimization; precompute hint→candidate-pattern indices at task-pattern registration. | Chat A R3 Phase 1 refactor | WSD installation |
| L3-41 | **`signal.task_outcome` enriched payload schema** — structured payload `{outcome, latency_ms, cost_tokens, output_quality_score, dont_know_occurred, ...}` under R3 binary-pipeline framework; single source serves multiple subsystems. | Chat A R3 PB-R3-18 | WSD installation |
| L3-42 | **`hint.*` L3 capacity family** — 20+ baseline hints + N domain-specific; ALL `inline=True` + `max_latency_ms ≤ 5`; admin extends per installation. Examples: `hint.has_question_mark`, `hint.detect_named_entities`, `hint.file_extension`, `hint.medical_terminology_present`. | Chat A R3 hint system | WSD installation |
| L3-43 | **`process.*` L3 capacity family** — domain-specific input processing (text, code, business-doc, multimodal-future); `process.dispatch` selects per input shape; step 2 of Phase 1. | Chat A R3 Phase 1 refactor | WSD installation |
| L3-44 | **`decision.derive_goal` capacity** — Phase 1 step 4; consumes structured_input + global hints; produces target DataState + intent description. | Chat A R3 Phase 1 refactor | WSD installation |
| L3-45 | **6 promotion-rule L3 capacities** — `promotion_rule.single_metric_threshold`, `.pareto_frontier`, `.composite`, `.statistical_significance`, `.shadow_deployment`, `.admin_discretionary`. ~50-100 LOC each. | Chat A R4 D17 | WSD installation |
| L3-46 | **`decision.select_promotion_rule` capacity** — chose promotion rule per case via WSD §A.1 heuristic; per R1 strict-line consistency; admin override. | Chat A R4 PB-R4-8 | WSD installation |
| ~~L3-47~~ | ~~**Typed CapacityContext base + family extensions**~~ | Chat A R5 D31 + PB-R5-7 | **CLOSED 2026-06-01 — base ratified in ADR-0159 (9 fields + 4 Protocols including `kl` + `cl` + `version_snapshot`); per-family extensions are downstream chat scope. Phase X3 ship.** |
| L3-48 | **`retrieval.by_admin_decision_similarity` capacity** — admin-aid precedent retrieval for UC-WSD-13; reads audit log via L0-20 query API; returns similar prior decisions; admin always re-decides (never auto-applies). | Chat A R5 D44 | WSD installation |
| L3-49 | **`adapter.*` capacity family (naming convention)** — cross-realm DataState bridges (e.g., `adapter.question_decompose_to_code_search_spec` for UC-X-1); each cross-realm task-pattern declares its bridge adapter. Standard L3 contract (not structurally distinct family). | Chat A R5 D50 | WSD installation + code-skill chat |

---

## 3. New L3 capacity families (WSD-driven)

| # | Item | Source | Owner chat |
|---|---|---|---|
| L3-6 | **5 method libraries** — `evaluator.*`, `combination.*`, `comparator.*`, `metric.*`, `class.ancestors_*` | WSD `coordinated_change_L3` §6 | Chat A (ratifies family vocabulary); WSD installation (ships method capacities) |
| L3-7 | **Signal sources** S1–S8 — self-distillation, gold anchor, FOL disagreement, ensemble agreement, HITL, task outcome, [reserved], replan divergence | WSD §9; WSD `coordinated_change_L3` | Chat A (decides v1 subset); WSD installation ships |
| L3-8 | **ALS `mechanism.*` capacities** — bayesian_update, ema, beta_posterior, etc. | WSD §4.2 | Chat A (decides v1 mechanisms); WSD installation ships |
| L3-9 | **SCMS init capacity** (`wsd-init`, `fol-init`) + Monitor capacities | WSD `coordinated_change_L3` | WSD installation |
| L3-10 | **MSUR helper L3 capacities** — `signal_partition`, etc. | WSD §5.2 | WSD installation |
| L3-11 | **Phase 6 failure-diagnosis capacities** — `analyze_failure_provenance`, `cross_validate_failure`, data-vs-capacity-gap classifier | WSD `coordinated_change_L3` §8; WSD `pending_adrs/L4_intelligence.md` §A.4 | Chat A (decides v1/v2); WSD installation |
| L3-12 | Promotion-rule capacities A–F | WSD `pending_adrs/L3_capacity.md` §A; L3-PROPOSAL-4 | Chat A (ratifies family); WSD installation |

---

## 4. FOL-driven L3 additions

| # | Item | Source | Owner chat |
|---|---|---|---|
| L3-13 | **Pluggable prover backends** behind `Prover` Protocol returning `ProofBound` + `unknown_within_bound` | FOL §2.1; B7 | FOL installation chat |
| L3-14 | `populate_negative_closure` capacity (formerly `populate_exception_closure`) | FOL §2.1; B5 | FOL installation chat |
| L3-15 | WSD decomposition — tokenization, lemma+POS, sense-inventory lookup, candidate-generator strategies, scorer strategies, confidence calibrator (all as separate L3 capacities) | FOL pushback #3; WSD `coordinated_change_L3` aligned | WSD installation (primary); FOL coordinates |
| L3-16 | **Plural learning strategies as L3 capacities** — `capacity:coherence_loop:<strategy>` for gradient descent / ES / GA / BO / REINFORCE | FOL pushback #2 | Chat A (decides per Q5); WSD/FOL installation ships per-strategy |

---

## 5. Phase 38 carry-forwards (L3-bucket)

| # | Item | Source | Owner chat / Status |
|---|---|---|---|
| L3-17 | Falkor-backed L3 bootstrap + state-file serialization | PHASE_38_DESIGN_LOG §4 #2 | Chat C plan; pairs with L0-1/L0-2 |
| ~~L3-18~~ | ~~`add_type_compat` admin API + bulk rediscover verb~~ | PHASE_38_DESIGN_LOG §4 #4 | **CLOSED 2026-06-01 — ADR-0156 retires ADR-0086; carry-forward dropped** |
| ~~L3-19~~ | ~~`include_deprecated` parameter discipline across L3 walks~~ | PHASE_38_DESIGN_LOG §4 #5 | **CLOSED 2026-06-01 — folded into ADR-0156 scope** |
| L3-20 | Per-user Local-scoped `ProblemTraceSink` dict | PHASE_38_DESIGN_LOG §4 #6 | Pairs with L0-1/L0-2 |
| L3-21 | `--install-builtins=<family,...>` CLI flag on `capacity invoke` | PHASE_38_DESIGN_LOG §4 #7 | Maintenance chat |

---

## 6. Open coordination questions

| # | Question | Source / Status |
|---|---|---|
| ~~L3-Q1~~ | ~~If L3-2 (monitor lifecycle) moves to L4, is Phase 31's `start_resident`/`stop_resident` deleted or repurposed?~~ | **RESOLVED 2026-06-01 — ADR-0155: deleted. No L3-internal residents; Monitors and "residents" collapse to one concept** |
| ~~L3-Q2~~ | ~~If L3-1 (capacities-as-hyperedges) ships, does the registry shape change or only the L3 graph topology?~~ | **RESOLVED 2026-06-01 — ADR-0156 picks bipartite (Option A): registry shape unchanged; topology rewrites with explicit `produces`/`consumes` IntergraphEdges replacing implicit TYPE_COMPAT** |
| ~~L3-Q3~~ | ~~L3-3 (action contracts) — opt-in or migrate-all?~~ | **RESOLVED 2026-06-01 — ADR-0159: opt-in default-None; Phase 27-33 capacities pass via defaults** |

---

## 7. New items from L1/L3 reframe chat closure (2026-06-01)

| # | Item | Source | Owner |
|---|---|---|---|
| L3-52 | **5 canonical decision verdict wrapper types** — `TierVerdict`, `GoalVerdict`, `PipelineFindVerdict`, `PromotionRuleVerdict` + shipped `ReplanVerdict`. Wrap bare-value `decision.*` returns so VERDICT family rule applies uniformly. | ADR-0159 + L3-36 batch | Phase X3 ship |
| L3-53 | **`signal.plan_decomposition_outcome`** new signal source per Chat B D-B51 + ALS subsystem #11 (planning decomposition calibration) per D-B52 — folded into L3-37 ALS family scope. | Chat B D-B51 + D-B52 | WSD installation |
| L3-54 | **`process.*` / `text.*` legacy coexistence** — Phase 31 builtins use `text.*` family for general-purpose; Phase 1 step 2 introduces `process.*` family for input dispatch. Documented as legacy; cleanup deferred to v1.5+. | L3-36 batch PB-FAM-4 | Future L3 chat |
| L3-55 | **`planning.*` + `dream.*` families** — Chat B D-B25 + D-B6. Contracts ratified (OPTIONAL_RETURN family rule); concrete authoring at WSD installation (planning) + dream family chat (dream, deferred). | Chat B + this chat | WSD installation + dream chat |

---

## 8. Chat C closure routing (2026-06-02)

Chat C plan-authoring closed 2026-06-02 (`confirmation_docs/POST_PHASE_38_PHASE_MAP.md`). Routing of open L3 items:

| Item | Routed to | Notes |
|---|---|---|
| L3-4 (typed `CapacityContext` family extensions) | **Per-family downstream chat** | Base ratified ADR-0159; per-family extensions in WSD_INSTALLATION_CHAT / FOL_INSTALLATION_CHAT / ADAPTER_FAMILY_CHAT / CODE_SKILL_INSTALLATION_CHAT. |
| L3-5 (capacity-level perf characterization) | **Future L3 chat** | No live consumer in Phase 39-49. |
| L3-6 to L3-12 (WSD-driven families) | **WSD_INSTALLATION_CHAT** | Catalog authoring. |
| L3-13 to L3-16 (FOL-driven additions) | **FOL_INSTALLATION_CHAT** | — |
| L3-17 (Falkor-backed L3 bootstrap) | **Phase 44** | Rail C; absorbs PHASE_38 §4 #2. |
| L3-20 (Per-user Local-scoped `ProblemTraceSink`) | **Stream A (item A3)** or Phase 44 absorb | — |
| L3-21 (`--install-builtins` CLI flag) | **Stream A (item A4)** | Waits for second builtins family ship. |
| L3-23 (alternative-sub-path registry) | **WSD_INSTALLATION_CHAT** | UC-WSD-15. |
| L3-25 (decision-precedent retrieval capacity) | **WSD_INSTALLATION_CHAT** | UC-WSD-13. |
| L3-26 (constraint-satisfaction over L2 path-finding) | **Future L3 chat** | UC-NLU-3. |
| L3-27 (abductive hypothesis generation) | **Future L3 chat** | UC-NLU-2. |
| L3-28 (code-realm capacity family) | **CODE_SKILL_INSTALLATION_CHAT** | — |
| L3-29 (structural-isomorphism shared) | **Future L3 chat** | — |
| L3-30 (patch-generation capacity) | **CODE_SKILL_INSTALLATION_CHAT** | — |
| L3-31 (side-effect analysis placement) | **Future L3 chat** | — |
| L3-33 (15-20 new decision/scoring family) | **WSD_INSTALLATION_CHAT** | Catalog; family contracts ratified by reframe chat. |
| L3-36 (`predicate.*` family catalog) | **WSD_INSTALLATION_CHAT** | Contract ratified; catalog in WSD. |
| L3-37 (ALS `als.*`/`mechanism.*`/`validate.*` catalogs) | **WSD_INSTALLATION_CHAT** | — |
| L3-38 (`pattern.extract_task_shape`) | **WSD_INSTALLATION_CHAT** | — |
| L3-39 (`decision.classify_dont_know_reason`) | **WSD_INSTALLATION_CHAT** | — |
| L3-40 (shape-indexing for Phase 1 perf) | **WSD_INSTALLATION_CHAT** | — |
| L3-41 (`signal.task_outcome` enriched payload) | **WSD_INSTALLATION_CHAT** | — |
| L3-42 (`hint.*` family catalog) | **WSD_INSTALLATION_CHAT** | Family contract ratified; catalog in WSD. |
| L3-43 (`process.*` family catalog) | **WSD_INSTALLATION_CHAT** (text) + **CODE_SKILL_INSTALLATION_CHAT** (code) | Per L1/L3 reframe L3-43 ownership split. |
| L3-44 (`decision.derive_goal`) | **WSD_INSTALLATION_CHAT** | — |
| L3-45 (6 promotion-rule capacities) | **WSD_INSTALLATION_CHAT** | — |
| L3-46 (`decision.select_promotion_rule`) | **WSD_INSTALLATION_CHAT** | — |
| L3-48 (`retrieval.by_admin_decision_similarity`) | **WSD_INSTALLATION_CHAT** | Reads L0-20 audit-log query API (also WSD scope per PB-T). |
| L3-49 (`adapter.*` family) | **ADAPTER_FAMILY_CHAT** (triggered by first cross-realm consumer) | Standard L3 contract; not structurally distinct. |
| L3-52 (5 verdict wrapper types) | **Phase 42** | Rail B X3 ship per ADR-0159. |
| L3-53 (`signal.plan_decomposition_outcome` signal source) | **WSD_INSTALLATION_CHAT** (in L3-37 ALS family scope) | Chat B D-B51 cascade. |
| L3-54 (`process.*`/`text.*` legacy coexistence) | **Future L3 chat** | Cleanup v1.5+. |
| L3-55 (`planning.*` + `dream.*` families) | **Phase 45** (dream ratification) + **Phase 47** (planning v0; full catalog at WSD installation) | — |
| L3-56 (`DontKnowReason.UNHANDLED_INPUT` enum value) | **L4 (Phase 46/47)** | Deferred at Phase 40 (PB-1): the enum doesn't exist; its 4 siblings are L4 MappingResult semantics; no v1 consumer. `DS_UNHANDLED_INPUT` (the L3 marker) shipped Phase 40. |
| L3-57 (`FAMILY_RULES` key-vocabulary reconciliation) | **RESOLVED Phase 42 (PB-8 Opt 3)** — residual deferred to install chats (below) | Phase 42 renamed `derive`→`derivation`/`signal`→`signalling` + added `consolidate`/`trace`; the 5 genuinely-unknown categories defer via `family_rules.DEFERRED_DEFAULT_CATEGORIES` (test-pinned). Decision + 13-category table: `confirmation_docs/PHASE_27_DONT_KNOW_AUDIT.md`; ADR-0157 §amendment-1; HANDOFF §3.1.17. |
| L3-58 (5 deferred `FAMILY_RULES` categories) | **WSD / FOL / code-skill / adapter installation chats** | `comprehension`, `decomposition`, `path-finding`, `interaction`, `learning-methods` resolve via the permissive `DATASTATE_MARKER` default (`family_rules.DEFERRED_DEFAULT_CATEGORIES`, pinned by `tests/phase_42/test_phase_27_audit_doc.py`). Each owning chat adds the explicit key + shape when it ships the first capacity in that category, and removes it from the deferred set. |
| L3-59 (CapacityContext read-path migration + union-drop — PB-23 read half) | **Contract authority: SKILL_ACQUISITION_PROCESS R0**; **mechanical corpus migration: WSD installation slot 1** | Phase 48 closed the PB-23 *authorization* half (ADR-0180 `writeable` capability; write-half of S12) but kept the read-path dict + the transitional `dict \| CapacityContext` union annotation on `capacity_layer.invoke` "one more phase" (A1′). Phase 49 shipped no feature surface, so the deferral landed nowhere — this row is the routing record (added by MAINTENANCE_CHAT M4, 2026-06-09). Split: (a) the **contract** is fixed at SKILL_ACQUISITION R0 — bundle capacity bodies are authored CapacityContext-native from day one, never dict (no new dict-debt enters via skill installs); (b) the **mechanical migration** of the existing read-path body corpus (`context["kl"]` → `context.kl`) + dropping the union annotation lands at WSD installation slot 1, which touches that corpus anyway for the `process.*`/`hint.*` catalogs. |

---

*End of L3_FUTURE_WORK.md. Last updated 2026-06-09 by MAINTENANCE_CHAT (M4 routing record L3-59; L3-57/58 closure state landed at M0).*
