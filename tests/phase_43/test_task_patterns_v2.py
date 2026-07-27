"""Phase 43 PR2 — request-patterns schema v2.

Per ADR-0152 §2: 13-field RequestPattern schema (flat). ``confidence``
KEPT (metadata); ``task_type`` renamed to ``pattern_name`` (content).
"""

from __future__ import annotations

from mindsos_knowledge.schemas import build_request_patterns_schema
from mindsos_knowledge.schemas._base import Discipline
from mindsos_knowledge.schemas.request_patterns import (
    REQUEST_PATTERN_CONTENT_FIELDS,
    REQUEST_PATTERN_METADATA_FIELDS,
    REQUEST_PATTERN_PROPS,
)


def test_task_pattern_props_has_13_fields() -> None:
    assert len(REQUEST_PATTERN_PROPS) == 13


def test_confidence_kept_as_metadata() -> None:
    """ADR-0152 §2: per-pattern confidence kept on RequestPattern."""
    assert "confidence" in REQUEST_PATTERN_METADATA_FIELDS
    assert "confidence" not in REQUEST_PATTERN_CONTENT_FIELDS


def test_pattern_name_in_content_partition() -> None:
    """Phase 13 ``task_type`` renamed to ``pattern_name`` per ADR-0152 §2."""
    assert "pattern_name" in REQUEST_PATTERN_CONTENT_FIELDS
    assert "task_type" not in REQUEST_PATTERN_PROPS


def test_paired_pipelines_in_content_partition() -> None:
    """D-L2-7 + PB-R3-21: paired_pipelines is source-of-truth on
    request-patterns (content)."""
    assert "paired_pipelines" in REQUEST_PATTERN_CONTENT_FIELDS


def test_timestamps_in_metadata_partition() -> None:
    """ADR-0152 §2 timestamps: 13 = 11 listed fields + 2 timestamps."""
    assert "created_at" in REQUEST_PATTERN_METADATA_FIELDS
    assert "last_updated_at" in REQUEST_PATTERN_METADATA_FIELDS


def test_task_pattern_discipline_is_immutable_successor() -> None:
    s = build_request_patterns_schema()
    assert s.mutation_discipline == Discipline.IMMUTABLE_SUCCESSOR
