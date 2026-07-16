"""Resident-brain boot helper.

Composes the durable L2/L3/L4/L5 stack a long-lived process holds: a
Falkor-backed KnowledgeLayer, a CapacityLayer with builtins + installed
skills reactivated, the user's Local booted, and an Orchestrator over a
MentalModel. This is the product-code promotion of the test-only
``tests/phase_49/integration_c.py::build_stack`` recipe (RESIDENT_BRAIN
design note, PB-2), extended with the durable path (PB-3=B):

``bootstrap_kl_from_falkordb`` → install builtins → ``apply_installed_skills``
→ ``boot_local``.

``client=None`` selects the in-memory ephemeral path (deterministic,
Falkor-free) for tests and quick trials — builtins only, no installed
skills, an in-memory persister.

The caller owns the ``client`` lifecycle (open / close) per Phase 07 P4 A;
:func:`boot_brain` never closes it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

log = logging.getLogger(__name__)


@dataclass
class Stack:
    """One live resident-brain instance."""

    kl: Any
    cl: Any
    mm: Any
    dispatcher: Any
    orch: Any
    session: Any
    persister: Any
    user: str
    #: Boot-time :class:`~mindsos_server.skills.ActivationReport` for
    #: installed-skill activation (``None`` on the ephemeral path, which
    #: activates no installed skills). Its ``skipped`` roster names any
    #: bundle a REPL/operator surface should report as unactivated.
    activation: Any = None

    def global_view(self) -> Any:
        """The read-only bipartite probe surface over the Global L3."""
        return self.cl.global_view()

    def local_view(self) -> Any:
        """The read-only probe surface over this user's Local L3 partition."""
        return self.cl.local_view(self.user)

    def save(self) -> None:
        """Persist the user's Local to Falkor (no-op when ephemeral)."""
        if self.persister is None:
            return
        self.persister.save(self.user, self.kl.local_metagraph(self.user))


class _BrainSession:
    """Permissive single-user Local session (SessionProtocol shape).

    ``has()`` returns ``True`` for any capability — a resident brain v1 is
    single-user and only writes its OWN Local, so the ADR-0180 scope-aware
    gate (which fires on Global writes) is never tripped. Mirrors the
    Phase-49 integration ``_Session``.
    """

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.session_id = f"brain-{user_id}"
        self.actor_role = "user"

    def has(self, capability: str) -> bool:  # noqa: D401 — protocol stub
        return True


def _install_builtins(cl: Any) -> None:
    """Install the v0 catalogs + builtins onto ``cl`` (build_stack parity)."""
    from mindsos_capacity.builtins import (
        install_orchestration_v0,
        install_phase1_v0,
        install_planning_v0,
        install_text_capacities,
        reset_v0_verdicts,
    )
    from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
    from mindsos_capacity.builtins.dream import install_dream_capacities

    install_planning_v0(cl)
    install_phase1_v0(cl)
    install_orchestration_v0(cl)
    install_consolidate_capacities(cl)
    install_text_capacities(cl)
    install_dream_capacities(cl)
    reset_v0_verdicts()


def boot_brain(
    client: Any = None,
    *,
    user: str,
    install_builtins: bool = True,
    session: Any = None,
) -> Stack:
    """Boot one resident-brain :class:`Stack`.

    Args:
        client: A live Falkor ``Client`` for the durable path, or ``None``
            for the in-memory ephemeral path. Caller owns its lifecycle.
        user: The single Local user this brain serves.
        install_builtins: Install the v0 catalogs + builtins (default).
        session: A SessionProtocol object; defaults to a permissive
            single-user :class:`_BrainSession`.
    """
    from mindsos_capacity import CapacityLayer
    from mindsos_intelligence.dispatch import L4Dispatcher
    from mindsos_intelligence.mm import MentalModel
    from mindsos_intelligence.orchestrator import Orchestrator
    from mindsos_knowledge import KnowledgeLayer

    session = session if session is not None else _BrainSession(user)
    activation: Any = None

    if client is None:
        # Ephemeral: in-memory Global, in-memory Local persister, no ledger.
        from mindsos_server.persistence.local_persister import InMemoryLocalPersister

        kl = KnowledgeLayer.bootstrap()
        cl = CapacityLayer(kl=kl)
        if install_builtins:
            _install_builtins(cl)
        persister: Optional[Any] = InMemoryLocalPersister()
    else:
        # Durable: load-or-mint Global from Falkor, reactivate installed skills.
        from mindsos_server.persistence.bootstrap import bootstrap_kl_from_falkordb
        from mindsos_server.persistence.local_persister import FalkorDBLocalPersister
        from mindsos_server.skills import apply_installed_skills

        kl = bootstrap_kl_from_falkordb(client)
        cl = CapacityLayer(kl=kl)
        if install_builtins:
            _install_builtins(cl)
        # Resilient at boot: one absent or broken bundle must not brick the
        # brain (ADR-0183 §am-2). Strict activation is the explicit
        # ``mindsos skill activate`` path, not this one. Skips are
        # process-local and reported, never written back to the record.
        activation = apply_installed_skills(cl, kl, strict=False)
        for _bundle, _reason in activation.skipped:
            log.warning(
                "boot: skill %r not activated for user %r: %s",
                _bundle,
                user,
                _reason,
            )
        persister = FalkorDBLocalPersister(client)

    # Load-or-mint the user's durable Local + reactivate its learned caps.
    from mindsos_server.local_boot import boot_local

    boot_local(cl, kl, persister, user, session=session)

    mm = MentalModel(session_id=session.session_id, user_id=user)
    dispatcher = L4Dispatcher(cl, session=session, kl=kl)
    orch = Orchestrator(dispatcher, mm, task_scope="brain")
    return Stack(
        kl, cl, mm, dispatcher, orch, session, persister, user,
        activation=activation,
    )


__all__ = ["Stack", "boot_brain"]
