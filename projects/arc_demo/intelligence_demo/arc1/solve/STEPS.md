# arc1/solve — pipeline phases

`./arc solve <task#|task_id> <step>` runs the pipeline up to `step`, checkpointing
each phase to `runs/<task_id>/step-<n>.json`. A later run reuses the cached prior
phases and (re)computes the requested one. `./arc solve --phases` lists the phases
with descriptions. Phases are **editable** — change a body in `pipeline.py`.

Each phase prints `uses` (input ctx + the real **function chain**), `→ future`
(the proposed MindsOS feature + location — see `STEP_TARGETS`), `produces`, and
`result`. Phases 1–4 render a **multi-line** per-pair `result` (perceive summary;
correspondence tiers; subdivision partitions; addition evidence); the rest are
single-line.

Scope tags: **general** = works for any task · **general\*** = general but uses a
v1 assumption · **semi** = runs generally but encodes the move-task model ·
**⚑ #8** = specimen-specific (hardcoded for 05f2a901; won't generalize).

| # | phase | scope | functions used |
|---|---|---|---|
| 1 | Input + Perceive | general | `arc_grids.get_task` · `arc_profile.grid_summary` → `extract_objects`, `extract_points`, `normalize_shape`, `palette`, `dimension` |
| 2 | Profile (profilers) | general | `arc_profile.build_profile`(`match_pair`, `profile_sweep`, `hypotheses`) · `arc_search.task_tokens`(`same_cell_count_pairs`, `same_bbox_area_pairs`) |
| 3 | Subdivision | general\* | `arc_grids.subdivisions` → `inset`, **bidirectional + bg-agnostic** (object = ≥2 disjoint insets, `split` in→out or `assemble` out→in, points included) |
| 4 | Component Re-Comparison | general\* | `pipeline.step_objcomp` over step-3 findings → per sub-piece `same_object`/`same_point` (colour kept) or `same_shape` (colour changed), tagged `[from split]`/`[from assemble]` |
| 5 | Task pattern | general\* | `arc_solver.task_patterns` → `_addition_evidence`, `_bg_color` (addition hypothesis from the profile) |
| 6 | Comparators | general | `arc_search.task_tokens` · `arc_grids.touching_pairs`, `inside_pairs`, `moved`, `recolored_pairs`, `rotated_pairs`, `reflected_pairs` |
| 7 | Background + state-change | general\* | `arc_solver.stage_background` → `_bg_color` (pooled most-frequent — **v1 assumption**) · `touching_changes` (`_correspondence`, `_touch_set`) |
| 8 | Roles | semi | `arc_solver.stage_roles` → `_moved_in`, `_touch_set`, `_comp` (mover / target / background, demo-1) |
| 9 | Persistence + combo | ⚑ #8 | `arc_solver.stage_persistence` → `_moved_in` · `(move, touching)` combo verdict |
| 10 | Selectors | semi | `arc_solver.stage_selectors` → `_selectors_for` (minimal discriminative selector · tie → shape) |
| 11 | Rule | ⚑ #8 | `arc_solver.stage_rule` (static — `(move, touching)`, mover=irregular, target=square, slide-to-touch, **hardcoded**) |
| 12 | Verify | ⚑ #8 | `arc_solver.stage_verify` → `apply_rule` (each demo · exact-match all) |
| 13 | Apply test → ANSWER | ⚑ #8 | `arc_solver.stage_apply` → `apply_rule(test input)` → output grid (test output withheld) |

**Subdivision, component re-comparison, task pattern (phases 3–5) are
hypothesis/display steps** — they read the phase-2 profile and narrate what the
task is doing; they are NOT consumed downstream (the #8 stages compute
independently). Phase 3 (subdivision) detects a disjoint cover in **either
direction** (bg-agnostic) — `split` (input object = ≥2 output insets) or
`assemble` (output object = ≥2 input insets), each finding tagged
`[split]`/`[assemble]`, points included. Phase 4 (component re-comparison)
re-compares each subdivision sub-piece (`O{i}.sub{k}.{color}`) against the
component it covers — `same_object`/`same_point` if colour kept, else
`same_shape`. Phase 5 (addition) flags dims+palette preserved + all non-bg
inputs kept + a new object appears. `inset` is a registered capacity-only
predicate (no Search facet — near-universal); `subdivision` is the phase process
that consumes it inline (D3).

**Operators in `./evaluate` (2026-06-27).** `inset` and `union` are now
`./evaluate` targets on a **show-only OPERATOR track** (occurrence + demands; no
Search-token cross-check). `union` is the first object **operator**
(`CATEGORY_OPERATOR`, output `DS_REGION`): ≥2 parts disjoint-cover a whole, both
directions (`split`=whole-in, `assemble`=whole-out), **bg-excluded**, built on
`inset`. Inference `union ⟹ inset` is a wired skip. Note: phase-3 `subdivision`
stays **bg-agnostic** and is the in→out *split* test only — the new *assemble*
direction is union-only (e.g. #46 `234bbc79`). See `./arc solve --inferences`
and PIPELINE_DECISIONS §4 (2026-06-27 union entry).

**Profiler / comparator split.** Phase 1 is **pure perception** — `grid_summary`
no longer computes `touching`/`inside`. Those intra-grid **comparator** relations
are attached by `arc_profile.attach_relations` (inside `build_profile`) and shown
under phase 6, where they belong. Profilers (phase 2) and comparators (phase 6)
are presentation slices of the single `build_profile` call.

**`same_shape` token vs display.** Phase 2 shows `same_shape` only for
non-identical `shape_groups` (real reuse). The `same_shape` *token* additionally
counts identical objects (`same_object ⟹ same_shape`, a wired skip — sound 0/400),
so the token (267/400) deliberately diverges from the display. See
`./arc solve --inferences`.

**Honest notes.** The perceive chain is *discovered* through the capacity layer
(`find_pipeline`); every phase *executes* inline (`arc_grids`/`arc_solver`),
because the solver is D3-inline and disjoint from the layer. Phases 1/2/6 are
general (3/4/5/7 general\*); 9/11/12/13 are #8-specific (the rule is hardcoded);
8/10 are move-model semi-general. The checkpoint stores `profile` + `bg` + each stage output + a
`_name_<n>` phase stamp (a layout change invalidates a stale checkpoint); the
per-pair `changes` (ref tuples) are **recomputed** from `profile`+`bg` each run
so JSON round-tripping stays safe.

**Checkpoints** are committed-optional (gitignored by default). Run dir:
`runs/<task_id>/`.
