"""Phase 36 — semantic-validator unit tests + handle composite tests.

ADR-0139 §Decision §Semantic-invariants. 5 pure-function validators
ship in ``mindsos_knowledge/validators.py``; per-role adapter registry
``_VALIDATORS_BY_ROLE`` consumed by :meth:`KLWriteHandle.validate_node`.

Phase 36 wires 2 adapters (memories + problem-trace) with the
single-validator chain ``(validate_role_routing,)``; future per-flow
phases extend the chain (ADR-0139 §amendment-1 clause 3 carry-forward).
"""

from __future__ import annotations

import pytest

from mindsos_capacity.exceptions import WriteHandleNotWiredError
from mindsos_knowledge import KnowledgeLayer, ValidationResult
from mindsos_knowledge.identifiers import (
    REF_TYPES,
    ROLE_CONCEPTS,
    ROLE_LEXICON,
    ROLE_MEMORIES,
    ROLE_ONTOLOGY,
    ROLE_PROBLEM_TRACE,
    alignment_role,
)
from mindsos_knowledge.validators import (
    _VALIDATORS_BY_ROLE,
    validate_alignment_role_naming,
    validate_local_to_global_ref,
    validate_promotion_candidate,
    validate_ref_type,
    validate_role_routing,
)


def _kl() -> KnowledgeLayer:
    return KnowledgeLayer.bootstrap()


# ── ValidationResult dataclass ────────────────────────────────────────


def test_validation_result_success_factory():
    r = ValidationResult.success()
    assert r.ok is True
    assert r.violation is None


def test_validation_result_violated_factory_carries_reason():
    r = ValidationResult.violated("role unknown")
    assert r.ok is False
    assert r.violation == "role unknown"


def test_validation_result_is_frozen():
    r = ValidationResult.success()
    with pytest.raises(Exception):
        r.ok = False  # type: ignore[misc]


# ── validate_role_routing ─────────────────────────────────────────────


def test_validate_role_routing_ok_global():
    mg = _kl().global_metagraph()
    result = validate_role_routing(role=ROLE_PROBLEM_TRACE, scope="global", mg=mg)
    assert result.ok is True
    assert result.violation is None


def test_validate_role_routing_miss_returns_violation():
    mg = _kl().global_metagraph()
    result = validate_role_routing(
        role="bogus-role-name", scope="global", mg=mg
    )
    assert result.ok is False
    assert "bogus-role-name" in result.violation
    assert "not registered" in result.violation


def test_validate_role_routing_scope_informational_at_phase_36():
    """``scope`` argument is informational at Phase 36 (reserved for
    future scope-specific routing rules). Passing any string does not
    affect outcome — role-graph existence is the gate."""
    mg = _kl().global_metagraph()
    result_a = validate_role_routing(role=ROLE_ONTOLOGY, scope="local", mg=mg)
    result_b = validate_role_routing(role=ROLE_ONTOLOGY, scope="global", mg=mg)
    assert result_a.ok == result_b.ok


# ── validate_local_to_global_ref ──────────────────────────────────────


def test_validate_local_to_global_ref_target_missing():
    mg = _kl().global_metagraph()
    result = validate_local_to_global_ref(
        target_role=ROLE_PROBLEM_TRACE,
        target_iri="problem-trace-v1:entry:nonexistent",
        mg=mg,
    )
    assert result.ok is False
    assert "not present" in result.violation


def test_validate_local_to_global_ref_role_graph_missing():
    mg = _kl().global_metagraph()
    result = validate_local_to_global_ref(
        target_role="bogus-role",
        target_iri="some-iri",
        mg=mg,
    )
    assert result.ok is False
    assert "no graph with role" in result.violation


def test_validate_local_to_global_ref_ok():
    """Populate problem-trace graph with a node, then validate ref to it."""
    mg = _kl().global_metagraph()
    target_iri = "problem-trace-v1:entry:t-test-1"
    for g in mg.graphs.values():
        if g.role == ROLE_PROBLEM_TRACE:
            g.add_node(
                value="seeded",
                type_name="ProblemTraceEntry",
                node_id=target_iri,
            )
            break
    result = validate_local_to_global_ref(
        target_role=ROLE_PROBLEM_TRACE,
        target_iri=target_iri,
        mg=mg,
    )
    assert result.ok is True


