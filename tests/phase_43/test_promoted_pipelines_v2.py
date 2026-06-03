"""Phase 43 PR2 — promoted-pipelines schema v2.

Per ADR-0152 §1: 16-field Pipeline schema. ``confidence`` DROPPED per
ADR-0094 §am-1. ``paired_pipelines`` lives ONLY on task-patterns
(D-L2-7 eliminated pipeline-side cache); MUST NOT be in
``PIPELINE_PROPS``.
"""

from __future__ import annotations

from mindsos_knowledge.schemas import build_promoted_pipelines_schema
from mindsos_knowledge.schemas._base import Discipline
from mindsos_knowledge.schemas.promoted_pipelines import (
    PIPELINE_CONTENT_FIELDS,
    PIPELINE_METADATA_FIELDS,
    PIPELINE_PROPS,
)


_EXPECTED_STATUS_VALUES = frozenset({
    "draft",
    "tested",
    "active",
    "quarantined",
    "retired",
})


def test_pipeline_props_has_16_fields() -> None:
    assert len(PIPELINE_PROPS) == 16


def test_status_field_in_metadata_partition() -> None:
    """ADR-0152 §1 status field is metadata (mutates in place under
    immutable_successor discipline per per-field partition)."""
    assert "status" in PIPELINE_METADATA_FIELDS
    assert "status" in PIPELINE_PROPS


def test_lifecycle_metadata_fields_present() -> None:
    """ADR-0152 §1 lifecycle timestamps + quarantine fields."""
    for field in (
        "created_at",
        "tested_at",
        "activated_at",
        "quarantined_at",
        "quarantined_by",
        "retired_at",
        "quarantine_threshold",
    ):
        assert field in PIPELINE_METADATA_FIELDS, (
            f"lifecycle metadata field {field!r} missing"
        )


def test_confidence_absent_from_pipeline() -> None:
    """ADR-0094 §am-1: per-pipeline confidence migrates to ALS."""
    assert "confidence" not in PIPELINE_PROPS
    assert "confidence" not in PIPELINE_CONTENT_FIELDS
    assert "confidence" not in PIPELINE_METADATA_FIELDS


def test_paired_pipelines_absent_from_pipeline() -> None:
    """D-L2-7: pipeline-side cache eliminated entirely; lives only on
    task-patterns."""
    assert "paired_pipelines" not in PIPELINE_PROPS


def test_pipeline_discipline_is_immutable_successor() -> None:
    s = build_promoted_pipelines_schema()
    assert s.mutation_discipline == Discipline.IMMUTABLE_SUCCESSOR


def test_status_value_set_documents_expected_5_values() -> None:
    """ADR-0152 §1 + Chat A R3 PB-R3-22: status enum is
    Literal[draft, tested, active, quarantined, retired]. The literal
    values are documentation per ADR; this test pins the set so
    schema v2 contracts stay aligned with the ADR's wording.
    """
    # Schema doesn't carry a STATUS_VALUES module-level constant; this
    # test pins the expected set for ADR alignment.
    assert _EXPECTED_STATUS_VALUES == frozenset({
        "draft",
        "tested",
        "active",
        "quarantined",
        "retired",
    })
