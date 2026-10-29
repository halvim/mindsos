"""A re-run is proven model-free, or says why not (``mindsos_llm`` plan I-21,
gate 3; R47, R53, R55–R61; ADR-0210 amendment 9 clauses 2 and 6).

``rerun`` re-derives ONE reading. Its agreement says nothing about where the
substitute's own inputs came from. Gate 3's claim: ``excision.prove`` reports a
value proven only when every model value it descends from — through a
substitute's inputs (R56) — re-derives through its own substitute, from proven
inputs, with exact agreement, and its report names what it relied on: the
starts it took as premises and the stored roles read on the way (R61). Every
other reason it is *not proven* is read from the record and named (R58).

Graphs are minted by the real ``CapacityMMWriter``; substitutes run through a
real ``L4Dispatcher`` with no model bound. Tokens are spelled as literals (the
report is a contract). No call to a model provider is made: no reader runs.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import Capacity, CapacityLayer
from mindsos_capacity.builtins.comprehension_v0 import reader_datastates
from mindsos_capacity.builtins.excision_v0 import install_excision_v0
from mindsos_capacity.builtins.origin_v0 import origin_record_iri
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_COMBINATION,
    CATEGORY_COMPREHENSION,
    CATEGORY_DERIVATION,
    capacity_iri,
    datastate_iri,
)
from mindsos_intelligence import L4Dispatcher
from mindsos_intelligence.capacity_mm_writer import CapacityMMWriter
from mindsos_intelligence.excision import ModelBoundError
from mindsos_intelligence.mm import MentalModel
from mindsos_knowledge import KnowledgeLayer

SRC = datastate_iri("proof3.source")
ANS = datastate_iri("proof3.answer")
EXTRA = datastate_iri("proof3.extra")
VAL = datastate_iri("proof3.value")
VAL2 = datastate_iri("proof3.value2")
DEC = datastate_iri("proof3.decision")
RECORD = origin_record_iri(VAL)
RECORD2 = origin_record_iri(VAL2)

PLAIN = capacity_iri(CATEGORY_DERIVATION, "proof3_decide")
PLAIN2 = capacity_iri(CATEGORY_DERIVATION, "proof3_decide2")

NONE = {"consults_llm": False, "model_answer_inputs": [], "reads_roles": [], "reads_mm": False}
CONSULTS = dict(NONE, consults_llm=True)
GIVEN = {"kind": "given"}
READING = {"origin_method": "read_by_model"}


def _api():
    from mindsos_intelligence import excision

    return excision


def _never(**kw):
    raise AssertionError("a reader ran: a proof runs substitutes only")


def _layer(*capacities):
    layer = CapacityLayer()
    install_excision_v0(layer)
    for iri in (SRC, ANS, EXTRA, DEC):
        name = iri.split(":", 1)[-1]
        layer.register_datastate(
            DataState(name=name, shape=ShapeDescriptor.opaque(name), description="d",
                      provenance_category=CATEGORY_COMPREHENSION),
            allow_new_realm=True,
        )
    for value in (VAL, VAL2):
        for datastate in reader_datastates(value_datastate_iri=value, value_description="v"):
            layer.register_datastate(datastate, allow_new_realm=True)
    for capacity in capacities:
        layer.register_capacity(capacity)
    return layer


def _reader(name="proof3_read", inputs=(SRC,), value=VAL, **kw):
    kw.setdefault("consults_llm", "model_answer_inputs" not in kw)
    return Capacity(
        name=name, category=CATEGORY_COMPREHENSION, inputs=inputs,
        outputs=(value, origin_record_iri(value)), implementation=_never,
        description="reads it", **kw,
    )


def _substitute(reader, name="proof3_rederive", inputs=(SRC,), value=VAL, gives=True,
                seen=None, **kw):
    def body(**kwargs):
        if seen is not None:
            seen.append(tuple(sorted(k for k in kwargs if k != "context")))
        if gives == "raise":
            raise RuntimeError("cannot read it")
        return {value: gives}

    return Capacity(
        name=name, category=CATEGORY_COMBINATION, inputs=inputs, outputs=(value,),
        implementation=body, description="re-derives it", substitute_for=reader.iri, **kw,
    )


def _dispatcher(layer, **kw):
    return L4Dispatcher(layer, kl=KnowledgeLayer.bootstrap(), llm=kw.pop("llm", None), **kw)


class _Run:
    def __init__(self, mm, ref, *, starts, origins=None, declarations):
        self.w = CapacityMMWriter(mm, "req-proof3", ref)
        self.w.manifest(
            declared_starts={ds: None for ds in starts}, capacity_phrases={},
            start_origins={ds: (origins or {}).get(ds, GIVEN) for ds in starts},
            capacity_declarations=declarations,
        )
        for ds, v in starts.items():
            self.w.seed(ds, v)

    def step(self, iri, inputs, outputs):
        self.w.record(iri, inputs, outputs)
        return self

    def ref(self, ds):
        return _api().ValueRef(self.w.graph.graph_id, self.w.index[ds])

    def at(self, ds):
        return {"graph_id": self.w.graph.graph_id, "instance_id": self.w.index[ds]}

    @property
    def graph(self):
        return self.w.graph


def _reading_run(mm, reader, *, plain=NONE):
    run = _Run(mm, "run-1", starts={SRC: "the letter"},
               declarations={reader.iri: CONSULTS, PLAIN: plain})
    run.step(reader.iri, (SRC,), {VAL: True, RECORD: READING})
    run.step(PLAIN, (VAL,), {DEC: "pay"})
    return run


def _why(report):
    return {(n.datastate, n.reason) for n in report.not_proven}


def test_a_decision_from_a_reading_whose_substitute_agrees_is_proven():
    reader = _reader()
    layer = _layer(reader, _substitute(reader))
    run = _reading_run(MentalModel(session_id="s", user_id="u"), reader)
    report = _api().prove(run.ref(DEC), [run.graph], dispatcher=_dispatcher(layer))
    assert (report.proven, report.not_proven) == (True, ())
    (rederived,) = report.rederived
    assert (rederived.datastate, rederived.reader_iri) == (VAL, reader.iri)
    assert [(r.agrees, r.failure) for r in rederived.runs] == [(True, None)]
    assert report.premises == (run.ref(SRC),)
    assert report.roles == ()


def test_a_disagreeing_substitute_leaves_it_not_proven_naming_the_reading():
    reader = _reader()
    layer = _layer(reader, _substitute(reader, gives=False))
    run = _reading_run(MentalModel(session_id="s", user_id="u"), reader)
    report = _api().prove(run.ref(DEC), [run.graph], dispatcher=_dispatcher(layer))
    assert report.proven is False
    assert _why(report) == {(VAL, "substitute_disagrees")}


def test_a_reading_with_no_substitute_is_not_yet_excisable():
    reader = _reader()
    layer = _layer(reader)
    run = _reading_run(MentalModel(session_id="s", user_id="u"), reader)
    report = _api().prove(run.ref(DEC), [run.graph], dispatcher=_dispatcher(layer))
    assert _why(report) == {(VAL, "not_yet_excisable")}


def test_a_substitute_that_raises_is_no_agreement_and_no_disagreement():
    reader = _reader()
    layer = _layer(reader, _substitute(reader, gives="raise"))
    run = _reading_run(MentalModel(session_id="s", user_id="u"), reader)
    report = _api().prove(run.ref(DEC), [run.graph], dispatcher=_dispatcher(layer))
    assert _why(report) == {(VAL, "no_substitute_agreed")}
    assert [r.failure for r in report.rederived[0].runs] == ["substitute_did_not_run"]


def test_one_substitute_agreeing_and_one_failing_is_proven():
    reader = _reader()
    layer = _layer(reader, _substitute(reader), _substitute(reader, name="proof3_b", gives="raise"))
    run = _reading_run(MentalModel(session_id="s", user_id="u"), reader)
    assert _api().prove(run.ref(DEC), [run.graph], dispatcher=_dispatcher(layer)).proven is True


def test_one_substitute_agreeing_and_one_disagreeing_is_not_proven():
    reader = _reader()
    layer = _layer(reader, _substitute(reader), _substitute(reader, name="proof3_b", gives=False))
    run = _reading_run(MentalModel(session_id="s", user_id="u"), reader)
    report = _api().prove(run.ref(DEC), [run.graph], dispatcher=_dispatcher(layer))
    assert _why(report) == {(VAL, "substitute_disagrees")}


def _chain(first_gives):
    reader = _reader()
    reader2 = _reader(name="proof3_read2", inputs=(VAL,), value=VAL2)
    layer = _layer(
        reader, reader2, _substitute(reader, gives=first_gives),
        _substitute(reader2, name="proof3_rederive2", inputs=(VAL,), value=VAL2, gives="seen"),
    )
    mm = MentalModel(session_id="s", user_id="u")
    first = _Run(mm, "run-1", starts={SRC: "the letter"}, declarations={reader.iri: CONSULTS})
    first.step(reader.iri, (SRC,), {VAL: True, RECORD: READING})
    second = _Run(
        mm, "run-2", starts={VAL: True},
        origins={VAL: {"kind": "produced", "by": [first.at(VAL)]}},
        declarations={reader2.iri: CONSULTS},
    )
    second.step(reader2.iri, (VAL,), {VAL2: "seen", RECORD2: READING})
    report = _api().prove(second.ref(VAL2), [first.graph, second.graph],
                          dispatcher=_dispatcher(layer))
    return report, first


def test_a_chain_is_proven_when_every_reading_up_it_agrees():
    report, first = _chain(True)
    assert report.proven is True
    assert {r.datastate for r in report.rederived} == {VAL, VAL2}
    assert report.premises == (first.ref(SRC),)


def test_a_chain_whose_upstream_reading_disagrees_names_that_reading():
    report, first = _chain(False)
    assert report.proven is False
    assert {(n.value, n.reason) for n in report.not_proven} == {
        (first.ref(VAL), "substitute_disagrees")
    }
    (downstream,) = [r for r in report.rederived if r.datastate == VAL2]
    assert [r.failure for r in downstream.runs] == ["substitute_inputs_not_proven"]


def _answer_fed(*, snapshot_answers=(ANS,), substitute_inputs=(SRC,), seen=None):
    fed = _reader(name="proof3_fed", inputs=(SRC, ANS, EXTRA), model_answer_inputs=(ANS,))
    layer = _layer(fed, _substitute(fed, inputs=substitute_inputs, seen=seen))
    run = _Run(
        MentalModel(session_id="s", user_id="u"), "run-1",
        starts={SRC: "the letter", ANS: {"a": 1}, EXTRA: "the matter"},
        declarations={fed.iri: dict(NONE, model_answer_inputs=list(snapshot_answers)),
                      PLAIN: NONE},
    )
    run.step(fed.iri, (SRC, ANS, EXTRA), {VAL: True, RECORD: READING})
    run.step(PLAIN, (ANS,), {DEC: "from the answer"})
    return layer, run


def test_a_withheld_answer_does_not_bear_on_the_proof():
    layer, run = _answer_fed(substitute_inputs=(SRC, EXTRA))
    report = _api().prove(run.ref(VAL), [run.graph], dispatcher=_dispatcher(layer))
    assert report.proven is True
    assert set(report.premises) == {run.ref(SRC), run.ref(EXTRA)}


def test_a_model_answer_with_no_model_made_lineage_is_not_excisable():
    layer, run = _answer_fed(substitute_inputs=(SRC, EXTRA))
    report = _api().prove(run.ref(DEC), [run.graph], dispatcher=_dispatcher(layer))
    assert _why(report) == {(ANS, "model_answer_not_excisable")}


def test_a_substitute_taking_an_input_the_run_withheld_is_not_run():
    seen = []
    layer, run = _answer_fed(snapshot_answers=(ANS, EXTRA), substitute_inputs=(SRC, EXTRA),
                             seen=seen)
    report = _api().prove(run.ref(VAL), [run.graph], dispatcher=_dispatcher(layer))
    assert report.proven is False
    assert [r.failure for r in report.rederived[0].runs] == [
        "substitute_takes_an_answer_the_run_withheld"
    ]
    assert seen == []


def test_a_substitute_that_reads_the_mental_model_is_not_run():
    reader = _reader()
    seen = []
    layer = _layer(reader, _substitute(reader, seen=seen, reads_mm=True))
    run = _reading_run(MentalModel(session_id="s", user_id="u"), reader)
    report = _api().prove(run.ref(DEC), [run.graph], dispatcher=_dispatcher(layer))
    assert [r.failure for r in report.rederived[0].runs] == ["substitute_reads_the_mental_model"]
    assert _why(report) == {(VAL, "no_substitute_agreed")}
    assert seen == []


def test_a_plain_step_that_read_the_mental_model_is_not_proven():
    reader = _reader()
    layer = _layer(reader, _substitute(reader))
    run = _reading_run(MentalModel(session_id="s", user_id="u"), reader,
                       plain=dict(NONE, reads_mm=True))
    report = _api().prove(run.ref(DEC), [run.graph], dispatcher=_dispatcher(layer))
    assert _why(report) == {(DEC, "reads_the_mental_model")}


def test_a_step_whose_reads_were_not_recorded_is_not_proven():
    reader = _reader()
    layer = _layer(reader, _substitute(reader))
    run = _reading_run(MentalModel(session_id="s", user_id="u"), reader)
    manifest = next(n for n in run.graph.nodes.values() if n.type_name == "RunManifest")
    del manifest.value["capacity_declarations"][PLAIN]["reads_roles"]
    report = _api().prove(run.ref(DEC), [run.graph], dispatcher=_dispatcher(layer))
    assert _why(report) == {(DEC, "reads_not_recorded")}


def test_a_step_that_consumed_an_origin_record_is_not_proven():
    reader = _reader()
    layer = _layer(reader, _substitute(reader))
    run = _Run(MentalModel(session_id="s", user_id="u"), "run-1", starts={SRC: "x"},
               declarations={reader.iri: CONSULTS, PLAIN: NONE})
    run.step(reader.iri, (SRC,), {VAL: True, RECORD: READING})
    run.step(PLAIN, (RECORD,), {DEC: "from the record"})
    report = _api().prove(run.ref(DEC), [run.graph], dispatcher=_dispatcher(layer))
    assert (DEC, "consumed_an_origin_record") in _why(report)


def test_the_report_names_the_roles_it_relied_on():
    reader = _reader()
    layer = _layer(reader, _substitute(reader, reads_roles=("lexicon",)))
    run = _reading_run(MentalModel(session_id="s", user_id="u"), reader,
                       plain=dict(NONE, reads_roles=["policies"]))
    report = _api().prove(run.ref(DEC), [run.graph], dispatcher=_dispatcher(layer))
    assert report.proven is True
    assert report.roles == ("lexicon", "policies")
    assert report.rederived[0].substitute_roles == ((_substitute(reader).iri, ("lexicon",)),)


def _interpreted(origin):
    run = _Run(MentalModel(session_id="s", user_id="u"), "run-1", starts={SRC: "x"},
               origins={SRC: origin}, declarations={PLAIN: NONE})
    run.step(PLAIN, (SRC,), {DEC: 1})
    return _api().prove(run.ref(DEC), [run.graph], dispatcher=_dispatcher(_layer())), run


def test_an_interpreted_start_is_a_premise_naming_interpretation_s_roles():
    report, run = _interpreted({
        "kind": "interpreted", "model_capacities": [],
        "capacity_declarations": {"capacity:process:identity": dict(NONE, reads_roles=["lexicon"])},
    })
    assert (report.proven, report.premises, report.roles) == (True, (run.ref(SRC),), ("lexicon",))


def test_an_interpreted_start_with_no_snapshot_is_not_proven():
    report, _ = _interpreted({"kind": "interpreted", "model_capacities": []})
    assert _why(report) == {(SRC, "interpretation_declarations_not_recorded")}


def test_an_interpreted_start_that_used_the_model_is_not_proven():
    report, _ = _interpreted({
        "kind": "interpreted", "model_capacities": ["capacity:process:read"],
        "capacity_declarations": {"capacity:process:read": CONSULTS},
    })
    assert _why(report) == {(SRC, "interpreted_with_the_model")}


def test_a_gap_in_the_lineage_is_not_proven():
    report, _ = _interpreted({"kind": "unrecorded"})
    assert _why(report) == {(SRC, "origin_unrecorded")}


def test_a_dispatcher_with_a_model_bound_is_refused():
    reader = _reader()
    layer = _layer(reader, _substitute(reader))
    run = _reading_run(MentalModel(session_id="s", user_id="u"), reader)
    with pytest.raises(ModelBoundError):
        _api().prove(run.ref(DEC), [run.graph], dispatcher=_dispatcher(layer, llm=object()))
    with pytest.raises(ModelBoundError):
        _api().proven_walk([run.graph], dispatcher=_dispatcher(layer, llm=object()))


def test_nothing_is_written():
    reader = _reader()
    layer = _layer(reader, _substitute(reader))
    run = _reading_run(MentalModel(session_id="s", user_id="u"), reader)
    before = (len(run.graph.nodes), len(run.graph.edges))
    _api().prove(run.ref(DEC), [run.graph], dispatcher=_dispatcher(layer))
    assert (len(run.graph.nodes), len(run.graph.edges)) == before


def test_the_walk_with_proof_status_lists_each_value_once():
    reader = _reader()
    layer = _layer(reader, _substitute(reader))
    run = _reading_run(MentalModel(session_id="s", user_id="u"), reader)
    listed = _api().proven_walk([run.graph], dispatcher=_dispatcher(layer))
    assert sorted((e.datastate, r.proven) for e, r in listed) == sorted([(VAL, True), (DEC, True)])
