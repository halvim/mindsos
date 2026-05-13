"""Lockfile + falkordb-pin guard tests (Phase 07)."""

from __future__ import annotations

import hashlib
from pathlib import Path

try:
    import tomllib  # type: ignore[import]  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]


REPO = Path(__file__).resolve().parents[2]


def test_requirements_in_pins_falkordb_already() -> None:
    """P46 A — Phase 00 baseline already pinned falkordb>=1.6.1,<2.0."""
    body = (REPO / "requirements.in").read_text()
    assert "falkordb>=1.6.1,<2.0" in body


def test_requirements_txt_resolved_to_1_6_1() -> None:
    body = (REPO / "requirements.txt").read_text()
    assert "falkordb==1.6.1" in body


def test_manifest_sha256_matches_requirements_txt() -> None:
    """Catches forgotten manifest bumps after lockfile regen."""
    txt = (REPO / "requirements.txt").read_bytes()
    actual = hashlib.sha256(txt).hexdigest()
    manifest = tomllib.loads((REPO / "mindsos_cli" / "manifest.toml").read_text())
    pinned = manifest["lockfile"]["requirements_txt_sha256"]
    if pinned == "PENDING_LOCK":
        # PENDING_LOCK is allowed; tester must rerun tools/lock.sh.
        return
    assert pinned == actual, (
        f"manifest sha256 drift: pinned={pinned} actual={actual}"
    )
