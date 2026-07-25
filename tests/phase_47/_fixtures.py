"""Shared fixtures for tests/phase_47/ — orchestrator wiring over the v0
catalogs (one shared file per the Phase 30 PB-18 precedent)."""

from __future__ import annotations

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins import (
    install_orchestration_v0,
    install_phase1_v0,
    install_planning_v0,
    reset_v0_verdicts,
)

from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.orchestrator import Orchestrator


class FakeSession:
    def __init__(self, caps=()):
        self.session_id = "s"
        self.user_id = "u"
        self.actor_role = "user"
        self.capabilities = set(caps)

    def has(self, capability: str) -> bool:
        return capability in self.capabilities


def make_orchestrator(*, task_scope="task-1", simplified=False, budget=5):
    layer = CapacityLayer()
    install_planning_v0(layer)
    install_phase1_v0(layer)
    install_orchestration_v0(layer)
    reset_v0_verdicts()
    mm = MentalModel(session_id="s", user_id="u")
    dispatcher = L4Dispatcher(layer, session=FakeSession())
    orch = Orchestrator(
        dispatcher, mm, task_scope=task_scope, simplified=simplified,
        per_request_replan_budget=budget,
    )
    return orch, mm, layer
