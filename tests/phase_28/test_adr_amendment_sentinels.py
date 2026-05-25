"""Phase 28 — ADR amendment sentinels (skip-in-container per Model C)."""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADR_DIR = _REPO_ROOT.parent / "docs" / "decisions" / "adr"


def _skip_if_adr_dir_missing():
    if not _ADR_DIR.exists():
        pytest.skip(
            f"ADR directory {_ADR_DIR!r} unreachable (in-container run); "
            f"ADRs live in parent project tree per Model C."
        )


def _adr_text(filename):
    adr = _ADR_DIR / filename
    assert adr.exists(), f"ADR file missing: {adr}"
    return adr.read_text(encoding="utf-8")


def test_adr_0040_amendment_2_present():
    _skip_if_adr_dir_missing()
    txt = _adr_text("0040-session-protocol-duck-typing.md")
    assert "amendment-2 (Phase 28 ship" in txt
    assert "mindsos_capacity/types.py" in txt


def test_adr_0061_implementation_phase_28_present():
    _skip_if_adr_dir_missing()
    txt = _adr_text("0061-dual-metagraph-global-local.md")
    assert "§Implementation (Phase 28" in txt
    assert "_resolve_declaration" in txt


def test_adr_0064_implementation_phase_28_present():
    _skip_if_adr_dir_missing()
    txt = _adr_text("0064-one-shared-datastates-graph.md")
    assert "§Implementation (Phase 28" in txt
    assert "ensure_datastate_graph" in txt


def test_adr_0065_implementation_with_15b_pb23_closure():
    _skip_if_adr_dir_missing()
    txt = _adr_text("0065-twelve-functional-categories.md")
    assert "§Implementation (Phase 28" in txt
    assert "Phase 15b PB-23 carry-forward RESOLVED" in txt
    assert "RETRIEVAL capacity" in txt


def test_adr_0066_implementation_footer_flipped_to_shipped():
    _skip_if_adr_dir_missing()
    txt = _adr_text("0066-capacity-iri-form.md")
    assert "Phase 28 (shipped 2026-05-24)" in txt
    assert "CapacityLayer.register_datastate" in txt


def test_adr_0078_amendment_1_uppercase_reconcile():
    _skip_if_adr_dir_missing()
    txt = _adr_text("0078-l3-capability-local-copy.md")
    assert "amendment-1 (Phase 28 ship" in txt
    assert '"CAN_WRITE_GLOBAL"' in txt
    assert "importorskip" in txt


def test_adr_0080_implementation_phase_28_present():
    _skip_if_adr_dir_missing()
    txt = _adr_text("0080-l3-bootstrap-carveout.md")
    assert "§Implementation (Phase 28" in txt
    assert "_enforce_global_write" in txt


def test_adr_0085_implementation_home_graph_only():
    _skip_if_adr_dir_missing()
    txt = _adr_text("0085-multi-graph-membership.md")
    assert "§Implementation (Phase 28" in txt
    assert "home-graph registration only" in txt


def test_adr_0118_amendment_5_in_graph_closure():
    _skip_if_adr_dir_missing()
    txt = _adr_text("0118-per-user-transactional-promotion.md")
    assert "amendment-5 (Phase 28 ship" in txt
    assert ":IN_GRAPH" in txt
    assert "B-26b-T5" in txt
