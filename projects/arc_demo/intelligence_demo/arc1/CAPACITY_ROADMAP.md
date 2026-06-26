# Capacity acquisition roadmap

**The icecuber DSL is a reference checklist only** — a coverage map of the primitive
vocabulary recurring ARC-1 tasks compose from (`ICECUBER_DSL.md`). It is **not** a build
plan and **not** a paradigm we adopt: icecuber is enumerative brute-force over a unified
`Image` type, scored by exact demo-fit (no induction, no MDL, no grounding). Our system is
the opposite — perceive → reason → grounded rule. We mine the DSL for *which capacities to
create*; we use it for nothing else.

## Hard constraints (decide before porting anything)

1. **Type model is a prerequisite.** Every DSL function assumes one `Image`-with-position
   type. We split `Grid / Object / Shape / Palette / Color` (ONTOLOGY §4). Each ported
   primitive must first decide: unify, or adapt to our split types.
2. **Demand-driven, not catalog-driven.** Add the 2–3 primitives a chosen task (D13) needs,
   grounded, through the layer — then repeat. Do not pre-build the catalog (no scaffolding
   without a consumer).
3. **We already have half of it.** `splitAll/splitCols` → `extract_objects/points`;
   `compress/toOrigin` → `normalize_shape`; `interior/Fill` → `inside`; `pick*` →
   `synthesize_selector`; `Move` → the slide in `apply_rule`.

## Tiers (dependency order)

- **Tier 0 — prerequisite (not a capacity):** the apply-stage type-model decision.
- **Tier 1 — single-input transforms (ground inline; no composer needed):** recolor family,
  `rigid` (D4 rotate/reflect), translate/align, fill/border (extends `inside`), count→value.
- **Tier 2 — selection over a list:** `pick_max`/`pick_unique` + a criterion set (generalises
  `synthesize_selector`).
- **Tier 3 — multi-input composition — BLOCKED on core Part 5 + a real composer:** `compose`,
  `align(a,b)`, `stack`, `replaceCols`, `repeat`/`mirror`.
- **Tier 4 — region/grid restructuring:** `cut`/`heuristicCut`, `getRegular`, `splitColumns`.
- **Tier 5 — enumerative/search combinators — out of scope:** `cutPickMax`, `greedyFill`,
  template matching, the full `id`-variant explosion (only pays off inside a brute-force
  search stage, which we are not building).

## Capacity model adopted here

Each transform family has a **generator** (present tense; produces a transformed Object/Shape)
and a **comparison** (past participle; detects the transform across the input→output pair and
fires as a gate facet). The comparison is the gate-panel capacity; the generator is registered
and invokable but does NOT appear in the Gates panel.

| family | generator | comparison (gate cap) | requires | implies |
|---|---|---|---|---|
| recolor | `recolor` (Object, Color) → Object | `recolored` (in/out Object) | `same_shape` | `same_shape` |
| rotate | `rotate` (Shape, {90,180,270}) → Shape | `rotated` (in/out Shape) | `same_cell_count`, `same_bbox_area` | — |
| reflect | `reflect` (Shape, {horizontal,vertical}) → Shape | `reflected` (in/out Shape) | `same_cell_count`, `same_bbox_area` | — |

`rotated`/`reflected` demand `same_cell_count` + `same_bbox_area` — both **D4-invariant** (a
rotation/reflection never changes cell count, and swaps bbox h↔w so area is preserved). They are a
cheap *necessary* pre-filter: `rotated_pairs`/`reflected_pairs` skip any object pair that differs on
count or area before the expensive shape-rotation/reflection check.

## Profiler / comparator taxonomy (2026-06-25)

Two kinds of bool facet, documented so they are not conflated:

- **Profilers** — universal task facts, NOT capacities, NOT `./evaluate` targets:
  `compare_grid_dimension`, `compare_palette`, `same_object`, `same_shape`, `same_point`, and the
  shape invariants `same_cell_count`, `same_bbox_area`. Registered under `CATEGORY_PROFILER`.
- **Comparators** — the 6 capacities: `moved`, `recolored`, `rotated`, `reflected`, `touching`,
  `inside` (bool facets outside the `atoms` group). These carry **demands** (their `requires`
  profilers) and may be **implied** by another comparator. `./evaluate` probes only these.

Constant-valued profilers were removed (zero information across 400): `colour_count`,
`object_presence`, `component_presence`. Kept: `point_presence`, `object_count`.

## Implication ("obvious") relations among comparisons

A stronger comparison subsumes a weaker one — test the stronger, the weaker is known-true and
skipped. Declared as an `implies` edge; rendered as indentation when both endpoints share a
phase, and as the existing `requires` gate edge when they cross phases.

- `inside ⟹ touching` (enclosed ⇒ border-adjacent) — within Phase 4 (intra-grid). **Sound** (0/400).
- `moved ⟹ same_shape`, `recolored ⟹ same_shape` — cross-phase (= their `requires`). Sound (0/400).
- `rotated`/`reflected ⟹ same_cell_count` + `same_bbox_area` — their `requires` (D4-invariant). Sound.
- `same_shape ⟹ same_cell_count`, `same_shape ⟹ same_bbox_area` — display-only (Search indentation),
  among profilers; independent of each other.
- `same_object ⟹ same_shape` — logically true but **NOT declared**: unsound at the token level
  (120/400). `same_shape` fires only for a shape-group among *non-identical* objects, so an
  all-identical task fires `same_object` without `same_shape`. The verification caught this; the
  skip would wrongly mark `same_shape` true.

Skip is wired **only** where the implication holds empirically over all 400 tasks (verified at spike
time), never on logical-looking pairs that fail at the token level.

## First-built set (this pass)

Tier-1 seed: `recolor`/`rotate`/`reflect` generators + `recolored`/`rotated`/`reflected`
comparison gate-caps, plus the implication relations above. No solver consumer yet (`apply_rule`
unchanged) — seed vocabulary, grounded and invokable, as the template for how transform
capacities enter the system.
