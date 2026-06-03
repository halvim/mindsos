"""Phase 43 PR2 — 4 new role-graph schemas + IRI builder registration.

Per ADR-0150 §amendment-5 (Phase 43 ship): 4 new role-graphs are
``parameter-staging`` / ``pending-promotions`` / ``capacity-gaps`` /
``learned-parameters``. Plus NPB14-4 5-item exclusion regression
guard — ``sense-correlations`` / ``world-axioms`` / ``training-runs``
/ ``fol-rules`` / ``fol-ledger`` must NOT be in the closed role-set.
"""

from __future__ import annotations

from mindsos_knowledge import (
    Discipline,
    ROLE_CAPACITY_GAPS,
    ROLE_LEARNED_PARAMETERS,
    ROLE_PARAMETER_STAGING,
    ROLE_PENDING_PROMOTIONS,
    capacity_gap_iri,
    learned_parameter_iri,
    pending_promotion_iri,
    staged_evidence_iri,
)
from mindsos_knowledge.identifiers import _IRI_BUILDERS
from mindsos_knowledge.schemas import _ROLE_SCHEMA_BUILDERS


def test_4_new_roles_registered_in_dispatch() -> None:
    for role in (
        ROLE_PARAMETER_STAGING,
        ROLE_PENDING_PROMOTIONS,
        ROLE_CAPACITY_GAPS,
        ROLE_LEARNED_PARAMETERS,
    ):
        assert role in _ROLE_SCHEMA_BUILDERS, (
            f"{role!r} not registered in _ROLE_SCHEMA_BUILDERS"
        )


def test_staged_evidence_iri_shape() -> None:
    assert (
        staged_evidence_iri("v1", "alice", "e1")
        == "parameter-staging-v1:evidence:alice:e1"
    )


def test_pending_promotion_iri_shape() -> None:
    assert (
        pending_promotion_iri("v1", "p1")
        == "pending-promotions-v1:promotion:p1"
    )


def test_capacity_gap_iri_shape() -> None:
    assert capacity_gap_iri("v1", "g1") == "capacity-gaps-v1:gap:g1"


def test_learned_parameter_iri_shape() -> None:
    assert (
        learned_parameter_iri("v1", "lp1")
        == "learned-parameters-v1:parameter:lp1"
    )


def test_4_iri_builder_tuple_keys_registered() -> None:
    for role, type_ in (
        (ROLE_PARAMETER_STAGING, "StagedEvidence"),
        (ROLE_PENDING_PROMOTIONS, "PendingPromotion"),
        (ROLE_CAPACITY_GAPS, "CapacityGap"),
        (ROLE_LEARNED_PARAMETERS, "LearnedParameter"),
    ):
        assert (role, type_) in _IRI_BUILDERS, (
            f"({role!r}, {type_!r}) missing from _IRI_BUILDERS registry"
        )


def test_default_disciplines_for_4_new_role_graphs() -> None:
    """Defaults: parameter-staging + capacity-gaps + learned-parameters (Local)
    are MUTABLE_WITH_RETENTION; pending-promotions is AUDIT_ONLY_AFTER_SETTLED.
    """
    expected = {
        ROLE_PARAMETER_STAGING: Discipline.MUTABLE_WITH_RETENTION,
        ROLE_PENDING_PROMOTIONS: Discipline.AUDIT_ONLY_AFTER_SETTLED,
        ROLE_CAPACITY_GAPS: Discipline.MUTABLE_WITH_RETENTION,
        ROLE_LEARNED_PARAMETERS: Discipline.MUTABLE_WITH_RETENTION,
    }
    for role, expected_discipline in expected.items():
        s = _ROLE_SCHEMA_BUILDERS[role]()
        assert s.mutation_discipline == expected_discipline, (
            f"{role!r} discipline {s.mutation_discipline!r} "
            f"!= expected {expected_discipline!r}"
        )


def test_5_item_exclusion_regression_guard() -> None:
    """NPB14-4 — withdrawn / FOL-chat-owned roles MUST NOT be in role-set."""
    excluded = {
        "sense-correlations",
        "world-axioms",
        "training-runs",
        "fol-rules",
        "fol-ledger",
    }
    registered = set(_ROLE_SCHEMA_BUILDERS.keys())
    leaked = excluded & registered
    assert not leaked, (
        f"excluded roles leaked into _ROLE_SCHEMA_BUILDERS: "
        f"{sorted(leaked)!r}"
    )
