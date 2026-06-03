"""Phase 34 — ``KLWriteHandle.write_and_validate`` composite (PHASE_MAP §34)."""

from __future__ import annotations

from datetime import datetime, timezone

from mindsos_capacity import WriteResult
from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES, ROLE_PROBLEM_TRACE

from tests.phase_34._fixtures import build_admin_session


def test_write_and_validate_returns_write_result_on_success():
    kl = KnowledgeLayer.bootstrap()
    sess = build_admin_session("alice")
    handle = kl.writeable(sess, role=ROLE_EPISODIC_MEMORIES, scope="local")
    out = handle.write_and_validate(
        value="hello",
        type_="Memory",
        user_id="alice",
        memory_id="m1",
    )
    assert isinstance(out, WriteResult)
    assert out.iri == "episodic-memories-v1:memory:alice:m1"
    assert out.role == ROLE_EPISODIC_MEMORIES
    assert out.scope == "local"
    assert isinstance(out.written_at, datetime)
    # ISO-format timezone-aware (UTC).
    assert out.written_at.tzinfo is not None


def test_write_and_validate_persists_node_to_l1_graph():
    """KL state actually mutates (handle shares ref with KL._locals)."""
    kl = KnowledgeLayer.bootstrap()
    sess = build_admin_session("alice")
    handle = kl.writeable(sess, role=ROLE_EPISODIC_MEMORIES, scope="local")
    handle.write_and_validate(
        value="persisted",
        type_="Memory",
        user_id="alice",
        memory_id="m1",
    )
    # Read back via the same metagraph the handle wrote into.
    g = handle.graph()
    assert "episodic-memories-v1:memory:alice:m1" in g.nodes
    node = g.nodes["episodic-memories-v1:memory:alice:m1"]
    assert node.value == "persisted"
    assert node.type_name == "Memory"


def test_write_and_validate_problem_trace_global_scope():
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(None, role=ROLE_PROBLEM_TRACE, scope="global")
    out = handle.write_and_validate(
        value={"error_kind": "exception", "message": "boom"},
        type_="ProblemTraceEntry",
        trace_id="t1",
    )
    assert isinstance(out, WriteResult)
    assert out.iri == "problem-trace-v1:entry:t1"
    assert out.role == ROLE_PROBLEM_TRACE
    assert out.scope == "global"


def test_write_and_validate_uses_utc_timestamp():
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(None, role=ROLE_PROBLEM_TRACE, scope="global")
    before = datetime.now(timezone.utc)
    out = handle.write_and_validate(
        value="t",
        type_="ProblemTraceEntry",
        trace_id="t1",
    )
    after = datetime.now(timezone.utc)
    assert before <= out.written_at <= after


def test_write_and_validate_extras_empty_dict():
    """Phase 34 doesn't populate extras; reserved for retry_count etc."""
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(None, role=ROLE_PROBLEM_TRACE, scope="global")
    out = handle.write_and_validate(
        value="t",
        type_="ProblemTraceEntry",
        trace_id="t1",
    )
    assert out.extras == {}
