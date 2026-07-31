"""10 signal-source registration skeletons (Chat A R3 D9.2 + Chat B D-B51).

The v1 signal catalog: 10 sources (S7 reserved). Phase 47 ships empty
payload contracts; the concrete payload schemas + emitters are unbuilt
CORE work (RULES §8). ``signal.plan_decomposition_outcome`` (S10) was added by
Chat B D-B51 for ALS subsystem #11.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class SignalSourceSkeleton:
    slot: str  # S1..S10
    iri: Optional[str]  # None for the reserved slot
    reserved: bool = False
    payload_contract: Tuple[str, ...] = ()  # empty at v0


SIGNAL_SOURCE_SKELETONS: Tuple[SignalSourceSkeleton, ...] = (
    SignalSourceSkeleton("S1", "signal.self_distillation"),
    SignalSourceSkeleton("S2", "signal.gold_anchor"),
    SignalSourceSkeleton("S3", "signal.fol_disagreement"),
    SignalSourceSkeleton("S4", "signal.ensemble_agreement"),
    SignalSourceSkeleton("S5", "signal.hitl"),
    SignalSourceSkeleton("S6", "signal.task_outcome"),
    SignalSourceSkeleton("S7", None, reserved=True),
    SignalSourceSkeleton("S8", "signal.replan_divergence"),
    SignalSourceSkeleton("S9", "signal.mutation_frequency"),
    SignalSourceSkeleton("S10", "signal.plan_decomposition_outcome"),
)


def register_signal_sources() -> Dict[str, SignalSourceSkeleton]:
    """Return the 10 signal-source skeletons keyed by slot (S1..S10)."""
    return {s.slot: s for s in SIGNAL_SOURCE_SKELETONS}


__all__ = ["SignalSourceSkeleton", "SIGNAL_SOURCE_SKELETONS", "register_signal_sources"]
