"""A role-graph's mutation discipline must survive a save -> load.

The loader does not restore graph schemas, so a role-graph that comes back
from FalkorDB carries no ``L2Schema``; ``KnowledgeLayer.discipline_for`` then
answers ``None`` and ``KLWriteHandle`` skips the discipline check. These tests
pin the invariant for a user's Local and for the Global: the discipline map
read after a reload equals the one read before the save.
"""

from __future__ import annotations

import pytest

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture

pytestmark = pytest.mark.integration


def _disciplines(kl, metagraph, roles):
    return {role: kl.discipline_for(metagraph, role) for role in sorted(roles)}


def test_local_disciplines_survive_reload(falkor_client) -> None:  # noqa: F811
    from mindsos_knowledge.bootstrap import _LOCAL_NAMED_ROLES
    from mindsos_knowledge.knowledge_layer import KnowledgeLayer
    from mindsos_server.persistence.local_persister import FalkorDBLocalPersister

    user = "alice"
    kl = KnowledgeLayer.bootstrap()
    before = _disciplines(kl, kl.local_metagraph(user), _LOCAL_NAMED_ROLES)
    assert all(d is not None for d in before.values()), before

    persister = FalkorDBLocalPersister(falkor_client)
    persister.save(user, kl.local_metagraph(user))
    loaded = persister.load(user)
    assert loaded is not None

    kl2 = KnowledgeLayer.bootstrap()
    kl2.install_local_metagraph(user, loaded)
    after = _disciplines(kl2, kl2.local_metagraph(user), _LOCAL_NAMED_ROLES)
    assert after == before


def test_global_disciplines_survive_reload(falkor_client) -> None:  # noqa: F811
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.reconstruction import MetagraphLoader
    from mindsos_knowledge.bootstrap import _GLOBAL_NAMED_ROLES
    from mindsos_knowledge.knowledge_layer import KnowledgeLayer

    kl = KnowledgeLayer.bootstrap()
    global_mg = kl.global_metagraph()
    before = _disciplines(kl, global_mg, _GLOBAL_NAMED_ROLES)
    assert all(d is not None for d in before.values()), before

    MetagraphRepository(falkor_client).persist(global_mg)
    loader = MetagraphLoader(falkor_client)
    metagraph_id = loader.find_by_name(global_mg.name)
    assert metagraph_id is not None
    loaded = loader.load(metagraph_id)

    kl2 = KnowledgeLayer(global_metagraph=loaded)
    after = _disciplines(kl2, kl2.global_metagraph(), _GLOBAL_NAMED_ROLES)
    assert after == before
