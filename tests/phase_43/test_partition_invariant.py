"""Phase 43 PR1 sentinel — content/metadata partition invariant.

ADR-0153 §3 partition discipline + ADR-0152 §1 + §2 (Pipeline +
RequestPattern field cardinalities). Covers ``promoted_pipelines`` +
``request_patterns`` + ``problem_trace`` per design log §5.2.
"""

from __future__ import annotations

import pytest

from mindsos_knowledge.schemas.problem_trace import (
    PROBLEM_TRACE_ENTRY_CONTENT_FIELDS,
    PROBLEM_TRACE_ENTRY_METADATA_FIELDS,
    PROBLEM_TRACE_ENTRY_PROPS,
)
from mindsos_knowledge.schemas.promoted_pipelines import (
    PIPELINE_CONTENT_FIELDS,
    PIPELINE_METADATA_FIELDS,
    PIPELINE_PROPS,
)
from mindsos_knowledge.schemas.request_patterns import (
    REQUEST_PATTERN_CONTENT_FIELDS,
    REQUEST_PATTERN_METADATA_FIELDS,
    REQUEST_PATTERN_PROPS,
)
from mindsos_knowledge.validators import validate_partition_invariant


_TRIPLES = (
    (
        "Pipeline",
        PIPELINE_CONTENT_FIELDS,
        PIPELINE_METADATA_FIELDS,
        PIPELINE_PROPS,
        5,
        11,
    ),
    (
        "RequestPattern",
        REQUEST_PATTERN_CONTENT_FIELDS,
        REQUEST_PATTERN_METADATA_FIELDS,
        REQUEST_PATTERN_PROPS,
        5,
        8,
    ),
    (
        "ProblemTraceEntry",
        PROBLEM_TRACE_ENTRY_CONTENT_FIELDS,
        PROBLEM_TRACE_ENTRY_METADATA_FIELDS,
        PROBLEM_TRACE_ENTRY_PROPS,
        7,
        0,
    ),
)


@pytest.mark.parametrize(
    "name,content,metadata,props,expected_content_n,expected_metadata_n",
    _TRIPLES,
)
def test_partition_clean_and_cardinality(
    name, content, metadata, props, expected_content_n, expected_metadata_n
) -> None:
    assert len(content) == expected_content_n, (
        f"{name} content cardinality {len(content)} != expected "
        f"{expected_content_n} per ADR-0152"
    )
    assert len(metadata) == expected_metadata_n, (
        f"{name} metadata cardinality {len(metadata)} != expected "
        f"{expected_metadata_n} per ADR-0152"
    )
    assert content & metadata == frozenset(), (
        f"{name} content/metadata partition overlap: "
        f"{sorted(content & metadata)!r}"
    )
    assert content | metadata == props, (
        f"{name} content ∪ metadata != PROPS union"
    )
    r = validate_partition_invariant(
        content_fields=content,
        metadata_fields=metadata,
        all_fields=props,
    )
    assert r.ok, (
        f"{name} validate_partition_invariant failed: {r.violation}"
    )


def test_pipeline_confidence_dropped() -> None:
    """ADR-0094 §amendment-1: per-pipeline confidence migrates off Pipeline."""
    assert "confidence" not in PIPELINE_PROPS
    assert "confidence" not in PIPELINE_CONTENT_FIELDS
    assert "confidence" not in PIPELINE_METADATA_FIELDS


def test_task_pattern_confidence_kept_as_metadata() -> None:
    """ADR-0152 §2: per-pattern confidence kept on RequestPattern as metadata."""
    assert "confidence" in REQUEST_PATTERN_METADATA_FIELDS
    assert "confidence" not in REQUEST_PATTERN_CONTENT_FIELDS


def test_problem_trace_metadata_partition_empty() -> None:
    """ADR-0153 §1: ``append_only`` discipline ⇒ no mutable metadata partition."""
    assert PROBLEM_TRACE_ENTRY_METADATA_FIELDS == frozenset()
