"""SubMindArbiter — preempt-vs-reconcile + unsatisfiable-need policy
(ADR-0189 §2 / §3). Slice 2 of ``feat/subminds``.

This is the "single Mind" arbitration the Slice-1 stub stood in for. When
a SubMind Signal is classified to a tier, the arbiter decides — purely
from **resource contention** (ADR-0189 §1: tier is decoupled from
preemption) — what happens to the resolver:

* **resource free → dispatch now.** The resolver is a *goal*; the finder
  builds a Pipeline to it from currently-available capabilities, and it
  runs as an independent concurrent task (``preempt=False``) holding the
  declared ``resolver_resources``. (This is "reconcile" — concurrent, not
  woven into a plan; no plan-injection substrate exists yet.)
* **resource contended → park** the need on the contended resource. If
  the need *outranks* the holder, additionally fire the holder's
  cooperative cancel to hasten release — but the resolver still only
  dispatches once the resource frees (cooperative preempt cannot seize).
  So preempt and defer collapse to *park + conditional cancel*; both
  **resume event-driven** when the ledger releases the resource.

Unsatisfiable need (ADR-0189 §3): **tier never decays**; the cap is on
**retry activity only** (backoff + a standing-pressure attempt cap);
**never auto-give-up** — a parked need persists (visible) until the vital
recovers (``clear``), the resolver resolves it, or a human dismisses it.

Goal-unreachable is **not** a failure — it is an honest *dont-know* ("no
capability reaches the goal"). The arbiter catches the finder's
not-found signal and fires the SubMind's ``fallback_resolver`` (a direct
ask-human capacity), so there is always a resolution path. (Replacing the
finder's ``PipelineNotFoundError`` with a path-finding dont-know verdict
is a separate core-mod chat — see STATE ``pipelinenotfound-to-dontknow``;
the arbiter swaps its ``except`` for a verdict read when that lands.)

All injected dependencies are duck-typed so the policy is unit-testable
without threads, a real executor, a finder, or FalkorDB.
"""

from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, FrozenSet, Optional

from mindsos_capacity.tiers import DEFAULT_HYSTERESIS, TierEnum

from .cancellation import CancelToken
from .mm import MentalModel
from .pipeline_execution import execute_pipeline as _default_execute_pipeline


@dataclass
class _PendingNeed:
    """One SubMind's outstanding need (keyed by ``submind_name`` — dedup;
    an escalation updates this in place, never stacks)."""

    submind_name: str
    signal: Any
    definition: Any
    tier: TierEnum
    blocked_on: FrozenSet[str] = frozenset()
    attempts: int = 0
    running_task_id: Optional[str] = None
    timer: Any = None


