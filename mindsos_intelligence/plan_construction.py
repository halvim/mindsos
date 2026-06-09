"""LifecyclePhase 2 — Plan + Pipeline construction (D-B22/B23, ADR-0171).

Dispatches ``planning.derive_initial_plan`` to seed a Plan, emits the root
Milestone + Plan, lazily decomposes (``planning.decompose`` -> [] at v0)
and tests leaves (``planning.is_leaf`` -> True at v0), then a v0
pipeline-finder emits one Pipeline per leaf Milestone. Cold-start
max-depth=3 (admin-tunable); v0's single-Milestone Plan never reaches it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from mindsos_capacity.builtins.planning_v0 import (
    DS_IS_LEAF,
    DS_MAPPING_RESULT,
    DS_MILESTONE,
    DS_MILESTONE_LIST,
    DS_PLAN,
)
from mindsos_capacity.identifiers import CATEGORY_PLANNING, capacity_iri

DERIVE_PLAN_IRI = capacity_iri(CATEGORY_PLANNING, "derive_initial_plan")
DECOMPOSE_IRI = capacity_iri(CATEGORY_PLANNING, "decompose")
IS_LEAF_IRI = capacity_iri(CATEGORY_PLANNING, "is_leaf")

MAX_DEPTH = 3


@dataclass
class PlanResult:
    plan_ref: str
    root_milestone_ref: str
    leaf_milestone_refs: List[str] = field(default_factory=list)
    pipeline_refs: Dict[str, str] = field(default_factory=dict)


def build(dispatcher, writer, mapping_result_ref, task_pattern_iri) -> PlanResult:
    # derive initial plan (v0: single-Milestone)
    dispatcher.dispatch(
        DERIVE_PLAN_IRI, {DS_MAPPING_RESULT: {"task_pattern_iri": task_pattern_iri}}
    )
    root = writer.emit_milestone("root", 0, is_leaf=True)
    plan = writer.emit_plan(root.iri, mapping_result_ref)

    # lazy decomposition + leaf detection (v0: root is the sole leaf)
    leaves = _decompose_recursive(dispatcher, writer, root, depth=0)

    pipelines: Dict[str, str] = {}
    for leaf_ref in leaves:
        pipe = writer.emit_pipeline(plan.iri, leaf_ref)
        pipelines[leaf_ref] = pipe.iri

    return PlanResult(
        plan_ref=plan.iri,
        root_milestone_ref=root.iri,
        leaf_milestone_refs=leaves,
        pipeline_refs=pipelines,
    )


def _decompose_recursive(dispatcher, writer, milestone, *, depth: int) -> List[str]:
    is_leaf = dispatcher.dispatch(IS_LEAF_IRI, {DS_MILESTONE: {}}).outputs[DS_IS_LEAF]
    if is_leaf or depth >= MAX_DEPTH:
        return [milestone.iri]
    children = dispatcher.dispatch(
        DECOMPOSE_IRI, {DS_MILESTONE: {}}
    ).outputs[DS_MILESTONE_LIST]
    leaves: List[str] = []
    for idx, _child_spec in enumerate(children):
        child = writer.emit_milestone(
            f"m{depth}.{idx}", idx, parent_ref=milestone.iri, is_leaf=False
        )
        leaves.extend(
            _decompose_recursive(dispatcher, writer, child, depth=depth + 1)
        )
    return leaves or [milestone.iri]


__all__ = ["build", "PlanResult", "MAX_DEPTH"]
