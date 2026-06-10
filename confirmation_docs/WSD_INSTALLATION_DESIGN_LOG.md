# WSD_INSTALLATION — Design Log

**Status:** design CLOSED 2026-06-10 (R0 + R1 + R2 + R3 buildability, zero reversals; saturation per Phase-43 rationale). Phase-map on disk: `WSD_INSTALLATION_PHASE_MAP.md` (slots = Phases 51–56). Ship slots pending.
**Chat type:** design-authoring (PB-A precedent). Deliverables: this log + `WSD_INSTALLATION_PHASE_MAP.md` + per-slot ship seeds.
**Prereqs verified:** tag `phase-50-confirmed` present; `main` at `7ef54f2` (post `cb5d207`). Untracked robot-demo/prototype corpus noted — selective staging only.
**Inputs consumed:** HANDOFF §3.1.23/§9/§10; `projects/ANALYSIS_DELTA_2026-06.md`; `projects/wsd/FUTURE_CHAT_PROMPT.md` (banners override body); `SKILL_ACQUISITION_PROCESS_PHASE_MAP.md` §3/§5 (binding); `SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md` S1–S13+R2; `PHASE_50_DESIGN_LOG.md` (G1, I4/I5/I6/I10); `POST_PHASE_38_PHASE_MAP.md` §6 WSD row + q4/q5; `projects/wsd/ANALYSIS.md` (historical); `projects/wsd/source/WSD_DESIGN_HANDOFF.md` §2/§4/§5/§6/§9/§10.

---

## §0 — R0 probe findings (file-level)

1. **"Lexicon empirical-layer" is a phantom.** Zero `empirical` hits in `mindsos_knowledge/`. D-L2-2's disposition for `sense-correlations` data points at a structure never shipped. WSD deliverables #2 (dream miner) + #3 (bootstrap importer) had no write target until PB-W2 resolved it.
2. **`world-axioms` is regression-guard-blocked**, not just ADR-0150-gated: `tests/phase_43/test_4_role_graphs.py::test_5_item_exclusion_regression_guard` (NPB14-4) excludes `world-axioms`/`sense-correlations`/`training-runs`/`fol-rules`/`fol-ledger`. Shipping it = ADR-0150 §am + deliberate guard amendment.
3. **L3-59(b) corpus is small** — dict-form `context["` usage: `capacity_layer.py` read path + `context.py` + 1 phase-34 test. Slot-1 migration is genuinely mechanical.
4. **ALS = 11 skeletons; signal sources = 10 empty-payload skeletons; v0 catalogs `placeholder=True` opt-in.** Shipped importers: `dolce`/`oewn`/`framenet` only.
5. **`learned-parameters` Global = `admin_authored` ("cross-user ALS applies via admin importer")**; coherence dream cut at Chat A (C-L4-1/C-L4-7 ratified).
6. **R1:** `AlignmentsImporter` body is DWF-owned, unshipped → alignment role-graphs empty at runtime; WSD §4.1 density number unmeasurable today.
7. **R1:** No NLU perception stack (only `text.space_split`/`text.sentence_split`; no POS/lemma/parse/`frame_match`/`slot_filler_candidates`); no NLP dep in `pyproject.toml`. Favorable: `REALM_NLU` reserved (Phase 40); `FAMILY_RULES` pre-provisions `scoring`/`process`/`hint`/`predicate`/`decision`.

## §1 — R0 decisions (all ACCEPTED by Henrique 2026-06-10)

| # | Surface | Pick |
|---|---|---|
| PB-W1 | Scope partition | **(b)** One `WSD_INSTALLATION_PHASE_MAP.md`, rails-style: **Rail S** (substrate: empirical-layer + world-axioms + importers), **Rail C** (capacity + catalogs + v0 replacement), **Rail L** (ALS + promotion loop + dream miner). Design rounds staged per rail. |
| PB-W2 | `sense-correlations` home | **(a)** Design + ship the **lexicon empirical-layer edge vocabulary** (new EdgeTypes on `lexicon`, release-side, own ADR). Honors D-L2-2; no role-set change; biggest unplanned design surface — Rail S slot 1 material. Rejected: role-graph revival (guard-blocked, no reversal evidence); LearnedParameter abuse. |
| PB-W3 | Importer roster | **(c)** SemCor + GlossTag (down-weighted) at v1; OntoNotes/VerbNet/SemLink/FrameNet-extended → v2-trigger ledger. §6 row reserves scope, doesn't bind v1 rosters. |
| PB-W4 | Coherence-loop fate (WSD §6.1) | **Ratify (a-ALS):** `learned-parameters` written via promotion loop, ALS-fired from dreams/signals. Consistent with shipped architecture. **Cascades to FOL pushbacks #2–#5** — cross-project ratification. |
| PB-W5 | ALS scope | **(b)** Mechanism + validator for WSD-consumed subsystems only (sense-ranker weights; possibly capacity-gaps reporting); other ~9 stay skeletons with named triggers. Explicit scope amendment of the §6 "#1–#11" wording in the WSD phase-map. |
| PB-W6 | v0 replacement granularity | Additive families (`hint.*`/`predicate.*`/`decision.*`/`process.*`) land in early slots; the v0→real flip is **one atomic slot** flipping `planning.*`+`phase1`+`orchestration` together + removing the `placeholder=True` guard. |
| PB-W7 | PB-T roster | **(b)** ALS audit constants + capacity-gaps tooling at v1; HITL channel + further scheduler infra → ledger (triggers: first interactive-approval consumer; first non-dream schedule). |
| PB-W8 | C-bin reframes | C-L1-2/C-L3-1 (capacities-as-hyperedges): **closed as satisfied-by-ADR-0156**. C-L3-3 (action contracts): additive fields only if the WSD replan-check predicate reads them at v1 (verify at R2); else ADR-note deferral to L4-v2. |
| PB-W9 | WSD §6.3 + §6.4 | **Confirm defer to v3+** (multi-domain ontology; ontology learning). FOL inherits. |
| PB-W10 | Risk placement | The capacity contract (WSD §10 q1–q8) is the real open design surface, not install plumbing → dedicated R1. |

