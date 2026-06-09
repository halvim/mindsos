"""LifecyclePhase 1 — task interpretation (5-step refactor, ADR-0172).

receive -> process -> extract_hints -> derive_goal -> map_to_task_pattern.
Each step dispatches its L3 v0 capacity; the phase emits HintSet (step 3)
and MappingResult (step 5) into intelligence-MM.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mindsos_capacity.builtins.phase1_v0 import (
    DS_GOAL,
    DS_HINT_SET,
    DS_MAPPING,
    DS_RAW_INPUT,
    DS_STRUCTURED_INPUT,
)
from mindsos_capacity.identifiers import (
    CATEGORY_DECISION,
    CATEGORY_HINT,
    CATEGORY_PROCESS,
    capacity_iri,
)

PROCESS_IRI = capacity_iri(CATEGORY_PROCESS, "identity")
HINT_IRI = capacity_iri(CATEGORY_HINT, "global")
DERIVE_GOAL_IRI = capacity_iri(CATEGORY_DECISION, "derive_goal")
MAP_IRI = capacity_iri(CATEGORY_DECISION, "map_to_task_pattern")


@dataclass
class Phase1Result:
    structured_input: Any
    hint_set_ref: str
    goal: Any
    task_pattern_iri: str
    mapping_confidence: float
    mapping_result_ref: str


def run(dispatcher, writer, task_input) -> Phase1Result:
    # step 2 — process
    structured = dispatcher.dispatch(
        PROCESS_IRI, {DS_RAW_INPUT: task_input}
    ).outputs[DS_STRUCTURED_INPUT]
    # step 3 — extract hints -> HintSet
    hints = dispatcher.dispatch(
        HINT_IRI, {DS_STRUCTURED_INPUT: structured}
    ).outputs[DS_HINT_SET]
    hint_set = writer.emit_hint_set(hints)
    # step 4 — derive goal
    goal = dispatcher.dispatch(
        DERIVE_GOAL_IRI, {DS_STRUCTURED_INPUT: structured, DS_HINT_SET: hints}
    ).outputs[DS_GOAL]
    # step 5 — map to task-pattern -> MappingResult
    mapping = dispatcher.dispatch(
        MAP_IRI,
        {DS_STRUCTURED_INPUT: structured, DS_HINT_SET: hints, DS_GOAL: goal},
    ).outputs[DS_MAPPING]
    mr = writer.emit_mapping_result(
        hint_set.iri, mapping["task_pattern_iri"], mapping["mapping_confidence"]
    )
    return Phase1Result(
        structured_input=structured,
        hint_set_ref=hint_set.iri,
        goal=goal,
        task_pattern_iri=mapping["task_pattern_iri"],
        mapping_confidence=mapping["mapping_confidence"],
        mapping_result_ref=mr.iri,
    )


__all__ = ["run", "Phase1Result"]
