"""m2 mint — a taught 'square' node is a composite over the parse (option A),
recognizes through cl.invoke, and survives a restart.

  * in-memory: the reactivation-factory-built runner discriminates square
    from rectangle (no DB).
  * integration (live FalkorDB): teach 'square' -> persist -> fresh KL/CL
    (restart) -> boot_local reactivates it -> the reloaded node still
    accepts squares and rejects rectangles, with no code registration.
"""

from __future__ import annotations

import math
import uuid

import pytest

from bongard.control import Solver, build_solver
from bongard.mint import (
    induce_from_examples,
    mint_shape,
    register_shape_reactivation,
    shape_descriptor,
    shape_reactivation_factory,
)
from bongard.ontology import SHAPE
from bongard.render import Sample, _rasterize_path, _regular_polygon
from bongard.shapes import DEFINITION_MATCH, register_shapes


def _sq(r, rot, cx=64.0, cy=64.0):
    return _rasterize_path(list(_regular_polygon(4, cx=cx, cy=cy, r=r, rot=rot)), closed=True)


def _rect(cx, cy, a, b):
    return _rasterize_path([(cx - a, cy - b), (cx + a, cy - b), (cx + a, cy + b), (cx - a, cy + b)], closed=True)


def _sample(pixels):
    return Sample("m2", pixels, None, "solve", "")


def _teach_squares():
    return [_sample(_sq(40, -math.pi / 2)), _sample(_sq(30, 0.3)), _sample(_sq(50, 0.7, 60, 68))]


def _match(cl, session, minted_iri, solver, pixels):
    v = solver.perceive(_sample(pixels))
    assert v.solved, v
    return cl.invoke(minted_iri, {SHAPE.iri: v.shape}, session=session).outputs[DEFINITION_MATCH.iri]


def test_minted_node_runner_discriminates_in_memory():
    solver = build_solver()
    register_shapes(solver.cl, solver.session)
    register_shape_reactivation(solver.cl)

    definition = induce_from_examples(solver, _teach_squares())
    descriptor = shape_descriptor("square", definition, solver.params)
    decl = shape_reactivation_factory(solver.cl)(descriptor)
    solver.cl.register_capacity(decl, session=solver.session, if_exists="upsert")

    assert _match(solver.cl, solver.session, decl.iri, solver, _sq(22, 1.1, 80, 50)) is True
    assert _match(solver.cl, solver.session, decl.iri, solver, _rect(64, 64, 50, 25)) is False


@pytest.fixture
def falkor_client():
    try:
        from mindsos_core.config import FalkorConfig
        from mindsos_core.persistence import FalkorClient
    except Exception as e:
        pytest.skip(f"FalkorClient import failed: {e}")
    base = FalkorConfig.from_env()
    config = FalkorConfig(
        host=base.host, port=base.port, password=base.password,
        graph=f"test_{uuid.uuid4().hex[:8]}",
    )
    try:
        client = FalkorClient(config)
    except Exception as e:
        pytest.skip(f"FalkorDB unreachable at {config.host}:{config.port}: {e}")
    try:
        yield client
    finally:
        try:
            client.run_query("MATCH (n) DETACH DELETE n")
        except Exception:
            pass
        try:
            client.close()
        except Exception:
            pass


def _register_perception(cl, session):
    from bongard.leaf import register_leaf
    from bongard.ontology import register_ontology
    from bongard.predicate import register_predicate
    from bongard.segments import register_segments
    register_ontology(cl, session)
    register_leaf(cl, session)
    register_segments(cl, session)
    register_predicate(cl, session)
    register_shapes(cl, session)


@pytest.mark.integration
def test_taught_square_survives_restart(falkor_client):
    from mindsos_capacity import CapacityLayer
    from mindsos_knowledge import KnowledgeLayer
    from mindsos_server.local_boot import boot_local
    from mindsos_server.persistence import FalkorDBLocalPersister
    from mindsos_server.session import Session

    user_id = "m2mint"
    persister = FalkorDBLocalPersister(falkor_client)

    # Teach + persist on the durable instance.
    kl1 = KnowledgeLayer.bootstrap()
    cl1 = CapacityLayer()
    session1 = Session.for_testing(user_id)
    _register_perception(cl1, session1)
    solver1 = Solver(user_id, cl=cl1, session=session1, register=False)
    minted_iri = mint_shape(solver1, kl1, persister, "square", _teach_squares())

    # Simulated restart: fresh KL/CL, re-register the atoms (code) + factory.
    kl2 = KnowledgeLayer.bootstrap()
    cl2 = CapacityLayer()
    session2 = Session.for_testing(user_id)
    _register_perception(cl2, session2)
    register_shape_reactivation(cl2)
    _, _, reactivated = boot_local(cl2, kl2, persister, user_id, session=session2)
    assert minted_iri in reactivated

    solver2 = Solver(user_id, cl=cl2, session=session2, register=False)
    try:
        assert _match(cl2, session2, minted_iri, solver2, _sq(22, 1.1, 80, 50)) is True
        assert _match(cl2, session2, minted_iri, solver2, _rect(64, 64, 50, 25)) is False
    finally:
        persister.delete(user_id)
