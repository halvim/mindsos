"""Phase 40 — family_rules two-level lookup + 5-shape catalog (ADR-0157)."""

from __future__ import annotations

import pytest

from mindsos_capacity import FAMILY_RULES, FamilyDontKnowShape, family_rule_for


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
    assert family_rule_for("capacity:consolidate:mm") == (
        FamilyDontKnowShape.DATASTATE_MARKER
    )
    assert family_rule_for("capacity:trace:problem") == (
        FamilyDontKnowShape.DATASTATE_MARKER
    )


def test_malformed_iri_raises():
    with pytest.raises(ValueError):
        family_rule_for("predicate.is_question")
    with pytest.raises(ValueError):
        family_rule_for("not-a-capacity-iri")


def test_family_rules_dict_values_are_shapes():
    assert all(isinstance(v, FamilyDontKnowShape) for v in FAMILY_RULES.values())
