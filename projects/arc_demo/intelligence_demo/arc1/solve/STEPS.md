# arc1/solve — pipeline phases

`./arc solve <task#|task_id> <step>` runs the pipeline up to `step`, recomputing
every phase in-memory on each invocation (no checkpoints). `./arc solve --phases`
lists the phases with descriptions. Phases are **editable** — change a body in
`pipeline.py`.

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
| 5 | Comparators Hypothesis | general | `arc_search.forall_comparators` over per-pair sets — the comparators triggering on **ALL** demo pairs (∀, add-only); each parametric comparator reports its **per-pair parameter + ∀ conclusion** (`pipeline._comparator_line`/`_conclusion`: `moved`→`(dr,dc)`, `rotated`→deg, `reflected`→`H/V-axis`, `recolored`→`from→to`, `touching_delta`→`gained/lost`; `multi`=within-pair disagreement, PB-l; `inside` bare); `touching_delta` (`arc_solver.touching_changes`, bg-forgotten) replaces intra-grid `touching`; **bg-colour objects excluded when bg is resolved** (`pipeline._drop_bg_grid`); ∃ `task_tokens` untouched |
| 6 | Task pattern | general\* | `arc_solver.task_patterns` → `_addition_evidence`, `_bg_color` (addition hypothesis from the profile) |
| 7 | Background + state-change | general\* | `arc_solver.stage_background` → `_bg_color` (pooled most-frequent — **v1 assumption**) · `touching_changes` (`_correspondence`, `_touch_set`) |
| 8 | Roles | semi | `arc_solver.stage_roles` → `_moved_in`, `_touch_set`, `_comp` (mover / target / background, demo-1) |
| 9 | Persistence + combo | ⚑ #8 | `arc_solver.stage_persistence` → `_moved_in` · `(move, touching)` combo verdict |
| 10 | Selectors | semi | `arc_solver.stage_selectors` → `_selectors_for` (minimal discriminative selector · tie → shape) |
| 11 | Rule | ⚑ #8 | `arc_solver.stage_rule` (static — `(move, touching)`, mover=irregular, target=square, slide-to-touch, **hardcoded**) |
| 12 | Verify | ⚑ #8 | `arc_solver.stage_verify` → `apply_rule` (each demo · exact-match all) |
| 13 | Apply test → ANSWER | ⚑ #8 | `arc_solver.stage_apply` → `apply_rule(test input)` → output grid (test output withheld) |

**Subdivision, component re-comparison, comparators hypothesis, task pattern
(phases 3–6) are hypothesis/display steps** — they read the phase-2 profile and
narrate what the task is doing; they are NOT consumed downstream (the #8 stages
compute independently). Phase 3 (subdivision) detects a disjoint cover in
**either direction** (bg-agnostic) — `split` (input object = ≥2 output insets) or
`assemble` (output object = ≥2 input insets), each finding tagged
`[split]`/`[assemble]`, points included. Phase 4 (component re-comparison)
re-compares each subdivision sub-piece (`O{i}.sub{k}.{color}`) against the
component it covers — `same_object`/`same_point` if colour kept, else
`same_shape`. Phase 5 (comparators hypothesis) lists the comparators that trigger
on **every** demo pair (∀); a comparator triggers on a pair iff it has ≥1
instance there, and the ∀ list is built add-only (the ∃ `task_tokens` driving the
gate/`./evaluate` are untouched). Each parametric comparator also reports its
**per-pair parameter** (one item per pair: the value if the pair's instances
agree, else `multi`) and a **∀ conclusion** (constant / directional / varies) —
see RESULT_OUTPUT_FORMAT.md "Phase 5 result body". The intra-grid `touching` is
replaced here by the `touching_delta` state-change (`arc_solver.touching_changes`:
a corresponded object's touching status flips gained/lost, bg-forgotten). Phase 6 (addition) flags dims+palette preserved
+ all non-bg inputs kept + a new object appears. `inset` is a registered
capacity-only predicate (no Search facet — near-universal); `subdivision` is the
phase process that consumes it inline (D3).

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
are attached by `arc_profile.attach_relations` (inside `build_profile`) and feed
the comparator hypothesis at phase 5. Profilers (phase 2) and comparators
(phase 5) are presentation slices of the single `build_profile` call.

**`same_shape` token vs display.** Phase 2 shows `same_shape` only for
non-identical `shape_groups` (real reuse). The `same_shape` *token* additionally
counts identical objects (`same_object ⟹ same_shape`, a wired skip — sound 0/400),
so the token (267/400) deliberately diverges from the display. See
`./arc solve --inferences`.

**Honest notes.** The perceive chain is *discovered* through the capacity layer
(`find_pipeline`); every phase *executes* inline (`arc_grids`/`arc_solver`),
because the solver is D3-inline and disjoint from the layer. Phases 1/2/5 are
general (3/4/6/7 general\*); 9/11/12/13 are #8-specific (the rule is hardcoded);
8/10 are move-model semi-general. The whole pipeline runs in-memory and is
recomputed from scratch on every invocation (no checkpoints).

**Background Color line (phases 2–13).** Each phase ≥2 prints a `Background Color`
step-block line rendering `bg_advance`'s per-grid `bg_cand`: `Pair{i}.bg=X` when
one side resolves to X **and** X is a candidate on the other side (option C), else
`In{i}.bg={…} · Out{i}.bg={…}`; `test.bg={…}` always (singletons bare, multi in
braces). The bg model adds **Phase Rule 4** (`arc_solver.bg_advance`): remove
same_shape+same_color components at phase 2 (objects) and phase 4 (sub-pieces).
See `PIPELINE_DECISIONS.md` §4 (2026-06-28 cont. entry) for the full bg model.
