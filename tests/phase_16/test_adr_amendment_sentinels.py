"""Phase 16 — ADR amendment sentinels for the 7 Phase 16 amendments.

Mirrors Phase 13 / 14 / 15a / 15b sentinel pattern: ADRs live in the
parent project tree (``/Layered Intelligence/docs/decisions/adr/``)
per Model C (`feedback_docs_source_of_truth.md`), NOT under
``halvim_mindsos/``, and are NOT COPYd into the runtime container
image. These sentinels run in the sandbox where the parent tree IS
reachable but **skip in container** when the parent path is unreachable.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# Parent-project ADR dir: halvim_mindsos/tests/phase_16/ →
# halvim_mindsos/tests/ → halvim_mindsos/ → /Layered Intelligence/.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADR_DIR = _REPO_ROOT.parent / "docs" / "decisions" / "adr"


def _skip_if_adr_dir_missing() -> None:
    if not _ADR_DIR.exists():
        pytest.skip(
            f"ADR directory {_ADR_DIR!r} unreachable (in-container run); "
            f"ADRs live in parent project tree per Model C."
        )


def _assert_amendment(filename: str, header_substr: str, *required_text: str) -> None:
    _skip_if_adr_dir_missing()
    adr = _ADR_DIR / filename
    assert adr.exists(), f"ADR file missing: {adr}"
    content = adr.read_text(encoding="utf-8")
    assert header_substr in content, (
        f"ADR amendment header {header_substr!r} missing from {filename}"
    )
    for substr in required_text:
        assert substr in content, (
            f"Required substring {substr!r} missing from {filename}"
        )


def test_adr_0049_amendment_1_present() -> None:
    """ADR-0049 §amendment-1 — documentary; gate doesn't ship at Phase 16."""
    _assert_amendment(
        "0049-similarity-report-before-promotion.md",
        "amendment-1 (Phase 16 ship",
        "mindsos_admin/similarity.py",
        "ADR-0141",
    )


def test_adr_0052_amendment_1_present() -> None:
    """ADR-0052 §amendment-1 — role-scoped hash + 6-decimal canonicalization."""
    _assert_amendment(
        "0052-report-id-deterministic-content-hash.md",
        "amendment-1 (Phase 16 ship",
        "role-graph being scored",
        "f\"{x:.6f}\"",
    )


def test_adr_0053_amendment_1_present() -> None:
    """ADR-0053 §amendment-1 — documentary; undo-stack doesn't ship at Phase 16."""
    _assert_amendment(
        "0053-promote-per-candidate-atomic-rollback.md",
        "amendment-1 (Phase 16 ship",
        "ADR-0141",
    )


def test_adr_0055_amendment_1_present() -> None:
    """ADR-0055 §amendment-1 — crude heuristic superseded by ADR-0144 §Heuristic."""
    _assert_amendment(
        "0055-baseline-similarity-heuristic-crude.md",
        "amendment-1 (Phase 16 ship",
        "ADR-0144 §Heuristic",
        "Pareto-dominated",
    )


def test_adr_0056_amendment_1_present() -> None:
    """ADR-0056 §amendment-1 — documentary; PromotionResult doesn't ship at Phase 16."""
    _assert_amendment(
        "0056-promotion-result-preserves-input-order.md",
        "amendment-1 (Phase 16 ship",
        "ADR-0141",
    )


def test_adr_0144_amendment_1_present() -> None:
    """ADR-0144 §amendment-1 — §Heuristic Accepted; §Placement stays Proposed."""
    _assert_amendment(
        "0144-similarity-at-release-ship-audit-gate.md",
        "amendment-1 (Phase 16 ship",
        "§Heuristic — Accepted at Phase 16",
        "§Placement — stays Proposed at Phase 16",
        "mindsos_admin/similarity.py",
    )


def test_adr_0144_amendment_2_present() -> None:
    """ADR-0144 §amendment-2 — empty-pair exclusion + EmptyComparisonError contract."""
    _assert_amendment(
        "0144-similarity-at-release-ship-audit-gate.md",
        "amendment-2 (Phase 16 ship",
        "empty-pair exclusion",
        "EmptyComparisonError",
    )
