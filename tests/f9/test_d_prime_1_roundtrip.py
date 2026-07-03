"""F9 — D'1 retention survives persist+reload (§9 PB-B), live FalkorDB.

The Phase-48 D'1 tests exercise retire/read in-memory; this closes the F9
gap: the ``_retired_inline_pending`` marker (ADR-0177/0161 — a reserved
property written by ``kl.retire_version``) and version-pinned reads must
survive a ``FalkorDBLocalPersister`` save→load round-trip. ``_filter_user_props``
does not strip the marker (only id/graph_id/metagraph_id/type_name/_version/
_props_json/_value_json), so it should round-trip; this asserts it.

Integration; auto-skipped without a live sidecar.
"""

from __future__ import annotations

import pytest

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture

pytestmark = pytest.mark.integration


def _seed_episode(kl, user_id, episode_id):
    from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES, episode_iri

    local = kl.local_metagraph(user_id)
    iri = episode_iri("v1", user_id, episode_id)
    g = next(g for g in local.graphs.values() if g.role == ROLE_EPISODIC_MEMORIES)
    g.add_node(value={"frozen": episode_id}, type_name="Episode", node_id=iri)
    return local, iri


def test_d1_retire_marker_and_read_survive_persist_reload(falkor_client):
    from mindsos_intelligence.retention import resolve_ref
    from mindsos_knowledge import KnowledgeLayer
    from mindsos_server.persistence import FalkorDBLocalPersister

    user_id = "dave"
    persister = FalkorDBLocalPersister(falkor_client)

    kl1 = KnowledgeLayer.bootstrap()
    local, iri = _seed_episode(kl1, user_id, "e1")
    kl1.retire_version(iri, 1)  # sets _retired_inline_pending=True
    persister.save(user_id, local)

    try:
        loaded = persister.load(user_id)
        assert loaded is not None
        kl2 = KnowledgeLayer.bootstrap()
        kl2.install_local_metagraph(user_id, loaded)

        # version-pinned read resolves post-reload
        node = kl2.read_at_version(iri, 1)
        assert node is not None
        assert node.value == {"frozen": "e1"}
        # the D'1 retire marker survived the round-trip
        assert node.properties.get("_retired_inline_pending") is True
        # the ADR-0177 read consumer reports it inlined
        r = resolve_ref(kl2, iri, 1)
        assert r is not None and r.inlined is True
    finally:
        persister.delete(user_id)


def test_d1_live_node_not_inlined_after_reload(falkor_client):
    from mindsos_intelligence.retention import resolve_ref
    from mindsos_knowledge import KnowledgeLayer
    from mindsos_server.persistence import FalkorDBLocalPersister

    user_id = "erin"
    persister = FalkorDBLocalPersister(falkor_client)

    kl1 = KnowledgeLayer.bootstrap()
    local, iri = _seed_episode(kl1, user_id, "e2")  # NOT retired
    persister.save(user_id, local)

    try:
        loaded = persister.load(user_id)
        kl2 = KnowledgeLayer.bootstrap()
        kl2.install_local_metagraph(user_id, loaded)
        r = resolve_ref(kl2, iri, 1)
        assert r is not None and r.inlined is False
    finally:
        persister.delete(user_id)
