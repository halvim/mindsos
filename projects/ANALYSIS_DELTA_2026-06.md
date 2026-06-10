# WSD / FOL ANALYSIS — delta addendum (2026-06-09)

> **What this is.** `projects/wsd/ANALYSIS.md` and `projects/fol/ANALYSIS.md` are
> dated **2026-05-28** — before Phases 43–49 shipped. They are the primary
> consumer inputs to SKILL_ACQUISITION_PROCESS_CHAT. This addendum records what
> changed; **the originals are intentionally not rewritten** (they carry banner
> pointers here). Authored by MAINTENANCE_CHAT (M5).
>
> **Method.** Every claim below is verified against **shipped code** (grep /
> file reads at `main` post `phase-49-confirmed` + maintenance commits), not
> HANDOFF prose — per the NPB11-META lesson (`PHASE_43_DESIGN_LOG.md` §10.1:
> a 2026-06-09 audit agent asserted the resident lifecycle still existed;
> grep showed Phase 41 removed it).

---

## 1. Headline state change

Both ANALYSIS docs assume the post-Phase-38 world: **L4/L5 "Nothing shipped."**
That is no longer true. Phases 39–49 all shipped (tag `phase-49-confirmed`):

| Was (2026-05-28) | Is (2026-06-09) | Evidence |
|---|---|---|
| WSD §2 L4 bin-A "Nothing shipped" | `mindsos_intelligence` (8th package): IntelligenceLayer, priority-tier Executor + worker pool, six-phase orchestrator, L4Dispatcher, chain artifacts, dream-cycle driver, crash recovery, consolidation | `mindsos_intelligence/*.py` (22 modules); Phases 46–48 |
| WSD §2 L5 bin-A "Nothing shipped (gated on note-fork)" | L5 v1 shipped Phase 48: MM consolidation → Episode + Memory + `MEMORY_CONTAINS_EPISODE` on all terminal paths; D'1 retention stack. **Note-fork retired** (Chat B) — the WSD L5 D-bin row's gating premise is gone | `mindsos_intelligence/consolidation.py`, `retention.py`; ADRs 0176–0180 |
| L2 role-set = 8 named roles | **12** named roles: Phase 43 added `parameter-staging`, `pending-promotions`, `capacity-gaps`, `learned-parameters` | `mindsos_knowledge/identifiers.py:57-76` (12 `ROLE_*`) |

## 2. WSD ANALYSIS deltas (by section/row)

