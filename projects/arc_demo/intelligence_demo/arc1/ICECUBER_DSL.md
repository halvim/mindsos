# icecuber ARC-2020 DSL — function catalog

Reference for the **seed operation set freeze** (`PIPELINE.md` open item). Transcribed from the
actual source of Johan Sokrates Wind's ARC-AGI-1 Kaggle 2020 winner (`top-quarks/ARC-solution`,
`src/image_functions.cpp` + `src/image_functions2.cpp`). Pure I/O, search-harness, and `core::*`
helpers (`majorityCol`, `count`, `colMask`, `countComponents`, `subImage`, `empty`, `full`,
`countCols`) are **not** DSL nodes and are omitted except where noted.

**Substrate:** every value is an `Image` = `{ position p, size sz, mask[] }` — a colored grid that
**carries its own position** (so "objects" and "grids" are the same type). `Image_` = const ref,
`vImage` = list of images. `badImg` = the failure value. Color `0` = blank/background-ish.

**Why the `id` params matter:** many functions take an integer `id` that selects a variant. The
named-function count is ~50, but the `id` expansion is what defines the real search space
(`rigid` = 9, `smear` = 15, `pickMax`/`maxCriterion` = 14, `compose` = 5, `count` = 7×3, etc.) —
roughly ~140+ concrete unary operations. This expansion is central to the freeze decision: the
icecuber DSL is *small in names, large in parameterization*.

---

## 1. Constructors / shape generators

| Function | Signature | What it does |
|---|---|---|
| `Col` | `(int id) → Image` | 1×1 image of color `id` (0–9). |
| `Pos` | `(int dx,int dy) → Image` | 1×1 image at position `(dx,dy)`. |
| `Square` | `(int id) → Image` | `id`×`id` filled square. |
| `Line` | `(int orient,int id) → Image` | `id`-long line, horizontal/vertical by `orient`. |
| `getPos` | `(Image) → Image` | 1×1 of majority color at the image's position. |
| `getSize` | `(Image) → Image` | image-sized block filled with majority color. |
| `getSize0` | `(Image) → Image` | image-sized block filled with 0. |
| `hull` | `(Image) → Image` | bounding box filled with majority color. |
| `hull0` | `(Image) → Image` | bounding box filled with 0. |
| `getW` / `getH` | `(Image,int id) → Image` | width/height-derived block (square or strip by `id`). |
| `toOrigin` | `(Image) → Image` | move position to `{0,0}`. |
| `majCol` | `(Image) → Image` | `Col(majorityColor)`. |
| `center` | `(Image) → Image` | the central 1–2 cell block. |

## 2. Color / filtering / recolor

| Function | Signature | What it does |
|---|---|---|
| `filterCol` | `(Image, Image palette) / (Image,int id)` | keep only cells whose color ∈ palette/`id`; else 0. |
| `colShape` | `(Image col, Image shape) / (Image,int id)` | paint `shape`'s footprint with `col` / with color `id`. |
| `broadcast` | `(Image col, Image shape, int include0=1)` | scale/tile the `col` pattern to fill `shape`'s size. |
| `invert` | `(Image) → Image` | swap blank↔filled (nonzero→0, 0→a present color). |
| `eraseCol` | `(Image,int col) → Image` | set all cells of `col` to 0. |
| `replaceCols` | `(Image base, Image cols)` | recolor each component of `base` by the majority overlapping color in `cols`. |
| `spreadCols` | `(Image, int skipmaj=0)` | flood every colored cell outward (BFS) until the grid is filled. |

## 3. Cropping / resizing

| Function | Signature | What it does |
|---|---|---|
| `compress` | `(Image, Image bg=Col(0)) / (Image)` | crop to the bounding box of non-background. |
| `compress2` | `(Image)` | delete fully-blank rows and columns. |
| `compress3` | `(Image)` | collapse runs of identical rows/cols (group single-color rectangles). |
| `half` | `(Image,int id)` | left / right / top / bottom half (`id` 0–3). |

## 4. Rigid / affine geometry

| Function | Signature | What it does |
|---|---|---|
| `transform` | `(Image,int A00,A01,A10,A11)` | apply a 2×2 integer matrix about the center. |
| `rigid` | `(Image,int id)` | the D4 group + heuristic: `id` 0–8 = identity, ±90°, 180°, flip-x/y, transpose, anti-transpose, heuristic-mirror. |
| `mirror2` | `(Image a, Image line)` | reflect `a` across a line-shaped image. |
| `mirrorHeuristic` | `(Image) → int` | helper: choose x- vs y-mirror by center of mass. |

