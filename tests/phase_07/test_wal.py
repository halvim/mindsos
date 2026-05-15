"""WAL tests (Phase 07 — P50 B + P82 A; refactored Phase 09 P51 + P62).

Phase 09 cascade:

* **P51 + P61 + P66 B** — replayer registration is per-Client; the
  module-level helpers ``register_replayer`` / ``clear_replayers`` /
  ``recover`` all take ``client`` as their first positional arg.
  ``setup_function`` / ``teardown_function`` no longer needed —
  each test creates its own throwaway :class:`InMemoryClient` so
  there is no cross-test pollution.
* **P62** — ``recover()`` raises :class:`WALReplayerMissingError`
  when an uncommitted WAL entry has no registered replayer; the
  Phase 08 silent narrow-catch was removed. The replacement test
  ``test_recover_raises_on_unknown_kind`` verifies the loud-fail
  contract.
"""

from __future__ import annotations

import pytest

from mindsos_core.exceptions import (
    PersistenceError,
    WALReplayerMissingError,
)
from mindsos_core.persistence import InMemoryClient
from mindsos_core.persistence.wal import (
    WriteAheadLog,
    WALEntry,
    clear_replayers,
    recover,
    register_replayer,
)


def test_begin_emits_match_metagraph_plus_merge_walentry() -> None:
    c = InMemoryClient()
    c.script([{"op_id": "op1"}])
    wal = WriteAheadLog(c, "mg1")
    op_id = wal.begin(operation_id="op1", kind="test.kind", payload={"x": 1})
    assert op_id == "op1"
    assert "WALEntry" in c.calls[0][0]


def test_commit_stamps_committed_true() -> None:
    c = InMemoryClient()
    c.script([{"op_id": "op1"}])  # begin
    c.script([{"op_id": "op1"}])  # commit
    wal = WriteAheadLog(c, "mg1")
    wal.begin(operation_id="op1", kind="k", payload={})
    wal.commit("op1")
    assert "committed = true" in c.calls[1][0]


def test_commit_raises_when_no_row() -> None:
    c = InMemoryClient()
    c.script([])  # commit returns empty rows
    wal = WriteAheadLog(c, "mg1")
    with pytest.raises(PersistenceError, match="not found"):
        wal.commit("missing")


def test_list_uncommitted_parses_payload_json() -> None:
    c = InMemoryClient()
    c.script([
        {
            "op_id": "op1",
            "kind": "test.kind",
            "payload_json": '{"x":1}',
            "started_at": "2026-05-13T00:00:00",
        }
    ])
    wal = WriteAheadLog(c, "mg1")
    rows = wal.list_uncommitted()
    assert len(rows) == 1
    assert rows[0].payload == {"x": 1}
    assert rows[0].kind == "test.kind"


def test_count_uncommitted_returns_int() -> None:
    c = InMemoryClient()
    c.script([{"n": 3}])
    wal = WriteAheadLog(c, "mg1")
    assert wal.count_uncommitted() == 3


def test_context_manager_commits_on_success() -> None:
    """P50 B — happy path stamps committed=true."""
    c = InMemoryClient()
    c.script([{"op_id": "op1"}])  # begin
    c.script([{"op_id": "op1"}])  # commit
    wal = WriteAheadLog(c, "mg1")
    with wal.entry(operation_id="op1", kind="k", payload={"x": 1}) as op_id:
        assert op_id == "op1"
    # Two queries emitted: begin + commit.
    commit_calls = [q for q, _ in c.calls if "committed = true" in q]
    assert len(commit_calls) == 1


def test_context_manager_leaves_uncommitted_on_exception() -> None:
    """P50 B — exception path skips commit; entry stays committed=false for recover."""
    c = InMemoryClient()
    c.script([{"op_id": "op2"}])  # begin
    wal = WriteAheadLog(c, "mg1")
    with pytest.raises(RuntimeError, match="boom"):
        with wal.entry(operation_id="op2", kind="k", payload={}):
            raise RuntimeError("boom")
    commit_calls = [q for q, _ in c.calls if "committed = true" in q]
    assert len(commit_calls) == 0


def test_whole_batch_refused_via_raises_on_nth_call() -> None:
    """P82 A renamed test. Wrapper at Client surface refuses entire batch from call N.

    Earlier calls forward to the real client; once triggered, the
    wrapper stays in error state.
    """
    from tests._shared.raises_on_nth_call import RaisesOnNthCall

    real = InMemoryClient()
    real.script([{"ok": 1}])  # first run_query forwards.
    wrap = RaisesOnNthCall(real, n=2)

    # Call 1 forwards through.
    wrap.run_query("Q1")
    assert wrap.count == 1
    # Call 2 raises whole-batch refusal.
    with pytest.raises(PersistenceError, match="RaisesOnNthCall: triggered"):
        wrap.run_query("Q2")
    assert wrap.count == 2


