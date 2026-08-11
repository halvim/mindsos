# ARC — Skill Intake Probe applied (validation run)

Ran `SKILL_INTAKE_PROBE.md` v0.1 against `MindsOS-arc:projects/arc_demo/intelligence_demo/arc1/`.
Doubles as the "organize the ARC project" proposal. **Caveat:** ARC is already MindsOS-shaped, so this
run tests the *alignment* half against ground-truth, not foreign extraction.

## Phase 0 — Triage (21 docs, ~5.2k LOC)

| Bucket | Files |
|---|---|
| **skill-content** | ONTOLOGY.md, LEXICON.md, PIPELINE.md, PIPELINE_DECISIONS.md, SOLVE_PIPELINE.md, REASON_STAGE_HYPOTHESES.md, VOCAB_CONSOLIDATION.md, CAPACITY_ROADMAP.md, ICECUBER_DSL.md |
| **code** | `spike/` (arc_solver, arc_capacities, arc_grids, arc_profile, arc_gates, arc_search, arc_metagraph, bg_ground) + `solve/` (pipeline, evaluate, runner) |
| **exhaust** | 6× `*_NEXT_CHAT_PROMPT.md`, CAPACITY_CREATION_GUIDE.md (how-to), README.md |
| **artifact** | arc_viewer/arc_graphs/arc_debug .html, *.svg, *_map.png, arc1.json, arc1_data.js, arc_debug_data.js |

**Redundancy flag:** PIPELINE / PIPELINE_DECISIONS / SOLVE_PIPELINE overlap on the reason stage — three records, one topic.
**Lineage flag:** two code paths — `spike/` (exploratory + debug UI) and `solve/` (clean harness). The registered topology (`arc_capacities.py`) and the executable `arc_solver.py` are **disjoint** (solver never invokes the layer).

## Phase 2 — K-table (filled)

| K | ARC component | Source |
|---|---|---|
| K0 | `arc.raw_task` | `DS_RAW_TASK`, arc_capacities.py:82 |
| K1 | ARC-1, 2D, monochrome atom; dataset = fixture | README, arc1.json |
| K2 | ~40 terms | LEXICON.md, ONTOLOGY §2 |
| K3 | Region-rooted class model, 4 role families, located/normalized axes | ONTOLOGY §1–2, §4 |
| K4 | 30 DataStates (`DS_*`, realm `arc`) | arc_capacities.py:82–155 |
| K5a | perceiver/profiler/detector/generator/predicate/comparator/reasoning contracts | `_*_capacities()`, ONTOLOGY §3 |
| K5b | real compute inline (`arc_grids.py`) + stub-registered | arc_grids.py; D3 |
| K6 | phase_1 mandatory sweep vs reason-time; profile = value-filter (D7) | PIPELINE, PIPELINE_DECISIONS §0 |
| K7 | induce→search→verify→apply\|abstain; MDL; ConjunctionFinder | PIPELINE_DECISIONS §1, §5 |
| K8 | provenance-to-`rawtask` invariant (design-stated; checker not built) | arc-grounding-invariant |
| K9 | task #8 (`05f2a901`) solves end-to-end | arc_solver stages 1–6 |

## Fit report (R1–R6)

- **R1** ✅ no higher-order dispatcher (GF-2 enforced; shared pure helpers only).
- **R5** ⚠️ **violation** — `find_pipeline` (BFS) composes multi-input reason caps unsoundly (D-A); needs the `ConjunctionFinder`. The one real fit problem.
- **R6** ⚠️ **partial** — most reason bodies inline/off-graph → provenance is *transcribed, not executed*. `touching_delta` is the only executed-grounded cap.
- R2/R3/R4 ✅ (4 role families incl. attribute §17; compositional hyperedge; dont-know contracts per cap).

## Gaps

- K8 checker unbuilt (invariant stated, not mechanized).
- K7 search/apply partial (#8-only; generalize-beyond-#8 unbuilt).

## Stage read

**Mid-prototype (Stage B).** Solves one use-case, bodies inline, layer not wired, format still churning. Not commit-ready: R5 open, R6 partial, K8 absent, K9 = single task.

---

## What this run says about the probe (v0.1 → v0.2)

- **Worked:** triage cleanly separated exhaust (6 prompts) + caught both the doc redundancy and the spike/solve lineage split; K-table recovered ARC's known structure; R5/R6 surfaced the two real fit problems.
- **Weak spots to fix in v0.2:** (1) the probe found ARC's MindsOS structure because it was *pre-labeled* — extraction rigor is untested (needs the foreign target). (2) No step distinguished *transcribed vs executed* grounding — I had to know MindsOS to spot R6; add an explicit "does the runtime actually call this, or is it registered-only?" check. (3) "Stage read" was inferable but the rubric didn't ask for the evidence — make it require citing why.
