"""Phase 13 PB-8 — advisory module-level property constants.

The 5 upper-layer schemas declare their per-NodeType properties as
module-level ``frozenset`` constants, NOT inside ``NodeType.property_types``
(which would require committing to ``PropertyType`` enum values
without a real consumer). Strict-tighten phase converts to typed
declarations.
"""

from __future__ import annotations

from mindsos_knowledge.schemas.capacity_state import CAPACITY_SNAPSHOT_PROPS
from mindsos_knowledge.schemas.memories import MEMORY_PROPS
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
    # Per DESIGN_UPPER_LAYER_ROLES.md §2.1.
    assert isinstance(PIPELINE_PROPS, frozenset)
    assert {"pipeline_name", "task_type", "confidence", "n_runs"} <= PIPELINE_PROPS


def test_pipeline_step_props_declare_design_properties() -> None:
    assert isinstance(PIPELINE_STEP_PROPS, frozenset)
    assert {"capacity_iri", "input_datastate", "output_datastate", "position"} <= PIPELINE_STEP_PROPS


def test_task_pattern_props_declare_design_properties() -> None:
    assert {"task_type", "n_observations", "confidence"} <= TASK_PATTERN_PROPS


def test_subgoal_template_props_is_frozenset() -> None:
    assert isinstance(SUBGOAL_TEMPLATE_PROPS, frozenset)


def test_memory_props_declare_design_properties() -> None:
    assert {"task_id", "task_type", "user_id", "completed_at", "result"} <= MEMORY_PROPS


def test_problem_trace_entry_props_declare_design_properties() -> None:
    assert {"capacity_iri", "task_id", "error_type", "error_message"} <= PROBLEM_TRACE_ENTRY_PROPS


def test_capacity_snapshot_props_declare_design_properties() -> None:
    assert {"capacity_iri", "user_id", "taken_at", "state_blob"} <= CAPACITY_SNAPSHOT_PROPS
