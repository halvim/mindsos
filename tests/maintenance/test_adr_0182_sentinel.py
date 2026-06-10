"""MAINTENANCE_CHAT M3 (L0-26) — ADR-0182 sentinel.

Pins the node-value serialization contract so SKILL_ACQUISITION R0 designs
against a fixed surface: the ADR exists, is Accepted, picks the node-level
``_value_json`` extension of the ADR-0130 pattern, and routes implementation
to skill-acquisition slot 1 (decide-and-document — zero L0 code ships with
the ADR itself, ADR-0181 precedent).
"""

from __future__ import annotations

from pathlib import Path

_ADR = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "decisions"
    / "adr"
    / "0182-node-value-serialization-contract.md"
)


def test_adr_0182_present_and_accepted() -> None:
    body = _ADR.read_text(encoding="utf-8")
    assert "status: Accepted" in body
    assert "ADR-0182" in body


def test_adr_0182_contract_surface_pinned() -> None:
    body = _ADR.read_text(encoding="utf-8")
    # The chosen mechanism — node-level JSON encoding, ADR-0130 pattern.
    assert "_value_json" in body
    # Primitive values stay on the fast path (no migration).
    assert "Primitive values are unchanged" in body
    # The writer lifts queryable fields flat (keeps ADR-0181 indexable).
    assert "Queryability rule" in body
    # Decide-and-document: implementation owner is skill-acquisition slot 1.
    assert "SKILL_ACQUISITION phase-map slot 1" in body


def test_adr_0182_no_implementation_shipped() -> None:
    """The contract is decided, not implemented: the node-create builder
    still emits the primitive ``n.value`` write and no ``_value_json``
    surface exists in L0 yet. When skill-acquisition slot 1 lands the
    implementation, REPLACE this test with round-trip coverage (extend
    tests/maintenance/test_l0_25_falkor_local_persister_live.py)."""
    builders = (
        Path(__file__).resolve().parents[2]
        / "mindsos_core"
        / "cypher"
        / "builders.py"
    )
    body = builders.read_text(encoding="utf-8")
    assert "n.value = row.value" in body
    assert "_value_json" not in body
