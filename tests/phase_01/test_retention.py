"""Pure-Python tests for the retention-window selection logic.

The release workflow shells out to `gh api` + `jq`, but the SELECTION logic
lives in `mindsos_cli/_retention.py` and is unit-tested here without GitHub.
"""

from __future__ import annotations

import pytest

from mindsos_cli._retention import (
    RetentionDecision,
    parse_phase_number,
    parse_tag,
    select_retention,
)


def test_parse_phase_number_recognises_canonical_form():
    assert parse_phase_number("phase-00-confirmed") == 0
    assert parse_phase_number("phase-01-confirmed") == 1
    assert parse_phase_number("phase-38-confirmed") == 38


def test_parse_phase_number_recognises_supersession_form():
    assert parse_phase_number("phase-01-v2-confirmed") == 1
    assert parse_phase_number("phase-12-v3-confirmed") == 12


def test_parse_tag_returns_version():
    assert parse_tag("phase-01-confirmed").version == 1
    assert parse_tag("phase-01-v2-confirmed").version == 2
    assert parse_tag("phase-01-v10-confirmed").version == 10


def test_parse_phase_number_rejects_other_tags():
    assert parse_phase_number("phase-00") is None  # no -confirmed
    assert parse_phase_number("phase-01-superseded") is None
    assert parse_phase_number("v1.0.0") is None
    assert parse_phase_number("phase-aa-confirmed") is None
    assert parse_phase_number("phase-01-v-confirmed") is None  # no number after v


def test_select_retention_keeps_all_when_under_window():
    tags = [f"phase-{i:02d}-confirmed" for i in range(3)]
    result = select_retention(tags, window=5)
    assert isinstance(result, RetentionDecision)
    assert sorted(result.keep) == sorted(tags)
    assert result.evict == []


def test_select_retention_evicts_oldest_when_over_window():
    tags = [f"phase-{i:02d}-confirmed" for i in range(8)]
    result = select_retention(tags, window=5)
    assert result.keep == [
        "phase-07-confirmed",
        "phase-06-confirmed",
        "phase-05-confirmed",
        "phase-04-confirmed",
        "phase-03-confirmed",
    ]
    assert result.evict == [
        "phase-02-confirmed",
        "phase-01-confirmed",
        "phase-00-confirmed",
    ]


def test_select_retention_ignores_non_matching_tags():
    tags = [
        "phase-01-confirmed",
        "phase-02-superseded",
        "v1.0.0",
        "phase-03-confirmed",
    ]
    result = select_retention(tags, window=5)
    assert sorted(result.keep) == ["phase-01-confirmed", "phase-03-confirmed"]
    assert result.evict == []


def test_select_retention_empty_input():
    result = select_retention([])
    assert result.keep == []
    assert result.evict == []


def test_select_retention_rejects_negative_window():
    with pytest.raises(ValueError):
        select_retention(["phase-00-confirmed"], window=-1)


def test_select_retention_window_zero_evicts_everything():
    tags = ["phase-00-confirmed", "phase-01-confirmed"]
    result = select_retention(tags, window=0)
    assert result.keep == []
    assert sorted(result.evict) == sorted(tags)


def test_supersession_tag_evicts_original_within_same_slot():
    """Both tags exist for phase 01; v2 wins, v1 evicts immediately."""
    tags = ["phase-01-confirmed", "phase-01-v2-confirmed"]
    result = select_retention(tags, window=5)
    assert result.keep == ["phase-01-v2-confirmed"]
    assert result.evict == ["phase-01-confirmed"]


def test_supersession_with_v3_evicts_v1_and_v2():
    tags = [
        "phase-05-confirmed",
        "phase-05-v2-confirmed",
        "phase-05-v3-confirmed",
    ]
    result = select_retention(tags, window=5)
    assert result.keep == ["phase-05-v3-confirmed"]
    assert sorted(result.evict) == [
        "phase-05-confirmed",
        "phase-05-v2-confirmed",
    ]


def test_supersession_slot_counts_as_one_window_slot():
    """A v2 supersession does not consume a second slot."""
    tags = [
        f"phase-{i:02d}-confirmed" for i in range(7)
    ] + ["phase-03-v2-confirmed"]
    result = select_retention(tags, window=5)
    # Top 5 slots are phases 6, 5, 4, 3, 2 — each represented by its highest version.
    keep_phases = [int(t.split("-")[1]) for t in result.keep]
    assert keep_phases == [6, 5, 4, 3, 2]
    # Phase 03's install target must be the v2 tag, not the original.
    assert "phase-03-v2-confirmed" in result.keep
    assert "phase-03-confirmed" in result.evict
    # Phase 01 + 00 evict for being outside the window.
    assert "phase-01-confirmed" in result.evict
    assert "phase-00-confirmed" in result.evict


