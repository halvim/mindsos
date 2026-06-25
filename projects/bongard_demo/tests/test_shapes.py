"""m2 recognition — atom-relation shape definition discriminates square
from rectangle / rhombus / pentagon, through the real capability path
(cl.invoke), not a Python closure (PB-10). In-memory; no FalkorDB."""

from __future__ import annotations

import math

import pytest

from bongard import render as R
from bongard.control import build_solver
from bongard.ontology import SHAPE
from bongard.render import Sample, _rasterize_path, _regular_polygon
from bongard.shapes import (
    ATOMS,
    ATOMS_SET,
    DEFINITION_MATCH,
    SHAPE_DEFINITION,
    register_shapes,
)


def _sq(r, rot, cx=64.0, cy=64.0):
    return _rasterize_path(list(_regular_polygon(4, cx=cx, cy=cy, r=r, rot=rot)), closed=True)


def _rect(cx, cy, a, b):
    return _rasterize_path([(cx - a, cy - b), (cx + a, cy - b), (cx + a, cy + b), (cx - a, cy + b)], closed=True)


def _rhombus(cx, cy, a, b):
    return _rasterize_path([(cx, cy - b), (cx + a, cy), (cx, cy + b), (cx - a, cy)], closed=True)


def _sample(pixels):
    return Sample("m2", pixels, None, "solve", "")


@pytest.fixture(scope="module")
def trained():
    solver = build_solver()
    extract, induce, matches = register_shapes(solver.cl, solver.session)
    teach = [_sq(40, -math.pi / 2), _sq(30, 0.3), _sq(50, 0.7, 60, 68)]
    atoms_list = []
    for pixels in teach:
        v = solver.perceive(_sample(pixels))
        assert v.solved, v
        out = solver.cl.invoke(extract, {SHAPE.iri: v.shape}, session=solver.session)
        atoms_list.append(out.outputs[ATOMS.iri])
    definition = solver.cl.invoke(
        induce, {ATOMS_SET.iri: atoms_list}, session=solver.session
    ).outputs[SHAPE_DEFINITION.iri]
    return solver, extract, matches, definition


def _match(trained, pixels):
    solver, extract, matches, definition = trained
    v = solver.perceive(_sample(pixels))
    if not v.solved:
        return None
    atoms = solver.cl.invoke(extract, {SHAPE.iri: v.shape}, session=solver.session).outputs[ATOMS.iri]
    return solver.cl.invoke(
        matches, {ATOMS.iri: atoms, SHAPE_DEFINITION.iri: definition}, session=solver.session
    ).outputs[DEFINITION_MATCH.iri]


def test_accepts_heldout_squares(trained):
    assert _match(trained, _sq(22, 1.1, 80, 50)) is True
    assert _match(trained, _sq(45, -2.0)) is True


def test_rejects_rectangles(trained):
    assert _match(trained, _rect(64, 64, 50, 25)) is False
    assert _match(trained, _rect(64, 64, 42, 35)) is False


def test_rejects_rhombus_and_pentagon(trained):
    assert _match(trained, _rhombus(64, 64, 30, 48)) is False
    pentagon = _rasterize_path(list(_regular_polygon(5, r=40)), closed=True)
    assert _match(trained, pentagon) is False


def test_recognition_flows_through_capabilities(trained):
    _, extract, matches, _ = trained
    assert extract.startswith("capacity:") and matches.startswith("capacity:predicate:")
