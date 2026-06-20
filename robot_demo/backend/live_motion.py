"""DM-3 — live-motion wrapper (G-7 / PB-F, design log §15).

The PB-F policy in one place, MuJoCo-free (PB-TT) via injected callables:

    cache lookup → HIT: play the cached frames.
                 → MISS: generate (on the generator thread, while the sim
                   holds pose) → run the atomic checklist → PASS: cache +
                   play; FAIL: an **honest motion dont-know** ("can't find a
                   safe motion"), NOT a stall (P-7).

``generate`` / ``play`` / ``checklist`` are injected so the policy is unit-
testable with fakes; the real ones are MuJoCo (the SimEngine, via the
BodyHandle). ``generate`` returns frames or ``None`` (or raises); a checklist
failure or a generation failure both surface as a dont-know.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from .motion_cache import CacheKey, Frames, TrajectoryCache
from .motion_checklist import Verdict

#: ``() -> Frames | None`` — produce a trajectory for this key (heavy IK).
GenerateFn = Callable[[], Optional[Frames]]
#: ``(Frames) -> None`` — stream frames into the stepping sim.
PlayFn = Callable[[Frames], None]
#: ``(Frames) -> Verdict`` — the atomic pre-present checklist.
ChecklistFn = Callable[[Frames], Verdict]


@dataclass(frozen=True)
class MotionOutcome:
    """Result of a live-motion attempt — the ``DS_MOTION_DONE`` payload."""

    ok: bool
    status: str               # "done" | "dont_know"
    reason: str
    cache_hit: bool = False
    frames_n: int = 0
    checks: Dict[str, object] = field(default_factory=dict)

    @classmethod
    def done(cls, frames_n: int, *, cache_hit: bool, checks=None) -> "MotionOutcome":
        return cls(True, "done", "PASS", cache_hit, frames_n, checks or {})

    @classmethod
    def dont_know(cls, reason: str, *, checks=None) -> "MotionOutcome":
        # P-7: a checklist-failing live miss is an honest motion dont-know,
        # not a stall. ok=False, status="dont_know".
        return cls(False, "dont_know", reason, False, 0, checks or {})


def run_motion(
    cache: TrajectoryCache,
    key: CacheKey,
    generate: GenerateFn,
    play: PlayFn,
    checklist: ChecklistFn,
    *,
    allow_live_generation: bool = True,
) -> MotionOutcome:
    """Cache-first live motion (PB-F). See module docstring."""
    cached = cache.get(key)
    if cached is not None:
        play(cached)
        return MotionOutcome.done(len(cached), cache_hit=True)

    if not allow_live_generation:
        return MotionOutcome.dont_know(
            "no cached trajectory and live generation disabled"
        )

    try:
        frames: Optional[Frames] = generate()
    except Exception as exc:  # generation blew up — honest dont-know, no stall
        return MotionOutcome.dont_know(f"motion generation failed: {exc}")
    if not frames:
        return MotionOutcome.dont_know("motion generation produced no trajectory")

    verdict: Verdict = checklist(frames)
    if not verdict.ok:
        return MotionOutcome.dont_know(
            f"unsafe motion (checklist): {verdict.reason}", checks=verdict.checks
        )

    cache.put(key, frames)
    play(frames)
    return MotionOutcome.done(len(frames), cache_hit=False, checks=verdict.checks)


__all__ = [
    "MotionOutcome",
    "GenerateFn",
    "PlayFn",
    "ChecklistFn",
    "run_motion",
]