| Row | Stale claim | Shipped reality | Evidence |
|---|---|---|---|
| §2-L2 B-bin "3 new role-graphs (`parameter-staging`, `pending-promotions`, `capacity-gaps`)" | Listed as **B** (not implemented) | **A-bin now** — all three shipped at Phase 43 (Global/Local placement per ADR-0150 §am-5) | `identifiers.py:73-75` + `mindsos_knowledge/schemas/` |
| §2-L2 D-bin "`sense-correlations` + `learned-parameters` (inherited from R0-PB-9)" | Disposition open | **Split disposition:** `learned-parameters` SHIPPED (Phase 43, single role-graph); `sense-correlations` **WITHDRAWN** as standalone role-graph (L2 chat D-L2-2; data lives in the lexicon empirical-layer). Regression guard `test_5_item_exclusion_regression_guard` (`tests/phase_43/test_4_role_graphs.py`) **forbids** re-adding it | grep: zero `sense-correlations` in `mindsos_knowledge/` |
| §4 R0-PB-9 row "WSD-chat resolution implies default = (a) ship both" | — | **Only `learned-parameters` shipped.** "Ship both" is dead; WSD designs against lexicon empirical-layer for sense-correlation data | as above |
| §2-L3 C-L3-2 (monitor lifecycle) + §6 Analysis-PB-A5 | "Conflicts with Phase 31 resident lifecycle… un-doing requires supersession" | **RESOLVED in WSD's favor.** ADR-0155 / Phase 41 removed `start_resident`/`stop_resident`/`_subscriptions`/`ResidentSubscription`/`ResidentError`; `KIND_RESIDENT`→`KIND_MONITOR` (value `"monitor"`). L4 owns lifecycle via `MonitorSubscriptionRegistry` (Phase 46) consuming `cl.iter_monitors()` (Phase 41). The supersession Analysis-PB-A5 called for **already happened** (ADR-0073 → Superseded by ADR-0155) | grep: zero `start_resident`/`stop_resident` in `mindsos_capacity/`; `mindsos_intelligence/monitor_subscription.py` |
| §4 R0-PB-2 row "`add_type_compat`" absorption | Listed as WSD-absorbable carry-forward | **Retired, not absorbable.** Phase 42 retired TYPE_COMPAT/discovery whole (`discovery.py`, `SuccessorHop`, `DiscoveryFailedError`, `rediscover`); topology is now explicit `PRODUCES`/`CONSUMES` IntergraphEdges + bipartite `find_pipeline` (ADR-0156/0159) | `mindsos_capacity/__init__.py:88` documents the retirement |
| §2-L1 C-L1-2 / §2-L3 C-L3-1 (capacities-as-hyperedges) | "Direct architectural conflict" vs node-model + TYPE_COMPAT | **Conflict remains but the surface moved.** Shipped model is still capacities-as-nodes, but Phase 42's bipartite produces/consumes edge topology (DataStates ↔ capacities as first-class edges) delivers part of what WSD's hyperedge reframe wanted. Re-litigate against ADR-0156/0159, not against Phase-27 TYPE_COMPAT | `mindsos_capacity/context.py`, `register_capacity` PRODUCES/CONSUMES emission |
| §2-L3 C-L3-3 (action contracts on registration) | "Registration carries no precondition/effect schema" | **Partially moved.** ADR-0159 contract v2 added 6 `_CapacityBase` fields + typed `CapacityContext` + family dont-know contracts (ADR-0157 `FAMILY_RULES`). Preconditions/effects per se still absent — the conflict row survives, but design against contract v2 | `mindsos_capacity/family_rules.py`, `context.py` |
| §2-L4 B-bin rows: six-phase lifecycle, dream scheduler, ALS, failure classifier, phase-6 blame | Listed as B (not implemented) | Six-phase lifecycle SHIPPED (Phase 47, v0 catalogs — `execution.py` dispatches no real L3 capacity yet); dream family (Phase 45) + dream-cycle timer (46) + driver (48) SHIPPED — v1 re-runs from episode `task_input`; **faithful episode→MM reconstruction + `replay_recorded` differentiation + real ALS firing are WSD-gated** (Phase 48 PB-9). 10 signal-source + 11 ALS **skeletons** shipped (Phase 47) | `mindsos_intelligence/orchestrator.py`, `dream_cycle.py`, `als_subsystems.py`, `signal_sources.py` |
| §2-L4 C-L4-1…C-L4-7 (7 critique-push picks) | "must land in the L4/L5 plan chat" | Chat A (2026-05-28) settled L4 architecture; Phases 46–48 shipped it. The 7 picks must now be re-validated against **shipped** L4, not a plan. Several are implicitly ratified (e.g. C-L4-3 pause-and-resume: nothing shipped → still open post-v1; C-L4-4 tiers: `TierEnum` shipped Phase 46 in L3 `tiers.py`, no learnable coefficients) | `mindsos_capacity/tiers.py` |
| §3 recommended chat ordering | "skill-acquisition FIRST, WSD second, FOL third" | **Revised 2026-06-09:** MAINTENANCE first (done — this addendum + ADR-0182 are its outputs), then SKILL_ACQUISITION → WSD → FOL; DWF after MAINTENANCE (single-tester gate serialization + ADR-0182 amends the persister contract DWF ingests against) | `POST_PHASE_38_PHASE_MAP.md` §6 + downstream-plan revision 2026-06-09 |
| §5 WSD §6.2 phantom-FOL blocker | resolved at analysis time | unchanged — still resolved | — |

**Re-grep result (WSD ANALYSIS, 2026-06-09):** stale-vocabulary hits at lines 88 + 172 (`resident` lifecycle — superseded as above) and line 146 (`add_type_compat` — retired). **No `PlanRun` / bare-`memories` hits.**

## 3. FOL ANALYSIS deltas (by row)