## 5. Translation / alignment

| Function | Signature | What it does |
|---|---|---|
| `Move` | `(Image, Image p)` | translate by `p`'s position. |
| `alignx` / `aligny` | `(Image a, Image b,int id)` | align `a` to `b` on one axis (`id` 0–4: before/start/center/end/after). |
| `align` | `(Image a, Image b,int idx,int idy)` | 2-axis align (`idx,idy` 0–5). |
| `align` | `(Image a, Image b)` | align by the best-matching shared color. |

## 6. Composition / overlay / stacking

| Function | Signature | What it does |
|---|---|---|
| `compose` | `(Image a, Image b, fn, int overlap_only)` | general per-cell combine over union/intersection/`a`-frame. |
| `compose` | `(Image a, Image b,int id=0)` | 5 overlay modes (`id` 0–4: a-then-b, intersection, mask, in-a, inverse-mask). |
| `compose` | `(vImage,int id)` | fold the list with `compose(...,id)`. |
| `composeGrowing` | `(vImage)` | overlay all, largest-count first (smaller drawn on top). |
| `composeGrowingSlow` | `(vImage)` | reference version of the above. |
| `outerProductIS` / `outerProductSI` | `(Image a, Image b)` | Kronecker-style outer product (image×shape / shape×image). |
| `myStack` | `(Image a, Image b,int orient)` | stack two images H / V / diagonal (`orient` 0–3). |
| `myStack` | `(vImage,int id)` | stack a list (size-ordered) with `myStack(...,id)`. |
| `stackLine` | `(vImage)` | stack a list along the inferred row/column axis. |
| `wrap` | `(Image line, Image area)` | wrap a 1-D strip into the `area` rectangle. |
| `repeat` | `(Image a, Image b,int pad=0)` | tile `a` across `b`'s region. |
| `mirror` | `(Image a, Image b,int pad=0)` | mirror-tile `a` across `b`'s region. |

## 7. Connected components / splitting / cutting

| Function | Signature | What it does |
|---|---|---|
| `splitAll` | `(Image) → vImage` | 4-connected same-color components, each cropped. |
| `splitCols` | `(Image,int include0=0) → vImage` | one image per present color. |
| `splitColumns` / `splitRows` | `(Image) → vImage` | one image per column / per row. |
| `cut` | `(Image, Image sep) / (Image)` | split into pieces separated by a cut color (auto = `heuristicCut`). |
| `heuristicCut` | `(Image) → Image` | pick the best separating color (≥2 pieces, spans opposite sides, no nesting, max-min piece). |
| `getRegular` | `(Image) → Image` | detect a regular grid-line lattice in one color. |
| `insideMarked` | `(Image) → vImage` | find rectangles defined by 4 matching corner markers; return interiors. |

## 8. Pick / select-from-list

| Function | Signature | What it does |
|---|---|---|
| `pickMax` | `(vImage,int id) / (vImage, fn)` | pick the image maximizing criterion `id`. |
| `maxCriterion` | `(Image,int id) → int` | 14 ranking criteria (`id` 0–13: ±cell-count, ±area, color-count, ±pos.y/x, components, ±interior, ±hollowness). |
| `pickMaxes` / `pickNotMaxes` | `(vImage,int id) → vImage` | keep all images tied for max / not-max. |
| `pickUnique` | `(vImage,int id=0)` | pick the one image with a color unique across the list. |

## 9. Cut/split combinators (compose 7 + 8)

| Function | Signature | What it does |
|---|---|---|
| `cutPickMax` | `(Image a, Image b,int id) / (Image,int id)` | cut, then pick the max piece. |
| `regularCutPickMax` | `(Image,int id)` | `getRegular`-cut, then pick max. |
| `splitPickMax` | `(Image,int id,int include0=0)` | color-split, then pick max. |
| `cutPickMaxes` / `splitPickMaxes` | `(…,int id)` | cut/split, keep all maxes, compose them. |
| `cutCompose` | `(Image a, Image b,int id)` | cut, origin-align pieces, compose. |
| `regularCutCompose` | `(Image,int id)` | regular-cut then compose. |
| `splitCompose` | `(Image,int id,int include0=0)` | color-split (cropped) then compose. |
| `cutIndex` | `(Image a, Image b,int ind) / (Image,int ind)` | cut and return the `ind`-th piece. |

