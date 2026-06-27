# arc1/solve — pipeline phases

`./arc solve <task#|task_id> <step>` runs the pipeline up to `step`, checkpointing
each phase to `runs/<task_id>/step-<n>.json`. A later run reuses the cached prior
phases and (re)computes the requested one. `./arc solve --phases` lists the phases
with descriptions. Phases are **editable** — change a body in `pipeline.py`.

Each phase prints `uses` (input ctx + the real **function chain**), `→ future`
(the proposed MindsOS feature + location — see `STEP_TARGETS`), `produces`, and
`result`. Phases 1–2 render a **multi-line** per-pair `result` (perceive summary;
correspondence tiers); the rest are single-line.

Scope tags: **general** = works for any task · **general\*** = general but uses a
v1 assumption · **semi** = runs generally but encodes the move-task model ·
**⚑ #8** = specimen-specific (hardcoded for 05f2a901; won't generalize).

| # | phase | scope | functions used |
|---|---|---|---|
| 1 | Input + Perceive | general | `arc_grids.get_task` · `arc_profile.grid_summary` → `extract_objects`, `extract_points`, `normalize_shape`, `palette`, `dimension` |
| 2 | Profile (profilers) | general | `arc_profile.build_profile`(`match_pair`, `profile_sweep`, `hypotheses`) · `arc_search.task_tokens`(`same_cell_count_pairs`, `same_bbox_area_pairs`) |
| 3 | Comparators | general | `arc_search.task_tokens` · `arc_grids.touching_pairs`, `inside_pairs`, `moved`, `recolored_pairs`, `rotated_pairs`, `reflected_pairs` |
| 4 | Background + state-change | general\* | `arc_solver.stage_background` → `_bg_color` (pooled most-frequent — **v1 assumption**) · `touching_changes` (`_correspondence`, `_touch_set`) |
| 5 | Roles | semi | `arc_solver.stage_roles` → `_moved_in`, `_touch_set`, `_comp` (mover / target / background, demo-1) |
| 6 | Persistence + combo | ⚑ #8 | `arc_solver.stage_persistence` → `_moved_in` · `(move, touching)` combo verdict |
| 7 | Selectors | semi | `arc_solver.stage_selectors` → `_selectors_for` (minimal discriminative selector · tie → shape) |
| 8 | Rule | ⚑ #8 | `arc_solver.stage_rule` (static — `(move, touching)`, mover=irregular, target=square, slide-to-touch, **hardcoded**) |
| 9 | Verify | ⚑ #8 | `arc_solver.stage_verify` → `apply_rule` (each demo · exact-match all) |
| 10 | Apply test → ANSWER | ⚑ #8 | `arc_solver.stage_apply` → `apply_rule(test input)` → output grid (test output withheld) |

**Profiler / comparator split.** Phase 1 is **pure perception** — `grid_summary`
no longer computes `touching`/`inside`. Those intra-grid **comparator** relations
are attached by `arc_profile.attach_relations` (inside `build_profile`) and shown
under phase 3, where they belong. Profilers (phase 2) and comparators (phase 3)
are presentation slices of the single `build_profile` call.

**`same_shape` token vs display.** Phase 2 shows `same_shape` only for
non-identical `shape_groups` (real reuse). The `same_shape` *token* additionally
counts identical objects (`same_object ⟹ same_shape`, a wired skip — sound 0/400),
so the token (267/400) deliberately diverges from the display. See
`./arc solve --inferences`.

**Honest notes.** The perceive chain is *discovered* through the capacity layer
(`find_pipeline`); every phase *executes* inline (`arc_grids`/`arc_solver`),
because the solver is D3-inline and disjoint from the layer. Phases 1–3 are
general; 6/8/9/10 are #8-specific (the rule is hardcoded); 5/7 are move-model
semi-general. The checkpoint stores `profile` + `bg` + each stage output + a
`_name_<n>` phase stamp (a layout change invalidates a stale checkpoint); the
per-pair `changes` (ref tuples) are **recomputed** from `profile`+`bg` each run
so JSON round-tripping stays safe.

**Checkpoints** are committed-optional (gitignored by default). Run dir:
`runs/<task_id>/`.
