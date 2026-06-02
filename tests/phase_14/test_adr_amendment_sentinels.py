"""Phase 14 — ADR-0042 §amendment-1 + ADR-0150 §amendment-1 sentinels.

Mirrors Phase 13 / Phase 12 sentinel pattern: the ADR files live in
the parent project tree (``/Layered Intelligence/docs/decisions/adr/``)
per Model C (`feedback_docs_source_of_truth.md`), NOT under
``halvim_mindsos/``, and therefore are NOT COPYd into the runtime
container image. These sentinels run in the sandbox where the parent
tree IS reachable but **skip in container** when the parent path is
unreachable.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


# Parent-project ADR dir. Test files run from inside `halvim_mindsos/`
# so the parent is two levels up: halvim_mindsos/tests/phase_14/ →
# halvim_mindsos/tests/ → halvim_mindsos/ → /Layered Intelligence/.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADR_DIR = _REPO_ROOT / "docs" / "decisions" / "adr"


def _adr_path(slug: str) -> Path:
    return _ADR_DIR / slug


def _skip_if_adr_dir_missing() -> None:
    """Skip the test when the parent ADR tree is unreachable (container)."""
    if not _ADR_DIR.exists():
        pytest.skip(
            f"ADR directory {_ADR_DIR!r} unreachable (in-container run); "
            f"ADRs live in parent project tree per Model C."
        )


def test_adr_0042_amendment_1_present() -> None:
    """ADR-0042 §amendment-1 (Phase 14 PB-7 — Global lifecycle) exists."""
    _skip_if_adr_dir_missing()
    p = _adr_path("0042-kl-install-extract-hooks.md")
    assert p.exists(), f"ADR-0042 file missing: {p}"
    content = p.read_text(encoding="utf-8")
    assert "amendment-1" in content, (
        "ADR-0042 missing §amendment-1 (Phase 14 PB-7 Global lifecycle "
        "via constructor parameter)."
    )
    assert "Phase 14" in content
    assert "Global lifecycle" in content


def test_adr_0150_amendment_1_present() -> None:
    """ADR-0150 §amendment-1 (Phase 14 PB-8 — alignment Global-only) exists."""
    _skip_if_adr_dir_missing()
    p = _adr_path("0150-l2-knowledge-lifecycle.md")
    assert p.exists(), f"ADR-0150 file missing: {p}"
    content = p.read_text(encoding="utf-8")
    assert "amendment-1" in content, (
        "ADR-0150 missing §amendment-1 (Phase 14 PB-8 alignment Global-"
        "only at v1)."
    )
    assert "alignment role is Global-only" in content


def test_adr_0042_amendment_documents_constructor_parameter() -> None:
    """Specific surface check on ADR-0042 §amendment-1 body."""
    _skip_if_adr_dir_missing()
    p = _adr_path("0042-kl-install-extract-hooks.md")
    content = p.read_text(encoding="utf-8")
    assert "global_metagraph: Metagraph | None" in content


def test_adr_0150_amendment_documents_ensure_local_rejection() -> None:
    """Specific surface check on ADR-0150 §amendment-1 body."""
    _skip_if_adr_dir_missing()
    p = _adr_path("0150-l2-knowledge-lifecycle.md")
    content = p.read_text(encoding="utf-8")
    assert "ensure_local_role_graph" in content
    assert "rejects alignment prefixes" in content
