"""CR: capacity_mm persist + submind — Slice C (D-B): the SubMindArbiter grounds
its resolver run into the REAL injected MentalModel.

The arbiter now takes a mandatory ``mm`` and runs its resolver via
``execute_pipeline(..., mm=self._mm, pipeline_run_ref=<fresh per run>)``, so each
resolver dispatch records a per-run grounding DAG (CapacityInstance +
DataStateInstance nodes wired by ``PRODUCES``/``CONSUMES``) into ``mm.capacity_mm``,
keyed on its own ``(task_id, run_ref)``. Covers CR §6: grounding with edges, two
concurrent resolvers → distinct graphs, a re-dispatch (replan) that does not
overwrite, and the phase-1 interpret-resolve MM-less carve-out left unchanged.

Pure unit tests with injected fakes (synchronous inline executor, fake
dispatcher/plan) + a real MentalModel — no threads, no FalkorDB (Py3.10 sandbox).
The writer-level same-``task_id`` replan / distinct-task guarantees are additionally
covered at the ``execute_pipeline`` boundary by
``tests/phase_48/test_capacity_mm_writer.py``.
"""

from __future__ import annotations

import pytest

from mindsos_capacity.tiers import TierEnum
from mindsos_capacity.identifiers import (
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_DATASTATE_INSTANCE,
)
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.pipeline_execution import execute_pipeline
from mindsos_intelligence.resources import ResourceLedger
from mindsos_intelligence.submind_arbiter import SubMindArbiter
from mindsos_intelligence.capacity_mm_writer import RUN_GRAPH_ROLE_PREFIX


# ── fakes ─────────────────────────────────────────────────────────────


class _Fut:
    def __init__(self, ret=None, exc=None):
        self._r, self._e = ret, exc

    def add_done_callback(self, cb):
        cb(self)

    def exception(self):
        return self._e

    def result(self):
        if self._e:
            raise self._e
        return self._r


class _Exec:
    """Synchronous executor: runs the resolver inline at submit."""

    def submit(self, fn, *, tier, task_id, score=None, cancel_token=None,
               preempt=True, held_resources=()):
        try:
            return _Fut(ret=fn())
        except BaseException as exc:  # noqa: BLE001
            return _Fut(exc=exc)


class _Inv:
    def __init__(self, outputs):
        self.success = True
        self.outputs = outputs
        self.error = None
        self.needs_input = None


class _Dispatcher:
    """Returns each capacity's declared outputs from a fixed table."""

    def __init__(self, outputs_by_cap):
        self._out = outputs_by_cap
        self.calls = []

    def dispatch(self, cap, inputs, *, cancel_token=None, task_id=None, step_id=None):
        self.calls.append(cap)
        return _Inv(dict(self._out.get(cap, {})))


class _Step:
    def __init__(self, cap, inputs=()):
        self.capacity_iri = cap
        self.input_datastates = tuple(inputs)
        self.output_datastates = ()


class _Pipeline:
    def __init__(self, steps):
        self.steps = tuple(steps)


class _Sig:
    def __init__(self, name, score=100, reading=None):
        self.submind_name = name
        self.tier = TierEnum.FOREGROUND
        self.attention_score = score
        self.reading = reading
        self.severity = 0.5
        self.kind = "signal"


class _Defn:
    def __init__(self, res=(), goal="datastate:energy",
                 start="datastate:reading", fb=None):
        self.resolver_resources = res
        self.resolver_goal_datastate = goal
        self.resolver_start_datastate = start
        self.fallback_resolver = fb


def _charge_plan(start, goal):
    # reading -(charge)-> energy
    return _Pipeline([_Step("capacity:charge", inputs=("datastate:reading",))])


def _arb(mm, executor, dispatcher, ledger, plan=_charge_plan):
    a = SubMindArbiter(executor, dispatcher, ledger, mm=mm, plan_fn=plan,
                       pipeline_not_found=Exception)
    a.install_on_ledger()
    return a


def _run_graphs(mm):
    return [g for g in mm.capacity_mm.graphs.values()
            if g.role.startswith(RUN_GRAPH_ROLE_PREFIX)]


# ── tests (CR §6) ──────────────────────────────────────────────────────


