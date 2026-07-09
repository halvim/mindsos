"""Register the ARC perceive + profile capacities into a CapacityLayer.

Mirrors the shipped ``builtins/phase1_v0.py`` registration template.
DataStates live in the new ``arc`` realm (``allow_new_realm=True``).

What this proves (M1): the perceive chain is a real bipartite PRODUCES/
CONSUMES subgraph that ``find_pipeline`` can walk with NO router. The
profile comparators are registered as L3 nodes but are invoked by the
L4-style sweep (``arc_profile.profile_sweep``), not discovered by
``find_pipeline`` — honoring the locked split (PIPELINE.md: comparators =
phase_1 sweep; reasoning order = find_pipeline).
"""

from __future__ import annotations

from typing import Any, List

from mindsos_capacity.capacity import Capacity, INPUT_GROUP_FOLD
from mindsos_capacity.capacity_layer import CapacityLayer
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_COMPREHENSION,
    CATEGORY_DECOMPOSITION,
    CATEGORY_DERIVATION,
    CATEGORY_PERCEPTION,
    capacity_iri,
    datastate_iri,
)

from . import arc_grids

# These categories are NOT shipped core FUNCTIONAL categories; they register
# under lazily-created category graphs (same mechanism as dream.*), so any
# string works. capacity_iri embeds the category, so renaming a category
# re-IRIs its caps (keep CAP_* + gate references in sync).
#
# THE 7 CAPACITY CATEGORIES (the organizing axis):
#   PERCEIVER — build objects from the raw grid: comprehend_task, build_grid,
#               extract_palette/objects/shapes/points.
#   PROFILER  — universal sameness facts: compare_grid_dimension/compare_palette,
#               same_object/same_shape/same_point, same_cell_count/same_bbox_area.
#   OPERATOR  — combine components → a new Region (dual of decomposition): union.
#   DETECTOR  — detect a transform/change across in→out: moved, recolored,
#               rotated, reflected, touching_delta.
#   GENERATOR — apply a transform: recolor, rotate, reflect, move. A `kind`
#               field (continuous|discrete) sets the argument set (reason [+goal]).
#   PREDICATE — test an intra/inter-grid relation: touching, inside, inset.
#   REASONING — compose: build_correspondence, synthesize_selector, bg_deduction.
# (moved/touching/inside/recolored/rotated/reflected = the 6 ./evaluate targets.)
CATEGORY_PERCEIVER = "perceiver"
CATEGORY_PROFILER = "profiler"
CATEGORY_OPERATOR = "operator"
CATEGORY_DETECTOR = "detector"
CATEGORY_GENERATOR = "generator"
CATEGORY_PREDICATE = "predicate"
CATEGORY_REASONING = "reasoning"
# retained for the DataState provenance_category tags (DataStates keep their
# origin-family labels; only capacities move to the 7-category organization).
CATEGORY_COMPARATOR = "comparator"

# Generator KIND — the subdivision that defines a generator's argument set:
#   continuous (move) needs a reason AND a goal (move <direction> until <predicate>);
#   discrete   (recolor/rotate/reflect) needs only a reason (the transform param).
KIND_CONTINUOUS = "continuous"
KIND_DISCRETE = "discrete"
GENERATOR_KIND = {
    "move": KIND_CONTINUOUS,
    "recolor": KIND_DISCRETE, "rotate": KIND_DISCRETE, "reflect": KIND_DISCRETE,
}


def generator_kind(name: str) -> str:
    return GENERATOR_KIND.get(name)


def generator_args(name: str) -> tuple:
    """The motivation argument set for a generator (per its KIND):
    continuous -> ("reason", "goal"); discrete -> ("reason",)."""
    return ("reason", "goal") if GENERATOR_KIND.get(name) == KIND_CONTINUOUS else ("reason",)

