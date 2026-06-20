# ARC Vocabulary Consolidation — worksheet

**Status:** working scaffold · started 2026-06-18 · **transitional** (per
`SKILL_ACQUISITION_MANUAL.md` §6A: discard once the L3 graph is canonical and the lexicon
is projected from it). Pass 1 = **perceive layer** (ground-up, closest to the substrate).
Method = harvest → classify → reconcile → place → edge → ground.

**Ground:** `RawTask` (the ARC Solver substrate; below it = future MindsOS).

**Legend.** Homes: ✓ present · ✎ add · ↻ reconcile (alias). Kind: D=data (DataState),
F=derivation (capacity), R=relationship. Provenance edges: `produced-by` (functional),
`composed-of` (compositional), `ground`. Attachment edges: `attribute:` / `relational:` /
taxonomic (`subclass_of`/`exemplifies`). A term is **grounded** when a provenance walk
reaches `RawTask`.

## Term table (perceive layer)

| Term | Kind | O | L | L3 | Provenance | Attachment / taxonomic | Grounds? |
|---|---|---|---|---|---|---|---|
| **RawTask** | D | ✎ | ✎ | `DS_RAW_TASK` ✓ | **ground** (substrate load) | — | ✓ root |
| **comprehend_task** | F | ✎§3 | ✎ | ✓ | consumes RawTask | — | ✓ |
| **Task** | D | ✓ | ✓ | `DS_TASK` ✓ | produced-by comprehend_task | `compositional:demonstration\|test` ⊣ Pair* | ✓ |
| **Pair** | D | ✓ | ✓ | `DS_PAIR` ✓ | produced-by comprehend_task | `compositional:input\|output` ⊣ RawGrid/Grid | ✓ |
| **RawGrid** | D | ✎ | ✎ | `DS_RAW_GRID` ✓ | produced-by comprehend_task | part-of Pair (`compositional:input\|output`) | ✓ |
| **Coordinate** | D | ↻ Position | ✓ coord | ✎ `DS_COORDINATE` | composed-of RawGrid (index structure) | `compositional:position` of Cell; value of `attribute:position` | ✓ |
| **Color** ↻ ColorSymbol | D | ✓ Color | ✓ | ✎ `DS_COLOR` | composed-of RawGrid (read @ Coordinate) | `compositional:color` of Cell; `attribute:color` of Object/Point; ⊣ Palette | ✓ |
| **Cell** | D | ✓ | ✓ | ✎ `DS_CELL` | `Cell ⊣ {Coordinate@position, Color@color}` (composed-of) **+** produced-by recognize_cell | part-of Grid; part-of Object (`compositional`) | ✓ |
| **recognize_cell** | F | ✓§3 | ✎ | ✎ register | consumes (Coordinate, Color) → Cell | — | ✓ |
| **build_grid** | F | ✓§3 | ✎ | ✓ | consumes Cell* → Grid | — | ✓ |
| **Grid** | D | ✓ | ✓ | `DS_GRID` ✓ | produced-by build_grid; `Grid ⊣ Cell*` | `attribute:dimension` Dimension | ✓ |
| **Dimension** | D | ✓ | ✎ | ✎ `DS_DIMENSION` | produced-by derive_dimension(Grid) | `attribute:dimension` of Grid | ✓* |
| **extract_palette** | F | ✎§3 | ✎ | ✓ | consumes Grid → Palette | — | ✓ |
| **Palette** | D | ✓ | ✓ | `DS_PALETTE` ✓ | produced-by extract_palette; `Palette ⊣ Color*` | — | ✓ |
| **Region** | D **concrete** | ✓ | ✓ | ✎ `DS_REGION` | root of located axis; instantiated via subclasses (perceive) / Selection (reason) | `subclass_of` target for Grid/Object/Point/Group/BBox/Pattern/Lattice/Selection; `exemplifies` PointSet | ✓ (via subclasses) |
| **Selection** | D | ✎ | ✎ | ✎ `DS_SELECTION` (reason-time) | produced-by selection/mask (reason-time) | `subclass_of` Region | ✓ (reason-time) |
| **extract_objects** | F | ✓§3 | ✎ | ✓ | consumes Grid → Object* | — | ✓ |
| **Object** | D | ✓ | ✓ | `DS_OBJECT` ✓ | produced-by extract_objects; `Object ⊣ Cell*` | `attribute:{color,bbox,size,position}`; `exemplifies` Shape; `subclass_of` Region | ✓ |
| **extract_points** | F | ✓§3 | ✎ | ✓ | consumes Grid → Point* | — | ✓ |
| **Point** | D | ✓ | ✎ | `DS_POINT` ✓ | produced-by extract_points | `attribute:{color,position}` | ✓ |
| **derive_bbox** | F | ✎§3 | ✎ | ✎ register | consumes Region → BBox | — | ✓ |
| **BBox** | D | ✓ | ✓ | ✎ `DS_BBOX` | produced-by derive_bbox(Region) | `attribute:bbox` of Object | ✓ |
| **derive_area** | F | ✎§3 | ✎ | ✎ register | consumes Region → Area | — | ✓ |
| **Area** ↻ size | D | ✓ | ✎ | ✎ `DS_AREA` | produced-by derive_area(Region) | `attribute:size` of Object | ✓ |
| **derive_position** | F | ✎§3 | ✎ | ✎ register | consumes Region → Coordinate | — | ✓ |
| **Mask** | D | ✓ | ✓ | **defer** (no consumer) | (would-be derive_mask) | `attribute:mask` | — |
| **extract_shapes** ↻ normalize_shape | F | ✓§3 normalize_shape | ✎ | ✓ | consumes Object → Shape | — | ✓ |
| **Shape** | D | ✓ | ✓ | `DS_SHAPE` ✓ | produced-by extract_shapes(Object) | Object `exemplifies` Shape | ✓ |
| **base-shape** | D abstract | ✓ #9 | ✎ | templated (recognized) | abstract individual in O | recognized-as (comparator) | ✓ |

