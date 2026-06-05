"""Phase 40 ADR sentinel chain (link from Phase 39).

Anchors the ratified text of ADR-0157 (family-specific dont-know
contracts) + ADR-0158 (DataState naming convention + realms). Both are
already ``status: Accepted`` on disk from the L1/L3 reframe chat
(2026-06-01); Phase 40 implements them and pins their canonical strings.
"""

from __future__ import annotations

from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADR_DIR = _REPO_ROOT / "docs" / "decisions" / "adr"

assert _ADR_DIR.exists(), (
    f"ADR directory missing at expected path: {_ADR_DIR}."
)


def _read_adr(slug: str) -> str:
    adr = _ADR_DIR / slug
    assert adr.exists(), f"ADR file missing: {adr}"
    return adr.read_text(encoding="utf-8")


_ADR_0157 = "0157-family-specific-dontknow-contracts.md"
_ADR_0158 = "0158-datastate-naming-convention-and-realms.md"


def test_adr_0157_accepted():
    assert "status: Accepted" in _read_adr(_ADR_0157)


def test_adr_0157_family_specific():
    text = _read_adr(_ADR_0157)
    assert "family-specific" in text
    assert "FAMILY_RULES" in text
    assert "family_rules.py" in text


def test_adr_0157_five_shape_catalog():
    text = _read_adr(_ADR_0157)
    for shape in (
        "DATASTATE_MARKER",
        "OPTIONAL_RETURN",
        "VERDICT",
        "VALIDATION_RESULT",
        "NO_DONT_KNOW",
    ):
        assert shape in text, f"ADR-0157 missing shape {shape!r}"


def test_adr_0157_marker_constant():
    text = _read_adr(_ADR_0157)
    assert "DS_UNHANDLED_INPUT" in text
    assert "datastate:marker.unhandled_input" in text


def test_adr_0158_accepted():
    assert "status: Accepted" in _read_adr(_ADR_0158)


def test_adr_0158_naming_convention():
    text = _read_adr(_ADR_0158)
    assert "datastate:<realm>.<name>" in text
    assert "RESERVED_REALMS" in text
    assert "allow_new_realm" in text


def test_adr_0158_nine_realms():
    text = _read_adr(_ADR_0158)
    for realm in (
        "core",
        "marker",
        "bridge",
        "text",
        "mm",
        "problem_trace",
        "nlu",
        "code",
        "dream",
    ):
        assert realm in text, f"ADR-0158 missing realm {realm!r}"
