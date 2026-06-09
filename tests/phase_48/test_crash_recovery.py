"""Phase 48 S8 — crash recovery (ADR-0179; Chat B D-B50).

v1 tombstone mechanism: an unconsolidated checkpoint marker → a
``crash_marker`` Episode (``outcome_classification="failed"``, ``mm_root_ref
= None``) on the L4-startup scan; idempotent on the task id; the orchestrator
records markers at the D-B50 triggers and clears them on consolidation.
"""

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins import (
    install_orchestration_v0,
    install_phase1_v0,
    install_planning_v0,
    reset_v0_verdicts,
)
from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
from mindsos_intelligence.crash_recovery import (
    CheckpointMarker,
    InMemoryCheckpointStore,
    recover_unconsolidated,
)
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.orchestrator import Orchestrator
from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
from mindsos_knowledge.metagraph_view import MetagraphView
from tests.phase_33._fixtures import build_session_with_caps


def _dispatcher(kl):
    layer = CapacityLayer(kl=kl)
    install_consolidate_capacities(layer)
    return L4Dispatcher(layer, session=build_session_with_caps("alice", frozenset()), kl=kl)


def _episodes(kl):
    g = MetagraphView(kl.local_metagraph("alice")).graphs_by_role(ROLE_EPISODIC_MEMORIES)[0]
    return [n for n in g.nodes.values() if n.type_name == "Episode"]


def test_recover_writes_crash_tombstone_episode():
    kl = KnowledgeLayer.bootstrap()
    store = InMemoryCheckpointStore()
    store.record(
        CheckpointMarker(
            task_id="t-crashed",
            task_input_ref="ti:x",
            task_pattern_iri="tp:x",
            last_phase="EXECUTION",
        )
    )
    recovered = recover_unconsolidated(store, _dispatcher(kl))
    assert recovered == ["t-crashed"]
    eps = _episodes(kl)
    assert len(eps) == 1
    val = eps[0].value
    assert val["outcome_classification"] == "failed"
    assert val["mm_root_ref"] is None
    assert val["crash_marker"]["last_phase"] == "EXECUTION"
    assert store.iter_unconsolidated() == []


def test_recover_is_idempotent_on_existing_episode():
    kl = KnowledgeLayer.bootstrap()
    d = _dispatcher(kl)
    s1 = InMemoryCheckpointStore()
    s1.record(CheckpointMarker(task_id="t1", task_pattern_iri="tp:x"))
    recover_unconsolidated(s1, d)
    # A second scan that sees the same task id finds the Episode already
    # present and writes no duplicate (ADR-0176 §4).
    s2 = InMemoryCheckpointStore()
    s2.record(CheckpointMarker(task_id="t1", task_pattern_iri="tp:x"))
    recover_unconsolidated(s2, d)
    assert len(_episodes(kl)) == 1


def test_consolidated_marker_not_recovered():
    kl = KnowledgeLayer.bootstrap()
    store = InMemoryCheckpointStore()
    store.record(CheckpointMarker(task_id="t1"))
    store.mark_consolidated("t1")
    assert recover_unconsolidated(store, _dispatcher(kl)) == []
    assert _episodes(kl) == []


def test_orchestrator_records_then_clears_checkpoint_on_success():
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_planning_v0(layer)
    install_phase1_v0(layer)
    install_orchestration_v0(layer)
    install_consolidate_capacities(layer)
    reset_v0_verdicts()
    store = InMemoryCheckpointStore()
    mm = MentalModel(session_id="s", user_id="alice")
    orch = Orchestrator(
        L4Dispatcher(layer, session=build_session_with_caps("alice", frozenset()), kl=kl),
        mm,
        task_scope="task-1",
        checkpoint_store=store,
    )
    outcome = orch.run_lifecycle("hi", task_id="task-7")
    assert outcome.status == "succeeded"
    assert store.iter_unconsolidated() == []  # recorded at triggers, cleared on consolidation