\* Dimension grounds once `derive_dimension` is registered.

## Reconciliation forks

**RESOLVED 2026-06-18** — R1–R4 + R7 promoted to ONTOLOGY §4 #19 + LEXICON; R5 → #18 (concrete);
R6 deferred (Mask, no consumer). Spike L3 renames (`size→area`, `extract_shapes→normalize_shape`,
`ColorSymbol→Color`, `Position→Coordinate`) land at the L3-registration build step.

- **R1 — Coordinate vs Position.** Same value `(row,col)`. **Pick:** one value type
  **`Coordinate`**; "position" becomes the *attribute role* (`attribute:position`) whose
  *value* is a Coordinate. Collapses the `Position` class into Coordinate-value +
  position-role. (Alternative: keep both as distinct DataStates — rejected as redundant.)
- **R2 — ColorSymbol = Color.** **Pick:** canonical **`Color`** (value, symbol 0–9);
  `ColorSymbol` was only the raw-read name → alias.
- **R3 — size = Area.** **Pick:** canonical **`Area`** (the ontology term); `size` (spike)
  → alias. Rename in spike at L3 registration.
- **R4 — extract_shapes vs normalize_shape.** **Pick:** canonical **`normalize_shape`**
  (it normalizes, not extracts); `extract_shapes` → alias. (Low stakes; spike rename.)
- **R5 — Region.** **RESOLVED 2026-06-18 → CONCRETE** (ONTOLOGY v0.9 §4 #18). Region = concrete
  root of the **located** axis; `subclass_of` target for Grid/Object/Point/Group/BBox/Pattern/
  Lattice/Selection. **Grid ⊑ Region** (maximal region) + `frame` role; decomposition generalises
  to `Region → X*`. **Two axes:** located (Region) vs normalized (PointSet); bridge = `exemplifies`/
  `normalize`; recognisers `Region → typed | don't-know` are down-only. Perceive instantiates via
  subclasses; bare Region = `Selection` (reason-time).
- **R6 — Mask.** **Pick:** **defer** — named in O, no consumer → not registered (YAGNI).
- **R7 — grounding of Coordinate/Color.** **Pick:** via `RawGrid ⊣ {Color @ Coordinate}`
  (compositional decomposition of the raw grid); `recognize_cell` then consumes a
  (Coordinate, Color) to produce a Cell. Confirms the raw layer grounds through RawGrid.

## Promotion plan (on sign-off)

1. **ONTOLOGY** — add §3 capacity rows (comprehend_task, extract_palette, derive_bbox,
   derive_area, derive_position); add RawTask/RawGrid classes; fold Position→Coordinate (R1);
   note Region abstract (R5). 
2. **LEXICON** — backfill: RawTask, RawGrid, Coordinate, Cell-as-composition, Dimension,
   Point, Area, base-shape, the perceive capacities; reconcile size→Area.
3. **L3 (spike `arc_capacities.py`)** — register `DS_COORDINATE/COLOR/CELL/DIMENSION/BBOX/AREA`
   + `recognize_cell/derive_bbox/derive_area/derive_position/derive_dimension`; add the
   compositional + attribute edges (same-graph `IntergraphHyperEdge` per L1-10). **Build step**
   — follows pair-execution (Mac commits, Linux gates).
4. **Grounding check** — assert every perceive term walks to RawTask (the pass-1 done-gate).

Then **discard this worksheet's rows** as each promotes (the graph becomes canonical).
