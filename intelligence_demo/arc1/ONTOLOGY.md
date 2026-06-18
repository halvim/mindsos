# ARC Skill Acquisition — Step 1: Ontology Definition

**Status:** v0.7 · updated 2026-06-16 · living document
**Scope:** the ARC-1 domain world-model (MindsOS L2 `ontology` role-graph).
**Companions:** `LEXICON.md` (terms), `arc_lexicon_map.svg` (terms visual),
`arc_graph_L2_ontology.svg`, `arc_graph_L3_capacity.svg`, `arc_graph_L5_mm_instance.svg`.

---

## 0. MindsOS grounding (how this maps to the stack)

This is the **world-model** sense of "ontology" (class definitions + their relationships),
not a formal upper-ontology exercise. It maps onto MindsOS as:

| MindsOS component | What we put there |
|---|---|
| L2 `lexicon` role-graph | the named terms + definitions (`LEXICON.md`) |
| L2 `ontology` role-graph | **this file** — classes + relationship edges |
| L3 capacity / datastate | every *derived* class becomes a **DataState** (`register_datastate`, with `l2_roles` backlink to its ontology class); every derivation/comparison becomes a **capacity** |
| L5 per-task MM | instances (ABox): a concrete task's grids/cells/objects + discovered facts |

**Two substrate decisions (locked):**

- **OWL structure, no DOLCE alignment.** The shipped L2 ontology schema is OWL+DOLCE, but we use only the OWL machinery (`Class`/`Individual`/`ObjectProperty`, `SUBCLASS_OF`, `TYPE_OF`, `SUBPROPERTY_OF`) and do **not** anchor ARC classes under DOLCE's upper categories. ARC concepts are synthetic and don't map cleanly onto DOLCE; the demo's auditability is about the *program*, not upper-ontology classification. Reversible if the skill graduates to shared L2.
- **Composition = the native `compositional` hyperedge.** MindsOS `HyperEdge`/`IntergraphHyperEdge` carry a `compositional: bool` (and `ordered: bool`) flag with `anchors` (whole) + `members` (parts). Part-whole is one n-ary hyperedge, not N binary part-edges and not a DOLCE `hasComponent` property.

---

## 1. Relationship vocabulary

### 1.1 Structural edges

| Relation | MindsOS form | Meaning |
|---|---|---|
| **compositional hyperedge** | `HyperEdge(compositional=True, ordered=?)` | whole ⊣ {parts}. n-ary. `ordered=True` when members carry positional roles. |
| **`subclass_of`** | `SUBCLASS_OF` | class ⊑ class. *Object ⊑ Region.* |
| **`instance_of`** | `TYPE_OF` | individual ∈ class. *thisCell ∈ Cell* (ABox). |
| **`exemplifies`** (inv. `abstracts`) | registered `ObjectProperty` | concrete individual realizes an **abstract individual**. *Object exemplifies Shape.* No native OWL primitive — we register it. |
| **`has_attribute`** | `ObjectProperty`/`DataProperty` | a value, not a part. *Cell has_attribute Color.* |
| **`derived_from`** | `ObjectProperty` (+ an L3 capacity computes it) | computed from a source. *Figure derived_from Grid.* |

### 1.2 Role relationships (subproperties)

Roles **are** relationships — labelled, role-specializing edges, each a `SUBPROPERTY_OF`
a base relation (OWL gives us property-subtyping natively, so a part-whole walk inherits).
Naming: **`<family>:<role>`**, family ∈ a closed set of three.

- **`compositional:<role>`** — `SUBPROPERTY_OF` the compositional hyperedge / parthood.
  `compositional:input`, `compositional:output` (Pair→Grid); `compositional:demonstration`, `compositional:test` (Task→Pair).
- **`relational:<role>`** — relation-participant roles.
  `relational:from`, `relational:to` (Vector, Congruence); `relational:container`, `relational:contained` (Containment); `relational:left`, `relational:right` (compare).
- **`functional:<role>`** — capacity I/O; maps to the shipped L3 edges.
  `functional:consumes` → `CONSUMES`, `functional:produces` → `PRODUCES`.

Discipline: add a role-edge only where the role distinguishes participants; homogeneous bags
(grid←cells) stay a plain compositional hyperedge.

---

## 2. Class catalog

`[1..*]` = cardinality. Visual: `arc_graph_L2_ontology.svg`.

### 2.1 Structural (the puzzle)

