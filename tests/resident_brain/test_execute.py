"""Slice-2 tests: standalone pipeline runner, ``execute``, invoke-pipeline.

``execute`` and invoke-pipeline are inert without a declared entry / a
promoted pipeline (neither exists in a stock brain), so these tests write
synthetic fixtures directly into the Global metagraph. Where the required
role-graph is absent in the ephemeral bootstrap, the test skips rather than
failing the gate on an environment assumption.
"""

from __future__ import annotations

import pytest

from mindsos_cli.commands.brain import BrainREPL
from mindsos_server.boot import boot_brain


@pytest.fixture
def repl():
    return BrainREPL(boot_brain(user="alice"))


# ── unit: the standalone step-runner ──────────────────────────────────

def test_run_pipeline_threads_state():
    from mindsos_server.pipeline_runner import run_pipeline

    class _Step:
        def __init__(self, cap, ins, outs):
            self.capacity_iri = cap
            self.input_datastates = ins
            self.output_datastates = outs

    class _Pipe:
        steps = (_Step("cap:one", ("a",), ("b",)), _Step("cap:two", ("b",), ("c",)))
        target_datastate = "c"
        start_datastates = ("a",)

    class _Res:
        def __init__(self, outs):
            self.success = True
            self.error = None
            self.outputs = outs
            self.needs_input = None

    class _Disp:
        def dispatch(self, cap, inputs):
            src = next(iter(inputs.values()), "")
            return _Res({"b": src + "-b"} if cap == "cap:one" else {"c": src + "-c"})

    state, err = run_pipeline(_Disp(), _Pipe(), {"a": "x"})
    assert err is None
    assert state["c"] == "x-b-c"


def test_run_pipeline_reports_step_failure():
    from mindsos_server.pipeline_runner import run_pipeline

    class _Step:
        capacity_iri = "cap:boom"
        input_datastates = ()
        output_datastates = ()

    class _Pipe:
        steps = (_Step(),)
        target_datastate = "t"
        start_datastates = ()

    class _Res:
        success = False
        error = "nope"
        needs_input = None
        outputs = {}

    class _Disp:
        def dispatch(self, cap, inputs):
            return _Res()

    _state, err = run_pipeline(_Disp(), _Pipe(), {})
    assert "failed" in err


# ── fixtures over the live Global metagraph ───────────────────────────

def _global_role_graph(kl, role):
    for g in kl.global_metagraph().graphs.values():
        if g.role == role:
            return g
    return None


def _text_start_target(repl):
    """(start, target) for the space_split builtin: raw_text -> its output."""
    from mindsos_capacity.builtins.text import DS_RAW_TEXT

    view = repl.stack.global_view()
    cap = next(
        (n.node_id for n in view.iter_capacities() if n.node_id.endswith("space_split")),
        None,
    )
    if cap is None:
        return None, None
    outs = view.outputs_of(cap)
    return (DS_RAW_TEXT, outs[0]) if outs else (DS_RAW_TEXT, None)


def _install_entry_fixture(repl, name, start, target):
    from mindsos_knowledge import ROLE_INSTALLED_SKILLS
    from mindsos_knowledge.schemas.installed_skills import NODE_SKILL_INSTALL_RECORD

    g = _global_role_graph(repl.stack.kl, ROLE_INSTALLED_SKILLS)
    if g is None:
        pytest.skip("installed-skills role-graph absent in ephemeral bootstrap")
    props = {
        "bundle_name": name,
        "bundle_version": "0.1.0",
        "status": "installed",
        "action": "install",
        "recorded_at": "2026-07-05T00:00:00.000Z",
        "seq": 1,
        "entry_start_datastate": start,
        "entry_target_datastate": target,
    }
    g.add_node(
        {"bundle_name": name},
        NODE_SKILL_INSTALL_RECORD,
        properties=props,
        node_id=f"installed-skills:{name}:1",
    )


# ── execute ───────────────────────────────────────────────────────────

def test_execute_no_entry(repl):
    assert "no installed skill declares an entry" in repl.dispatch("execute foo")


def test_execute_runs_declared_entry(repl):
    start, target = _text_start_target(repl)
    if target is None:
        pytest.skip("space_split builtin / output datastate not found")
    _install_entry_fixture(repl, "textskill", start, target)
    usage = repl.dispatch("execute")
    assert "usage:" in usage and "textskill" in usage
    out = repl.dispatch('execute "the cat sat"')
    assert out.startswith("execute[textskill]:")
    assert target in out


def test_execute_ambiguous(repl):
    start, target = _text_start_target(repl)
    if target is None:
        pytest.skip("space_split not found")
    _install_entry_fixture(repl, "skillA", start, target)
    _install_entry_fixture(repl, "skillB", start, target)
    assert "ambiguous" in repl.dispatch("execute x")


# ── invoke a promoted pipeline ────────────────────────────────────────

def test_invoke_promoted_pipeline(repl):
    from mindsos_capacity.exceptions import PipelineNotFoundError
    from mindsos_capacity.pipeline import find_pipeline
    from mindsos_knowledge import ROLE_PROMOTED_PIPELINES
    from mindsos_knowledge.schemas.promoted_pipelines import NODE_PIPELINE

    start, target = _text_start_target(repl)
    if target is None:
        pytest.skip("space_split not found")
    g = _global_role_graph(repl.stack.kl, ROLE_PROMOTED_PIPELINES)
    if g is None:
        pytest.skip("promoted-pipelines role-graph absent in ephemeral bootstrap")
    try:
        pipe = find_pipeline(
            repl.stack.cl,
            session=repl.stack.session,
            start_datastate=start,
            target_datastate=target,
        )
    except PipelineNotFoundError:
        pytest.skip("no space_split pipeline available")
    g.add_node(
        pipe.to_dict(),
        NODE_PIPELINE,
        properties={"pipeline_name": "textpipe"},
        node_id="promoted-pipelines:textpipe:1",
    )
    out = repl.dispatch('invoke textpipe:1 "the cat sat"')
    assert out.startswith("pipeline ->")
    assert target in out


def test_task_still_present(repl):
    assert repl.dispatch("task the cat sat") == "task: succeeded"


def test_run_pipeline_converging_multi_input():
    """A converging DAG: two seeds feed two producers whose outputs a 2-input
    step folds together. This is the shape ConjunctionFinder emits for ARC's
    5-input apply_solution — verifies run_pipeline threads it correctly."""
    from mindsos_server.pipeline_runner import run_pipeline

    class _Step:
        def __init__(self, cap, ins, outs):
            self.capacity_iri = cap
            self.input_datastates = ins
            self.output_datastates = outs

    class _Pipe:
        steps = (
            _Step("s1", ("a",), ("x",)),
            _Step("s2", ("b",), ("y",)),
            _Step("join", ("x", "y"), ("z",)),
        )
        target_datastate = "z"
        start_datastates = ("a", "b")

    class _Res:
        def __init__(self, outs):
            self.success = True
            self.error = None
            self.outputs = outs
            self.needs_input = None

    class _Disp:
        def dispatch(self, cap, inputs):
            if cap == "s1":
                return _Res({"x": inputs["a"] + "X"})
            if cap == "s2":
                return _Res({"y": inputs["b"] + "Y"})
            return _Res({"z": inputs["x"] + inputs["y"]})

    state, err = run_pipeline(_Disp(), _Pipe(), {"a": "1", "b": "2"})
    assert err is None
    assert state["z"] == "1X2Y"
