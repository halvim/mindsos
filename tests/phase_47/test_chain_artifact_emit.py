"""Phase 47 — chain artifacts emit into intelligence-MM (Chat B D-B22).

All 9 chain composite types (the 8 chain levels + Milestone) are emitted
as nodes in the ``chain`` graph of intelligence-MM, under the MM writer
lock, with no shadow state outside the MM.
"""

from __future__ import annotations

from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.chain_artifacts import (
    CHAIN_ARTIFACT_TYPES,
    ChainArtifactWriter,
    ReplanVerdict,
    TYPE_HINT_SET,
    TYPE_MAPPING_RESULT,
    TYPE_MILESTONE,
    TYPE_PLAN,
    TYPE_PIPELINE,
    TYPE_PIPELINE_RUN,
    TYPE_TASK_RUN,
    TYPE_REPLAN_RECORD,
    TYPE_STEP_EXECUTION_RECORD,
    iter_chain_artifacts,
)


def _mm():
    return MentalModel(session_id="s", user_id="u")


def test_emit_full_chain_into_intelligence_mm():
    mm = _mm()
    w = ChainArtifactWriter(mm, "task-1")

    hs = w.emit_hint_set({"hint.modality": "text"})
    mr = w.emit_mapping_result(hs.iri, "task-pattern:v0:trivial", 1.0)
    root = w.emit_milestone("root", 0, is_leaf=True)
    plan = w.emit_plan(root.iri, mr.iri)
    tr = w.emit_request_run(plan_ref=plan.iri)
    pipe = w.emit_pipeline(plan.iri, root.iri)
    pr = w.emit_pipeline_run(pipe.iri, root.iri, tr.iri)
    w.emit_step_execution_record("capacity:planning:derive_initial_plan", pipeline_run_ref=pr.iri)
    w.emit_replan_record("pipeline", ReplanVerdict("replan"), invalidated_refs=[pr.iri])

    # every chain composite type is present in intelligence-MM
    emitted_types = {
        node_type
        for node_type in CHAIN_ARTIFACT_TYPES
        if any(True for _ in iter_chain_artifacts(mm, node_type))
    }
    assert emitted_types == set(CHAIN_ARTIFACT_TYPES)


def test_task_run_ref_recorded_on_root():
    mm = _mm()
    w = ChainArtifactWriter(mm, "task-2")
    tr = w.emit_request_run()
    assert mm.root.task_run_ref == tr.iri


def test_iter_filters_by_type():
    mm = _mm()
    w = ChainArtifactWriter(mm, "task-3")
    w.emit_hint_set({})
    w.emit_hint_set({"a": 1})
    w.emit_plan(None, None)
    hint_sets = list(iter_chain_artifacts(mm, TYPE_HINT_SET))
    plans = list(iter_chain_artifacts(mm, TYPE_PLAN))
    assert len(hint_sets) == 2
    assert len(plans) == 1


def test_artifacts_live_in_intelligence_sub_mm_only():
    mm = _mm()
    w = ChainArtifactWriter(mm, "task-4")
    w.emit_request_run()
    # nothing leaked into knowledge-/capacity-MM
    assert sum(len(g.nodes) for g in mm.knowledge_mm.graphs.values()) == 0
    assert sum(len(g.nodes) for g in mm.capacity_mm.graphs.values()) == 0
    assert sum(len(g.nodes) for g in mm.intelligence_mm.graphs.values()) == 1
