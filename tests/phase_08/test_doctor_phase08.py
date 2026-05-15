"""Manifest + version-string parity verification for Phase 08 (R4-15 A).

**Phase 09 B-09-T5** — original Phase 08 baseline literals (`"08"`,
`"0.0.0+phase08"`, `"phase08-prod"`) replaced with dynamic reads from
the manifest. Tests now verify *parity* across files (manifest +
__init__.py + pyproject.toml + docker-compose.yml all agree on the
current phase string), not the literal `08` value. Future phase bumps
no longer require edits here.
"""

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


def test_manifest_phase_field_present_and_well_formed() -> None:
    """Phase field is a 2-digit string."""
    m = _read_manifest()
    phase = m["mindsos"]["phase"]
    assert isinstance(phase, str)
    assert phase.isdigit()
    assert len(phase) == 2


def test_manifest_version_field_matches_phase() -> None:
    """Version field encodes the same phase as the phase field."""
    m = _read_manifest()
    phase = m["mindsos"]["phase"]
    version = m["mindsos"]["version"]
    assert version == f"0.0.0+phase{phase}"


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


def test_compose_image_tags_match_manifest_phase() -> None:
    """R4-16 A — image tags `mindsos:phase<NN>-prod` / `mindsos:phase<NN>-test`.

    Phase 09 B-09-T5: dynamic read from manifest replaces the
    hard-coded `phase08` literals. Parity ensures the compose tags
    match whatever phase the manifest declares.
    """
    m = _read_manifest()
    phase = m["mindsos"]["phase"]
    text = (_REPO_ROOT / "docker-compose.yml").read_text()
    assert f"mindsos:phase{phase}-prod" in text
    assert f"mindsos:phase{phase}-test" in text
