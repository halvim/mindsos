# ARC track — status & index

**Status:** Step 1 (Ontology) COMPLETE; **Step 2 (Task-Solving Pipeline) — reason-stage convention
LOCKED; end-to-end Solver SOLVES the use-case task #8** (updated 2026-06-17). This folder is the ARC
foundation for the intelligence demo (see `../DEMO_BUILD_NEXT_CHAT_PROMPT.md` for the binding demo
contract). The ontology work here is the Skill-Acquisition byproduct the pipeline builds on.

**Pipeline progress (2026-06-17):** `ONTOLOGY.md` is at **v0.7** (decisions §4 #1–16). perceive +
profile + induce built; the `touching` intra-grid predicate is built. The **reason-stage convention
is LOCKED** (transition∘state goal-conditioned rules; greedy goal-seeking apply; MDL rule-set) and a
read-only **Solver** (`spike/arc_solver.py`, stages 1–6) **solves task #8 (`05f2a901`) end-to-end**
(verify 3/3 demos + produced test output = withheld answer). **Next phase: generalize beyond #8.**
Canonical records: `PIPELINE.md` ("Reason-stage design — agreed 2026-06-17" + Build progress + Parked
problems), `ONTOLOGY.md` §4, `spike/SOLVER_UI_MAP.md`. Next-chat prompt: `SOLVER_NEXT_CHAT_PROMPT.md`.

## What's here

| File | What it is |
|---|---|
| `arc1.json` / `arc1_data.js` | ARC-AGI-**1** dataset (400 train + 400 eval), per-task input/output pairs. Sourced from the `arckit` PyPI bundle (verified canonical ARC-1, *not* ARC-2). |
| `arc_viewer.html` | Standalone puzzle browser — pick any task, train/eval toggle, hide-answer quiz. |
| `LEXICON.md` + `arc_lexicon_map.svg` | The named terms + definitions (MindsOS L2 `lexicon`). Map = the detailed visual. |
| `ONTOLOGY.md` | **The canonical world-model record** (v0.4). Class+relationship model (L2 `ontology`), capacity→family map (§3), **resolved-decisions table (§4 #1–14)**. |
| `PIPELINE.md` | **The pipeline design record.** Stage decomposition, locked perceive + profile capacities, layer discipline, reason-stage backlog. |
| `ICECUBER_DSL.md` | Full DSL of the 2020 ARC winner (`top-quarks/ARC-solution`) — reference for the seed-operation freeze. |
| `arc_graph_L2_ontology.svg` · `_L3_capacity.svg` · `_L5_mm_instance.svg` | **Static layer graphs — STALE** (pre-pipeline export; `arc_graphs.html` is the source of truth). |
| `arc_graphs.html` | Interactive viewer of all three graphs (updated this chat) — draggable nodes, Edit/Lock, zoom. |
| `spike/` | **The runnable spike** — live `CapacityLayer`, perceive/profile/induce capabilities, hypotheses, Arc metagraph, and the `arc_debug.html` human interface. See `spike/README.md`. |
| `PIPELINE_NEXT_CHAT_PROMPT.md` | **Opening prompt for the next chat** (continue the pipeline — reason stage). |

## What was decided (do not relitigate)

All locked decisions are in **`ONTOLOGY.md §4`** with rationale throughout the file.
Headlines: OWL structure (no DOLCE); composition = native `compositional` hyperedge;
monochrome `Object` atom + `Group` via `add`; `Shape` = colorless connected `PointSet`
*individual*; roles = `<family>:<role>` subproperties (compositional/relational/functional);
is-a split (`subclass_of`/`instance_of`/`exemplifies`); relations computed by capacities +
materialized into the task MM; capacities map onto the shipped L3 families.

## Open items carried forward

- **Reason stage** — induce → search → verify → apply | abstain (the next chat; see `PIPELINE.md`).
- **Seed operation set freeze** — freeze the minimal basis at the `id`-variant level using `ICECUBER_DSL.md`; decide type-unification vs the split-class ontology. Blocks `search`.
- **Verify DataState realm names** against the live L3 when an instance is stood up (the `arc` realm).
- **Persistence probe** (build-order step 1) — minted capacity + `learned-parameters` survive a restart? Still an open prerequisite for any cross-session claim.
- Re-export the static `arc_graph_*.svg` from `arc_graphs.html` (currently stale).

## Next phase

Generalize the solver beyond task #8 — see `SOLVER_NEXT_CHAT_PROMPT.md`. (The earlier reason-stage
prompt `PIPELINE_NEXT_CHAT_PROMPT.md` is superseded.)
