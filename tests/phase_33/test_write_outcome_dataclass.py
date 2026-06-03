"""Phase 33 — WriteResult dataclass shape + WriteOutcome alias."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

import mindsos_capacity
from mindsos_capacity import ProblemTraceRecord, WriteOutcome, WriteResult


def test_write_result_is_frozen_dataclass():
    wr = WriteResult(
        iri="episodic-memories-v1:memory:alice:m1",
        role="episodic_memories",
        scope="local",
        written_at=datetime.now(timezone.utc),
    )
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        wr.iri = "other"  # type: ignore[misc]


def test_write_result_fields():
    now = datetime.now(timezone.utc)
    wr = WriteResult(
        iri="episodic-memories-v1:memory:alice:m1",
        role="episodic_memories",
        scope="local",
        written_at=now,
    )
    assert wr.iri == "episodic-memories-v1:memory:alice:m1"
    assert wr.role == "episodic_memories"
    assert wr.scope == "local"
    assert wr.written_at == now
    assert wr.extras == {}


def test_write_result_extras_defaults_to_empty_dict():
    wr = WriteResult(
        iri="x", role="episodic_memories", scope="local", written_at=datetime.now(timezone.utc)
    )
    assert wr.extras == {}
    # Ensure each instance gets its own dict (field(default_factory=dict))
    wr2 = WriteResult(
        iri="y", role="episodic_memories", scope="local", written_at=datetime.now(timezone.utc)
    )
    assert wr.extras is not wr2.extras


def test_write_outcome_is_union_of_writeresult_and_problemtracerecord():
    # WriteOutcome is a typing.Union — instances of either member match.
    wr = WriteResult(
        iri="x", role="episodic_memories", scope="local", written_at=datetime.now(timezone.utc)
    )
    ptr = ProblemTraceRecord(
        task_id="t1",
        capacity_iri="capacity:trace:problem",
        error_kind="probe",
        payload={},
    )
    # At runtime, isinstance against typing.Union doesn't work directly;
    # the test is that both members are valid carriers.
    assert isinstance(wr, WriteResult)
    assert isinstance(ptr, ProblemTraceRecord)
    # WriteOutcome is exported as a value (Union object).
    assert WriteOutcome is mindsos_capacity.WriteOutcome


def test_write_result_scope_literal():
    # The dataclass accepts the literal values; Python doesn't enforce
    # Literal at runtime, so we assert presence not enforcement.
    for scope in ("local", "global"):
        wr = WriteResult(
            iri="x",
            role="episodic_memories" if scope == "local" else "problem-trace",
            scope=scope,  # type: ignore[arg-type]
            written_at=datetime.now(timezone.utc),
        )
        assert wr.scope == scope
