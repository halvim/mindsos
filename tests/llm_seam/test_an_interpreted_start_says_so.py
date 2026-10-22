"""A start that came through interpretation says so (``mindsos_llm`` plan
I-19, gate 2; R51).

The request's first value is not handed to ``execution.run`` by the caller:
it is the output of Phase-1 interpretation — the process, hint, goal and map
steps, then ``_resolve_reference``'s pipeline — and interpretation runs
UNGROUNDED, so nothing in the stored Episode records what it ran. Gate 1
labels that value ``given``. If an interpretation step used the borrowed
model, every conclusion downstream rests on a model reading no record shows.

Gate 2's claim: ``interpret`` names every capacity it dispatched that consults
the model or declares answer inputs (``model_capacities``, empty when none
did), and the request seed the orchestrator hands to ``execution.run`` is
recorded ``interpreted`` with that list. The persisted shape is spelled as
literals (a contract on stored Episodes). No call to a model provider is made:
the model-using bodies here never touch the client they are handed.
"""

from __future__ import annotations

from mindsos_capacity import Capacity, CapacityLayer, DataState, ShapeDescriptor
from mindsos_capacity.builtins import (
    install_orchestration_v0,
    install_phase1_v0,
    reset_v0_verdicts,
)
from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
from mindsos_capacity.builtins.phase1_v0 import (
    DS_GOAL,
    DS_HINT_SET,
    DS_MAPPING,
    DS_RAW_INPUT,
    DS_STRUCTURED_INPUT,
)
from mindsos_capacity.builtins.planning_v0 import (
    DS_MAPPING_RESULT,
    DS_PLAN,
    build_aggregate_outputs,
    build_decompose,
    build_is_leaf,
    planning_datastates,
)
from mindsos_capacity.identifiers import (
    CATEGORY_DECISION,
    CATEGORY_DERIVATION,
    CATEGORY_HINT,
    CATEGORY_PLANNING,
    CATEGORY_PROCESS,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_RUN_MANIFEST,
    PROP_CAPACITY_INSTANCE_TYPE,
    capacity_iri,
    datastate_iri,
)
from mindsos_knowledge import KnowledgeLayer, ROLE_REQUEST_PATTERNS
from mindsos_intelligence import L4Dispatcher, Phase1Profile
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.orchestrator import Orchestrator
from mindsos_intelligence.phase_1 import HINT_REFERENCE, HINT_REFERENCE_KIND, interpret

KEY = "start_origins"

#: Stands in for a bound client. The model-using bodies below never call it.
NOT_CALLED = object()

MODEL_PROCESS_IRI = capacity_iri(CATEGORY_PROCESS, "isso_read_request")

DS_REF = datastate_iri("isso.index_ref")
DS_CANON = datastate_iri("isso.canonical_ref")
PATTERN = "request-pattern:isso:solve"
HINT_IRI = capacity_iri(CATEGORY_HINT, "isso")
MAP_IRI = capacity_iri(CATEGORY_DECISION, "isso_map")
MODEL_RESOLVE_IRI = capacity_iri(CATEGORY_DECISION, "isso_read_reference")

DS_TASK = datastate_iri("isso.task")
DS_ANSWER = datastate_iri("isso.answer")
SOLVE_IRI = capacity_iri(CATEGORY_DERIVATION, "isso_solve")


class FakeSession:
    session_id = "s"
    user_id = "u"
    actor_role = "user"
    capabilities: set = set()

    def has(self, capability: str) -> bool:
        return False


def _register_model_process(layer):
    layer.register_capacity(
        Capacity(
            name="isso_read_request", category=CATEGORY_PROCESS,
            inputs=(DS_RAW_INPUT,), outputs=(DS_STRUCTURED_INPUT,),
            implementation=lambda **kw: {DS_STRUCTURED_INPUT: kw.get(DS_RAW_INPUT)},
            consults_llm=True,
            description="reads the request (declares that it consults the model)",
        )
    )


def _ds(name):
    return DataState(name=name, shape=ShapeDescriptor.opaque(name), description=name)


def _resolving_consumer():
    """hint -> map -> resolve, where the resolve step consults the model."""
    layer = CapacityLayer()
    install_phase1_v0(layer)
    for name in ("isso.index_ref", "isso.canonical_ref"):
        layer.register_datastate(_ds(name), allow_new_realm=True)
    layer.register_capacity(Capacity(
        name="isso", category=CATEGORY_HINT,
        inputs=(DS_STRUCTURED_INPUT,), outputs=(DS_HINT_SET,),
        implementation=lambda **kw: {
            DS_HINT_SET: {HINT_REFERENCE_KIND: DS_REF, HINT_REFERENCE: 8}
        },
    ))
    layer.register_capacity(Capacity(
        name="isso_map", category=CATEGORY_DECISION,
        inputs=(DS_STRUCTURED_INPUT, DS_HINT_SET, DS_GOAL), outputs=(DS_MAPPING,),
        implementation=lambda **kw: {
            DS_MAPPING: {"request_pattern_iri": PATTERN, "mapping_confidence": 1.0}
        },
    ))
    layer.register_capacity(Capacity(
        name="isso_read_reference", category=CATEGORY_DECISION,
        inputs=(DS_REF,), outputs=(DS_CANON,),
        implementation=lambda **kw: {DS_CANON: f"id{kw[DS_REF]}"},
        consults_llm=True,
    ))
    kl = KnowledgeLayer.bootstrap()
    graph = next(
        g for g in kl.global_metagraph().graphs.values()
        if g.role == ROLE_REQUEST_PATTERNS
    )
    graph.add_node(value=PATTERN, type_name="RequestPattern", node_id=PATTERN)
    profile = Phase1Profile(hint=HINT_IRI, map=MAP_IRI, resolve_target_datastate=DS_CANON)
    return layer, kl, profile


