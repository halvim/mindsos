"""Phase 48 S1 — orchestrator consolidation seam (ADR-0176 §1).

``run_lifecycle`` freezes the MM and writes an Episode to L2
``episodic_memories`` on every terminal path (retain-by-default). Skipped in
simplified mode and gracefully skipped when no consolidate capacity / KL is
wired (the Phase-47 v0 smoke — covered by its own green run).
"""

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins import (
    install_orchestration_v0,
    install_phase1_v0,
    install_planning_v0,
    reset_v0_verdicts,
)
from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.orchestrator import Orchestrator
from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
from mindsos_knowledge.metagraph_view import MetagraphView


class FakeSession:
    def __init__(self, caps=()):
        self.session_id = "s"
        self.user_id = "u"
        self.actor_role = "user"
        self.capabilities = set(caps)

    def has(self, capability: str) -> bool:
        return capability in self.capabilities


def _orch_with_kl(simplified: bool = False):
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_planning_v0(layer)
    install_phase1_v0(layer)
    install_orchestration_v0(layer)
    install_consolidate_capacities(layer)
    reset_v0_verdicts()
    mm = MentalModel(session_id="s", user_id="u")
    dispatcher = L4Dispatcher(layer, session=FakeSession(), kl=kl)
    orch = Orchestrator(dispatcher, mm, request_scope="request-1", simplified=simplified)
    return orch, mm, kl


def _episodes(kl):
    g = MetagraphView(kl.local_metagraph("u")).graphs_by_role(ROLE_EPISODIC_MEMORIES)[0]
    return [n for n in g.nodes.values() if n.type_name == "Episode"]


def test_run_lifecycle_writes_episode_on_success():
    orch, mm, kl = _orch_with_kl()
    outcome = orch.run_lifecycle("hello", request_id="T")
    assert outcome.status == "succeeded"
    eps = _episodes(kl)
    assert len(eps) == 1
    val = eps[0].value
    assert val["outcome_classification"] == "succeeded"
    chain_graphs = [
        g for g in mm.intelligence_mm.graphs.values() if g.role == "chain"
    ]
    assert len(chain_graphs) == 1
    assert val["mm_root_ref"] == chain_graphs[0].graph_id


def test_simplified_mode_skips_consolidation():
    orch, mm, kl = _orch_with_kl(simplified=True)
    outcome = orch.run_lifecycle("hello", request_id="T")
    assert outcome.status == "succeeded"
    assert _episodes(kl) == []
