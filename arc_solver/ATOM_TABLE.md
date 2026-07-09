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

> **⚠ SUPERSEDED (2026-07-07).** This decision-cap table is the *old shim shape*. It is being
> replaced by the **Decision-cap decomposition** section below (profile/bg/correspondence/
> touching_delta done; `synthesize_selector`/`emit`/`select`/`apply` pending). `build_correspondence`,
> `bg_deduction`, and `profile`-as-a-DataState are **killed** there. Kept here only for the diff.

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

## Decision-cap decomposition (v0.3 · 2026-07-07 · IN PROGRESS)

Core shipped **C1/C3/C4** (ADR-0198/0199/0200, tag `operand-arity-groups-readsmm-confirmed`). ARC now
decomposes the shim's decision caps into honest transitions. **`reads_mm=False` is the ARC default**
— L4 sources every input from L5 and passes it (comparators get operands via `operand_arity`).
`reads_mm=True` is reserved for MM-*navigation* (retrieval / path-finding / trace) — **none found in
ARC yet**. Sourcing an input from L5 ≠ `reads_mm=True`. `bg_colour` is **optional everywhere** (PB-4):
unresolved → no bg-exclusion (permissive); `select_rules` verification catches any bg-mis-inclusion.

**Status:** **full pipeline model complete** ✓ (7 decision caps + subdivision + re-comparison;
converged 2026-07-07). **`enclosed` deleted** — a "trapped background region" is just a bg-coloured
**object** that is `inside` another; `inside` (any-colour, already extracted) covers it, and the
recolor-fill rule recolors that contained object's cells. No `enclose_bg` cap.

### Killed / replaced
- **`profile`** (god-object DataState) → **deleted**; it *is* the L5 knowledge-MM. Consumers source
  the named DataStates below.
- **`build_correspondence`** (hardcoded 3-comparator fold) → **deleted** → `comparison_matrix` +
  `resolve_correspondence`.
- **`bg_deduction`** (cross-phase monolith) → **deleted** → bg-pipeline + `eliminate_bg_colour`.
- **`synthesize_selector`** monolith → split into `identify_roles` + `synthesize_selector`.
- **`emit_candidates`** → motivations-pipeline + per-family `assemble_*` (enumerate only; no verify).
- **`select_rules`** → **verifier pipeline** (verify moved out of emit).
- **`apply_solution`** → thin `apply_rule_set` on the test; `matches_withheld` lifted to **eval**.

### Foundational structure (PB-1): one `comparison_matrix`, computed once

