"""feat/subminds Slice 2 — SubMindArbiter policy (ADR-0189 §2/§3).

Pure unit tests with injected fakes (synchronous executor, fake
dispatcher/finder/timer) — no threads, no FalkorDB; Py3.10 sandbox.

Covers: reconcile-on-free, park-on-contention + cooperative cancel,
event-driven resume on release, goal-unreachable → dont-know → ask-human
fallback, runs-and-fails backoff + standing-pressure cap, escalation
dedup while in-flight, recovery clear.
"""

from __future__ import annotations

from mindsos_capacity.tiers import TierEnum
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.resources import ResourceLedger
from mindsos_intelligence.submind_arbiter import SubMindArbiter


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

    def __init__(self):
        self.submitted = []

    def submit(
        self, fn, *, tier, request_id, score=None, cancel_token=None,
        preempt=True, held_resources=(),
    ):
        self.submitted.append(
            dict(request_id=request_id, tier=tier, preempt=preempt,
                 held=frozenset(held_resources))
        )
        try:
            return _Fut(ret=fn())
        except BaseException as exc:  # noqa: BLE001
            return _Fut(exc=exc)


class _Inv:
    def __init__(self, success=True):
        self.success, self.outputs, self.error = success, {}, None


class _Dispatcher:
    def __init__(self, success=True):
        self.calls = []
        self._success = success

    def dispatch(self, cap, inputs, *, cancel_token=None, request_id=None, step_id=None):
        self.calls.append(cap)
        return _Inv(success=self._success)


class _Pipeline:
    def __init__(self, steps=()):
        self.steps = steps


class _Step:
    def __init__(self, cap):
        self.capacity_iri = cap
        self.input_datastates = ()
        self.output_datastates = ()


class PNF(Exception):
    pass


class _Sig:
    def __init__(self, name, tier, score, reading=0.0):
        self.submind_name = name
        self.tier = tier
        self.attention_score = score
        self.reading = reading
        self.severity = 0.5
        self.kind = "signal"


class _Defn:
    def __init__(self, res=(), goal="goal", start=None, fb=None):
        self.resolver_resources = res
        self.resolver_goal_datastate = goal
        self.resolver_start_datastate = start
        self.fallback_resolver = fb


def _ok_plan(s, g):
    return _Pipeline(steps=(_Step("cap.charge"),))


def _arb(executor, dispatcher, ledger, plan=_ok_plan, mm=None, **kw):
    # Slice C: `mm` is now mandatory on the arbiter (D-B). These policy tests
    # don't inspect grounding, so a real (empty) MentalModel satisfies the
    # contract; the resolver path writes into it harmlessly where it runs.
    if mm is None:
        mm = MentalModel(session_id="s", user_id="u")
    a = SubMindArbiter(executor, dispatcher, ledger, mm=mm, plan_fn=plan,
                       pipeline_not_found=PNF, **kw)
    a.install_on_ledger()
    return a


# ── tests ─────────────────────────────────────────────────────────────


def test_free_resource_reconciles_concurrent_dispatch():
    led, ex, dp = ResourceLedger(), _Exec(), _Dispatcher()
    a = _arb(ex, dp, led)
    a.on_need(_Sig("energy", TierEnum.FOREGROUND, 100), TierEnum.FOREGROUND,
              _Defn(res=("arm",)))
    assert ex.submitted and ex.submitted[0]["preempt"] is False
    assert ex.submitted[0]["held"] == {"arm"}
    assert "cap.charge" in dp.calls  # pipeline actually executed


def test_contended_parks_and_cancels_outranked_holder():
    led, ex, dp = ResourceLedger(), _Exec(), _Dispatcher()
    cancelled = {"hit": False}
    led.acquire("holder", frozenset({"arm"}), tier=int(TierEnum.BACKGROUND),
                score=10, cancel=lambda: cancelled.__setitem__("hit", True))
    a = _arb(ex, dp, led)
    a.on_need(_Sig("energy", TierEnum.CRITICAL, 9000), TierEnum.CRITICAL,
              _Defn(res=("arm",)))
    assert not ex.submitted          # parked, not dispatched
    assert cancelled["hit"]          # outranked holder cooperatively cancelled


def test_contended_does_not_cancel_when_not_outranked():
    led, ex, dp = ResourceLedger(), _Exec(), _Dispatcher()
    cancelled = {"hit": False}
    led.acquire("holder", frozenset({"arm"}), tier=int(TierEnum.CRITICAL),
                score=9999, cancel=lambda: cancelled.__setitem__("hit", True))
    a = _arb(ex, dp, led)
    a.on_need(_Sig("energy", TierEnum.BACKGROUND, 1), TierEnum.BACKGROUND,
              _Defn(res=("arm",)))
    assert not ex.submitted and not cancelled["hit"]  # defer, no cancel