def test_recover_dispatches_replayer_and_commits() -> None:
    """Phase 09 P51 — register_replayer + recover both take client positional."""
    c = InMemoryClient()
    # list_uncommitted scripted result.
    c.script([
        {
            "op_id": "op3",
            "kind": "test.kind",
            "payload_json": '{"k":"v"}',
            "started_at": "2026-05-13T00:00:00",
        }
    ])
    # commit scripted result.
    c.script([{"op_id": "op3"}])

    seen: list = []
    register_replayer(c, "test.kind", lambda payload: seen.append(payload))
    n = recover(c, "mg1")
    assert n == 1
    assert seen == [{"k": "v"}]


def test_recover_raises_on_unknown_kind() -> None:
    """Phase 09 P62 — unknown kind raises WALReplayerMissingError loudly.

    The Phase 08 silent narrow-catch was removed (P62). Phase 09's
    ``register_all_l1_replayers`` registers ``xref_add`` /
    ``xref_remove`` on FalkorClient construction; an unknown kind in
    the WAL post-Phase-09 is a real bug, not a tolerable no-op.
    """
    c = InMemoryClient()
    c.script([
        {"op_id": "op4", "kind": "unknown.kind", "payload_json": "{}",
         "started_at": "2026-05-13T00:00:00"}
    ])
    with pytest.raises(WALReplayerMissingError, match="unknown.kind"):
        recover(c, "mg1")


def test_recover_skips_failing_replayers() -> None:
    """A replayer that raises leaves the entry uncommitted for the next retry."""
    c = InMemoryClient()
    c.script([
        {"op_id": "op5", "kind": "boom.kind", "payload_json": "{}",
         "started_at": "2026-05-13T00:00:00"}
    ])

    def _boom(payload):
        raise RuntimeError("replayer failed")

    register_replayer(c, "boom.kind", _boom)
    n = recover(c, "mg1")
    assert n == 0


def test_register_replayer_overwrites_previous() -> None:
    """Phase 09 P51 — same kind on same client overwrites; per-Client dict."""
    c = InMemoryClient()
    seen: list = []
    register_replayer(c, "k1", lambda p: seen.append("v1"))
    register_replayer(c, "k1", lambda p: seen.append("v2"))

    c.script([
        {"op_id": "op6", "kind": "k1", "payload_json": "{}",
         "started_at": "2026-05-13T00:00:00"}
    ])
    c.script([{"op_id": "op6"}])
    recover(c, "mg1")
    assert seen == ["v2"]


def test_per_client_replayer_isolation() -> None:
    """Phase 09 P51 — replayers on client A are NOT visible to client B.

    Locks the per-Client semantics: distinct InMemoryClient instances
    have distinct ``_replayers`` dicts. Test pollution via module-
    level singleton is impossible by construction.
    """
    c1 = InMemoryClient()
    c2 = InMemoryClient()
    seen: list = []
    register_replayer(c1, "k1", lambda p: seen.append("c1"))
    # c2 has no replayer for "k1"; recover() must raise per P62.
    c2.script([
        {"op_id": "op7", "kind": "k1", "payload_json": "{}",
         "started_at": "2026-05-13T00:00:00"}
    ])
    with pytest.raises(WALReplayerMissingError):
        recover(c2, "mg1")
    assert seen == []


def test_clear_replayers_per_client() -> None:
    """Phase 09 P51 — clear_replayers takes client; clears that client only."""
    c1 = InMemoryClient()
    c2 = InMemoryClient()
    register_replayer(c1, "k1", lambda p: None)
    register_replayer(c2, "k1", lambda p: None)
    clear_replayers(c1)
    # c1 has no registered replayers; c2 still does.
    c1.script([
        {"op_id": "op8", "kind": "k1", "payload_json": "{}",
         "started_at": "2026-05-13T00:00:00"}
    ])
    with pytest.raises(WALReplayerMissingError):
        recover(c1, "mg1")
    # c2 still has its replayer; recover() commits.
    c2.script([
        {"op_id": "op9", "kind": "k1", "payload_json": "{}",
         "started_at": "2026-05-13T00:00:00"}
    ])
    c2.script([{"op_id": "op9"}])
    assert recover(c2, "mg1") == 1


def test_wal_entry_dataclass_round_trip() -> None:
    e = WALEntry(operation_id="op", kind="k", payload={"a": 1})
    assert e.operation_id == "op"
    assert e.committed is False
    assert e.committed_at is None