| Row | Stale claim | Shipped reality | Evidence |
|---|---|---|---|
| B10 / D1 (`sense-correlations` + `learned-parameters` "not shipped") | Both open | `learned-parameters` SHIPPED (Phase 43); `sense-correlations` WITHDRAWN + regression-guarded. D1's "8 ROLE_* constants" is now 12 | `identifiers.py`; schema `mindsos_knowledge/schemas/learned_parameters.py` |
| B15 (FOL pushback #4: 3-way `learned-parameters` split) | Open proposal | **Deferred, NOT aligned at v1.** Phase 43 shipped the SINGLE role-graph; the schema docstring explicitly reserves the split for the FOL chat (D-L2-12; Chat A R5 D28/D30) | `schemas/learned_parameters.py` docstring lines 19-23 |
| B6 / B11 / D2 / D3 (task-to-pipeline flow; "no L4 code"; "L4 mid-flight, 7 pushes pending") | L4 unshipped/mid-flight | **All stale.** L4 settled (Chat A) and shipped (Phases 46–48): six-phase lifecycle + `task-patterns` → `promoted-pipelines` flow exists as v0 `planning.*` catalogs (full catalog = WSD installation). D3's "resolves first" is **done** | `mindsos_intelligence/orchestrator.py`, `builtins/planning_v0.py` |
| B20 (FOL pushback #9 — typed `CapacityContext`) | "L3 capacity-context redesign" (future) | **SHIPPED** Phase 42 (`context.py`: 10-field typed `CapacityContext` + 4 Protocols + 5 verdicts; 11th field `writeable` Phase 48 ADR-0180). Residual: read-path corpus migration + union-drop = **L3-59** (contract authority SKILL_ACQUISITION R0; mechanical migration WSD slot 1) | `mindsos_capacity/context.py`; `docs/_workbench/L3_FUTURE_WORK.md` L3-59 |
| C1 (L5 holds Coherence-Loop populations) | Conflict vs L5 design *notes* | Conflict now runs against **shipped** L5 (per-task MM, consolidation at terminal paths, D'1 retention). The pushback-#5 resolution path (`training-runs` role-graph, B16) is unshipped and now also requires an ADR-0150 §am-5 role-set amendment (closed set = 12) | Phase 48 ship; `identifiers.py` |
| C5 (concurrency model unspecified; "MindsOS is per-session single-thread") | High-severity open | **Materially changed.** Phase 46 shipped a worker pool + priority-tier Executor + writer-preferred MM RWLock + cooperative cancellation; Phase 47 worker-per-task lifecycle (ADR-0171). In-process multi-threaded is now the shipped answer; FOL's prover in-process-vs-subprocess question survives, but argue it against ADR-0163-0170/0171 | `mindsos_intelligence/executor.py`, `intelligence_layer.py` |
| C4 (DOLCE locked / multi-ontology) | unchanged | Still open — no shipped change to `ontology` role-graph import model | — |
| A-bin rows (A1–A5) | — | Still accurate; A5's "population deferred to L4" now partially live (v0 catalogs) | — |

**Re-grep result (FOL ANALYSIS, 2026-06-09):** **zero** hits for `TYPE_COMPAT`/`discovery`/`PlanRun`/bare-`memories`/`resident` — the FOL doc is vocabulary-clean.

## 4. Vocabulary map (for reading the 2026-05-28 docs + WSD/FOL *source* materials)

| 2026-05-28 term | Shipped term | Changed at |
|---|---|---|
| `memories` role-graph | `episodic_memories` | Phase 39 (ADR-0044 §am-3) |
| resident / `KIND_RESIDENT` | monitor / `KIND_MONITOR` (L4-owned lifecycle) | Phase 41 (ADR-0155) |
| TYPE_COMPAT / discovery / `SuccessorHop` / `rediscover` | retired → `PRODUCES`/`CONSUMES` IntergraphEdges + bipartite `find_pipeline` | Phase 42 (ADR-0156) |
| `PlanRun` | `PipelineRun` (6-level chain: HintSet → MappingResult → Plan → Pipeline → PipelineRun → TaskRun) | Chat B / Phase 47 `chain_artifacts.py` |
| alignment `alignment:<a>-<b>` | `alignment:<a>:<b>` (`:` separator) | Phase 39 (ADR-0154) |

## 5. Still open — noted, NOT resolved here

- **`InterGraphEdge` vs `IntergraphEdge` casing** (WSD C-L1-1): shipped code is
  `IntergraphEdge` (`mindsos_core/models/intergraph_edge.py:51`). Routed to
  **SKILL_ACQUISITION R0** per HANDOFF §2.1.
- **C-bin ledger full re-pass:** this addendum re-passed the rows the
  2026-06-09 reanalysis flagged (C-L3-2 resolved; C-L1-2/C-L3-1 surface moved;
  C-L3-3 partially moved; C1/C5 re-grounded; C4 unchanged). The WSD chat should
  treat the remaining C-rows + the 7 C-L4 picks as **re-validate against
  shipped code**, not as a fresh conflict inventory.
- **Node-value serialization** for structured records (bundle manifests,
  install provenance, durable Episodes): contract FIXED at **ADR-0182**
  (decide-and-document; impl = skill-acquisition slot 1). WSD/FOL source
  materials proposing blob stores (FOL pushback #8 / B19) should be read
  against ADR-0182's rejected-options section — the blob store was rejected
  for *node values*; FOL's large-model-artefact case (100MB checkpoints) is a
  **different** question and remains open (B19 survives for artefacts, not for
  role-graph node values).
- **Falkor delete-sweep completeness audit** (L0-25 residual): routed to WSD
  installation (`tests/maintenance/test_l0_25_falkor_local_persister_live.py`
  xfail probe documents the seam).

---

*End of addendum. Consumers: SKILL_ACQUISITION_PROCESS_CHAT (primary), WSD/FOL
installation chats. Verify against shipped code on entry — this document ages
the same way the originals did.*
