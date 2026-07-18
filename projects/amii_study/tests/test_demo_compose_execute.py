"""Guard test for the Amii demo path: compose + execute end-to-end,
honest unit-refusal, and honest no-route. Mirrors amii_demo.py."""
import pytest
from mindsos_capacity import (
    Capacity, CapacityLayer, DataState, ShapeDescriptor,
    INPUT_GROUP_ALL_REQUIRED, CATEGORY_PERCEPTION, CATEGORY_COMPREHENSION,
    CATEGORY_DECISION,
)
from mindsos_capacity.pipeline import find_pipeline
from mindsos_capacity.exceptions import PipelineNotFoundError
from mindsos_capacity.needs_input import NeedsInput
from mindsos_capacity.runtime import invoke
from mindsos_intelligence.pipeline_execution import execute_pipeline

def IRI(s): return f"datastate:t.{s}"
RAW, PARSED, NORMAL, COND, ACTION, DIAG = map(IRI, (
    "raw_signal","parsed_signal","normal_signal","condition","action","diagnosis"))
CONDITIONS = {"pressure_high": "vent", "nominal": "hold"}

def _ds(s):
    n = f"t.{s}"; return DataState(name=n, shape=ShapeDescriptor.scalar("str", opaque_tag=n))
def _cap(name, cat, ins, outs, impl):
    return Capacity(name=name, category=cat, inputs=tuple(ins), outputs=tuple(outs),
                    input_group=INPUT_GROUP_ALL_REQUIRED, implementation=impl)

def _classify(**kw):
    v = kw[NORMAL]
    if v not in CONDITIONS:
        return NeedsInput(question=f"unknown {v!r}", missing=COND, choices={c: c for c in CONDITIONS})
    return {COND: v}

@pytest.fixture
def cl():
    layer = CapacityLayer(categories=(CATEGORY_PERCEPTION, CATEGORY_COMPREHENSION, CATEGORY_DECISION))
    for s in ("raw_signal","parsed_signal","normal_signal","condition","action","diagnosis"):
        layer.register_datastate(_ds(s), allow_new_realm=True)
    layer.register_capacity(_cap("parse",     CATEGORY_PERCEPTION,    [RAW],    [PARSED], lambda **kw: {PARSED: str(kw[RAW]).strip().lower()}))
    layer.register_capacity(_cap("normalize", CATEGORY_COMPREHENSION, [PARSED], [NORMAL], lambda **kw: {NORMAL: kw[PARSED].replace(" ", "_")}))
    layer.register_capacity(_cap("classify",  CATEGORY_DECISION,      [NORMAL], [COND],   _classify))
    layer.register_capacity(_cap("recommend", CATEGORY_DECISION,      [COND],   [ACTION], lambda **kw: {ACTION: CONDITIONS[kw[COND]]}))
    return layer

class _Disp:
    def __init__(self, cl): self.cl = cl
    def dispatch(self, ci, inputs, *, cancel_token=None, task_id=None, step_id=None):
        return invoke(self.cl.get_declaration(ci), inputs, task_id=task_id, step_id=step_id)

def test_composes_and_executes_end_to_end(cl):
    pipe = find_pipeline(cl, start_datastate=RAW, target_datastate=ACTION)
    assert [s.capacity_iri.split(":")[-1] for s in pipe.steps] == ["parse","normalize","classify","recommend"]
    res = execute_pipeline(_Disp(cl), pipe, {RAW: "  Pressure High "}, task_id="t")
    assert res.success and res.outputs[ACTION] == "vent"

def test_unit_refuses_out_of_vocab(cl):
    pipe = find_pipeline(cl, start_datastate=RAW, target_datastate=ACTION)
    res = execute_pipeline(_Disp(cl), pipe, {RAW: "gremlins"}, task_id="t")
    assert res.needs_input is not None and not res.success

def test_no_route_raises_not_found(cl):
    with pytest.raises(PipelineNotFoundError):
        find_pipeline(cl, start_datastate=RAW, target_datastate=DIAG)
