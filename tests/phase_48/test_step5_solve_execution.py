"""Out-of-CR Step 5 — the solve path activates the L5 capacity writer + persist.

Steps 1-4 built the capacity_mm grounding writer + Slice-B persist + the
knowledge writer, all inert in prod. Step 5 wires ``execution.run`` to find and
run the real leaf pipeline via ``execute_pipeline`` (grounding the resolved task
into ``capacity_mm``) and threads the per-run graph into ``consolidate_task`` so
persist fires. These tests exercise that activation over a synthetic solve
capacity + a plan that names a ``solve_target`` — no Falkor (a fake persister
stands in for the durable path; the live edge-aware round-trip is already
covered by ``tests/phase_48/test_capacity_mm_persist.py``).
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins import (
    install_orchestration_v0,
    install_phase1_v0,
    reset_v0_verdicts,
)
from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
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
    CATEGORY_DERIVATION,
    CATEGORY_PLANNING,
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_DATASTATE_INSTANCE,
    PROP_DATASTATE_INSTANCE_TYPE,
    capacity_iri,
    datastate_iri,
)

from mindsos_intelligence import execution, plan_construction
from mindsos_intelligence.chain_artifacts import (
    TYPE_STEP_EXECUTION_RECORD,
    ChainArtifactWriter,
    iter_chain_artifacts,
)
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.orchestrator import Orchestrator
from mindsos_intelligence.pipeline_execution import execute_pipeline
from mindsos_intelligence.plan_construction import PlanResult

DS_RAW = datastate_iri("step5.raw_task")
DS_ANSWER = datastate_iri("step5.answer")
SOLVE_IRI = capacity_iri(CATEGORY_DERIVATION, "step5_solve")

_ANSWER_VALUE = {"answer": [[7]]}


class FakeSession:
    def __init__(self, user_id="u", caps=()):
        self.session_id = "s"
        self.user_id = user_id
        self.actor_role = "user"
        self.capabilities = set(caps)

    def has(self, capability: str) -> bool:
        return capability in self.capabilities


def _solve_body(**kwargs):
    return {DS_ANSWER: _ANSWER_VALUE}


def _register_solve(layer, *, session=None):
    """Register a 1-step solve capacity raw_task -> answer (Local when a
    session is given, else Global)."""
    layer.register_datastate(
        DataState(
            name="step5.raw_task",
            shape=ShapeDescriptor.opaque("step5.raw_task"),
            description="a resolved task to solve",
            provenance_category=CATEGORY_DERIVATION,
        ),
        session=session,
        allow_new_realm=True,
    )
    layer.register_datastate(
        DataState(
            name="step5.answer",
            shape=ShapeDescriptor.opaque("step5.answer"),
            description="the solved answer",
            provenance_category=CATEGORY_DERIVATION,
        ),
        session=session,
        allow_new_realm=True,
    )
    layer.register_capacity(
        Capacity(
            name="step5_solve",
            category=CATEGORY_DERIVATION,
            inputs=(DS_RAW,),
            outputs=(DS_ANSWER,),
            implementation=_solve_body,
            description="test solve: raw_task -> answer",
        ),
        session=session,
    )


def _capacity_run_graph(mm):
    for g in mm.capacity_mm.graphs.values():
        if g.role.startswith("capacity:run:"):
            return g
    return None


# ── execution.run: the real solve run grounds capacity_mm ───────────────────


def test_execution_run_grounds_capacity_mm_on_solve():
    sess = FakeSession()
    layer = CapacityLayer()
    _register_solve(layer, session=sess)
    mm = MentalModel(session_id="s", user_id="u")
    disp = L4Dispatcher(layer, session=sess)
    writer = ChainArtifactWriter(mm, "t1")
    task_run = writer.emit_task_run()

    plan = PlanResult(
        plan_ref="plan:1",
        root_milestone_ref="milestone:1",
        leaf_milestone_refs=["milestone:1"],
        pipeline_refs={"milestone:1": "pipeline:1"},
        solve_target={"start_datastate": DS_RAW, "target_datastate": DS_ANSWER},
    )
    graphs: list = []
    execution.run(
        disp, writer, plan, task_run,
        mm=mm, run_scope="t1",
        solve_seed={DS_RAW: {"grid": [[1, 2]]}},
        capacity_graphs=graphs,
    )

    g = _capacity_run_graph(mm)
    assert g is not None, "solve run did not create a capacity_mm run graph"
    ds_types = {
        n.properties.get(PROP_DATASTATE_INSTANCE_TYPE)
        for n in g.nodes.values()
        if n.type_name == NODE_TYPE_DATASTATE_INSTANCE
    }
    assert DS_RAW in ds_types  # the resolved task landed (seeded root)
    assert DS_ANSWER in ds_types  # the produced answer landed
    assert any(n.type_name == NODE_TYPE_CAPACITY_INSTANCE for n in g.nodes.values())
    edge_types = {e.type_name for e in g.edges.values()}
    assert edge_types == {EDGE_CONSUMES, EDGE_PRODUCES}
    # The run graph is collected for persistence, and the produced value is real.
    assert graphs == [g]
    answer_nodes = [
        n.value for n in g.nodes.values()
        if n.properties.get(PROP_DATASTATE_INSTANCE_TYPE) == DS_ANSWER
    ]
    assert answer_nodes == [_ANSWER_VALUE]
    # Real (not notional) provenance: one StepExecutionRecord per capacity step.
    recs = [v for _, v in iter_chain_artifacts(mm, TYPE_STEP_EXECUTION_RECORD)]
    assert [r.capacity_iri for r in recs] == [SOLVE_IRI]


def test_execution_run_notional_when_no_solve_target():
    """No solve_target (v0) → the notional record path, capacity_mm untouched."""
    sess = FakeSession()
    layer = CapacityLayer()
    mm = MentalModel(session_id="s", user_id="u")
    disp = L4Dispatcher(layer, session=sess)
    writer = ChainArtifactWriter(mm, "t1")
    task_run = writer.emit_task_run()
    plan = PlanResult(
        plan_ref="plan:1",
        root_milestone_ref="milestone:1",
        leaf_milestone_refs=["milestone:1"],
        pipeline_refs={"milestone:1": "pipeline:1"},
        solve_target=None,
    )
    graphs: list = []
    execution.run(
        disp, writer, plan, task_run, mm=mm, run_scope="t1",
        solve_seed=None, capacity_graphs=graphs,
    )
    assert _capacity_run_graph(mm) is None
    assert graphs == []
    recs = [v for _, v in iter_chain_artifacts(mm, TYPE_STEP_EXECUTION_RECORD)]
    assert [r.capacity_iri for r in recs] == ["pipeline:1"]  # notional (pipeline ref)


# ── plan_construction: reads solve_target + threads resolved_reference ───────


class _Res:
    def __init__(self, outputs):
        self.outputs = outputs


class _RecordingDispatcher:
    """A fake dispatcher capturing the derive_initial_plan payload and
    returning a chosen plan output (is_leaf → True for the single leaf)."""

    def __init__(self, plan_out):
        self._plan_out = plan_out
        self.payloads = []

    def dispatch(self, iri, inputs, **kw):
        self.payloads.append((iri, inputs))
        from mindsos_capacity.builtins.planning_v0 import DS_IS_LEAF

        if iri == plan_construction.DERIVE_PLAN_IRI:
            return _Res({DS_PLAN: self._plan_out} if self._plan_out is not None else {})
        return _Res({DS_IS_LEAF: True})


class _FakeWriter:
    def __init__(self):
        self._seq = 0

    def _mk(self, prefix):
        self._seq += 1
        return type("A", (), {"iri": f"{prefix}:{self._seq}"})()

    def emit_milestone(self, *a, **k):
        return self._mk("milestone")

    def emit_plan(self, *a, **k):
        return self._mk("plan")

    def emit_pipeline(self, *a, **k):
        return self._mk("pipeline")


def test_plan_construction_reads_solve_target_and_threads_resolved_reference():
    plan_out = {
        "single_milestone": True,
        "solve_target": {"start_datastate": DS_RAW, "target_datastate": DS_ANSWER},
    }
    disp = _RecordingDispatcher(plan_out)
    result = plan_construction.build(
        disp, _FakeWriter(), "mappingresult:1", "task-pattern:x",
        resolved_reference={"grid": [[9]]},
    )
    assert result.solve_target == {
        "start_datastate": DS_RAW,
        "target_datastate": DS_ANSWER,
    }
    # resolved_reference rode the DS_MAPPING_RESULT value dict (no new input).
    derive_payload = disp.payloads[0][1][DS_MAPPING_RESULT]
    assert derive_payload["resolved_reference"] == {"grid": [[9]]}
    assert derive_payload["task_pattern_iri"] == "task-pattern:x"


def test_plan_construction_v0_shape_yields_no_solve_target():
    plan_out = {"root_milestone": {"name": "root"}, "single_milestone": True}
    disp = _RecordingDispatcher(plan_out)
    result = plan_construction.build(disp, _FakeWriter(), "mr:1", "tp:x")
    assert result.solve_target is None


# ── execute_pipeline exposes the per-run capacity graph ─────────────────────


def test_execute_pipeline_exposes_capacity_graph():
    from mindsos_capacity.pipeline import find_pipeline

    sess = FakeSession()
    layer = CapacityLayer()
    _register_solve(layer, session=sess)
    mm = MentalModel(session_id="s", user_id="u")
    disp = L4Dispatcher(layer, session=sess)
    pipeline = find_pipeline(
        layer, session=sess, start_datastate=DS_RAW, target_datastate=DS_ANSWER
    )
    res = execute_pipeline(
        disp, pipeline, {DS_RAW: {"grid": [[1]]}},
        task_id="t1", mm=mm, pipeline_run_ref="pipelinerun:t1:0:0",
    )
    assert res.success
    assert res.capacity_graph is not None
    assert res.capacity_graph is _capacity_run_graph(mm)

    # No MM → no grounding graph exposed (byte-identical no-MM path).
    res2 = execute_pipeline(disp, pipeline, {DS_RAW: {"grid": [[1]]}}, task_id="t2")
    assert res2.success
    assert res2.capacity_graph is None


# ── full orchestrator: run_lifecycle grounds + persists the solve ───────────


def _install_solve_planning(layer):
    """A planning catalog whose derive_initial_plan names a solve_target
    (mirrors install_planning_v0 but the plan carries the solve endpoints)."""
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
    def __init__(self):
        self.roles = []

    def persist(self, metagraph, graph, *, node_value_encoder=None):
        self.roles.append(graph.role)


def _episode_values(kl):
    from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
    from mindsos_knowledge.metagraph_view import MetagraphView

    g = MetagraphView(kl.local_metagraph("u")).graphs_by_role(ROLE_EPISODIC_MEMORIES)[0]
    return [n.value for n in g.nodes.values() if n.type_name == "Episode"]


def _orch_with_solve(persister=None):
    from mindsos_knowledge import KnowledgeLayer

    sess = FakeSession()
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    _install_solve_planning(layer)
    install_phase1_v0(layer)
    install_orchestration_v0(layer)
    install_consolidate_capacities(layer)
    _register_solve(layer, session=sess)
    reset_v0_verdicts()
    mm = MentalModel(session_id="s", user_id="u")
    disp = L4Dispatcher(layer, session=sess, kl=kl)
    orch = Orchestrator(disp, mm, task_scope="task-1", mm_persister=persister)
    return orch, mm, kl


def test_run_lifecycle_grounds_solve_into_capacity_mm():
    orch, mm, _kl = _orch_with_solve()
    outcome = orch.run_lifecycle("hello", task_id="T")
    assert outcome.status == "succeeded"
    g = _capacity_run_graph(mm)
    assert g is not None
    assert any(
        n.value == SOLVE_IRI
        for n in g.nodes.values()
        if n.type_name == NODE_TYPE_CAPACITY_INSTANCE
    )


def test_run_lifecycle_persists_capacity_root_ref():
    persister = _FakePersister()
    orch, _mm, kl = _orch_with_solve(persister=persister)
    outcome = orch.run_lifecycle("hello", task_id="T")
    assert outcome.status == "succeeded"
    vals = _episode_values(kl)
    assert len(vals) == 1
    # Step 5.4 — the capacity grounding graph is persisted and the Episode's
    # capacity_root_ref points at the task-level index (was None / inert pre-5).
    assert vals[0]["capacity_root_ref"] is not None
    assert any(r.startswith("capacity:run:") for r in persister.roles)
    assert any(r.startswith("capacity:index:") for r in persister.roles)


def test_v0_lifecycle_unchanged_no_capacity_grounding():
    """Regression: the plain v0 catalog (no solve_target) still grounds
    nothing into capacity_mm — Steps 1-4 stay inert without Step-5 activation."""
    from mindsos_capacity.builtins import install_planning_v0
    from mindsos_knowledge import KnowledgeLayer

    sess = FakeSession()
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_planning_v0(layer)
    install_phase1_v0(layer)
    install_orchestration_v0(layer)
    install_consolidate_capacities(layer)
    reset_v0_verdicts()
    mm = MentalModel(session_id="s", user_id="u")
    disp = L4Dispatcher(layer, session=sess, kl=kl)
    orch = Orchestrator(disp, mm, task_scope="task-1")
    outcome = orch.run_lifecycle("hello", task_id="T")
    assert outcome.status == "succeeded"
    assert _capacity_run_graph(mm) is None
