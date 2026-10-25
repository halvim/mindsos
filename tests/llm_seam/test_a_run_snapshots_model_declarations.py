"""A run snapshots the model declarations of what it composed (``mindsos_llm``
plan I-19, gate 3).

R52 says a value is the model's when a capacity that declared ``consults_llm``
WHEN IT RAN produced it, or a reader consumed it as a declared answer input
(R44) — and that those declarations are read from the run's own snapshot, not
today's registry. Today's registry cannot answer for a stored Episode:
``register_capacity(if_exists="upsert")`` re-binds a declaration and a Local
declaration shadows the Global one (R45's measurement), so a capacity that
consulted the model when the run happened can declare it does not by the time
anyone asks.

Gate 3's claim: every run manifest ``execute_pipeline`` mints carries
``capacity_declarations`` — for every capacity the run composed, its
``consults_llm`` and ``model_answer_inputs`` as resolved when the run started,
both fields always present. A capacity missing from the map is NOT RECORDED,
never *does not consult the model* (ADR-0201 amendment 5's key-presence rule,
applied per entry). A run that composed nothing records an empty map.

The persisted shape is spelled as literals on purpose: it is a contract on
stored Episodes, and renaming a constant must not silently change it.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import CapacityLayer
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_DERIVATION,
    NODE_TYPE_RUN_MANIFEST,
    capacity_iri,
    datastate_iri,
)
from mindsos_intelligence import execution
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.execution import LeafPipelineNotFound
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.pipeline_execution import execute_pipeline
from mindsos_intelligence.plan_construction import PlanResult

KEY = "capacity_declarations"

DS_TEXT = datastate_iri("smd.text")
DS_CLEAN = datastate_iri("smd.clean")
DS_ANSWER = datastate_iri("smd.answer")
DS_VERDICT = datastate_iri("smd.verdict")
DS_NOWHERE = datastate_iri("smd.nowhere")

CAP_CLEAN = capacity_iri(CATEGORY_DERIVATION, "smd_clean")
CAP_ASK = capacity_iri(CATEGORY_DERIVATION, "smd_ask")
CAP_READ = capacity_iri(CATEGORY_DERIVATION, "smd_read_answer")

#: Gate 3's two fields plus I-20 gate 2's two read fields (R48, R53); the
#: read fields are pinned in ``test_a_run_records_declared_reads.py``.
NO_READS = {"reads_roles": [], "reads_mm": False}
PLAIN = {"consults_llm": False, "model_answer_inputs": [], **NO_READS}


class FakeSession:
    session_id = "s"
    user_id = "u"
    actor_role = "user"
    capabilities: set = set()

    def has(self, capability: str) -> bool:
        return False


class _NoCallModel:
    """Bound so dispatch admits a ``consults_llm`` capacity; never called —
    the bodies here ignore it, and calling it fails the test."""

    def read(self, **kwargs):
        raise AssertionError("no model call is made in this file")


def _register(layer, session, name, inputs, outputs, body, *, upsert=False, **flags):
    layer.register_capacity(
        Capacity(
            name=name, category=CATEGORY_DERIVATION,
            inputs=inputs, outputs=outputs, implementation=body,
            description=name.replace("_", " "), **flags,
        ),
        session=session,
        **({"if_exists": "upsert"} if upsert else {}),
    )


def _harness():
    session = FakeSession()
    layer = CapacityLayer()
    for name in ("smd.text", "smd.clean", "smd.answer", "smd.verdict", "smd.nowhere"):
        layer.register_datastate(
            DataState(
                name=name,
                shape=ShapeDescriptor.opaque(name),
                description=name.replace("smd.", "the "),
                provenance_category=CATEGORY_DERIVATION,
            ),
            session=session,
            allow_new_realm=True,
        )
    _register(layer, session, "smd_clean", (DS_TEXT,), (DS_CLEAN,),
              lambda **kw: {DS_CLEAN: kw[DS_TEXT].strip()})
    _register(layer, session, "smd_ask", (DS_CLEAN,), (DS_ANSWER,),
              lambda **kw: {DS_ANSWER: f"asked {kw[DS_CLEAN]}"},
              consults_llm=True)
    _register(layer, session, "smd_read_answer", (DS_ANSWER,), (DS_VERDICT,),
              lambda **kw: {DS_VERDICT: f"read {kw[DS_ANSWER]}"},
              model_answer_inputs=(DS_ANSWER,))
    mm = MentalModel(session_id="s", user_id="u")
    dispatcher = L4Dispatcher(layer, session=session, llm=_NoCallModel())
    return layer, session, mm, dispatcher


def _manifest(graph):
    manifests = [n for n in graph.nodes.values() if n.type_name == NODE_TYPE_RUN_MANIFEST]
    assert len(manifests) == 1
    return manifests[0].value


def _run(harness, ref="pipelinerun:smd"):
    _, _, mm, dispatcher = harness
    pipeline = execution._compose_pipeline(
        dispatcher, (DS_TEXT,), DS_VERDICT, execution.FINDER_BFS,
    ).pipeline
    result = execute_pipeline(
        dispatcher, pipeline, {DS_TEXT: " q "},
        request_id=ref, mm=mm, pipeline_run_ref=ref,
    )
    assert result.success
    return _manifest(result.capacity_graph).get(KEY)


def test_every_composed_capacity_has_an_entry_with_every_field():
    snapshot = _run(_harness())
    assert snapshot is not None, "no capacity_declarations in the manifest"
    assert set(snapshot) == {CAP_CLEAN, CAP_ASK, CAP_READ}
    assert snapshot[CAP_CLEAN] == PLAIN


def test_a_capacity_that_consults_the_model_is_recorded_so():
    snapshot = _run(_harness())
    assert snapshot is not None, "no capacity_declarations in the manifest"
    assert snapshot[CAP_ASK] == {
        "consults_llm": True, "model_answer_inputs": [], **NO_READS,
    }


def test_an_answer_fed_reader_records_which_inputs_carry_the_answer():
    snapshot = _run(_harness())
    assert snapshot is not None, "no capacity_declarations in the manifest"
    assert snapshot[CAP_READ] == {
        "consults_llm": False, "model_answer_inputs": [DS_ANSWER], **NO_READS,
    }


def test_each_run_records_what_was_declared_when_it_ran():
    """R45's hazard: an upsert re-binds the declaration. The run before it
    keeps what was declared then; the run after it records the new one."""
    harness = _harness()
    layer, session, _, _ = harness
    before = _run(harness, "pipelinerun:smd-1")
    _register(layer, session, "smd_ask", (DS_CLEAN,), (DS_ANSWER,),
              lambda **kw: {DS_ANSWER: "no model now"}, upsert=True)
    after = _run(harness, "pipelinerun:smd-2")
    assert before is not None and after is not None, "no capacity_declarations"
    assert before[CAP_ASK]["consults_llm"] is True
    assert after[CAP_ASK]["consults_llm"] is False


def test_a_run_that_composed_nothing_records_an_empty_snapshot():
    """Present and empty — recorded, nothing composed — not absent."""
    _, _, mm, dispatcher = _harness()
    writer = ChainArtifactWriter(mm, "t")
    plan = PlanResult(
        plan_ref="plan:smd-noroute",
        root_milestone_ref="m0",
        leaf_milestone_refs=["m"],
        pipeline_refs={"m": "pm"},
        leaf_targets={"m": {"start_datastate": DS_TEXT, "target_datastate": DS_NOWHERE}},
        milestone_specs={},
    )
    graphs: list = []
    with pytest.raises(LeafPipelineNotFound):
        execution.run(
            dispatcher, writer, plan, writer.emit_request_run(),
            mm=mm, run_scope="t", solve_seed={DS_TEXT: "q"}, capacity_graphs=graphs,
        )
    assert len(graphs) == 1
    assert _manifest(graphs[0]).get(KEY) == {}
