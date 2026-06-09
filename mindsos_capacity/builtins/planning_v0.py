"""Placeholder ``planning.*`` v0 catalog (Phase 47, ADR-0172 / PB-L).

Four placeholder capacities that let the L4 orchestrator build and walk a
Plan tree before the real planning catalog exists:

- ``planning.derive_initial_plan`` → single-Milestone Plan.
- ``planning.decompose``          → ``[]`` (no children).
- ``planning.is_leaf``            → ``True``.
- ``planning.aggregate_outputs``  → last-child-output.

Every capacity carries ``placeholder=True``. The install is **opt-in**
(never called by ``create_global`` bootstrap) — that opt-in discipline IS
the production guard: a bare system never holds these. WSD installation
atomically replaces this catalog with the real ``planning.*`` family.

The bodies are pure and context-agnostic (they ignore ``context``), so
they run identically whether dispatched with a legacy dict context or a
typed ``CapacityContext`` (ADR-0175 transitional window).
"""

from __future__ import annotations

from typing import Any, List

from ..bootstrap import ensure_datastate_graph
from ..capacity import Capacity
from ..datastate import DataState, ShapeDescriptor
from ..exceptions import CapacityRegistrationError
from ..identifiers import CATEGORY_PLANNING, capacity_iri, datastate_iri


DS_MAPPING_RESULT = datastate_iri("planning.mapping_result")
DS_PLAN = datastate_iri("planning.plan")
DS_MILESTONE = datastate_iri("planning.milestone")
DS_MILESTONE_LIST = datastate_iri("planning.milestone_list")
DS_IS_LEAF = datastate_iri("planning.is_leaf")
DS_CHILD_OUTPUTS = datastate_iri("planning.child_outputs")
DS_AGG_OUTPUT = datastate_iri("planning.aggregated_output")


def planning_datastates() -> List[DataState]:
    return [
        DataState(
            name="planning.mapping_result",
            shape=ShapeDescriptor.opaque("planning.mapping_result"),
            description="A MappingResult handed to plan derivation.",
            provenance_category=CATEGORY_PLANNING,
        ),
        DataState(
            name="planning.plan",
            shape=ShapeDescriptor.opaque("planning.plan"),
            description="A derived Plan (root Milestone + metadata).",
            provenance_category=CATEGORY_PLANNING,
        ),
        DataState(
            name="planning.milestone",
            shape=ShapeDescriptor.opaque("planning.milestone"),
            description="A single Milestone tree node.",
            provenance_category=CATEGORY_PLANNING,
        ),
        DataState(
            name="planning.milestone_list",
            shape=ShapeDescriptor.opaque("planning.milestone_list"),
            description="An ordered list of child Milestones.",
            provenance_category=CATEGORY_PLANNING,
        ),
        DataState(
            name="planning.is_leaf",
            shape=ShapeDescriptor.scalar("bool", opaque_tag="planning.is_leaf"),
            description="Leaf predicate result for a Milestone.",
            provenance_category=CATEGORY_PLANNING,
        ),
        DataState(
            name="planning.child_outputs",
            shape=ShapeDescriptor.opaque("planning.child_outputs"),
            description="Ordered child output DataStates to aggregate.",
            provenance_category=CATEGORY_PLANNING,
        ),
        DataState(
            name="planning.aggregated_output",
            shape=ShapeDescriptor.opaque("planning.aggregated_output"),
            description="Aggregated parent output DataState.",
            provenance_category=CATEGORY_PLANNING,
        ),
    ]


def _derive_initial_plan(**kwargs: Any) -> dict:
    mapping_result = kwargs.get(DS_MAPPING_RESULT)
    root = {
        "name": "root",
        "sequence_index": 0,
        "parent_ref": None,
        "is_leaf": True,
        "children": [],
    }
    return {
        DS_PLAN: {
            "root_milestone": root,
            "mapping_result": mapping_result,
            "single_milestone": True,
        }
    }


def _decompose(**kwargs: Any) -> dict:
    return {DS_MILESTONE_LIST: []}


def _is_leaf(**kwargs: Any) -> dict:
    return {DS_IS_LEAF: True}


def _aggregate_outputs(**kwargs: Any) -> dict:
    child_outputs = kwargs.get(DS_CHILD_OUTPUTS) or []
    last = child_outputs[-1] if child_outputs else None
    return {DS_AGG_OUTPUT: last}


def build_derive_initial_plan() -> Capacity:
    return Capacity(
        name="derive_initial_plan",
        category=CATEGORY_PLANNING,
        inputs=(DS_MAPPING_RESULT,),
        outputs=(DS_PLAN,),
        implementation=_derive_initial_plan,
        description="v0 placeholder: single-Milestone Plan.",
        placeholder=True,
    )


def build_decompose() -> Capacity:
    return Capacity(
        name="decompose",
        category=CATEGORY_PLANNING,
        inputs=(DS_MILESTONE,),
        outputs=(DS_MILESTONE_LIST,),
        implementation=_decompose,
        description="v0 placeholder: no children.",
        placeholder=True,
    )


def build_is_leaf() -> Capacity:
    return Capacity(
        name="is_leaf",
        category=CATEGORY_PLANNING,
        inputs=(DS_MILESTONE,),
        outputs=(DS_IS_LEAF,),
        implementation=_is_leaf,
        description="v0 placeholder: every Milestone is a leaf.",
        placeholder=True,
    )


def build_aggregate_outputs() -> Capacity:
    return Capacity(
        name="aggregate_outputs",
        category=CATEGORY_PLANNING,
        inputs=(DS_CHILD_OUTPUTS,),
        outputs=(DS_AGG_OUTPUT,),
        implementation=_aggregate_outputs,
        description="v0 placeholder: last-child-output.",
        placeholder=True,
    )


_DS_IRIS = (
    DS_MAPPING_RESULT,
    DS_PLAN,
    DS_MILESTONE,
    DS_MILESTONE_LIST,
    DS_IS_LEAF,
    DS_CHILD_OUTPUTS,
    DS_AGG_OUTPUT,
)
_CAP_IRIS = (
    capacity_iri(CATEGORY_PLANNING, "derive_initial_plan"),
    capacity_iri(CATEGORY_PLANNING, "decompose"),
    capacity_iri(CATEGORY_PLANNING, "is_leaf"),
    capacity_iri(CATEGORY_PLANNING, "aggregate_outputs"),
)


def install_planning_v0(capacity_layer) -> None:
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
            "install_planning_v0: partial install state detected — "
            f"datastates_present={sorted(ds_present)}, "
            f"capacities_present={sorted(cap_present)}"
        )
    for ds in planning_datastates():
        capacity_layer.register_datastate(ds, allow_new_realm=True)
    capacity_layer.register_capacity(build_derive_initial_plan())
    capacity_layer.register_capacity(build_decompose())
    capacity_layer.register_capacity(build_is_leaf())
    capacity_layer.register_capacity(build_aggregate_outputs())


__all__ = [
    "DS_MAPPING_RESULT",
    "DS_PLAN",
    "DS_MILESTONE",
    "DS_MILESTONE_LIST",
    "DS_IS_LEAF",
    "DS_CHILD_OUTPUTS",
    "DS_AGG_OUTPUT",
    "planning_datastates",
    "build_derive_initial_plan",
    "build_decompose",
    "build_is_leaf",
    "build_aggregate_outputs",
    "install_planning_v0",
]
