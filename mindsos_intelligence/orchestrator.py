"""L4 orchestrator — six-phase task lifecycle driver (ADR-0171, D12).

Drives a task through LifecyclePhase 1->6 on the dequeuing worker thread
(no separate orchestrator thread — Phase-46 substrate is worker-per-task).
The lifecycle is enqueued as a closure (``run_lifecycle``); capacity
invocations route through the L4 ``L4Dispatcher`` (CapacityContext build +
write-gate), and every reasoning step emits a chain artifact into
intelligence-MM under the MM writer lock.

Phase 47 ran over the v0 catalogs; real catalogs ship in WSD installation.
Consolidation (Phase 5 -> completion) is **wired at Phase 48** (ADR-0176):
on every terminal path (success / dont-know / abort) the MM is frozen and an
Episode is written to L2 ``episodic_memories`` via ``consolidate:mm``
(retain-by-default; gracefully skipped in simplified mode or when no
consolidate capacity / KL is wired — e.g. the v0 smoke).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Optional

from mindsos_capacity.builtins.orchestration_v0 import DS_SCORE, DS_SCORE_INPUT
from mindsos_capacity.identifiers import CATEGORY_SCORING, capacity_iri
from mindsos_capacity.needs_input import NeedsInput
from mindsos_capacity.tiers import TierEnum

from . import (
    consolidation,
    crash_recovery,
    execution,
    phase_1,
    phase_6,
    plan_construction,
    replan_check,
    sufficient_predicate,
)
from .chain_artifacts import ChainArtifactWriter

# Episode ``outcome_classification`` (Chat B §4.3 enum) by TaskRun status.
_OUTCOME_BY_STATUS = {
    "aborted": "failed",
    "failed": "dont_know",
    "completed": "succeeded",
}

ATTENTION_SCORE_IRI = capacity_iri(CATEGORY_SCORING, "attention_score")

DEFAULT_PER_TASK_REPLAN_BUDGET = 5


class LifecyclePhase(IntEnum):
    INTERPRETATION = 1
    PLAN_CONSTRUCTION = 2
    EXECUTION = 3  # 3-5 collapsed (sibling-sequential v1)
    DIAGNOSIS = 6


@dataclass
class TaskOutcome:
    status: str  # succeeded | dont_know | aborted | pending_confirmation
    task_run_ref: Optional[str]  # None on the pending_confirmation path (no TaskRun yet)
    outcome: Any = None
    dont_know_reason: Optional[str] = None
    blame: Any = None
    replans_used: int = 0
    # ADR-0196 — non-terminal clarification request. Orthogonal to the three
    # terminal statuses + the ``_OUTCOME_BY_STATUS`` consolidation map (both
    # untouched); when set, the lifecycle short-circuited at Phase 1 and did
    # NOT consolidate. ``status`` carries the non-terminal
    # ``"pending_confirmation"`` marker (never a key in the consolidation map).
    pending_confirmation: Any = None


class Orchestrator:
    def __init__(
        self,
        dispatcher,
        mm,
        *,
        task_scope: str = "task",
        per_task_replan_budget: int = DEFAULT_PER_TASK_REPLAN_BUDGET,
        simplified: bool = False,
        checkpoint_store: Any = None,
        mm_persister: Any = None,
    ) -> None:
        self._dispatcher = dispatcher
        self._mm = mm
        self._task_scope = task_scope
        self._budget = per_task_replan_budget
        self._simplified = simplified
        self._checkpoint_store = checkpoint_store
        # DQ-8 / CR#4 — narrow MM persister (``persist(metagraph, graph)``);
        # None = live-only (ephemeral / no Falkor client). Injected at boot.
        self._mm_persister = mm_persister
        # Per-orchestrator counter for the task-unique writer scope when a
        # caller supplies no task_id. Guarded — run_lifecycle runs on
        # concurrent worker threads.
        self._lifecycle_seq = 0
        self._seq_lock = threading.Lock()

    def _writer_scope(self, task_id) -> str:
        """A task-UNIQUE chain-writer scope (DQ-8 / CR#4). ``task_id`` when the
        caller supplies one; else a per-orchestrator counter. This uniqueness
        is what keeps two tasks' chain IRIs — and thus their ``episode_id``s —
        from colliding in one resident session."""
        if task_id is not None:
            return f"{self._task_scope}:{task_id}"
        with self._seq_lock:
            self._lifecycle_seq += 1
            return f"{self._task_scope}:auto{self._lifecycle_seq}"

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

    # ── consolidation seam (Phase 5 -> completion; ADR-0176) ───────────

    def _consolidate(
        self, task_run, task_pattern_iri, task_id=None, writer=None,
        capacity_graphs=None,
    ) -> None:
        """Freeze the MM + write the Episode on a terminal path (retain-by-
        default). No-op in simplified mode; graceful skip when unwired. Clears
        the crash-recovery checkpoint on completion (ADR-0179). Persists this
        task's chain graph and points ``mm_root_ref`` at it (DQ-8 / CR#4).

        ``capacity_graphs`` (Step 5.4): this task's per-run ``capacity_mm``
        grounding graphs. When supplied (a real solve run) and a persister is
        wired, Slice-B persist writes them + a task-level index and points the
        Episode's ``capacity_root_ref`` at it — non-inert. Empty / ``None``
        (v0, notional runs) leaves ``capacity_root_ref`` ``None``. Per-DataState
        ``encode`` hints are a brain follow-up (PB-1); with none supplied every
        grounded value must already be codec-safe (primitive/dict/list)."""
        if self._simplified:
            return
        consolidation.consolidate_task(
            self._dispatcher,
            self._mm,
            task_run,
            task_pattern_iri=task_pattern_iri,
            outcome_classification=_OUTCOME_BY_STATUS.get(task_run.status, "failed"),
            chain_graph=writer.chain_graph() if writer is not None else None,
            mm_persister=self._mm_persister,
            capacity_graphs=capacity_graphs or None,
        )
        if self._checkpoint_store is not None and task_id is not None:
            self._checkpoint_store.mark_consolidated(task_id)

    def _checkpoint(self, task_id, **fields) -> None:
        """Record a crash-recovery checkpoint at a D-B50 trigger (no-op when no
        store is configured or the task is anonymous)."""
        if self._checkpoint_store is None or task_id is None:
            return
        crash_recovery.record_checkpoint(
            self._checkpoint_store, task_id=task_id, **fields
        )

    # ── six-phase lifecycle ────────────────────────────────────────────

    def run_lifecycle(self, task_input, *, tier=TierEnum.FOREGROUND, executor=None, task_id=None) -> TaskOutcome:
        # Task-unique scope (DQ-8): drives both the chain-writer graph and the
        # capacity grounding run's task_id / run refs (Step 5), so a task with
        # no explicit ``task_id`` still grounds into an isolated per-run graph.
        scope = self._writer_scope(task_id)
        writer = ChainArtifactWriter(self._mm, scope)

        task_input_ref = f"taskinput:{task_id}" if task_id is not None else None

        # Phase 1 — task interpretation (HintSet + MappingResult)
        p1 = phase_1.run(self._dispatcher, writer, task_input)
        # ADR-0196 — interpretation asked the user. Short-circuit into a
        # non-terminal pending_confirmation outcome BEFORE plan/exec: no
        # TaskRun, no consolidation, terminal invariants untouched. (The
        # mid-execution needs_input path — execution.run halt+bubble — is
        # deferred, L4-25.)
        if isinstance(p1, NeedsInput):
            return TaskOutcome(
                status="pending_confirmation",
                task_run_ref=None,
                pending_confirmation=p1,
            )
        self._checkpoint(
            task_id, last_phase="INTERPRETATION", task_input_ref=task_input_ref
        )

        # Phase 2 — Plan + Pipeline construction. Thread the Phase-1
        # ``resolved_reference`` (Step 5.1 drop fix) so the planner can name a
        # solve target against the resolved task.
        plan_result = plan_construction.build(
            self._dispatcher, writer, p1.mapping_result_ref, p1.task_pattern_iri,
            resolved_reference=p1.resolved_reference,
        )
        self._checkpoint(
            task_id,
            last_phase="PLAN_CONSTRUCTION",
            task_input_ref=task_input_ref,
            task_pattern_iri=p1.task_pattern_iri,
        )

        # TaskRun wraps the whole execution (Level 6)
        task_run = writer.emit_task_run(plan_ref=plan_result.plan_ref)
        self.update_priority(task_run, tier=tier, executor=executor, task_id=task_id)

        # Step 5 — solve seed + capacity-graph collection. When the plan names a
        # ``solve_target`` (a real consumer, not v0) and we're not in simplified
        # mode, seed the resolved task at the pipeline's start DataState and let
        # ``execution.run`` ground + run the real pipeline into ``capacity_mm``.
        # ``capacity_graphs`` accumulates each real run's grounding graph (incl.
        # replan re-runs) for Slice-B persistence at consolidation.
        solve_target = None if self._simplified else getattr(
            plan_result, "solve_target", None
        )
        solve_seed = (
            {solve_target["start_datastate"]: p1.resolved_reference}
            if solve_target is not None else None
        )
        capacity_graphs: list = []

        # Phase 3-5 — execution with bounded replan (invalidate-at-and-below)
        replans = 0
        sufficient = True
        while True:
            execution.run(
                self._dispatcher, writer, plan_result, task_run,
                mm=self._mm, run_scope=scope, solve_seed=solve_seed,
                capacity_graphs=capacity_graphs, run_attempt=replans,
            )
            if self._simplified:
                break
            sufficient = sufficient_predicate.evaluate(self._dispatcher)
            verdict = replan_check.check(self._dispatcher)
            if verdict.decision == "abort":
                writer.emit_replan_record("pipeline", verdict)
                task_run.status = "aborted"
                self._consolidate(
                    task_run, p1.task_pattern_iri, task_id, writer, capacity_graphs
                )
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
            self._consolidate(
                task_run, p1.task_pattern_iri, task_id, writer, capacity_graphs
            )
            return TaskOutcome(
                "dont_know",
                task_run.iri,
                dont_know_reason="INSUFFICIENT",
                blame=blame,
                replans_used=replans,
            )

        # Phase 5 -> completion: freeze MM + write Episode (ADR-0176).
        task_run.status = "completed"
        self._consolidate(
            task_run, p1.task_pattern_iri, task_id, writer, capacity_graphs
        )
        return TaskOutcome(
            "succeeded", task_run.iri, outcome=p1.task_pattern_iri, replans_used=replans
        )


__all__ = ["Orchestrator", "TaskOutcome", "LifecyclePhase", "DEFAULT_PER_TASK_REPLAN_BUDGET"]
