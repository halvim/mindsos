"""Phase 34 — ``InvocationResult.write_outcome`` field shape (R0 PB-2 + R1 PB-A)."""

from __future__ import annotations

from mindsos_capacity import InvocationResult, WriteResult


def test_invocation_result_has_write_outcome_field():
    fields = InvocationResult.__dataclass_fields__
    assert "write_outcome" in fields


def test_write_outcome_defaults_to_none():
    """Read paths leave it None; only bypass-branch writes populate."""
    r = InvocationResult(outputs={}, duration_ms=0.0, success=True)
    assert r.write_outcome is None


def test_write_outcome_accepts_write_result():
    from datetime import datetime, timezone

    wr = WriteResult(
        iri="episodic-memories-v1:memory:a:b",
        role="episodic_memories",
        scope="local",
        written_at=datetime.now(timezone.utc),
    )
    r = InvocationResult(
        outputs={}, duration_ms=0.0, success=True, write_outcome=wr
    )
    assert r.write_outcome is wr


def test_existing_fields_unchanged_at_phase_34():
    """Additive change only — outputs/duration_ms/success/error/signals/trace stay."""
    fields = InvocationResult.__dataclass_fields__
    for name in (
        "outputs", "duration_ms", "success", "error", "signals", "trace",
    ):
        assert name in fields, f"existing field {name} missing"
