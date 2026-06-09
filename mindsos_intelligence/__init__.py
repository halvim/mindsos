"""MindsOS Layer 4 — Intelligence substrate (Phase 46).

The first L4 code: per-session ``IntelligenceLayer`` lifecycle + the
substrate primitives it owns (priority-tier Executor + worker pool,
three-sub-MM container + RWLock, MM resolution/instantiation, cooperative
cancellation, signal-triage thread, ALS subsystem registry, Monitor
subscription registry, dream-cycle timer). L4 = substrate + control flow
only; all decisions/computations are L3 capacities (Chat A R1 strict
line). Built additively atop L1-L3 (imports downward only).
"""

from __future__ import annotations

__version__ = "0.0.0+phase47"

from .cancellation import CancelToken, CancelTokenView
from .executor import PriorityTierExecutor, default_worker_count
from .als_registry import ALSSubsystemRegistration, ALSSubsystemRegistry
from .intelligence_layer import DreamCycleTimer, IntelligenceLayer
from .mm import MentalModel, MMRoot
from .mm_resolver import (
    InstantiatedNode,
    MMResolver,
    MMSource,
    PinnedRef,
    SourceNode,
)
from .monitor_subscription import MonitorSubscriptionRegistry
from .rwlock import RWLock
from .signal_triage import SignalTriageWorker, passthrough_classifier
from .dispatch import L4Dispatcher, required_capability_for
from .chain_artifacts import ChainArtifactWriter
from .orchestrator import LifecyclePhase, Orchestrator, TaskOutcome
from .signal_sources import register_signal_sources
from .als_subsystems import register_als_subsystems

__all__ = [
    "L4Dispatcher",
    "required_capability_for",
    "Orchestrator",
    "TaskOutcome",
    "LifecyclePhase",
    "ChainArtifactWriter",
    "register_signal_sources",
    "register_als_subsystems",
    "CancelToken",
    "CancelTokenView",
    "PriorityTierExecutor",
    "default_worker_count",
    "MentalModel",
    "MMRoot",
    "RWLock",
    "MMResolver",
    "MMSource",
    "SourceNode",
    "InstantiatedNode",
    "PinnedRef",
    "MonitorSubscriptionRegistry",
    "ALSSubsystemRegistry",
    "ALSSubsystemRegistration",
    "SignalTriageWorker",
    "passthrough_classifier",
    "IntelligenceLayer",
    "DreamCycleTimer",
]
