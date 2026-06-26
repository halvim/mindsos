# arc1/solve — pipeline steps

`./solve <task#|task_id> <step>` runs the pipeline up to `step`, checkpointing
each step to `runs/<task_id>/step-<n>.json`. A later `solve` reuses the cached
prior steps and (re)computes the requested step. Steps are **editable** — change
a step body in `pipeline.py` and its sub-steps below.

Scope tags: **general** = works for any task · **general\*** = general but uses a
v1 assumption · **semi** = runs generally but encodes the move-task model ·
**⚑ #8** = specimen-specific (hardcoded for 05f2a901; won't generalize).

| # | step | scope | sub-steps | engine |
|---|---|---|---|---|
| 1 | Input | general | load dataset · `get_task` → train pairs + test | inline |
| 2 | Perceive | general | per grid: `grid_summary` → objects · points · shapes · palette · dims | layer-discovered, executed inline |
| 3 | Profile / Match | general | per pair: `match_pair` (same_object/shape/point · moved) · touching · inside · recolored/rotated/reflected · dim/palette delta | inline |
| 4 | Background + state-change | general\* | `bg = _bg_color` (pooled most-frequent — **v1 assumption**) · correspondence C · `touching_changes` (gained/lost/maintained) | inline |
| 5 | Roles | semi | classify gained-pair endpoints → mover / target / background (demo-1) | inline |
| 6 | Persistence + combo | ⚑ #8 | persistence ∀demo (moved/same_object/same_shape/touching-gained) · `(move, touching)` combo verdict | inline |
| 7 | Selectors | semi | per role across demos: minimal discriminative selector · tie → shape | inline |
| 8 | Rule | ⚑ #8 | assemble `(move, touching)`; mover=irregular, target=square; slide-to-touch (**hardcoded**) | inline |
| 9 | Verify | ⚑ #8 | `apply_rule` on each demo · exact-match all | inline |
| 10 | Apply test → ANSWER | ⚑ #8 | `apply_rule(test input)` → output grid (test output withheld) | inline |

**Honest notes.** Only step 2 *discovers* through the capacity layer
(`find_pipeline`); every step *executes* inline (`arc_grids`/`arc_solver`),
because the solver is D3-inline and disjoint from the layer. Steps 1–3 are
general; 6/8/9/10 are #8-specific (the rule is hardcoded); 5/7 are move-model
semi-general. The checkpoint stores `profile` + `bg` + each stage output; the
per-pair `changes` (ref tuples) are **recomputed** from `profile`+`bg` each run
so JSON round-tripping stays safe.

**Checkpoints** are committed-optional (gitignored by default). Run dir:
`runs/<task_id>/`.
