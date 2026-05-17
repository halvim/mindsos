"""Tier 14 — confirm-phase pytest summary regex regression (PB-33 / B-10-T6).

Per the Phase 10 B-10-T6 fix, ``_PYTEST_SUMMARY_RE`` must match BOTH
the framed pytest default form (``===== 4 passed in 0.5s =====``) AND
the bare ``-q`` form (``4 passed, 1 skipped in 0.5s``). A regression
in either form would silently zero counts and mask failures (which is
exactly what happened from Phase 09 to Phase 10).
"""

from __future__ import annotations

import pytest

from mindsos_cli.commands.confirm_phase import (
    _PYTEST_SUMMARY_RE,
    _parse_pytest_summary,
)


@pytest.mark.parametrize("line", [
    "===== 4 passed in 0.5s =====",
    "==== 4 passed in 0.5s ====",
    "= 4 passed in 0.5s =",
    "===== 162 passed, 3 skipped in 1.2s =====",
])
def test_framed_summary_form_matches(line: str) -> None:
    """Framed pytest summary lines match the regex."""
    assert _PYTEST_SUMMARY_RE.match(line.strip()) is not None


@pytest.mark.parametrize("line", [
    "4 passed, 1 skipped in 0.5s",
    "162 passed in 1.2s",
    "1 failed, 2 passed in 0.3s",
])
def test_bare_summary_form_matches(line: str) -> None:
    """Bare ``pytest -q`` summary lines match (B-10-T6 fix)."""
    assert _PYTEST_SUMMARY_RE.match(line.strip()) is not None


def test_count_extractor_yields_nonzero_for_framed_form() -> None:
    """End-to-end: framed line produces non-zero ``passed`` count."""
    counts = _parse_pytest_summary("===== 162 passed, 3 skipped in 1.2s =====")
    assert counts["passed"] == 162
    assert counts["skipped"] == 3
    assert counts["failed"] == 0


def test_count_extractor_yields_nonzero_for_bare_form() -> None:
    """End-to-end: bare line produces non-zero ``passed`` count."""
    counts = _parse_pytest_summary("162 passed, 3 skipped in 1.2s")
    assert counts["passed"] == 162
    assert counts["skipped"] == 3
    assert counts["failed"] == 0


def test_count_extractor_handles_failures() -> None:
    """``failed`` is parsed in both forms."""
    framed = _parse_pytest_summary("===== 1 failed, 161 passed in 1.0s =====")
    bare = _parse_pytest_summary("1 failed, 161 passed in 1.0s")
    assert framed["failed"] == 1
    assert framed["passed"] == 161
    assert bare["failed"] == 1
    assert bare["passed"] == 161
