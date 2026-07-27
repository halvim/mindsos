"""Collection-iteration Slice 3 — targeted (per-member) replan/diagnosis address.

Slices 1a/1b/2 gave every executed leaf an isolated grounding *ref-path*
(``pipelinerun:{scope}:…:m{i}:…``) — a locatable member address. Slice 3 lets a
real consumer (arc) put that address on its ``decision.should_replan`` verdict,
so replan/diagnosis can name the suspect member instead of the whole pipeline.

**This slice is addressing only.** Replan *execution* stays whole-pipeline
(clear-all): the advisory target is (a) recorded on the ``ReplanRecord``
(``replan_milestone_ref``) for member-scoped audit, and (b) fed into Phase-6
diagnosis (``attribute_blame`` input) so blame can be member-scoped
(``BlameVerdict.milestone_ref``). It does NOT scope what re-runs — targeted
re-execution reverses Slice-1a's attempt-scoped blackboard and is a later slice.

Inertness: a v0 verdict names no target, so ``replan_check.check`` yields
``target_ref=None``/``replan_level=None``, the ``ReplanRecord`` records
``replan_milestone_ref=None`` at ``replan_level="pipeline"`` (the actual action),
and diagnosis dispatches ``{}`` exactly as before — byte-identical.

No Falkor (a fake persister stands in), mirroring
``tests/phase_48/test_step5_solve_execution.py``.
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins import install_phase1_v0
from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
from mindsos_capacity.builtins.orchestration_v0 import (
    DS_BLAME,
    DS_BLAME_INPUT,
    DS_REPLAN_STATE,
    DS_REPLAN_VERDICT,
    build_attention_score,
    build_signal_to_tier,
    build_sufficient,
    install_orchestration_v0,
    reset_v0_verdicts,
    set_should_replan_decision,
    set_sufficient_result,
)
from mindsos_capacity.builtins.planning_v0 import (
    DS_MAPPING_RESULT,
    DS_PLAN,
    build_aggregate_outputs,
    build_decompose,
    build_is_leaf,
    planning_datastates,
)
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_DECISION,
    CATEGORY_DERIVATION,
    CATEGORY_PHASE6,
    CATEGORY_PLANNING,
    capacity_iri,
    datastate_iri,
)

from mindsos_intelligence import replan_check
from mindsos_intelligence.chain_artifacts import TYPE_REPLAN_RECORD, iter_chain_artifacts
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.orchestrator import Orchestrator

DS_RAW = datastate_iri("s3.raw_task")
DS_ANSWER = datastate_iri("s3.answer")
SOLVE_IRI = capacity_iri(CATEGORY_DERIVATION, "s3_solve")

_TARGET_REF = "pipelinerun:task-1:0:m2:0:r0"  # a Slice-2 member ref-path
_ANSWER_VALUE = {"answer": [[7]]}


class FakeSession:
    def __init__(self, user_id="u", caps=()):
        self.session_id = "s"
        self.user_id = user_id
        self.actor_role = "user"
        self.capabilities = set(caps)

    def has(self, capability: str) -> bool:
        return capability in self.capabilities


# ── unit: replan_check.check carries the advisory target ────────────────────


class _Res:
    def __init__(self, outputs):
        self.outputs = outputs


class _VerdictDispatcher:
    """Returns a fixed ``should_replan`` verdict dict."""

    def __init__(self, verdict):
        self._v = verdict

    def dispatch(self, iri, inputs, **kw):
        return _Res({DS_REPLAN_VERDICT: self._v})


def test_check_carries_advisory_target_when_present():
    out = replan_check.check(
        _VerdictDispatcher(
            {
                "decision": "replan",
                "verified": True,
                "divergence": 0.0,
                "replan_level": "plan_subtree",
                "target_ref": _TARGET_REF,
            }
        )
    )
    assert out.decision == "replan"
    assert out.replan_level == "plan_subtree"
    assert out.target_ref == _TARGET_REF


def test_check_defaults_none_when_target_absent():
    """v0 verdict shape (no target) → None/None → byte-identical."""
    out = replan_check.check(_VerdictDispatcher({"decision": "continue"}))
    assert out.decision == "continue"
    assert out.replan_level is None
    assert out.target_ref is None


# ── integration scaffold (mirrors test_step5_solve_execution) ───────────────


def _solve_body(**kwargs):
    return {DS_ANSWER: _ANSWER_VALUE}


def _register_solve(layer, *, session=None):
    for name in ("s3.raw_task", "s3.answer"):
        layer.register_datastate(
            DataState(
                name=name,
                shape=ShapeDescriptor.opaque(name),
                description=name,
                provenance_category=CATEGORY_DERIVATION,
            ),
            session=session,
            allow_new_realm=True,
        )
    layer.register_capacity(
        Capacity(
            name="s3_solve",
            category=CATEGORY_DERIVATION,
            inputs=(DS_RAW,),
            outputs=(DS_ANSWER,),
            implementation=_solve_body,
            description="test solve: raw_task -> answer",
        ),
        session=session,
    )


def _install_solve_planning(layer):
    for ds in planning_datastates():
        layer.register_datastate(ds, allow_new_realm=True)

    def _derive(**kwargs):
        return {
            DS_PLAN: {
                "root_milestone": {"name": "root", "is_leaf": True},
                "single_milestone": True,
                "solve_target": {
                    "start_datastate": DS_RAW,
                    "target_datastate": DS_ANSWER,
                },
            }
        }

    layer.register_capacity(
        Capacity(
            name="derive_initial_plan",
            category=CATEGORY_PLANNING,
            inputs=(DS_MAPPING_RESULT,),
            outputs=(DS_PLAN,),
            implementation=_derive,
            description="test: single-Milestone plan naming a solve_target",
            placeholder=True,
        )
    )
    layer.register_capacity(build_decompose())
    layer.register_capacity(build_is_leaf())
    layer.register_capacity(build_aggregate_outputs())


class _FakePersister:
    def persist(self, metagraph, graph, *, node_value_encoder=None):
        pass


class _TargetedOrchState:
    """Mutable state for the custom targeted orchestration capacities."""

    replan_calls = 0
    blame_inputs: list = []

    @classmethod
    def reset(cls):
        cls.replan_calls = 0
        cls.blame_inputs = []


def _targeted_should_replan(**kwargs):
    """Replan once (naming a member via the reserved level + ref-path), then
    continue. The advisory target rides every verdict."""
    _TargetedOrchState.replan_calls += 1
    decision = "replan" if _TargetedOrchState.replan_calls == 1 else "continue"
    return {
        DS_REPLAN_VERDICT: {
            "decision": decision,
            "verified": True,
            "divergence": 0.0,
            "replan_level": "plan_subtree",
            "target_ref": _TARGET_REF,
        }
    }


def _capturing_attribute_blame(**kwargs):
    """Capture the DS_BLAME_INPUT the orchestrator fed us, and return a
    member-scoped BlameVerdict."""
    _TargetedOrchState.blame_inputs.append(kwargs.get(DS_BLAME_INPUT))
    return {
        DS_BLAME: {
            "chain_level": "plan_subtree",
            "milestone_ref": _TARGET_REF,
            "capacity_step_ref": None,
            "blame_score": 1.0,
            "rationale": "targeted at member",
        }
    }


def _fresh_targeted_layer(kl):
    layer = CapacityLayer(kl=kl)
    _install_solve_planning(layer)
    install_phase1_v0(layer)
    # Orchestration: register datastates via the v0 installer's datastate set,
    # then our 5 capacities (3 standard + 2 custom) under the canonical IRIs.
    from mindsos_capacity.builtins.orchestration_v0 import _orchestration_datastates

    for ds in _orchestration_datastates():
        layer.register_datastate(ds, allow_new_realm=True)
    layer.register_capacity(build_signal_to_tier())
    layer.register_capacity(build_attention_score())
    layer.register_capacity(build_sufficient())
    layer.register_capacity(
        Capacity(
            name="should_replan",
            category=CATEGORY_DECISION,
            inputs=(DS_REPLAN_STATE,),
            outputs=(DS_REPLAN_VERDICT,),
            implementation=_targeted_should_replan,
            description="test: targeted replan verdict",
            placeholder=True,
        )
    )
    layer.register_capacity(
        Capacity(
            name="attribute_blame",
            category=CATEGORY_PHASE6,
            inputs=(DS_BLAME_INPUT,),
            outputs=(DS_BLAME,),
            implementation=_capturing_attribute_blame,
            description="test: capturing blame verdict",
            placeholder=True,
        )
    )
    install_consolidate_capacities(layer)
    _register_solve(layer, session=FakeSession())
    return layer


def _replan_records(mm):
    return [v for _, v in iter_chain_artifacts(mm, TYPE_REPLAN_RECORD)]


def test_advisory_target_flows_to_replan_record_and_diagnosis():
    from mindsos_knowledge import KnowledgeLayer

    _TargetedOrchState.reset()
    reset_v0_verdicts()
    set_sufficient_result(False)  # drive the dont-know / diagnosis path
    try:
        kl = KnowledgeLayer.bootstrap()
        layer = _fresh_targeted_layer(kl)
        mm = MentalModel(session_id="s", user_id="u")
        disp = L4Dispatcher(layer, session=FakeSession(), kl=kl)
        orch = Orchestrator(disp, mm, task_scope="task-1", mm_persister=_FakePersister())
        outcome = orch.run_lifecycle("hello", request_id="T")
    finally:
        reset_v0_verdicts()
        set_sufficient_result(True)

    assert outcome.status == "dont_know"

    # (a) The advisory target reached the ReplanRecord. Exactly one replan fired
    # (replan-once-then-continue). The RECORDED replan_level is "pipeline" (the
    # actual whole-pipeline action) — never a finer level that would contradict
    # a full clear — while replan_milestone_ref carries the advisory member
    # address, and the verdict itself preserves the consumer's plan_subtree level.
    records = _replan_records(mm)
    assert len(records) == 1
    rec = records[0]
    assert rec.replan_level == "pipeline"
    assert rec.replan_milestone_ref == _TARGET_REF
    assert rec.invalidated_refs  # whole-pipeline clear still records the refs
    assert rec.verdict.replan_level == "plan_subtree"
    assert rec.verdict.target_ref == _TARGET_REF

    # (b) The advisory target reached Phase-6 diagnosis — the orchestrator fed
    # the member address into attribute_blame's input, and the member-scoped
    # blame propagated to the outcome.
    assert _TargetedOrchState.blame_inputs == [
        {"target_ref": _TARGET_REF, "replan_level": "plan_subtree"}
    ]
    assert outcome.blame.milestone_ref == _TARGET_REF
    assert outcome.blame.chain_level == "plan_subtree"


def test_v0_replan_record_has_no_target_byte_identical():
    """v0 verdicts name no member → ReplanRecord.replan_milestone_ref is None,
    replan_level stays 'pipeline', and diagnosis is fed no target. Byte-identical
    to the pre-Slice-3 record + diagnosis path."""
    from mindsos_knowledge import KnowledgeLayer

    reset_v0_verdicts()
    set_should_replan_decision("replan")  # force the replan-record path
    set_sufficient_result(False)  # then dont-know
    try:
        sess = FakeSession()
        kl = KnowledgeLayer.bootstrap()
        layer = CapacityLayer(kl=kl)
        _install_solve_planning(layer)
        install_phase1_v0(layer)
        install_orchestration_v0(layer)  # standard v0 (no target on the verdict)
        install_consolidate_capacities(layer)
        _register_solve(layer, session=sess)
        mm = MentalModel(session_id="s", user_id="u")
        disp = L4Dispatcher(layer, session=sess, kl=kl)
        orch = Orchestrator(disp, mm, task_scope="task-1")
        outcome = orch.run_lifecycle("hello", request_id="T")
    finally:
        reset_v0_verdicts()

    assert outcome.status == "dont_know"
    records = _replan_records(mm)
    # Budget-bounded replans (default 5), each recorded with NO advisory target.
    assert records
    assert all(r.replan_milestone_ref is None for r in records)
    assert all(r.replan_level == "pipeline" for r in records)
    # v0 blame verdict is whole-pipeline (unchanged).
    assert outcome.blame.chain_level == "pipeline"
    assert outcome.blame.milestone_ref is None
