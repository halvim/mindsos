"""Phase 48 S7 — D'1 inline-on-retire read consumer (ADR-0177 §2; Chat B §4.4).

Unit-test-only at v1 (PB-9 — no live consumer; WSD reconstruction/retrieval
wire it). Exercises: a version-pinned read returns the node; after
``kl.retire_version`` the read reports the content as inlined (the
``_retired_inline_pending`` marker consulted).
"""

from mindsos_intelligence.retention import resolve_ref, resolve_refs
from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES, episode_iri


def _seed(kl, episode_id):
    local = kl.local_metagraph("alice")
    iri = episode_iri("v1", "alice", episode_id)
    g = next(g for g in local.graphs.values() if g.role == ROLE_EPISODIC_MEMORIES)
    g.add_node(value={"frozen": episode_id}, type_name="Episode", node_id=iri)
    return iri


def test_resolve_ref_returns_node_value_not_inlined():
    kl = KnowledgeLayer.bootstrap()
    iri = _seed(kl, "e1")
    r = resolve_ref(kl, iri, 1)
    assert r is not None
    assert r.value == {"frozen": "e1"}
    assert r.inlined is False


def test_resolve_ref_inlines_after_retire():
    kl = KnowledgeLayer.bootstrap()
    iri = _seed(kl, "e1")
    kl.retire_version(iri, 1)
    r = resolve_ref(kl, iri, 1)
    assert r is not None
    assert r.inlined is True  # marker consulted -> lazy inline (D'1)


def test_resolve_ref_unknown_returns_none():
    kl = KnowledgeLayer.bootstrap()
    assert resolve_ref(kl, episode_iri("v1", "alice", "ghost"), 1) is None


def test_resolve_refs_batch_mixes_inlined_and_live():
    kl = KnowledgeLayer.bootstrap()
    a = _seed(kl, "a")
    b = _seed(kl, "b")
    kl.retire_version(a, 1)
    out = resolve_refs(kl, [(a, 1), (b, 1)])
    by_iri = {r.iri: r.inlined for r in out}
    assert by_iri[a] is True
    assert by_iri[b] is False
