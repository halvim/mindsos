"""Tier 2 — Loader policy resolver + drop-application helper (unit).

Covers :func:`_resolve_unknown_edge_policy` precedence (per-call kwarg
→ env var → default) and the :func:`_apply_unknown_edge_policy`
branching (warn/error/ignore) per PB-10 A + PB-14 A locks.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest

from mindsos_core.exceptions import UnknownEdgeTypeError
from mindsos_core.reconstruction import LoadReport
from mindsos_core.reconstruction.graph_loader import (
    _DEFAULT_UNKNOWN_EDGE_POLICY,
    _UNKNOWN_EDGE_POLICY_ENV,
    _VALID_UNKNOWN_EDGE_POLICIES,
    _apply_unknown_edge_policy,
    _resolve_unknown_edge_policy,
)


# ── precedence ───────────────────────────────────────────────────────────────


def test_default_policy_is_warn() -> None:
    """Hard-coded default (ADR-0134 "default flips" lock)."""
    assert _DEFAULT_UNKNOWN_EDGE_POLICY == "warn"


def test_valid_policies_are_three() -> None:
    """Exactly warn/error/ignore."""
    assert set(_VALID_UNKNOWN_EDGE_POLICIES) == {"warn", "error", "ignore"}


def test_resolve_returns_default_when_nothing_set() -> None:
    """No kwarg + no env var → ``warn``."""
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop(_UNKNOWN_EDGE_POLICY_ENV, None)
        assert _resolve_unknown_edge_policy(None) == "warn"


def test_resolve_kwarg_wins_over_env_and_default() -> None:
    """Per-call kwarg takes precedence over env var (PB-14 A)."""
    with mock.patch.dict(os.environ, {_UNKNOWN_EDGE_POLICY_ENV: "ignore"}):
        assert _resolve_unknown_edge_policy("error") == "error"


def test_resolve_env_wins_over_default_when_kwarg_none() -> None:
    """Env var falls back when kwarg is ``None`` (PB-14 A)."""
    with mock.patch.dict(os.environ, {_UNKNOWN_EDGE_POLICY_ENV: "ignore"}):
        assert _resolve_unknown_edge_policy(None) == "ignore"


def test_resolve_rejects_invalid_kwarg() -> None:
    """Invalid kwarg raises :class:`ValueError`."""
    with pytest.raises(ValueError, match="unknown_edge_type_policy"):
        _resolve_unknown_edge_policy("bogus")


def test_resolve_rejects_invalid_env_var() -> None:
    """Invalid env var raises :class:`ValueError`."""
    with mock.patch.dict(os.environ, {_UNKNOWN_EDGE_POLICY_ENV: "bogus"}):
        with pytest.raises(ValueError, match=_UNKNOWN_EDGE_POLICY_ENV):
            _resolve_unknown_edge_policy(None)


def test_resolve_accepts_all_three_valid_values() -> None:
    """All three valid values pass through."""
    for v in ("warn", "error", "ignore"):
        assert _resolve_unknown_edge_policy(v) == v


# ── _apply_unknown_edge_policy ───────────────────────────────────────────────


def test_apply_policy_warn_marks_warned_set_and_records_drop() -> None:
    """``warn`` records + marks for end-of-load summary log (PB-10 A)."""
    report = LoadReport(graph_id="g1")
    warned: set = set()
    _apply_unknown_edge_policy(
        graph_id="g1",
        type_name="WORKS_AT_LEGACY",
        element_kind="Edge",
        report=report,
        policy="warn",
        warned_types=warned,
    )
    assert report.dropped_edge_count == 1
    assert report.dropped_by_type == {"WORKS_AT_LEGACY": 1}
    assert "WORKS_AT_LEGACY" in warned


def test_apply_policy_warn_per_distinct_type_only_marks_once_per_type() -> None:
    """Multiple drops of the same type mark the type ONCE in ``warned``."""
    report = LoadReport(graph_id="g1")
    warned: set = set()
    for _ in range(5):
        _apply_unknown_edge_policy(
            graph_id="g1",
            type_name="WORKS_AT_LEGACY",
            element_kind="Edge",
            report=report,
            policy="warn",
            warned_types=warned,
        )
    assert report.dropped_edge_count == 5
    assert warned == {"WORKS_AT_LEGACY"}, "PB-10 A — per-distinct-type only"


def test_apply_policy_error_raises_immediately() -> None:
    """``error`` raises :class:`UnknownEdgeTypeError` on first hit."""
    report = LoadReport(graph_id="g1")
    warned: set = set()
    with pytest.raises(UnknownEdgeTypeError) as exc_info:
        _apply_unknown_edge_policy(
            graph_id="g1",
            type_name="UNKNOWN_TYPE",
            element_kind="Edge",
            report=report,
            policy="error",
            warned_types=warned,
        )
    assert exc_info.value.graph_id == "g1"
    assert exc_info.value.type_name == "UNKNOWN_TYPE"
    assert exc_info.value.element_kind == "Edge"
    # Drop IS recorded before raise (so caller can inspect partial state).
    assert report.dropped_edge_count == 1


def test_apply_policy_ignore_records_drop_but_does_not_mark_warned() -> None:
    """``ignore`` is silent — no WARN, no error, but still tracks drops."""
    report = LoadReport(graph_id="g1")
    warned: set = set()
    _apply_unknown_edge_policy(
        graph_id="g1",
        type_name="ANY",
        element_kind="Edge",
        report=report,
        policy="ignore",
        warned_types=warned,
    )
    assert report.dropped_edge_count == 1
    assert warned == set(), "ignore must not mark for WARN summary"


def test_apply_policy_error_carries_element_kind_label() -> None:
    """``element_kind="HyperEdge"`` propagates into the exception."""
    report = LoadReport(graph_id="g1")
    warned: set = set()
    with pytest.raises(UnknownEdgeTypeError) as exc_info:
        _apply_unknown_edge_policy(
            graph_id="g1",
            type_name="MEETING_LEGACY",
            element_kind="HyperEdge",
            report=report,
            policy="error",
            warned_types=warned,
        )
    assert exc_info.value.element_kind == "HyperEdge"
