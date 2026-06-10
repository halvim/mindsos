# WSD — Analysis vs Shipped MindsOS

> ⚠️ **STALE AS OF 2026-06-09 — read `projects/ANALYSIS_DELTA_2026-06.md` alongside this document.**
> This analysis is dated 2026-05-28, before Phases 43–49 shipped. Known-stale rows
> (grep-verified): the L4/L5 "Nothing shipped" bins, the 3 L2 role-graph B-rows
> (shipped Phase 43), the `sense-correlations`/`learned-parameters` D-bin
> (split disposition), C-L3-2 + Analysis-PB-A5 (resident lifecycle removed
> Phase 41 — resolved in WSD's favor), the `add_type_compat` absorption row
> (TYPE_COMPAT retired Phase 42), and the §3 chat ordering. The delta addendum
> is the authoritative correction; this file is intentionally left unrewritten.

> **Project:** Word Sense Disambiguation skill for MindsOS — a multi-layer intelligent system to be installed via the skill-acquisition process.
> **Project status:** Goal-finalized; pre-code. Per WSD_DESIGN_HANDOFF.md §1, the project ran under "extreme critique" instructions and §6 names 4 MindsOS-internal blockers (coherence loop fate, FOL phantom dependency, multi-domain ontology scope, ontology learning scope). The 5 `coordinated_change_*` documents (one per L0-L4) propose major cross-cutting changes. The 5 `pending_adrs/L0-L4.md` files contain ~50 PROPOSED ADRs awaiting per-layer ratification.
> **Analysis date:** 2026-05-28.
> **Source materials:** `projects/wsd/source/` — 21 files: 4 handoff/finalization docs, 5 coordinated_change docs (one per L0-L4), 5 pending_adrs/ docs (one per L0-L4), 1 USE_CASES doc (16 stress-test use cases), 1 ARCHITECTURE doc, 3 demo/business docs, 1 CLAUDE.md, 1 README in pending_adrs/.
> **Triage shape:** A/B/C/D same as DWF + FOL. WSD's scale (50+ proposed ADRs) means I summarize per-layer rather than enumerate every row; see source docs for proposition-level detail.

---

## 1. Source-material inventory

| File / folder | Size | Role |
|---|---|---|
| `WSD_DESIGN_HANDOFF.md` | 20KB | 2026-04-26 handoff. §2 TL;DR, §3 reframing-into-MindsOS, §4 settled, §5 cuts, §6 4 blockers, §10 8 open questions, §11 12-doc reading list |
| `WSD_GOAL_FINALIZATION_HANDOFF.md` + `_latest.md` | 12KB each | Goal-finalization chat handoffs (2026-04-30) |
| `WSD_GOAL_FINALIZATION_OUTPUT.md` | 20KB | Goal-finalization output summary; load alongside per-layer pending ADRs |
| `WSD_GOAL_DISCUSSION_GUIDANCE.md` | 8KB | Discussion guidance |
| `WSD_ARCHITECTURE.md` | 40KB | Full architectural design |
| `WSD_USE_CASES.md` | 116KB | **16 architectural stress-test use cases.** Largest file |
| `MINDSOS_DEMO_EXAMPLES.md` | 36KB | Synthetic-domain demos (post-v1 priority) |
| `MINDSOS_BUSINESS_PROBLEMS.md` | 12KB | Commercial use-case catalog (post-v1 priority) |
| `coordinated_change_L0_user_settings.md` | 12KB | L0 user-settings table for ALS training prefs + 8 sub-sections |
| `coordinated_change_L1_intergraph_and_layers.md` | 24KB | L1 InterGraphEdge primitive + Schema-declared layers |
| `coordinated_change_L2_lexicon_layers_and_role_graphs.md` | 32KB | L2 lexicon layers + 6 new importers + 3 new role-graphs |
| `coordinated_change_L3_capacities_and_monitors.md` | 32KB | L3 SCMS / MSUR / ALS capacities + 5 method libraries + failure-diagnosis |
| `coordinated_change_L4_intelligence_and_als.md` | 36KB | **L4 ALS + MSUR + SCMS + Six-Phase Task Lifecycle**; resolutions for 7 of the L4 critique pushes |
| `pending_adrs/README.md` | 4KB | Per-layer ADR organization |
| `pending_adrs/L0_server.md` | 8KB | 8 §A ADRs + §B server code changes |
| `pending_adrs/L1_core.md` | 8KB | 4 §A ADRs + §B core code changes + §C cross-layer interfaces |
| `pending_adrs/L2_knowledge.md` | 12KB | 8 §A ADRs (incl. new `world-axioms` sub-graph) + §B schema changes |
| `pending_adrs/L3_capacity.md` | 12KB | 8 §A ADRs (capacity-as-hyperedge model) + §B code changes |
| `pending_adrs/L4_intelligence.md` | 12KB | 9 §A ADRs + §B intelligence-layer code changes |
| `CLAUDE.md` | 4KB | Original project CLAUDE.md |

---

## 2. Per-layer triage (summary form)

WSD spans all 5 layers. Per-layer summary; granular per-ADR detail in `source/pending_adrs/L{0,1,2,3,4}.md` §A.

### L0 — Server

| Bin | Count | Notes |
|---|---|---|
| A | ~3 | Auth, session, audit primitives (Phase 18-22) all shipped |
| B | ~5 | New `user_settings` table for ALS training prefs; minimal user UI; capacity sandbox; per-capacity I/O extraction; reproducibility infrastructure |
| C | ~0 | No direct conflicts; mostly additive |
| D | ~0 | None |

### L1 — Core

| Bin | Count | Notes |
|---|---|---|
| A | ~2 | Graph + Metagraph primitives (Phase 03-05d) |
| B | ~2 | Path-engine inter-graph traversal; named-DS registry; reproducibility primitives |
| C | **2** | **Real conflicts** — see C-bin below |
| D | 0 | None |

**C-bin items at L1:**
- **C-L1-1: `InterGraphEdge` primitive proposal.** WSD `coordinated_change_L1` §3 proposes `InterGraphEdge` (capital G). MindsOS shipped `IntergraphEdge` (lowercase g) at Phase 05b + `IntergraphHyperEdge` at Phase 05c. Naming differs; semantic verification needed — likely the same intent, but WSD spec may have additional properties (graph context, cross-graph traversal hooks) not in shipped form.
- **C-L1-2: "Capacities as hyperedges in the L3 capacity graph"** (pending_adrs/L1 §A.2 + L3 §A.1). MindsOS L3 ships capacities as graph **nodes** (per `mindsos_capacity/capacity_layer.py:116` `class CapacityLayer`; Phase 27). WSD reframes capacities as hyperedges with DataStates as nodes. **Direct architectural conflict** at L3 model.

### L2 — Knowledge

| Bin | Count | Notes |
|---|---|---|
| A | ~5 | KL, MetagraphView, 8 role-graphs, alignment schema, 4 importers (Phase 12-16) |
| B | **15+** | Heavy additive surface: empirical-layer edge vocabulary; 6 new importers (SemCor, OntoNotes, VerbNet, SemLink, GlossTag, FrameNet-extended); 3 new role-graphs (`parameter-staging`, `pending-promotions`, `capacity-gaps`); `world-axioms` sub-graph; cross-system mappings as InterGraphEdges |
| C | **2** | Real conflicts |
| D | **2** | sense-correlations + learned-parameters (inherited from R0-PB-9) |

**C-bin items at L2:**
- **C-L2-1: Lexicon "theoretical layers" via Schema-declared layers** (coordinated_change_L1 §4 + L2 §3). Requires L1 schema-layers primitive (not shipped). Depends on L1 acceptance.
- **C-L2-2: `world-axioms` sub-graph** (pending_adrs/L2 §A.1). New v1 role-graph. ADR-0150 §am-1 currently bounds role-graphs to 8 named + alignment-prefix. Adding `world-axioms` requires an ADR amendment per ADR-0150 §"expansion requires an ADR amendment."

### L3 — Capacity

| Bin | Count | Notes |
|---|---|---|
| A | ~3 | CapacityLayer, DataStates, register_capacity, register_datastate (Phase 27-31) |
| B | **20+** | Massive additive surface: SCMS init + monitor capacities; MSUR helper; 5 method libraries (evaluator.*, combination.*, comparator.*, metric.*, class.ancestors_*); ALS signal-source capacities; update-mechanism library; failure-diagnosis capacities; monitor declaration extensions |
| C | **3** | Real conflicts |
| D | 0 | None |

**C-bin items at L3:**
- **C-L3-1: Capacities-as-hyperedges architectural reframe.** Same as C-L1-2; load-bearing at L3.
- **C-L3-2: Monitors descriptive-only with L4-owned lifecycle** (coordinated_change_L3 §9; resolves L3 ADR-014). Conflicts with MindsOS Phase 31 ship which has CapacityLayer-owned resident lifecycle (`start_resident` / `stop_resident` / `_subscriptions`). Architectural reframe required.
- **C-L3-3: Action contracts on L3 capacity registrations** (coordinated_change_L3 §10; per FOL pushback #2 ACCEPT). Currently MindsOS Phase 28-33 capacity registration carries no precondition/effect schema; adding it changes the registration contract.

### L4 — Intelligence

| Bin | Count | Notes |
|---|---|---|
| A | 0 | Nothing shipped |
| B | **20+** | ALS (Audited Learning Subsystem); MSUR pipeline (Multi-Source Update Resolver); SCMS BSP turn pipeline; promotion-rule auto-selection; dream scheduler; failure classifier; phase-6 blame attribution; migration phase orchestration; six-phase task lifecycle |
| C | **7** | All 7 are explicit resolution picks on L4 critique pushes (see below) |
| D | **1** | L4 architecture itself contested (inherited from R0-PB-1) |

**C-bin items at L4 (explicit ACCEPT picks on L4 critique pushes from L4_session_handoff_2026-04-25):**
- C-L4-1 — Push 3 (coherence dream): ACCEPT cut from v1; ALS substitutes
- C-L4-2 — Push 2 (replan-check predicate): ACCEPT action contracts on L3 capacities
- C-L4-3 — Push 5 (pause-and-resume): ACCEPT defer to post-v1
- C-L4-4 — Push 6 (four-tier preemption with learnable coefficients): ACCEPT keep tiers, drop coefficients
- C-L4-5 — Push 1 (meta-pipeline-everywhere): PARTIAL ACCEPT
- C-L4-6 — Push 7 / Push 4 (predicate distillation): ACCEPT drop
- C-L4-7 — Coherence-loop-as-GA: ACCEPT cut + replace with ALS plural strategies (per FOL pushback #2)

**Each of these is an L4 design decision that must land in the L4/L5 plan or skill-acquisition chat. They cannot be ratified in WSD's chat alone because they shape L4 architecture broadly.**

### L5 — Mental Model

| Bin | Count | Notes |
|---|---|---|
| A | 0 | Nothing shipped (gated on note-fork per L5 §3.4) |
| B | ~3 | Coherence-loop populations placement (now moot per C-L4-1); ALS workspace; SCMS state snapshots |
| C | ~1 | L5 retention-model gating per R0-PB-3 |
| D | 1 | Note-fork mechanism (L0 v2 dep) inherited from L4/L5 plan |

---

## 3. Cross-reference with FOL project

WSD and FOL overlap on at least 5 propositions (see `projects/fol/ANALYSIS.md` §3):

| Topic | WSD position | FOL position | Resolution path |
|---|---|---|---|
| `sense-correlations` role-graph | Proposed (coordinated_change_L2 §6) | Proposed (FOL B10) | Same; ship once |
| `learned-parameters` role-graph | Proposed (coordinated_change_L2 §6) | Proposed + split per FOL pushback #4 | If FOL pushback #4 accepted, WSD uses split |
| WSD decomposition | ACCEPT decompose into SCMS / MSUR / ALS (coordinated_change_L3 §3-§4-§6) | ACCEPT decomposition per FOL pushback #3 | Aligned |
| Coherence Loop fate | §6.1 contested; depends on resolution | §2.2 contested per pushback #2-#5 | Same blocker; resolve once |
| 7 L4 critique pushes | C-L4-1 through C-L4-7 explicit picks | Pushback #1, #2, #5 ACCEPT-recommendations | WSD has stated picks; FOL accepts/co-occurs |

**Recommended chat ordering** (also documented in `projects/fol/FUTURE_CHAT_PROMPT.md` §6):
- Skill-acquisition process design ships FIRST.
- WSD chat ships SECOND (has explicit ACCEPT picks on L4 pushes — load-bearing for FOL).
- FOL chat ships THIRD (inherits WSD resolutions on shared propositions).

---

## 4. Cross-reference with Phase 38 19-item carry-forward + R0 slate

| Phase 38 / R0 item | WSD intersection |
|---|---|
| R0-PB-1 (Plan vs design-resolution; 7 critique pushes) | WSD's C-L4-1 through C-L4-7 are explicit resolution picks on those 7 pushes. WSD chat is downstream of (or coordinates with) the L4/L5 plan chat that ratifies them |
| R0-PB-2 (carry-forward scope absorption) | WSD's L2 + L3 surface absorbs multiple items: per-Local `ProblemTraceSink`, `add_type_compat`, `include_deprecated`, `validate_xref` body |
| R0-PB-3 (L4 vs L5 ordering; L5 gated on note-fork) | WSD §5.3-§5.5 + L4 ALS scope-tightening intersect L5's gating |
| R0-PB-9 (`sense-correlations` + `learned-parameters` disposition) | WSD coordinated_change_L2 §6 ships both as additions; WSD-chat resolution implies R0-PB-9 default = (a) ship both |
| R0-PB-10 (single-tenant vs multi-tenant L4 scope) | WSD §6.3 multi-domain ontology = multi-tenant; v3+ defer recommendation per WSD-PB |

---

## 5. WSD's own §6 four blockers (need MindsOS-internal resolution)

These block WSD spec independently of skill acquisition:

- **WSD §6.1 — Coherence loop fate.** Three resolutions; (a)/(b)/(c) per source. Same blocker as FOL pushback #2-#5; resolve once.
- **WSD §6.2 — FOL Layer design phantom dependency.** "L4 notes say `sense-correlations` and `learned-parameters` were 'added 2026-04-23, from FOL Layer design.' Grepping the workspace turns up no FOL Layer design doc." **RESOLVED in this housekeeping:** the FOL Layer design materials are now at `projects/fol/source/`. WSD §6.2 is no longer a blocker.
- **WSD §6.3 — Multi-domain ontology support (medical / legal / technology).** Recommendation: defer to v3+. Confirm or refute in skill-acquisition chat.
- **WSD §6.4 — Ontology learning (relation induction, hierarchy inference).** Recommendation: defer to v3+. Confirm or refute.

---

## 6. Documented design pushbacks (deferred to future chat)

WSD's own pushbacks already documented in source materials; the ANALYSIS chat doesn't re-litigate them. Analysis-side corrections:

- **Analysis-PB-A1** — WSD §6.2 phantom-FOL dependency is resolved by this housekeeping. Notable for the future chat.
- **Analysis-PB-A2** — The 50+ proposed ADRs in `pending_adrs/L{0,1,2,3,4}.md` need to be triaged for ratification ordering. Many depend on others (e.g., L3 hyperedge-model A.1 depends on L1 hyperedge-edge support).
- **Analysis-PB-A3** — WSD's C-bin includes some **architectural reframes** (capacities-as-hyperedges, monitor lifecycle ownership) that are bigger than typical additive proposals. These are not skill-specific; they're MindsOS-architecture-level. Ratifying them in a WSD chat is scope mis-fit.
- **Analysis-PB-A4** — WSD's 16 use cases in `WSD_USE_CASES.md` (116KB) need separate review; they may surface additional propositions not in the per-layer coordinated_change docs.
- **Analysis-PB-A5** — Phase 31 shipped resident lifecycle on CapacityLayer (`start_resident`/`stop_resident`). WSD C-L3-2 wants L4-owned lifecycle. The MindsOS shipped form was a design choice per Phase 31; un-doing it requires a Phase 31 supersession or amendment, not just a forward-looking addition.

---

*End of analysis. See `FUTURE_CHAT_PROMPT.md` for the design-resolution chat seed.*