# ── DataState IRIs (arc realm) ──────────────────────────────────────────
DS_RAW_TASK = datastate_iri("arc.raw_task")
DS_TASK = datastate_iri("arc.task")
DS_PAIR = datastate_iri("arc.pair")
DS_RAW_GRID = datastate_iri("arc.raw_grid")
DS_GRID = datastate_iri("arc.grid")
DS_PERCEIVED_GRID = datastate_iri("arc.perceived_grid")
DS_PALETTE = datastate_iri("arc.palette")
DS_OBJECT = datastate_iri("arc.object")
DS_SHAPE = datastate_iri("arc.shape")
DS_DIMENSION_DELTA = datastate_iri("arc.dimension_delta")
DS_PALETTE_DELTA = datastate_iri("arc.palette_delta")
DS_POINT = datastate_iri("arc.point")
DS_SAME_OBJECT = datastate_iri("arc.same_object")
DS_SAME_SHAPE = datastate_iri("arc.same_shape")
DS_SAME_POINT = datastate_iri("arc.same_point")
DS_SAME_CELL_COUNT = datastate_iri("arc.same_cell_count")
DS_SAME_BBOX_AREA = datastate_iri("arc.same_bbox_area")
DS_MOVE_TRANSFORM = datastate_iri("arc.move_transform")
DS_TOUCHING = datastate_iri("arc.touching")
DS_INSIDE = datastate_iri("arc.inside")
DS_INSET = datastate_iri("arc.inset")
DS_REGION = datastate_iri("arc.region")
DS_BACKGROUND = datastate_iri("arc.background")
DS_BACKGROUND_SET = datastate_iri("arc.background_set")
DS_CORRESPONDENCE = datastate_iri("arc.correspondence")
DS_STATE_CHANGE = datastate_iri("arc.state_change")
DS_SELECTOR = datastate_iri("arc.selector")
# transform family (generators consume a param; comparators produce a transform)
DS_COLOR = datastate_iri("arc.color")
DS_RECOLOR_TRANSFORM = datastate_iri("arc.recolor_transform")
DS_ROTATE_TRANSFORM = datastate_iri("arc.rotate_transform")
DS_REFLECT_TRANSFORM = datastate_iri("arc.reflect_transform")
# solve-stage DataStates — phases 8/9/10 dispatched as L3 DECISIONS (the L4
# driver sequences them; each result is L5 MM working state).
DS_PROFILE = datastate_iri("arc.profile")
DS_BG_CAND = datastate_iri("arc.bg_cand")
DS_RECOMPARISON = datastate_iri("arc.recomparison")
DS_ENCLOSED = datastate_iri("arc.enclosed")
DS_RULES = datastate_iri("arc.rules")
DS_SELECTION = datastate_iri("arc.selection")
DS_SOLVE = datastate_iri("arc.solve")


def arc_datastates() -> List[DataState]:
    def ds(name: str, cat: str, desc: str) -> DataState:
        return DataState(
            name=name,
            shape=ShapeDescriptor.opaque(name),
            description=desc,
            provenance_category=cat,
        )

    return [
        ds("arc.raw_task", CATEGORY_COMPREHENSION, "Deserialized, uninterpreted task."),
        ds("arc.task", CATEGORY_COMPREHENSION, "Structured task (role-bound pairs)."),
        ds("arc.pair", CATEGORY_COMPREHENSION, "A demonstration|test pair."),
        ds("arc.raw_grid", CATEGORY_COMPREHENSION, "An input|output grid, uninterpreted."),
        ds("arc.grid", CATEGORY_PERCEPTION, "A built Grid (cells)."),
        ds("arc.perceived_grid", CATEGORY_PERCEPTION, "Materialized per-grid perception bundle (objects+points+dims); the intra-grid predicate input."),
        ds("arc.palette", CATEGORY_DERIVATION, "Per-grid color set."),
        ds("arc.object", CATEGORY_DECOMPOSITION, "Monochrome connected component (size >= 2)."),
        ds("arc.shape", CATEGORY_DERIVATION, "Colorless normalized point-set."),
        ds("arc.point", CATEGORY_DECOMPOSITION, "Single-cell component (not an Object/Shape)."),
        ds("arc.dimension_delta", CATEGORY_PROFILER, "in/out Grid dimension change | None (profiler)."),
        ds("arc.palette_delta", CATEGORY_PROFILER, "in/out Palette change | None (profiler)."),
        ds("arc.same_object", CATEGORY_PROFILER, "same_object profiler: same color + position."),
        ds("arc.same_shape", CATEGORY_PROFILER, "same_shape profiler: identical normalized point-set."),
        ds("arc.same_point", CATEGORY_PROFILER, "same_point profiler: same colour + position."),
        ds("arc.same_cell_count", CATEGORY_PROFILER, "same_cell_count profiler: equal cell count (size); D4-invariant; implied by same_shape."),
        ds("arc.same_bbox_area", CATEGORY_PROFILER, "same_bbox_area profiler: equal bbox area (h×w); D4-invariant; implied by same_shape."),
        ds("arc.move_transform", CATEGORY_COMPARATOR, "moved: translation Δ between same-shape objects."),
        ds("arc.touching", CATEGORY_PREDICATE, "touching verdict: different-colour components share an 8-neighbour (intra-grid)."),
        ds("arc.inside", CATEGORY_PREDICATE, "inside verdict: a enclosed by a single-colour object b; intra-grid, background-excluded."),
        ds("arc.inset", CATEGORY_PREDICATE, "inset verdict: a's cell-set ⊆ b's cell-set (positional, reflexive); inter-grid; consumed by the subdivision process (phase 3) + the union operator."),
        ds("arc.region", CATEGORY_OPERATOR, "Region: an arbitrary cell-set (NOT necessarily monochrome/connected, so NOT an Object). Output of the union operator (cell-union of ≥2 components)."),
        ds("arc.background_candidate", CATEGORY_DERIVATION, "Per-grid background proposal from one detector (frequency at v1)."),
        ds("arc.background", CATEGORY_REASONING, "Reconciled background (fold over candidates; degenerate pass-through at v1)."),
        ds("arc.background_set", CATEGORY_REASONING, "Per-grid background-candidate set: per-colour component lists are mutated by the phases (add/remove/replace) and a colour is eliminated when its list empties; rules reapplied after each phase (arc_solver.bg_advance)."),
        ds("arc.correspondence", CATEGORY_REASONING, "input ref -> output ref map; unambiguous subset (ambiguous left uncorresponded)."),
        ds("arc.state_change", CATEGORY_COMPARATOR, "touching_delta: gained/lost/maintained across a pair over C, background-excluded."),
        ds("arc.selector", CATEGORY_REASONING, "Minimal discriminative state-conjunction resolving a unique mover + target."),
        ds("arc.color", CATEGORY_DERIVATION, "A single colour value (recolor generator parameter)."),
        ds("arc.recolor_transform", CATEGORY_COMPARATOR, "recolored: same shape + position, different colour | None."),
        ds("arc.rotate_transform", CATEGORY_COMPARATOR, "rotated: 90/180/270 rotation between Shapes | None."),
        ds("arc.reflect_transform", CATEGORY_COMPARATOR, "reflected: horizontal/vertical reflection between Shapes | None."),
        ds("arc.profile", CATEGORY_REASONING, "Built TaskProfile + per-phase working state (perceive/hypothesis)."),
        ds("arc.bg_cand", CATEGORY_REASONING, "Per-grid background candidates (bg_advance)."),
        ds("arc.recomparison", CATEGORY_REASONING, "Phase-4 sub-piece re-comparison results."),
        ds("arc.enclosed", CATEGORY_REASONING, "Phase-3 input-only enclosed-region cells per split (train/test)."),
        ds("arc.rules", CATEGORY_REASONING, "Phase-8 candidate rules + resolved bg."),
        ds("arc.selection", CATEGORY_REASONING, "Phase-9 minimum covering rule set (or None)."),
        ds("arc.solve", CATEGORY_REASONING, "Phase-10 solution: answer grid + matches_withheld."),
    ]


