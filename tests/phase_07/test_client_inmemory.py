"""Unit tests for :class:`InMemoryClient` (Phase 07)."""

from __future__ import annotations

from mindsos_core.persistence import InMemoryClient, QueryResult, Client


def test_inmemory_implements_client_protocol() -> None:
    """InMemoryClient satisfies the runtime-checkable Client Protocol."""
    c = InMemoryClient()
    assert isinstance(c, Client)


def test_inmemory_records_calls() -> None:
    """run_query records (query, params) tuples in order."""
    c = InMemoryClient()
    c.run_query("FOO", {"a": 1})
    c.run_query("BAR")
    assert c.calls == [("FOO", {"a": 1}), ("BAR", {})]


def test_inmemory_scripted_results_pop_in_order() -> None:
    """Scripted results return on subsequent run_query calls; default empty."""
    c = InMemoryClient()
    c.script([{"x": 1}])
    c.script([{"y": 2}])
    r1 = c.run_query("Q1")
    r2 = c.run_query("Q2")
    r3 = c.run_query("Q3")
    assert r1.rows == [{"x": 1}]
    assert r2.rows == [{"y": 2}]
    assert r3.rows == []


def test_inmemory_run_batch_sequential() -> None:
    """run_batch invokes run_query per statement, preserving order."""
    c = InMemoryClient()
    results = c.run_batch([("A", {}), ("B", {})])
    assert len(results) == 2
    assert c.calls == [("A", {}), ("B", {})]


def test_inmemory_close_is_idempotent() -> None:
    """close() flips .closed and is safe to call twice."""
    c = InMemoryClient()
    assert c.closed is False
    c.close()
    assert c.closed is True
    c.close()
    assert c.closed is True
