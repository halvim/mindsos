"""The walk lists every value that leaned on the model (``mindsos_llm`` plan
I-21, gate 2; R49, R50, R52, R62; ADR-0210 amendment 9 clauses 4 and 5).

``identify`` lists readings. A value a plain capacity computed FROM a reading
also leaned on the borrowed model (§1) and is identified by nothing. Gate 2's
claim: ``excision.walk`` lists, for a persisted Episode's run graphs, every
value whose lineage holds a model value, with those model values — and every
value whose lineage is not recorded, with the gap, since an unlisted value
must mean *no model in its lineage* (R62). The lineage crosses run graphs by
the manifest's ``start_origins`` (ADR-0201 amendment 8).

A value is the model's (R52) when its origin record says ``read_by_model``,
when its producer declared ``consults_llm`` as the run snapshotted it, when a
reader consumed it as a declared answer input — and an ``interpreted`` start
whose interpretation used the model (R51). A copy carried into the next run
is the same value: a mark found on the copy is the original's too.

Graphs are minted by the real ``CapacityMMWriter``. Persisted shapes and
tokens are spelled as literals (a contract on stored Episodes). No call to a
model provider is made: nothing here dispatches.
"""

from __future__ import annotations

import pytest

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture

from mindsos_capacity.builtins.origin_v0 import origin_record_iri
from mindsos_intelligence.capacity_mm_writer import CapacityMMWriter
from mindsos_intelligence.mm import MentalModel

SRC = "ds:walk.source"
ANS = "ds:walk.answer"
VAL = "ds:walk.value"
DEC = "ds:walk.decision"
OUT = "ds:walk.other"
COLL = "ds:walk.collection"
ELEM = "ds:walk.element"

READER = "capacity:comprehension:walk_reader"
CALLER = "capacity:comprehension:walk_caller"
FED = "capacity:comprehension:walk_answer_fed"
PLAIN = "capacity:derivation:walk_plain"
PLAIN2 = "capacity:derivation:walk_plain2"

NONE = {"consults_llm": False, "model_answer_inputs": [], "reads_roles": [], "reads_mm": False}
CONSULTS = dict(NONE, consults_llm=True)

GIVEN = {"kind": "given"}


def _walk(graphs):
    from mindsos_intelligence import excision

    return excision.walk(graphs)


class _Run:
    """One run graph through the real writer."""

    def __init__(self, mm, ref, *, starts, origins=None, declarations=None, no_origins=False,
                 no_declarations=False):
        self.w = CapacityMMWriter(mm, "req-walk", ref)
        self.w.manifest(
            declared_starts={ds: None for ds in starts},
            capacity_phrases={},
            start_origins=None if no_origins else {
                ds: (origins or {}).get(ds, GIVEN) for ds in starts
            },
            capacity_declarations=None if no_declarations else (declarations or {}),
        )
        for ds, value in starts.items():
            self.w.seed(ds, value)

    def step(self, iri, inputs, outputs):
        self.w.record(iri, inputs, outputs)
        return self

    def at(self, ds):
        return {"graph_id": self.w.graph.graph_id, "instance_id": self.w.index[ds]}

    @property
    def graph(self):
        return self.w.graph


def _reading(value=True):
    return {"origin_method": "read_by_model", "value": value}


def _listed(entries):
    """``{(graph_id, datastate): {(model datastate, hows), ...}}`` — what the walk listed."""
    return {
        (e.value.graph_id, e.datastate): {(m.datastate, tuple(m.hows)) for m in e.model_values}
        for e in entries
    }


def _gaps(entries):
    return {
        (e.value.graph_id, e.datastate): {(g.datastate, g.kind) for g in e.gaps}
        for e in entries
    }


def _one_reading_run(mm, ref="run-1"):
    run = _Run(mm, ref, starts={SRC: "the letter"}, declarations={READER: CONSULTS, PLAIN: NONE})
    run.step(READER, (SRC,), {VAL: True, origin_record_iri(VAL): _reading()})
    run.step(PLAIN, (VAL,), {DEC: "pay"})
    return run


def test_a_reading_and_what_was_computed_from_it_are_listed():
    mm = MentalModel(session_id="s", user_id="u")
    run = _one_reading_run(mm)
    g = run.graph.graph_id
    model = {(VAL, ("consults_llm", "read_by_model"))}
    assert _listed(_walk([run.graph])) == {(g, VAL): model, (g, DEC): model}


