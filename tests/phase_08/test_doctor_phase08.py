"""Manifest + version-string parity verification for Phase 08 (R4-15 A)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import mindsos_cli
import mindsos_core
import mindsos_instances


_REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_manifest() -> dict:
    return tomllib.loads(
        (_REPO_ROOT / "mindsos_cli" / "manifest.toml").read_text()
    )


def test_manifest_phase_bumped_to_08() -> None:
    m = _read_manifest()
    assert m["mindsos"]["phase"] == "08"


def test_manifest_version_bumped_to_phase08() -> None:
    m = _read_manifest()
    assert m["mindsos"]["version"] == "0.0.0+phase08"


def test_three_package_version_string_parity() -> None:
    """R4-15 A — `mindsos_cli`, `mindsos_core`, `mindsos_instances` parity."""
    m = _read_manifest()
    expected = m["mindsos"]["version"]
    assert mindsos_cli.__version__ == expected
    assert mindsos_core.__version__ == expected
    assert mindsos_instances.__version__ == expected


def test_pyproject_version_matches_manifest() -> None:
    """pyproject.toml [project] version matches manifest [mindsos] version."""
    pp = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text())
    m = _read_manifest()
    assert pp["project"]["version"] == m["mindsos"]["version"]


def test_compose_image_tags_match_phase() -> None:
    """R4-16 A — image tags `mindsos:phase08-prod` / `mindsos:phase08-test`."""
    text = (_REPO_ROOT / "docker-compose.yml").read_text()
    assert "mindsos:phase08-prod" in text
    assert "mindsos:phase08-test" in text
    # Stale phase07 tags absent.
    assert "mindsos:phase07-prod" not in text
    assert "mindsos:phase07-test" not in text