Comparators run **once** over all in×out object pairs → `comparison_matrix` `{(in,out):[comparators
that fire]}` (L4-assembled). **`object_matches*` / `shape_matches*` / `point_matches*` are named
slices/views of it** — *not* separately computed. The strictest-first filtering ("same_shape matters
only where not same_object") lives in `resolve_correspondence`.

### Pipelines (everything L4 runs is a pipeline; iterate/fold are ARC caps; no separate "L4 process")

| pipeline | composition | out |
|---|---|---|
| **comparison-matrix** | all comparators × in×out pairs → matrix | `comparison_matrix` (+ slices) |
| **profile** (2 sub-pipelines ‖) | dims-vary (`compare_grid_dimension`* → `classify_variance`) + palette-vary (`compare_palette`* → `classify_variance`) | `dimension_variance`, `palette_variance` |
| **bg** (re-run on `objects*` change; explicit re-call v1) | init `bg_candidate` → `eliminate_bg_colour` → resolve `bg_colour` | `bg_candidate`, `bg_colour` |
| **correspondence** | `comparison_matrix` → `resolve_correspondence` | `correspondence` (1:1, carries transform) |
| **touching-change** | `touching`* → `touching_delta` (scoped ≥1 moved) | `state_change` |
| **motivations** (before selector) | `detect_move_motivation`, `detect_recolor_motivation`, … | `motivations` |
| **selector** | `identify_roles` → `synthesize_selector` (motivations = **soft** scope) | `selector` |
| **emit** | per-family `assemble_move` / `assemble_recolor` (use `selector`+`demos`) | `candidates*` (unverified) |
| **select_rules** (verifier) | iterate subsets → `combine_candidates` → per demo (`apply_rule_set` → `grids_equal`) → ∀-cover fold → first covering | `selection` |
| **apply_rule_set** (shared) | `resolve_selector` → dispatch by transform type → `move`/`recolor` generator | predicted grid |
| **apply_solution** (thin) | `apply_rule_set` on test grid | `answer` (`solve`) |
| **subdivision** | `inset` (from `comparison_matrix`, **both directions** — PB-C) → `detect_cover` (≥2 disjoint parts = whole; split/assemble) | `subdivision` |
| **re-comparison** | `subdivision` + colours → `classify_part_relation` (**reuses** `same_object`/`recolored` — PB-B) | `recomparison` |

`apply_rule_set`'s dispatch (transform type → generator) is a legit **find_pipeline**-composable step
(PRODUCES/CONSUMES, ONTOLOGY #10). `select_min_covering` is **not a cap** — minimality = the pipeline's
iterate-by-size order (PB-3). `apply_rule_set` is a **pipeline**, not a cap (PB-2).

### New / changed caps (all `reads_mm=False`)

| cap | in → out | note |
|---|---|---|
| `classify_variance` | `delta*` → `variance` | fold (dims + palette) |
| `eliminate_bg_colour` | (`bg_candidate`, `object_matches*`, `shape_matches*`) → `bg_candidate'` | fold; fixpoint on `objects*` change |
| `resolve_correspondence` | `comparison_matrix` → `correspondence` | 1:1; strictest-first; ambiguous → uncorresponded |
| `touching_delta` | (`touchings_in*`, `touchings_out*`, `correspondence`, `bg_colour?`) → `state_change` | C3-fixed; scoped ≥1 moved participant (incl. static neighbours) |
| `identify_roles` | (`state_change`, `correspondence`) → `roles` | per demo; mover/target; v1 slide-to-touch family |
| `synthesize_selector` | (`roles*`, object features, `motivations?`) → `selector` | ∀demo fold; per role; motivations soft-scope |
| `detect_*_motivation` | matches/`state_change`/variance → `motivations` | per transform family |
| `assemble_move` / `assemble_recolor` | (`motivations`, `selector`, `demos*`) → `candidates*` | enumerate only |
| `combine_candidates` | (`candidate`, `candidate`) → combined \| None | explicit combine (intersect targets); extensible |
| `grids_equal` | `grid × grid` → bool | verify match |
| `resolve_selector` | (`selector`, `grid`, `bg_colour?`) → target objects | "the red object" → actual objects |
| `∀-cover` | per-demo bool* → bool | generic all-true fold |
| `detect_cover` | `inset` slices (both dirs) → `subdivision` | ≥2 disjoint parts exactly cover a whole |
| `classify_part_relation` | (`subdivision`, colours) → `recomparison` | routes each part through `same_object`/`recolored` (no new comparator) |

### New DataStates (beyond the perceive/comparator ones)

| DataState | scope | produced by |
|---|---|---|
| `comparison_matrix` (+ `object_matches*`/`shape_matches*`/`point_matches*` slices) | per pair | comparison-matrix pipeline (L4-assembled) |
| `dimension_variance`, `palette_variance` | task | `classify_variance` |
| `bg_candidate` (refined), `bg_colour` | per grid | bg-pipeline |
| `correspondence` (1:1) | per pair | `resolve_correspondence` |
| `state_change` | per pair | `touching_delta` |
| `roles` | per demo | `identify_roles` |
| `motivations` | task | motivations pipeline |
| `selector` | task | `synthesize_selector` |
| `candidates*` | task | `assemble_*` |
| `selection` | task | `select_rules` |
| `answer` (`solve`) | test | `apply_solution` |
| `subdivision` | per pair | `detect_cover` |
| `recomparison` | per pair | `classify_part_relation` |

### Comparators (register with `operand_arity` per C1; `reads_mm=False`)
`same_object`, `same_shape`, `same_point`, `moved`, `rotated`, `reflected`, `inside`, `touching`,
`grids_equal`, … — each runs `component × component` (or `grid × grid`), filling `comparison_matrix`.

### Eval (outside the solve pipeline)
`matches_withheld` = `grids_equal(answer, withheld_output)` — a **scoring** step run only when the
known answer exists; **not** part of solving.

---

## Pipelines (what L4 runs)

**Everything L4 runs is a pipeline** — a composition of L3 capacities, *including* ARC-specific
**iterate/fold** caps (the fold cap **is** the domain decision cap, e.g. `classify_variance`). **There
is no separate "L4 process" category** (PB3): the L4 substrate (`mindsos_intelligence`
Executor/Dispatcher) only **walks** pipelines + holds the MM — it owns no logic. `decompose`-style
fan-out (iterate) and aggregate (fold) are **caps** in the pipeline, not substrate.

**Known** pipelines are recorded in **L2 `promoted-pipelines`** (C5, pending); `find_pipeline` is the
fallback for **unknown** compositions only. Meanwhile L4 code sequences the known ones. Detail for the
decision-side pipelines is in the **Decision-cap decomposition** section above.

Full composition detail is in the **Decision-cap decomposition** section above; this is the index.

| pipeline | target | status |
|---|---|---|
| perceive (per grid; L4 iterates `grids*`) | perceived grid | ✓ |
| comparison-matrix | `comparison_matrix` (+ match slices) | ✓ |
| profile (dims-vary + palette-vary) | `dimension_variance`, `palette_variance` | ✓ |
| bg | `bg_candidate`, `bg_colour` | ✓ |
| correspondence | `correspondence` | ✓ |
| touching-change | `state_change` | ✓ |
| motivations | `motivations` | ✓ |
| selector (`identify_roles` → `synthesize_selector`) | `selector` | ✓ |
| emit (`assemble_*`) | `candidates*` | ✓ |
| select_rules (verifier) | `selection` | ✓ |
| apply_solution (`apply_rule_set` on test) | `answer` | ✓ |
| subdivision | `subdivision` | ✓ |
| re-comparison | `recomparison` | ✓ |

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
| palette | Palette | extract_palette | compare_palette, bg-pipeline |
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
| same_object / same_objects* | same_object | `comparison_matrix` (cells) → correspondence, bg |
| same_shape / same_shapes* | same_shape | `comparison_matrix` → correspondence, bg |
| same_point / same_points* | same_point | `comparison_matrix` → correspondence, bg |
| same_cell_count, same_bbox_area | same_* | rot/refl pre-filter |
| move_transform / move_transforms* | moved | `comparison_matrix`, move (gen) |
| touching / touchings* | touching | touching_delta |
| inside | inside | `comparison_matrix` |
| inset | inset | subdivision |
| region | union | subdivision |
| recolor_transform | recolored | (recolor pair broken — E7) |
| rotate_transform | rotated | rotate |
| reflect_transform | reflected | reflect |

**Decision-side DataStates → see the Decision-cap decomposition section above.** The old aggregate
list (`profile`, `bg_cand`, `build_correspondence`/`bg_deduction` outputs) is **superseded**: `profile`
is killed (it's the MM); the real DataStates are `comparison_matrix` (+ match slices),
`dimension_variance`/`palette_variance`, `bg_candidate`/`bg_colour`, `correspondence`, `state_change`,
`roles`, `motivations`, `selector`, `candidates*`, `selection`, `answer`, `subdivision`,
`recomparison`. **`enclosed` is deleted** (a bg-coloured object `inside` another; `inside` covers it).

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
