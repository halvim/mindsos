"""L4 orchestrator — six-phase task lifecycle driver (ADR-0171, D12).

Drives a task through LifecyclePhase 1->6 on the dequeuing worker thread
(no separate orchestrator thread — Phase-46 substrate is worker-per-task).
The lifecycle is enqueued as a closure (``run_lifecycle``); capacity
invocations route through the L4 ``L4Dispatcher`` (CapacityContext build +
write-gate), and every reasoning step emits a chain artifact into
intelligence-MM under the MM writer lock.

Phase 47 ran over the v0 catalogs; real catalogs ship in WSD installation.
Consolidation (Phase 5 -> completion) is **wired at Phase 48** (ADR-0176):
on every terminal path (success / dont-know / conceded) the MM is frozen and an
Episode is written to L2 ``episodic_memories`` via ``consolidate:mm``. Dream
PRE-0 Slice 1b makes the Episode a STREAMING record — opened ``state=open`` at
Request start, closed ``state=closed`` on the terminal decision (gracefully
skipped in simplified mode or when no consolidate capacity / KL is wired).
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Optional

from mindsos_capacity.builtins.orchestration_v0 import DS_SCORE, DS_SCORE_INPUT
from mindsos_capacity.identifiers import CATEGORY_SCORING, capacity_iri
from mindsos_capacity.needs_input import NeedsInput
from mindsos_capacity.tiers import TierEnum

from . import (
    consolidation,
    execution,
    phase_1,
    phase_6,
    plan_construction,
    replan_check,
    request_input_persister,
    sufficient_predicate,
)
from .chain_artifacts import ChainArtifactWriter
from .capacity_persister import CapacityStreamSink
from .ingress import InputEnvelope
from mindsos_core.exceptions import PersistenceError

# Episode ``outcome_classification`` by RequestRun terminal status (Dream PRE-0
# Slice 1b vocab fix, D4). Every terminal status is a REACHED DECISION → a
# success class; ``"failed"`` is reserved for a CRASH (``run_lifecycle`` raises /
# the process dies with no decision — the Episode stays ``state=open`` and the
# startup scan stamps ``failed``). ``"conceded"`` = tried, hit the replan/member
# limit, and stopped as a decision (was the misleading ``"aborted"→"failed"``).
_OUTCOME_BY_STATUS = {
    "conceded": "conceded",
    "dont_know": "dont_know",
    "completed": "succeeded",
}

ATTENTION_SCORE_IRI = capacity_iri(CATEGORY_SCORING, "attention_score")

DEFAULT_PER_REQUEST_REPLAN_BUDGET = 5


class LifecyclePhase(IntEnum):
    INTERPRETATION = 1
    PLAN_CONSTRUCTION = 2
    EXECUTION = 3  # 3-5 collapsed (sibling-sequential v1)
    DIAGNOSIS = 6


@dataclass
class RequestOutcome:
    status: str  # succeeded | dont_know | conceded | pending_confirmation
    request_run_ref: Optional[str]  # None on the pending_confirmation path (no RequestRun yet)
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
        request_scope: str = "task",
        per_request_replan_budget: int = DEFAULT_PER_REQUEST_REPLAN_BUDGET,
        simplified: bool = False,
        checkpoint_store: Any = None,
        mm_persister: Any = None,
        local_persister: Any = None,
    ) -> None:
        self._dispatcher = dispatcher
        self._mm = mm
        self._task_scope = request_scope
        self._budget = per_request_replan_budget
        self._simplified = simplified
        # Legacy checkpoint store (ADR-0179). Dream PRE-0 Slice 1b subsumes it
        # into the streaming Episode (the open Episode IS the crash bookmark), so
        # it is retained only for constructor back-compat and no longer drives
        # crash recovery. Kept unread.
        self._checkpoint_store = checkpoint_store
        # DQ-8 / CR#4 — narrow MM persister (``persist(metagraph, graph)``);
        # None = live-only (ephemeral / no Falkor client). Injected at boot.
        self._mm_persister = mm_persister
        # Dream PRE-0 Slice 1b (D3) — durable Local persister
        # (``save(user_id, local_metagraph)``). The streaming Episode's open /
        # suspend / close each flush the Local to Falkor so a crash leaves a real
        # partial Episode on disk. None = live-only (ephemeral / no Falkor). The
        # whole-Local save is fine at 1b's cadence (≤2 flushes/request); the
        # cheap per-property targeted flush is a Slice-2 follow-up.
        self._local_persister = local_persister
        # Per-orchestrator counter for the task-unique writer scope when a
        # caller supplies no request_id. Guarded — run_lifecycle runs on
        # concurrent worker threads.
        self._lifecycle_seq = 0
        self._seq_lock = threading.Lock()

    def _writer_scope(self, request_id) -> str:
        """A task-UNIQUE chain-writer scope (DQ-8 / CR#4). ``request_id`` when the
        caller supplies one; else a per-orchestrator counter. This uniqueness
        is what keeps two tasks' chain IRIs — and thus their ``episode_id``s —
        from colliding in one resident session."""
        if request_id is not None:
            return f"{self._task_scope}:{request_id}"
        with self._seq_lock:
            self._lifecycle_seq += 1
            return f"{self._task_scope}:auto{self._lifecycle_seq}"

    # ── attention-score write-through (PB-6 / D32.5c.4) ────────────────

    def update_priority(self, request_run, *, tier=TierEnum.FOREGROUND, executor=None, request_id=None) -> int:
        """Invoke L3 ``scoring.attention_score`` and write the result to the
        queue (if an executor is given) AND through to ``RequestRun.attention_
        score`` under the MM writer lock (atomic, D32.5c.4)."""
        score = self._dispatcher.dispatch(
            ATTENTION_SCORE_IRI, {DS_SCORE_INPUT: tier}
        ).outputs[DS_SCORE]
        with self._mm.lock.write_locked():
            request_run.attention_score = score
        if executor is not None and request_id is not None:
            executor.write_priority(request_id, score=score, tier=tier)
        return score

    # ── streaming-Episode durability (Dream PRE-0 Slice 1b) ────────────

    def _flush_local(self) -> None:
        """Durably flush the user's Local to Falkor (Dream PRE-0 Slice 1b, D3).

        Best-effort: durability must NEVER fail the solve. No-op when no durable
        persister is wired (ephemeral / simplified / no session)."""
        lp = self._local_persister
        if lp is None:
            return
        kl = getattr(self._dispatcher, "_kl", None)
        session = getattr(self._dispatcher, "_session", None)
        user = getattr(session, "user_id", None)
        if kl is None or user is None:
            return
        try:
            lp.save(user, kl.local_metagraph(user))
        except Exception:
            # Best-effort durability (mirrors the PRE-1 inert posture): a failed
            # flush loses only the crash anchor for this window, never the solve.
            pass

    def _open_episode(
        self, episode_id, request_input_ref, request_input_root_ref
    ) -> None:
        """Open the streaming Episode at Request start (``state=open``) + flush."""
        if self._simplified:
            return
        consolidation.open_episode(
            self._dispatcher,
            episode_id=episode_id,
            request_input_ref=request_input_ref,
            request_input_root_ref=request_input_root_ref,
        )
        self._flush_local()

    def _suspend_episode(self, episode_id) -> None:
        """Mark the Episode SUSPENDED (needs-input / pending-confirmation) + flush."""
        if self._simplified:
            return
        consolidation.suspend_episode(self._dispatcher, episode_id=episode_id)
        self._flush_local()

    # ── consolidation seam (Phase 5 -> completion; ADR-0176) ───────────

    def _consolidate(
        self, request_run, request_pattern_iri, episode_id, writer=None,
        capacity_graphs=None,
    ) -> None:
        """CLOSE the Episode on a terminal path (``state=closed`` + terminal
        content) and flush. No-op in simplified mode; graceful skip when unwired.
        Persists this task's chain graph and points ``mm_root_ref`` at it (DQ-8 /
        CR#4).

        ``capacity_graphs`` (Step 5.4): this task's per-run ``capacity_mm``
        grounding graphs. When supplied (a real solve run) and a persister is
        wired, Slice-B persist writes them + a task-level index and points the
        Episode's ``capacity_root_ref`` at it — non-inert. Empty / ``None``
        (v0, notional runs) leaves ``capacity_root_ref`` ``None``. Per-DataState
        ``encode`` hints are a brain follow-up (PB-1); with none supplied every
        grounded value must already be codec-safe (primitive/dict/list)."""
        if self._simplified:
            return
        consolidation.consolidate_request(
            self._dispatcher,
            self._mm,
            request_run,
            episode_id=episode_id,
            request_pattern_iri=request_pattern_iri,
            outcome_classification=_OUTCOME_BY_STATUS.get(request_run.status, "failed"),
            chain_graph=writer.chain_graph() if writer is not None else None,
            mm_persister=self._mm_persister,
            capacity_graphs=capacity_graphs or None,
        )
        self._flush_local()

    # ── six-phase lifecycle ────────────────────────────────────────────

    def run_lifecycle(self, request_input, *, tier=TierEnum.FOREGROUND, executor=None, request_id=None) -> RequestOutcome:
        # Dream PRE-0 Slice 1b (D2) — mint a stable request_id when the caller
        # supplies none (the brain REPL path does not), so EVERY real request
        # gets a durable Episode. The minted id is the Episode's stable identity
        # for its whole open->close life; the crash scan finds crashed Episodes
        # by ``state=open``, so the id needs only to be stored at open, not
        # re-derived. Simplified/notional runs skip persistence, so no Episode.
        if request_id is None:
            request_id = uuid.uuid4().hex
        episode_id = request_id
        # Task-unique scope (DQ-8): drives both the chain-writer graph and the
        # capacity grounding run's request_id / run refs (Step 5), so a task with
        # no explicit ``request_id`` still grounds into an isolated per-run graph.
        scope = self._writer_scope(request_id)
        writer = ChainArtifactWriter(self._mm, scope)

        request_input_ref = f"requestinput:{request_id}"

        # PRE-1 — persist the raw input value (+ modality) at Request START so the
        # Episode carries a real reload anchor (``request_input_root_ref``), not
        # just a label. Best-effort + inert: skipped in simplified mode or with no
        # persister wired, and a non-codec-safe input with no encoder is swallowed
        # (ref stays None) rather than failing the solve. (Restored here — a prior
        # collection-iteration merge to main dropped this run_lifecycle wiring
        # while keeping the persister + chain fields; Slice 1b's open needs it.)
        request_input_root_ref = None
        if self._mm_persister is not None and not self._simplified:
            if isinstance(request_input, InputEnvelope):
                _in_value, _in_modality = request_input.value, request_input.modality
            else:
                _in_value, _in_modality = request_input, None
            try:
                request_input_root_ref = request_input_persister.persist_request_input(
                    self._mm_persister,
                    self._mm.intelligence_mm,
                    scope=scope,
                    value=_in_value,
                    modality=_in_modality,
                )
            except PersistenceError:
                request_input_root_ref = None

        # Dream PRE-0 Slice 1b — OPEN the streaming Episode (state=open) at
        # Request START, carrying the reload anchors. This is the crash bookmark:
        # a crash before the terminal close leaves a real partial Episode on disk
        # (subsumes the legacy InMemoryCheckpointStore). Inert in simplified mode
        # / when consolidation is unwired.
        self._open_episode(episode_id, request_input_ref, request_input_root_ref)

        # Phase 1 — task interpretation (HintSet + MappingResult)
        p1 = phase_1.run(self._dispatcher, writer, request_input)
        # ADR-0196 — interpretation asked the user. Short-circuit into a
        # non-terminal pending_confirmation outcome BEFORE plan/exec: no
        # RequestRun, no consolidation, terminal invariants untouched. The
        # Episode is SUSPENDED (not crashed, not decided) — it resumes on
        # re-submit and the crash scan (state=open only) leaves it alone. (The
        # mid-execution needs_input path — execution.run halt+bubble — is
        # deferred, L4-25.)
        if isinstance(p1, NeedsInput):
            self._suspend_episode(episode_id)
            return RequestOutcome(
                status="pending_confirmation",
                request_run_ref=None,
                pending_confirmation=p1,
            )

        # Phase 2 — Plan + Pipeline construction. Thread the Phase-1
        # ``resolved_reference`` (Step 5.1 drop fix) so the planner can name a
        # solve target against the resolved task.
        plan_result = plan_construction.build(
            self._dispatcher, writer, p1.mapping_result_ref, p1.request_pattern_iri,
            resolved_reference=p1.resolved_reference,
        )

        # RequestRun wraps the whole execution (Level 6). Thread the PRE-1 input
        # refs onto it (the Episode's reload anchor).
        request_run = writer.emit_request_run(
            request_input_ref=request_input_ref,
            request_input_root_ref=request_input_root_ref,
            plan_ref=plan_result.plan_ref,
        )
        self.update_priority(request_run, tier=tier, executor=executor, request_id=request_id)

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
        # Dream PRE-0 Slice 2 — stream each run's capacity grounding graph
        # to Falkor as the run completes (crash durability), instead of
        # batching at terminal consolidation. The sink IS the ``capacity_graphs``
        # list ``execution.run`` appends to; its append persists the graph.
        # Plain list (byte-identical, no streaming) in simplified mode or with
        # no persister wired.
        capacity_graphs = (
            CapacityStreamSink(self._mm, self._mm_persister)
            if (not self._simplified and self._mm_persister is not None)
            else []
        )

        # Phase 3-5 — execution with bounded replan (invalidate-at-and-below).
        # Slice 3b — the blackboard is held across the loop so a *targeted* replan
        # (the verdict names a re-runnable top-level map member) can re-run only
        # that member and reuse the completed siblings' values; a whole-pipeline
        # replan resets it to a fresh seed → byte-identical to the pre-3b path.
        replans = 0
        sufficient = True
        blackboard: dict = dict(solve_seed or {}) if solve_seed is not None else {}
        targeted = None
        while True:
            try:
                execution.run(
                    self._dispatcher, writer, plan_result, request_run,
                    mm=self._mm, run_scope=scope, solve_seed=solve_seed,
                    capacity_graphs=capacity_graphs, run_attempt=replans,
                    blackboard=blackboard, targeted=targeted,
                )
            except execution.MemberAbortError:
                # Collection-iteration Slice 1b — a map member exhausted
                # MEMBER_RETRY_CAP still failing (all-or-nothing abort). The
                # fold did not run; close (conceded) what grounded. Dream Slice
                # 1b (D4): a reached abort is a DECISION → conceded, not "failed".
                request_run.status = "conceded"
                self._consolidate(
                    request_run, p1.request_pattern_iri, episode_id, writer, capacity_graphs
                )
                return RequestOutcome("conceded", request_run.iri, replans_used=replans)
            if self._simplified:
                break
            sufficient = sufficient_predicate.evaluate(self._dispatcher)
            verdict = replan_check.check(self._dispatcher)
            if verdict.decision == "abort":
                # Slice 3 — record the consumer's advisory target (if any) on the
                # abort ReplanRecord for member-scoped audit. ``replan_level``
                # stays "pipeline" (the ACTUAL action); ``replan_milestone_ref``
                # is the advisory pointer (None for v0 → byte-identical).
                writer.emit_replan_record(
                    "pipeline", verdict, replan_milestone_ref=verdict.target_ref
                )
                # Dream Slice 1b (D4): reached abort = a DECISION → conceded.
                request_run.status = "conceded"
                self._consolidate(
                    request_run, p1.request_pattern_iri, episode_id, writer, capacity_graphs
                )
                return RequestOutcome("conceded", request_run.iri, replans_used=replans)
            if verdict.decision == "replan" and replans < self._budget:
                replans += 1
                # Slice 3b — if the verdict names a re-runnable top-level map
                # member (reserved "map"/"plan_subtree" level + a resolvable
                # ref-path), invalidate only that map + fold + downstream and
                # re-run just that member against the RETAINED blackboard (the
                # untargeted siblings + their grounding graphs are reused); the
                # recorded ``replan_level`` is then the ACTUAL targeted level.
                # Otherwise fall back to the whole-pipeline clear + a fresh
                # blackboard, recorded as "pipeline" — byte-identical to Slice 3
                # (a v0 verdict, a full ``pipelinerun:`` advisory ref, or a nested
                # target all resolve to None here).
                member_target = (
                    execution.resolve_member_target(plan_result, verdict.target_ref)
                    if verdict.replan_level in ("map", "plan_subtree")
                    and verdict.target_ref
                    else None
                )
                if member_target is not None:
                    map_idx, member_idx = member_target
                    targeted = (map_idx, member_idx)
                    invalidated = replan_check.invalidate_at_and_below(
                        request_run, verdict.replan_level, at_index=map_idx
                    )
                    recorded_level = verdict.replan_level
                else:
                    targeted = None
                    blackboard = (
                        dict(solve_seed or {}) if solve_seed is not None else {}
                    )
                    invalidated = replan_check.invalidate_at_and_below(
                        request_run, "pipeline"
                    )
                    recorded_level = "pipeline"
                writer.emit_replan_record(
                    recorded_level, verdict,
                    replan_milestone_ref=verdict.target_ref,
                    invalidated_refs=invalidated,
                )
                continue
            break

        # Phase 6 — failure diagnosis on the dont-know path
        if not self._simplified and not sufficient:
            # Slice 3 — feed the last verdict's advisory target (grounding
            # ref-path of the suspect member) into diagnosis so the L3
            # ``attribute_blame`` capability can return member-scoped blame
            # (``BlameVerdict.milestone_ref``) instead of whole-pipeline. When no
            # target was named (v0), pass ``outcome=None`` so ``phase_6.diagnose``
            # dispatches ``{}`` exactly as before — byte-identical. (``verdict``
            # is always bound here: in non-simplified mode the loop runs
            # ``replan_check.check`` before any break.)
            diag_outcome = (
                {"target_ref": verdict.target_ref, "replan_level": verdict.replan_level}
                if verdict.target_ref
                else None
            )
            blame = phase_6.diagnose(self._dispatcher, outcome=diag_outcome)
            # Dream Slice 1b (D4): the insufficient path is a reached "I can't
            # determine this" DECISION → dont_know, NOT "failed" (reserved for a
            # crash). Runtime status matches the recorded outcome.
            request_run.status = "dont_know"
            self._consolidate(
                request_run, p1.request_pattern_iri, episode_id, writer, capacity_graphs
            )
            return RequestOutcome(
                "dont_know",
                request_run.iri,
                dont_know_reason="INSUFFICIENT",
                blame=blame,
                replans_used=replans,
            )

        # Phase 5 -> completion: freeze MM + write Episode (ADR-0176).
        request_run.status = "completed"
        self._consolidate(
            request_run, p1.request_pattern_iri, episode_id, writer, capacity_graphs
        )
        return RequestOutcome(
            "succeeded", request_run.iri, outcome=p1.request_pattern_iri, replans_used=replans
        )


__all__ = [
    "Orchestrator",
    "RequestOutcome",
    "LifecyclePhase",
    "DEFAULT_PER_REQUEST_REPLAN_BUDGET",
]
