"""Phase 48 S6 — KL D'1 hooks: ``read_at_version`` + ``retire_version`` +
the ``_retired_inline_pending`` marker (ADR-0177 / ADR-0161 §amendment-1).

Opt C: the hooks keep the shipped ``CapacityContext.KLHandle.read_at_version``
``(iri, version)`` signature, backed by the current one-version-per-role store.
The lazy-inline read consumer (S7, ``retention.py``) lands in commit-group 4;
these tests exercise the KL contract directly.
"""

import pytest

from mindsos_core import RESERVED_PROPERTY_KEYS
from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES, episode_iri


def _seed_episode(kl: KnowledgeLayer, user_id: str, episode_id: str) -> str:
    """Add a frozen ``Episode`` node to the user's Local episodic_memories."""
    local = kl.local_metagraph(user_id)
    iri = episode_iri("v1", user_id, episode_id)
    g = next(g for g in local.graphs.values() if g.role == ROLE_EPISODIC_MEMORIES)
    g.add_node(value="frozen-mm", type_name="Episode", node_id=iri)
    return iri


def test_read_at_version_returns_node():
    kl = KnowledgeLayer.bootstrap()
    iri = _seed_episode(kl, "alice", "e1")
    node = kl.read_at_version(iri, 1)
    assert node is not None
    assert not node.properties.get("_retired_inline_pending", False)


def test_read_at_version_unknown_iri_returns_none():
    kl = KnowledgeLayer.bootstrap()
    assert kl.read_at_version(episode_iri("v1", "ghost", "none"), 1) is None


def test_retire_version_sets_lazy_inline_marker():
    kl = KnowledgeLayer.bootstrap()
    iri = _seed_episode(kl, "alice", "e1")
    kl.retire_version(iri, 1)
    node = kl.read_at_version(iri, 1)
    assert node.properties.get("_retired_inline_pending") is True


def test_retire_version_unknown_iri_raises():
    kl = KnowledgeLayer.bootstrap()
    with pytest.raises(KeyError):
        kl.retire_version(episode_iri("v1", "ghost", "none"), 1)


def test_marker_key_reserved_against_user_writes():
    assert "_retired_inline_pending" in RESERVED_PROPERTY_KEYS
    kl = KnowledgeLayer.bootstrap()
    local = kl.local_metagraph("bob")
    g = next(g for g in local.graphs.values() if g.role == ROLE_EPISODIC_MEMORIES)
    with pytest.raises(Exception):
        g.add_node(
            value="x",
            type_name="Episode",
            node_id=episode_iri("v1", "bob", "e2"),
            properties={"_retired_inline_pending": True},
        )
