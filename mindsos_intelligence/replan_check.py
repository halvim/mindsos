"""Replan-check dispatch + invalidate-at-and-below (D14 / D-B36 / ADR-0173).

L4 dispatches the L3 ``decision.should_replan`` capacity and acts on the
verdict: ``continue`` proceeds, ``replan`` invalidates chain artifacts at
and below the replan level (reusing upstream) and re-enters, ``abort``
ends the task. ReplanRecords are emitted sparsely (only replan/abort).
At Phase 47 the body is the v0 stub (test-configurable).
"""

from __future__ import annotations

from mindsos_capacity.builtins.orchestration_v0 import DS_REPLAN_STATE, DS_REPLAN_VERDICT
from mindsos_capacity.identifiers import CATEGORY_DECISION, capacity_iri

from .chain_artifacts import ReplanVerdict

SHOULD_REPLAN_IRI = capacity_iri(CATEGORY_DECISION, "should_replan")

REPLAN_LEVELS = ("hint", "map", "plan", "plan_subtree", "pipeline")


def check(dispatcher, state=None) -> ReplanVerdict:
    result = dispatcher.dispatch(SHOULD_REPLAN_IRI, {DS_REPLAN_STATE: state or {}})
    v = result.outputs[DS_REPLAN_VERDICT]
    return ReplanVerdict(
        decision=v["decision"],
        verified=v.get("verified", True),
        divergence=v.get("divergence", 0.0),
    )


def invalidate_at_and_below(task_run, replan_level: str) -> list:
    """Return the chain refs invalidated at and below ``replan_level``.

    v0 (pipeline-level): the TaskRun's PipelineRuns are the at-and-below
    set; upstream Plan/Mapping/HintSet are reused. Returns the invalidated
    refs and clears them from the TaskRun so execution re-enters.
    """
    if replan_level not in REPLAN_LEVELS:
        raise ValueError(f"unknown replan_level {replan_level!r}")
    invalidated = list(task_run.pipeline_runs)
    task_run.pipeline_runs.clear()
    return invalidated


__all__ = ["check", "invalidate_at_and_below", "SHOULD_REPLAN_IRI", "REPLAN_LEVELS"]