class SubMindArbiter:
    def __init__(
        self,
        executor: Any,
        dispatcher: Any,
        ledger: Any,
        *,
        mm: MentalModel,
        plan_fn: Callable[[Optional[str], str], Any],
        pipeline_not_found: type = Exception,
        execute_pipeline: Callable[..., Any] = _default_execute_pipeline,
        cancel_token_factory: Callable[[], Any] = CancelToken,
        timer_factory: Optional[Callable[[float, Callable[[], None]], Any]] = None,
        hysteresis: int = DEFAULT_HYSTERESIS,
        max_attempts: int = 6,
        base_backoff_s: float = 0.5,
        max_backoff_s: float = 30.0,
    ) -> None:
        self._executor = executor
        self._dispatcher = dispatcher
        self._ledger = ledger
        # D-B (CR: capacity_mm persist §2.5): the REAL MentalModel the solve
        # path threads, injected directly (NOT the dispatcher's mm_handle). The
        # resolver grounds + persists its run into it. Mandatory: a None mm
        # would silently drop grounding via execute_pipeline's mm=None path.
        if mm is None:
            raise ValueError(
                "SubMindArbiter requires a real MentalModel (`mm`): the resolver "
                "grounds its run into the injected MM (D-B, "
                "CORE_CR_CAPACITY_MM_PERSIST_AND_SUBMIND §2.5); a None mm would "
                "silently drop grounding."
            )
        self._mm = mm
        self._plan_fn = plan_fn
        self._pnf = pipeline_not_found
        self._execute_pipeline = execute_pipeline
        self._token_factory = cancel_token_factory
        self._timer_factory = timer_factory or (
            lambda interval, fn: threading.Timer(interval, fn)
        )
        self._hysteresis = hysteresis
        self._max_attempts = max_attempts
        self._base_backoff = base_backoff_s
        self._max_backoff = max_backoff_s

        self._pending: Dict[str, _PendingNeed] = {}
        self._lock = threading.RLock()
        self._seq = itertools.count()
        # Test/inspection visibility (not load-bearing).
        self.dispatched: list = []
        self.parked: list = []
        self.dont_knows: list = []

    # ── ledger wiring ─────────────────────────────────────────────────

    def install_on_ledger(self) -> None:
        """Register the resume hook so a released resource wakes parked
        needs blocked on it (event-driven resume, ADR-0189 §3)."""
        self._ledger.set_on_release(self._on_release)

    # ── public seam (called by SubMindRegistry on a classified Signal) ─

    def on_need(self, signal: Any, tier: TierEnum, definition: Any) -> None:
        name = signal.submind_name
        resources = frozenset(getattr(definition, "resolver_resources", ()) or ())
        with self._lock:
            need = self._pending.get(name)
            if need is None:
                need = _PendingNeed(name, signal, definition, tier)
                self._pending[name] = need
            else:
                # Escalation/re-emit: update in place (dedup, ADR-0188 §4).
                need.signal, need.tier, need.definition = signal, tier, definition
            self._evaluate_locked(need, resources)

    def clear(self, submind_name: str) -> None:
        """Drop a need because the vital recovered (the registry detects
        the SubMind's FIRED→ARMED transition). Cancels any pending retry
        timer and any in-flight resolver."""
        with self._lock:
            need = self._pending.pop(submind_name, None)
            if need is None:
                return
            self._cancel_timer(need)
            self._cancel_inflight(need)

    def stop(self) -> None:
        with self._lock:
            for need in self._pending.values():
                self._cancel_timer(need)
            self._pending.clear()

    # ── core decision (lock held) ────────────────────────────────────

    def _evaluate_locked(self, need: _PendingNeed, resources: FrozenSet[str]) -> None:
        if need.running_task_id is not None:
            # A resolver is already in flight for this need; an escalation
            # while in-flight does not stack a second dispatch.
            return
        contention = self._ledger.contention(resources)
        # A conflict that is THIS need's own running resolver is not a
        # rival — but running_task_id is None here, so any conflict is
        # external. (Self-contention only matters if we ever dispatch
        # while still holding; guarded by the running_task_id check.)
        conflicts = contention.conflicts
        if not conflicts:
            need.blocked_on = frozenset()
            self._dispatch_locked(need, resources)
            return
        # Contended: park, and cooperatively cancel holders we outrank.
        need.blocked_on = resources
        self.parked.append((need.submind_name, tuple(h.task_id for h in conflicts)))
        for hold in conflicts:
            if self._outranks(need, hold) and hold.cancel is not None:
                hold.cancel()

    def _dispatch_locked(self, need: _PendingNeed, resources: FrozenSet[str]) -> None:
        task_id = f"submind-resolver-{need.submind_name}-{next(self._seq)}"
        token = self._token_factory()
        need.running_task_id = task_id
        definition, signal, tier = need.definition, need.signal, need.tier
        score = int(getattr(signal, "attention_score", 0))

        def _resolver() -> dict:
            return self._run_resolver(definition, signal, token, task_id)

        self.dispatched.append((need.submind_name, task_id))
        fut = self._executor.submit(
            _resolver,
            tier=tier,
            task_id=task_id,
            score=score,
            cancel_token=token,
            preempt=False,
            held_resources=resources,
        )
        add_done = getattr(fut, "add_done_callback", None)
        if callable(add_done):
            add_done(lambda f: self._on_resolver_done(need.submind_name, f))

    # ── resolver body (runs on an executor worker) ────────────────────

    def _run_resolver(
        self, definition: Any, signal: Any, token: Any, task_id: str
    ) -> dict:
        start = getattr(definition, "resolver_start_datastate", None)
        goal = getattr(definition, "resolver_goal_datastate", None)
        pipeline = None
        if goal is not None:
            try:
                pipeline = self._plan_fn(start, goal)
            except self._pnf:
                pipeline = None  # goal unreachable → dont-know (below)
        if pipeline is None:
            return self._fire_fallback(definition, signal, task_id)
        init = {start: signal.reading} if start is not None else {}
        # D-B: ground + persist this resolver run into the injected MM. Slice A
        # made `pipeline_run_ref` mandatory whenever `mm` is supplied (it killed
        # the `run_ref = task_id` default that collided on replan), so mint a
        # fresh per-run ref from this dispatch's unique `task_id` — each resolver
        # dispatch (incl. a replan re-dispatch) is its own run and gets its own
        # per-run grounding graph, so runs never overwrite each other.
        result = self._execute_pipeline(
            self._dispatcher,
            pipeline,
            init,
            task_id=task_id,
            cancel_token=token,
            mm=self._mm,
            pipeline_run_ref=f"pipelinerun:{task_id}",
        )
        return {
            "resolved": bool(getattr(result, "success", False)),
            "cancelled": bool(getattr(result, "cancelled", False)),
        }

    def _fire_fallback(self, definition: Any, signal: Any, task_id: str) -> dict:
        """Goal unreachable → honest dont-know. Fire the declared direct
        ask-human fallback (a 1-step terminator — no recursive planning),
        so the need is escalated, not silently dropped."""
        self.dont_knows.append(signal.submind_name)
        fallback = getattr(definition, "fallback_resolver", None)
        if not fallback:
            return {"resolved": False, "dont_know": True, "fallback": False}
        res = self._dispatcher.dispatch(
            fallback, {}, task_id=f"{task_id}-fallback"
        )
        return {
            "resolved": bool(getattr(res, "success", False)),
            "dont_know": True,
            "fallback": True,
        }

    # ── completion + backoff (standing pressure) ──────────────────────

    def _on_resolver_done(self, submind_name: str, fut: Any) -> None:
        with self._lock:
            need = self._pending.get(submind_name)
            if need is None:
                return  # cleared (vital recovered) while in flight
            need.running_task_id = None
            exc = None
            outcome: dict = {}
            try:
                exc = fut.exception()
                if exc is None:
                    outcome = fut.result() or {}
            except Exception:  # noqa: BLE001 — cancelled future, etc.
                exc = exc or RuntimeError("resolver future not readable")

            if exc is None and outcome.get("cancelled"):
                # Preempted mid-run: re-park, await resource release. No
                # backoff (this is contention, not failure).
                need.blocked_on = frozenset(
                    getattr(need.definition, "resolver_resources", ()) or ()
                )
                return
            if exc is None and outcome.get("resolved"):
                # Serviced (resolver ran / human escalated). Keep the need
                # parked + visible until the vital recovers (clear()); no
                # retry. Tier never decays.
                need.blocked_on = frozenset()
                return
            # Ran and failed (or means-unavailable with no fallback) →
            # backoff retry, capped. Never auto-give-up: past the cap the
            # need stays parked + visible, just no longer auto-retries.
            self._schedule_backoff_locked(need)

    def _schedule_backoff_locked(self, need: _PendingNeed) -> None:
        need.attempts += 1
        if need.attempts > self._max_attempts:
            return  # standing-pressure cap reached — park, stay visible
        interval = min(
            self._max_backoff, self._base_backoff * (2 ** (need.attempts - 1))
        )
        timer = self._timer_factory(interval, lambda: self._retry(need.submind_name))
        need.timer = timer
        start = getattr(timer, "start", None)
        if callable(start):
            start()

    def _retry(self, submind_name: str) -> None:
        with self._lock:
            need = self._pending.get(submind_name)
            if need is None or need.running_task_id is not None:
                return
            need.timer = None
            resources = frozenset(
                getattr(need.definition, "resolver_resources", ()) or ()
            )
            self._evaluate_locked(need, resources)

    # ── event-driven resume on resource release ───────────────────────

    def _on_release(self, freed: FrozenSet[str], task_id: str) -> None:
        with self._lock:
            # Most-urgent parked need first (lower tier int, higher score).
            candidates = [
                n
                for n in self._pending.values()
                if n.running_task_id is None and (n.blocked_on & freed)
            ]
            candidates.sort(
                key=lambda n: (int(n.tier), -int(getattr(n.signal, "attention_score", 0)))
            )
            for need in candidates:
                if need.running_task_id is not None:
                    continue
                resources = frozenset(
                    getattr(need.definition, "resolver_resources", ()) or ()
                )
                self._evaluate_locked(need, resources)

    # ── helpers ───────────────────────────────────────────────────────

    def _outranks(self, need: _PendingNeed, hold: Any) -> bool:
        need_tier = int(need.tier)
        need_score = int(getattr(need.signal, "attention_score", 0))
        if need_tier < hold.tier:
            return True
        return need_tier == hold.tier and need_score > hold.score + self._hysteresis

    def _cancel_timer(self, need: _PendingNeed) -> None:
        timer = need.timer
        need.timer = None
        cancel = getattr(timer, "cancel", None)
        if callable(cancel):
            cancel()

    def _cancel_inflight(self, need: _PendingNeed) -> None:
        # Cooperatively cancel an in-flight resolver via its ledger hold
        # (the executor wired the hold's cancel to the task's token).
        task_id = need.running_task_id
        if task_id is None:
            return
        for r in getattr(need.definition, "resolver_resources", ()) or ():
            hold = self._ledger.holder_of(r)
            if hold is not None and hold.task_id == task_id and hold.cancel:
                hold.cancel()
                break
        need.running_task_id = None


__all__ = ["SubMindArbiter"]
