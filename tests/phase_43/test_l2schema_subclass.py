"""Phase 43 PR1 sentinel — ``L2Schema`` subclass shape + enum surface.

ADR-0153 §amendment-1 (L2Schema(Schema) subclass placement; required
``mutation_discipline``); ADR-0153 §1 (six-value ``Discipline``);
ADR-0151 §Decision (three-value ``StorageMode``); design log NPB14-3
single-field-invariant guard.
"""

from __future__ import annotations

import pytest

from mindsos_core import Schema
from mindsos_knowledge import (
    Discipline,
    L2Schema,
    StorageMode,
    build_alignment_schema,
    build_capacity_state_schema,
    build_concepts_schema,
    build_episodic_memories_schema,
    build_lexicon_schema,
    build_ontology_schema,
    build_problem_trace_schema,
    build_promoted_pipelines_schema,
    build_task_patterns_schema,
)


def test_l2schema_bases_is_schema_only() -> None:
    assert L2Schema.__bases__ == (Schema,)


def test_l2schema_constructor_requires_mutation_discipline() -> None:
    with pytest.raises(TypeError):
        L2Schema(strict=False)  # type: ignore[call-arg]


def test_l2schema_round_trip_defaults() -> None:
    s = L2Schema(mutation_discipline=Discipline.MUTABLE_WITH_RETENTION)
    assert s.mutation_discipline == Discipline.MUTABLE_WITH_RETENTION
    assert s.strict is False


def test_l2schema_round_trip_strict_true() -> None:
    s = L2Schema(
        mutation_discipline=Discipline.ADMIN_AUTHORED, strict=True
    )
    assert s.strict is True


_BUILDERS_AND_DISCIPLINES = (
    (build_ontology_schema, Discipline.ADMIN_AUTHORED),
    (build_lexicon_schema, Discipline.ADMIN_AUTHORED),
    (build_concepts_schema, Discipline.ADMIN_AUTHORED),
    (build_alignment_schema, Discipline.ADMIN_AUTHORED),
    (build_promoted_pipelines_schema, Discipline.IMMUTABLE_SUCCESSOR),
    (build_task_patterns_schema, Discipline.IMMUTABLE_SUCCESSOR),
    (
        build_episodic_memories_schema,
        Discipline.APPEND_ONLY_WITH_LAZY_INLINE,
    ),
    (build_problem_trace_schema, Discipline.APPEND_ONLY),
    (build_capacity_state_schema, Discipline.MUTABLE_WITH_RETENTION),
)


@pytest.mark.parametrize("builder,expected", _BUILDERS_AND_DISCIPLINES)
def test_all_9_builders_return_l2schema_with_expected_discipline(
    builder, expected
) -> None:
    s = builder()
    assert isinstance(s, L2Schema)
    assert s.mutation_discipline == expected


def test_discipline_enum_has_six_values() -> None:
    assert len(Discipline) == 6
    expected = {
        "immutable_successor",
        "append_only_with_lazy_inline",
        "mutable_with_retention",
        "audit_only_after_settled",
        "admin_authored",
        "append_only",
    }
    assert {d.value for d in Discipline} == expected


def test_storage_mode_enum_three_values() -> None:
    assert len(StorageMode) == 3
    assert StorageMode.INLINE.value == "inline"
    assert StorageMode.FALKOR_BLOB.value == "falkor_blob"
    assert StorageMode.BLOB_REF.value == "blob_ref"


def test_l2schema_adds_exactly_mutation_discipline_beyond_schema() -> None:
    """NPB14-3 single-field invariant guard.

    ``L2Schema`` instances must add exactly one attribute
    (``mutation_discipline``) beyond what ``Schema`` instances carry —
    future field additions require an ADR amendment.
    """
    schema_attrs = set(Schema(strict=False).__dict__)
    l2_attrs = set(
        L2Schema(
            mutation_discipline=Discipline.MUTABLE_WITH_RETENTION
        ).__dict__
    )
    diff = l2_attrs - schema_attrs
    assert diff == {"mutation_discipline"}, (
        "L2Schema must add exactly 'mutation_discipline' beyond Schema; "
        f"found extras: {diff!r}"
    )
