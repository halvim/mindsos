# ARC Lexicon — terms & definitions

> MindsOS L2 `lexicon` role: the named terms and their meanings. The class+relationship world-model is in `ONTOLOGY.md` (L2 `ontology` role); the visual is `arc_lexicon_map.svg`.

Shared vocabulary for the ARC-1 work. **Domain layer** (puzzle) — kept separate
from MindsOS substrate terms (`TaskRun`, metagraph, capacities). When a seed
operation becomes a `register_capacity`, the *capacity* name is MindsOS; the
*operation* it performs is domain. Don't let the namespaces bleed.

Visual reference: `arc_lexicon_map.svg`.

## Core structure

- **task** — a puzzle: a set of `pair`s split into `demonstration` (train) and a `query` (test).
- **pair** — one `input → output` example.
- **demonstration** — a train pair; the rule is shown on both sides.
- **query** — the test input.
- **answer** — the held-out test output (never in the solver's inputs).

## Grid atoms

- **grid** — the full H×W array; **every** cell has a color (including background). Row-major, origin top-left.
- **cell** — one unit, **composed of** a coordinate + a color (`compositional:position`, `compositional:color`); built by `recognize_cell`.
- **coordinate** (canonical; aka position / coord) — `(row, col)`, zero-indexed from top-left. "Position" names the `attribute:position` role whose value is a coordinate.
- **color** — one of 10 fixed symbols `0–9`. (L3 alias: `ColorSymbol`.)
- **background** — the most-frequent color; **derived, not hardcoded** to `0`.
- **palette** — the set of colors present in a grid.
- **figure** — all non-background cells (what the rule usually acts on).

## Objects & abstraction

- **object** — a connected component as it sits in the grid: located + colored.
- **shape** — an object's normalized mask: position- and color-agnostic geometry. (Same shape → any color, any position.)
- **template** — a shape+color pattern reused across objects.
- **mask** — boolean footprint of a region.
- **connectivity** — the grouping rule: **4** (orthogonal) or **8** (incl. diagonal). Fixed per operation; diagonal touch only groups under 8.

## Regions & relations

- **region** (concrete root, located axis) — any absolute cell-set; supertype of grid, object, point, group, bbox, pattern, lattice, selection. The *normalized* counterpart is a **point-set** (a region `exemplifies` one via `normalize`).
- **bbox** — the tightest rectangle enclosing a region.
- **area** — a region's cell count (scalar). (Spike alias: `size`.)
- **vector** — a displacement `(Δr, Δc)`; keeps direction.
- **distance** — a scalar under a named metric: Manhattan / Chebyshev / Euclidean. Throws direction away.
- relations to name as needed: **alignment**, **containment**, **overlap/touching**, **symmetry** (mirror axis / rotation order).

## Operations (seed primitives — the DSL verbs)

- geometry: `translate`, `rotate`, `reflect`, `scale`/`tile`, `crop`, `pad`
- color: `recolor`, `map_color`, `fill`, `flood_fill`
- structure: `select`/`filter`, `count`, `overlay`/`compose`, `mask_out`, `split`/`partition`

## Inference

- **rule / program** — the hypothesized transform `input → output`.
- **consistency** — the rule reproduces **every** demonstration. (Necessary, not sufficient, for a correct answer.)
- **predicate / property** — a measurable attribute used in a condition.
- **abstain** — a structural verdict: "no consistent rule within budget." The honest don't-know — **not** a low-confidence guess.
