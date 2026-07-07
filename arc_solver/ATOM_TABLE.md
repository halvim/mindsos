# ARC Atom Table — DataStates → Transitions → Pipelines

**Status:** v0.2 · working draft 2026-07-06 · edit-as-we-go
**2026-07-07 update:** ARC committed to **real registration** (execute comparators via `invoke`,
reopening D3). C1's operand shape is now spec'd + validated → `PART5_OPERAND_SPEC.md`; the core
track is a **BUILD** (C4 + Part-5/5a + C3). See `PIPELINE_DECISIONS.md §4` (2026-07-07) + `CORE_REQUESTS.md` Disposition.
**Goal (this chat):** the `arc_solver`/`arc_profile`/`pipeline.py` code is imperative Python
*mimicking* capacities — it is **not** organized as DataState transitions. `arc_capacities.py`
is a **shim** that registered transitions and got some wrong. This table **extracts the true
DataStates + transitions latent in the solver code** and proposes correct MindsOS registration.
ARC is a *user* of the core; every inconsistency it hits is a core inconsistency to fix once,
for all brains. Companion: `ONTOLOGY.md`, `PIPELINE_DECISIONS.md` §4/§5.

**NOT folded into `ONTOLOGY.md` yet** — discussion surface.

---

## Definitions (locked this chat)

- **Capacity = a DataState transition** (`consumes → produces`), not a function. Its body must
  actually realize that transition.
- **L3 capacity ✓** — a clean single-shot transition the core supports today (1→1, or N *different*
  input types → outputs). `find_pipeline` composes it.
- **L3 transition — blocked-by-C1** — a real transition, but takes **two operands of the same
  DataState type** (e.g. Object×Object). The core keys inputs by DS-IRI, so it can't express the
  arity. Real; needs a **core change** (C1 = §5 Part 5).
- **L4 process** — **not** a transition: a fold / per-pair iteration / cross-phase aggregation /
  search. It *orchestrates* capacities but is not one. Provenance lives in **L5 chain artifacts**
  (Plan → Pipeline → PipelineRun → TaskRun), **not** an L3 capacity registration. The shim
  currently mis-registers these as capacities with fiction bodies — that is the inconsistency.
- **Layer of a datum:** L2 = class def · L3 = DataState *type* · L5 = per-task *value*.
- **Group / member (C4):** a `*` DataState is a **group** (list/set) whose members L4 iterates
  individually; its singular is the **member** type. Group and member are *distinct* DataState types
  (`objects*` ≠ `object`), so the finder never bridges them — L4 owns the unpack loop. This types the
  L3→L4 iteration seam and is why runtime fan-out needs **no** finder cardinality (the old C2).

---

## How to read this doc

- **Table 0** is the one to read first: `in_ds → capacity → out_ds`. Every entry is an **L3
  capacity** — there are no "L4 capacities." What varies is only **where L4 routes each ds**.
- **Home** legend: **`L3✓`** = registerable today · **`L3·C1`** = a real capacity *blocked* on core
  change C1 (two operands of the same type; ships today as a single-input fiction).
