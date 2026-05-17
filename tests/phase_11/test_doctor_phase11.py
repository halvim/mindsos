"""Tier 11 — Phase 11 doctor / manifest self-consistency.

Per `feedback_phase_baseline_literal_audit.md` (re-extended at B-10-T7):
phase-string / version / compose-tag self-consistency is asserted
DYNAMICALLY against the manifest, never against hard-coded literals.
Phase 11 bumps phase → "11", version → "0.0.0+phase11", image tags →
"mindsos:phase11-{prod,test}".
"""

from __future__ import annotations

from pathlib import Path

import tomli


_MANIFEST_PATH = Path(__file__).resolve().parents[2] / "mindsos_cli" / "manifest.toml"


def _read_manifest() -> dict:
    with _MANIFEST_PATH.open("rb") as f:
        return tomli.load(f)


def test_manifest_phase_matches_version_string() -> None:
    """``manifest.toml`` [mindsos] phase ↔ version stay in sync."""
    m = _read_manifest()
    phase = m["mindsos"]["phase"]
    version = m["mindsos"]["version"]
    # Version format: 0.0.0+phaseNN; the NN must match the phase field.
    assert version.endswith(f"+phase{phase}"), (
        f"version={version!r} does not end with +phase{phase}"
    )


def test_package_versions_parity_with_manifest() -> None:
    """All three top-level packages carry the same ``__version__`` as manifest."""
    import mindsos_cli
    import mindsos_core
    import mindsos_instances
    m = _read_manifest()
    expected = m["mindsos"]["version"]
    assert mindsos_core.__version__ == expected
    assert mindsos_cli.__version__ == expected
    assert mindsos_instances.__version__ == expected


def test_pyproject_version_parity_with_manifest() -> None:
    """``pyproject.toml`` version matches manifest version."""
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with pyproject.open("rb") as f:
        py = tomli.load(f)
    m = _read_manifest()
    assert py["project"]["version"] == m["mindsos"]["version"]


def test_docker_compose_image_tags_parity_with_manifest() -> None:
    """``docker-compose.yml`` image tags use ``mindsos:phaseNN-{prod,test}``."""
    compose = Path(__file__).resolve().parents[2] / "docker-compose.yml"
    text = compose.read_text(encoding="utf-8")
    m = _read_manifest()
    phase = m["mindsos"]["phase"]
    assert f"mindsos:phase{phase}-prod" in text
    assert f"mindsos:phase{phase}-test" in text
