"""Phase 39 L2-35 alignment canonical-form reconciliation.

Per ADR-0154 + L2_CHAT_DECISIONS D-L2-1: ``alignment_role(a, b)``
returns ``alignment:<sorted_a>:<sorted_b>``. Separator is ``:``
between sorted role atoms (Phase 39 reconciliation switched from
``<->`` to ``:``).
"""

from __future__ import annotations

from mindsos_knowledge import alignment_role


def test_alignment_role_returns_colon_separator_form() -> None:
    """Output uses ``:`` between sorted role atoms."""
    out = alignment_role("lexicon", "concepts")
    assert out == "alignment:concepts:lexicon"


def test_alignment_role_sort_invariance() -> None:
    """Order of args doesn't matter — output is canonical."""
    a = alignment_role("lexicon", "concepts")
    b = alignment_role("concepts", "lexicon")
    assert a == b


def test_alignment_role_no_arrow_separator() -> None:
    """Old ``<->`` form retired per Phase 39 L2-35 reconciliation."""
    out = alignment_role("lexicon", "ontology")
    assert "<->" not in out


def test_alignment_role_starts_with_prefix() -> None:
    """All outputs start with the literal ``alignment:`` prefix."""
    for a, b in [
        ("lexicon", "concepts"),
        ("ontology", "lexicon"),
        ("ontology", "concepts"),
    ]:
        assert alignment_role(a, b).startswith("alignment:")


def test_alignment_role_idempotence_on_same_atom() -> None:
    """Same atom on both sides still produces canonical form."""
    out = alignment_role("lexicon", "lexicon")
    assert out == "alignment:lexicon:lexicon"