- **Routing tag** on each ds (L4's binding choice; the capacity itself is location-agnostic):
  `[in]` task input · `[pipe]` wired from a predecessor cap's output (find_pipeline) ·
  `[L5]` mental model · `[L2]` knowledge store (unused in ARC v1).
- `×` = two operands of the same type (C1). `*` = a **group** DataState whose members L4 iterates;
  singular = its **member** type (C4). `⟳` = an L4 unpack-and-iterate seam.
- **Known pipelines** table = the compositions L4 selects/calls per task.
- Tables A/B/C = detail views (DataStates, shim-drift, per-phase). Skip on a first read.

---

## Table 0 — in_ds → capacity → out_ds  ← read this first

Every row is an **L3 capacity**. The `[in|pipe|L5|L2]` tag on each ds is **L4's routing choice**, not
part of the capacity. No "L4 capacity" exists — decisions are L3; L4 only orchestrates + routes.

**Group registry (C4).** Each `*` group pairs with a singular member; L4 iterates the group to feed
member-consuming capacities.

| group | member | how the group forms |
|---|---|---|
| pairs* | pair | comprehend_task emits it |
| raw_grids* | raw_grid | comprehend_task emits it |
| grids* | grid | L4 collects (build_grid per raw_grid) |
| objects* | object | extract_objects emits it (segmentation) |
| points* | point | extract_points emits it |
| shapes* | shape | L4 collects (extract_shapes per object) |

**Perceive — L3✓ (per grid; `⟳` = L4 iterates a group)**

| in_ds | capacity | out_ds |
|---|---|---|
| raw_task[in] | comprehend_task | task[L5], pairs*[L5], raw_grids*[L5] |
| raw_grid[L5] ⟳ | build_grid | grid[pipe] |
| grid[pipe] | extract_palette | palette[L5] |
| grid[pipe] | extract_objects | objects*[L5] |
| grid[pipe] | extract_points | points*[L5] |
| object[L5] ⟳ | extract_shapes | shape[L5] |
| perceived_grid[L5] | inside | inside[L5] |

**Generators — L3✓ (different input types → no C1)**

| in_ds | capacity | out_ds |
|---|---|---|
| object[L5], color[L5] | recolor | object[L5] |
| object[L5], move_transform[L5] | move | object[L5] |
| shape[L5], rotate_transform[L5] | rotate | shape[L5] |
| shape[L5], reflect_transform[L5] | reflect | shape[L5] |

**Decisions — L3✓ (inputs L5-sourced; different-type → no C1)**

| in_ds | capacity | out_ds |
|---|---|---|
| same_objects*[L5], move_transforms*[L5], same_points*[L5] | build_correspondence | correspondence[L5] |
| touchings*[L5], correspondence[L5] | touching_delta | state_change[L5] ⚠C3 |
| state_change[L5], objects*[L5] | synthesize_selector | selector[L5] |
| palette[L5], same_objects*[L5], same_points*[L5] | bg_deduction | bg_cand[L5] |
| profile[L5], bg_cand[L5], recomparison[L5], enclosed[L5] | emit_candidates | rules*[L5] |
| profile[L5], rules*[L5], enclosed[L5] | select_rules | selection[L5] |
| profile[L5], selection[L5], rules*[L5], enclosed[L5], raw_task[L5] | apply_solution | solve[L5] |

`⚠C3` = declared in_ds (touching, correspondence) ≠ what the body reads (pair, background) — the
truthful-contract violation. `bg_deduction` is re-applied per phase by L4 (cross-phase state).
`profile`/`enclosed`/`recomparison` are L5 MM state assembled by earlier caps + L4 control flow —
a decision cap sources them from L5. **No ∅-producer**: they're stored, then sourced.
`*` on a decision's in_ds = it consumes the **whole group** (the comparator emits one verdict per
call; L4 collects them into `same_objects*` etc. — C4).

**Comparators / profilers — L3·C1 (two same-type operands; L4 picks the pair from a group in L5)**

| in_ds | capacity | out_ds |
|---|---|---|
| grid[L5] × grid[L5] | compare_grid_dimension | dimension_delta[L5] |
| palette[L5] × palette[L5] | compare_palette | palette_delta[L5] |
| object[L5] × object[L5] | same_object | same_object[L5] |
| shape[L5] × shape[L5] | same_shape | same_shape[L5] |
| point[L5] × point[L5] | same_point | same_point[L5] |
| shape[L5] × shape[L5] | same_cell_count | same_cell_count[L5] |
| shape[L5] × shape[L5] | same_bbox_area | same_bbox_area[L5] |
| object[L5] × object[L5] | moved | move_transform[L5] |
| region[L5] × region[L5] | touching | touching[L5] |
| object[L5] × object[L5] | inset | inset[L5] |
| object[L5] × object[L5] | union | region[L5] |
| object[L5] × object[L5] | recolored | recolor_transform[L5] |
| shape[L5] × shape[L5] | rotated | rotate_transform[L5] |
| shape[L5] × shape[L5] | reflected | reflect_transform[L5] |

**One-line takeaway:** every row is L3; `L3✓` registers now, `L3·C1` once arity lands; the
`[in|pipe|L5]` tags are L4's routing; `⟳` is an L4 iteration seam (C4).

---

## Known pipelines & L4 processes

A **pipeline** = a composition of L3 capacities → a target. **Known** pipelines are recorded in
**L2 `promoted-pipelines`** and looked up by L4; `find_pipeline` is the **discovery fallback for
*unknown* compositions** (novelty), not the path for known ones. An **L4 process** is orchestration
that *selects pipelines + iterates groups + folds L5* — it is **not** a pipeline and is not recorded.

**Known pipelines (→ L2)**

