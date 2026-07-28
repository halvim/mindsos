"""Phase 48 S8 — crash recovery (ADR-0179; Chat B D-B50;
reworked Dream PRE-0 Slice 1b).

The streaming Episode subsumes the legacy checkpoint-marker store: a crash leaves
the Episode ``state=open`` (the only failure). The L4-startup scan
(:func:`recover_unconsolidated`) closes each open Episode in place — stamping
``state=closed`` + ``outcome_classification="failed"`` + a recovered
``crash_marker`` — while preserving the partial content written at open.
Closed / suspended Episodes are left untouched.
"""

import json

from mindsos_capacity import CapacityLayer, DS_MM_COMPOSITE_INSTANCE
from mindsos_capacity.builtins import (
    install_orchestration_v0,
    install_phase1_v0,
    install_planning_v0,
    reset_v0_verdicts,
)
from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
from mindsos_intelligence import consolidation, crash_recovery
from mindsos_intelligence.crash_recovery import recover_unconsolidated
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.orchestrator import Orchestrator
from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
from mindsos_knowledge.metagraph_view import MetagraphView
from mindsos_knowledge.schemas.episodic_memories import (
    EPISODE_STATE_CLOSED,
    EPISODE_STATE_OPEN,
    EPISODE_STATE_SUSPENDED,
)
from tests.phase_33._fixtures import build_session_with_caps


def _dispatcher(kl):
    layer = CapacityLayer(kl=kl)
    install_consolidate_capacities(layer)
    return L4Dispatcher(
        layer, session=build_session_with_caps("alice", frozenset()), kl=kl
    )


def _episodes(kl):
    g = MetagraphView(kl.local_metagraph("alice")).graphs_by_role(
        ROLE_EPISODIC_MEMORIES
    )[0]
    return [n for n in g.nodes.values() if n.type_name == "Episode"]


def _by_id(kl, episode_id):
    for n in _episodes(kl):
        if n.value == episode_id:
            return n
    raise AssertionError(f"no Episode {episode_id!r}")


def _close(dispatcher, episode_id, **props):
    record = {
        DS_MM_COMPOSITE_INSTANCE: {
            "episode_id": episode_id,
            "value": {"op": "close", "props": {"state": EPISODE_STATE_CLOSED, **props}},
        }
    }
    dispatcher.dispatch("capacity:consolidate:mm", record, request_id=episode_id)


def test_recover_closes_open_episode_as_failed():
    kl = KnowledgeLayer.bootstrap()
    d = _dispatcher(kl)
    consolidation.open_episode(d, episode_id="t-crashed", request_input_ref="ti:x")
    assert _by_id(kl, "t-crashed").properties["state"] == EPISODE_STATE_OPEN

    recovered = recover_unconsolidated(d)
    assert recovered == ["t-crashed"]
    node = _by_id(kl, "t-crashed")
    assert node.properties["state"] == EPISODE_STATE_CLOSED
    assert node.properties["outcome_classification"] == "failed"
    # Partial content written at open is preserved (ADR-0179 §3 promoted).
    assert node.properties["request_input_ref"] == "ti:x"
    # crash_marker is a JSON-encoded property (L1 props are primitives-only).
    assert json.loads(node.properties["crash_marker"])["recovered"] is True


def test_recover_ignores_closed_and_suspended():
    kl = KnowledgeLayer.bootstrap()
    d = _dispatcher(kl)
    consolidation.open_episode(d, episode_id="done")
    _close(d, "done", outcome_classification="succeeded")
    consolidation.open_episode(d, episode_id="waiting")
    consolidation.suspend_episode(d, episode_id="waiting")

    assert recover_unconsolidated(d) == []
    assert _by_id(kl, "done").properties["state"] == EPISODE_STATE_CLOSED
    assert _by_id(kl, "waiting").properties["state"] == EPISODE_STATE_SUSPENDED


def test_recover_is_idempotent():
    kl = KnowledgeLayer.bootstrap()
    d = _dispatcher(kl)
    consolidation.open_episode(d, episode_id="t1")
    assert recover_unconsolidated(d) == ["t1"]
    # Second scan: the Episode is now closed → nothing open to recover.
    assert recover_unconsolidated(d) == []
    assert len(_episodes(kl)) == 1


def test_recover_noop_without_consolidate_capacity():
    kl = KnowledgeLayer.bootstrap()
    # A dispatcher whose layer never installed consolidate → recovery is a
    # graceful no-op (consolidation_enabled is False).
    bare = L4Dispatcher(
        CapacityLayer(kl=kl),
        session=build_session_with_caps("alice", frozenset()),
        kl=kl,
    )
    assert recover_unconsolidated(bare) == []


def test_lifecycle_success_leaves_a_closed_episode():
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_planning_v0(layer)
    install_phase1_v0(layer)
    install_orchestration_v0(layer)
    install_consolidate_capacities(layer)
    reset_v0_verdicts()
    mm = MentalModel(session_id="s", user_id="alice")
    orch = Orchestrator(
        L4Dispatcher(
            layer, session=build_session_with_caps("alice", frozenset()), kl=kl
        ),
        mm,
        request_scope="request-1",
    )
    outcome = orch.run_lifecycle("hi", request_id="request-7")
    assert outcome.status == "succeeded"
    # The Episode was opened at start and closed at completion — none left open.
    node = _by_id(kl, "request-7")
    assert node.properties["state"] == EPISODE_STATE_CLOSED
    assert node.properties["outcome_classification"] == "succeeded"
    assert recover_unconsolidated(
        L4Dispatcher(
            layer, session=build_session_with_caps("alice", frozenset()), kl=kl
        )
    ) == []
