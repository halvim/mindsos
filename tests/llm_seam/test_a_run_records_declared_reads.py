"""A run records the reads each composed capacity declared (``mindsos_llm``
plan I-20, gate 2; ruling R48).

R48: *"the run records the declaration"*. Where (owner, 2026-10-23, *"A for
now"*): the manifest's ``capacity_declarations`` map (ADR-0201 amendment 8
section 5) - one more field in each composed capacity's entry, not a key of its
own. Two fields, both read declarations:

* ``reads_roles`` - the L2 roles the capacity declared it reads (gate 1). A
  proven re-run (I-21) names these as premises.
* ``reads_mm`` - whether it declared the mental-model channel. R53 says such a
  capacity is named and not run at re-run; R52's reason says that is read from
  the run's own snapshot, since an upsert can re-bind the declaration later.

Both are always present in an entry minted from now on. A field ABSENT from an
entry - every Episode stored before this gate - means *not recorded*, never
*read nothing* (amendment 8 section 5).

The persisted shape is spelled as literals on purpose, as in the gate-3 file
next door: it is a contract on stored Episodes.
"""

from __future__ import annotations

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
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.pipeline_execution import execute_pipeline

KEY = "capacity_declarations"

DS_A = datastate_iri("rdx.a")
DS_B = datastate_iri("rdx.b")
DS_C = datastate_iri("rdx.c")
DS_D = datastate_iri("rdx.d")

CAP_PLAIN = capacity_iri(CATEGORY_DERIVATION, "rdx_plain")
CAP_LOOK = capacity_iri(CATEGORY_DERIVATION, "rdx_look")
CAP_MM = capacity_iri(CATEGORY_DERIVATION, "rdx_mm")


class FakeSession:
    session_id = "s"
    user_id = "u"
    actor_role = "user"
    capabilities: set = set()

    def has(self, capability: str) -> bool:
        return False


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
    for name in ("rdx.a", "rdx.b", "rdx.c", "rdx.d"):
        layer.register_datastate(
            DataState(
                name=name,
                shape=ShapeDescriptor.opaque(name),
                description=name.replace("rdx.", "the "),
                provenance_category=CATEGORY_DERIVATION,
            ),
            session=session,
            allow_new_realm=True,
        )
    _register(layer, session, "rdx_plain", (DS_A,), (DS_B,),
              lambda **kw: {DS_B: f"b {kw[DS_A]}"})
    _register(layer, session, "rdx_look", (DS_B,), (DS_C,),
              lambda **kw: {DS_C: f"c {kw[DS_B]}"},
              reads_roles=("policies",))
    _register(layer, session, "rdx_mm", (DS_C,), (DS_D,),
              lambda **kw: {DS_D: f"d {kw[DS_C]}"},
              reads_mm=True)
    mm = MentalModel(session_id="s", user_id="u")
    dispatcher = L4Dispatcher(layer, session=session)
    return layer, session, mm, dispatcher


def _run(harness, ref="pipelinerun:rdx"):
    _, _, mm, dispatcher = harness
    pipeline = execution._compose_pipeline(
        dispatcher, (DS_A,), DS_D, execution.FINDER_BFS,
    ).pipeline
    result = execute_pipeline(
        dispatcher, pipeline, {DS_A: "q"},
        request_id=ref, mm=mm, pipeline_run_ref=ref,
    )
    assert result.success, result.error
    manifests = [
        n for n in result.capacity_graph.nodes.values()
        if n.type_name == NODE_TYPE_RUN_MANIFEST
    ]
    assert len(manifests) == 1
    snapshot = manifests[0].value.get(KEY)
    assert snapshot is not None, "no capacity_declarations in the manifest"
    assert set(snapshot) == {CAP_PLAIN, CAP_LOOK, CAP_MM}
    return snapshot


def test_a_declared_reader_records_its_roles():
    assert _run(_harness())[CAP_LOOK]["reads_roles"] == ["policies"]


def test_a_capacity_that_reads_nothing_records_so():
    entry = _run(_harness())[CAP_PLAIN]
    assert entry["reads_roles"] == []
    assert entry["reads_mm"] is False


def test_a_mental_model_reader_is_recorded_so():
    entry = _run(_harness())[CAP_MM]
    assert entry["reads_mm"] is True
    assert entry["reads_roles"] == []


def test_each_run_records_the_reads_declared_when_it_ran():
    """R45's hazard, for reads: an upsert re-binds the declaration. The run
    before it keeps what was declared then; the run after it, the new one."""
    harness = _harness()
    layer, session, _, _ = harness
    before = _run(harness, "pipelinerun:rdx-1")
    _register(layer, session, "rdx_look", (DS_B,), (DS_C,),
              lambda **kw: {DS_C: "c"}, upsert=True)
    after = _run(harness, "pipelinerun:rdx-2")
    assert before[CAP_LOOK]["reads_roles"] == ["policies"]
    assert after[CAP_LOOK]["reads_roles"] == []


def test_every_entry_carries_every_declaration_field():
    """The field set is the contract a stored Episode is read against: with
    every field always present, an absent one can only mean *not recorded*."""
    for iri, entry in _run(_harness()).items():
        assert set(entry) == {
            "consults_llm", "model_answer_inputs", "reads_roles", "reads_mm",
        }, iri
