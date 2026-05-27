"""Phase 34 — ``KLWriteHandle.graph()`` body wiring (ADR-0146 §Impl)."""

from __future__ import annotations

import pytest

from mindsos_core import Graph
from mindsos_knowledge import KLWriteHandle, KnowledgeLayer
from mindsos_knowledge.identifiers import ROLE_MEMORIES, ROLE_PROBLEM_TRACE

from tests.phase_34._fixtures import build_admin_session


def test_graph_returns_real_l1_graph_for_problem_trace_role():
    """Phase 34 wired: graph() now returns the Graph (was raising at Phase 33)."""
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(None, role=ROLE_PROBLEM_TRACE, scope="global")
    g = handle.graph()
    assert isinstance(g, Graph)
    assert g.role == ROLE_PROBLEM_TRACE


def test_graph_returns_real_l1_graph_for_memories_role():
    kl = KnowledgeLayer.bootstrap()
    sess = build_admin_session("alice")
    handle = kl.writeable(sess, role=ROLE_MEMORIES, scope="local")
    g = handle.graph()
    assert isinstance(g, Graph)
    assert g.role == ROLE_MEMORIES


def test_graph_raises_keyerror_when_role_absent_from_metagraph():
    """Programmer error per ADR-0146 §Decision (propagate not envelope)."""
    kl = KnowledgeLayer.bootstrap()
    # Hand-construct a handle pointing at the Global metagraph but with
    # a bogus role — bypasses writeable()'s no-role-check pattern.
    handle = KLWriteHandle(
        role="nonexistent-role",
        scope="global",
        session=None,
        _kl=kl,
        _metagraph=kl.global_metagraph(),
        _version="v1",
    )
    with pytest.raises(KeyError, match="no graph with that role"):
        handle.graph()


def test_metagraph_returns_real_metagraph_unchanged_from_phase_33():
    """Metagraph accessor unchanged at Phase 34."""
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(None, role=ROLE_PROBLEM_TRACE, scope="global")
    mg = handle.metagraph()
    assert mg is kl.global_metagraph()
