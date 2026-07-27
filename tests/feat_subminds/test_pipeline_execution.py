"""feat/subminds Slice 2 — core pipeline-step executor (pipeline_execution).

Exercises the real DAG-step walk: blackboard threading, fail-stop, and
cooperative cancel between steps. Pure (fake dispatcher) — Py3.10 sandbox.
"""

from __future__ import annotations

from mindsos_intelligence.pipeline_execution import (
    PipelineExecutionResult,
    execute_pipeline,
)


class _Step:
    def __init__(self, cap, ins=(), outs=()):
        self.capacity_iri = cap
        self.input_datastates = tuple(ins)
        self.output_datastates = tuple(outs)


class _Pipeline:
    def __init__(self, steps=()):
        self.steps = tuple(steps)


class _Res:
    def __init__(self, success=True, outputs=None, error=None):
        self.success = success
        self.outputs = outputs or {}
        self.error = error


class _Dispatcher:
    def __init__(self, by_cap=None):
        self.calls = []
        self._by_cap = by_cap or {}

    def dispatch(self, cap, inputs, *, cancel_token=None, request_id=None, step_id=None):
        self.calls.append((cap, dict(inputs), step_id))
        return self._by_cap.get(cap, _Res())


class _Token:
    def __init__(self, set_=False):
        self._set = set_

    def is_set(self):
        return self._set


def test_noop_pipeline_is_success():
    r = execute_pipeline(_Dispatcher(), _Pipeline(steps=()), {"x": 1}, request_id="t")
    assert isinstance(r, PipelineExecutionResult)
    assert r.success and r.steps_run == 0 and r.outputs == {"x": 1}


def test_multi_step_threads_blackboard():
    dp = _Dispatcher(
        by_cap={
            "cap.a": _Res(outputs={"b": 10}),
            "cap.b": _Res(outputs={"c": 20}),
        }
    )
    pipe = _Pipeline(
        steps=[_Step("cap.a", ins=("a",), outs=("b",)), _Step("cap.b", ins=("b",), outs=("c",))]
    )
    r = execute_pipeline(dp, pipe, {"a": 1}, request_id="t")
    assert r.success and r.steps_run == 2
    # step b received the output of step a off the blackboard
    assert dp.calls[1][0] == "cap.b" and dp.calls[1][1] == {"b": 10}
    assert r.outputs["c"] == 20


def test_failure_stops_walk():
    dp = _Dispatcher(by_cap={"cap.a": _Res(success=False, error=ValueError("boom"))})
    pipe = _Pipeline(steps=[_Step("cap.a", outs=("b",)), _Step("cap.b")])
    r = execute_pipeline(dp, pipe, {}, request_id="t")
    assert not r.success and r.failed_step == "cap.a" and r.steps_run == 0
    assert len(dp.calls) == 1  # second step never dispatched


def test_cancel_before_step():
    dp = _Dispatcher()
    pipe = _Pipeline(steps=[_Step("cap.a")])
    r = execute_pipeline(dp, pipe, {}, request_id="t", cancel_token=_Token(set_=True))
    assert not r.success and r.cancelled and not dp.calls
