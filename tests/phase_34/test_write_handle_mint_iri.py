"""Phase 34 — ``KLWriteHandle.mint_iri`` body + per-(role, NodeType) dispatch.

Phase 39 update: signature is ``mint_iri(type_, **content)`` per
ADR-0146 §amendment-3; registry keyed by ``(role, NodeType_name)``
tuple. Tests at this file cover the original Phase 34 behavior
under the new dispatch shape.
"""

from __future__ import annotations

import pytest

from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.identifiers import (
    ROLE_EPISODIC_MEMORIES,
    ROLE_PROBLEM_TRACE,
    _IRI_BUILDERS,
)

from tests.phase_34._fixtures import build_admin_session


def test_mint_iri_episodic_memories_episode_produces_episode_iri():
    kl = KnowledgeLayer.bootstrap()
    sess = build_admin_session("alice")
    handle = kl.writeable(sess, role=ROLE_EPISODIC_MEMORIES, scope="local")
    iri = handle.mint_iri("Episode", user_id="alice", episode_id="e1")
    assert iri == "episodic-memories-v1:episode:alice:e1"


def test_mint_iri_episodic_memories_memory_type_produces_composite_iri():
    kl = KnowledgeLayer.bootstrap()
    sess = build_admin_session("alice")
    handle = kl.writeable(sess, role=ROLE_EPISODIC_MEMORIES, scope="local")
    iri = handle.mint_iri("Memory", user_id="alice", memory_id="m1")
    assert iri == "episodic-memories-v1:memory:alice:m1"


def test_mint_iri_problem_trace_role_produces_entry_iri():
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(None, role=ROLE_PROBLEM_TRACE, scope="global")
    iri = handle.mint_iri("ProblemTraceEntry", trace_id="t-abc")
    assert iri == "problem-trace-v1:entry:t-abc"


def test_mint_iri_uses_handle_bound_version_default_v1():
    """R2 PB-D: version literal bound at writeable() entry, default 'v1'."""
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(None, role=ROLE_PROBLEM_TRACE, scope="global")
    iri = handle.mint_iri("ProblemTraceEntry", trace_id="t1")
    assert "-v1:" in iri


def test_mint_iri_custom_version_threads_through():
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(
        None, role=ROLE_PROBLEM_TRACE, scope="global", version="v2"
    )
    iri = handle.mint_iri("ProblemTraceEntry", trace_id="t1")
    assert iri == "problem-trace-v2:entry:t1"


def test_mint_iri_missing_kwarg_raises_keyerror():
    """ADR-0146 §Decision: programmer error → propagate (R1 PB-I)."""
    kl = KnowledgeLayer.bootstrap()
    sess = build_admin_session("alice")
    handle = kl.writeable(sess, role=ROLE_EPISODIC_MEMORIES, scope="local")
    with pytest.raises(KeyError):
        handle.mint_iri("Memory", user_id="alice")  # memory_id missing


def test_mint_iri_unsupported_role_type_pair_raises_keyerror():
    """Roles + NodeType pairs not in the tuple-key registry raise KeyError
    (per-flow build + ADR-0146 §amendment-3 dispatch shape)."""
    from mindsos_knowledge import KLWriteHandle

    kl = KnowledgeLayer.bootstrap()
    handle = KLWriteHandle(
        role="ontology",  # not in _IRI_BUILDERS at Phase 39
        scope="global",
        session=None,
        _kl=kl,
        _metagraph=kl.global_metagraph(),
        _version="v1",
    )
    with pytest.raises(KeyError, match="no IRI builder registered"):
        handle.mint_iri("Concept", some_kwarg="x")


def test_mint_iri_dispatches_for_every_registered_pair():
    """Every ``(role, NodeType)`` in the registry has a callable minter.

    ⚠ This used to be a second hand-copied list of the registry's contents,
    which is what the phase_39 shape suite is for. Two copies of one closed
    set means adding an entry fails twice and can be fixed in one place and
    not the other. The claim that belongs HERE is about ``mint_iri``: every
    registered pair dispatches.
    """
    assert _IRI_BUILDERS, "the registry is empty - nothing to dispatch"
    for (role, type_name), minter in _IRI_BUILDERS.items():
        assert callable(minter), (role, type_name)
