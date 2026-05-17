"""Tier 5 — Phase 12 doctor / manifest self-consistency (4-pkg parity).

Per `feedback_phase_baseline_literal_audit.md` (re-extended at B-10-T7):
phase-string / version / compose-tag self-consistency is asserted
DYNAMICALLY against the manifest, never against hard-coded literals.
Phase 12 bumps phase → "12", version → "0.0.0+phase12", image tags →
"mindsos:phase12-{prod,test}", AND adds 4-pkg parity over
mindsos_knowledge.
"""

from __future__ import annotations

from pathlib import Path

try:
    import tomllib  # Python 3.11+ stdlib (feedback_tomllib_stdlib_fallback.md)
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]


_MANIFEST_PATH = Path(__file__).resolve().parents[2] / "mindsos_cli" / "manifest.toml"


def _read_manifest() -> dict:
    with _MANIFEST_PATH.open("rb") as f:
        return tomllib.load(f)


def test_phase_12_four_package_parity() -> None:
    """All FOUR top-level packages carry the same ``__version__`` as manifest."""
    import mindsos_cli
    import mindsos_core
    import mindsos_instances
    import mindsos_knowledge

    m = _read_manifest()
    expected = m["mindsos"]["version"]
    assert mindsos_core.__version__ == expected
    assert mindsos_cli.__version__ == expected
    assert mindsos_instances.__version__ == expected
    assert mindsos_knowledge.__version__ == expected


def test_phase_12_compose_image_tags_parity() -> None:
    compose = Path(__file__).resolve().parents[2] / "docker-compose.yml"
    text = compose.read_text(encoding="utf-8")
    m = _read_manifest()
    phase = m["mindsos"]["phase"]
    assert f"mindsos:phase{phase}-prod" in text
    assert f"mindsos:phase{phase}-test" in text
