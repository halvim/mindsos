"""Phase 47 — trivial-task end-to-end smoke (control-flow only).

enqueue-equivalent: run_lifecycle over the v0 catalog produces a single-
Milestone Plan, executes it, and returns succeeded; the full chain is
emitted to intelligence-MM. Real consolidation is Phase 48 (stub seam).
"""

from __future__ import annotations

from mindsos_intelligence.chain_artifacts import (
    TYPE_HINT_SET,
    TYPE_MAPPING_RESULT,
    TYPE_PIPELINE,
    TYPE_PIPELINE_RUN,
    TYPE_PLAN,
    TYPE_TASK_RUN,
    iter_chain_artifacts,
)

from ._fixtures import make_orchestrator


def test_trivial_task_runs_end_to_end():
    orch, mm, _layer = make_orchestrator()
    outcome = orch.run_lifecycle({"text": "hello world"})

    assert outcome.status == "succeeded"
    assert outcome.outcome == "task-pattern:v0:trivial"
    assert outcome.replans_used == 0
    assert mm.root.task_run_ref == outcome.task_run_ref

    for t in (
        TYPE_HINT_SET,
        TYPE_MAPPING_RESULT,
        TYPE_PLAN,
        TYPE_PIPELINE,
        TYPE_PIPELINE_RUN,
        TYPE_TASK_RUN,
    ):
        assert any(True for _ in iter_chain_artifacts(mm, t)), f"missing {t}"


def test_attention_score_written_through_to_task_run():
    orch, mm, _layer = make_orchestrator()
    outcome = orch.run_lifecycle({"text": "hi"})
    task_runs = dict(iter_chain_artifacts(mm, TYPE_TASK_RUN))
    tr = task_runs[outcome.task_run_ref]
    # FOREGROUND cold-start constant (DEFAULT_TIER_SCORES) = 500
    assert tr.attention_score == 500


def test_simplified_mode_skips_verification():
    orch, mm, _layer = make_orchestrator(simplified=True)
    outcome = orch.run_lifecycle({"text": "hi"})
    assert outcome.status == "succeeded"
