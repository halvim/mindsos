"""SubMind (Mindlet) runtime — the autonomous, no-reasoning reflex (ADR-0188).

Slice 1 of ``feat/subminds``. A :class:`SubMind` owns a minimal control
loop — **sense → compare to threshold → emit** — and never deliberates
(the reflex/deliberation split, ADR-0188 §1). It is *driven* by the L4
:class:`~mindsos_intelligence.submind_scheduler.SubMindScheduler` (one
thread, timer-heap) and *managed* by the per-session
:class:`~mindsos_intelligence.submind_registry.SubMindRegistry`.

This module is the **pure, threadless core**: :meth:`SubMind.tick`
invokes the check-capacity, computes physical severity + cadence
proximity, runs the storm-suppression state machine, and *returns* a
:class:`SubMindSignal` (or ``None``) — it performs no I/O and starts no
threads, so cadence + storm behavior are unit-testable without timing.

Slice boundary (per the design log + chat pushbacks):

* **Signal path only.** ``tick`` emits a Signal; the registry routes it
  through the shipped signal-triage worker onto the
  ``PriorityTierExecutor`` heap with a *stub* resolver. Real resolver
  dispatch + preempt/reconcile arrive in Slice 2 (the resource model).
* **Reflex deferred.** The declared-predicate Reflex bypass + arbiter
  seizure is Slice 3.
* ``resolver_resources`` rides on the definition (ADR-0189 §2) but is
  **unconsumed** here (consumer-discipline pattern).

Severity/tier/score ownership (ADR-0189 §1):

* **severity** — physical, ``0–1`` over ``[threshold → failure]``;
  SubMind-owned.
* **tier** — fixed monotonic step-function of severity, set at
  endowment; the SubMind never *names* its tier, the mapping does.
* **attention_score** — ``importance_weight × severity``, scaled to the
  shipped integer heap key ``[0, ATTENTION_SCORE_MAX]`` (the heap key is
  ``int``; severity is a float fraction).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, Tuple

from mindsos_capacity.tiers import ATTENTION_SCORE_MAX, TierEnum


# ── State + activation enums ───────────────────────────────────────────


class SubMindState(str, Enum):
    """Storm-suppression state (ADR-0188 §4)."""

    ARMED = "armed"   # watching; a threshold crossing emits once → FIRED
    FIRED = "fired"   # silent below threshold; re-emits only on worsening step


class ActivationState(str, Enum):
    """L4-owned activation (ADR-0188 §6 / ADR-0189 §4)."""

    ACTIVE = "active"     # normal adaptive cadence
    FLOORED = "floored"   # "deactivated" → slow floor cadence (bounded blindness)
    OFF = "off"           # not ticked at all


class VitalDirection(str, Enum):
    """Which way the raw reading moves toward distress."""

    HIGH_BAD = "high_bad"   # higher reading = worse (temperature, load)
    LOW_BAD = "low_bad"     # lower reading = worse (battery, water level)


# ── Emitted output ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class SubMindSignal:
    """A SubMind's normal output (ADR-0188 §3). Carries the SubMind-computed
    ``tier`` so the shipped passthrough triage classifier forwards it
    unchanged (the per-SubMind mapping is the tier authority, not the L3
    ``decision.signal_to_tier`` classifier — ADR-0189 §1)."""

    submind_name: str
    severity: float
    tier: TierEnum
    attention_score: int
    kind: str  # "signal" (first crossing) | "escalation" (worsening step)
    reading: float


# ── Cadence law (ADR-0188 §4) ──────────────────────────────────────────


@dataclass(frozen=True)
class CadenceLaw:
    """Proximity→interval control law with bounds + floor.

    ``interval = max - proximity·(max - min)`` — rare when safe
    (proximity 0 → ``max_interval``), frequent near threshold
    (proximity 1 → ``min_interval``). ``floor_interval`` is the slow
    cadence used while FLOORED (ADR-0188 §6). Anti-thrash hysteresis is
    applied to *tier-band* selection (continuous interval cannot flap),
    see :meth:`SubMind.tier_for`.
    """

    min_interval: float
    max_interval: float
    floor_interval: float

    def __post_init__(self) -> None:
        if not (0 < self.min_interval <= self.max_interval):
            raise ValueError(
                f"cadence requires 0 < min_interval ({self.min_interval}) "
                f"<= max_interval ({self.max_interval})"
            )
        if self.floor_interval < self.max_interval:
            raise ValueError(
                f"floor_interval ({self.floor_interval}) must be >= "
                f"max_interval ({self.max_interval}) — the floor is the "
                f"slowest cadence (ADR-0188 §6)"
            )

    def interval_for(self, proximity: float, *, floored: bool) -> float:
        if floored:
            return self.floor_interval
        p = _clamp01(proximity)
        return self.max_interval - p * (self.max_interval - self.min_interval)


# ── Definition (runtime mirror of the L2 record) ───────────────────────


@dataclass
class SubMindDefinition:
    """Runtime mirror of the L2 ``subminds`` definition record (ADR-0190 §1).

    Slice 1 receives ``check`` as an injected callable returning the
    vital's current raw reading; later slices resolve it from the L3
    check-capacity ref. ``severity_tier_bands`` is the fixed monotonic
    step-function (ascending severity floors → non-increasing TierEnum
    int, i.e. more severe ⇒ more urgent), validated at construction.
    """

    name: str
    check: Callable[[], float]
    direction: VitalDirection
    safe: float        # reading at which cadence proximity = 0 (far from threshold)
    threshold: float   # severity = 0 boundary / proximity = 1 boundary
    failure: float     # severity = 1 boundary
    severity_tier_bands: Tuple[Tuple[float, TierEnum], ...]
    importance_weight: int
    cadence: CadenceLaw
    activation_class: str = "always_on"
    tier_hysteresis: float = 0.0       # severity margin to flip tier band
    reset_margin: float = 0.0          # severity recovery margin to re-ARM
    # ── resolver (ADR-0189 §2; consumed by submind_arbiter in Slice 2) ──
    # The resolver is a GOAL, not a fixed capacity: the need is satisfied
    # by a pipeline the finder builds at dispatch from whatever
    # capabilities the system currently has (charger vs battery-swap).
    # ``resolver_goal_datastate`` is the target the pipeline must reach
    # ("energy sufficient"); ``resolver_start_datastate`` seeds the
    # search. ``resolver_resources`` are the exclusive resources the
    # resolver needs (static, for the contention check — the chosen
    # pipeline may use a subset). ``fallback_resolver`` is a DIRECT
    # ask-human capacity (a 1-step terminator, no recursive planning)
    # fired when the goal is unreachable (a dont-know), so there is
    # always a resolution path (ADR-0189 §3 — never auto-give-up).
    resolver_resources: Tuple[str, ...] = field(default_factory=tuple)
    resolver_start_datastate: Optional[str] = None
    resolver_goal_datastate: Optional[str] = None
    fallback_resolver: Optional[str] = None

    def __post_init__(self) -> None:
        if not (0 <= self.importance_weight <= ATTENTION_SCORE_MAX):
            raise ValueError(
                f"importance_weight must be in [0, {ATTENTION_SCORE_MAX}]; "
                f"got {self.importance_weight}"
            )
        if not self.severity_tier_bands:
            raise ValueError("severity_tier_bands must be non-empty")
        floors = [f for f, _ in self.severity_tier_bands]
        if floors != sorted(floors):
            raise ValueError(
                "severity_tier_bands floors must be ascending; got "
                f"{floors}"
            )
        tier_ints = [int(t) for _, t in self.severity_tier_bands]
        if any(b > a for a, b in zip(tier_ints, tier_ints[1:])):
            # Higher severity must map to an equal-or-more-urgent tier.
            # TierEnum is IntEnum with CRITICAL=0 lowest, so more urgent =
            # smaller int → the sequence must be non-increasing.
            raise ValueError(
                "severity_tier_bands must be monotonic: higher severity "
                f"⇒ more urgent (non-increasing TierEnum int); got {tier_ints}"
            )


# ── Runtime ────────────────────────────────────────────────────────────


class SubMind:
    """A single endowed SubMind: definition + mutable sense-loop state.

    Pure core — :meth:`tick` does the work and returns a Signal or
    ``None``; threads + emission live in the scheduler/registry.
    """

    def __init__(
        self,
        definition: SubMindDefinition,
        *,
        activation: ActivationState = ActivationState.ACTIVE,
    ) -> None:
        self.definition = definition
        self.activation = activation
        self._state = SubMindState.ARMED
        self._last_emitted_tier: Optional[TierEnum] = None
        self._last_reading: Optional[float] = None
        self._last_severity: float = 0.0

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def state(self) -> SubMindState:
        return self._state

    # ── physical quantities ────────────────────────────────────────────

    def severity_of(self, reading: float) -> float:
        """Physical severity ``0–1`` over ``[threshold → failure]`` (clamped;
        readings on the safe side of threshold yield 0)."""
        d = self.definition
        span = d.failure - d.threshold
        if span == 0:
            return 1.0 if self._past_threshold(reading) else 0.0
        if d.direction is VitalDirection.HIGH_BAD:
            return _clamp01((reading - d.threshold) / span)
        return _clamp01((d.threshold - reading) / (d.threshold - d.failure))

    def proximity_of(self, reading: float) -> float:
        """Cadence proximity ``0–1`` over ``[safe → threshold]`` (clamped;
        at/over threshold ⇒ 1.0 = fastest cadence)."""
        d = self.definition
        span = d.threshold - d.safe
        if span == 0:
            return 1.0
        if d.direction is VitalDirection.HIGH_BAD:
            return _clamp01((reading - d.safe) / span)
        return _clamp01((d.safe - reading) / (d.safe - d.threshold))

    def _past_threshold(self, reading: float) -> bool:
        d = self.definition
        if d.direction is VitalDirection.HIGH_BAD:
            return reading >= d.threshold
        return reading <= d.threshold

    # ── tier + score (ADR-0189 §1) ─────────────────────────────────────

    def tier_for(self, severity: float) -> TierEnum:
        """Map severity → tier via the fixed monotonic step-function, with
        anti-thrash hysteresis on band edges: an *escalation* (toward a
        more-urgent tier) takes effect immediately; relaxing back requires
        clearing the previous band floor by ``tier_hysteresis`` so a value
        hovering on an edge does not flap."""
        bands = self.definition.severity_tier_bands
        # Pick the most-urgent band whose floor ≤ severity.
        chosen = bands[0][1]
        chosen_floor = bands[0][0]
        for floor, tier in bands:
            if severity >= floor:
                chosen, chosen_floor = tier, floor
            else:
                break
        h = self.definition.tier_hysteresis
        if h > 0 and self._last_emitted_tier is not None:
            # If the new band is *less* urgent than last (int greater) but
            # severity is still within the hysteresis margin above the
            # chosen band's floor, stick with the last (more-urgent) tier.
            if int(chosen) > int(self._last_emitted_tier):
                if severity < chosen_floor + h:
                    return self._last_emitted_tier
        return chosen

    def attention_score(self, severity: float) -> int:
        """``importance_weight × severity`` scaled to the integer heap key."""
        raw = round(self.definition.importance_weight * severity)
        return max(0, min(ATTENTION_SCORE_MAX, int(raw)))

    # ── sense loop ──────────────────────────────────────────────────────

    def next_interval(self) -> float:
        """Adaptive cadence for the *current* reading (or floor when FLOORED)."""
        reading = self._last_reading
        proximity = 0.0 if reading is None else self.proximity_of(reading)
        # FLOORED and OFF both ride the slow floor cadence so a deactivated
        # SubMind never consumes the fast adaptive budget (ADR-0188 §6).
        floored = self.activation in (ActivationState.FLOORED, ActivationState.OFF)
        return self.definition.cadence.interval_for(proximity, floored=floored)

    def tick(self) -> Optional[SubMindSignal]:
        """One sense cycle: read the vital, update state, maybe emit.

        Returns a :class:`SubMindSignal` to emit, or ``None``. Never
        raises on a normal reading; a failing check-capacity is the
        caller's concern (the scheduler isolates it like the dream timer).
        """
        if self.activation is ActivationState.OFF:
            return None
        reading = float(self.definition.check())
        self._last_reading = reading
        severity = self.severity_of(reading)
        self._last_severity = severity
        past = self._past_threshold(reading)

        if self._state is SubMindState.ARMED:
            if past:
                return self._emit(reading, severity, kind="signal")
            return None

        # FIRED — silent unless we recover (re-ARM) or worsen past a step.
        if not past:
            # Re-arm once recovered past the reset margin (in severity units
            # on the safe side ⇒ severity is already 0; require the reading
            # to clear threshold by the margin).
            if self._recovered(reading):
                self._state = SubMindState.ARMED
                self._last_emitted_tier = None
            return None

        new_tier = self.tier_for(severity)
        if (
            self._last_emitted_tier is not None
            and int(new_tier) < int(self._last_emitted_tier)
        ):
            # Worsened into a strictly more-urgent tier ⇒ escalation.
            return self._emit(reading, severity, kind="escalation")
        return None

    def _emit(self, reading: float, severity: float, *, kind: str) -> SubMindSignal:
        tier = self.tier_for(severity)
        self._state = SubMindState.FIRED
        self._last_emitted_tier = tier
        return SubMindSignal(
            submind_name=self.name,
            severity=severity,
            tier=tier,
            attention_score=self.attention_score(severity),
            kind=kind,
            reading=reading,
        )

    def _recovered(self, reading: float) -> bool:
        """Has the reading cleared the threshold by ``reset_margin`` (in the
        same normalized severity units), so the SubMind may re-ARM?"""
        d = self.definition
        margin = d.reset_margin
        if margin <= 0:
            return True
        span = abs(d.failure - d.threshold) or 1.0
        if d.direction is VitalDirection.HIGH_BAD:
            return reading <= d.threshold - margin * span
        return reading >= d.threshold + margin * span


# ── helpers ────────────────────────────────────────────────────────────


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


__all__ = [
    "SubMind",
    "SubMindDefinition",
    "SubMindSignal",
    "SubMindState",
    "ActivationState",
    "VitalDirection",
    "CadenceLaw",
]
