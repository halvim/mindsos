"""PB-2 — _resolve_at(None) → datetime.now(timezone.utc); passthrough on explicit."""

from __future__ import annotations

from datetime import datetime, timezone

from mindsos_core.persistence.soft_delete import _resolve_at


def test_resolve_at_none_returns_utc_now() -> None:
    result = _resolve_at(None)
    assert isinstance(result, datetime)
    assert result.tzinfo is timezone.utc


def test_resolve_at_explicit_passthrough() -> None:
    explicit = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
    assert _resolve_at(explicit) is explicit


def test_resolve_at_naive_datetime_passthrough() -> None:
    """Helper trusts the caller; no tz coercion."""
    naive = datetime(2026, 5, 15, 12, 0)
    assert _resolve_at(naive) is naive
