"""Phase 43 PR1 sentinel — ``validate_mutation_discipline`` reject paths.

ADR-0153 §2 + §3 (discipline-by-discipline reject logic) +
``MutationDisciplineError`` construction surface (ADR-0153 §5).
"""

from __future__ import annotations

from mindsos_knowledge import (
    Discipline,
    KnowledgeError,
    MutationDisciplineError,
)
from mindsos_knowledge.validators import validate_mutation_discipline


def test_immutable_successor_rejects_content_field() -> None:
    r = validate_mutation_discipline(
        discipline=Discipline.IMMUTABLE_SUCCESSOR,
        field="pipeline_name",
        role="promoted-pipelines",
        iri="iri://x",
        content_fields=frozenset({"pipeline_name"}),
    )
    assert not r.ok
    assert "immutable_successor" in r.violation


def test_immutable_successor_allows_metadata_field() -> None:
    r = validate_mutation_discipline(
        discipline=Discipline.IMMUTABLE_SUCCESSOR,
        field="status",
        role="promoted-pipelines",
        iri="iri://x",
        content_fields=frozenset({"pipeline_name"}),
    )
    assert r.ok


def test_append_only_with_lazy_inline_rejects_non_lazy_content() -> None:
    r = validate_mutation_discipline(
        discipline=Discipline.APPEND_ONLY_WITH_LAZY_INLINE,
        field="request_input_ref",
        role="episodic_memories",
        iri="iri://x",
        content_fields=frozenset({"request_input_ref"}),
        via_lazy_inline=False,
    )
    assert not r.ok


def test_append_only_with_lazy_inline_allows_lazy_inline_path() -> None:
    r = validate_mutation_discipline(
        discipline=Discipline.APPEND_ONLY_WITH_LAZY_INLINE,
        field="request_input_ref",
        role="episodic_memories",
        iri="iri://x",
        content_fields=frozenset({"request_input_ref"}),
        via_lazy_inline=True,
    )
    assert r.ok


def test_append_only_rejects_content_field() -> None:
    r = validate_mutation_discipline(
        discipline=Discipline.APPEND_ONLY,
        field="error_type",
        role="problem-trace",
        iri="iri://x",
        content_fields=frozenset({"error_type"}),
    )
    assert not r.ok


def test_audit_only_after_settled_rejects_settled_writes() -> None:
    r = validate_mutation_discipline(
        discipline=Discipline.AUDIT_ONLY_AFTER_SETTLED,
        field="status",
        role="pending-promotions",
        iri="iri://x",
        is_settled=True,
    )
    assert not r.ok


def test_audit_only_after_settled_allows_pre_settled_writes() -> None:
    r = validate_mutation_discipline(
        discipline=Discipline.AUDIT_ONLY_AFTER_SETTLED,
        field="status",
        role="pending-promotions",
        iri="iri://x",
        is_settled=False,
    )
    assert r.ok


def test_admin_authored_rejects_non_admin_writes() -> None:
    r = validate_mutation_discipline(
        discipline=Discipline.ADMIN_AUTHORED,
        field="dolce_label",
        role="ontology",
        iri="iri://x",
        is_admin=False,
    )
    assert not r.ok


def test_admin_authored_allows_admin_writes() -> None:
    r = validate_mutation_discipline(
        discipline=Discipline.ADMIN_AUTHORED,
        field="dolce_label",
        role="ontology",
        iri="iri://x",
        is_admin=True,
    )
    assert r.ok


def test_mutable_with_retention_allows_free_writes() -> None:
    r = validate_mutation_discipline(
        discipline=Discipline.MUTABLE_WITH_RETENTION,
        field="evidence_pointer",
        role="parameter-staging",
        iri="iri://x",
    )
    assert r.ok


def test_mutation_discipline_error_carries_metadata() -> None:
    err = MutationDisciplineError(
        iri="iri://x",
        role="promoted-pipelines",
        discipline="immutable_successor",
        field="pipeline_name",
        attempted_op="write_content",
        hint="mint successor IRI",
    )
    assert err.iri == "iri://x"
    assert err.role == "promoted-pipelines"
    assert err.discipline == "immutable_successor"
    assert err.field == "pipeline_name"
    assert err.attempted_op == "write_content"
    assert err.hint == "mint successor IRI"
    assert "immutable_successor" in str(err)
    assert "pipeline_name" in str(err)


def test_mutation_discipline_error_is_value_error_and_knowledge_error() -> None:
    err = MutationDisciplineError(
        iri="i",
        role="r",
        discipline="d",
        field="f",
        attempted_op="write_content",
        hint="h",
    )
    assert isinstance(err, ValueError)
    assert isinstance(err, KnowledgeError)
