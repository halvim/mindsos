# arc1/solve — pipeline phases

`./arc solve <task#|task_id> <step>` runs the pipeline up to `step`, recomputing
every phase in-memory on each invocation (no checkpoints). `./arc solve --phases`
lists the phases with descriptions. Phases are **editable** — change a body in
`pipeline.py`.

Each phase prints `about` (the phase description — see `STEP_DESC`), `uses`
(input ctx + the real **function chain**), `→ future` (the proposed MindsOS
feature + location — see `STEP_TARGETS`), `produces`, and `result`. Phases 1–4
render a **multi-line** per-pair `result` (perceive summary; correspondence
tiers; subdivision partitions; addition evidence); the rest are single-line.

The pipeline is **10 phases, fully general** (2026-07-01): 1–8 perceive →
profile → hypothesis → **candidate rules**; 9 **Rules Selection** (minimum rule
set, or `I don't know how to solve this task`); 10 **Solve Task** (apply the set
to the test input → answer + explanation). The #8-specific hardcoded tail (old
stages 10–16: Background/Roles/Persistence/Selectors/Rule/Verify/Apply) was
**retired** — its reasoning is now general (bg from phases 1–9, selectors from
phase 8). The monolithic `arc_solver.build_solver` (the same `stage_*` functions)
survives only for the `arc_debug` solver panel + the D3 spike.

Scope tags: **general** = works for any task · **general\*** = general but uses a
v1 assumption.

