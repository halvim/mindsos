# ARC-1 Solver — Pipeline Design

**Status:** updated **2026-06-17**. Perceive + Profile + induce built; `touching` intra-grid predicate
built. **Reason-stage convention LOCKED** — see **"Reason-stage design — agreed 2026-06-17"** below
(transition∘state goal-conditioned rules · greedy goal-seeking apply · MDL rule-set · P1 ≈ option (b)).
A read-only **Solver** (`spike/arc_solver.py`, stages 1–6) **SOLVES the end-to-end use-case task #8
(`05f2a901`)** — verify 3/3 demos + produced test output = the withheld answer. Next phase =
**generalize beyond #8**. Canonical build record = **Build progress** below; reason-stage decisions =
the **"Reason-stage design"** block; UI element→code reference = `spike/SOLVER_UI_MAP.md`; spike nav =
`spike/README.md`; next-chat prompt = `SOLVER_NEXT_CHAT_PROMPT.md`.
**Companions:** `ONTOLOGY.md` (§4 locked decisions), `LEXICON.md`,
`docs/future_work/L3_FUTURE_WORK.md` §9/§10/§10.1 (generalizable principles surfaced here).

---

## Pipeline shape

```
parse → perceive → profile(preparation) → reason( induce → search → verify → apply | abstain )
```

- **parse / perceive / profile** map to the L4 **`phase_1`** lifecycle (run for every task).
- **reason** maps to `plan_construction` + `execution` — where **`find_pipeline`** composes the
  task-specific pipeline by PRODUCES/CONSUMES.

---

## Layer discipline (locked principles)

| Concern | Home |
|---|---|
| acquire external data | **adapter family** (future, L3-49); ARC = fixture. L3_FW §9 |
| move data across a boundary (load, transfer) | **substrate / Server effect** — never raw IO in L3. L3_FW §10 |
| decide *to* load (relevance) | L3 capability (`retrieval.*`). L3_FW §10 |
| the meaning of raw symbols | **L2** (ontology + lexicon) |
| interpret raw data against L2 | **L3 capability** (perception/comprehension). L3_FW §10.1 |
| which capacity runs next (activation) | **paths in the L3 bipartite graph** — not a hand-coded tree |
| order reasoning capacities | **`find_pipeline`** (PRODUCES/CONSUMES) |
| run the mandatory profilers | **L4 `phase_1` sweep** over `preparation`-tagged leaves |
| **no higher-order dispatcher** | a capacity never selects/calls other capacities (ONTOLOGY §3) |

---

## Perceive (LOCKED) — build the representation, no inductive commitment

Phase-1 line: perceive the grid **and** its uncommitted structure (palette, objects, shapes).
**No background, no figure, no "which objects matter"** — those are reasoning judgments.

### Non-capacity steps
- **acquire corpus** — ARC dataset is a **fixture (file)**. (Future autonomous acquire = adapter family.)
- **load task** — substrate transfer → `RawTask` (deserialized, uninterpreted).

### Capacities

| Capacity | consumes → produces | family | dont-know |
|---|---|---|---|
| **comprehend_task** | `RawTask` → `Task`, `Pair`*, `RawGrid`* | comprehension | DATASTATE_MARKER |
| **recognize_cell** | (`Coordinate`, `ColorSymbol`) → `Cell` | perception | DATASTATE_MARKER |
| **build_grid** | `RawGrid` (→ `Cell`*) → `Grid` | perception | DATASTATE_MARKER |
| **extract_palette** | `Grid` → `Palette` (per-grid color set) | derivation | DATASTATE_MARKER |
| **extract_objects** | `Grid` → `Object`* (monochrome, 8-connected, size ≥ 2) | decomposition | (deferred default) |
| **extract_shapes** | `Object` → `Shape` (colorless, normalized) | derivation | DATASTATE_MARKER |
| **extract_points** | `Grid` → `Point`* (single cells; not Objects/Shapes) | decomposition | (deferred default) |

```
[substrate load] → RawTask
  → comprehend_task → Task + Pair*(role demo|test) + RawGrid*(role input|output)
    → build_grid (drives recognize_cell) → Grid (Cells)
      → extract_palette → Palette
      → extract_objects → Object*   (connected components, EVERY color, no background special-case)
        → extract_shapes → Shape*
```