def test_resolver_grounds_capacity_and_outputs_with_edges():
    """§6.1: one resolver run → one CapacityInstance + the seed/output
    DataStateInstances, wired by intra-graph CONSUMES/PRODUCES, in its own
    per-run graph."""
    mm = MentalModel(session_id="s", user_id="u")
    dp = _Dispatcher({"capacity:charge": {"datastate:energy": 42}})
    a = _arb(mm, _Exec(), dp, ResourceLedger())

    a.on_need(_Sig("energy", reading=[[1]]), TierEnum.FOREGROUND, _Defn(res=("arm",)))

    assert "capacity:charge" in dp.calls          # resolver actually executed
    graphs = _run_graphs(mm)
    assert len(graphs) == 1                        # exactly one per-run graph
    g = graphs[0]
    caps = [n for n in g.nodes.values() if n.type_name == NODE_TYPE_CAPACITY_INSTANCE]
    dss = [n for n in g.nodes.values() if n.type_name == NODE_TYPE_DATASTATE_INSTANCE]
    assert len(caps) == 1                          # one CapacityInstance
    assert len(dss) == 2                           # seed(reading) + output(energy)
    edge_types = sorted(e.type_name for e in g.edges.values())
    assert edge_types == [EDGE_CONSUMES, EDGE_PRODUCES]
    # D-A: edges are intra-graph; the writer creates no intergraph edges.
    assert len(mm.capacity_mm.intergraph_edges) == 0


def test_two_concurrent_resolvers_write_distinct_graphs():
    """§6.2: two resolvers (disjoint resources) both dispatch and land in
    disjoint per-run graphs — real isolation, no overwrite."""
    mm = MentalModel(session_id="s", user_id="u")
    dp = _Dispatcher({"capacity:charge": {"datastate:energy": 1}})
    a = _arb(mm, _Exec(), dp, ResourceLedger())

    a.on_need(_Sig("energy", reading=[[1]]), TierEnum.FOREGROUND, _Defn(res=("arm",)))
    a.on_need(_Sig("coolant", reading=[[2]]), TierEnum.FOREGROUND, _Defn(res=("pump",)))

    graphs = _run_graphs(mm)
    assert len(graphs) == 2
    assert set(graphs[0].nodes).isdisjoint(set(graphs[1].nodes))


def test_redispatch_same_submind_does_not_overwrite():
    """§6.3 (replan): a second resolver dispatch for the SAME need mints a
    fresh per-run graph (fresh task_id → fresh run_ref); the first run's nodes
    are untouched. (Same-``task_id`` / different-``run_ref`` replan is covered
    at the ``execute_pipeline`` boundary by test_capacity_mm_writer.)"""
    mm = MentalModel(session_id="s", user_id="u")
    dp = _Dispatcher({"capacity:charge": {"datastate:energy": 1}})
    a = _arb(mm, _Exec(), dp, ResourceLedger())

    a.on_need(_Sig("energy", reading=[[1]]), TierEnum.FOREGROUND, _Defn(res=()))
    # Re-emit while the first run is already serviced-and-parked → re-dispatch.
    a.on_need(_Sig("energy", reading=[[2]]), TierEnum.FOREGROUND, _Defn(res=()))

    graphs = _run_graphs(mm)
    assert len(graphs) == 2
    assert set(graphs[0].nodes).isdisjoint(set(graphs[1].nodes))
    for g in graphs:                               # both runs grounded their full DAG
        assert len(g.nodes) == 3                   # 2 DataStateInstances + 1 CapacityInstance


def test_mm_less_interpret_carveout_unchanged():
    """§6.7: the phase-1 interpret-resolve carve-out calls execute_pipeline
    with mm=None — value-only, no grounding, no ``pipeline_run_ref`` required
    (CR §2.5; the carve-out stays MM-less permanently)."""
    control = MentalModel(session_id="s", user_id="u")   # never touched
    dp = _Dispatcher({"capacity:charge": {"datastate:energy": 7}})
    pipe = _Pipeline([_Step("capacity:charge", inputs=("datastate:reading",))])

    res = execute_pipeline(dp, pipe, {"datastate:reading": [[1]]}, task_id="interpret")
    assert res.success and res.outputs["datastate:energy"] == 7
    # No mm supplied → nothing grounded (a fresh MM stays empty).
    assert sum(len(g.nodes) for g in control.capacity_mm.graphs.values()) == 0


def test_arbiter_requires_real_mm():
    """D-B is mandatory: the arbiter refuses to construct without a real MM."""
    dp = _Dispatcher({})
    with pytest.raises(TypeError):        # `mm` is a required keyword-only arg
        SubMindArbiter(_Exec(), dp, ResourceLedger(), plan_fn=_charge_plan)
    with pytest.raises(ValueError):       # an explicit None is rejected loudly
        SubMindArbiter(_Exec(), dp, ResourceLedger(), mm=None, plan_fn=_charge_plan)
