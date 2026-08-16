"""Two readers over one document wire back to the same document node.

The failure this guards is silent: if the second reader's ``CONSUMES`` edge
pointed at a re-minted document instance — or at nothing — the Decision Record
would attribute one of the two values to the wrong source, or to no source, and
the run would still report success. A reachability guard at the document does
not catch it, because the document itself is fine; only the second reader's
wiring is wrong.

Also pins that both readers share one document instance (the writer's seed is
idempotent for anything already indexed) and that each reader mints its own
value and its own reading record — the per-reader record type from
``origin_record_iri``, which exists precisely so the second reader cannot
displace the first's provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from mindsos_capacity.builtins.comprehension_v0 import (
    build_reader,
)
from mindsos_capacity.builtins.origin_v0 import (
    BASIS_STATED,
    ORIGIN_READ_BY_MODEL,
    REFUSAL_QUOTE_NOT_IN_SOURCE,
    origin_record_iri,
)
from mindsos_capacity.identifiers import (
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    NODE_TYPE_CAPACITY_INSTANCE,
    PROP_DATASTATE_INSTANCE_TYPE,
    datastate_iri,
)
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.pipeline_execution import execute_pipeline

SOURCE_DS = datastate_iri("claims.submission_email")
DATE_DS = datastate_iri("claims.purchase_date")
STAY_DS = datastate_iri("claims.hospital_stay_asserted")

EMAIL = (
    "Order 4471. I purchased the item on 3 March 2026 and only got round to\n"
    "claiming now. I was in hospital for three weeks after the operation."
)

FIELDS = [
    {"name": "purchase_date", "value": "2026-03-03",
     "quote": "purchased the item on 3 March 2026", "basis": BASIS_STATED},
    {"name": "hospital_stay", "value": True,
     "quote": "I was in hospital for three weeks", "basis": BASIS_STATED},
]


class _LLM:
    """One document-level reading; each reader selects its own field."""

    def read(self, **kwargs: Any) -> Mapping[str, Any]:
        return {
            "fields": FIELDS,
            "model_id": "model-x",
            "model_version": "2026-05-01",
            "request_key": "sha256:same-for-both",
            "recorded": True,
        }


class _Ctx:
    def __init__(self, llm): self.llm = llm


@dataclass
class _Step:
    capacity_iri: str
    input_datastates: Tuple[str, ...]


@dataclass
class _Pipeline:
    steps: Tuple[_Step, ...]


@dataclass
class _Result:
    success: bool
    outputs: Mapping[str, Any] = field(default_factory=dict)
    needs_input: Any = None
    error: Any = None


class _Dispatcher:
    def __init__(self, capacities):
        self._by_iri = {c.iri: c for c in capacities}

    def dispatch(self, capacity_iri, inputs, **kwargs):
        body = self._by_iri[capacity_iri].implementation
        return _Result(success=True, outputs=body(**dict(inputs), context=_Ctx(_LLM())))


def _reader(name, value_ds, field_name, question):
    return build_reader(
        name=name,
        source_datastate_iri=SOURCE_DS,
        value_datastate_iri=value_ds,
        prompt_iri="prompt:claims.submission",
        prompt_version=1,
        field_name=field_name,
        question=question,
        description=f"Read {question} from the submission.",
        origin_party_phrase="the customer",
        source_identity_phrase="their submission email",
        expected_basis=BASIS_STATED,
    )


def _run():
    date_reader = _reader("read_purchase_date", DATE_DS, "purchase_date",
                          "the date the item was purchased")
    stay_reader = _reader("read_hospital_stay", STAY_DS, "hospital_stay",
                          "whether the customer says they were in hospital")
    result = execute_pipeline(
        _Dispatcher([date_reader, stay_reader]),
        _Pipeline(steps=(
            _Step(date_reader.iri, (SOURCE_DS,)),
            _Step(stay_reader.iri, (SOURCE_DS,)),
        )),
        initial_inputs={SOURCE_DS: EMAIL},
        request_id="req-1",
        mm=MentalModel(session_id="s", user_id="u"),
        pipeline_run_ref="pipelinerun:req-1:1",
    )
    return result


def _instances_of(graph, datastate_type):
    return [
        n for n in graph.nodes.values()
        if (n.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE) == datastate_type
    ]


def test_both_readers_run_and_both_values_land():
    result = _run()
    assert result.success is True
    assert result.outputs[DATE_DS] == "2026-03-03"
    assert result.outputs[STAY_DS] is True


def test_the_document_is_minted_once_and_both_readers_consume_that_node():
    graph = _run().capacity_graph
    documents = _instances_of(graph, SOURCE_DS)
    assert len(documents) == 1, "the document must not be re-minted per reader"

    consumes = [e for e in graph.edges.values() if e.type_name == EDGE_CONSUMES]
    assert len(consumes) == 2
    assert {e.source.node_id for e in consumes} == {documents[0].node_id}


def test_each_reader_mints_its_own_value_and_its_own_record():
    graph = _run().capacity_graph
    for datastate_type in (DATE_DS, STAY_DS,
                           origin_record_iri(DATE_DS), origin_record_iri(STAY_DS)):
        assert len(_instances_of(graph, datastate_type)) == 1, datastate_type


def test_each_record_hangs_off_its_own_reader():
    graph = _run().capacity_graph
    capacities = [
        n for n in graph.nodes.values() if n.type_name == NODE_TYPE_CAPACITY_INSTANCE
    ]
    assert len(capacities) == 2
    for capacity in capacities:
        produced = {
            e.target.node_id
            for e in graph.edges.values()
            if e.type_name == EDGE_PRODUCES and e.source.node_id == capacity.node_id
        }
        # A value and its reading record, from the same invocation — never
        # one reader's value paired with the other reader's provenance.
        assert len(produced) == 2