# ── capacity bodies (kwargs->dict convention; not invoked at M1) ─────────
def _touching_delta(**kw: Any) -> dict:
    """D3 ONE-SPECIMEN SPIKE (2026-06-21): a **real** body for `touching_delta`,
    executed through `capacity_layer.invoke`. This is the only reason cap with a
    live body — the rest stay stubs (D3 inline). It deliberately exposes the
    inline↔registered gap rather than hiding it:

      * It consumes the **pair** (`kw[DS_PAIR]`) + **background** (`kw[DS_BACKGROUND]`),
        NOT the DECLARED inputs (`DS_TOUCHING`, `DS_CORRESPONDENCE`). Core now
        enforces the CONSUMES contract at `invoke` (ADR-0072 §am-2), so this cap
        is registered `input_group=fold` — the sanctioned escape (GF-3 typed
        input-group): declared topology stays **provenance** (the cap folds over
        C), enforcement skipped, so the body's real inputs need not match it.
      * It recomputes touching + correspondence internally (a **monolith** over the
        pair) — so the reason-graph decomposition is paper-only; the body is not
        the composed cap the topology claims.
      * It reaches into `arc_solver` (deferred import) — an **inverted dependency**
        (the solver should invoke the cap, not vice-versa). Threading the
        CapacityLayer into the solver is the real (deferred) wiring cost.

    See PIPELINE_DECISIONS.md §4 (D3-spike entry) for the findings.
    """
    pair = kw.get(DS_PAIR)
    bg = kw.get(DS_BACKGROUND)
    if pair is None or bg is None:
        return {DS_STATE_CHANGE: None}
    from . import arc_solver
    return {DS_STATE_CHANGE: arc_solver.touching_changes(pair, bg)}