- **comprehend_task** = structural comprehension + role-binding only (emits `RawGrid`, doesn't
  descend into cells). Dont-know = structure doesn't match the task schema (honest "not a task").
- **extract_objects**: per-color connected components for all colors → **monochrome Objects by
  construction** (matches ONTOLOGY §2.2). **Connectivity = 8-connectivity (orthogonal OR diagonal),
  fixed** (ONTOLOGY §4 #1b, v0.5). Background-color components are extracted too (cost: set bloat —
  pruning is a reasoning-time judgment, not here).
- Output per grid: `Grid`, `Palette`, `Object`*, `Shape`*. Two sets per pair (input/output);
  test-pair **output `withheld`** (ONTOLOGY §4 decision 4) — gated, not in solver inputs.

### Realm
New realm **`arc`** (via `allow_new_realm`) for all ARC DataStates (vs reusing `mm` — rejected).
Concrete `register_datastate` constants verified against live L3 when the instance stands up.
Shipped reserved realms: core, marker, bridge, text, mm, problem_trace, nlu, code, dream.

---

## Profile / preparation (LOCKED shape) — mandatory feature profiling

Runs for **every task** as the L4 `phase_1` sweep. Comparators run on **demonstrations only**
(query output withheld); folds span all demos.

### Capacities (L3)

| Capacity | consumes → produces | family | dont-know |
|---|---|---|---|
| **compare_grid_dimension** | (in `Grid`, out `Grid`) → `DimensionDelta` \| None | comparator | OPTIONAL_RETURN |
| **compare_palette** | (in `Palette`, out `Palette`) → `PaletteDelta` \| None | comparator | OPTIONAL_RETURN |
| **agrees_across_demos** | `Delta`* (one per demo, same feature) → `Bool` + common `Delta` | predicate/fold | NO_DONT_KNOW |

- **Delta-or-None IS the yes/no.** OPTIONAL_RETURN's dont-know = "no change" → that branch never
  activates; a returned Delta = "yes + how". Activation follows from the graph paths.
- **`agrees_across_demos` is generic over the Delta *type*** (shared `Delta` DataState shape) — it
  folds whatever Deltas exist; it does **not** call feature comparators. No dispatcher.
- A consistent Delta = a **candidate Rule fragment/constraint** the reasoning stage consumes.

### L4 control (not capacities)
- the **mandatory sweep**: run every `preparation`-tagged comparator leaf over each demo pair →
  Deltas → `agrees_across_demos`. This is the "generic profiler" — it lives in `phase_1`
  orchestration, not as an L3 capacity. Keep preparation a **small set of cheap universal profilers**
  (dimension, palette); the long tail stays lazy reasoning capacities `find_pipeline` pulls on demand.

---

## Reason — in design (NEXT CHAT starts here)

`find_pipeline` composes the task-specific pipeline from the preparation fragments/verdicts:
**induce** (feature comparators emit transform fragments) → **search** (compose fragments into
grid→grid Rules over the seed basis, MDL-ordered) → **verify** (Rule reproduces *every* demo) →
**apply | abstain** (best Rule on query, else structural abstain).

### Building blocks already defined for the reason stage (ONTOLOGY §2.2–2.4, §4 #7–14)
- **Transform** = detector/generator pair around one shared `Transform` DataState (past-tense
  comparator `PRODUCES`, present-tense generator `CONSUMES`); exists iff a detector exists.
  This *is* the induce↔apply arc.
- **Comparators ready:** `compare_grid_dimension`, `compare_palette` (profiling); `offset`
  (Object×Object→Vector), `is_equal` (invariance), the `compare` shape family (congruence etc.).
- **Structure to recognize/derive at reason-time:** Background/Figure (the deferred judgment),
  base shapes (`vertical/horizontal/diagonal/square`), `Divider` (role), `Pattern` (composite),
  `Lattice(N)` (composite), sub-shape decomposition.
- **Correspondence** (which input object ↔ which output object) is a required pre-step *before*
  any transform detector runs — not yet designed.

