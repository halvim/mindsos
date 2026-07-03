"""F9 — reset_run_state semantics (ADR-0187), live FalkorDB.

reset wipes run-state (episodic_memories) while retaining durable
learning (learned-parameters). Integration; auto-skipped without a live
sidecar.
"""

from __future__ import annotations

import pytest

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture

pytestmark = pytest.mark.integration


def _role_graph(mg, role):
    for g in mg.graphs.values():
        if getattr(g, "role", None) == role:
            return g
    return None


def test_reset_wipes_run_state_retains_learned_parameters(falkor_client):
    from mindsos_knowledge import (
        KnowledgeLayer,
        ROLE_EPISODIC_MEMORIES,
        ROLE_LEARNED_PARAMETERS,
        ensure_local_role_graph,
        learned_parameter_iri,
    )
    from mindsos_knowledge.schemas.episodic_memories import NODE_EPISODE
    from mindsos_knowledge.schemas.learned_parameters import NODE_LEARNED_PARAMETER
    from mindsos_server.persistence import FalkorDBLocalPersister

    from ._fixtures import taught_descriptor

    user_id = "carol"
    persister = FalkorDBLocalPersister(falkor_client)
    kl = KnowledgeLayer.bootstrap()
    local_mg = kl.local_metagraph(user_id)

    # Durable: a learned-parameters descriptor.
    lp = ensure_local_role_graph(local_mg, ROLE_LEARNED_PARAMETERS)
    desc = taught_descriptor()
    lp.add_node(
        dict(desc),
        NODE_LEARNED_PARAMETER,
        properties={"parameter_set_iri": "taught:text.demo", "confidence": 1.0},
        node_id=learned_parameter_iri("v1", desc["capability"]),
    )
    # Run-state: an episodic_memories entry.
    em = ensure_local_role_graph(local_mg, ROLE_EPISODIC_MEMORIES)
    em.add_node({"task": "t1"}, NODE_EPISODE, node_id="episode:carol:t1")

    persister.save(user_id, local_mg)

    try:
        assert persister.reset_run_state(user_id) is True

        reloaded = persister.load(user_id)
        assert reloaded is not None
        # episodic_memories graph present but empty; learned-parameters retained.
        em2 = _role_graph(reloaded, ROLE_EPISODIC_MEMORIES)
        lp2 = _role_graph(reloaded, ROLE_LEARNED_PARAMETERS)
        assert em2 is not None and len(em2.nodes) == 0
        assert lp2 is not None and len(lp2.nodes) == 1
    finally:
        persister.delete(user_id)


def test_reset_missing_local_returns_false(falkor_client):
    from mindsos_server.persistence import FalkorDBLocalPersister

    persister = FalkorDBLocalPersister(falkor_client)
    assert persister.reset_run_state("ghost") is False