def _inside(**kw: Any) -> dict:
    """REAL body for the `inside` predicate (step 1 of the MindsOS wiring — the
    first detector/predicate moved off a stub). Consumes the **perceived-grid
    bundle** (objects+points+dims) — its honest input, mirroring how the
    `touching_delta` spike consumes the pair bundle — and returns the ray-based
    containment pairs. `bg_resolved=False` = the perception/∃-token result, so it
    matches `arc_profile.attach_relations` (`gs["inside"]`) grid-for-grid. Invoked
    through `cl.invoke`; no shadow — the registered cap IS the executed compute."""
    gs = kw.get(DS_PERCEIVED_GRID)
    if gs is None:
        return {DS_INSIDE: None}
    return {DS_INSIDE: arc_grids.contained_pairs(gs, bg_resolved=False)}


def _same_object(**kw: Any) -> dict:
    a, b = kw[DS_OBJECT]
    return {DS_SAME_OBJECT: arc_grids.same_object(a, b)}


def _arc_emit_candidates(**kw: Any) -> dict:
    """Phase 8 (L3 decision) — emit candidate rules from the profile. REAL body =
    the shipped `arc_solver.rules`; dispatched by the L4 driver, not inline."""
    prof = kw.get(DS_PROFILE)
    if prof is None:
        return {DS_RULES: None}
    from . import arc_solver
    enclosed = kw.get(DS_ENCLOSED)
    return {DS_RULES: arc_solver.rules(prof, kw.get(DS_BG_CAND),
                                       kw.get(DS_RECOMPARISON),
                                       (enclosed or {}).get("train"))}


def _arc_select_rules(**kw: Any) -> dict:
    """Phase 9 (L3 decision) — the minimum covering rule set (arc_solver.select_rules)."""
    prof, rules = kw.get(DS_PROFILE), kw.get(DS_RULES)
    if prof is None or rules is None:
        return {DS_SELECTION: None}
    from . import arc_solver
    return {DS_SELECTION: arc_solver.select_rules(prof, rules, kw.get(DS_ENCLOSED))}


def _arc_apply_solution(**kw: Any) -> dict:
    """Phase 10 (L3 decision) — apply the selected set to the TEST input → answer
    (mirrors `pipeline.step_solve` over `arc_solver._apply_candidate_set`)."""
    prof, sel, rules = kw.get(DS_PROFILE), kw.get(DS_SELECTION), kw.get(DS_RULES)
    if prof is None or sel is None or rules is None or not prof.get("test"):
        return {DS_SOLVE: None}
    from . import arc_solver
    bg = rules["bg"]
    tin = prof["test"][0]["input"]
    enc = (kw.get(DS_ENCLOSED) or {}).get("test") or []
    enc_cells = enc[0] if enc else None
    if not enc_cells:
        enc_cells = arc_grids.enclosed_bg_cells(tin["cells"], bg)
    out = arc_solver._apply_candidate_set(sel["set"], tin, bg, enc_cells)
    if out is None:
        return {DS_SOLVE: None}
    raw = kw.get(DS_RAW_TASK)
    matches = (out == raw["test"][0]["output"]) if (raw and raw.get("test")) else None
    return {DS_SOLVE: {"output": out, "matches_withheld": matches}}


def _comprehend_task(**kw: Any) -> dict:
    return {DS_TASK: kw.get(DS_RAW_TASK), DS_PAIR: None, DS_RAW_GRID: None}


def _build_grid(**kw: Any) -> dict:
    return {DS_GRID: kw.get(DS_RAW_GRID)}


def _extract_palette(**kw: Any) -> dict:
    g = kw.get(DS_GRID)
    return {DS_PALETTE: arc_grids.palette(g) if g else None}


def _extract_objects(**kw: Any) -> dict:
    g = kw.get(DS_GRID)
    return {DS_OBJECT: arc_grids.extract_objects(g) if g else None}


def _extract_shapes(**kw: Any) -> dict:
    o = kw.get(DS_OBJECT)
    return {DS_SHAPE: arc_grids.normalize_shape(o) if o else None}


def _extract_points(**kw: Any) -> dict:
    g = kw.get(DS_GRID)
    return {DS_POINT: arc_grids.extract_points(g) if g else None}


# ── capacity declarations (the perceive chain) ──────────────────────────
def _perceive_capacities() -> List[Capacity]:
    return [
        Capacity(
            name="comprehend_task", category=CATEGORY_PERCEIVER,
            inputs=(DS_RAW_TASK,), outputs=(DS_TASK, DS_PAIR, DS_RAW_GRID),
            implementation=_comprehend_task,
            description="Structural comprehension + role binding.",
        ),
        Capacity(
            name="build_grid", category=CATEGORY_PERCEIVER,
            inputs=(DS_RAW_GRID,), outputs=(DS_GRID,),
            implementation=_build_grid, description="RawGrid -> Grid (cells).",
        ),
        Capacity(
            name="extract_palette", category=CATEGORY_PERCEIVER,
            inputs=(DS_GRID,), outputs=(DS_PALETTE,),
            implementation=_extract_palette, description="Per-grid color set.",
        ),
        Capacity(
            name="extract_objects", category=CATEGORY_PERCEIVER,
            inputs=(DS_GRID,), outputs=(DS_OBJECT,),
            implementation=_extract_objects,
            description="Monochrome connected components, all colors.",
        ),
        Capacity(
            name="extract_shapes", category=CATEGORY_PERCEIVER,
            inputs=(DS_OBJECT,), outputs=(DS_SHAPE,),
            implementation=_extract_shapes, description="Object -> normalized Shape.",
        ),
        Capacity(
            name="extract_points", category=CATEGORY_PERCEIVER,
            inputs=(DS_GRID,), outputs=(DS_POINT,),
            implementation=_extract_points,
            description="Grid -> single-cell Points (size 1; not Objects/Shapes).",
        ),
    ]