def test_event_driven_resume_on_release():
    led, ex, dp = ResourceLedger(), _Exec(), _Dispatcher()
    led.acquire("holder", frozenset({"arm"}), tier=int(TierEnum.BACKGROUND), score=10)
    a = _arb(ex, dp, led)
    a.on_need(_Sig("energy", TierEnum.CRITICAL, 9000), TierEnum.CRITICAL,
              _Defn(res=("arm",)))
    assert not ex.submitted
    led.release("holder")            # resource frees → parked need resumes
    assert ex.submitted and ex.submitted[0]["held"] == {"arm"}


def test_unreachable_goal_fires_dont_know_fallback():
    led, ex, dp = ResourceLedger(), _Exec(), _Dispatcher()

    def fail_plan(s, g):
        raise PNF("no capacity reaches the goal")

    a = _arb(ex, dp, led, plan=fail_plan)
    a.on_need(_Sig("energy", TierEnum.CRITICAL, 9000), TierEnum.CRITICAL,
              _Defn(res=(), fb="cap.ask_human"))
    assert "cap.ask_human" in dp.calls
    assert "energy" in a.dont_knows


def test_runs_and_fails_schedules_capped_backoff():
    led, dp = ResourceLedger(), _Dispatcher()
    intervals = []

    class _Timer:
        def __init__(self, interval, fn):
            self.interval = interval

        def start(self):
            intervals.append(self.interval)

        def cancel(self):
            pass

    class _FailExec:
        def submit(self, fn, *, tier, request_id, score=None, cancel_token=None,
                   preempt=True, held_resources=()):
            return _Fut(ret={"resolved": False})  # ran and failed

    a = _arb(_FailExec(), dp, led, timer_factory=lambda i, f: _Timer(i, f),
             base_backoff_s=1.0, max_attempts=3)
    a.on_need(_Sig("energy", TierEnum.FOREGROUND, 100), TierEnum.FOREGROUND, _Defn())
    # one backoff scheduled after the first failed attempt
    assert intervals == [1.0]
    # drive retries to the cap; past max_attempts no further timer is scheduled
    a._retry("energy")
    a._retry("energy")
    a._retry("energy")
    assert len(intervals) <= 3  # capped (standing pressure), need stays parked


def test_escalation_while_in_flight_does_not_double_dispatch():
    led, dp = ResourceLedger(), _Dispatcher()
    # An executor that holds the resolver "running" (does not run inline).
    class _HoldExec:
        def __init__(self):
            self.count = 0

        def submit(self, fn, *, tier, request_id, score=None, cancel_token=None,
                   preempt=True, held_resources=()):
            self.count += 1
            return _Fut(ret=None)  # callback fires but we inspect count

    ex = _HoldExec()
    a = _arb(ex, dp, led)
    # Force in-flight by stubbing the done-callback to not clear running.
    # Simpler: call on_need twice; the resolver runs inline (ret None →
    # not resolved → backoff), so simulate in-flight via a never-finishing
    # future is overkill. Instead assert dedup: second identical need with
    # an active running_request_id is a no-op.
    need_defn = _Defn(res=("arm",))
    a.on_need(_Sig("energy", TierEnum.FOREGROUND, 100), TierEnum.FOREGROUND, need_defn)
    first = ex.count
    # Manually mark in-flight to exercise the early-return guard.
    a._pending["energy"].running_request_id = "still-running"
    a.on_need(_Sig("energy", TierEnum.CRITICAL, 9000), TierEnum.CRITICAL, need_defn)
    assert ex.count == first  # no second dispatch while in flight
    # but the escalated tier was recorded in place (dedup, not stacked)
    assert a._pending["energy"].tier is TierEnum.CRITICAL


def test_clear_drops_parked_need():
    led, ex, dp = ResourceLedger(), _Exec(), _Dispatcher()
    led.acquire("holder", frozenset({"arm"}), tier=int(TierEnum.BACKGROUND), score=10)
    a = _arb(ex, dp, led)
    a.on_need(_Sig("energy", TierEnum.CRITICAL, 9000), TierEnum.CRITICAL,
              _Defn(res=("arm",)))
    assert "energy" in a._pending
    a.clear("energy")                # vital recovered
    assert "energy" not in a._pending
    led.release("holder")            # no resume — the need is gone
    assert not ex.submitted
