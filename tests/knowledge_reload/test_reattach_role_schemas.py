"""``reattach_role_schemas`` without a store: strip the schemas, put them back.

The live round-trip is ``test_discipline_survives_reload.py``; this file pins
the same invariant with no FalkorDB, so it runs in every gate.
"""

from __future__ import annotations

import pytest

from mindsos_knowledge.bootstrap import (
    _GLOBAL_NAMED_ROLES,
    _LOCAL_NAMED_ROLES,
    reattach_role_schemas,
)
from mindsos_knowledge.knowledge_layer import KnowledgeLayer


def _disciplines(kl, metagraph, roles):
    kl._discipline_cache.clear()
    return {role: kl.discipline_for(metagraph, role) for role in sorted(roles)}


def _strip(metagraph) -> None:
    for graph in metagraph.graphs.values():
        graph.schema = None


@pytest.mark.parametrize("scope", ["local", "global"])
def test_reattach_restores_every_discipline(scope) -> None:
    kl = KnowledgeLayer.bootstrap()
    if scope == "local":
        metagraph, roles = kl.local_metagraph("alice"), _LOCAL_NAMED_ROLES
    else:
        metagraph, roles = kl.global_metagraph(), _GLOBAL_NAMED_ROLES
    before = _disciplines(kl, metagraph, roles)
    assert all(d is not None for d in before.values()), before

    _strip(metagraph)
    assert set(_disciplines(kl, metagraph, roles).values()) == {None}

    attached = reattach_role_schemas(metagraph, scope)
    assert attached == sorted(roles)
    assert _disciplines(kl, metagraph, roles) == before


def test_reattach_leaves_an_attached_schema_alone() -> None:
    kl = KnowledgeLayer.bootstrap()
    metagraph = kl.global_metagraph()
    schemas = {g.role: g.schema for g in metagraph.graphs.values()}
    assert reattach_role_schemas(metagraph, "global") == []
    assert all(g.schema is schemas[g.role] for g in metagraph.graphs.values())


def test_install_reattaches_a_stripped_local() -> None:
    kl = KnowledgeLayer.bootstrap()
    before = _disciplines(kl, kl.local_metagraph("alice"), _LOCAL_NAMED_ROLES)
    stripped = kl.extract_local_metagraph("alice")
    _strip(stripped)

    kl2 = KnowledgeLayer.bootstrap()
    kl2.install_local_metagraph("alice", stripped)
    assert _disciplines(kl2, kl2.local_metagraph("alice"), _LOCAL_NAMED_ROLES) == before


def test_constructor_reattaches_a_stripped_global() -> None:
    kl = KnowledgeLayer.bootstrap()
    global_mg = kl.global_metagraph()
    before = _disciplines(kl, global_mg, _GLOBAL_NAMED_ROLES)
    _strip(global_mg)

    kl2 = KnowledgeLayer(global_metagraph=global_mg)
    assert _disciplines(kl2, kl2.global_metagraph(), _GLOBAL_NAMED_ROLES) == before


def test_reattach_rejects_an_unknown_scope() -> None:
    kl = KnowledgeLayer.bootstrap()
    with pytest.raises(ValueError):
        reattach_role_schemas(kl.global_metagraph(), "both")