def _profiler_capacities() -> List[Capacity]:
    """PROFILERS (universal task facts; NOT comparators): the profile-sweep
    multi-result facts + the sameness atoms. Single declared input DataState (the
    in/out pairing is a sweep-time concern). same_object/same_shape feed the
    tiered match (arc_profile.match_pair), a fold — no capacity invokes another
    via the layer (#4 fold; shared pure helpers allowed — GF-2)."""
    return [
        Capacity(
            name="compare_grid_dimension", category=CATEGORY_PROFILER,
            inputs=(DS_GRID,), operand_arity={DS_GRID: 2}, outputs=(DS_DIMENSION_DELTA,),
            implementation=lambda **kw: {DS_DIMENSION_DELTA: None},
            description="(in Grid, out Grid) -> DimensionDelta | None.",
        ),
        Capacity(
            name="compare_palette", category=CATEGORY_PROFILER,
            inputs=(DS_PALETTE,), operand_arity={DS_PALETTE: 2}, outputs=(DS_PALETTE_DELTA,),
            implementation=lambda **kw: {DS_PALETTE_DELTA: None},
            description="(in Palette, out Palette) -> PaletteDelta | None.",
        ),
        Capacity(
            name="same_object", category=CATEGORY_PROFILER,
            inputs=(DS_OBJECT,), operand_arity={DS_OBJECT: 2}, outputs=(DS_SAME_OBJECT,),
            implementation=_same_object,
            description="(in Object, out Object) -> Bool (same color + position).",
        ),
        Capacity(
            name="same_shape", category=CATEGORY_PROFILER,
            inputs=(DS_SHAPE,), operand_arity={DS_SHAPE: 2}, outputs=(DS_SAME_SHAPE,),
            implementation=lambda **kw: {DS_SAME_SHAPE: None},
            description="(Shape, Shape) -> Bool (identical normalized point-set; no rotation). Implies same_cell_count + same_bbox_area.",
        ),
        Capacity(
            name="same_cell_count", category=CATEGORY_PROFILER,
            inputs=(DS_SHAPE,), operand_arity={DS_SHAPE: 2}, outputs=(DS_SAME_CELL_COUNT,),
            implementation=lambda **kw: {DS_SAME_CELL_COUNT: None},
            description="(Shape, Shape) -> Bool (equal cell count; D4-invariant). Implied by same_shape; demanded by rotated/reflected.",
        ),
        Capacity(
            name="same_bbox_area", category=CATEGORY_PROFILER,
            inputs=(DS_SHAPE,), operand_arity={DS_SHAPE: 2}, outputs=(DS_SAME_BBOX_AREA,),
            implementation=lambda **kw: {DS_SAME_BBOX_AREA: None},
            description="(Shape, Shape) -> Bool (equal bbox area h×w; D4-invariant). Implied by same_shape; demanded by rotated/reflected.",
        ),
        Capacity(
            name="same_point", category=CATEGORY_PROFILER,
            inputs=(DS_POINT,), operand_arity={DS_POINT: 2}, outputs=(DS_SAME_POINT,),
            implementation=lambda **kw: {DS_SAME_POINT: None},
            description="(Point, Point) -> Bool (same colour + position).",
        ),
    ]


def _comparator_capacities() -> List[Capacity]:
    """COMPARATOR ``moved`` (inter-grid). recolored/rotated/reflected live in
    ``_transform_capacities``; touching/inside (PREDICATE) in
    ``_intra_grid_capacities`` — together the 6 ./evaluate targets."""
    return [
        Capacity(
            name="moved", category=CATEGORY_DETECTOR,
            inputs=(DS_OBJECT,), operand_arity={DS_OBJECT: 2}, outputs=(DS_MOVE_TRANSFORM,),
            implementation=lambda **kw: {DS_MOVE_TRANSFORM: None},
            description="(in Object, out Object | same_shape) -> move Transform (Δ) | None if not displaced.",
        ),
        Capacity(
            name="inset", category=CATEGORY_PREDICATE,
            inputs=(DS_OBJECT,), operand_arity={DS_OBJECT: 2}, outputs=(DS_INSET,),
            implementation=lambda **kw: {DS_INSET: None},
            description="(a Object, b Object) -> Bool (a's cell-set ⊆ b's cell-set; "
                        "positional, reflexive; inter-grid). Capacity-only (no Search "
                        "facet — near-universal); the subdivision process (phase 3) "
                        "consumes it via arc_grids.inset (D3 inline).",
        ),
    ]