- **Task** — compositional ⊣ Pair `[1..*]`. Member pairs carry `compositional:demonstration` | `compositional:test`.
- **Pair** — compositional (ordered) ⊣ Grid `[2]`: `compositional:input`, `compositional:output`.
- **Grid** — compositional ⊣ Cell `[1..*]`; `has_attribute` Dimension; `derived_from`-sources for Palette, Background, Figure.
- **Cell** — `has_attribute` Position, Color.
- **Position** — value `(row, col)`.
- **Color** — value (symbol 0–9). Categorical, not ordinal.
- **Background** — a Color in the `functional:background` role, **derived per-grid** (most-frequent color). *Not a subclass of Color.*
- **Palette** — compositional ⊣ Color `[1..*]`; `derived_from` Grid (set present).
- **Figure** — `derived_from` Grid; compositional ⊣ Object `[0..*]` (non-background content).
- **Dimension** — value `(H, W)`.

### 2.2 Objects & abstraction

- **Object** — `subclass_of` Region; **monochrome** (`has_attribute` one Color); a set of points **connected under 8-connectivity** (orthogonal OR diagonal — the single fixed object rule, §4 #1b); compositional ⊣ Cell `[2..*]` (**size ≥ 2** — a single cell is a Point, NOT an Object, §4 #15); `exemplifies` Shape; `has_attribute` Position, BBox.
- **Group** — compositional ⊣ Object `[2..*]`; built by the `add` capacity; `derived` Coloring (from parts) + PointSet geometry (may be disconnected). *Result of adding objects — not an Object.*
- **Shape** — colorless, connected, normalized point-set; `subclass_of` PointSet; abstract **individual** (capacities transform it). Object `exemplifies` it; shared/reusable. **Connected = under 8-connectivity (orthogonal *or* diagonal)** — a diagonal line *is* a Shape. Object and Shape share the **same** 8-connectivity rule (§4 #1b/#7).
- **PointSet** — general (possibly disconnected) set of normalized points; the operand for transform/compare capacities. `Shape` = the connected case.
- **Sub-shape** — a *subdivision* of a Shape; **not a distinct class** — it is a `Shape` in the
  `compositional:part` role. Composition is **recursive**: a Shape subdivides into sub-shapes
  (`compositional ⊣ Shape`), which subdivide further, bottoming out at the **Point** atom.
  "points → sub-shapes → Shape" is a **granularity gradient**, not three types. A simple Shape
  subdivides straight to Points (zero intermediate levels); a complex one nests.
  - **Extension vs decomposition (distinct relations):** a Shape's **point-set is its extension**
    (what it *is* — intrinsic, unique). A Shape's **sub-shape decomposition is a chosen structure**
    (non-unique — many valid splits). The Point (atom) level is exact; intermediate sub-shape
    levels are hypotheses → the canonical decomposition is a **reasoning judgment**, not a stored fact.
- **Point** — the **atomic** subdivision (a normalized cell-position). All Shapes/sub-shapes
  reduce to Points. (`Cell` = a Point with a Color; the Shape level is colorless.) A
  **single-cell connected component IS a Point** (extracted by `extract_points`) and is **neither
  an Object nor a Shape** (§4 #15); only `same_point` (colour + position) applies to it —
  `same_object`/`same_shape` never do.
- **Base shapes** — ordinary named `Shape` individuals that are *easily recognizable* and recur:
  `vertical`, `horizontal`, `diagonal`, `square` (filled). **Abstract templated individuals**
  living in the ontology, **parametric by size** (`vertical(n)`, `square(n)`), with the concrete
  size-N instantiated at runtime (not a stored individual per size, not learned generation). A
  Shape is recognized *as* a base shape by **matching against the template** (a comparator), per
  the 8-connectivity Shape rule (so `diagonal` is a valid base shape). `cube` is **not** defined
  (ARC is 2D).
- **Template** — a recurring Shape + Color pattern.
- **Pattern** — **not a class** — a composite over 2+ Shapes via the `compositional` hyperedge whose
  **anchor is a (possibly disconnected) PointSet**, with the inter-member offsets carried as
  `relational:from`/`to` **Vector** edges. "2+ shapes bound by their distance vectors = one unit."
  Mirrors sub-shape (composition, not a type); the binding Vector is produced by the `offset` capacity.
- **Divider** — **a role, not a class** — a full-span `vertical`/`horizontal` line that is *invariant*
  across input↔output (detected by `same_object`). Same-dim only (needs a shared frame). The geometry is
  a sized base shape; "divider" is the derived separator role.
- **Lattice(N)** — a composite/pattern: **repeating** vertical + horizontal dividers; `N` = the side
  of the repeating cell-square; **1-thick lines** (default); a single crossing `lattice(N)` spans
  `(2N+1)²`. Detector (≈ icecuber `getRegular`) / generator pair.
- **Region** — any cell-set; `has_attribute` BBox, Mask, Area.
- **BBox** — `subclass_of` Region (rectangular); `derived_from` Region; `(r0,c0,r1,c1)`.
- **Mask** — `derived_from` Region; boolean footprint.
- **Connectivity** — **fixed at 8-connectivity** (orthogonal ∪ diagonal). An Object is a monochrome point-set connected under this rule; there is no ranked strong/weak layering and no per-task override. (Was a ranked adjacency-layer parameter through v0.4; collapsed to the single rule at v0.5.)
- **ColorMode** — `monochrome` (default). (Multi-color is handled by `Group`/composition, not by relaxing the Object atom.)

### 2.3 Relations

Relation *types* are named here; **instances are computed by capacities** (`comparator`/`predicate`
family) and materialized into the task MM only when worth keeping — nothing is pre-stored.

- **Vector** `(Δr, Δc)` — `relational:from`/`to`. Distinct from **Distance** (scalar; `parameterized_by` Metric). Produced between two Objects by the **`offset`** capacity (vector between bbox origins) — this is the directional offset; `distance` stays the direction-discarding scalar.
- **Congruence** — two PointSets equal up to a D4 transform; computed by a comparator; `relational:from`/`to` + the transform.
- **Alignment** (Axis), **Symmetry** (Axis/order) — reified when they carry a parameter.
- **Touching** — **parameter-free** (connectivity fixed at 8, §4 #1b) → plain `touches` edge, like Containment/Overlap. Holds **only between different-colour objects** (same-colour 8-adjacent cells are already one component) and any **Point**; operand = Region/PointSet. Computed by the `touching` predicate (§3). The **intra-grid** member of the positional-comparison axis (`moved` = the **inter-grid** member).
- **Containment**, **Overlap** — parameter-free → plain `contains`/`overlaps` edges; promote later only if needed.

### 2.4 Operational

- **Operation / capacity** — `functional:consumes` → … → `functional:produces`. Grouped by the shipped L3 **families** (tags, not superclasses): see §3.
- **Rule / Program** — an ordered pipeline of Operations; `consumes` input-Grid, `produces` output-Grid.
- **Predicate** — a total test over an attribute (no abstain).
- **Transform** — a parameterized change between two Shapes, shared by a **detector/generator pair**:
  - **detector** (past tense — `moved`, `rotated`, `scaled`): `(A, B) → Transform | None`
    (`comparator` family; the `None`/value is the yes+how). Used in **induce**.
  - **generator** (present tense — `move`, `rotate`, `scale`): `(A, Transform) → B`
    (`transform` family). Used in **apply**.
  - The two are paired around **one shared `Transform` DataState** — the detector `PRODUCES` it,
    the generator `CONSUMES` it, so `find_pipeline` pairs them with no dispatcher. **Rule:** a
    transform exists **iff** a detector exists (richness ranges from full parameter recovery for
    rigid/scale to an existence check `generator(A)==B?` for fill/compress). **Correspondence**
    (which A maps to which B) is a separate reasoning pre-step, *not* part of the transform.

### 2.5 Inference (solver-facing)

- **Consistency** — a Rule reproduces every demonstration (necessary, not sufficient).
- **Generalization** — the Rule also produces the held-out Answer.
- **Abstain** — "no consistent Rule within budget" (structural verdict, not low-confidence).

---

## 3. Capacities → shipped L3 families

Every derivation/comparison registers as a capacity under an **existing** family
(`mindsos_capacity/family_rules.py`). Visual: `arc_graph_L3_capacity.svg`.

| Capacity | consumes → produces | family | dont-know |
|---|---|---|---|
| recognize_cell | (Coordinate, Color) → Cell | `perception` | DATASTATE_MARKER |
| build_grid | Cell* → Grid | `perception` | DATASTATE_MARKER |
| detect_background | Grid → Background | `perception` | DATASTATE_MARKER |
| extract_objects | Grid → Object* (8-conn, size ≥ 2) | `decomposition` | (deferred default) |
| extract_points | Grid → Point* (single cells) | `decomposition` | (deferred default) |
| normalize_shape | Object → Shape | `derivation` | DATASTATE_MARKER |
| rotate / reflect / recolor / translate | Shape/Object → Shape/Object | `transform` | DATASTATE_MARKER |
| add | Object × Object → Group | `combination` | OPTIONAL_RETURN |
| union | PointSet × PointSet → PointSet | `combination` | OPTIONAL_RETURN |
| compare (`is_rotation`, `is_congruent`, …) | PointSet × PointSet → Transform? | `comparator` | OPTIONAL_RETURN |
| distance | A × B → Scalar | `metric` | OPTIONAL_RETURN |
| offset | Object × Object → Vector (bbox-origin Δ) | `comparator` | OPTIONAL_RETURN |
| same_object | Object × Object → Bool (same color + position) | `comparator` | OPTIONAL_RETURN |
| same_shape | Shape × Shape → Bool (identical normalized point-set; no rotation) | `comparator` | OPTIONAL_RETURN |
| same_point | Point × Point → Bool (same colour + position) | `comparator` | OPTIONAL_RETURN |
| moved | (in Object, out Object) → move Transform `{kind:translate, vector:Δ}` \| None unless same colour + same shape + displaced (self-guards) | `comparator` | OPTIONAL_RETURN |
| touching | (Region, Region) → Bool (share an 8-neighbour; **different-colour objects + Points only**; parameter-free) | `predicate` | NO_DONT_KNOW |
| same_color, aligned … | entities → Bool | `predicate` | NO_DONT_KNOW |

`compare(A, B, fn)` is a **call-site convenience**: `fn` is a first-class comparator-family
capacity, and selecting it is the bipartite `find_pipeline` choosing among comparator nodes
between two DataStates — there is no separate higher-order dispatcher node.

---

## 4. Resolved decisions

| # | Decision | Resolution |
|---|---|---|
| 1 | Shape identity | colorless connected point-set; translation-normalized; **not** rotation/reflection. Shape is an *individual* (transformed by capacities). Object `exemplifies` Shape; color on the Object. |
| 1b | Connectivity | **An Object IS a monochrome set of points connected under 8-connectivity (orthogonal OR diagonal).** Single fixed rule — no ranked strong/weak layers, no per-task override. Matches Shape connectivity (#7). *(Revised v0.5; superseded the ranked-adjacency-layer model.)* |
| 2 | Object color | **monochrome** atom; multi-color via `add` → **Group** (a distinct class). Coloring derived from parts. |
| 2b | add vs union | separate capacities: `add` (Object×Object→Group, structure-preserving) vs `union` (PointSet→PointSet, geometry-only). `overlay`/`merge` deferred as known family members. |
| 3 | Background | per-Grid, derived; input/output may differ; no Task-level. |
| 4 | Query/Answer/Demo | role-bindings, **not** classes (Pair: demonstration|test; Grid: input|output). `withheld` is the one real attribute on the Answer. |
| 5 | Relations | computed by `comparator`/`predicate` capacities; discovered facts materialized into the task MM. Parametric ones reified; `contains`/`overlaps` stay plain edges. |
| 6 | Operation grouping | shipped L3 **families** as tags, not superclasses. |
| — | is-a split | `subclass_of` (`SUBCLASS_OF`) · `instance_of` (`TYPE_OF`) · `exemplifies` (registered ObjectProperty). |
| — | roles | first-class `<family>:<role>` relationships, `SUBPROPERTY_OF` a base relation. Families: compositional / relational / functional. |
| — | DOLCE | not used (OWL structure only). |
| — | composition | native `compositional` hyperedge (`ordered` for positional roles). |
| 7 | Shape connectivity | connected = under **8-connectivity** (orthogonal *or* diagonal); a diagonal *is* a Shape. **Same rule as Object connectivity (§1b)** — unified at v0.5. |
| 8 | Sub-shape | **not a class** — a `Shape` in `compositional:part`. Recursive subdivision Shape→sub-shapes→…→**Point** (atom). Extension (Shape→Point, unique) ≠ decomposition (Shape→sub-shape, chosen → reasoning judgment). |
| 9 | Base shapes | named abstract templated `Shape` individuals in ontology (`vertical`/`horizontal`/`diagonal`/`square` filled), parametric by size, size-N instantiated at runtime; recognized by matching (comparator). `cube` dropped (2D). |
| 10 | Transform | detector/generator pair around one shared `Transform` DataState (past-tense comparator `PRODUCES`, present-tense generator `CONSUMES`); exists iff a detector exists; correspondence is a separate pre-step. |
| 11 | Pattern | **not a class** — composite hyperedge over 2+ Shapes (disconnected-PointSet anchor) + `relational:from`/`to` Vector edges (the `offset`). |
| 12 | Divider | **a role, not a class** — full-span `vertical`/`horizontal` line invariant across input↔output (via `same_object`); same-dim. |
| 13 | Lattice(N) | composite/pattern of repeating dividers; `N` = cell-square side, 1-thick lines; single crossing `(2N+1)²`; detector(≈`getRegular`)/generator pair. |
| 14 | offset vs distance | `offset` (Object×Object → **Vector**, bbox-origin Δ) keeps direction; `distance` stays the **scalar** metric. |
| 15 | Point vs Object | A **single-cell** 8-connected component is a **Point**, **not an Object and not a Shape**. Objects are size ≥ 2 (Object cardinality `[2..*]`). Points are extracted by `extract_points`; only `same_point` (colour + position) applies — `same_object`/`same_shape` never touch Points. Points are not grouped. *(v0.6.)* |
| 16 | Touching | **Positional predicate**, parameter-free (connectivity fixed §1b). `(Region, Region) → Bool`, true iff the two share an 8-neighbour. Holds **only between different-colour objects and Points** (same-colour 8-adjacent cells are one component); operand Region/PointSet. Serves **both** induce-time structure (grouping + correspondence P3 + hypotheses) **and** apply/verify-time rule conditions (selectors); the rule-condition role commits Rules to relational selectors → bears on P1 (leans (c)). The **intra-grid** member of the **positional-comparison** axis (a cross-cutting operand tag, **not** a functional family); `moved` is the **inter-grid** member. *(v0.7.)* |

---

## 5. Changelog

- **v0.7** (2026-06-16) — **Touching predicate + positional-comparison categorization (§4 #16).**
  `touching` `(Region, Region) → Bool` (share an 8-neighbour), parameter-free (connectivity fixed
  §1b), holds **only between different-colour objects and Points**; serves both induce-time structure
  and apply/verify-time rule conditions. Capability-organization: a cross-cutting **positional
  comparison** tag splits into **intra-grid** (`touching`, predicate) and **inter-grid** (`moved`,
  comparator) — an operand/axis tag, **not** a functional family (PIPELINE.md Build progress). §2.3
  touching moved from parameterized to plain `touches` edge.
- **v0.6** (2026-06-15) — **Point vs Object boundary (§4 #15).** A single-cell component is a
  **Point** — neither an Object nor a Shape; Objects are size ≥ 2 (cardinality `[2..*]`). New
  `extract_points` capacity (Grid → Point*) + `same_point` comparator (colour + position). Points
  are not grouped; `same_object`/`same_shape` never apply to them. Also renamed `is_equal` →
  `same_object` and added `same_shape` (object-tier matching) in this cycle.
- **v0.5** (2026-06-15) — **object-connectivity rule revised.** An Object IS a monochrome set of
  points connected under **8-connectivity** (orthogonal OR diagonal) — a single fixed rule. The
  v0.4 ranked-adjacency-layer model (orthogonal-primary default + diagonal weak super-objects +
  per-task override) is **superseded**. Object and Shape connectivity now unified (§4 #1b = #7).
  Connectivity is no longer an extraction parameter. Propagated to the M1 spike (`extract_objects`
  8-conn, connectivity toggle removed). Trade-off accepted: corner-touching same-color objects merge.
- **v0.4** (2026-06-15) — pipeline-chat additions. Shape connectivity = 8-conn (diagonal is a Shape);
  sub-shape = recursive `compositional:part` subdivision down to the Point atom (extension vs
  decomposition split); base shapes as named templated Shape individuals (`vertical`/`horizontal`/
  `diagonal`/`square`, `cube` dropped); Transform detector/generator pair around a shared Transform
  DataState; Pattern (composite, not a class) + Divider (role) + Lattice(N) (composite) + `offset`
  (Object×Object→Vector) + `same_object`; `offset`≠`distance`. Decisions §4 #7–14.
- **v0.3** (2026-06-15) — consolidation. MindsOS grounding (OWL no-DOLCE, compositional hyperedge, L2/L3/L5 mapping); monochrome Object + Group; Shape = connected PointSet (individual); capacities → shipped families; comparators via `compare(A,B,fn)`; roles as `<family>:<role>` subproperties; is-a three-way split; Background/Query/Answer as role-bindings. Three layer graphs added.
- **v0.2** (2026-06-15) — first decision pass (superseded by v0.3 grounding).
- **v0.1** (2026-06-15) — initial draft (TBox/ABox, generic edge types).
