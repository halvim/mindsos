"""Phase 48 S2/S3 — ``consolidate:mm`` writes the Episode + materialises the
Memory composite + the ``MEMORY_CONTAINS_EPISODE`` edge (ADR-0176 §1/§3;
Chat B D-B47 §4.6).

Dispatched through ``L4Dispatcher`` (the pre-authorized ``context.writeable``
capability path, ADR-0180). The Episode ``value`` carries the 6-field D-B47
record assembled by L4 consolidation (the L4 ``consolidation.py`` assembler
lands in commit-group 3; here the record is constructed directly).
"""

from mindsos_capacity import CapacityLayer, DS_MM_COMPOSITE_INSTANCE
from mindsos_capacity.builtins.consolidate import (
    _memory_id_for,
    install_consolidate_capacities,
)
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES, memory_composite_iri
from mindsos_knowledge.metagraph_view import MetagraphView
from mindsos_knowledge.schemas.episodic_memories import EDGE_MEMORY_CONTAINS_EPISODE
from tests.phase_33._fixtures import build_session_with_caps

_TP = "task-pattern-v1:pattern:greet"


def _record(episode_id, task_pattern_iri=_TP):
    return {
        DS_MM_COMPOSITE_INSTANCE: {
            "episode_id": episode_id,
            "value": {
                "task_input_ref": "xref:ti",
                "mm_root_ref": "xref:mm",
                "task_pattern_iri": task_pattern_iri,
                "outcome_classification": "succeeded",
                "crash_marker": None,
                "consolidated_at": "2026-06-09T00:00:00Z",
            },
        }
    }


def _layer_dispatcher(kl, sess):
    layer = CapacityLayer(kl=kl)
    install_consolidate_capacities(layer)
    return L4Dispatcher(layer, session=sess, kl=kl)


def test_episode_written_and_memory_materialised_with_edge():
    kl = KnowledgeLayer.bootstrap()
    sess = build_session_with_caps("alice", frozenset())  # Local write, no cap
    result = _layer_dispatcher(kl, sess).dispatch(
        "capacity:consolidate:mm", _record("e1"), task_id="T"
    )
    assert result.success is True
    episode_iri = result.write_outcome.iri

    view = MetagraphView(kl.local_metagraph("alice"))
    memory_iri = memory_composite_iri("v1", "alice", _memory_id_for(_TP))
    assert view.get_node(ROLE_EPISODIC_MEMORIES, memory_iri) is not None
    edges = view.get_edges(
        ROLE_EPISODIC_MEMORIES, memory_iri, edge_type=EDGE_MEMORY_CONTAINS_EPISODE
    )
    assert any(e.target.node_id == episode_iri for e in edges)


def test_memory_materialises_once_per_pattern():
    kl = KnowledgeLayer.bootstrap()
    sess = build_session_with_caps("alice", frozenset())
    d = _layer_dispatcher(kl, sess)
    d.dispatch("capacity:consolidate:mm", _record("e1"), task_id="T1")
    d.dispatch("capacity:consolidate:mm", _record("e2"), task_id="T2")

    view = MetagraphView(kl.local_metagraph("alice"))
    g = view.graphs_by_role(ROLE_EPISODIC_MEMORIES)[0]
    memories = [n for n in g.nodes.values() if n.type_name == "Memory"]
    episodes = [n for n in g.nodes.values() if n.type_name == "Episode"]
    assert len(memories) == 1  # one Memory per task-pattern
    assert len(episodes) == 2

    memory_iri = memory_composite_iri("v1", "alice", _memory_id_for(_TP))
    edges = view.get_edges(
        ROLE_EPISODIC_MEMORIES, memory_iri, edge_type=EDGE_MEMORY_CONTAINS_EPISODE
    )
    assert len(edges) == 2  # both episodes attached


def test_bare_value_writes_episode_without_memory():
    """Backward-compat: a non-dict value (no task_pattern_iri) writes the
    Episode and materialises no Memory."""
    kl = KnowledgeLayer.bootstrap()
    sess = build_session_with_caps("alice", frozenset())
    result = _layer_dispatcher(kl, sess).dispatch(
        "capacity:consolidate:mm",
        {DS_MM_COMPOSITE_INSTANCE: {"episode_id": "e1", "value": "bare"}},
        task_id="T",
    )
    assert result.success is True
    view = MetagraphView(kl.local_metagraph("alice"))
    g = view.graphs_by_role(ROLE_EPISODIC_MEMORIES)[0]
    assert [n for n in g.nodes.values() if n.type_name == "Memory"] == []
