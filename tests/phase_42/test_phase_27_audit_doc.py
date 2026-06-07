"""Phase 42 — Phase 27 dont-know audit deliverable sentinel (L3-57).

Pins the audit doc's presence + shape AND the consistency between the
doc's deferred-category list and the shipped
``family_rules.DEFERRED_DEFAULT_CATEGORIES`` frozenset (so neither can
drift silently). See confirmation_docs/PHASE_27_DONT_KNOW_AUDIT.md.
"""

from __future__ import annotations

import pathlib

from mindsos_capacity.family_rules import (
    FAMILY_RULES,
    DEFERRED_DEFAULT_CATEGORIES,
)

_AUDIT = (
    pathlib.Path(__file__).resolve().parents[2]
    / "confirmation_docs"
    / "PHASE_27_DONT_KNOW_AUDIT.md"
)


def _text() -> str:
    return _AUDIT.read_text(encoding="utf-8")


def test_audit_doc_exists():
    assert _AUDIT.is_file()


def test_audit_doc_has_required_sections():
    text = _text()
    for anchor in (
        "Phase 27 Dont-Know Audit",
        "L3-57",
        "ADR-0157 §amendment-1",
        "DEFERRED_DEFAULT_CATEGORIES",
    ):
        assert anchor in text, f"audit doc missing anchor: {anchor!r}"


def test_deferred_categories_pinned_at_five():
    assert DEFERRED_DEFAULT_CATEGORIES == frozenset({
        "comprehension",
        "decomposition",
        "path-finding",
        "interaction",
        "learning-methods",
    })


def test_doc_lists_every_deferred_category():
    text = _text()
    for cat in DEFERRED_DEFAULT_CATEGORIES:
        assert cat in text, f"deferred category {cat!r} not documented in audit"


def test_deferred_categories_are_not_keyed_in_family_rules():
    # Deferred categories resolve via the permissive default, not a key.
    assert DEFERRED_DEFAULT_CATEGORIES.isdisjoint(set(FAMILY_RULES))


def test_reconciled_keys_present_old_keys_gone():
    for keyed in ("derivation", "signalling", "consolidate", "trace"):
        assert keyed in FAMILY_RULES
    for retired in ("derive", "signal"):
        assert retired not in FAMILY_RULES
