"""Phase 40 — confirm-phase high-water-mark behavior under the rail DAG.

Phase 40 (Rail B) ships after Phase 44 (Rail C), so the manifest
``[mindsos] phase`` is ahead of the slot being confirmed. confirm-phase
must accept a slot at or below the manifest high-water mark and reject
only a slot strictly ahead. See POST_PHASE_38_PHASE_MAP §1.
"""

from __future__ import annotations

from mindsos_cli.commands.confirm_phase import _phase_exceeds_manifest


def test_equal_phase_not_ahead():
    assert _phase_exceeds_manifest("44", "44") is False


def test_lower_phase_accepted_under_dag():
    assert _phase_exceeds_manifest("40", "44") is False


def test_higher_phase_rejected():
    assert _phase_exceeds_manifest("46", "44") is True


def test_zero_padded_equal():
    assert _phase_exceeds_manifest("09", "09") is False


def test_subphase_numeric_prefix_parsed():
    assert _phase_exceeds_manifest("05a", "44") is False
    assert _phase_exceeds_manifest("44", "05a") is True


def test_non_numeric_token_falls_back_to_inequality():
    assert _phase_exceeds_manifest("xx", "xx") is False
    assert _phase_exceeds_manifest("xx", "yy") is True
