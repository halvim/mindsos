"""L4 orchestrator — six-phase task lifecycle driver (ADR-0171, D12).

Drives a task through LifecyclePhase 1->6 on the dequeuing worker thread
(no separate orchestrator thread — Phase-46 substrate is worker-per-task).
The lifecycle is enqueued as a closure (``run_lifecycle``); capacity
invocations route through the L4 ``L4Dispatcher`` (CapacityContext build +
write-gate), and every reasoning step emits a chain artifact into
intelligence-MM under the MM writer lock.

Phase 47 runs over the v0 catalogs; real catalogs ship in WSD
installation. Consolidation (Phase 5 -> completion) is a stub seam here;
the real MM-freeze + Episode write lands at Phase 48.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Optional

from mindsos_capacity.builtins.orchestration_v0 import DS_SCORE, DS_SCORE_INPUT
from mindsos_capacity.identifiers import CATEGORY_SCORING, capacity_iri
from mindsos_capacity.tiers import TierEnum

from . import execution, phase_1, phase_6, plan_construction, replan_check, sufficient_predicate
from .chain_artifacts import ChainArtifactWriter

ATTENTION_SCORE_IRI = capacity_iri(CATEGORY_SCORING, "attention_score")

DEFAULT_PER_TASK_REPLAN_BUDGET = 5


class LifecyclePhase(IntEnum):
    INTERPRETATION = 1
    PLAN_CONSTRUCTION = 2
    EXECUTION = 3  # 3-5 collapsed (sibling-sequential v1)
    DIAGNOSIS = 6


@dataclass
class TaskOutcome:
    status: str  # succeeded | dont_know | aborted
    task_run_ref: str
    outcome: Any = None
    dont_know_reason: Optional[str] = None
    blame: Any = None
    replans_used: int = 0


class Orchestrator:
    def __init__(
        self,
        dispatcher,
        mm,
        *,
        task_scope: str = "task",
        per_task_replan_budget: int = DEFAULT_PER_TASK_REPLAN_BUDGET,
        simplified: bool = False,
    ) -> None:
        self._dispatcher = dispatcher
        self._mm = mm
        self._task_scope = task_scope
        self._budget = per_task_replan_budget
        self._simplified = simplified

    # ── attention-score write-through (PB-6 / D32.5c.4) ────────────────

    def update_priority(self, task_run, *, tier=TierEnum.FOREGROUND, executor=None, task_id=None) -> int:
        """Invoke L3 ``scoring.attention_score`` and write the result to the
        queue (if an executor is given) AND through to ``TaskRun.attention_
        score`` under the MM writer lock (atomic, D32.5c.4)."""
        score = self._dispatcher.dispatch(
            ATTENTION_SCORE_IRI, {DS_SCORE_INPUT: tier}
        ).outputs[DS_SCORE]
        with self._mm.lock.write_locked():
            task_run.attention_score = score
        if executor is not None and task_id is not None:
            executor.write_priority(task_id, score=score, tier=tier)
        return score

    # ── six-phase lifecycle ────────────────────────────────────────────

    def run_lifecycle(self, task_input, *, tier=TierEnum.FOREGROUND, executor=None, task_id=None) -> TaskOutcome:
        writer = ChainArtifactWriter(self._mm, self._task_scope)

        # Phase 1 — task interpretation (HintSet + MappingResult)
        p1 = phase_1.run(self._dispatcher, writer, task_input)

        # Phase 2 — Plan + Pipeline construction
        plan_result = plan_construction.build(
            self._dispatcher, writer, p1.mapping_result_ref, p1.task_pattern_iri
        )

        # TaskRun wraps the whole execution (Level 6)
        task_run = writer.emit_task_run(plan_ref=plan_result.plan_ref)
        self.update_priority(task_run, tier=tier, executor=executor, task_id=task_id)

        # Phase 3-5 — execution with bounded replan (invalidate-at-and-below)
        replans = 0
        sufficient = True
        while True:
            execution.run(self._dispatcher, writer, plan_result, task_run)
            if self._simplified:
                break
            sufficient = sufficient_predicate.evaluate(self._dispatcher)
            verdict = replan_check.check(self._dispatcher)
            if verdict.decision == "abort":
                writer.emit_replan_record("pipeline", verdict)
                task_run.status = "aborted"
                return TaskOutcome("aborted", task_run.iri, replans_used=replans)
            if verdict.decision == "replan" and replans < self._budget:
                replans += 1
                invalidated = replan_check.invalidate_at_and_below(task_run, "pipeline")
                writer.emit_replan_record(
                    "pipeline", verdict, invalidated_refs=invalidated
                )
                continue
            break

        # Phase 6 — failure diagnosis on the dont-know path
        if not self._simplified and not sufficient:
            blame = phase_6.diagnose(self._dispatcher)
            task_run.status = "failed"
            return TaskOutcome(
                "dont_know",
                task_run.iri,
                dont_know_reason="INSUFFICIENT",
                blame=blame,
                replans_used=replans,
            )

        # Phase 5 -> completion: consolidation is a stub seam (Phase 48).
        task_run.status = "completed"
        return TaskOutcome(
            "succeeded", task_run.iri, outcome=p1.task_pattern_iri, replans_used=replans
        )


__all__ = ["Orchestrator", "TaskOutcome", "LifecyclePhase", "DEFAULT_PER_TASK_REPLAN_BUDGET"]