def _operator_capacities() -> List[Capacity]:
    """OPERATORS — object constructors (combination family; dual of
    DECOMPOSITION). ``union`` combines objects into a Region. Registered for its
    I/O contract; L4-called when needed (no standing demo consumer — provenance,
    stub body, like every ARC cap per D3). Output is DS_REGION, not DS_OBJECT
    (the union of two objects need not be a valid Object). Arity fiction: a
    single declared DS_OBJECT input (operand-position is a core concern — §5
    Part 5), as with inset and the comparators."""
    return [
        Capacity(
            name="union", category=CATEGORY_OPERATOR,
            inputs=(DS_OBJECT,), operand_arity={DS_OBJECT: 2}, outputs=(DS_REGION,),
            implementation=lambda **kw: {DS_REGION: None},
            description="(a Object, b Object) -> Region (positional cell-union; "
                        "may be multi-colour/disconnected → Region not Object). "
                        "C = union(a,b) ⟹ inset(a,C) ∧ inset(b,C). Bg-excluded "
                        "occurrence detector = arc_grids.union_in_pair (D3 inline); "
                        "shown in ./evaluate as an operator (occurrence + demands).",
        ),
    ]


def _intra_grid_capacities() -> List[Capacity]:
    # touching = intra-grid positional predicate. Computed by the per-grid fold
    # (arc_profile.grid_summary -> touching_pairs), NOT discovered by
    # find_pipeline. Operand is Region/PointSet (Object|Point); the spike
    # declares DS_OBJECT as the nominal input (single declared type, as with the
    # other comparators — the participant pairing is fold-time).
    return [
        Capacity(
            name="touching", category=CATEGORY_PREDICATE,
            inputs=(DS_OBJECT,), outputs=(DS_TOUCHING,),
            implementation=lambda **kw: {DS_TOUCHING: None},
            description="(Region, Region) -> Bool (different-colour components share an 8-neighbour; intra-grid).",
        ),
        Capacity(
            name="inside", category=CATEGORY_PREDICATE,
            inputs=(DS_PERCEIVED_GRID,), outputs=(DS_INSIDE,),
            implementation=_inside,  # step-1 wiring: REAL body (first non-stub predicate)
            description="(perceived grid: objects+points+dims) -> contained_pairs "
                        "[{a, b}] (ray-based; a enclosed by single-colour object b; "
                        "cannot reach the grid border without crossing b; intra-grid). "
                        "bg_resolved=False = perception/∃-token result. REAL body "
                        "invoked through the layer — matches attach_relations 400/400.",
        ),
    ]


def _reason_capacities() -> List[Capacity]:
    return [
        Capacity(
            name="build_correspondence", category=CATEGORY_REASONING,
            inputs=(DS_SAME_OBJECT, DS_MOVE_TRANSFORM, DS_SAME_POINT),
            outputs=(DS_CORRESPONDENCE,),
            implementation=lambda **kw: {DS_CORRESPONDENCE: None},
            description="Fold over pairwise comparator verdicts -> Correspondence (strictest-first 1:1; ambiguous left uncorresponded).",
        ),
        Capacity(
            name="touching_delta", category=CATEGORY_DETECTOR,
            inputs=(DS_TOUCHING, DS_CORRESPONDENCE), outputs=(DS_STATE_CHANGE,),
            input_group=INPUT_GROUP_FOLD,  # folds over C; provenance topology,
            # invoke enforcement skipped (ADR-0072 §am-2 fold escape = GF-3 typed
            # input-group; the body reads pair+background, declared = provenance)
            implementation=_touching_delta,  # D3 spike: REAL body (sole non-stub)
            description="(touching over C) -> StateChange (gained/lost/maintained, background-excluded). "
                        "D3-spike: real body consumes the PAIR+BACKGROUND, not the declared "
                        "CONSUMES (which is fiction relative to the body) — see PIPELINE_DECISIONS §4.",
        ),
        Capacity(
            name="synthesize_selector", category=CATEGORY_REASONING,
            inputs=(DS_STATE_CHANGE, DS_OBJECT), outputs=(DS_SELECTOR,),
            implementation=lambda **kw: {DS_SELECTOR: None},
            description="(StateChange, Object features) -> Selector resolving a unique mover + target, else FLAG (option A; the shape tie-break is a recorded flag — real tie-break -> D11).",
        ),
        Capacity(
            name="bg_deduction", category=CATEGORY_REASONING,
            inputs=(DS_PALETTE, DS_SAME_OBJECT, DS_SAME_POINT),
            outputs=(DS_BACKGROUND_SET,),
            implementation=lambda **kw: {DS_BACKGROUND_SET: None},
            description="Per-grid background by ELIMINATION over PERSISTENT "
                        "per-colour component lists. The phases mutate the lists "
                        "(1 add · 2 remove same_object/same_point matches · 3 replace "
                        "subdivided wholes with sub-pieces · 4 remove colour-kept "
                        "sub-pieces); after each phase all rules reapply (FR1 commit "
                        "guard · FR3 len(cand)==1=>bg · PR1 empty-list elimination · "
                        "PR2 train->test inheritance). A colour is eliminated when its "
                        "component list empties. Real compute = arc_solver.bg_advance "
                        "(stub-registered here, D3).",
        ),
    ]