## 10. Fill / interior / borders

| Function | Signature | What it does |
|---|---|---|
| `Fill` | `(Image)` | flood-fill enclosed holes with majority color. |
| `interior` / `interior2` | `(Image)` | the enclosed-hole cells (two variants). |
| `border` | `(Image)` | the outer border cells of the shape. |
| `makeBorder` | `(Image,int bcol=1)` | add a 1-cell halo around filled cells. |
| `makeBorder2` | `(Image,int usemaj=1) / (Image, Image bord)` | wrap a uniform border ring around the grid. |
| `greedyFillBlack` | `(Image,int N=3)` | fill black using learned N×N tiles from the image's own patterns. |
| `greedyFillBlack2` | `(Image,int N=3)` | as above, keeping original non-black on top. |
| `greedyFill` | `(Image&, pieces, done, …)` | the underlying greedy N×N tiling engine. |
| `extend` | `(Image, Image room)` | extend by clamping edge colors to fill `room`. |
| `extend2` | `(Image, Image room)` | extend `room` by learned-pattern greedy fill. |

## 11. Counting → image

| Function | Signature | What it does |
|---|---|---|
| `count` | `(Image,int id,int outType)` | count (cells / colors / components / w / h / max / min — `id` 0–6) and emit as a square / row / column (`outType` 0–2) of majority color. |

## 12. Directional movement / connection

| Function | Signature | What it does |
|---|---|---|
| `smear` | `(Image base, Image room,int id)` | smear colors along directions within `room` (`id` 0–6: R, L, D, U, RL, DU, RLDU). |
| `smear` | `(Image,int id)` | self-smear, 8-directional set (`id` 0–14, incl. diagonals + all-8). |
| `connect` | `(Image,int id)` | draw lines between equal-color pairs (`id` 0–2: horizontal / vertical / both). |
| `gravity` | `(Image,int d) → vImage` | drop all pieces in direction `d` until they collide. |

## 13. Template matching

| Function | Signature | What it does |
|---|---|---|
| `replaceTemplate` | `(Image in, Image need, Image marked,int overlapping=0,int rigids=0)` | find `need` (optionally under all 8 rotations) and overwrite with `marked`. |
| `swapTemplate` | `(Image in, Image a, Image b,int rigids=0)` | swap every occurrence of `a`↔`b`. |

## 14. Frame / embed

| Function | Signature | What it does |
|---|---|---|
| `embed` | `(Image, Image shape)` | place `img` into `shape`'s frame/coordinate window. |
| `embedSlow` | `(Image, Image shape)` | reference version of `embed`. |

---

## Notes for the seed freeze

- **Type unification is the key idea.** One `Image` type with an embedded position means grids,
  objects, masks, palettes, and single colors are all the same type — so functions compose freely
  and the search is uniform. Our ontology splits these (`Grid`, `Object`, `Shape`, `Palette`,
  `Color`); a seed basis must decide whether to follow icecuber's unification or keep the split.
- **The DSL is enumerative, not inductive.** icecuber brute-forces compositions (depth-limited,
  with greedy "pieces" + DAG dedup), scoring by exact fit on the demos — no neural prior, no MDL.
  This is the front-2/3 recombination baseline; it is what our `search` stage must match or beat.
- **`id`-parameterization is the real surface.** A "minimal basis" debate that counts only the ~50
  names understates the space; the ~140+ `id`-variants are the actual primitives. Freeze decisions
  should be made at the `id`-variant level, not the function-name level.
- **Candidate seed primitives** (the recurring atoms most ARC-1 tasks compose from): `filterCol`,
  `compress`, `rigid`, `Move`/`align*`, `compose`, `splitAll`/`cut`, `colShape`/`replaceCols`,
  `count`, `smear`, `Fill`/`border`/`interior`, `broadcast`/`repeat`/`mirror`, `pickMax`/`pickUnique`.

**Provenance:** `top-quarks/ARC-solution` `@master`, `src/image_functions.cpp` +
`src/image_functions2.cpp`. Catalog generated 2026-06-15.
