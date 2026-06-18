# Next-Chat Prompt — ARC-1 Solver: generalize beyond task #8

This continues the ARC-1 task-solving pipeline. The reason stage now **SOLVES the end-to-end
use-case task #8 (`05f2a901`)** via a read-only **Solver** (stages 1–6). This chat **generalizes the
solver beyond #8**. Relitigate locked decisions only with the owner.

## Role / posture
Critical design reviewer for a complex system (MindsOS project posture): skeptical by default, terse,
no validation-to-be-polite, lead with the strongest concern, alternatives as a scannable menu, push
back on vague choices. Design before building; agree each step before wiring code; mock UI for
approval before implementing; one decision at a time. (The project instructions + PIPELINE.md working
style govern — follow them; do not restate them back.)

## Required reading (load before proposing anything — do NOT restate it back)
1. `CLAUDE.md` + `HANDOFF.md` (root) — shipped MindsOS state; the L0–L5 stack + vocabulary to reuse.
2. `intelligence_demo/arc1/PIPELINE.md` — **start here.** Read **"Reason-stage design — agreed
   2026-06-17"** (the locked convention), **Build progress** (everything built incl. the Solver and
   `touching`), **Parked problems P1–P6 + pushbacks PB-A/B/C**, and **Open items / FUTURE WORK**.
3. `intelligence_demo/arc1/ONTOLOGY.md` §4 (#1–16) + changelog — the binding world-model (v0.7). Do
   not re-open §4.
4. `intelligence_demo/arc1/spike/README.md` — spike navigation + how to run.
5. `intelligence_demo/arc1/spike/SOLVER_UI_MAP.md` — the Solver UI element→code map.
6. `intelligence_demo/arc1/spike/arc_solver.py` — the solver stages 1–6; **read it to see exactly
   what is #8-specific** (single mover, axis-aligned slide, no overlap, shape selector).
7. `intelligence_demo/arc1/ICECUBER_DSL.md` — seed-op reference (note: the locked convention replaced
   blind enumeration with greedy goal-seeking; see PIPELINE).
8. Memory: `arc-pipeline-design-state`, `arc-ontology-mindsos-grounding`.

## First action
Run `./run_spike` from the repo root (or `python -m intelligence_demo.arc1.spike.run_spike`; needs
`tomli` on py3.10). Open `intelligence_demo/arc1/spike/arc_debug.html` → **Solver** (the #8 run, stages
1–6) and **Map** (callout part-name maps per section, selector bar). Confirm the locked + built state
(do NOT restate it). Then open the first generalization decision (below) with a scannable menu and
your strongest concern — do not build yet.

## Goal — generalize the solver beyond #8
The Solver is honestly **#8-specific**, and the mandate from the start is "demonstrate, don't assume."
The likely order (owner picks; flag dependencies):
1. Pick a **second, structurally-different train task** and trace the solver against it — find exactly
   where it abstains or breaks (which stage, which assumption). Let the failure choose the next build.
2. Generalize **one** item from PIPELINE **Open items / FUTURE WORK**, e.g.: the objects→grid
   **serializer** (general; overlap/z-order = an L3 decision); the **roster** (states: aligned /
   inside / overlapping / touches-edge; transitions: expand / compress / rotate / reflect / recolor;
   selector family: max / min / center); the L3 **next-step proposer** (the boundary-keeper for the
   apply loop); the **filter / priority / teaching** mechanism; the equal-MDL **tie-break** prior.

## Constraints (binding)
Honor the locked **Reason-stage design** + the **L4 = control-only** boundary (all decisions are L3
capabilities; mechanical ops — the loop, topo-sort — are L4/substrate) + ONTOLOGY §4. Capability
bodies are still **not** executed via `invoke` (the spike computes via the body functions;
`find_pipeline` walks edges — decide if/when to cross into `invoke`). The Solver is **read-only option
A**: machine-proposed decisions are flagged → answered in chat → rerun. The persistence probe remains
an open prerequisite for any cross-session claim — flag if/when it blocks.

## Working style
One decision at a time, with pushback and a scannable menu. Mock UI (callout-map style, `maps/*.py`)
for approval before building. Document each locked decision into `PIPELINE.md` (Build progress /
Parked problems) and `ONTOLOGY.md` §4 if it is a world-model decision, as you go. Keep
`spike/README.md`, `spike/SOLVER_UI_MAP.md`, and the `spike/maps/*.py` callout maps current.
Regenerate `arc_debug_data.js` (`./run_spike`) after any code/data change.