def _solver_capacities() -> List[Capacity]:
    """The SOLVE-stage L3 decisions (phases 8/9/10), real bodies wrapping the
    shipped `arc_solver` functions. The L4 driver (`arc_l4.solve_through_layer`)
    sequences them and threads the results — L4 = control, these = the decisions."""
    return [
        Capacity(
            name="emit_candidates", category=CATEGORY_REASONING,
            inputs=(DS_PROFILE, DS_BG_CAND, DS_RECOMPARISON, DS_ENCLOSED),
            outputs=(DS_RULES,), implementation=_arc_emit_candidates,
            description="Phase 8 — candidate rules per generator+param+condition.",
        ),
        Capacity(
            name="select_rules", category=CATEGORY_REASONING,
            inputs=(DS_PROFILE, DS_RULES, DS_ENCLOSED),
            outputs=(DS_SELECTION,), implementation=_arc_select_rules,
            description="Phase 9 — minimum covering rule set (or None).",
        ),
        Capacity(
            name="apply_solution", category=CATEGORY_REASONING,
            inputs=(DS_PROFILE, DS_SELECTION, DS_RULES, DS_ENCLOSED, DS_RAW_TASK),
            outputs=(DS_SOLVE,), implementation=_arc_apply_solution,
            description="Phase 10 — apply the selected set to the test input -> answer.",
        ),
    ]


# capacity IRIs (for assertions / introspection)
CAP_COMPREHEND = capacity_iri(CATEGORY_PERCEIVER, "comprehend_task")
CAP_EMIT_CANDIDATES = capacity_iri(CATEGORY_REASONING, "emit_candidates")
CAP_SELECT_RULES = capacity_iri(CATEGORY_REASONING, "select_rules")
CAP_APPLY_SOLUTION = capacity_iri(CATEGORY_REASONING, "apply_solution")
CAP_BUILD_GRID = capacity_iri(CATEGORY_PERCEIVER, "build_grid")
CAP_EXTRACT_PALETTE = capacity_iri(CATEGORY_PERCEIVER, "extract_palette")
CAP_EXTRACT_OBJECTS = capacity_iri(CATEGORY_PERCEIVER, "extract_objects")
CAP_EXTRACT_SHAPES = capacity_iri(CATEGORY_PERCEIVER, "extract_shapes")


def _short_ds(iri: str) -> str:
    # "datastate:arc.grid" -> "grid"
    return iri.split(":")[-1].split(".")[-1]


