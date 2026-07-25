"""LifecyclePhase 2 — Plan + Pipeline construction (D-B22/B23, ADR-0171).

Dispatches ``planning.derive_initial_plan`` to seed a Plan, emits the root
Milestone + Plan, lazily decomposes (``planning.decompose`` -> [] at v0)
and tests leaves (``planning.is_leaf`` -> True at v0), then a v0
pipeline-finder emits one Pipeline per leaf Milestone. Cold-start
max-depth=3 (admin-tunable); v0's single-Milestone Plan never reaches it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

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
    #: The DataState endpoints of the solve pipeline the leaf(s) run, read from
    #: the planner's ``planning.plan`` output (out-of-CR Step 5). ``None`` when
    #: the plan names none — the v0 placeholder planner does, so the v0 path is
    #: unchanged (``execution.run`` emits the notional record). A real consumer's
    #: ``derive_initial_plan`` (e.g. arc, seeing ``resolved_reference``) names
    #: ``{"start_datastate", "target_datastate"}``; ``execution.run`` then finds
    #: + runs a real pipeline (single-leaf scope at v1; multi-leaf target routing
    #: is deferred with real decomposition / WSD).
    solve_target: Optional[Dict[str, str]] = None
    #: Optional per-leaf solve endpoints ``{leaf_ref: {start_datastate,
    #: target_datastate}}`` for a multi-stage plan whose leaves form a value
    #: chain (collection-iteration Slice 1a — ``execution.run`` threads a leaf's
    #: outputs to a downstream leaf's start via the run blackboard). A leaf with
    #: no entry falls back to the plan-global ``solve_target``; ``None``/absent →
    #: today's single-target behaviour (v0 + Step-5 single-leaf path unchanged).
    #: The map/fold fan-out that populates this for real rides Slice 1b + arc's
    #: planner; the v0 builder below never sets it.
    leaf_targets: Optional[Dict[str, Dict[str, str]]] = None
    #: Slice 1b — per-milestone map/fold spec the executor interprets. Maps a
    #: milestone ref to a kind descriptor: a ``map`` node
    #: (``{"kind": "map", "collection_ds", "member_ds", "sub_target",
    #: "out_ds"}``) fans a uniform sub-plan over the ordered members of a
    #: collection DataState (ADR-0199) and writes their ordered ``sub_target``
    #: outputs to ``out_ds``; a ``fold`` node (``{"kind": "fold",
    #: "reducer_iri", "in_ds"}``) dispatches an L3 reducer over that ordered
    #: list. A ref absent from this map is a plain leaf (v0 / Slice-1a path,
    #: unchanged). Emitted by the consumer's planner (arc's
    #: ``derive_initial_plan`` shadow), not by core (locked decision 3).
    milestone_specs: Optional[Dict[str, Dict[str, Any]]] = None


def _read_solve_target(plan_out: Any) -> Optional[Dict[str, str]]:
    """Extract the solve pipeline's ``{start,target}`` DataState endpoints from
    the planner's ``planning.plan`` output, or ``None``.

    Tolerant by construction: a v0 plan (or any plan without a well-formed
    ``solve_target`` naming both a non-empty ``start_datastate`` and
    ``target_datastate``) yields ``None`` → the notional-record fallback."""
    if not isinstance(plan_out, Mapping):
        return None
    st = plan_out.get("solve_target")
    if not isinstance(st, Mapping):
        return None
    start = st.get("start_datastate")
    target = st.get("target_datastate")
    if not start or not target:
        return None
    return {"start_datastate": start, "target_datastate": target}


def build(
    dispatcher, writer, mapping_result_ref, task_pattern_iri, *,
    resolved_reference: Any = None,
) -> PlanResult:
    # Derive initial plan (v0: single-Milestone). ``resolved_reference`` (Step
    # 5.1 / Phase-1→2 drop fix) rides the already-declared ``DS_MAPPING_RESULT``
    # value dict — no new declared input, so the strict ``_validate_inputs``
    # contract is untouched and the v0 body (reads only ``task_pattern_iri``)
    # ignores it. The planner's output is no longer discarded: its
    # ``solve_target`` (when present) tells ``execution.run`` what pipeline to
    # find + run.
    plan_out = dispatcher.dispatch(
        DERIVE_PLAN_IRI,
        {DS_MAPPING_RESULT: {
            "task_pattern_iri": task_pattern_iri,
            "resolved_reference": resolved_reference,
        }},
    ).outputs.get(DS_PLAN)
    solve_target = _read_solve_target(plan_out)
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
        solve_target=solve_target,
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
