"""Per-device-instance stack assembly (plan P-1/P-4/P-5, Round-3).

Each brain is an independent MindsOS install: its own ``KnowledgeLayer``
(Global + Local L2), ``CapacityLayer`` (L3, builtin catalog at DM-1),
``IntelligenceLayer`` (L4 substrate), and an ``Orchestrator`` bound to the
IL's MM. The session is injected (real ``mindsos_server`` Session in
``bootstrap.py``; a duck session in tests) so this module imports only
the domain stack and stays runnable wherever L3/L4/L5 import.

Wiring facts grounded against the shipped code (design log §1, P5):
  * ``IntelligenceLayer.mm`` exists only after ``.start()`` → build the
    Orchestrator after start, over ``il.mm``.
  * ``Orchestrator(L4Dispatcher(cl, session, kl), il.mm)`` runs the
    six-phase lifecycle; ``il.enqueue(lambda: orch.run_lifecycle(...))``
    runs it on the IL worker pool (P5).
  * Consolidation writes the brain's OWN Local ``episodic_memories``
    (auto-created lazily by ``kl.local_metagraph(user)``, PB-T); the
    ADR-0180 gate only fires on Global writes, so a normal-user Local
    consolidate needs no ``CAN_WRITE_GLOBAL`` (Phase-48 PB-10).
"""

from __future__ import annotations

import uuid
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Optional

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins import (
    install_orchestration_v0,
    install_phase1_v0,
    install_planning_v0,
    reset_v0_verdicts,
)
from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.intelligence_layer import IntelligenceLayer
from mindsos_intelligence.orchestrator import Orchestrator
from mindsos_knowledge import KnowledgeLayer

from .profiles import DeviceProfile


@dataclass
class Brain:
    """One device-instance's live stack (held by the bootstrap)."""

    profile: DeviceProfile
    session: Any
    kl: Any
    cl: Any
    il: IntelligenceLayer
    orch: Orchestrator
    dispatcher: L4Dispatcher

    @property
    def device_id(self) -> str:
        return self.profile.device_id


def build_device_kl(profile: DeviceProfile) -> Any:
    """DM-1: a fresh in-memory per-device Global (renamed for clarity).

    PB-J: the shipped ``bootstrap_kl_from_falkordb`` is single-Global-by-
    name; per-device persisted Globals are a DM-2 helper. At DM-1 the KL
    is in-memory (no Falkor persist), so 4 independent ``bootstrap()``s
    cannot collide — the rename is clarity-only. The Local is pre-touched
    (auto-creates ``episodic_memories`` + ``capacity-state``, PB-T).
    """
    kl = KnowledgeLayer.bootstrap()
    try:
        kl.global_metagraph().name = profile.kl_name
    except Exception:  # pragma: no cover — name is settable (verified)
        pass
    kl.local_metagraph(profile.device_id)  # defensive pre-create (PB-T)
    return kl


def install_builtin_catalog(cl: Any) -> None:
    """Register the shipped builtin catalog into a CapacityLayer.

    DM-1: the v0 lifecycle catalogs + the consolidate write capacity —
    exactly what a trivial ``run_lifecycle`` dispatches and what
    ``consolidation_enabled`` requires. Demo L3 capacities (§4) are
    DM-3; device-type-exclusive bundles (§3.4) are DM-2.
    """
    install_planning_v0(cl)
    install_phase1_v0(cl)
    install_orchestration_v0(cl)
    install_consolidate_capacities(cl)
    reset_v0_verdicts()


def build_brain_stack(
    profile: DeviceProfile, session: Any, *, kl: Any = None
) -> Brain:
    """Assemble + start one device-instance. Returns a live :class:`Brain`.

    Order matters (P5): construct + ``start()`` the IL first so ``il.mm``
    exists, then bind the Orchestrator to it.

    ``kl``: a pre-built KnowledgeLayer (DM-2 supplies a per-device Falkor
    load-or-minted Global, ``persistence.load_or_mint_global``). When
    ``None`` (DM-1 / sandbox), a fresh in-memory per-device Global is
    minted via :func:`build_device_kl`.
    """
    if kl is None:
        kl = build_device_kl(profile)
    cl = CapacityLayer(kl=kl)
    install_builtin_catalog(cl)

    il = IntelligenceLayer(
        session,
        knowledge=kl,
        capacity=cl,
        max_workers=profile.max_workers,
        dream_interval_s=None,  # dreaming OFF during the demo (plan §5)
    )
    il.start()

    dispatcher = L4Dispatcher(cl, session=session, kl=kl)
    orch = Orchestrator(dispatcher, il.mm, task_scope=f"demo-{profile.device_id}")

    return Brain(
        profile=profile,
        session=session,
        kl=kl,
        cl=cl,
        il=il,
        orch=orch,
        dispatcher=dispatcher,
    )


# ── task_input capture (DM-4 Mode-A export, design-log PB-17) ──────────
#
# The consolidated Episode stores only ``task_input_ref`` (a string), NOT the
# resolved order payload — and the v0 ``hint.global`` produces an empty
# HintSet, so the order is not recoverable from the chain either. The Mode-A
# snapshot's ``episode.task_input`` wants the real payload, so ``run_task``
# records it here keyed by the unique per-task scope (which the serializer also
# derives from the Episode id). Bounded FIFO — the demo runs a handful of tasks
# per brain, but cap it so a long-lived process can't grow unboundedly.
_TASK_INPUTS: "OrderedDict[str, Any]" = OrderedDict()
_TASK_INPUTS_MAX = 256


