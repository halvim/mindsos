"""m5 tier-1 — INVENT an atomic relation (`same_shape`) from the geometric
atoms, name it, and round-trip it as a durable predicate (PLAN m5 atom-grain
block + the sizing result).

  * in-memory (no DB): invent `same_shape` from real parsed atoms; the moat
    abstains on a no-rule problem and on a confounded one (the decorrelated
    probe separates `same_shape` from `same_size`); the registered relation
    re-recognizes scenes.
  * integration (live FalkorDB): mint -> persist -> fresh KL/CL restart ->
    boot_local reactivates -> the reloaded relation still classifies.
"""

from __future__ import annotations

import uuid

import pytest

from bongard.control import Solver, build_solver
from bongard.invent import (
    RELATION_VERDICT,
    invent_relation,
    mint_relation,
    register_invented_relation,
    register_relation_reactivation,
)
from bongard.invent_problems import (
    AllSameProblem,
    ConfoundProblem,
    NoiseProblem,
    render_scene,
)
from bongard.ontology import SCENE
from bongard.scene import parse_scene
from bongard.shapes import register_shapes


@pytest.fixture(scope="module")
def solver():
    s = build_solver()
    register_shapes(s.cl, s.session)
    return s


def test_invents_same_shape_from_atoms(solver):
    r = invent_relation(solver, AllSameProblem(), n_train=3, n_holdout=8,
                        n_probe=10, seed=0)
    assert r.concluded, r.detail
    assert r.relation == ("n", "all")                 # discovered = vertex-count, all-pairs
    assert ("angle", "all") in r.members              # redundant encoding collapsed in


def test_moat_no_rule_abstains(solver):
    r = invent_relation(solver, NoiseProblem(), n_train=3, n_holdout=8,
                        n_probe=10, seed=0)
    assert r.status == "abstain"
    assert r.reason in ("no_consistent", "no_held_out_survivor")


def test_confound_abstains_ambiguous(solver):
    r = invent_relation(solver, ConfoundProblem(), n_train=3, n_holdout=8,
                        n_probe=12, seed=0)
    assert r.status == "abstain"
    assert r.reason == "ambiguous"                    # probe separates shape from size


def test_registered_relation_round_trip(solver):
    r = invent_relation(solver, AllSameProblem(), n_train=3, n_holdout=8,
                        n_probe=10, seed=0)
    iri = register_invented_relation(solver, r)
    assert iri == "capacity:predicate:same_shape"

    def verdict(types, rs):
        sc = parse_scene(solver, render_scene(types, rs))
        return solver.cl.invoke(iri, {SCENE.iri: sc},
                                session=solver.session).outputs[RELATION_VERDICT.iri]

    assert verdict([4, 4, 4], [22, 26, 30]) is True    # same shape, varied size (size-invariant)
    assert verdict([3, 4, 5], [22, 26, 30]) is False   # mixed


# ── integration: durable mint + restart (live FalkorDB, Linux gate) ────────

@pytest.fixture
def falkor_client():
    try:
        from mindsos_core.config import FalkorConfig
        from mindsos_core.persistence import FalkorClient
    except Exception as e:
        pytest.skip(f"FalkorClient import failed: {e}")
    base = FalkorConfig.from_env()
    config = FalkorConfig(host=base.host, port=base.port, password=base.password,
                          graph=f"test_{uuid.uuid4().hex[:8]}")
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
    from bongard.invent import register_relation_datastates
    from bongard.leaf import register_leaf
    from bongard.ontology import register_ontology
    from bongard.predicate import register_predicate
    from bongard.segments import register_segments
    register_ontology(cl, session)
    register_leaf(cl, session)
    register_segments(cl, session)
    register_predicate(cl, session)
    register_shapes(cl, session)
    register_relation_datastates(cl, session)


@pytest.mark.integration
def test_invented_relation_survives_restart(falkor_client):
    from mindsos_capacity import CapacityLayer
    from mindsos_knowledge import KnowledgeLayer
    from mindsos_server.local_boot import boot_local
    from mindsos_server.persistence import FalkorDBLocalPersister
    from mindsos_server.session import Session

    user_id = "m5invent"
    persister = FalkorDBLocalPersister(falkor_client)

    # Invent + mint + persist on the durable instance.
    kl1 = KnowledgeLayer.bootstrap()
    cl1 = CapacityLayer()
    session1 = Session.for_testing(user_id)
    _register_perception(cl1, session1)
    solver1 = Solver(user_id, cl=cl1, session=session1, register=False)
    result = invent_relation(solver1, AllSameProblem(), n_train=3, n_holdout=8,
                             n_probe=10, seed=0)
    assert result.concluded, result.detail
    minted_iri = mint_relation(solver1, kl1, persister, result)

    # Simulated restart: fresh KL/CL, re-register the atoms (code) + factory.
    kl2 = KnowledgeLayer.bootstrap()
    cl2 = CapacityLayer()
    session2 = Session.for_testing(user_id)
    _register_perception(cl2, session2)
    register_relation_reactivation(cl2)
    _, _, reactivated = boot_local(cl2, kl2, persister, user_id, session=session2)
    assert minted_iri in reactivated

    solver2 = Solver(user_id, cl=cl2, session=session2, register=False)
    try:
        same = parse_scene(solver2, render_scene([4, 4, 4], [22, 26, 30]))
        mixed = parse_scene(solver2, render_scene([3, 4, 5], [22, 26, 30]))
        assert cl2.invoke(minted_iri, {SCENE.iri: same},
                          session=session2).outputs[RELATION_VERDICT.iri] is True
        assert cl2.invoke(minted_iri, {SCENE.iri: mixed},
                          session=session2).outputs[RELATION_VERDICT.iri] is False
    finally:
        persister.delete(user_id)
