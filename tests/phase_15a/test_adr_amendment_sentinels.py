"""Phase 15a — ADR-0042 §amendment-2 + ADR-0140 §amendment-1 sentinels.

**Current behaviour (2026-09-16):** ``docs/`` is in this repo and is copied into
the test image, so a missing ADR is a FAILURE here, never a skip. The Model C
layout described below is historical;
``tests/architecture/test_no_skip_when_docs_missing.py`` keeps it that way.

Mirrors Phase 13/14 sentinel pattern: ADRs live in the parent project
tree (``/Layered Intelligence/docs/decisions/adr/``) per Model C
(`feedback_docs_source_of_truth.md`), NOT under ``halvim_mindsos/``,
and are NOT COPYd into the runtime container image. These sentinels
run in the sandbox where the parent tree IS reachable but **skip in
container** when the parent path is unreachable.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# Parent-project ADR dir: halvim_mindsos/tests/phase_15a/ →
# halvim_mindsos/tests/ → halvim_mindsos/ → /Layered Intelligence/.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADR_DIR = _REPO_ROOT / "docs" / "decisions" / "adr"


def _skip_if_adr_dir_missing() -> None:
    if not _ADR_DIR.exists():
        pytest.fail(
            f"ADR directory {_ADR_DIR!r} is missing; docs/ is in the repo "
            f"and copied into the test image, so this is a real failure."
        )


def test_adr_0140_amendment_1_present() -> None:
    """ADR-0140 §amendment-1 — admin permanent home; supersedes §Decision §1+§2."""
    _skip_if_adr_dir_missing()
    adr = _ADR_DIR / "0140-server-owns-admin-operations.md"
    assert adr.exists(), f"ADR-0140 file missing: {adr}"
    content = adr.read_text(encoding="utf-8")
    assert "amendment-1 (Phase 15a ship" in content, (
        "ADR-0140 §amendment-1 (Phase 15a) header missing — "
        "see Phase 15a PB-2-i Round 4 + design log §3."
    )
    assert "mindsos_admin/" in content
    assert "§Decision §1 superseded" in content
    assert "§Decision §2 superseded" in content


def test_adr_0042_amendment_2_present() -> None:
    """ADR-0042 §amendment-2 — third first-install sequence."""
    _skip_if_adr_dir_missing()
    adr = _ADR_DIR / "0042-kl-install-extract-hooks.md"
    assert adr.exists(), f"ADR-0042 file missing: {adr}"
    content = adr.read_text(encoding="utf-8")
    assert "amendment-2 (Phase 15a ship" in content, (
        "ADR-0042 §amendment-2 (Phase 15a) header missing — "
        "see Phase 15a PB-4-i Round 3 + design log §3."
    )
    assert "bootstrap_global" in content
    assert "third first-install sequence" in content
