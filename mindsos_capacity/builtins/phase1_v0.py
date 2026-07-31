"""Placeholder Phase-1 v0 catalog (Phase 47, ADR-0172 / PB-7).

The L4 orchestrator's LifecyclePhase 1 runs a 5-step flow (receive →
process → extract_hints → derive_goal → map_to_task_pattern). Its real L3
capacities (``process.*``, ``hint.*``, ``decision.derive_goal``, the
mapping subsystem) are unbuilt CORE work (RULES §8). Phase 47 ships trivial
placeholders so the trivial-task smoke runs the real 5-step control path:

- ``process.identity``           → structured == raw (passthrough).
- ``hint.global``                → empty global hint set.
- ``decision.derive_goal``       → a fixed trivial goal.
- ``decision.map_to_task_pattern`` → a fixed request-pattern + confidence 1.0.

All carry ``placeholder=True``; install is opt-in; CORE-C4R8 replaces. Bodies
are pure and context-agnostic.
"""

from __future__ import annotations

from typing import Any, List

from ..bootstrap import ensure_datastate_graph
from ..capacity import Capacity
from ..datastate import DataState, ShapeDescriptor
from ..exceptions import CapacityRegistrationError
from ..identifiers import (
    CATEGORY_DECISION,
    CATEGORY_HINT,
    CATEGORY_PROCESS,
    capacity_iri,
    datastate_iri,
)


DS_RAW_INPUT = datastate_iri("phase1.raw_input")
DS_STRUCTURED_INPUT = datastate_iri("phase1.structured_input")
DS_HINT_SET = datastate_iri("phase1.hint_set")
DS_GOAL = datastate_iri("phase1.goal")
DS_MAPPING = datastate_iri("phase1.mapping")

TRIVIAL_REQUEST_PATTERN_IRI = "request-pattern:v0:trivial"


def phase1_datastates() -> List[DataState]:
    return [
        DataState(
            name="phase1.raw_input",
            shape=ShapeDescriptor.opaque("phase1.raw_input"),
            description="Raw task input handed to Phase 1.",
            provenance_category=CATEGORY_PROCESS,
        ),
        DataState(
            name="phase1.structured_input",
            shape=ShapeDescriptor.opaque("phase1.structured_input"),
            description="Structured input after process.* step 2.",
            provenance_category=CATEGORY_PROCESS,
        ),
        DataState(
            name="phase1.hint_set",
            shape=ShapeDescriptor.opaque("phase1.hint_set"),
            description="Global hint set from step 3.",
            provenance_category=CATEGORY_HINT,
        ),
        DataState(
            name="phase1.goal",
            shape=ShapeDescriptor.opaque("phase1.goal"),
            description="Derived goal from step 4.",
            provenance_category=CATEGORY_DECISION,
        ),
        DataState(
            name="phase1.mapping",
            shape=ShapeDescriptor.opaque("phase1.mapping"),
            description="Task-pattern mapping result from step 5.",
            provenance_category=CATEGORY_DECISION,
        ),
    ]


def _process_identity(**kwargs: Any) -> dict:
    return {DS_STRUCTURED_INPUT: kwargs.get(DS_RAW_INPUT)}


def _hint_global(**kwargs: Any) -> dict:
    return {DS_HINT_SET: {}}


def _derive_goal(**kwargs: Any) -> dict:
    return {DS_GOAL: {"goal": "v0:trivial-goal"}}


def _map_to_request_pattern(**kwargs: Any) -> dict:
    return {
        DS_MAPPING: {
            "request_pattern_iri": TRIVIAL_REQUEST_PATTERN_IRI,
            "mapping_confidence": 1.0,
        }
    }


def build_process_identity() -> Capacity:
    return Capacity(
        name="identity",
        category=CATEGORY_PROCESS,
        inputs=(DS_RAW_INPUT,),
        outputs=(DS_STRUCTURED_INPUT,),
        implementation=_process_identity,
        description="v0 placeholder: passthrough raw -> structured.",
        placeholder=True,
    )


def build_hint_global() -> Capacity:
    return Capacity(
        name="global",
        category=CATEGORY_HINT,
        inputs=(DS_STRUCTURED_INPUT,),
        outputs=(DS_HINT_SET,),
        implementation=_hint_global,
        description="v0 placeholder: empty global hint set.",
        placeholder=True,
    )


def build_derive_goal() -> Capacity:
    return Capacity(
        name="derive_goal",
        category=CATEGORY_DECISION,
        inputs=(DS_STRUCTURED_INPUT, DS_HINT_SET),
        outputs=(DS_GOAL,),
        implementation=_derive_goal,
        description="v0 placeholder: trivial goal.",
        placeholder=True,
    )


def build_map_to_request_pattern() -> Capacity:
    return Capacity(
        name="map_to_task_pattern",
        category=CATEGORY_DECISION,
        inputs=(DS_STRUCTURED_INPUT, DS_HINT_SET, DS_GOAL),
        outputs=(DS_MAPPING,),
        implementation=_map_to_request_pattern,
        description="v0 placeholder: fixed request-pattern, confidence 1.0.",
        placeholder=True,
    )


_DS_IRIS = (
    DS_RAW_INPUT,
    DS_STRUCTURED_INPUT,
    DS_HINT_SET,
    DS_GOAL,
    DS_MAPPING,
)
_CAP_IRIS = (
    capacity_iri(CATEGORY_PROCESS, "identity"),
    capacity_iri(CATEGORY_HINT, "global"),
    capacity_iri(CATEGORY_DECISION, "derive_goal"),
    capacity_iri(CATEGORY_DECISION, "map_to_task_pattern"),
)


def install_phase1_v0(capacity_layer) -> None:
    mg = capacity_layer.global_metagraph()
    cap_index = capacity_layer._capacity_index[mg.metagraph_id]
    ds_graph = ensure_datastate_graph(mg, strict=capacity_layer._strict)

    ds_present = {iri for iri in _DS_IRIS if iri in ds_graph.nodes}
    cap_present = {iri for iri in _CAP_IRIS if iri in cap_index}
    present_total = len(ds_present) + len(cap_present)

    if present_total == len(_DS_IRIS) + len(_CAP_IRIS):
        return
    if present_total > 0:
        raise CapacityRegistrationError(
            "install_phase1_v0: partial install state detected — "
            f"datastates_present={sorted(ds_present)}, "
            f"capacities_present={sorted(cap_present)}"
        )
    for ds in phase1_datastates():
        capacity_layer.register_datastate(ds, allow_new_realm=True)
    capacity_layer.register_capacity(build_process_identity())
    capacity_layer.register_capacity(build_hint_global())
    capacity_layer.register_capacity(build_derive_goal())
    capacity_layer.register_capacity(build_map_to_request_pattern())


__all__ = [
    "DS_RAW_INPUT",
    "DS_STRUCTURED_INPUT",
    "DS_HINT_SET",
    "DS_GOAL",
    "DS_MAPPING",
    "TRIVIAL_REQUEST_PATTERN_IRI",
    "phase1_datastates",
    "build_process_identity",
    "build_hint_global",
    "build_derive_goal",
    "build_map_to_request_pattern",
    "install_phase1_v0",
]
