"""Phase 40 — family_rules two-level lookup + 5-shape catalog (ADR-0157)."""

from __future__ import annotations

import pytest

from mindsos_capacity import FAMILY_RULES, FamilyDontKnowShape, family_rule_for
from mindsos_capacity.family_rules import DEFERRED_DEFAULT_CATEGORIES


def test_five_shapes_present():
    names = {s.name for s in FamilyDontKnowShape}
    assert names == {
        "DATASTATE_MARKER",
        "OPTIONAL_RETURN",
        "VERDICT",
        "VALIDATION_RESULT",
        "NO_DONT_KNOW",
    }


def test_category_lookup_predicate_no_dont_know():
    assert family_rule_for("capacity:predicate:is_question") == (
        FamilyDontKnowShape.NO_DONT_KNOW
    )


def test_category_lookup_scoring_optional_return():
    assert family_rule_for("capacity:scoring:attention_score") == (
        FamilyDontKnowShape.OPTIONAL_RETURN
    )


def test_category_lookup_decision_verdict():
    assert family_rule_for("capacity:decision:tier") == FamilyDontKnowShape.VERDICT


def test_category_lookup_validate_validation_result():
    assert family_rule_for("capacity:validate:xref") == (
        FamilyDontKnowShape.VALIDATION_RESULT
    )


def test_name_prefix_lookup_method_library():
    assert family_rule_for("capacity:agglomeration:combination.bayesian") == (
        FamilyDontKnowShape.OPTIONAL_RETURN
    )


def test_explicit_perception_datastate_marker():
    assert family_rule_for("capacity:perception:text.space_split") == (
        FamilyDontKnowShape.DATASTATE_MARKER
    )


def test_permissive_default_for_unkeyed_category():
    # Phase 42 / L3-57 (PB-21): consolidate + trace now resolve via
    # explicit FAMILY_RULES keys, so this default-path check moved to the
    # categories that intentionally stay unkeyed (DEFERRED_DEFAULT_CATEGORIES).
    #
    # **It named two of them by hand, and one was ratified out from under
    # it** (2026-08-16: `comprehension` took an explicit OPTIONAL_RETURN
    # key when the model reader shipped, and this went red). The example
    # is now READ FROM the frozenset it is an example of, so the next
    # ratification cannot break it — the audit doc's own pin already
    # walks that set, and this walks it for the LOOKUP path.
    assert DEFERRED_DEFAULT_CATEGORIES, "an empty set would assert nothing"
    for category in sorted(DEFERRED_DEFAULT_CATEGORIES):
        assert family_rule_for(f"capacity:{category}:foo") == (
            FamilyDontKnowShape.DATASTATE_MARKER
        ), f"{category!r} is in the deferred set but resolves to a keyed shape"


def test_renamed_and_added_category_keys_phase42():
    # ADR-0157 §am-1: derive->derivation, signal->signalling (typo-class
    # renames vs shipped FUNCTIONAL_CATEGORIES); consolidate + trace added.
    assert family_rule_for("capacity:derivation:foo") == (
        FamilyDontKnowShape.DATASTATE_MARKER
    )
    assert family_rule_for("capacity:signalling:foo") == (
        FamilyDontKnowShape.OPTIONAL_RETURN
    )
    assert family_rule_for("capacity:consolidate:mm") == (
        FamilyDontKnowShape.DATASTATE_MARKER
    )
    assert family_rule_for("capacity:trace:problem") == (
        FamilyDontKnowShape.DATASTATE_MARKER
    )
    # The old misspelled keys no longer exist.
    assert "derive" not in FAMILY_RULES
    assert "signal" not in FAMILY_RULES


def test_malformed_iri_raises():
    with pytest.raises(ValueError):
        family_rule_for("predicate.is_question")
    with pytest.raises(ValueError):
        family_rule_for("not-a-capacity-iri")


def test_family_rules_dict_values_are_shapes():
    assert all(isinstance(v, FamilyDontKnowShape) for v in FAMILY_RULES.values())
