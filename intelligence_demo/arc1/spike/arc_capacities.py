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

from mindsos_capacity.capacity import Capacity
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

# comparator is a family in ONTOLOGY §3 but NOT a shipped FUNCTIONAL category;
# register under a lazily-created category graph (same mechanism as dream.*).
CATEGORY_COMPARATOR = "comparator"

# ── DataState IRIs (arc realm) ──────────────────────────────────────────
DS_RAW_TASK = datastate_iri("arc.raw_task")
DS_TASK = datastate_iri("arc.task")
DS_PAIR = datastate_iri("arc.pair")
DS_RAW_GRID = datastate_iri("arc.raw_grid")
DS_GRID = datastate_iri("arc.grid")
DS_PALETTE = datastate_iri("arc.palette")
DS_OBJECT = datastate_iri("arc.object")
DS_SHAPE = datastate_iri("arc.shape")
DS_DIMENSION_DELTA = datastate_iri("arc.dimension_delta")
DS_PALETTE_DELTA = datastate_iri("arc.palette_delta")
DS_POINT = datastate_iri("arc.point")
DS_SAME_OBJECT = datastate_iri("arc.same_object")
DS_SAME_SHAPE = datastate_iri("arc.same_shape")
DS_SAME_POINT = datastate_iri("arc.same_point")
DS_MOVE_TRANSFORM = datastate_iri("arc.move_transform")


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
        ds("arc.palette", CATEGORY_DERIVATION, "Per-grid color set."),
        ds("arc.object", CATEGORY_DECOMPOSITION, "Monochrome connected component (size >= 2)."),
        ds("arc.shape", CATEGORY_DERIVATION, "Colorless normalized point-set."),
        ds("arc.point", CATEGORY_DECOMPOSITION, "Single-cell component (not an Object/Shape)."),
        ds("arc.dimension_delta", CATEGORY_COMPARATOR, "in/out Grid dimension change | None."),
        ds("arc.palette_delta", CATEGORY_COMPARATOR, "in/out Palette change | None."),
        ds("arc.same_object", CATEGORY_COMPARATOR, "same_object verdict: same color + position."),
        ds("arc.same_shape", CATEGORY_COMPARATOR, "same_shape verdict: identical normalized point-set."),
        ds("arc.same_point", CATEGORY_COMPARATOR, "same_point verdict: same colour + position."),
        ds("arc.move_transform", CATEGORY_COMPARATOR, "moved: translation Δ between same-shape objects."),
    ]


# ── capacity bodies (kwargs->dict convention; not invoked at M1) ─────────
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
            name="comprehend_task", category=CATEGORY_COMPREHENSION,
            inputs=(DS_RAW_TASK,), outputs=(DS_TASK, DS_PAIR, DS_RAW_GRID),
            implementation=_comprehend_task,
            description="Structural comprehension + role binding.",
        ),
        Capacity(
            name="build_grid", category=CATEGORY_PERCEPTION,
            inputs=(DS_RAW_GRID,), outputs=(DS_GRID,),
            implementation=_build_grid, description="RawGrid -> Grid (cells).",
        ),
        Capacity(
            name="extract_palette", category=CATEGORY_DERIVATION,
            inputs=(DS_GRID,), outputs=(DS_PALETTE,),
            implementation=_extract_palette, description="Per-grid color set.",
        ),
        Capacity(
            name="extract_objects", category=CATEGORY_DECOMPOSITION,
            inputs=(DS_GRID,), outputs=(DS_OBJECT,),
            implementation=_extract_objects,
            description="Monochrome connected components, all colors.",
        ),
        Capacity(
            name="extract_shapes", category=CATEGORY_DERIVATION,
            inputs=(DS_OBJECT,), outputs=(DS_SHAPE,),
            implementation=_extract_shapes, description="Object -> normalized Shape.",
        ),
        Capacity(
            name="extract_points", category=CATEGORY_DECOMPOSITION,
            inputs=(DS_GRID,), outputs=(DS_POINT,),
            implementation=_extract_points,
            description="Grid -> single-cell Points (size 1; not Objects/Shapes).",
        ),
    ]