| # | phase | scope | functions used |
|---|---|---|---|
| 1 | Input + Perceive | general | `arc_grids.get_task` · `arc_profile.grid_summary` → `extract_objects`, `extract_points`, `normalize_shape`, `palette`, `dimension` |
| 2 | Profile (profilers) | general | `arc_profile.build_profile`(`match_pair`, `profile_sweep`, `hypotheses`) · `arc_search.task_tokens`(`same_cell_count_pairs`, `same_bbox_area_pairs`) |
| 3 | Subdivision | general\* | `arc_grids.subdivisions` → `inset`, **bidirectional + bg-agnostic** (object = ≥2 disjoint insets, `split` in→out or `assemble` out→in, points included). Also computes the **input-only enclosed regions** (`arc_grids.enclosed_bg_cells` — bg cells that can't reach the border through bg, 4-conn; the cell analogue of `inside`) into `ctx["enclosed"]`, so later phases consume them rather than re-deriving (phase 8 recolor) |
| 4 | Component Re-Comparison | general\* | `pipeline.step_objcomp` over step-3 findings → per sub-piece (a **full object**) `same_object`/`same_point` (colour kept) or **`recolored`** (colour changed — same cells), tagged `[from split]`/`[from assemble]` |
| 5 | Comparators Hypothesis | general | `arc_search.forall_comparators` over per-pair sets — the comparators triggering on **ALL** demo pairs (∀, add-only); each parametric comparator reports its **per-pair parameter + ∀ conclusion** (`moved`→`(dr,dc)`, `rotated`→deg, `reflected`→`H/V-axis`, `recolored`→`from→to`, `touching_delta`→`gained/lost`; `multi`=within-pair disagreement; `inside` bare). Transforms over the full grids; `recolored` also fires off subdivision sub-pieces; **`touching`/`touching_delta` exclude the bg colour when that grid's bg is resolved; `inside` = ray-based containment (`arc_grids.contained_pairs`): `a inside b` iff every ray from every cell of `a` to the grid edge (4 dirs) passes through object `b` (captures nested containment O1⊃O2⊃P0, unlike first-diff). `bg_resolved` flag — **True** (bg known, phase 5/7): a bg-coloured object is a valid container only if itself contained (ambient bg excluded, enclosed pocket kept); **False** (perception/∃ token): raw, no bg filter. Replaces `inside_pairs` as the perception relation + ∃ token**; ∃ token 268/400 |
| 6 | Task Patterns | general\* | `arc_solver.task_patterns` over the phase-2/4 `same_*` matches with subdivided wholes replaced by their sub-pieces — patterns holding ∀ demo pair (addition / subtraction / recoloring / moving / rotation / reflection); `moving` = dims+palette preserved + ≥1 moved; **no bg exclusion** (bg objects participate); bg from `bg_cand` only sets the `bg not resolved` suffix |
| 7 | Motivations | general\* | `arc_solver.motivations` — per **generator**, the goals/reasons holding ∀ demo pair (add-only): discrete (recolor/rotate/reflect) = a constant-parameter reason (`recolor yellow`) + a predicate condition-reason (`… if touching`/`… if inside`, transformed set == predicate set); continuous `move` = a reason (`move (dr,dc)`) and/or a goal (`move [<dir>] until touching`). Tested by applying the generator. Display/hypothesis |
| 8 | Rules | general\* | `arc_solver.rules` — emit **candidate** rules, one per generator+param+condition. **MOVE** (`move [<mover>] to [<target>] until touching` #8 / `move [<sel>] by (dr,dc)`) and **cell-RECOLOR** (`recolor [enclosed] {colour}`, #2) are self-contained **complete** candidates (marked `✓ complete`, ∀-verified at assembly). **object-RECOLOR** emits one candidate per **necessary** single condition (`recolor {c} if inside` / `… if biggest` / `… if colour=…` / `… if shape=…` — every recoloured object satisfies it ∀), which need **not** reproduce the output alone → phase 9 conjoins them. rotate/reflect deferred. Display/hypothesis |
| 9 | Rules Selection | general\* | `arc_solver.select_rules` — the **minimum candidate set** reproducing every demo (apply set to `input_k`, match `output_k`, ∀): singles first (a complete candidate = size 1), then **2×2 → 3×3 conjunctions** of same-param `recolor_obj` conditions (intersect target sets); first covering set wins; **no covering set → `I don't know how to solve this task`**. Conjunction only; cross-generator composition deferred. Does **not** apply to the test (that is phase 10) |
| 10 | Solve Task | general\* | `arc_solver._apply_candidate_set` — apply the phase-9 rule set to the **test input** → answer grid, with an explanation summarising the rule set (`solved by: {rule set}`). Recolor-enclosed recomputes the test enclosure at the solver bg if phase 3 abstained. `matches withheld test` ✓/✗ only when the dataset carries the withheld output. Abstains `I don't know how to solve this task` when phase 9 found no set. The general replacement for the retired #8 verify/apply stages |

**Subdivision, component re-comparison, comparators hypothesis, task pattern,
motivations (phases 3–7) are hypothesis/display steps** — they read the
phase-2 profile and narrate what the task is doing. Phase 8 (rules) emits
**candidate** rules (complete move/cell-recolor + per-condition object-recolor);
**phase 9 (rules selection)** picks the **minimum candidate set** that reproduces
every demo (or abstains `I don't know how to solve this task`); **phase 10 (solve
task)** applies that set to the test input → answer + explanation. Phases 8–10
are the general solver (they replaced the retired #8-specific tail). Phase 3 (subdivision) detects a disjoint cover in
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
general; 3/4/6/7/8/9/10 are general\* (v1 assumptions — the move/recolor rule
model). **No phase is #8-specific any more** (the hardcoded tail was retired
2026-07-01). The whole pipeline runs in-memory and is recomputed from scratch on
every invocation (no checkpoints).

**Background Color line (phases 2–10).** Each phase ≥2 prints a `Background Color`
step-block line rendering `bg_advance`'s per-grid `bg_cand`: `Pair{i}.bg=X` when
one side resolves to X **and** X is a candidate on the other side (option C), else
`In{i}.bg={…} · Out{i}.bg={…}`; `test.bg={…}` always (singletons bare, multi in
braces). The bg model adds **Phase Rule 4** (`arc_solver.bg_advance`): remove
same_shape+same_color components at phase 2 (objects) and phase 4 (sub-pieces).
See `PIPELINE_DECISIONS.md` §4 (2026-06-28 cont. entry) for the full bg model.
