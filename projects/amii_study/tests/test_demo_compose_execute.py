"""Guard test for the Amii live-demo path: compose -> execute -> refuse.

Imports the single demo domain (``amii_demo.domain``) so the exact path the
live demo runs is what's validated: compose a pipeline nobody wired, execute
it end-to-end, refuse at the unit on an out-of-vocab reading, and report
no-route for an unreachable target. Green here = the demo cannot break on
stage.
"""
import pytest

from mindsos_capacity.pipeline import find_pipeline
from mindsos_capacity.exceptions import PipelineNotFoundError
from mindsos_intelligence.pipeline_execution import execute_pipeline

from amii_demo.domain import build_layer, Dispatcher, RAW, ACTION, DIAGNOSIS


@pytest.fixture
def cl():
    return build_layer()


def test_composes_and_executes_end_to_end(cl):
    pipe = find_pipeline(cl, start_datastate=RAW, target_datastate=ACTION)
    assert [s.capacity_iri.split(":")[-1] for s in pipe.steps] == [
        "parse",
        "normalize",
        "classify",
        "recommend",
    ]
    res = execute_pipeline(Dispatcher(cl), pipe, {RAW: "  Pressure High "}, task_id="t")
    assert res.success and res.outputs[ACTION] == "vent"


def test_unit_refuses_out_of_vocab(cl):
    pipe = find_pipeline(cl, start_datastate=RAW, target_datastate=ACTION)
    res = execute_pipeline(Dispatcher(cl), pipe, {RAW: "gremlins"}, task_id="t")
    assert res.needs_input is not None and not res.success


def test_no_route_raises_not_found(cl):
    with pytest.raises(PipelineNotFoundError):
        find_pipeline(cl, start_datastate=RAW, target_datastate=DIAGNOSIS)
