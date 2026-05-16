"""D1-rev — CompositionalImmutableError class retained per ADR-0148.

Phase 10 ADR-0133 amendment-2 strips the compositional clause from the
soft-delete contract but the exception class itself stays alive because
``IntergraphEdge.compositional`` consumes it (per Phase 05b R3-B
re-shipped + ADR-0148 §4.3). Step 0 probe 10 confirmed at port time.
"""

from __future__ import annotations

from mindsos_core import CompositionalImmutableError, CoreError


def test_compositional_immutable_error_is_core_error() -> None:
    assert issubclass(CompositionalImmutableError, CoreError)


def test_compositional_immutable_error_at_expected_module() -> None:
    """Step 0 probe 10 — class lives at exceptions.py:120."""
    import mindsos_core.exceptions as exc_mod
    assert hasattr(exc_mod, "CompositionalImmutableError")
    assert exc_mod.CompositionalImmutableError is CompositionalImmutableError


def test_compositional_immutable_error_raisable() -> None:
    try:
        raise CompositionalImmutableError("test message")
    except CompositionalImmutableError as e:
        assert "test message" in str(e)
