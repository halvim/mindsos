"""Chain artifacts — the 6-level reasoning chain in intelligence-MM.

Chat B D-B22 settled an immutable chain of artifacts authored by L4 into
the intelligence sub-MM: HintSet -> MappingResult -> Plan(+Milestone tree)
-> Pipeline -> PipelineRun -> TaskRun, plus the provenance composites
ReplanRecord + StepExecutionRecord. Phase 47 emits them as nodes in a
``chain`` graph inside ``mm.intelligence_mm`` under the MM writer lock
(no shadow state outside the MM — Chat B D-B11).

The dataclasses carry the load-bearing fields from
``l5_mental_model_design_notes §2``; v0 omits the fields whose only
consumer is Phase 48 consolidation. ``ReplanVerdict`` / ``BlameVerdict``
are the verdict shapes the replan-check + Phase-6 dispatch map into.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mindsos_core import Graph

from .mm import MentalModel

CHAIN_GRAPH_ROLE = "chain"

TYPE_HINT_SET = "HintSet"
TYPE_MAPPING_RESULT = "MappingResult"
TYPE_PLAN = "Plan"
TYPE_MILESTONE = "Milestone"
TYPE_PIPELINE = "Pipeline"
TYPE_PIPELINE_RUN = "PipelineRun"
TYPE_TASK_RUN = "TaskRun"
TYPE_REPLAN_RECORD = "ReplanRecord"
TYPE_STEP_EXECUTION_RECORD = "StepExecutionRecord"

CHAIN_ARTIFACT_TYPES = (
    TYPE_HINT_SET,
    TYPE_MAPPING_RESULT,
    TYPE_PLAN,
    TYPE_MILESTONE,
    TYPE_PIPELINE,
    TYPE_PIPELINE_RUN,
    TYPE_TASK_RUN,
    TYPE_REPLAN_RECORD,
    TYPE_STEP_EXECUTION_RECORD,
)


# ── Verdict shapes (dispatch results) ─────────────────────────────────


@dataclass
class ReplanVerdict:
    decision: str  # "continue" | "replan" | "abort"
    verified: bool = True
    divergence: float = 0.0


@dataclass
class BlameVerdict:
    chain_level: str  # hint | map | plan | plan_subtree | pipeline
    blame_score: float
    rationale: str
    milestone_ref: Optional[str] = None
    capacity_step_ref: Optional[str] = None


# ── Chain artifact dataclasses ────────────────────────────────────────


@dataclass
class HintSet:
    iri: str
    hints: Dict[str, Any] = field(default_factory=dict)
    phase: str = "1_task_interpretation"


@dataclass
class MappingResult:
    iri: str
    hint_set_ref: Optional[str]
    selected_task_pattern_iri: Optional[str]
    mapping_confidence: float


@dataclass
class Milestone:
    iri: str
    name: str
    sequence_index: int
    parent_ref: Optional[str] = None
    is_leaf: bool = True
    children_refs: List[str] = field(default_factory=list)
    pipeline_ref: Optional[str] = None
    status: str = "pending"
    output_data_state_ref: Optional[str] = None
    replans_used: int = 0


@dataclass
class Plan:
    iri: str
    root_milestone_ref: Optional[str]
    mapping_result_ref: Optional[str]


@dataclass
class Pipeline:
    iri: str
    plan_ref: Optional[str]
    milestone_ref: Optional[str]


@dataclass
class PipelineRun:
    iri: str
    pipeline_ref: Optional[str]
    milestone_ref: Optional[str]
    task_run_ref: Optional[str]
    status: str = "running"


@dataclass
class TaskRun:
    iri: str
    task_input_ref: Optional[str] = None
    plan_ref: Optional[str] = None
    pipeline_runs: List[str] = field(default_factory=list)
    replan_history: List[str] = field(default_factory=list)
    status: str = "running"
    attention_score: int = 0


@dataclass
class ReplanRecord:
    iri: str
    replan_level: str
    verdict: ReplanVerdict
    replan_milestone_ref: Optional[str] = None
    invalidated_refs: List[str] = field(default_factory=list)
    spawned_refs: List[str] = field(default_factory=list)


@dataclass
class StepExecutionRecord:
    iri: str
    capacity_iri: str
    pipeline_run_ref: Optional[str] = None
    milestone_ref: Optional[str] = None
    confidence: Optional[float] = None


# ── Writer — emits artifacts into intelligence-MM under the MM lock ───


def _chain_graph(mm: MentalModel) -> Graph:
    for g in mm.intelligence_mm.graphs.values():
        if g.role == CHAIN_GRAPH_ROLE:
            return g
    g = Graph(name="chain", role=CHAIN_GRAPH_ROLE)
    mm.intelligence_mm.add_graph(g)
    return g


class ChainArtifactWriter:
    """Mints chain-artifact IRIs and emits them into intelligence-MM.

    One per TaskRun. All writes acquire the MM writer lock (D32.3) so
    chain emission is serialized against worker-thread MM reads.
    """

    def __init__(self, mm: MentalModel, task_scope: str) -> None:
        self._mm = mm
        self._scope = task_scope
        self._seq = 0

    def _mint(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}:{self._scope}:{self._seq}"

    def _emit(self, iri: str, type_name: str, artifact: Any) -> str:
        with self._mm.lock.write_locked():
            _chain_graph(self._mm).add_node(
                value=artifact, type_name=type_name, node_id=iri
            )
        return iri

    def emit_hint_set(self, hints: Dict[str, Any]) -> HintSet:
        art = HintSet(iri=self._mint("hintset"), hints=dict(hints))
        self._emit(art.iri, TYPE_HINT_SET, art)
        return art

    def emit_mapping_result(
        self, hint_set_ref, task_pattern_iri, confidence
    ) -> MappingResult:
        art = MappingResult(
            iri=self._mint("mappingresult"),
            hint_set_ref=hint_set_ref,
            selected_task_pattern_iri=task_pattern_iri,
            mapping_confidence=confidence,
        )
        self._emit(art.iri, TYPE_MAPPING_RESULT, art)
        return art

    def emit_milestone(
        self, name, sequence_index, *, parent_ref=None, is_leaf=True
    ) -> Milestone:
        art = Milestone(
            iri=self._mint("milestone"),
            name=name,
            sequence_index=sequence_index,
            parent_ref=parent_ref,
            is_leaf=is_leaf,
        )
        self._emit(art.iri, TYPE_MILESTONE, art)
        return art

    def emit_plan(self, root_milestone_ref, mapping_result_ref) -> Plan:
        art = Plan(
            iri=self._mint("plan"),
            root_milestone_ref=root_milestone_ref,
            mapping_result_ref=mapping_result_ref,
        )
        self._emit(art.iri, TYPE_PLAN, art)
        return art

    def emit_pipeline(self, plan_ref, milestone_ref) -> Pipeline:
        art = Pipeline(
            iri=self._mint("pipeline"),
            plan_ref=plan_ref,
            milestone_ref=milestone_ref,
        )
        self._emit(art.iri, TYPE_PIPELINE, art)
        return art

    def emit_pipeline_run(
        self, pipeline_ref, milestone_ref, task_run_ref, status="running"
    ) -> PipelineRun:
        art = PipelineRun(
            iri=self._mint("pipelinerun"),
            pipeline_ref=pipeline_ref,
            milestone_ref=milestone_ref,
            task_run_ref=task_run_ref,
            status=status,
        )
        self._emit(art.iri, TYPE_PIPELINE_RUN, art)
        return art

    def emit_task_run(self, *, task_input_ref=None, plan_ref=None) -> TaskRun:
        art = TaskRun(
            iri=self._mint("taskrun"),
            task_input_ref=task_input_ref,
            plan_ref=plan_ref,
        )
        self._emit(art.iri, TYPE_TASK_RUN, art)
        self._mm.root.task_run_ref = art.iri
        return art

    def emit_replan_record(
        self, replan_level, verdict, *, replan_milestone_ref=None,
        invalidated_refs=None, spawned_refs=None
    ) -> ReplanRecord:
        art = ReplanRecord(
            iri=self._mint("replanrecord"),
            replan_level=replan_level,
            verdict=verdict,
            replan_milestone_ref=replan_milestone_ref,
            invalidated_refs=list(invalidated_refs or []),
            spawned_refs=list(spawned_refs or []),
        )
        self._emit(art.iri, TYPE_REPLAN_RECORD, art)
        return art

    def emit_step_execution_record(
        self, capacity_iri, *, pipeline_run_ref=None, milestone_ref=None,
        confidence=None
    ) -> StepExecutionRecord:
        art = StepExecutionRecord(
            iri=self._mint("stepexecutionrecord"),
            capacity_iri=capacity_iri,
            pipeline_run_ref=pipeline_run_ref,
            milestone_ref=milestone_ref,
            confidence=confidence,
        )
        self._emit(art.iri, TYPE_STEP_EXECUTION_RECORD, art)
        return art


def iter_chain_artifacts(mm: MentalModel, type_name: Optional[str] = None):
    """Yield ``(node_id, value)`` for chain artifacts in intelligence-MM,
    optionally filtered by ``type_name``."""
    with mm.lock.read_locked():
        for g in mm.intelligence_mm.graphs.values():
            if g.role != CHAIN_GRAPH_ROLE:
                continue
            for node in g.nodes.values():
                if type_name is None or node.type_name == type_name:
                    yield node.node_id, node.value


__all__ = [
    "CHAIN_GRAPH_ROLE",
    "CHAIN_ARTIFACT_TYPES",
    "TYPE_HINT_SET",
    "TYPE_MAPPING_RESULT",
    "TYPE_PLAN",
    "TYPE_MILESTONE",
    "TYPE_PIPELINE",
    "TYPE_PIPELINE_RUN",
    "TYPE_TASK_RUN",
    "TYPE_REPLAN_RECORD",
    "TYPE_STEP_EXECUTION_RECORD",
    "ReplanVerdict",
    "BlameVerdict",
    "HintSet",
    "MappingResult",
    "Milestone",
    "Plan",
    "Pipeline",
    "PipelineRun",
    "TaskRun",
    "ReplanRecord",
    "StepExecutionRecord",
    "ChainArtifactWriter",
    "iter_chain_artifacts",
]
