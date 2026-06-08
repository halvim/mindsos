"""Phase 46 sentinel — ADRs 0163-0170 (L4 substrate) landing checks.

Convergence phase: anchors the 8 new ADRs authored at R0 (the PB-BB
count). Each is Accepted with a §Implementation (Phase 46) footer.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_ADR_DIR = Path(__file__).parents[2] / "docs" / "decisions" / "adr"

_ADRS = [
    "0163-l4-priority-tier-executor.md",
    "0164-mm-rwlock-granularity.md",
    "0165-three-sub-mm-composition.md",
    "0166-mm-resolution-and-instantiation.md",
    "0167-cooperative-cancellation-contract.md",
    "0168-monitor-subscription-registry.md",
    "0169-tier-enum-home-and-signal-triage.md",
    "0170-write-body-session-gating-boundary.md",
]


def _read(name: str) -> str:
    return (_ADR_DIR / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name", _ADRS)
def test_adr_present_and_accepted(name):
    body = _read(name)
    assert "status: Accepted" in body
    assert "**Status:** Accepted" in body


@pytest.mark.parametrize("name", _ADRS)
def test_adr_has_phase_46_implementation_footer(name):
    assert "§Implementation (Phase 46" in _read(name)


def test_eight_adrs_anchored():
    assert len(_ADRS) == 8


def test_tier_enum_home_adr_names_l3_home():
    body = _read("0169-tier-enum-home-and-signal-triage.md")
    assert "mindsos_capacity" in body
    assert "TierVerdict" in body


def test_session_gating_adr_defers_to_phase_47():
    body = _read("0170-write-body-session-gating-boundary.md")
    assert "Phase 47" in body
