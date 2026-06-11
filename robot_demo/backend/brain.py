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

from dataclasses import dataclass
from typing import Any

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


__all__ = [
    "Brain",
    "build_device_kl",
    "install_builtin_catalog",
    "build_brain_stack",
]
