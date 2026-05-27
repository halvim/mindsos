"""Phase 34 — ``KLWriteHandle.mint_iri`` body + per-role dispatch."""

from __future__ import annotations

import pytest

from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.identifiers import (
    ROLE_MEMORIES,
    ROLE_PROBLEM_TRACE,
    _IRI_BUILDERS,
)

from tests.phase_34._fixtures import build_admin_session


def test_mint_iri_memories_role_produces_memory_iri():
    kl = KnowledgeLayer.bootstrap()
    sess = build_admin_session("alice")
    handle = kl.writeable(sess, role=ROLE_MEMORIES, scope="local")
    iri = handle.mint_iri(user_id="alice", memory_id="m1")
    assert iri == "memories-v1:memory:alice:m1"


def test_mint_iri_problem_trace_role_produces_entry_iri():
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(None, role=ROLE_PROBLEM_TRACE, scope="global")
    iri = handle.mint_iri(trace_id="t-abc")
    assert iri == "problem-trace-v1:entry:t-abc"


def test_mint_iri_uses_handle_bound_version_default_v1():
    """R2 PB-D: version literal bound at writeable() entry, default 'v1'."""
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(None, role=ROLE_PROBLEM_TRACE, scope="global")
    iri = handle.mint_iri(trace_id="t1")
    assert "-v1:" in iri


def test_mint_iri_custom_version_threads_through():
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(
        None, role=ROLE_PROBLEM_TRACE, scope="global", version="v2"
    )
    iri = handle.mint_iri(trace_id="t1")
    assert iri == "problem-trace-v2:entry:t1"


def test_mint_iri_missing_kwarg_raises_keyerror():
    """ADR-0146 §Decision: programmer error → propagate (R1 PB-I)."""
    kl = KnowledgeLayer.bootstrap()
    sess = build_admin_session("alice")
    handle = kl.writeable(sess, role=ROLE_MEMORIES, scope="local")
    with pytest.raises(KeyError):
        handle.mint_iri(user_id="alice")  # memory_id missing


def test_mint_iri_unsupported_role_raises_keyerror():
    """Roles not in the registry raise KeyError (per-flow build)."""
    from mindsos_knowledge import KLWriteHandle

    kl = KnowledgeLayer.bootstrap()
    handle = KLWriteHandle(
        role="ontology",  # not in _IRI_BUILDERS at Phase 34
        scope="global",
        session=None,
        _kl=kl,
        _metagraph=kl.global_metagraph(),
        _version="v1",
    )
    with pytest.raises(KeyError, match="no IRI builder registered"):
        handle.mint_iri(some_kwarg="x")


def test_iri_builders_registry_minimal_at_phase_34():
    """R1 PB-B: 2-entry registry (per-flow build discipline)."""
    assert set(_IRI_BUILDERS.keys()) == {ROLE_MEMORIES, ROLE_PROBLEM_TRACE}
