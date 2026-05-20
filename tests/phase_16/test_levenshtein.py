"""Phase 16 — in-house Levenshtein DP correctness.

Tests for the private :func:`_levenshtein_distance` +
:func:`_levenshtein_score` + :func:`_iri_tail` helpers in
``mindsos_admin.similarity``. The in-house DP is selected (over
``rapidfuzz``) per Phase 16 design-close — zero external dependency.
"""

from __future__ import annotations

import pytest

from mindsos_admin.similarity import (
    _iri_tail,
    _levenshtein_distance,
    _score_levenshtein,
)


class TestLevenshteinDistance:
    def test_identical_strings_distance_zero(self) -> None:
        assert _levenshtein_distance("hello", "hello") == 0

    def test_empty_left_returns_len_right(self) -> None:
        assert _levenshtein_distance("", "abc") == 3

    def test_empty_right_returns_len_left(self) -> None:
        assert _levenshtein_distance("abc", "") == 3

    def test_both_empty_distance_zero(self) -> None:
        assert _levenshtein_distance("", "") == 0

    def test_single_substitution(self) -> None:
        assert _levenshtein_distance("car", "cat") == 1

    def test_single_insertion(self) -> None:
        assert _levenshtein_distance("car", "cars") == 1

    def test_single_deletion(self) -> None:
        assert _levenshtein_distance("cars", "car") == 1

    def test_classic_kitten_sitting(self) -> None:
        # Canonical example: kitten → sitting = 3 edits.
        assert _levenshtein_distance("kitten", "sitting") == 3

    def test_symmetry(self) -> None:
        # d(a,b) == d(b,a) for all inputs.
        cases = [("abc", "def"), ("longer", "short"), ("car", "automobile")]
        for a, b in cases:
            assert _levenshtein_distance(a, b) == _levenshtein_distance(b, a)


class TestIriTail:
    def test_single_colon(self) -> None:
        assert _iri_tail("dolce:PhysicalObject") == "PhysicalObject"

    def test_multi_colon(self) -> None:
        # Last `:`-separated segment.
        assert _iri_tail("dolce:Class:PhysicalObject") == "PhysicalObject"

    def test_oewn_dotted_tail(self) -> None:
        # OEWN Synsets use dotted tails — preserved verbatim.
        assert _iri_tail("oewn:Synset:car.n.01") == "car.n.01"

    def test_no_colon_returns_input(self) -> None:
        assert _iri_tail("bareword") == "bareword"

    def test_empty_returns_empty(self) -> None:
        assert _iri_tail("") == ""


class TestLevenshteinScore:
    def test_identical_iri_returns_one(self) -> None:
        assert _score_levenshtein(
            "dolce:Class:PhysicalObject", "dolce:Class:PhysicalObject"
        ) == 1.0

    def test_one_edit_close_to_one(self) -> None:
        # PhysicalObject (14) vs PhysicalObjects (15) — 1 edit / 15 = 0.9333...
        score = _score_levenshtein(
            "dolce:Class:PhysicalObject", "dolce:Class:PhysicalObjects"
        )
        assert score is not None
        assert 0.9 < score < 1.0

    def test_wholly_different_returns_low(self) -> None:
        score = _score_levenshtein(
            "dolce:Class:Foo", "dolce:Class:zzzzzzzzz"
        )
        assert score is not None
        assert score < 0.5

    def test_empty_tail_returns_none(self) -> None:
        # When either side has an empty IRI tail, score is undefined.
        assert _score_levenshtein("", "anything") is None
        assert _score_levenshtein("anything", "") is None

    def test_score_uses_iri_tail_only(self) -> None:
        # IRIs with same tail but different prefixes → score 1.0.
        assert _score_levenshtein(
            "dolce:Class:Foo", "framenet:Frame:Foo"
        ) == 1.0
