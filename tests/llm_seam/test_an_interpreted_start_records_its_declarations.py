"""An interpreted start records what interpretation declared (``mindsos_llm``
plan I-21, gate 1; R46, R48, R51; ADR-0201 amendment 8 §5b).

The request's first value is Phase-1 interpretation's output, and
interpretation runs UNGROUNDED: no run graph and no manifest records its
steps. I-19 gate 2 records which of them leaned on the model
(``model_capacities``). It does not record the stored roles they declared they
read, so a proven re-run (R46: *given what the caller handed in and the stored
roles the derivation declared it read*) cannot name them, and absence means
*not recorded*, never *read nothing* (ADR-0201 amendment 8 §5a).

Gate 1's claim: ``interpret`` snapshots the declaration of EVERY capacity it
dispatched — the four steps and the resolve pipeline's steps that ran — with
the same entry the run manifest's ``capacity_declarations`` carries
(``consults_llm``, ``model_answer_inputs``, ``reads_roles``, ``reads_mm``), and
the orchestrator's ``interpreted`` origin carries that snapshot. The persisted
shape is spelled as literals (a contract on stored Episodes). No call to a
model provider is made: the model-using bodies never touch the client.
"""

from __future__ import annotations

from mindsos_capacity import Capacity, CapacityLayer
from mindsos_capacity.builtins import install_phase1_v0
from mindsos_capacity.builtins.phase1_v0 import DS_RAW_INPUT, DS_STRUCTURED_INPUT
from mindsos_capacity.identifiers import CATEGORY_PROCESS, capacity_iri
from mindsos_intelligence import L4Dispatcher, Phase1Profile
from mindsos_intelligence.capacity_mm_writer import capacity_declarations
from mindsos_intelligence.phase_1 import (
    DERIVE_GOAL_IRI,
    HINT_IRI,
    MAP_IRI,
    PROCESS_IRI,
    interpret,
)
from mindsos_knowledge.identifiers import ROLE_LEXICON

from tests.llm_seam.test_an_interpreted_start_says_so import (
    DS_TASK,
    HINT_IRI as CONSUMER_HINT_IRI,
    MAP_IRI as CONSUMER_MAP_IRI,
    MODEL_PROCESS_IRI,
    MODEL_RESOLVE_IRI,
    NOT_CALLED,
    _lifecycle,
    _register_model_process,
    _resolving_consumer,
)

KEY = "capacity_declarations"

PLAIN = {"consults_llm": False, "model_answer_inputs": [], "reads_roles": [], "reads_mm": False}
MODEL = {"consults_llm": True, "model_answer_inputs": [], "reads_roles": [], "reads_mm": False}

READING_PROCESS_IRI = capacity_iri(CATEGORY_PROCESS, "irid_read_with_lexicon")


def _v0():
    return {PROCESS_IRI: PLAIN, HINT_IRI: PLAIN, DERIVE_GOAL_IRI: PLAIN, MAP_IRI: PLAIN}


def test_every_dispatched_step_is_recorded_with_every_field():
    layer = CapacityLayer()
    install_phase1_v0(layer)
    result = interpret(L4Dispatcher(layer), "anything")
    assert getattr(result, KEY, None) == _v0()


def test_a_step_that_declares_reads_is_recorded_with_its_roles():
    layer = CapacityLayer()
    install_phase1_v0(layer)
    layer.register_capacity(
        Capacity(
            name="irid_read_with_lexicon", category=CATEGORY_PROCESS,
            inputs=(DS_RAW_INPUT,), outputs=(DS_STRUCTURED_INPUT,),
            implementation=lambda **kw: {DS_STRUCTURED_INPUT: kw.get(DS_RAW_INPUT)},
            reads_roles=(ROLE_LEXICON,),
            description="reads the request against the lexicon",
        )
    )
    dispatcher = L4Dispatcher(layer, phase1_profile=Phase1Profile(process=READING_PROCESS_IRI))
    result = interpret(dispatcher, "anything")
    expected = _v0()
    del expected[PROCESS_IRI]
    expected[READING_PROCESS_IRI] = dict(PLAIN, reads_roles=[ROLE_LEXICON])
    assert getattr(result, KEY, None) == expected


def test_a_model_using_step_is_recorded_as_consulting():
    layer = CapacityLayer()
    install_phase1_v0(layer)
    _register_model_process(layer)
    dispatcher = L4Dispatcher(
        layer, phase1_profile=Phase1Profile(process=MODEL_PROCESS_IRI), llm=NOT_CALLED,
    )
    result = interpret(dispatcher, "anything")
    expected = _v0()
    del expected[PROCESS_IRI]
    expected[MODEL_PROCESS_IRI] = MODEL
    assert getattr(result, KEY, None) == expected


def test_the_resolve_steps_that_ran_are_recorded():
    layer, kl, profile = _resolving_consumer()
    dispatcher = L4Dispatcher(layer, kl=kl, phase1_profile=profile, llm=NOT_CALLED)
    result = interpret(dispatcher, "solve task 8")
    assert getattr(result, KEY, None) == {
        PROCESS_IRI: PLAIN,
        CONSUMER_HINT_IRI: PLAIN,
        DERIVE_GOAL_IRI: PLAIN,
        CONSUMER_MAP_IRI: PLAIN,
        MODEL_RESOLVE_IRI: MODEL,
    }


def test_the_entry_is_the_one_a_run_manifest_carries():
    """One entry shape for both records, so a reader of either reads the same
    fields — checked against the manifest's own snapshot function."""

    class _Step:
        def __init__(self, iri):
            self.capacity_iri = iri

    class _Pipeline:
        steps = (_Step(PROCESS_IRI), _Step(HINT_IRI), _Step(DERIVE_GOAL_IRI), _Step(MAP_IRI))

    layer = CapacityLayer()
    install_phase1_v0(layer)
    dispatcher = L4Dispatcher(layer)
    assert getattr(interpret(dispatcher, "anything"), KEY, None) == capacity_declarations(
        dispatcher, _Pipeline()
    )


def test_the_interpreted_origin_carries_the_snapshot():
    assert _lifecycle(model_process=False) == {
        DS_TASK: {"kind": "interpreted", "model_capacities": [], KEY: _v0()},
    }


def test_the_interpreted_origin_names_the_model_step_in_its_snapshot():
    expected = _v0()
    del expected[PROCESS_IRI]
    expected[MODEL_PROCESS_IRI] = MODEL
    assert _lifecycle(model_process=True) == {
        DS_TASK: {"kind": "interpreted", "model_capacities": [MODEL_PROCESS_IRI], KEY: expected},
    }
