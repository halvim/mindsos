"""Phase 31 — text capacity IRI literals are stable.

Tests the `text.X` naming convention picked at R0 PB-4 (mirror parent;
the `text.` prefix scales as Phase 32+ may add `text.lowercase` etc.).
"""

from __future__ import annotations

from mindsos_capacity.identifiers import CATEGORY_PERCEPTION, capacity_iri


def test_space_split_iri_literal():
    assert (
        capacity_iri(CATEGORY_PERCEPTION, "text.space_split")
        == "capacity:perception:text.space_split"
    )


def test_sentence_split_iri_literal():
    assert (
        capacity_iri(CATEGORY_PERCEPTION, "text.sentence_split")
        == "capacity:perception:text.sentence_split"
    )
