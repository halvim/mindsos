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
| 3 | Subdivision | general\* | `arc_grids.subdivisions` → `inset`, **bidirectional + bg-agnostic** (object = ≥2 disjoint insets, `split` in→out or `assemble` out→in, points included). Also computes the **input-only enclosed regions** (`arc_grids.enclosed_bg_cells` — bg cells that can't reach the border through bg, 4-conn; the cell analogue of `inside`) into `ctx["enclosed"]`, so later phases consume them rather than re-deriving (phase 8 recolor) |
| 4 | Component Re-Comparison | general\* | `pipeline.step_objcomp` over step-3 findings → per sub-piece (a **full object**) `same_object`/`same_point` (colour kept) or **`recolored`** (colour changed — same cells), tagged `[from split]`/`[from assemble]` |
| 5 | Comparators Hypothesis | general | `arc_search.forall_comparators` over per-pair sets — the comparators triggering on **ALL** demo pairs (∀, add-only); each parametric comparator reports its **per-pair parameter + ∀ conclusion** (`moved`→`(dr,dc)`, `rotated`→deg, `reflected`→`H/V-axis`, `recolored`→`from→to`, `touching_delta`→`gained/lost`; `multi`=within-pair disagreement; `inside` bare). Transforms over the full grids; `recolored` also fires off subdivision sub-pieces; **`touching`/`touching_delta` exclude the bg colour when that grid's bg is resolved; `inside` applies the background RULE — an enclosure is dropped only when its OUTSIDE container is bg (a shape floating in the bg field), a bg-coloured enclosed pocket is KEPT (`arc_grids.inside_bg_filtered`)**; ∃ `task_tokens` untouched |
| 6 | Task Patterns | general\* | `arc_solver.task_patterns` over the phase-2/4 `same_*` matches with subdivided wholes replaced by their sub-pieces — patterns holding ∀ demo pair (addition / subtraction / recoloring / moving / rotation / reflection); `moving` = dims+palette preserved + ≥1 moved; **no bg exclusion** (bg objects participate); bg from `bg_cand` only sets the `bg not resolved` suffix |
| 7 | Motivations | general\* | `arc_solver.motivations` — per **generator**, the goals/reasons holding ∀ demo pair (add-only): discrete (recolor/rotate/reflect) = a constant-parameter reason (`recolor yellow`) + a predicate condition-reason (`… if touching`/`… if inside`, transformed set == predicate set); continuous `move` = a reason (`move (dr,dc)`) and/or a goal (`move [<dir>] until touching`). Tested by applying the generator. Display/hypothesis |
| 8 | Rules | general\* | `arc_solver.rules` — assemble each phase-7 motivation into a rule, **generatively verified ∀**; abstain otherwise. **MOVE**: `move [<mover>] to [<target>] until touching` (#8) / `move [<sel>] by (dr,dc)` (selector-bound via `_selectors_for`, apply reuses `_slide`/`_render`). **RECOLOR**: `recolor [enclosed] {colour}` — fill the **enclosed background region** consumed from phase 3 (`ctx["enclosed"]`, input-only; #2). rotate/reflect deferred — no reliable in→out object correspondence. Display/hypothesis; the general precursor to the hardcoded #8 stages 13–15 |
| 9 | Background + state-change | general\* | `arc_solver.stage_background` → bg from `bg_cand` (`bg_advance`, injected) · `touching_changes` (`_correspondence`, `_touch_set`) |
| 10 | Roles | semi | `arc_solver.stage_roles` → `_moved_in`, `_touch_set`, `_comp` (mover / target / background, demo-1) |
| 11 | Persistence + combo | ⚑ #8 | `arc_solver.stage_persistence` → `_moved_in` · `(move, touching)` combo verdict |
| 12 | Selectors | semi | `arc_solver.stage_selectors` → `_selectors_for` (minimal discriminative selector · tie → shape) |
| 13 | Rule | ⚑ #8 | `arc_solver.stage_rule` (static — `(move, touching)`, mover=irregular, target=square, slide-to-touch, **hardcoded**) |
| 14 | Verify | ⚑ #8 | `arc_solver.stage_verify` → `apply_rule` (each demo · exact-match all) |
| 15 | Apply test → ANSWER | ⚑ #8 | `arc_solver.stage_apply` → `apply_rule(test input)` → output grid (test output withheld) |

**Subdivision, component re-comparison, comparators hypothesis, task pattern,
motivations, rules (phases 3–8) are hypothesis/display steps** — they read the
phase-2 profile and narrate what the task is doing; they are NOT consumed
downstream (the #8 stages compute independently). Phase 8 (rules) assembles a
selector-bound MOVE motivation and generatively verifies it reproduces every
demo output ∀ — the general precursor to the hardcoded rule stages 13–15. Phase 3 (subdivision) detects a disjoint cover in
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
a corresponded object's touching status flips gained/lost, bg-forgotten).
Phase 6 (Task Patterns) lists the patterns holding on **every** demo pair (∀),
read off the phase-2/4 `same_*` matches over the **augmented** universe (a
subdivided whole is replaced by its sub-pieces, each a full object, matched): a
component is **matched** if it has a same_object / same_point /
same_shape+same_color (moved) / same_shape+different_color (recolored) / rotated /
reflected correspondence (or it's a sub-piece covering a part), else
**unmatched**. addition = ≥1 unmatched output (dims preserved, palette
preserved/increased); subtraction = ≥1 unmatched input (palette
preserved/decreased); moving = ≥1 moved (dims+palette preserved);
recoloring/rotation/reflection = ≥1 of that family (dims preserved). bg objects
participate in matched/unmatched, **but the addition/subtraction unmatched-test
drops the resolved bg colour** (a resolved bg can't read as added/removed; an
unresolved bg still counts); `bg_cand` also sets the `· bg not resolved` suffix.
`inset` is a registered capacity-only predicate (no
Search facet — near-universal); `subdivision` is the phase process that consumes
it inline (D3).

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
general (3/4/6/7/8 general\*); 11/13/14/15 are #8-specific (the rule is
hardcoded); 10/12 are move-model semi-general. The whole pipeline runs in-memory and is
recomputed from scratch on every invocation (no checkpoints).

**Background Color line (phases 2–14).** Each phase ≥2 prints a `Background Color`
step-block line rendering `bg_advance`'s per-grid `bg_cand`: `Pair{i}.bg=X` when
one side resolves to X **and** X is a candidate on the other side (option C), else
`In{i}.bg={…} · Out{i}.bg={…}`; `test.bg={…}` always (singletons bare, multi in
braces). The bg model adds **Phase Rule 4** (`arc_solver.bg_advance`): remove
same_shape+same_color components at phase 2 (objects) and phase 4 (sub-pieces).
See `PIPELINE_DECISIONS.md` §4 (2026-06-28 cont. entry) for the full bg model.