def test_a_consulting_producer_with_no_record_makes_its_value_the_model_s():
    mm = MentalModel(session_id="s", user_id="u")
    run = _Run(mm, "run-1", starts={SRC: "x"}, declarations={CALLER: CONSULTS})
    run.step(CALLER, (SRC,), {VAL: 1})
    g = run.graph.graph_id
    assert _listed(_walk([run.graph])) == {(g, VAL): {(VAL, ("consults_llm",))}}


def test_a_value_a_reader_takes_as_its_answer_is_the_model_s():
    mm = MentalModel(session_id="s", user_id="u")
    run = _Run(
        mm, "run-1", starts={SRC: "x", ANS: {"a": 1}},
        declarations={FED: dict(NONE, model_answer_inputs=[ANS]), PLAIN: NONE},
    )
    run.step(FED, (SRC, ANS), {VAL: 1})
    run.step(PLAIN, (ANS,), {OUT: 2})
    g = run.graph.graph_id
    model = {(ANS, ("answer_input",))}
    assert _listed(_walk([run.graph])) == {(g, ANS): model, (g, VAL): model, (g, OUT): model}


def test_the_walk_follows_a_value_into_the_next_run():
    mm = MentalModel(session_id="s", user_id="u")
    first = _one_reading_run(mm)
    second = _Run(
        mm, "run-2", starts={VAL: True},
        origins={VAL: {"kind": "produced", "by": [first.at(VAL)]}},
        declarations={PLAIN2: NONE},
    )
    second.step(PLAIN2, (VAL,), {OUT: "x"})
    g1, g2 = first.graph.graph_id, second.graph.graph_id
    model = {(VAL, ("consults_llm", "read_by_model"))}
    listed = _listed(_walk([first.graph, second.graph]))
    assert listed[(g2, OUT)] == model
    assert listed[(g2, VAL)] == model
    assert {k for k in listed if k[0] == g1} == {(g1, VAL), (g1, DEC)}


def test_a_copy_taken_as_an_answer_in_the_next_run_marks_the_original():
    mm = MentalModel(session_id="s", user_id="u")
    first = _Run(mm, "run-1", starts={SRC: "x"}, declarations={PLAIN: NONE, PLAIN2: NONE})
    first.step(PLAIN, (SRC,), {ANS: "answer"})
    first.step(PLAIN2, (ANS,), {OUT: "computed from the answer"})
    second = _Run(
        mm, "run-2", starts={ANS: "answer", SRC: "x"},
        origins={ANS: {"kind": "produced", "by": [first.at(ANS)]}, SRC: GIVEN},
        declarations={FED: dict(NONE, model_answer_inputs=[ANS])},
    )
    second.step(FED, (SRC, ANS), {VAL: 1})
    g1 = first.graph.graph_id
    listed = _listed(_walk([first.graph, second.graph]))
    assert listed[(g1, OUT)] == {(ANS, ("answer_input",))}
    assert (g1, SRC) not in listed


def test_an_element_taken_as_an_answer_does_not_mark_its_collection():
    mm = MentalModel(session_id="s", user_id="u")
    first = _Run(mm, "run-1", starts={SRC: "x"}, declarations={PLAIN: NONE, PLAIN2: NONE})
    first.step(PLAIN, (SRC,), {COLL: ["a", "b"]})
    first.step(PLAIN2, (COLL,), {OUT: 2})
    member = _Run(
        mm, "run-m0", starts={ELEM: "a", SRC: "x"},
        origins={ELEM: {"kind": "produced", "by": [first.at(COLL)]}, SRC: GIVEN},
        declarations={FED: dict(NONE, model_answer_inputs=[ELEM])},
    )
    member.step(FED, (SRC, ELEM), {VAL: 1})
    g1 = first.graph.graph_id
    listed = _listed(_walk([first.graph, member.graph]))
    assert {k for k in listed if k[0] == g1} == set()


def test_given_and_model_free_interpreted_starts_lean_on_nothing():
    mm = MentalModel(session_id="s", user_id="u")
    run = _Run(
        mm, "run-1", starts={SRC: "x", ANS: "y"},
        origins={SRC: GIVEN, ANS: {"kind": "interpreted", "model_capacities": []}},
        declarations={PLAIN: NONE},
    )
    run.step(PLAIN, (SRC, ANS), {DEC: 1})
    assert _walk([run.graph]) == ()