def _transform_capacities() -> List[Capacity]:
    """Transform family: GENERATORS (present; real bodies) + COMPARATORS (past;
    detect the transform across an in→out pair, fold-time like ``moved``).
    Generators are invokable but have no solver consumer yet (seed vocabulary)."""
    return [
        # generators (real bodies) — NOT shown in the Gates panel
        Capacity(
            name="recolor", category=CATEGORY_GENERATOR,
            inputs=(DS_OBJECT, DS_COLOR), outputs=(DS_OBJECT,),
            implementation=lambda **kw: {DS_OBJECT: arc_grids.recolor(kw[DS_OBJECT], kw[DS_COLOR])},
            description="(Object, Color) -> Object (every cell recoloured; shape/position kept).",
        ),
        Capacity(
            name="rotate", category=CATEGORY_GENERATOR,
            inputs=(DS_SHAPE, DS_ROTATE_TRANSFORM), outputs=(DS_SHAPE,),
            implementation=lambda **kw: {DS_SHAPE: arc_grids.rotate_shape(kw[DS_SHAPE], kw[DS_ROTATE_TRANSFORM])},
            description="(Shape, rotate Transform {90,180,270}) -> Shape (rotated, re-normalized).",
        ),
        Capacity(
            name="reflect", category=CATEGORY_GENERATOR,
            inputs=(DS_SHAPE, DS_REFLECT_TRANSFORM), outputs=(DS_SHAPE,),
            implementation=lambda **kw: {DS_SHAPE: arc_grids.reflect_shape(kw[DS_SHAPE], kw[DS_REFLECT_TRANSFORM])},
            description="(Shape, reflect Transform {horizontal,vertical}) -> Shape (reflected, re-normalized).",
        ),
        Capacity(
            name="move", category=CATEGORY_GENERATOR,
            inputs=(DS_OBJECT, DS_MOVE_TRANSFORM), outputs=(DS_OBJECT,),
            implementation=lambda **kw: {DS_OBJECT: arc_grids.translate(kw[DS_OBJECT], kw[DS_MOVE_TRANSFORM])},
            description="(Object, move Transform [dr,dc]) -> Object (translated; the moved↔move generator/detector pair). CONTINUOUS generator (needs a goal — move until a predicate).",
        ),
        # comparators (fold-time detection; stub bodies like moved) — Gates caps
        Capacity(
            name="recolored", category=CATEGORY_DETECTOR,
            inputs=(DS_OBJECT,), operand_arity={DS_OBJECT: 2}, outputs=(DS_RECOLOR_TRANSFORM,),
            implementation=lambda **kw: {DS_RECOLOR_TRANSFORM: None},
            description="(in Object, out Object | same_shape) -> recolor Transform | None (same shape+position, diff colour). recolored ⟹ same_shape.",
        ),
        Capacity(
            name="rotated", category=CATEGORY_DETECTOR,
            inputs=(DS_SHAPE,), operand_arity={DS_SHAPE: 2}, outputs=(DS_ROTATE_TRANSFORM,),
            implementation=lambda **kw: {DS_ROTATE_TRANSFORM: None},
            description="(in Shape, out Shape) -> rotate Transform (90/180/270) | None.",
        ),
        Capacity(
            name="reflected", category=CATEGORY_DETECTOR,
            inputs=(DS_SHAPE,), operand_arity={DS_SHAPE: 2}, outputs=(DS_REFLECT_TRANSFORM,),
            implementation=lambda **kw: {DS_REFLECT_TRANSFORM: None},
            description="(in Shape, out Shape) -> reflect Transform (horizontal/vertical) | None.",
        ),
    ]


#: display order of the 7 capacity categories (the organizing axis).
CATEGORY_ORDER = [CATEGORY_PERCEIVER, CATEGORY_PROFILER, CATEGORY_OPERATOR,
                  CATEGORY_DETECTOR, CATEGORY_GENERATOR, CATEGORY_PREDICATE,
                  CATEGORY_REASONING]


def ordered_catalog() -> List[dict]:
    """Capacities grouped by the 7 categories (perceiver → profiler → operator
    → detector → generator → predicate → reasoning), with consumes/produces —
    the list the debug UI + `_print_instance` render. ``phase`` = the category
    (the organizing axis)."""
    caps = (_perceive_capacities() + _profiler_capacities()
            + _comparator_capacities() + _intra_grid_capacities()
            + _operator_capacities() + _transform_capacities()
            + _reason_capacities() + _solver_capacities())
    rows = [{"name": c.name, "category": c.category, "phase": c.category,
             "consumes": [_short_ds(i) for i in c.inputs],
             "produces": [_short_ds(o) for o in c.outputs]} for c in caps]
    order = {cat: i for i, cat in enumerate(CATEGORY_ORDER)}
    rows.sort(key=lambda r: order.get(r["category"], len(order)))
    return rows


def install_arc(capacity_layer: CapacityLayer, session: Any = None) -> None:
    """Register all arc DataStates + capacities. ``session=None`` → Global (the
    demo gate). ``session`` present → the user's **Local** L3 (DataStates AND caps
    together — they must share scope; a Local cap referencing a Global DataState
    raises). Verified: all-Local registration round-trips."""
    for ds in arc_datastates():
        capacity_layer.register_datastate(ds, allow_new_realm=True, session=session)
    for group in (_perceive_capacities, _profiler_capacities, _comparator_capacities,
                  _intra_grid_capacities, _operator_capacities, _transform_capacities,
                  _reason_capacities, _solver_capacities):
        for cap in group():
            capacity_layer.register_capacity(cap, session=session)


def fresh_layer() -> CapacityLayer:
    cl = CapacityLayer()
    install_arc(cl)
    return cl
