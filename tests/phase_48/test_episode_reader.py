"""Dream PRE-0 Slice 3 — the open-tolerant Episode reader.

Unit: Episode node/prop parsing (no Falkor) + latest-attempt-wins dedup.
Integration (@integration, live Falkor): a CRASHED episode (null grounding refs)
has its streamed chain + capacity run graphs located by deterministic role/name;
a CLOSED episode resolves the same grounding via its stored refs.
"""

from __future__ import annotations

import pytest

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture

from mindsos_capacity import CapacityLayer, DS_MM_COMPOSITE_INSTANCE
from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
from mindsos_core.models.graph import Graph
from mindsos_intelligence import consolidation
from mindsos_intelligence.crash_recovery import recover_unconsolidated
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.episode_reader import (
    EpisodeView,
    _attempt_key,
    _latest_by_position,
    read_episode,
)
from mindsos_intelligence.mm import MentalModel
from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
from mindsos_knowledge.metagraph_view import MetagraphView
from mindsos_knowledge.schemas.episodic_memories import EPISODE_STATE_CLOSED
from tests.phase_33._fixtures import build_session_with_caps


def _dispatcher(kl):
    layer = CapacityLayer(kl=kl)
    install_consolidate_capacities(layer)
    return L4Dispatcher(
        layer, session=build_session_with_caps("alice", frozenset()), kl=kl
    )


def _by_id(kl, episode_id):
    g = MetagraphView(kl.local_metagraph("alice")).graphs_by_role(
        ROLE_EPISODIC_MEMORIES
    )[0]
    for n in g.nodes.values():
        if n.type_name == "Episode" and n.value == episode_id:
            return n
    raise AssertionError(f"no Episode {episode_id!r}")


def _close(dispatcher, episode_id, **props):
    dispatcher.dispatch(
        "capacity:consolidate:mm",
        {
            DS_MM_COMPOSITE_INSTANCE: {
                "episode_id": episode_id,
                "value": {
                    "op": "close",
                    "props": {"state": EPISODE_STATE_CLOSED, **props},
                },
            }
        },
        request_id=episode_id,
    )


def _run_graph(role):
    g = Graph(name=role, role=role)
    g.add_node("cap", "CapacityInstance")
    return g


# ── unit: prop parsing + dedup (no Falkor) ──────────────────────────────────


def test_read_episode_parses_props_and_partial_without_client():
    kl = KnowledgeLayer.bootstrap()
    d = _dispatcher(kl)
    consolidation.open_episode(d, episode_id="c1", request_input_ref="ti:c1")
    recover_unconsolidated(d)  # -> closed/failed + JSON crash_marker; refs stay null

    view = read_episode(kl, None, episode_id="c1", user_id="alice")
    assert isinstance(view, EpisodeView)
    assert view.state == "closed"
    assert view.outcome_classification == "failed"
    assert view.request_input_ref == "ti:c1"
    assert isinstance(view.crash_marker, dict) and view.crash_marker["recovered"] is True
    # No client -> grounding skipped, marked partial.
    assert view.partial is True
    assert view.chain_graph is None and view.capacity_run_graphs == []


def test_read_episode_absent_returns_none():
    kl = KnowledgeLayer.bootstrap()
    kl.local_metagraph("alice")  # ensure the (empty) Local role-graph exists
    assert read_episode(kl, None, episode_id="nope", user_id="alice") is None


def test_latest_by_position_keeps_highest_attempt():
    a0 = {"id": "a", "role": "capacity:run:E:E-0-0", "name": "n"}
    a1 = {"id": "b", "role": "capacity:run:E:E-0-1", "name": "n"}  # leaf0 replan
    c0 = {"id": "c", "role": "capacity:run:E:E-1-0", "name": "n"}  # leaf1
    kept = {x["id"] for x in _latest_by_position([a0, a1, c0])}
    assert kept == {"b", "c"}  # leaf0's newer attempt wins; leaf1 kept


def test_attempt_key_position_is_attempt_stable():
    # Same map member, two replan attempts -> same position, ordered recency.
    p0, r0 = _attempt_key("capacity:run:E:E-0-m1-0-r0")
    p1, r1 = _attempt_key("capacity:run:E:E-0-m1-1-r0")
    assert p0 == p1 and r1 > r0


# ── integration: locate streamed grounding (live Falkor) ────────────────────


@pytest.mark.integration
def test_read_crashed_episode_locates_grounding_by_role(falkor_client):
    from mindsos_intelligence.mm_persister import FalkorMMPersister

    kl = KnowledgeLayer.bootstrap()
    d = _dispatcher(kl)
    eid = "crashed-1"
    mm = MentalModel(session_id="s", user_id="alice")
    persister = FalkorMMPersister(falkor_client)

    # Streamed grounding is on disk; the Episode crashed (no refs written).
    chain = Graph(name=f"chain:task:{eid}", role="chain")
    chain.add_node("rr", "RequestRun")
    persister.persist(mm.intelligence_mm, chain)
    for i in (0, 1):
        persister.persist(mm.capacity_mm, _run_graph(f"capacity:run:{eid}:{eid}-{i}-0"))

    consolidation.open_episode(d, episode_id=eid, request_input_ref=f"ti:{eid}")
    recover_unconsolidated(d)  # closes failed; leaves grounding refs null
    assert _by_id(kl, eid).properties.get("mm_root_ref") is None

    view = read_episode(kl, falkor_client, episode_id=eid, user_id="alice")
    assert view is not None
    assert view.state == "closed" and view.outcome_classification == "failed"
    assert view.chain_graph is not None and view.chain_graph.role == "chain"
    assert len(view.capacity_run_graphs) == 2
    assert view.partial is False


@pytest.mark.integration
def test_read_closed_episode_via_refs(falkor_client):
    from mindsos_intelligence.capacity_persister import persist_capacity_mm
    from mindsos_intelligence.mm_persister import FalkorMMPersister

    kl = KnowledgeLayer.bootstrap()
    d = _dispatcher(kl)
    eid = "closed-1"
    mm = MentalModel(session_id="s", user_id="alice")
    persister = FalkorMMPersister(falkor_client)

    chain = Graph(name=f"chain:task:{eid}", role="chain")
    chain.add_node("rr", "RequestRun")
    persister.persist(mm.intelligence_mm, chain)
    runs = [_run_graph(f"capacity:run:{eid}:{eid}-{i}-0") for i in (0, 1)]
    cap_root = persist_capacity_mm(persister, mm.capacity_mm, runs, request_id=eid)

    consolidation.open_episode(d, episode_id=eid, request_input_ref=f"ti:{eid}")
    _close(
        d, eid,
        outcome_classification="succeeded",
        mm_root_ref=chain.graph_id,
        capacity_root_ref=cap_root,
    )
    assert _by_id(kl, eid).properties["capacity_root_ref"] == cap_root

    view = read_episode(kl, falkor_client, episode_id=eid, user_id="alice")
    assert view.state == "closed" and view.outcome_classification == "succeeded"
    assert view.chain_graph is not None
    assert len(view.capacity_run_graphs) == 2
    assert view.partial is False
