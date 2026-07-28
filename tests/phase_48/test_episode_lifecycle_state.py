"""Dream PRE-0 Slice 1b — Episode open/close lifecycle + ``state`` property.

The streaming Episode is created ``state=open`` at Request start, flipped
``suspended`` on needs-input, and closed ``state=closed`` with the terminal
content at a decision. Its fields are real L1 node properties (D1), edited
through ``KLWriteHandle.update_and_validate`` (Slice 1a) via the ``op``-tagged
``consolidate:mm`` record. This locks the capacity-level behaviour directly.
"""

import json

from mindsos_capacity import CapacityLayer, DS_MM_COMPOSITE_INSTANCE
from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
from mindsos_intelligence import consolidation
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
from mindsos_knowledge.metagraph_view import MetagraphView
from mindsos_knowledge.schemas.episodic_memories import (
    EPISODE_STATE_CLOSED,
    EPISODE_STATE_OPEN,
    EPISODE_STATE_SUSPENDED,
)
from tests.phase_33._fixtures import build_session_with_caps

_TP = "request-pattern-v1:pattern:greet"


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


def _one(kl):
    eps = _episodes(kl)
    assert len(eps) == 1
    return eps[0]


def _close(dispatcher, episode_id, **props):
    record = {
        DS_MM_COMPOSITE_INSTANCE: {
            "episode_id": episode_id,
            "value": {"op": "close", "props": props},
        }
    }
    return dispatcher.dispatch(
        "capacity:consolidate:mm", record, request_id=episode_id
    )


def test_open_creates_open_episode_with_fields_as_properties():
    kl = KnowledgeLayer.bootstrap()
    d = _dispatcher(kl)
    consolidation.open_episode(
        d, episode_id="e1", request_input_ref="ri:e1", request_input_root_ref="root:e1"
    )
    node = _one(kl)
    assert node.value == "e1"  # node value IS the episode_id
    assert node.properties["state"] == EPISODE_STATE_OPEN
    assert node.properties["request_input_ref"] == "ri:e1"
    assert node.properties["request_input_root_ref"] == "root:e1"
    # No terminal content yet.
    assert node.properties.get("outcome_classification") is None


def test_open_is_idempotent():
    kl = KnowledgeLayer.bootstrap()
    d = _dispatcher(kl)
    consolidation.open_episode(d, episode_id="e1")
    consolidation.open_episode(d, episode_id="e1")
    assert len(_episodes(kl)) == 1
    assert _one(kl).properties["state"] == EPISODE_STATE_OPEN


def test_suspend_flips_state_only():
    kl = KnowledgeLayer.bootstrap()
    d = _dispatcher(kl)
    consolidation.open_episode(d, episode_id="e1", request_input_ref="ri:e1")
    consolidation.suspend_episode(d, episode_id="e1")
    node = _one(kl)
    assert node.properties["state"] == EPISODE_STATE_SUSPENDED
    # The open anchor is preserved (metadata-only edit).
    assert node.properties["request_input_ref"] == "ri:e1"


def test_close_upserts_content_flips_state_and_materialises_memory():
    kl = KnowledgeLayer.bootstrap()
    d = _dispatcher(kl)
    consolidation.open_episode(d, episode_id="e1", request_input_ref="ri:e1")
    _close(
        d,
        "e1",
        state=EPISODE_STATE_CLOSED,
        mm_root_ref="mm:e1",
        request_pattern_iri=_TP,
        outcome_classification="succeeded",
        crash_marker=None,
        consolidated_at="2026-07-28T00:00:00Z",
    )
    node = _one(kl)
    assert node.properties["state"] == EPISODE_STATE_CLOSED
    assert node.properties["outcome_classification"] == "succeeded"
    assert node.properties["mm_root_ref"] == "mm:e1"
    assert node.properties["request_input_ref"] == "ri:e1"  # preserved from open
    # Memory materialised on close (one Memory node + its containment edge).
    g = MetagraphView(kl.local_metagraph("alice")).graphs_by_role(
        ROLE_EPISODIC_MEMORIES
    )[0]
    assert [n for n in g.nodes.values() if n.type_name == "Memory"]


def test_close_without_prior_open_creates_whole_episode():
    kl = KnowledgeLayer.bootstrap()
    d = _dispatcher(kl)
    _close(
        d,
        "e1",
        mm_root_ref="mm:e1",
        outcome_classification="conceded",
        consolidated_at="2026-07-28T00:00:00Z",
    )
    node = _one(kl)
    # ``state`` defaults to closed on a close write that omitted it.
    assert node.properties["state"] == EPISODE_STATE_CLOSED
    assert node.properties["outcome_classification"] == "conceded"


def test_crash_marker_dict_is_json_encoded_property():
    kl = KnowledgeLayer.bootstrap()
    d = _dispatcher(kl)
    _close(
        d,
        "e1",
        outcome_classification="failed",
        crash_marker={"recovered": True, "detected_at": "x"},
    )
    raw = _one(kl).properties["crash_marker"]
    assert isinstance(raw, str)  # dicts are not L1-primitive → JSON-encoded
    assert json.loads(raw)["recovered"] is True
