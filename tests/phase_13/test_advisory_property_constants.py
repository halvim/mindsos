"""Phase 13 PB-8 — advisory module-level property constants.

The upper-layer schemas declare their per-NodeType properties as
module-level ``frozenset`` constants, NOT inside ``NodeType.property_types``
(which would require committing to ``PropertyType`` enum values
without a real consumer). Strict-tighten phase converts to typed
declarations.

**Phase 39 rename (ADR-0044 §am-3 + design log PB-R1-B):** the
former ``MEMORY_PROPS`` constant was dropped from the Phase 39
``episodic_memories`` schema. Properties for Episode + Memory composite
NodeTypes land at Phase 43 alongside CONTENT_FIELDS / METADATA_FIELDS /
mutation_discipline apparatus per ADR-0153 / ADR-0152 (Rail A schema-v2).

**Phase 43 schema-v2 update (ADR-0152 §1 + §2):** Pipeline + TaskPattern
PROPS sets expanded from Phase 13 advisory shape to full v2 field set
(union of ``*_CONTENT_FIELDS`` + ``*_METADATA_FIELDS``). ``task_type``
dropped from both (Pipeline never had a real ``task_type``; TaskPattern
``task_type`` renamed to ``pattern_name`` per ADR-0152 §2).
``confidence`` dropped from Pipeline per ADR-0094 §am-1 (migrates to
ALS subsystems); kept on TaskPattern as metadata.
"""

from __future__ import annotations

from mindsos_knowledge.schemas.capacity_state import CAPACITY_SNAPSHOT_PROPS
from mindsos_knowledge.schemas.problem_trace import PROBLEM_TRACE_ENTRY_PROPS
from mindsos_knowledge.schemas.promoted_pipelines import (
    PIPELINE_PROPS,
    PIPELINE_STEP_PROPS,
)
from mindsos_knowledge.schemas.task_patterns import (
    SUBGOAL_TEMPLATE_PROPS,
    TASK_PATTERN_PROPS,
)


def test_pipeline_props_declare_design_properties() -> None:
    # Per DESIGN_UPPER_LAYER_ROLES.md §2.1 + Phase 43 schema-v2
    # expansion (ADR-0152 §1). ``task_type`` never had a real
    # consumer (Phase 13 advisory only); ``confidence`` dropped per
    # ADR-0094 §am-1 (migrates to ALS subsystems on
    # ``learned-parameters``).
    assert isinstance(PIPELINE_PROPS, frozenset)
    assert {"pipeline_name", "edge_sequence", "status", "n_runs"} <= PIPELINE_PROPS
    assert "task_type" not in PIPELINE_PROPS
    assert "confidence" not in PIPELINE_PROPS


def test_pipeline_step_props_declare_design_properties() -> None:
    assert isinstance(PIPELINE_STEP_PROPS, frozenset)
    assert {"capacity_iri", "input_datastate", "output_datastate", "position"} <= PIPELINE_STEP_PROPS


def test_task_pattern_props_declare_design_properties() -> None:
    # Phase 13 advisory ``task_type`` renamed to ``pattern_name`` per
    # ADR-0152 §2 schema-v2 expansion; ``n_observations`` +
    # ``confidence`` (metadata) preserved per ADR-0152 §2.
    assert {"pattern_name", "n_observations", "confidence"} <= TASK_PATTERN_PROPS
    assert "task_type" not in TASK_PATTERN_PROPS


def test_subgoal_template_props_is_frozenset() -> None:
    assert isinstance(SUBGOAL_TEMPLATE_PROPS, frozenset)


def test_problem_trace_entry_props_declare_design_properties() -> None:
    assert {"capacity_iri", "request_id", "error_type", "error_message"} <= PROBLEM_TRACE_ENTRY_PROPS


def test_capacity_snapshot_props_declare_design_properties() -> None:
    assert {"capacity_iri", "user_id", "taken_at", "state_blob"} <= CAPACITY_SNAPSHOT_PROPS