def test_an_interpretation_that_used_no_model_names_none():
    layer = CapacityLayer()
    install_phase1_v0(layer)
    result = interpret(L4Dispatcher(layer), "anything")
    assert getattr(result, "model_capacities", None) == ()


def test_a_model_using_interpretation_step_is_named():
    layer = CapacityLayer()
    install_phase1_v0(layer)
    _register_model_process(layer)
    dispatcher = L4Dispatcher(
        layer, phase1_profile=Phase1Profile(process=MODEL_PROCESS_IRI), llm=NOT_CALLED,
    )
    result = interpret(dispatcher, "anything")
    assert getattr(result, "model_capacities", None) == (MODEL_PROCESS_IRI,)


def test_a_model_using_resolve_step_is_named():
    layer, kl, profile = _resolving_consumer()
    dispatcher = L4Dispatcher(layer, kl=kl, phase1_profile=profile, llm=NOT_CALLED)
    result = interpret(dispatcher, "solve task 8")
    assert result.resolved_reference == "id8"
    assert getattr(result, "model_capacities", None) == (MODEL_RESOLVE_IRI,)


# ── the lifecycle: the seed handed to execution.run says it was interpreted ──


def _install_solve_planning(layer):
    for ds in planning_datastates():
        layer.register_datastate(ds, allow_new_realm=True)
    layer.register_capacity(Capacity(
        name="derive_initial_plan", category=CATEGORY_PLANNING,
        inputs=(DS_MAPPING_RESULT,), outputs=(DS_PLAN,),
        implementation=lambda **kw: {DS_PLAN: {
            "root_milestone": {"name": "root", "is_leaf": True},
            "single_milestone": True,
            "solve_target": {"start_datastate": DS_TASK, "target_datastate": DS_ANSWER},
        }},
        description="test: single-Milestone plan naming a solve_target",
        placeholder=True,
    ))
    layer.register_capacity(build_decompose())
    layer.register_capacity(build_is_leaf())
    layer.register_capacity(build_aggregate_outputs())


def _lifecycle(*, model_process: bool):
    session = FakeSession()
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    _install_solve_planning(layer)
    install_phase1_v0(layer)
    install_orchestration_v0(layer)
    install_consolidate_capacities(layer)
    for name in ("isso.task", "isso.answer"):
        layer.register_datastate(_ds(name), session=session, allow_new_realm=True)
    layer.register_capacity(Capacity(
        name="isso_solve", category=CATEGORY_DERIVATION,
        inputs=(DS_TASK,), outputs=(DS_ANSWER,),
        implementation=lambda **kw: {DS_ANSWER: {"solved": kw.get(DS_TASK)}},
        description="test solve: task -> answer",
    ), session=session)
    if model_process:
        _register_model_process(layer)
    reset_v0_verdicts()
    mm = MentalModel(session_id="s", user_id="u")
    dispatcher = L4Dispatcher(
        layer, session=session, kl=kl,
        phase1_profile=Phase1Profile(process=MODEL_PROCESS_IRI) if model_process else None,
        llm=NOT_CALLED if model_process else None,
    )
    outcome = Orchestrator(dispatcher, mm, request_scope="request-1").run_lifecycle(
        "hello", request_id="T",
    )
    assert outcome.status == "succeeded"
    solved = [
        g for g in mm.capacity_mm.graphs.values()
        if g.role.startswith("capacity:run:")
        and any(
            n.properties.get(PROP_CAPACITY_INSTANCE_TYPE) == SOLVE_IRI
            for n in g.nodes.values() if n.type_name == NODE_TYPE_CAPACITY_INSTANCE
        )
    ]
    assert len(solved) == 1
    manifest = [n for n in solved[0].nodes.values() if n.type_name == NODE_TYPE_RUN_MANIFEST]
    return manifest[0].value.get(KEY)


def test_the_request_seed_is_recorded_as_interpreted():
    assert _lifecycle(model_process=False) == {
        DS_TASK: {"kind": "interpreted", "model_capacities": []},
    }


def test_a_seed_interpreted_with_the_model_names_the_capacity():
    assert _lifecycle(model_process=True) == {
        DS_TASK: {"kind": "interpreted", "model_capacities": [MODEL_PROCESS_IRI]},
    }
