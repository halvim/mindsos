"""m5 tier-2 — COMPOSE a conjunction over the invented `same_shape` + the
taught `count_eq` operator (PLAN D-M5-13/15/16). Proves an invented relation
is CONSUMED by a higher tier (§14 vocabulary reuse) — shallow (bool AND bool)
but real: the basis carries the persisted invented IRI, not an authored
`all_same` template, so the conjunction cannot re-derive it.

  * in-memory (no DB):
    - DELTA: tier-2 CONCLUDEs `count_eq_3 ∧ same_shape` where m4
      single-template selection ABSTAINs (same generator) — and the concluded
      conjunction consumes `capacity:predicate:same_shape` (D-M5-13).
    - MINIMALITY: a generator where `same_shape` alone separates → tier-2
      concludes `same_shape` alone, dropping the redundant `count_eq_3`.
    - MOAT: a no-rule generator → abstain.
  * integration (live FalkorDB): mint same_shape + mint the conjunction
    (referencing it) → fresh KL/CL restart → boot_local reactivates BOTH
    (dep-ordered) → the reloaded conjunction still classifies.

HONESTY (PLAN D-M5-19): tier-2 is a vocabulary-REUSE mechanism proof, NOT the
§11 verdict. The non-trivial, non-pre-planted instance is the separate test.
"""

from __future__ import annotations

import uuid

import pytest

from bongard.compose import COMPOSITE_VERDICT, register_composite_reactivation
from bongard.control import Solver, build_solver
from bongard.count import count_eq_iri, register_count
from bongard.invent import (
    invent_relation,
    mint_relation,
    register_invented_relation,
    register_relation_reactivation,
)
from bongard.invent_problems import AllSameProblem, render_scene
from bongard.ontology import SCENE
from bongard.scene import parse_scene
from bongard.search import search_and_verify
from bongard.shapes import register_shapes
from bongard.tier2 import discover_conjunction
from bongard.tier2_problems import AllSameOnlyProblem, DeltaProblem, NoRuleProblem

SAME_SHAPE_IRI = "capacity:predicate:same_shape"
KS = (2, 3, 4)


@pytest.fixture(scope="module")
def t2():
    """A solver with same_shape INVENTED + registered, and the taught count
    operators registered. Returns (solver, operands)."""
    s = build_solver()
    register_shapes(s.cl, s.session)
    inv = invent_relation(s, AllSameProblem(), n_train=3, n_holdout=8,
                          n_probe=10, seed=0)
    assert inv.concluded, inv.detail
    rel_iri = register_invented_relation(s, inv)
    assert rel_iri == SAME_SHAPE_IRI
    register_count(s.cl, s.session, KS)
    operands = [rel_iri] + [count_eq_iri(k) for k in KS]
    return s, operands


def test_delta_concludes_conjunction(t2):
    solver, operands = t2
    r = discover_conjunction(solver, DeltaProblem(), operands,
                             name="count3_allsame", n_train=4, n_holdout=8)
    assert r.concluded, r.detail
    assert len(r.operands) == 2
    assert SAME_SHAPE_IRI in r.operands             # consumes the invented relation (D-M5-13)
    assert count_eq_iri(3) in r.operands


def test_delta_m4_abstains(t2):
    """Same generator: m4's single-template selection cannot separate it."""
    solver, _ = t2
    m = search_and_verify(solver, DeltaProblem(), n_train=4, n_holdout=8)
    assert m.status == "abstain", m.detail       # the delta vs tier-2's conclude


def test_minimality_drops_redundant_count(t2):
    solver, operands = t2
    r = discover_conjunction(solver, AllSameOnlyProblem(), operands,
                             name="min_test", n_train=4, n_holdout=8)
    assert r.concluded, r.detail
    assert r.operands == (SAME_SHAPE_IRI,)          # count_eq_3 dropped by minimality


def test_no_rule_abstains(t2):
    solver, operands = t2
    r = discover_conjunction(solver, NoRuleProblem(), operands, n_train=4, n_holdout=8)
    assert r.status == "abstain"
    assert r.reason in ("no_consistent", "no_held_out_survivor")


# ── integration: mint the conjunction + dep-ordered restart (FalkorDB) ──────

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
    from bongard.compose import register_composite_datastates
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
    register_composite_datastates(cl, session)
    register_count(cl, session, KS)


@pytest.mark.integration
def test_conjunction_survives_restart(falkor_client):
    from mindsos_capacity import CapacityLayer
    from mindsos_knowledge import KnowledgeLayer
    from mindsos_server.local_boot import boot_local
    from mindsos_server.persistence import FalkorDBLocalPersister
    from mindsos_server.session import Session

    user_id = "m5tier2"
    persister = FalkorDBLocalPersister(falkor_client)

    # Invent + mint same_shape (durable), then discover + mint the conjunction.
    kl1 = KnowledgeLayer.bootstrap()
    cl1 = CapacityLayer()
    session1 = Session.for_testing(user_id)
    _register_perception(cl1, session1)
    solver1 = Solver(user_id, cl=cl1, session=session1, register=False)
    inv = invent_relation(solver1, AllSameProblem(), n_train=3, n_holdout=8,
                          n_probe=10, seed=0)
    assert inv.concluded, inv.detail
    rel_iri = mint_relation(solver1, kl1, persister, inv)
    operands = [rel_iri] + [count_eq_iri(k) for k in KS]
    result = discover_conjunction(solver1, DeltaProblem(), operands,
                                  name="count3_allsame", n_train=4, n_holdout=8,
                                  mint=True, kl=kl1, persister=persister)
    assert result.concluded, result.detail
    assert rel_iri in result.operands
    comp_iri = "capacity:predicate:count3_allsame"

    # Simulated restart: fresh KL/CL, re-register atoms+count (code) + factories.
    kl2 = KnowledgeLayer.bootstrap()
    cl2 = CapacityLayer()
    session2 = Session.for_testing(user_id)
    _register_perception(cl2, session2)
    register_relation_reactivation(cl2)
    register_composite_reactivation(cl2)
    _, _, reactivated = boot_local(cl2, kl2, persister, user_id, session=session2)
    assert rel_iri in reactivated          # the invented relation operand
    assert comp_iri in reactivated         # the conjunction (reactivated AFTER it)

    solver2 = Solver(user_id, cl=cl2, session=session2, register=False)
    try:
        def verdict(types, rs):
            sc = parse_scene(solver2, render_scene(types, rs))
            return cl2.invoke(comp_iri, {SCENE.iri: sc},
                              session=session2).outputs[COMPOSITE_VERDICT.iri]
        assert verdict([4, 4, 4], [22, 26, 30]) is True     # 3 all-same
        assert verdict([3, 4, 3], [22, 26, 30]) is False    # 3 mixed  -> same_shape False
        assert verdict([4, 4], [22, 26]) is False           # 2 all-same -> count_eq_3 False
    finally:
        persister.delete(user_id)
