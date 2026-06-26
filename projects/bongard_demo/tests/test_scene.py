"""m3 — multi-object scene parse + relations (in-memory, sandbox-fast).

Exercises the full m3 vertical (PLAN D-M3-* / first slice A+): connected-
components individuation → per-figure ``cl.invoke`` chain → ``Scene`` →
``extract_relations`` predicate through real ``cl.invoke`` emitting
role-labeled ``same_shape`` hyperedges. No ``mindsos_*`` edits, no
FalkorDB (CapacityLayer() + DuckSession).
"""

from __future__ import annotations

from bongard.control import Solver
from bongard.relations import REL_SAME_SHAPE
from bongard.scene import connected_components, parse_scene, scene_relations
from bongard import render


def _solver() -> Solver:
    return Solver("bongard-m3")


# ── individuation ──────────────────────────────────────────────────────

def test_connected_components_splits_disjoint_figures():
    img = render.scene_two_squares()
    comps = connected_components(img)
    assert len(comps) == 2
    # union of components == original foreground (lossless split)
    union = set().union(*[set(c.fg) for c in comps])
    assert union == set(img.fg)


def test_overlapping_figures_are_one_component():
    img = render.scene_overlapping()
    assert len(connected_components(img)) == 1


# ── scene parse ────────────────────────────────────────────────────────

def test_two_squares_parse_to_two_shapes():
    scene = parse_scene(_solver(), render.scene_two_squares())
    assert scene.n_shapes == 2
    assert {s.polygon_type for s in scene.shapes} == {"quadrilateral"}
    assert scene.n_abstained == 0


def test_square_triangle_parse():
    scene = parse_scene(_solver(), render.scene_square_triangle())
    assert scene.n_shapes == 2
    assert {s.polygon_type for s in scene.shapes} == {"quadrilateral", "triangle"}


def test_three_mixed_parse():
    scene = parse_scene(_solver(), render.scene_three_mixed())
    assert scene.n_shapes == 3
    types = sorted(s.polygon_type for s in scene.shapes)
    assert types == ["pentagon", "triangle", "triangle"]


def test_overlapping_scene_abstains():
    scene = parse_scene(_solver(), render.scene_overlapping())
    assert scene.n_shapes == 0          # the single merged component won't parse
    assert scene.n_abstained == 1


# ── relations (through real cl.invoke) ─────────────────────────────────

def test_same_shape_relation_two_squares():
    s = _solver()
    scene = parse_scene(s, render.scene_two_squares())
    rels = scene_relations(s, scene)
    assert len(rels) == 1
    r = rels[0]
    assert r.rel_type == REL_SAME_SHAPE
    assert (r.subj, r.obj) == (0, 1)
    assert r.symmetric


def test_no_same_shape_when_types_differ():
    s = _solver()
    scene = parse_scene(s, render.scene_square_triangle())
    rels = scene_relations(s, scene)
    assert rels == ()


def test_one_same_shape_pair_among_three():
    s = _solver()
    scene = parse_scene(s, render.scene_three_mixed())
    rels = scene_relations(s, scene)
    # two triangles (indices 0,1) match; pentagon (2) does not
    assert len(rels) == 1
    assert rels[0].rel_type == REL_SAME_SHAPE
    assert {rels[0].subj, rels[0].obj} == {0, 1}