## §2 — R1 decisions (capacity contract; all ACCEPTED by Henrique 2026-06-10)

| # | Surface | Pick |
|---|---|---|
| PB-W11 | DWF dependency | **(c)** Capacity designed to run without alignments (dont-know contract covers the absent stratum) + **DWF_INSTALLATION_CHAT opened in parallel**; alignment-density number (§4.1: fraction of OEWN verb senses with FrameNet alignment) gates only the **enrichment** slot, not the capacity slot. |
| PB-W12 | External parser dep | **(a)** Optional-extra dependency group (`mindsos[nlu]`, spaCy or stanza — final pick at R2); perception capacities emit family dont-know when absent. **Own ADR — dependency-policy precedent** (FOL prover hits the same fork). |
| PB-W13 (q1) | Sense inventory | Fine-grained OEWN synsets. Coarse clusters would need the deferred OntoNotes importer + a nonexistent mapping. Eval target = human IAA (~70–80%), per WSD §5.1. |
| PB-W14 (q3) | Generalisation layer | **(c)** Layered: WordNet hypernym chain = v1-shippable core (lexicon-internal, populated today, classical Resnik home); DOLCE/FrameNet stratum = DWF-gated enrichment. Makes the capacity slot DWF-independent. |
| PB-W15 (q4) | Scoring | **(a)** Resnik-style selectional association over hypernym classes + MFS-prior fallback chain. Mixing weights (association vs MFS prior vs GlossTag down-weight) = `learned-parameters` entries with static defaults → makes the consumed ALS subsystem + promotion loop real. No learned scorer (fixed-L3). |
| PB-W16 (q8) | Capacity shape | **(b)** `scoring.wsd_rank_senses` (scoring family; OPTIONAL_RETURN dont-know). I/O = REALM_NLU DataStates (`nlu.predicate_arguments` → `nlu.sense_candidates` carrying `(sense_iri, score, justification_refs)` + ambiguity flag per WSD §4.3). DataState roster = R2. |
| q2 | Argument extraction | UD `nsubj`+`dobj`(+`iobj`) v1; obliques v2. |
| q5 | Inference | Per-token independent ranking v1; beam/pairwise = v1.5 trigger. |
| q6 | Bootstrap scope | SemCor + GlossTag down-weighted (locked by PB-W3). |
| q7 | Miner window | Same-sentence co-occurrence. |

## §3 — Coordination notes for the parallel DWF chat (2026-06-10)

1. **New binding deliverable for DWF:** the **alignment-density measurement** — fraction of OEWN **verb** senses with (i) a FrameNet alignment and (ii) a DOLCE/DULplus class, reported at import time. It is WSD's §4.1 blocking number and gates WSD's enrichment slot (PB-W11/PB-W14).
2. **Boundary:** the lexicon **empirical-layer** (sense-correlation strata) is **WSD-owned** (PB-W2). DWF owns alignment ingestion (`alignment:<a>:<b>` pair-graphs) only. No empirical-layer work in DWF.
3. **Slot coordination:** both chats ship numbered phases from the same pool (next free = 51, high-water 50). WSD has NOT yet reserved slots (phase-map pending R2). DWF must check the live next-free slot (HANDOFF header + `git tag`) at its own phase-map authoring and record its reservation in HANDOFF immediately to prevent collision. Single-tester gate serialization applies (delta §2 ordering row).
4. **Stale-seed corrections for DWF:** its FUTURE_CHAT_PROMPT PB-7 (naming) is **resolved** — canonical `alignment:<a>:<b>` per ADR-0154 (Phase 39); its seed predates the skill-install driver — whether knowledge-acquisition reuses the ADR-0183 driver (L2-content-only bundle) vs stays a bare importer run is DWF's R0 headline question.