def test_supersession_outside_window_all_versions_evict():
    """Phase 00 is outside the 5-slot window; both its v1 and v2 tarballs evict."""
    tags = [
        "phase-00-confirmed",
        "phase-00-v2-confirmed",
    ] + [f"phase-{i:02d}-confirmed" for i in range(1, 6)]
    result = select_retention(tags, window=5)
    keep_phases = sorted(int(t.split("-")[1]) for t in result.keep)
    assert keep_phases == [1, 2, 3, 4, 5]
    assert sorted(result.evict) == [
        "phase-00-confirmed",
        "phase-00-v2-confirmed",
    ]


# ── Letter sub-phase coverage (Phase 05a hotfix; SUPER-§1-EXT lock) ─────────


def test_parse_tag_recognises_letter_sub_phase():
    """phase-05a-confirmed parses with letter='a'."""
    info = parse_tag("phase-05a-confirmed")
    assert info is not None
    assert info.phase == 5
    assert info.letter == "a"
    assert info.version == 1
    assert info.slot == (5, "a")


def test_parse_tag_letter_with_supersession():
    """phase-05a-v2-confirmed combines letter + vM."""
    info = parse_tag("phase-05a-v2-confirmed")
    assert info is not None
    assert info.phase == 5
    assert info.letter == "a"
    assert info.version == 2


def test_parse_tag_bare_numeric_has_empty_letter():
    """phase-05-confirmed has letter=''."""
    info = parse_tag("phase-05-confirmed")
    assert info is not None
    assert info.letter == ""
    assert info.slot == (5, "")


def test_parse_phase_number_returns_numeric_part_only():
    """Back-compat: parse_phase_number('phase-05a-confirmed') == 5."""
    assert parse_phase_number("phase-05a-confirmed") == 5
    assert parse_phase_number("phase-05b-v3-confirmed") == 5


def test_letter_sub_phase_is_separate_slot_from_bare_numeric():
    """phase-05 and phase-05a count as TWO slots, not one."""
    tags = ["phase-05-confirmed", "phase-05a-confirmed", "phase-05b-confirmed"]
    result = select_retention(tags, window=5)
    # All three kept (3 distinct slots within window).
    assert sorted(result.keep) == sorted(tags)
    assert result.evict == []


def test_letter_sub_phase_supersession_evicts_within_slot():
    """phase-05a-v2 evicts phase-05a (same slot); phase-05a stays separate from phase-05."""
    tags = [
        "phase-05-confirmed",
        "phase-05a-confirmed",
        "phase-05a-v2-confirmed",
    ]
    result = select_retention(tags, window=5)
    assert "phase-05a-v2-confirmed" in result.keep
    assert "phase-05-confirmed" in result.keep      # different slot, kept
    assert "phase-05a-confirmed" in result.evict   # same slot, evicted by v2


def test_slot_ordering_05_lt_05a_lt_05b_lt_06():
    """Tuple sort: 05 < 05a < 05b < 06. Window=2 keeps the 2 highest."""
    tags = [
        "phase-05-confirmed",
        "phase-05a-confirmed",
        "phase-05b-confirmed",
        "phase-06-confirmed",
    ]
    result = select_retention(tags, window=2)
    # Top 2 by slot: 06 then 05b.
    assert result.keep == ["phase-06-confirmed", "phase-05b-confirmed"]
    # 05a + 05 evict.
    assert sorted(result.evict) == ["phase-05-confirmed", "phase-05a-confirmed"]


def test_select_retention_letter_sub_phase_evicts_outside_window():
    """5 numeric + 2 letter sub-phases; window=5 keeps top 5 slots by tuple sort."""
    tags = [
        f"phase-{i:02d}-confirmed" for i in range(5)
    ] + ["phase-05a-confirmed", "phase-05b-confirmed"]
    # Slots present: 00, 01, 02, 03, 04, 05a, 05b. 7 slots; top 5 = 05b, 05a, 04, 03, 02.
    result = select_retention(tags, window=5)
    assert result.keep == [
        "phase-05b-confirmed",
        "phase-05a-confirmed",
        "phase-04-confirmed",
        "phase-03-confirmed",
        "phase-02-confirmed",
    ]
    assert sorted(result.evict) == ["phase-00-confirmed", "phase-01-confirmed"]