def test_a_start_interpreted_with_the_model_is_the_model_s():
    mm = MentalModel(session_id="s", user_id="u")
    run = _Run(
        mm, "run-1", starts={ANS: "y"},
        origins={ANS: {"kind": "interpreted", "model_capacities": [CALLER]}},
        declarations={PLAIN: NONE},
    )
    run.step(PLAIN, (ANS,), {DEC: 1})
    g = run.graph.graph_id
    model = {(ANS, ("interpreted",))}
    assert _listed(_walk([run.graph])) == {(g, ANS): model, (g, DEC): model}


def test_a_run_that_recorded_no_origins_is_listed_with_the_gap():
    mm = MentalModel(session_id="s", user_id="u")
    run = _Run(mm, "run-1", starts={SRC: "x"}, declarations={PLAIN: NONE}, no_origins=True)
    run.step(PLAIN, (SRC,), {DEC: 1})
    g = run.graph.graph_id
    gap = {(SRC, "origins_not_recorded")}
    assert _gaps(_walk([run.graph])) == {(g, SRC): gap, (g, DEC): gap}


def test_an_unrecorded_start_is_listed_with_the_gap():
    mm = MentalModel(session_id="s", user_id="u")
    run = _Run(
        mm, "run-1", starts={SRC: "x"}, origins={SRC: {"kind": "unrecorded"}},
        declarations={PLAIN: NONE},
    )
    run.step(PLAIN, (SRC,), {DEC: 1})
    g = run.graph.graph_id
    gap = {(SRC, "origin_unrecorded")}
    assert _gaps(_walk([run.graph])) == {(g, SRC): gap, (g, DEC): gap}


def test_a_start_produced_by_a_run_not_in_the_episode_is_listed_with_the_gap():
    mm = MentalModel(session_id="s", user_id="u")
    run = _Run(
        mm, "run-1", starts={SRC: "x"},
        origins={SRC: {"kind": "produced", "by": [{"graph_id": "gone", "instance_id": "i"}]}},
        declarations={PLAIN: NONE},
    )
    run.step(PLAIN, (SRC,), {DEC: 1})
    g = run.graph.graph_id
    gap = {(SRC, "origin_not_in_the_episode")}
    assert _gaps(_walk([run.graph])) == {(g, SRC): gap, (g, DEC): gap}


def test_a_capacity_whose_declaration_was_not_recorded_is_listed_with_the_gap():
    mm = MentalModel(session_id="s", user_id="u")
    run = _Run(mm, "run-1", starts={SRC: "x"}, declarations={})
    run.step(PLAIN, (SRC,), {DEC: 1})
    g = run.graph.graph_id
    assert _gaps(_walk([run.graph])) == {
        (g, SRC): {(SRC, "declarations_not_recorded")},
        (g, DEC): {(SRC, "declarations_not_recorded"), (DEC, "declarations_not_recorded")},
    }


def test_a_manifest_with_no_declaration_snapshot_is_listed_with_the_gap():
    mm = MentalModel(session_id="s", user_id="u")
    run = _Run(mm, "run-1", starts={SRC: "x"}, no_declarations=True)
    run.step(PLAIN, (SRC,), {DEC: 1})
    g = run.graph.graph_id
    assert set(_gaps(_walk([run.graph]))) == {(g, SRC), (g, DEC)}


@pytest.mark.integration
def test_a_stored_episode_walks_the_same(falkor_client):
    from mindsos_core.reconstruction import load_graph
    from mindsos_intelligence.capacity_persister import persist_capacity_mm
    from mindsos_intelligence.mm_persister import FalkorMMPersister

    mm = MentalModel(session_id="s", user_id="u")
    first = _one_reading_run(mm)
    second = _Run(
        mm, "run-2", starts={VAL: True},
        origins={VAL: {"kind": "produced", "by": [first.at(VAL)]}},
        declarations={PLAIN2: NONE},
    )
    second.step(PLAIN2, (VAL,), {OUT: "x"})
    graphs = [first.graph, second.graph]
    persist_capacity_mm(
        FalkorMMPersister(falkor_client), mm.capacity_mm, graphs,
        request_id="req-walk", encoders={},
    )
    loaded = [load_graph(falkor_client, g.graph_id) for g in graphs]
    assert _walk(loaded) == _walk(graphs)
    assert len(_walk(loaded)) == 4
