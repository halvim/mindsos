"""Phase 33 — ``KnowledgeLayer.writeable`` entry point + KLWriteHandle stub."""

from __future__ import annotations

import pytest

from mindsos_capacity import WriteHandleNotWiredError
from mindsos_knowledge import KLWriteHandle, KnowledgeLayer
from mindsos_knowledge.identifiers import ROLE_MEMORIES, ROLE_PROBLEM_TRACE
from tests.phase_33._fixtures import build_session_with_caps


def _kl():
    return KnowledgeLayer.bootstrap()


# ── writeable() entry-point behavior ──────────────────────────────────


def test_writeable_global_session_none_returns_handle():
    """ADR-0080 bootstrap carve-out: session=None permitted for Global."""
    h = _kl().writeable(None, ROLE_PROBLEM_TRACE, "global")
    assert isinstance(h, KLWriteHandle)
    assert h.role == ROLE_PROBLEM_TRACE
    assert h.scope == "global"
    assert h.session is None


def test_writeable_local_with_session_returns_handle():
    sess = build_session_with_caps("alice", frozenset({"CAN_WRITE_GLOBAL"}))
    h = _kl().writeable(sess, ROLE_MEMORIES, "local")
    assert isinstance(h, KLWriteHandle)
    assert h.role == ROLE_MEMORIES
    assert h.scope == "local"
    assert h.session is sess


def test_writeable_local_session_none_raises_value_error():
    with pytest.raises(ValueError, match="requires a session"):
        _kl().writeable(None, ROLE_MEMORIES, "local")


def test_writeable_bad_scope_raises_value_error():
    with pytest.raises(ValueError, match="scope must be"):
        _kl().writeable(None, ROLE_MEMORIES, "cloud")


# ── KLWriteHandle method stub behavior ────────────────────────────────


def test_handle_metagraph_returns_real_metagraph_global():
    """metagraph() works (read-only state inspection; PB-D Pick)."""
    from mindsos_core import Metagraph

    h = _kl().writeable(None, ROLE_PROBLEM_TRACE, "global")
    mg = h.metagraph()
    assert isinstance(mg, Metagraph)
    # Global has problem-trace role-graph.
    assert ROLE_PROBLEM_TRACE in {g.role for g in mg.graphs.values()}


def test_handle_metagraph_returns_real_metagraph_local():
    from mindsos_core import Metagraph

    sess = build_session_with_caps("bob", frozenset())
    h = _kl().writeable(sess, ROLE_MEMORIES, "local")
    mg = h.metagraph()
    assert isinstance(mg, Metagraph)
    assert ROLE_MEMORIES in {g.role for g in mg.graphs.values()}


def test_handle_graph_raises_writehandle_not_wired():
    h = _kl().writeable(None, ROLE_PROBLEM_TRACE, "global")
    with pytest.raises(WriteHandleNotWiredError, match="not wired at Phase 33"):
        h.graph()


def test_handle_mint_iri_raises_writehandle_not_wired():
    h = _kl().writeable(None, ROLE_PROBLEM_TRACE, "global")
    with pytest.raises(WriteHandleNotWiredError, match="not wired at Phase 33"):
        h.mint_iri(trace_id="t1")


def test_handle_validate_node_raises_writehandle_not_wired():
    h = _kl().writeable(None, ROLE_PROBLEM_TRACE, "global")
    with pytest.raises(WriteHandleNotWiredError, match="not wired"):
        h.validate_node(value="x", type_="Memory")


def test_handle_validate_xref_raises_writehandle_not_wired():
    h = _kl().writeable(None, ROLE_PROBLEM_TRACE, "global")
    with pytest.raises(WriteHandleNotWiredError, match="not wired"):
        h.validate_xref(
            target_metagraph=h.metagraph(),
            target_role=ROLE_PROBLEM_TRACE,
            target_id="x",
            ref_type="DERIVED_FROM",
        )


def test_handle_is_frozen_dataclass():
    """ADR-0143 §Constraint: never mutates; frozen prevents mutation accretion."""
    h = _kl().writeable(None, ROLE_PROBLEM_TRACE, "global")
    with pytest.raises(Exception):
        h.role = "other"  # type: ignore[misc]
