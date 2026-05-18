"""Phase 13 — ADR-0017 §Revisions amendment + ADR-0149 sentinels.

Mirrors Phase 12's ``test_adr_0044_amendment_1_user_id_charset``
4-skip pattern (and Phase 11's ``test_adr_0134_amendments.py``):
the ADR files live in the parent project tree
(``/Layered Intelligence/docs/decisions/adr/``), NOT under
``halvim_mindsos/``, and therefore are NOT COPYd into the runtime
container image. These sentinels run in the sandbox (where the
parent tree IS reachable) but skip in container.

Per `feedback_docs_source_of_truth.md` Model C (hybrid): ADRs are
immutable + live in the parent project tree; design scratchpad lives
in ``halvim_mindsos/`` until ship.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


# Parent-project ADR dir. Test files run from inside `halvim_mindsos/`
# so the parent is two levels up: halvim_mindsos/tests/phase_13/ →
# halvim_mindsos/tests/ → halvim_mindsos/ → /Layered Intelligence/.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADR_DIR = _REPO_ROOT.parent / "docs" / "decisions" / "adr"


def _adr_dir_reachable() -> bool:
    return _ADR_DIR.exists()


pytestmark = pytest.mark.skipif(
    not _adr_dir_reachable(),
    reason=(
        "Parent-project ADR dir not reachable from this filesystem "
        "(expected in the runtime container per Model C — ADR files "
        "live in /Layered Intelligence/docs/decisions/adr/ outside "
        "the halvim_mindsos/ subtree)."
    ),
)


def _find_adr(num: int) -> Path | None:
    matches = list(_ADR_DIR.glob(f"{num:04d}-*.md"))
    if not matches:
        return None
    return matches[0]


def test_adr_0017_amendment_strict_false_l2_role_schemas() -> None:
    """Phase 13 PB-3 — ADR-0017 §Revisions amendment names the 8 L2
    role schemas + the 2-week-no-edit tightening rule."""
    path = _find_adr(17)
    assert path is not None, "ADR-0017 file not found in parent ADR dir."
    text = path.read_text(encoding="utf-8")
    # Loose check — the amendment mentions L2 role schemas + tightening.
    assert "strict" in text.lower()
    # Phase 13 specifically named amendment marker.
    assert "phase 13" in text.lower() or "Phase 13" in text


def test_adr_0149_l2_role_schemas_strict_false_rule_exists() -> None:
    """Phase 13 PB-7 — ADR-0149 'L2 role-graph schemas at strict=False
    with 2-week tightening rule' is Accepted."""
    path = _find_adr(149)
    assert path is not None, "ADR-0149 file not found in parent ADR dir."
    text = path.read_text(encoding="utf-8")
    assert "strict" in text.lower()
    assert "L2" in text or "Knowledge" in text


def test_adr_0150_reserved_for_phase_14a() -> None:
    """Phase 13 PB-23 — ADR-0150 number reserved; content drafted in
    Phase 14a."""
    path = _find_adr(150)
    assert path is not None, "ADR-0150 file not found in parent ADR dir."
    text = path.read_text(encoding="utf-8")
    assert "reserved" in text.lower() or "Reserved" in text
    assert "14a" in text or "14-a" in text
