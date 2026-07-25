"""Phase 48 S9 — retention monitoring instrumentation (Chat B §7 R1 / PB-QQ).

Instrumentation only: episode count + size histogram + Memory count +
Falkor-row count. No retention policy / eviction at v1.
"""

from mindsos_capacity import CapacityLayer, DS_MM_COMPOSITE_INSTANCE
from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.monitoring import export_retention_metrics
from mindsos_knowledge import KnowledgeLayer
from tests.phase_33._fixtures import build_session_with_caps

_TP = "task-pattern-v1:pattern:greet"


def _write_episode(dispatcher, episode_id, task_pattern_iri=_TP):
    record = {
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
    dispatcher.dispatch("capacity:consolidate:mm", record, request_id=episode_id)


def test_metrics_zero_for_fresh_user():
    kl = KnowledgeLayer.bootstrap()
    m = export_retention_metrics(kl, "alice")
    assert m.episode_count == 0
    assert m.memory_count == 0
    assert m.falkor_row_count == 0


def test_metrics_count_episodes_memories_and_rows():
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_consolidate_capacities(layer)
    d = L4Dispatcher(layer, session=build_session_with_caps("alice", frozenset()), kl=kl)
    _write_episode(d, "e1")
    _write_episode(d, "e2")  # same task-pattern -> still one Memory

    m = export_retention_metrics(kl, "alice")
    assert m.episode_count == 2
    assert m.memory_count == 1
    assert sum(m.size_histogram.values()) == 2
    # 2 Episodes + 1 Memory + 2 MEMORY_CONTAINS_EPISODE edges
    assert m.falkor_row_count == 5
