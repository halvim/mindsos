"""LifecyclePhase 3-5 — execution (DFS Milestone order, ADR-0171).

Walks the Plan's leaf Milestones in DFS order; per leaf emits a
PipelineRun, "runs" the leaf Pipeline, and emits a StepExecutionRecord per
L3 capacity invocation. MSUR + SCMS are L3 orchestration capacities whose
bodies ship in WSD installation — at Phase 47 their hooks are absent and
the loop tolerates it (sibling-sequential v1; child-failure fail-fast v1).
"""

from __future__ import annotations

from typing import List


def run(dispatcher, writer, plan_result, task_run) -> List[str]:
    pipeline_run_refs: List[str] = []
    for leaf_ref in plan_result.leaf_milestone_refs:
        pipeline_ref = plan_result.pipeline_refs[leaf_ref]
        pr = writer.emit_pipeline_run(pipeline_ref, leaf_ref, task_run.iri)
        # MSUR / SCMS orchestration hooks: absent at Phase 47 (WSD bodies).
        # v0 Pipeline has no real capacity steps; emit one notional step
        # record so the PipelineRun has provenance.
        writer.emit_step_execution_record(
            pipeline_ref,
            pipeline_run_ref=pr.iri,
            milestone_ref=leaf_ref,
            confidence=1.0,
        )
        pr.status = "completed"
        pipeline_run_refs.append(pr.iri)
        task_run.pipeline_runs.append(pr.iri)
    return pipeline_run_refs


__all__ = ["run"]
