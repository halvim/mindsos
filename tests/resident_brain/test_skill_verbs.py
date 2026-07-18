"""Unit coverage for skill-declared brain verbs (ADR-0183 §am-3).

Pure tests over ``build_skill_l4_tables`` (the boot-side table builder) and
``BrainREPL``'s verb routing / builtin-shadow / error-handling — no Falkor,
no real capacities. The full end-to-end path is the ``@integration``
companion ``test_skill_verb_durable.py``.
"""
from __future__ import annotations

from types import SimpleNamespace

from mindsos_cli.commands.brain import BrainREPL
from mindsos_intelligence.ingress import InputEnvelope
from mindsos_server.boot import build_skill_l4_tables


def _rec(name, seq, slots):
    return SimpleNamespace(bundle_name=name, seq=seq, value={"l4_slots": slots})


def _slots(verb="arc", modality="datastate:arc.raw_text", **extra):
    base = {
        "verb": verb,
        "modality": modality,
        "process": "capacity:perception:p",
        "hint": "capacity:hint:h",
        "map": "capacity:decision:m",
    }
    base.update(extra)
    return base


# ── build_skill_l4_tables ─────────────────────────────────────────────

def test_happy_builds_both_maps():
    mp, sv, drops = build_skill_l4_tables([_rec("arc1", 1, _slots())], set())
    assert set(sv) == {"arc"}
    assert set(mp) == {"datastate:arc.raw_text"}
    assert mp["datastate:arc.raw_text"].process == "capacity:perception:p"
    assert mp["datastate:arc.raw_text"].map == "capacity:decision:m"
    assert drops == []


def test_skipped_bundle_excluded_and_reported():  # Fix 3 / D-4
    recs = [_rec("arc1", 1, _slots())]
    mp, sv, drops = build_skill_l4_tables(recs, {"arc1"})
    assert sv == {} and mp == {}
    assert drops and drops[0][0] == "arc1"


def test_slot_without_modality_contributes_nothing():  # D-3
    mp, sv, drops = build_skill_l4_tables(
        [_rec("x", 1, {"verb": "x"})], set()
    )
    assert sv == {} and mp == {}


def test_modality_collision_first_wins():  # #5
    recs = [
        _rec("arc1", 1, _slots(verb="a", modality="datastate:arc.raw_text")),
        _rec("arc3", 2, _slots(verb="b", modality="datastate:arc.raw_text")),
    ]
    mp, sv, drops = build_skill_l4_tables(recs, set())
    assert set(sv) == {"a"}
    assert set(mp) == {"datastate:arc.raw_text"}
    assert any(d[0] == "arc3" and "modality" in d[2] for d in drops)


def test_verb_collision_first_wins():  # #8
    recs = [
        _rec("arc1", 1, _slots(verb="arc", modality="datastate:m1")),
        _rec("arc3", 2, _slots(verb="arc", modality="datastate:m2")),
    ]
    mp, sv, drops = build_skill_l4_tables(recs, set())
    assert set(sv) == {"arc"}
    assert mp.get("datastate:m1") is not None and "datastate:m2" not in mp
    assert any(d[0] == "arc3" and "verb" in d[2] for d in drops)


# ── BrainREPL routing / shadow / error handling ───────────────────────

class _RecordingOrch:
    def __init__(self, outcome=None, exc=None):
        self.calls, self._outcome, self._exc = [], outcome, exc

    def run_lifecycle(self, task_input, **kw):
        self.calls.append(task_input)
        if self._exc is not None:
            raise self._exc
        return self._outcome


def _stack(skill_verbs, orch, skipped=()):
    return SimpleNamespace(
        skill_verbs=skill_verbs,
        orch=orch,
        activation=SimpleNamespace(skipped=tuple(skipped)),
    )


def test_builtin_shadows_skill_verb():  # #4/#6/#1
    orch = _RecordingOrch(
        SimpleNamespace(status="succeeded", pending_confirmation=None)
    )
    repl = BrainREPL(_stack({"task": _slots(verb="task")}, orch))
    assert "task" not in repl._skill_verbs and "task" in repl._shadowed
    assert repl.dispatch("task hi") == "task: succeeded"
    assert orch.calls == [{"text": "hi"}]


def test_skill_verb_builds_envelope_and_runs():  # #1
    orch = _RecordingOrch(
        SimpleNamespace(status="succeeded", pending_confirmation=None)
    )
    repl = BrainREPL(_stack({"arc": _slots()}, orch))
    assert repl.dispatch("arc hello world") == "succeeded"
    env = orch.calls[0]
    assert isinstance(env, InputEnvelope)
    assert env.modality == "datastate:arc.raw_text"
    assert env.value == "hello world"


def test_skill_verb_survives_run_lifecycle_raise():  # #2 — no REPL crash
    orch = _RecordingOrch(exc=RuntimeError("unroutable"))
    repl = BrainREPL(_stack({"arc": _slots()}, orch))
    out = repl.dispatch("arc x")
    assert out.startswith("skill error:") and "RuntimeError" in out


def test_pending_confirmation_surfaced_not_swallowed():  # #7
    outcome = SimpleNamespace(
        status="pending_confirmation", pending_confirmation="pick a task id"
    )
    repl = BrainREPL(_stack({"arc": _slots()}, _RecordingOrch(outcome)))
    assert repl.dispatch("arc x") == "needs input: pick a task id"


def test_help_lists_skill_and_skipped():
    repl = BrainREPL(
        _stack({"arc": _slots()}, _RecordingOrch(), skipped=[("bongard", "unresolved")])
    )
    out = repl.dispatch("help")
    assert "arc" in out and "bongard" in out


def test_unknown_verb_still_reported():
    repl = BrainREPL(_stack({}, _RecordingOrch()))
    assert repl.dispatch("frobnicate").startswith("unknown verb")


def test_skill_verb_usage_when_no_args():
    repl = BrainREPL(_stack({"arc": _slots()}, _RecordingOrch()))
    assert repl.dispatch("arc").startswith("usage: arc")
