"""Perception-family don't-know signal (G8 / ADR-0157 DATASTATE_MARKER).

Grounding/derivation capacities in the ``perception``/``derivation``
families signal don't-know by emitting a **marker** in place of their
declared output (FAMILY_RULES → ``DATASTATE_MARKER``). At runtime that
marker is this :class:`DontKnow` sentinel, carried as the output value;
the **control loop** (not the capacity, not the predicate — G5/G6)
inspects each step's output and converts a ``DontKnow`` into the
verdict: re-segment (once, R=1) or abstain.

``reason`` names the gate that fired so the verification asserts the
moat, not a bare failure:

- ``"fit"``      — best segmentation RMS > τ_fit (curve / edge-decoration).
- ``"structure"``— atoms don't close into a simple polygon.
- ``"trace"``    — the leaf couldn't order a clean boundary at all.
- ``"budget"``   — the dormant safety valve tripped (logged, uninformative).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DontKnow:
    """The perception-family abstain marker (a DATASTATE_MARKER value)."""

    reason: str          # "fit" | "structure" | "trace" | "budget"
    detail: str = ""

    def __bool__(self) -> bool:  # truthy-guard: `if dk:` must not pass
        return False


def is_dont_know(value) -> bool:
    return isinstance(value, DontKnow)