| pipeline | composes | target |
|---|---|---|
| perceive (per grid) | comprehend_task → build_grid → extract_palette/objects/points/shapes, inside | perceived grid |
| pair-compare (per object-pair) | same_object / moved / … (C1-blocked) | verdict |
| selector-spine (#8) | touching_delta → synthesize_selector | selector |
| rule-synthesis | emit_candidates → select_rules → apply_solution | solve |

**L4 processes** are run by the **L4 substrate** (`mindsos_intelligence` Executor/Dispatcher — it
iterates, dispatches, holds the MM; **not** a capacity). The **control decisions** inside them are
**L3 capacities** in the `orchestration.*`/`planning.*`/`phase1.*` families (`mindsos_capacity/
builtins/`, registered like any cap, dispatched via the normal invoke path). So a "process" = the
substrate executing a plan that calls (a) ARC domain caps + (b) these orchestration-decision caps.
*(Shipped `planning.*` etc. are `placeholder=True`, opt-in — an installer swaps the real family;
ARC reuses or ships its own.)*

| process | substrate does | decision cap (L3) | target (→L5) |
|---|---|---|---|
| profile-build | iterate pairs, dispatch | pair-compare + aggregate | profile |
| subdivision | iterate, dispatch | inset + cover-reduce | enclosed |
| re-comparison | iterate sub-pieces | same_* | recomparison |
| bg-deduction | iterate phases, route/write | bg elimination rule | bg_cand |
| comparators-hyp | iterate, ∀-fold | the 6 comparators | hypotheses |

**C5 gap:** L2 `promoted-pipelines` is written by **user teaching (explicit entry)** now,
**dream-suggestion** later — **not** an auto-promotion loop. Today it has **no writer** and the finder's
promoted-path-lookup strategy is **deferred** (both verified). So known pipelines can't be L2-recorded
yet — ARC v1 sequences them in L4 code. **C5 = teaching/dream writer + lookup strategy** (ARC consumer).

---

## Table A — DataState reference (noun view)

Every DataState is an **L3 type** with an **L5 value** (class=L2 / type=L3 / value=L5). Kind: **atom**
(perceive), **verdict** (comparator output), **aggregate** (decision output / MM composite), **group**
(`*`, C4 — member type alongside). **Every DataState has a real producer — no ∅.**

**Atoms & groups (perceive)**

| ds (group* / member) | L2 class | produced by | consumed by |
|---|---|---|---|
| raw_task | Task (raw) | entry | comprehend_task, apply_solution |
| task | Task | comprehend_task | (task-level) |
| pairs* / pair | Pair | comprehend_task / unpack | per-pair processes |
| raw_grids* / raw_grid | Grid (raw) | comprehend_task / unpack | build_grid |
| grids* / grid | Grid | L4 collect / build_grid | extract_* , compare_grid_dimension |
| palette | Palette | extract_palette | compare_palette, bg_deduction |
| objects* / object | Object | extract_objects / unpack | comparators, generators, extract_shapes |
| shapes* / shape | Shape | L4 collect / extract_shapes | shape comparators, generators |
| points* / point | Point | extract_points / unpack | same_point |
| perceived_grid | Grid (bundle) | L4 assemble (E1) | inside |
| color | Color | input / param | recolor |

**Verdicts (comparator/profiler outputs; L4 collects members into `*` groups)**

| ds (member / group*) | from cap | consumed by |
|---|---|---|
| dimension_delta | compare_grid_dimension | profile |
| palette_delta | compare_palette | profile |
| same_object / same_objects* | same_object | build_correspondence, bg_deduction |
| same_shape / same_shapes* | same_shape | profile |
| same_point / same_points* | same_point | build_correspondence, bg_deduction |
| same_cell_count, same_bbox_area | same_* | profile (rot/refl pre-filter) |
| move_transform / move_transforms* | moved | move, build_correspondence |
| touching / touchings* | touching | touching_delta |
| inside | inside | hypotheses |
| inset | inset | subdivision |
| region | union | subdivision, rules |
| recolor_transform | recolored | (recolor pair broken — E7) |
| rotate_transform | rotated | rotate |
| reflect_transform | reflected | reflect |

**Aggregates (decision outputs / MM composites — stored in L5, sourced by later caps)**

| ds | from | consumed by |
|---|---|---|
| correspondence | build_correspondence | touching_delta, subdivision |
| state_change | touching_delta | synthesize_selector |
| selector | synthesize_selector | apply |
| bg_cand (background) | bg_deduction | emit_candidates |
| profile | profile-build | emit / select / apply |
| recomparison | re-comparison | emit_candidates |
| enclosed | subdivision | emit / select / apply |
| rules* | emit_candidates | select / apply |
| selection | select_rules | apply |
| solve | apply_solution | terminal |

### Atom-layer — L2 class + L5 value only, no L3 DataState (coarse-perceive pick)

| Class | L3 DataState | Why no L3 type |
|---|---|---|
| Cell | none | compositional (not derived); realized via `point` + `color`. Fine cells → L4 fold (not v1). |
| Coordinate | none | a value, not a derived class. |
| Color | `arc.color` (fix decl) | the one real edit; still no *new* DataState. |

---

## Table B — shim → true (the code fix-list)

What the shipped `arc_capacities.py` shim declares vs the true model, and the fix path. (Everything
is an L3 capacity; the old "L4 process / de-register / ∅-producer" framing is retired.)

| item | shim declares | true model | fix |
|---|---|---|---|
| 14 comparators/profilers | single input (arity fiction) | `X × X` two same-type operands | **C1** |
| touching_delta | consumes (touching, correspondence) | body reads (pair, background) | **C3** |
| groups | `arc.object` singular | `arc.objects*` group + `arc.object` member | **C4** |
| decision caps | reasoning cap, aggregate CONSUMES edges | L3 decision, in_ds **L5-sourced** (routing = L4) | keep (declared types ok) |
| orchestration decisions | inline in `arc_solver` | L3 caps in an `orchestration.*` family | register (post-C-reqs) |
| arc.color | "recolor param only" | Color value class | **E7** (code) |
| recolor ↔ recolor_transform | generator consumes `color` | detector/generator pair (ONTOLOGY #10) | **E7** |
| perceived_grid | no producer cap | L4-assembled bundle | **E1** (materialize cap or ∅-by-design) |
| arc.background | orphan (freq detector deleted) | drop or keep placeholder | **E2** |
| known pipelines | none (inline / find_pipeline) | recorded in L2 (teaching/dream) | **C5** |

---

## Reading it

1. **Every row is an L3 capacity.** What differs is the routing (`[in|pipe|L5]`, L4's choice) and the
   home (`L3✓` now, `L3·C1` after arity). There are no "L4 capacities" and no ∅-producers.
2. **The comparator/profiler family is one blocked class** — 14 real L3 transitions waiting on **C1**
   (same-type operand arity); they ship as single-input fictions today.
3. **Aggregates are normal L3 DataStates stored in L5.** A decision cap produces one; a later cap
   sources it from L5. The L4 substrate runs the plan; the orchestration *decisions* are L3 caps
   (`orchestration.*` family); the iterate/dispatch loop is substrate, not a capacity.

---

## Core-change requests (ARC as motivating consumer — filed, not built here)

File as **one** proposal extending PIPELINE_DECISIONS §5:

- **C1 — same-type operand arity.** A transition consuming two operands of the same DataState type
  (all comparators/profilers) can't be expressed; inputs are keyed by DS-IRI. = §5 **Part 5**
  (deferred). Un-defer, ARC = consumer of record. **Blocks the entire comparator family from
  honest registration.**
- **C3 — truthful invoke contract.** Declared `consumes` must equal what the body reads. = §5
  **Part 6** (validates inputs, shipped) **extended** to enforce declared==body. Without it,
  fiction bodies (touching_delta) pass. *(Note: if reason/solver caps are de-registered as L4
  processes, C3's ARC surface shrinks to the honest transitions only.)*
- **C4 — group/member DataState attribute** (`group=True` + `member_ds=<iri>`). Marks a list/set
  whose members L4 iterates individually; makes the L3→L4 iteration seam **typed + machine-visible**
  (group ≠ member, so the finder stays sound and L4 knows where to loop). Cheap (one additive
  attribute). ARC = first consumer. **Replaces the dropped C2** — fan-out needs no finder cardinality,
  just this typing.
- **C5 — known-pipeline record + lookup.** L2 `promoted-pipelines` has **no writer** and the finder's
  promoted-path-lookup strategy is **deferred** (both verified). To record known pipelines (perceive,
  etc.) in L2 and have L4 look them up — instead of re-discovering or hardcoding — needs the writer +
  the lookup Finder strategy un-deferred. ARC = consumer. Not blocking v1 (L4 can sequence knowns in
  code); the proper home for "known pipeline."
- **C2 — DROPPED** (superseded by C4). Runtime fan-out is L4 by design; C4 types the seam.

---

## Open edit points

- **E5** — de-register the 7 reason/solver caps to L4-process (chain-artifact provenance): confirm
  chain artifacts are the provenance home (verify when wired; if insufficient → new core request).
- **E6** — coarse vs fine perceive: keep `object`/`point` as bundle values (L3 1→1), or split to
  atoms (→ L4 fold)? v1 = coarse. Cell layer stays deferred.
- **E7** — `color` declaration fix + broken `recolor`↔`recolor_transform` pairing (ONTOLOGY #10).
- **E8** — after C1 lands: re-register the comparator family with real arity; drop the single-input
  fictions.
