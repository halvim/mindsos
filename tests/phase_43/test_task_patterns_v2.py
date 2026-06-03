"""Phase 43 PR2 — task-patterns schema v2.

Per ADR-0152 §2: 13-field TaskPattern schema (flat). ``confidence``
KEPT (metadata); ``task_type`` renamed to ``pattern_name`` (content).
"""

from __future__ import annotations

from mindsos_knowledge.schemas import build_task_patterns_schema
from mindsos_knowledge.schemas._base import Discipline
from mindsos_knowledge.schemas.task_patterns import (
    TASK_PATTERN_CONTENT_FIELDS,
    TASK_PATTERN_METADATA_FIELDS,
    TASK_PATTERN_PROPS,
)


def test_task_pattern_props_has_13_fields() -> None:
    assert len(TASK_PATTERN_PROPS) == 13


def test_confidence_kept_as_metadata() -> None:
    """ADR-0152 §2: per-pattern confidence kept on TaskPattern."""
    assert "confidence" in TASK_PATTERN_METADATA_FIELDS
    assert "confidence" not in TASK_PATTERN_CONTENT_FIELDS


def test_pattern_name_in_content_partition() -> None:
    """Phase 13 ``task_type`` renamed to ``pattern_name`` per ADR-0152 §2."""
    assert "pattern_name" in TASK_PATTERN_CONTENT_FIELDS
    assert "task_type" not in TASK_PATTERN_PROPS


def test_paired_pipelines_in_content_partition() -> None:
    """D-L2-7 + PB-R3-21: paired_pipelines is source-of-truth on
    task-patterns (content)."""
    assert "paired_pipelines" in TASK_PATTERN_CONTENT_FIELDS


def test_timestamps_in_metadata_partition() -> None:
    """ADR-0152 §2 timestamps: 13 = 11 listed fields + 2 timestamps."""
    assert "created_at" in TASK_PATTERN_METADATA_FIELDS
    assert "last_updated_at" in TASK_PATTERN_METADATA_FIELDS


def test_task_pattern_discipline_is_immutable_successor() -> None:
    s = build_task_patterns_schema()
    assert s.mutation_discipline == Discipline.IMMUTABLE_SUCCESSOR