def _record_task_input(scope: str, task_input: Any) -> None:
    _TASK_INPUTS[scope] = task_input
    _TASK_INPUTS.move_to_end(scope)
    while len(_TASK_INPUTS) > _TASK_INPUTS_MAX:
        _TASK_INPUTS.popitem(last=False)


def task_input_for(scope: str) -> Optional[Any]:
    """The resolved ``task_input`` captured for a task ``scope`` (or None)."""
    return _TASK_INPUTS.get(scope)


# ── refusal capture (DM-5 embodiment gate, design-log §23) ─────────────
#
# The shipped ``run_lifecycle`` returns the dont-know ``blame`` only on the
# ``TaskOutcome`` (it is NOT written to the chain), so the Mode-A serializer
# can't recover ``reasoning.dont_know``/``blame`` from ``il.mm``. We capture it
# here from the TaskOutcome, keyed by the same unique scope the serializer
# slices on — race-free (the scope + outcome both belong to this task).
_REFUSALS: "OrderedDict[str, dict]" = OrderedDict()
_REFUSALS_MAX = 256


def _record_refusal(scope: str, record: dict) -> None:
    _REFUSALS[scope] = record
    _REFUSALS.move_to_end(scope)
    while len(_REFUSALS) > _REFUSALS_MAX:
        _REFUSALS.popitem(last=False)


def refusal_for(scope: str) -> Optional[dict]:
    """The captured refusal record (``{"reason", "blame"}``) for a dont-know
    task ``scope`` (or ``None`` on the happy path)."""
    return _REFUSALS.get(scope)


# DM-6: a behavior-level reroute/recalibration summary, keyed by the same unique
# scope the serializer slices on (the ReplanRecord carries no free-text "why",
# so the headline lives here — sourced from the brain's real fault-stash cause).
_REPLAN_SUMMARIES: "OrderedDict[str, str]" = OrderedDict()
_REPLAN_SUMMARIES_MAX = 256


def _record_replan_summary(scope: str, summary: str) -> None:
    _REPLAN_SUMMARIES[scope] = summary
    _REPLAN_SUMMARIES.move_to_end(scope)
    while len(_REPLAN_SUMMARIES) > _REPLAN_SUMMARIES_MAX:
        _REPLAN_SUMMARIES.popitem(last=False)


def replan_summary_for(scope: str) -> Optional[str]:
    """The sanitized behavior-level replan headline for a task ``scope`` (or
    ``None`` when the run had no replan)."""
    return _REPLAN_SUMMARIES.get(scope)


def _capture_outcome(scope: str, outcome: Any) -> None:
    """Record a refusal if the lifecycle produced a dont-know (else no-op)."""
    if getattr(outcome, "status", None) != "dont_know":
        return
    blame = getattr(outcome, "blame", None)
    reason = (
        getattr(blame, "rationale", None)
        or getattr(outcome, "dont_know_reason", None)
        or "could not complete the task"
    )
    blame_d = (
        {
            "chain_level": getattr(blame, "chain_level", None),
            "blame_score": getattr(blame, "blame_score", None),
            "rationale": getattr(blame, "rationale", None),
        }
        if blame is not None
        else None
    )
    _record_refusal(scope, {"reason": reason, "blame": blame_d})


def run_task(brain: Brain, task_input: Any, *, task_id: str = "task") -> Any:
    """Enqueue ONE lifecycle on the brain's IL with a FRESH per-task
    Orchestrator + a unique ``task_scope``. Returns the Future.

    PB-HHH: the chain-artifact writer mints IRIs from ``task_scope``; a
    constant per-brain scope collides those IRIs on the brain's *second*
    lifecycle (``IdentityError: Duplicate id`` — the first ``place_order``
    after the bootstrap smoke). A unique scope per task fixes the crash and,
    as a bonus, keeps each task's chain nodes distinguishable in the shared
    intelligence-MM (exactly what the Mode-A per-task export needs).

    PB-17: the resolved ``task_input`` is recorded under the scope so the
    Mode-A serializer can render ``episode.task_input`` faithfully (the Episode
    itself only keeps a ref string).

    ``brain.orch`` (built in :func:`build_brain_stack`) is retained for its
    dispatcher/back-compat; task execution goes through here.
    """
    tid = f"{task_id}-{uuid.uuid4().hex[:8]}"
    scope = f"demo-{brain.device_id}-{tid}"
    _record_task_input(scope, task_input)
    orch = Orchestrator(brain.dispatcher, brain.il.mm, task_scope=scope)
    fut = brain.il.enqueue(lambda: orch.run_lifecycle(task_input, task_id=tid))

    def _on_done(f: Any) -> None:
        try:
            outcome = f.result()
            _capture_outcome(scope, outcome)
            # DM-6: on a real replan (recalibration or reroute), capture the
            # behavior-level summary from this brain's fault-stash cause (single-
            # flight → the stash belongs to this task). Keyed by this scope.
            if getattr(outcome, "replans_used", 0) > 0:
                from .gate import get_fault_state
                fs = get_fault_state(brain)
                if fs and fs.get("cause"):
                    _record_replan_summary(scope, fs["cause"])
        except Exception:  # noqa — capture is best-effort, never crash the task
            pass

    fut.add_done_callback(_on_done)
    return fut


__all__ = [
    "Brain",
    "build_device_kl",
    "install_builtin_catalog",
    "build_brain_stack",
    "run_task",
    "task_input_for",
    "refusal_for",
]