# ── validate_alignment_role_naming ────────────────────────────────────


def test_validate_alignment_role_naming_ok_sorted():
    canonical = alignment_role(ROLE_LEXICON, ROLE_CONCEPTS)
    result = validate_alignment_role_naming(role=canonical)
    assert result.ok is True


def test_validate_alignment_role_naming_missing_prefix():
    result = validate_alignment_role_naming(role="lexicon<->concepts")
    assert result.ok is False
    assert "alignment-prefixed" in result.violation


def test_validate_alignment_role_naming_missing_separator():
    result = validate_alignment_role_naming(role="alignment:lexicon-concepts")
    assert result.ok is False
    assert "<->" in result.violation


def test_validate_alignment_role_naming_wrong_order():
    """Sort-order canonicalisation — supplied unsorted pair must fail."""
    a, b = sorted((ROLE_LEXICON, ROLE_CONCEPTS))
    swapped = f"alignment:{b}<->{a}"
    result = validate_alignment_role_naming(role=swapped)
    assert result.ok is False
    assert "not canonical" in result.violation


# ── validate_ref_type ─────────────────────────────────────────────────


def test_validate_ref_type_ok_known():
    for known in REF_TYPES:
        result = validate_ref_type(ref_type=known, target_role=ROLE_LEXICON)
        assert result.ok is True


def test_validate_ref_type_unknown():
    result = validate_ref_type(
        ref_type="MADE_UP_TYPE", target_role=ROLE_LEXICON
    )
    assert result.ok is False
    assert "MADE_UP_TYPE" in result.violation
    assert "not in REF_TYPES" in result.violation


# ── validate_promotion_candidate ──────────────────────────────────────


def test_validate_promotion_candidate_not_found():
    kl = _kl()
    local = kl.local_metagraph("alice")
    result = validate_promotion_candidate(
        local_iri="memories-v1:memory:alice:nonexistent", mg=local
    )
    assert result.ok is False
    assert "not found" in result.violation


def test_validate_promotion_candidate_ok():
    """Seed a Local memory node; validate the IRI is a promotion candidate."""
    kl = _kl()
    local = kl.local_metagraph("alice")
    iri = "memories-v1:memory:alice:m-test-1"
    for g in local.graphs.values():
        if g.role == ROLE_MEMORIES:
            g.add_node(value="seed", type_name="Memory", node_id=iri)
            break
    result = validate_promotion_candidate(local_iri=iri, mg=local)
    assert result.ok is True


# ── KLWriteHandle.validate_node composite ─────────────────────────────


def test_validators_by_role_registry_has_two_entries_at_phase_36():
    """Phase 36 ships 2 adapters (memories + problem-trace) per per-flow
    discipline (ADR-0147 §am-1 clause 3 applied to adapter population)."""
    assert ROLE_MEMORIES in _VALIDATORS_BY_ROLE
    assert ROLE_PROBLEM_TRACE in _VALIDATORS_BY_ROLE
    assert len(_VALIDATORS_BY_ROLE) == 2


def test_handle_validate_node_returns_validation_result_for_memories():
    from tests.phase_33._fixtures import build_session_with_caps

    sess = build_session_with_caps("alice", frozenset())
    h = _kl().writeable(sess, ROLE_MEMORIES, "local")
    result = h.validate_node(value="x", type_="Memory")
    assert isinstance(result, ValidationResult)
    assert result.ok is True


def test_handle_validate_node_returns_validation_result_for_problem_trace():
    h = _kl().writeable(None, ROLE_PROBLEM_TRACE, "global")
    result = h.validate_node(value="x", type_="ProblemTraceEntry")
    assert isinstance(result, ValidationResult)
    assert result.ok is True


def test_handle_validate_node_unregistered_role_raises():
    """Roles without a registered adapter raise WriteHandleNotWiredError
    per per-flow extension discipline (ADR-0139 §am-1 clause 3 carry-
    forward). validate_xref body remains unwired per R1-PB-B."""
    h = _kl().writeable(None, ROLE_ONTOLOGY, "global")
    with pytest.raises(WriteHandleNotWiredError, match="no validator adapter"):
        h.validate_node(value="x", type_="Concept")