## §4 — R2 decisions (rail design pass; all ACCEPTED by Henrique 2026-06-10)

Probe basis: lexicon schema `strict=False` + `ADMIN_AUTHORED`, any→any EdgeTypes; `replan_check.py` thin v0 stub (dispatcher state, no declaration fields); promotion-loop schemas single-NodeType shells; `world-axioms`' only v1 consumer in WSD source = ConceptNet distillation (CC-BY-SA legal-review path); NPB14-4 guard comment labels it "FOL-chat-owned" — contradicting the POST_PHASE_38 §6 WSD row.

| # | Surface | Pick |
|---|---|---|
| PB-W20 | `world-axioms` | **(b) Defer to ledger** (trigger: first axiom-consuming capacity); no WSD-v1 consumer; §6-row scope amendment recorded in phase-map §4; ownership contradiction routed to FOL. Consequence: **no ADR-0150 amendment anywhere in the WSD plan.** |
| PB-W21 | Empirical-layer write discipline | **(b)** Miner emits `parameter-staging` (Local); promotion applies settled correlations to Global lexicon empirical layer via admin path. Zero discipline exceptions; S10 loop + ALS sense-ranker + miner = **one mechanism, two artifact targets** (learned-parameters values + empirical edges). |
| PB-W22 | Parser | **spaCy** `en_core_web_sm` (MIT, no PyTorch, native nsubj/dobj/iobj). Model-download + missing-model→dont-know in the W12 dependency ADR. |
| PB-W23 | C-L3-3 | **No action-contract fields at v1.** Replan signal = family dont-know + tier verdicts over the linear NLU pipeline. ADR-notes deferral to L4-v2 (C-L4-2 preserved as direction). |
| PB-W24 | Dream miner shape | **(b)** Miner = consolidation-time hook in `dream.maintenance` `replay_recorded` path, reading episode `task_input`/results directly. **Faithful episode→MM reconstruction + `replay_recorded` differentiation → ledger** (trigger: first full-MM-replay consumer) — was Phase-48 PB-9 "WSD-gated"; v1 mining doesn't need it. |
| PB-W25 | Slot skeleton | 6 slots / 3 rails — authored as phase-map §2 (Phases 51–56). |

## §5 — R3 buildability scan (2026-06-10; refinements only, zero reversals)

Favorable: OEWN importer already ships `EDGE_HYPERNYM_OF`/`EDGE_INSTANCE_HYPERNYM_OF` (hypernym backbone in Global lexicon today — slot 51 needs zero new substrate imports); v0 installs opt-in by discipline (clean atomic-flip seam); W20 ⇒ no role-set change in the whole plan; L3-59(b) ripple contained to `capacity_layer.invoke` + CLI (dispatch already CapacityContext-native; the exact surface Phase 48 A1′ left open).

| # | Finding | Pick |
|---|---|---|
| PB-W26 | spaCy in the hermetic docker gate | **(b)** Parser-injectable capacities; unit tests on injected stub; real-spaCy tests live-marked (Falkor-live precedent). Revisit baking the model only on observed stub/live drift. |
| PB-W27 | S8 upgrade-rejection vs multi-slot bundle delivery | **(b) Sibling bundles** `wsd-core` (53) → `wsd-pipeline` (54) → `wsd-learning` (55) chained via `requires_bundles`; fits driver as-built; reverse-dep check orders de-install for free. |
| PB-W28 | Corpus distribution | Path-based importer sources (OEWN precedent) + small XML fixtures in-repo; acquisition + Princeton-license notes in slot-52 ADR. No legal-review path (unlike deferred ConceptNet). |

ADR roster estimate: 6–7 (empirical-layer vocabulary; dependency policy; NLU DataStates + capacity contract; importers/bootstrap; promotion mechanism; L4 slot-shapes amendment to SA S2; v0-flip/orchestration). Gate sizing per slot within the normal envelope.

## §6 — Saturation declaration + closure

R0 (10 pushbacks) / R1 (6 + 4 minors) / R2 (6) / R3 (3) — all accepted, zero reversals across four rounds; remaining unknowns (exact EdgeType property set, hint/predicate/decision roster, slot-56 coverage bar) are slot-R0 items absorbed by per-slot design logs. **Design CLOSED 2026-06-10.**

**Closure outputs:**
1. `WSD_INSTALLATION_PHASE_MAP.md` — slots 51–56 + ledger + §6-row scope amendments + FOL inheritance + DWF coordination.
2. `WSD_PHASE_51_NEXT_CHAT_PROMPT.md` — Phase 51 ship-chat seed.
3. HANDOFF slot-reservation note (Phases 51–56 = WSD; DWF takes 57+).
4. This log → CLOSED; §3 coordination notes remain live for the parallel DWF chat.

*End of WSD_INSTALLATION_DESIGN_LOG.md.*