### Open dependency — the seed operation set freeze
`search` cannot enumerate until the seed basis is frozen. Reference: **`ICECUBER_DSL.md`** (the
full 2020 ARC winner DSL — ~50 names, ~140+ `id`-variants). Freeze at the **variant level**, not
the name level. Three earlier-raised, still-open framing points live in `git log` / chat history
but are summarized here: type-unification (icecuber's one `Image` type vs our split classes),
enumerative-vs-inductive search (icecuber is the recombination baseline to beat), and whether the
parse is fixed or part of the search (default fixed for the spike).

---

## Build progress

- **M1 spike — BUILT 2026-06-15** (`spike/`). Dataflow spike, no router. Stands up a live
  in-memory `CapacityLayer`, registers the `arc`-realm DataStates + the perceive capacities
  (`comprehend_task → build_grid → extract_objects/extract_palette → extract_shapes`) + the two
  profile comparators, and **proves `find_pipeline` discovers the perceive chain** by
  PRODUCES/CONSUMES alone (`raw_task → shape` = comprehend_task → build_grid → extract_objects →
  extract_shapes; asserted in `run_spike.py`). Comparators run via the L4-style `profile_sweep`
  (not `find_pipeline`) per the lock. `TaskProfile` = steps 1–3 + demo deltas **only**;
  correspondence/equal-objects/remaining-objects held for **M2 (induce)**. Human debug interface =
  `spike/arc_debug.html` (task picker, grid render, extracted objects w/ bbox overlay, normalized
  shapes, profile verdicts) fed by `arc_debug_data.js` (generated; all 400 train tasks).
  Files: `arc_grids.py` (pure algorithm) · `arc_capacities.py` (registration) · `arc_profile.py`
  (profile + discovery) · `run_spike.py`. Note: needs `tomli` on Python 3.10 (3.11+ has `tomllib`).
  Bodies are wired but **not yet executed via `invoke`** (M-later); find_pipeline only walks edges.
- **M2 (induce) — `same_object` + `same_shape` tiered match.** New `induce` phase, two pairwise
  comparators registered: **`same_object`** (`Object → arc.same_object` Bool; same colour AND
  position — *renamed from `is_equal`*) and **`same_shape`** (`Shape → arc.same_shape` Bool;
  identical translation-normalized point-set, **no rotation/reflection**). The tiered match is a
  **fold over both** (`arc_profile.match_pair`, L4-style — no capacity calls another, approved #4):
  1. **`same_object`** — 1:1 invariant pairs. Runs **regardless of in/out dims** (compares absolute
     cells; the per-pair dims gate was removed).
  2. **`same_shape`** — over the *leftover* objects, **group by identical shape**; single-point
     shapes excluded; a group kept only when present on **both** sides; carries the **base-shape
     name** (`square`/`vertical`/`horizontal`/`diagonal` via `arc_grids.base_shape_name`, else
     unnamed) + cell size. Dim-independent.
  3. **rest** — unique-shape, one-sided, or point objects.
  Demos only. Debug UI = two-column card (grids on top; object list tiered: green `≡` `same_object`
  pairs, blue `≅` `same_shape` group boxes, then rest). **Scope note:** `same_shape` is grouping,
  not 1:1 mover correspondence — duplicate shapes stay an unresolved group (P3). Files:
  `arc_grids.{same_object,same_shape,base_shape_name,shape_key}`, `arc_capacities._induce_capacities`,
  `arc_profile.match_pair`.
- **M2 points (ONTOLOGY v0.6 / §4 #15) — Point as a first-class category.** A single-cell component
  is a **Point**, not an Object/Shape; Objects are size ≥ 2. New perceive capacity **`extract_points`**
  (`Grid → Point*`) and induce comparator **`same_point`** (`Point → arc.same_point`; colour +
  position). `match_pair` adds a 4th tier: **`same_point` invariant 1:1 pairs** (amber `≡`, NOT
  grouped) + leftover points into rest. `same_object`/`same_shape` never touch Points. Debug-card tier
  order: `same_object` (green `≡`) → `same_shape` (blue `≅`) → `same_point` (amber `≡`) → rest.
  Object names `[In|Out]<pair>.O<i>`, point names `[In|Out]<pair>.P<i>`. Files: `arc_grids.{_components,
  extract_objects,extract_points,same_point}`, `arc_capacities` (arc.point/arc.same_point + caps),
  `arc_profile.{grid_summary,match_pair}`.
- **M2 moved (induce; transform detector, ADR §4 #10).** `moved` capacity (`Object →
  arc.move_transform`): emits the **move Transform** `{kind:"translate", vector:Δ}` (bbox-origin
  translation). **Self-guarding (total):** returns `None` unless **same colour AND same shape AND
  displaced** (Δ≠0) — safe to call on any pair. Computed **per (input, output) pair** within each
  `same_shape` group, restricted to **same-colour** pairs (caller pre-skip + capacity guard); N×M
  candidates surface P3 as explicit candidates, do not resolve it. The past-tense **detector** half
  of the move duality; the `move` generator is later. Debug UI: a **moved-candidates accordion**
  under each `same_shape` group. Files: `arc_grids.moved`, `arc_capacities` (arc.move_transform +
  `moved`), `arc_profile.match_pair` (`shape_groups[].moves` = `{in,out,transform}`).

- **M2 hypotheses (L4 fold — `agrees_across_demos` over induce caps).** Per task, **pair 1 is
  canonical**: the induce capabilities that fire there (`same_object`/`same_shape`/`same_point`/`moved`)
  are each checked for **presence in every demo pair**; those that persist are appended to the task's
  **hypotheses** list (`arc_profile.hypotheses` → `task.hypotheses = {list, detail}`). Presence only
  (value/why deferred); correspondence ambiguity ignored; `compare_*` (profile-sweep) **excluded**.
  These are candidate *constraints*, not yet an executable/generalizable Rule (P1/P5). Surfaced in
  Main (a Hypotheses card: per-cap `k/N pairs` + ✓/✗/— status) and in the Search expand (a hypotheses
  line). Files: `arc_profile.{INDUCE_CAPS,_present,hypotheses,build_profile}`, `arc_debug.html`.
- **Arc metagraph (L3 overlay, choice A2).** `arc_metagraph.py` builds a real Core `Metagraph`
  ("arc") whose contained graphs are the capability **sections** — `atoms` (`same_object`/`same_shape`/
  `same_point`), `object_comparator` (`moved`), `profile` (`compare_*`) — referencing the same caps the
  `CapacityLayer` registers under their **functional** families (comparator, …) by capacity-IRI. This
  is the **operand axis**, additive (the functional axis + Capacities panel stay intact, A2). The
  `moved → requires → same_shape` dependency is a **binary `IntergraphEdge`** (single requirement;
  colour is `moved`'s internal guard) — a *compositional* `IntergraphHyperEdge` would apply only with
  ≥2 atoms (hyperedges refuse 1:1). Surfaced in the Map section (`DATA.arc_metagraph`). Files:
  `arc_metagraph.py`, `run_spike` (`payload.arc_metagraph`), `arc_debug.html`.
- **Search facet sections + row treatment.** Facets grouped into `profile` / `atoms` /
  `object_comparator` (with `moved ⊃ shape, colour`); matched-row result counts hidden by default
  behind per-type show-counts toggles; green **`hypothesis ✓`** flag when all selected induce facets
  persist across all pairs. Files: `arc_search.FACETS` (`group`/`requires_label`), `arc_debug.html`.
- **Debug tooling — Search panel.** `arc_search.py` builds a per-task **availability index**
  (`{task_id: [tokens]}`, derived from the existing `match`/profile data — single source of truth):
  boolean tokens (`same_object`/`same_shape`/`same_point`, fire on ≥1 demo) + multi-result tokens
  (`compare_grid_dimension:<preserved|grew|shrank|mixed|varies>`, `compare_palette:<preserved|added|
  removed|added+removed|varies>`). Non-deterministic extractors + trivial perceive caps excluded.
  UI Search panel (region ⑦, toggle): C1 accordion facets (boolean checkboxes + multi-result
  expanders, per-result counts), **AND across capacities / OR within a capacity's results**, matched
  task list with **S2 inline expand** (click a match → its pairs + per-tier counts) + open-in-main.
  Pure tooling — no L3 capacity. Files: `arc_search.py`, `run_spike` (`payload.search`), `arc_debug.html`.
- **Positional-comparison categorization + `touching` predicate (LOCKED 2026-06-16, not yet built).**
  A cross-cutting **positional comparison** tag (an operand/axis label like the Arc-metagraph
  sections — **not** a functional family; must not drive dont-know/registration) splits into:
  **intra-grid positional comparison** (relations among co-present objects in one grid — `touching`,
  predicate → Bool) and **inter-grid positional comparison** (displacement of a corresponded object
  across the input→output pair — `moved`, comparator → Transform). New predicate **`touching`**
  (`(Region, Region) → Bool`, total, NO_DONT_KNOW): true iff the two share an 8-neighbour; holds
  **only between different-colour objects and Points** (same-colour 8-adjacent cells are already one
  component); operand = Region/PointSet so Object/Point/Group all participate; **parameter-free**
  (connectivity fixed §1b). Serves **both** induce-time structure (grouping + correspondence P3 +
  hypotheses) **and** apply/verify-time rule conditions — see PB-A update. World-model record:
  ONTOLOGY §2.3 / §3 / §4 #16 (v0.7).
- **`touching` BUILT 2026-06-16** (spike). `arc_grids.touching`/`touching_pairs`; per-grid pairs in
  `grid_summary["touching"]`; `arc.touching` DataState + `touching` predicate capacity in a new
  `intra-grid` catalog group; `arc_search` `touching` token + FACETS `division` field
  (inter-grid/intra-grid); `touching` added to `INDUCE_CAPS` so it carries a hypothesis. UI: Main
  demo cards split into inter-grid/intra-grid divisions + a `touching candidates` accordion (dim
  title like moved, violet pair boxes); Search facets in two divisions + the hypothesis flag.
  Discovery proof unchanged; data regenerated (400 tasks). **Signal-quality flag (open):** touching
  fires on **400/400** tasks (and is a hypothesis on all) — `extract_objects` extracts the
  **background as a component** and the background region is 8-adjacent to nearly everything, so the
  facet is currently non-discriminating. Faithful to "no background special-case" (perceive stays
  uncommitted); a background-aware variant is a **reasoning-time** judgment (deferred — ties to the
  Background/Figure open item). Not yet executed via `invoke` (computed by the body fold).
- **Solver stages 1–2 BUILT 2026-06-17** (`arc_solver.py`, read-only run viewer = option A; scoped to
  task #8 `05f2a901`). **Stage 1** states·transitions·**changes**: background proposal (most-frequent
  colour), correspondence (`same_object` ∪ 1:1 `moved`), the **state-change detector** (P6 un-parked —
  `touching_changes`: gained/lost across a pair, bg-excluded) → `touching gained (O1·O2) 3/3`.
  **Stage 2** hypothesis formation: persistence + the `(transition, state-change)` combination test
  (same object within a pair, existential across pairs) → candidate `(move, touching)` (mover varies
  by pair: O1,O1,O2). Static states excluded (not changes). Stages 3–6 (selector/rule/verify/apply)
  are **pending** rows; expected flags: ⚑ selector tie (mover = bigger / non-square), ⚑ mismatch.
  **Background is optional** (analyse separately) — not a blocking flag: excluding it only hides the
  maintained bg-touching noise, the `gained` signal is exclusion-independent, so both views are
  precomputed and the UI toggles (`solverBg`, display-only, still option A). New **Solver** section in
  `arc_debug.html` (vertical stepper, data-driven from `payload.solver`); UI reference =
  `spike/SOLVER_UI_MAP.md`. Recompute-requiring decisions stay machine-proposed → answered in chat →
  rerun. `find_pipeline` proof unchanged; data regenerated.
- **Solver stage 3 BUILT 2026-06-17.** Selector synthesis (`arc_solver._selectors_for`): single-
  attribute discriminative descriptions (colour / size-rank / base-shape) that identify mover &
  target in **every** demo and distinguish them from the other non-bg object. For #8 → mover
  {colour=2, largest non-bg, irregular}, target {colour=8, smallest non-bg, square} — a **3-way tie**
  → ⚑ selector flag (`solverStep3` card, amber "needs you"). Note: all three candidates resolve the
  **same** objects on the #8 test, so the pick doesn't change #8's answer — it only matters as the
  **generalization prior** (where teaching/priority will eventually live). Stages 4–6 pending.
- **Solver stages 4–6 BUILT 2026-06-17 — task #8 SOLVED end-to-end.** Selector locked = **shape**
  (mover = irregular, target = square; owner pick). **Stage 4** rule assembly: `(move, touching)` +
  the shape selectors + slide policy + trivial dependency DAG (target invariant, grounded). **Stage 5**
  verify: the **greedy move generator** (`_slide` — translate one cell/step toward the target along
  the shared-axis perpendicular until touching; budget = grid bound → abstain) + the **minimal
  serializer** (`_render` — bg fill + non-mover objects at origin + mover slid; #8-scoped, no overlap)
  reproduce **all 3 demos** (slides 6/3/3, exact match) → "sufficient". **Stage 6** apply: the produced
  test output is **byte-for-byte the withheld answer** (`matches_withheld: True`; the answer is checked
  only for our confidence, not used by the solver). Full chain in `arc_solver.apply_rule`; UI cards
  `solverStep4/5/6` (verify table + test input/output mini-grids). The thinnest end-to-end slice
  (PB-1) is closed: the transition·state·selector apparatus + greedy generator + minimal serializer
  solve a real ARC task, with one human-in-the-loop decision (the selector). `find_pipeline` proof
  unchanged; data regenerated. **Not generalized** beyond #8 (single mover, axis-aligned, no overlap,
  shape selector); the general serializer/filter stay future work.
- **Solver UI + tooling refinements 2026-06-17.** Read-only **Solver** section in `arc_debug.html`
  (vertical stepper, stages 1–6, data from `payload.solver`); background = optional display toggle
  (not a flag); selector tie shown resolved (= shape); SOLVED banner. **Main layout reworked**:
  demonstrations side by side (`.demorow`), test + hypotheses row beneath (`.botrow`), compact 300px
  cards, input/output grids fixed **120px-wide** (variable height, fill perfectly via `cs = 112/cols`),
  object cards = grid width with the relationship sign between (3-col `120/24/120` matchgrid),
  multi-line grid info labels, an **Object info** toolbar toggle (`show.info`, color·size hidden by
  default), and the **rest — no match** tier as an accordion (`.restacc`). **Callout part-name maps**
  (demo_ui style) for all five sections (Main / Search / Solver / Capacities / Map) with a selector
  bar (`#mapnav` / `setMap`) in the **Map** section — generators `spike/maps/*.py` (cairosvg) +
  `_kit.py`; full Solver element→code table in `spike/SOLVER_UI_MAP.md`. **Launcher**: `./run_spike`
  at the repo root (+ `run_spike.py` runs directly via a package-bootstrap). No data-model change.

## Parked problems (reason-stage — raised, not yet resolved)

- **P1 — `search` is not a PRODUCES/CONSUMES node (gating).** Search is a combinatorial
  control loop (compose seed ops → execute → backtrack), not a one-shot consume→produce capacity.
  Collides with locked "activation = graph paths" + "no capacity calls other capacities". Cannot
  draw `search`'s consumed/produced DataStates until the **Rule representation** is chosen:
  - **(a) Rule-as-data / closed interpreter** — seed basis = frozen opcodes; `search`+`verify`
    are ordinary L3 capacities; Rule = AST; a self-contained interpreter executes it (not the L3
    graph). Cost: duplicate execution semantics (opcode table vs transform family); rigid seed freeze.
  - **(b) Rule-as-live-chain / search-in-L4** — seed ops are registered capacities; `search` is
    L4 control iterating `find_pipeline`; verified Rule = frozen Pipeline artifact (reuses L5
    chain-artifacts). Cost: MDL/enumeration *decision* leaks into L4 (boundary erosion); per-candidate
    find_pipeline+execute cost; new backtracking surface in L4.
  - **(c) Hybrid — Rule-as-data, opcodes are thin wrappers over the same transform capacities
    (shared kernel).** No dispatcher, single semantics, seed freeze stays in L3. Cost: must enforce
    seed-basis ≡ transform-family one implementation; "thin wrapper" can drift.
  - This pick also resolves the open **type-unification** item (interpreter wants one `Image`
    operand type; live-chain keeps the split classes).
- **P2 — `induce` and `search` are not cleanly separable.** "Feature comparators emit transform
  fragments" *is already* partial search. Boundary between fragment-emission and fragment-composition
  is undrawn.
- **P3 — correspondence is upstream of `induce`, not a sub-step of it.** Which input object ↔ which
  output object gates *every* transform detector, so it sits before induce, not inside it. Placement
  + its consumed/produced DataStates undrawn.
- **P4 — abstain "within budget" needs a budget semantics.** Abstain is structural ("no consistent
  Rule within budget"), but "budget" (search depth? node count? wall cost?) is undefined; without it
  abstain collapses back into an implicit threshold.
- **P5 — a literal per-object Transform passes `verify` but fails generalization.** A movement rule
  expressed as `{object → Vector}` reproduces the demos (Consistency, ONTOLOGY §2.5) yet transfers
  to nothing — the query has different objects. `induce` must emit the *generator* of the vector (a
  relational rule: fall-to-bottom / move-toward-X / align-to-divider), not the vector. Designing it
  requires the real grids. Verify-green ≠ solved; this is a false-confidence trap the spike should
  *demonstrate* (M2), not assume.
- **P6 — relation state-transition check (PARKED 2026-06-16).** Idea: for a corresponded object
  pair, detect `touching` flipping across the pair (touch→¬touch / ¬touch→touch) and correlate with
  `moved`. Designed but **not built** (owner pivoted to the transition∘state convention below).
  Naming candidates considered: `touching_delta` (relation Delta, lean), `joined`/`separated`
  (directional past-tense), generic `transitioned(state,…)`. Hard dependency: correspondence (P3) —
  buildable only over the unambiguous subset (`same_object` + 1:1 `moved`), rest tagged undetermined.
  Concept home = relation Delta (§2.4–2.5), **not** a Transform (#10). Resume from here if revived.

### Reason-stage pushbacks (raised 2026-06-16, open — review before settling P1)

- **PB-A — P1 is under-determined until P5 fixes what a Rule must *express*.** The a/b/c
  representations differ on *expressivity*, not plumbing, and expressivity is decided by P5 (a Rule
  must emit the *generator*, not a per-object `{object → Vector}`). Freezing a representation — and
  its seed basis — before that is fixed reproduces the P5 trap at the architecture level:
  verify-green Rules that can't transfer because the basis can't name a relational generator. The
  prior question is **"what class of rule must the demo solve?"**:
  - **whole-grid recombination** (icecuber's one `Image` operand, ops `Image→Image`) → favours
    **(a)** closed interpreter over a flat opcode basis; the split-class ontology becomes
    type-unification friction.
  - **relational object rules** (P5's space — refer to *other* objects in the query) → **(a)**
    can't express "relative to whatever's present"; favours **(c)**, opcodes as thin wrappers over
    the transform/comparator family that already speak Object/Vector/Divider.
  Decide the task slice first; it collapses most of P1 and fixes whether the seed freeze is
  icecuber-flat or transform-family-typed.
  - **Update 2026-06-16:** `touching` was accepted as **both** an induce-time structure input **and**
    an apply/verify-time rule condition (selector). The rule-condition role commits Rules to carry
    relational selectors ("the object touching X") as first-class terms — which a flat opcode basis
    (option **a**) cannot express. So **P1 now leans (c)** before it is formally opened. Not yet locked.
- **PB-B — P1 silently assumes P3 (correspondence) is solved.** Every transform detector needs A↔B
  fixed first, and a *relational* generator must be able to *name* its correspondent ("the divider",
  "the largest object"). With correspondence unresolved the Rule has no stable referents regardless
  of representation — so P3 is a hard predecessor of P1, not parallel to it.
- **PB-C — (c) degrades to (a) unless the wrapper invariant is enforced.** "Opcodes are thin
  wrappers over the transform/comparator capacities" only buys single-semantics if seed-basis ≡
  transform-family one-implementation is a checked invariant; otherwise the wrapper drifts into a
  second execution semantics and you are back at (a)'s cost.

### Reason-stage design — agreed 2026-06-17 (transition∘state convention; use case = task #8 `05f2a901`)

**Convention (locked).** Present-participle = a **State** (intra-grid predicate); past-tense = a
**transition** (carries a Transform; consistency optional). A transition composes with a
**state-change** (input→output, gained/lost) into a goal-conditioned rule, **graph-composed**
(DataState composition, not a call). Form is **ternary**: `(mover-transition, state-change,
target = select(S))`. Notation = **tuple** `(transition, state)`. Any transition × any state, but
instantiated **only when observed**. States do three jobs: **goal / change-verified / selector**.

**Hypothesis formation (locked).** (1) enumerate states+transitions for pair 1; (2) keep those
persisting across all pairs (on **changes/transitions**, not static states); (3) add to the
hypothesis set; (4) test `(transition, state-change)` combos — **same object within a pair,
existential across pairs** (∀pair ∃object). Spurious combos culled by MDL + selector.

**Apply (locked).** L4 loop applies the transition **greedily, min transform/step**, checking the
state-change until the goal holds; **budget = grid bounds** → structural abstain. Target = direction,
iteration = magnitude. Next-step proposer = **L3** (ranked); closed-form solve optional (directional
contact distance — *not* bbox-adjacency).

**Targets/selectors (locked).** Moving targets → a **dependency DAG**, topo-resolved (mechanical →
L4 `kahn_sort`), acyclic, grounded at an **absolute referent** (edge / divider / invariant). Selector
= a **minimal discriminative state-conjunction**, task-invariant, must resolve a **unique** source +
target (else abstain). "touches the edge" = a new object↔frame predicate.

**Verify/selection (locked).** Verify = apply the rule set, exact-match every demo (Consistency).
Minimal set (MDL) = **minimum path in a rule graph**; **L4 drives the loop, L3 scores/selects**;
equal-MDL tie-break = an L3 prior. Write-conflict/compositing = L3.

**Boundary invariant.** L4 = loop/control only; the decisions (next-step, goal/selector, conflict,
min-path cost+selection, tie-break) are **L3**. Mechanical (the loop, topo-sort) = L4/substrate.
Commits **P1 ≈ option (b)** (search-as-L4-control + L3 scoring; rule = the DAG run by the loop).

**P6 un-parked:** the state-change detector (touching gained/lost across the pair) is the
verification substrate — required for task #8.

## Open items (the next chat's backlog)
- **(FUTURE WORK) Rule-set filter / priority / teaching** — how the minimum sufficient rule set is
  chosen (acquired by teaching, priority, experience). Deferred per owner 2026-06-17.
- **(FUTURE WORK) objects→grid serializer (general)** — the apply-side inverse of perceive
  (background fill, overlap/z-order, clipping). A **task-#8-scoped minimal** serializer (single mover,
  no overlap) is built for the slice; the general one is deferred per owner 2026-06-17.
- **Reason-stage decomposition** — induce → search → verify → apply | abstain at DataState
  granularity; correspondence pre-step; transform detector/generator pairs; the abstain gate.
- **Seed operation set freeze** (blocks `search`) — freeze the minimal basis at the `id`-variant
  level using `ICECUBER_DSL.md`; decide type-unification vs the split-class ontology.
- Background / figure as reasoning-time judgments (which object-set/color is background).
- ~~`extract_objects` connectivity: uncommitted~~ **RESOLVED v0.5** — fixed 8-connectivity (ONTOLOGY §4 #1b).
- Withheld-answer enforcement on the MM (test-pair output gated from induce/search).
- DataState realm constants verified against live L3 (the `arc` realm).
- Fixed-parse vs parse-in-search (default fixed for the spike, deferred).
- Perceive/profile capacity DataState specs not yet written as a registration contract.
- Thin spike target (smallest real ARC-1 slice exercising perceive→induce→verify→apply/abstain).