def _profile_comparators() -> List[Capacity]:
    # Single declared input DataState (the comparator consumes two Grids of
    # the same DataState *type*; the in/out pairing is a sweep-time concern).
    return [
        Capacity(
            name="compare_grid_dimension", category=CATEGORY_COMPARATOR,
            inputs=(DS_GRID,), outputs=(DS_DIMENSION_DELTA,),
            implementation=lambda **kw: {DS_DIMENSION_DELTA: None},
            description="(in Grid, out Grid) -> DimensionDelta | None.",
        ),
        Capacity(
            name="compare_palette", category=CATEGORY_COMPARATOR,
            inputs=(DS_PALETTE,), outputs=(DS_PALETTE_DELTA,),
            implementation=lambda **kw: {DS_PALETTE_DELTA: None},
            description="(in Palette, out Palette) -> PaletteDelta | None.",
        ),
    ]


def _induce_capacities() -> List[Capacity]:
    # same_object + same_shape are pairwise comparators; the tiered match
    # (object-equal pairs / shape-equal groups / rest) is a fold over them
    # (arc_profile.match_pair), L4-style — no capacity calls another (#4 fold).
    return [
        Capacity(
            name="same_object", category=CATEGORY_COMPARATOR,
            inputs=(DS_OBJECT,), outputs=(DS_SAME_OBJECT,),
            implementation=lambda **kw: {DS_SAME_OBJECT: None},
            description="(in Object, out Object) -> Bool (same color + position).",
        ),
        Capacity(
            name="same_shape", category=CATEGORY_COMPARATOR,
            inputs=(DS_SHAPE,), outputs=(DS_SAME_SHAPE,),
            implementation=lambda **kw: {DS_SAME_SHAPE: None},
            description="(Shape, Shape) -> Bool (identical normalized point-set; no rotation).",
        ),
        Capacity(
            name="same_point", category=CATEGORY_COMPARATOR,
            inputs=(DS_POINT,), outputs=(DS_SAME_POINT,),
            implementation=lambda **kw: {DS_SAME_POINT: None},
            description="(Point, Point) -> Bool (same colour + position).",
        ),
        Capacity(
            name="moved", category=CATEGORY_COMPARATOR,
            inputs=(DS_OBJECT,), outputs=(DS_MOVE_TRANSFORM,),
            implementation=lambda **kw: {DS_MOVE_TRANSFORM: None},
            description="(in Object, out Object | same_shape) -> move Transform (Δ) | None if not displaced.",
        ),
    ]


# capacity IRIs (for assertions / introspection)
CAP_COMPREHEND = capacity_iri(CATEGORY_COMPREHENSION, "comprehend_task")
CAP_BUILD_GRID = capacity_iri(CATEGORY_PERCEPTION, "build_grid")
CAP_EXTRACT_PALETTE = capacity_iri(CATEGORY_DERIVATION, "extract_palette")
CAP_EXTRACT_OBJECTS = capacity_iri(CATEGORY_DECOMPOSITION, "extract_objects")
CAP_EXTRACT_SHAPES = capacity_iri(CATEGORY_DERIVATION, "extract_shapes")


def _short_ds(iri: str) -> str:
    # "datastate:arc.grid" -> "grid"
    return iri.split(":")[-1].split(".")[-1]


def ordered_catalog() -> List[dict]:
    """Capacities in pipeline order (perceive chain, then profile sweep),
    with consumes/produces — the list the debug UI renders."""
    rows: List[dict] = []
    for phase, caps in (("perceive", _perceive_capacities()),
                        ("profile-sweep", _profile_comparators()),
                        ("induce", _induce_capacities())):
        for c in caps:
            rows.append({
                "name": c.name,
                "category": c.category,
                "phase": phase,
                "consumes": [_short_ds(i) for i in c.inputs],
                "produces": [_short_ds(o) for o in c.outputs],
            })
    return rows


def install_arc(capacity_layer: CapacityLayer) -> None:
    """Register all arc DataStates + perceive/profile capacities (Global)."""
    for ds in arc_datastates():
        capacity_layer.register_datastate(ds, allow_new_realm=True)
    for cap in _perceive_capacities():
        capacity_layer.register_capacity(cap)
    for cap in _profile_comparators():
        capacity_layer.register_capacity(cap)
    for cap in _induce_capacities():
        capacity_layer.register_capacity(cap)


def fresh_layer() -> CapacityLayer:
    cl = CapacityLayer()
    install_arc(cl)
    return cl
