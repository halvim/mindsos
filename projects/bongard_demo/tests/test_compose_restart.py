"""m5 tier-2 DE-RISK — a REFERENCING composite over the minted ``same_shape``
relation survives a fresh-process restart via dep-ordered reactivation
(PLAN D-M5-16). Isolates the one risk tier-1 never exercised: a composite
whose COMPOSITE_DAG names another minted node's IRI must reactivate AFTER that
node at ``boot_local``.

  * in-memory (no DB): invent ``same_shape`` -> register a composite that
    REFERENCES it -> the composite re-recognizes scenes by invoking the
    referenced node; ``composite_dependencies`` exposes the reference (the
    *data* half of dep-ordered boot).
  * integration (live FalkorDB): mint ``same_shape`` + mint the referencing
    composite -> fresh KL/CL restart -> ``boot_local`` reactivates BOTH (the
    operand first, then the composite) -> the reloaded composite still
    classifies through the reactivated operand.
"""

from __future__ import annotations

import uuid

import pytest

from mindsos_capacity import composite_dependencies

from bongard.compose import (
    COMPOSITE_VERDICT,
    composite_descriptor,
    mint_composite,
    register_composite,
    register_composite_reactivation,
)
from bongard.control import Solver, build_solver
from bongard.invent import (
    invent_relation,
    mint_relation,
    register_invented_relation,
    register_relation_reactivation,
)
from bongard.invent_problems import AllSameProblem, render_scene
from bongard.ontology import SCENE
from bongard.scene import parse_scene
from bongard.shapes import register_shapes

WRAP = "same_shape_wrapped"
WRAP_IRI = f"capacity:predicate:{WRAP}"


@pytest.fixture(scope="module")
def solver():
    s = build_solver()
    register_shapes(s.cl, s.session)
    return s


def test_composite_references_minted_relation(solver):
    r = invent_relation(solver, AllSameProblem(), n_train=3, n_holdout=8,
                        n_probe=10, seed=0)
    assert r.concluded, r.detail
    rel_iri = register_invented_relation(solver, r)
    assert rel_iri == "capacity:predicate:same_shape"

    # the composite's serialized DAG must expose the reference (data half of
    # dep-ordered boot) — this is what _dep_order_descriptors topo-sorts on.
    desc = composite_descriptor(WRAP, [rel_iri])
    assert composite_dependencies(desc) == {rel_iri}

    comp_iri = register_composite(solver, WRAP, [rel_iri])
    assert comp_iri == WRAP_IRI

    def verdict(types, rs):
        sc = parse_scene(solver, render_scene(types, rs))
        return solver.cl.invoke(comp_iri, {SCENE.iri: sc},
                                session=solver.session).outputs[COMPOSITE_VERDICT.iri]

    # the composite produces its verdict by INVOKING the referenced node.
    assert verdict([4, 4, 4], [22, 26, 30]) is True     # all-same -> same_shape True
    assert verdict([3, 4, 5], [22, 26, 30]) is False    # mixed   -> same_shape False


# ── integration: durable mint + dep-ordered restart (live FalkorDB, Linux) ──

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
    """Fresh-process boot: register the atom code + BOTH minted-node output
    DataStates + BOTH reactivation factories, before ``boot_local`` runs."""
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


@pytest.mark.integration
def test_composite_survives_restart(falkor_client):
    from mindsos_capacity import CapacityLayer
    from mindsos_knowledge import KnowledgeLayer
    from mindsos_server.local_boot import boot_local
    from mindsos_server.persistence import FalkorDBLocalPersister
    from mindsos_server.session import Session

    user_id = "m5compose"
    persister = FalkorDBLocalPersister(falkor_client)

    # Invent + mint the relation, then mint a composite that REFERENCES it.
    kl1 = KnowledgeLayer.bootstrap()
    cl1 = CapacityLayer()
    session1 = Session.for_testing(user_id)
    _register_perception(cl1, session1)
    solver1 = Solver(user_id, cl=cl1, session=session1, register=False)
    result = invent_relation(solver1, AllSameProblem(), n_train=3, n_holdout=8,
                             n_probe=10, seed=0)
    assert result.concluded, result.detail
    rel_iri = mint_relation(solver1, kl1, persister, result)
    comp_iri = mint_composite(solver1, kl1, persister, WRAP, [rel_iri])

    # Simulated restart: fresh KL/CL, re-register atoms (code) + BOTH factories.
    kl2 = KnowledgeLayer.bootstrap()
    cl2 = CapacityLayer()
    session2 = Session.for_testing(user_id)
    _register_perception(cl2, session2)
    register_relation_reactivation(cl2)
    register_composite_reactivation(cl2)
    _, _, reactivated = boot_local(cl2, kl2, persister, user_id, session=session2)
    # dep-ordered boot must reactivate the referenced operand AND the composite.
    assert rel_iri in reactivated
    assert comp_iri in reactivated

    solver2 = Solver(user_id, cl=cl2, session=session2, register=False)
    try:
        same = parse_scene(solver2, render_scene([4, 4, 4], [22, 26, 30]))
        mixed = parse_scene(solver2, render_scene([3, 4, 5], [22, 26, 30]))
        # the reloaded composite classifies by invoking the reloaded operand.
        assert cl2.invoke(comp_iri, {SCENE.iri: same},
                          session=session2).outputs[COMPOSITE_VERDICT.iri] is True
        assert cl2.invoke(comp_iri, {SCENE.iri: mixed},
                          session=session2).outputs[COMPOSITE_VERDICT.iri] is False
    finally:
        persister.delete(user_id)
