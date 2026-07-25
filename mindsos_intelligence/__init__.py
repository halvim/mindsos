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

__version__ = "0.0.0+phase50"

from .cancellation import CancelToken, CancelTokenView
from .executor import PriorityTierExecutor, default_worker_count
from .als_registry import ALSSubsystemRegistration, ALSSubsystemRegistry
from .intelligence_layer import DreamCycleTimer, IntelligenceLayer
from .mm import MentalModel, MMRoot
from .mm_resolver import (
    InstantiatedNode,
    KnowledgeMMSource,
    MMResolver,
    MMSource,
    PinnedRef,
    SourceNode,
)
from .monitor_subscription import MonitorSubscriptionRegistry
from .rwlock import RWLock
from .signal_triage import SignalTriageWorker, passthrough_classifier
from .submind import (
    ActivationState,
    CadenceLaw,
    SubMind,
    SubMindDefinition,
    SubMindSignal,
    SubMindState,
    VitalDirection,
)
from .submind_registry import SubMindRegistry
from .submind_scheduler import SubMindScheduler
from .submind_arbiter import SubMindArbiter
from .resources import Contention, ResourceHold, ResourceLedger
from .pipeline_execution import PipelineExecutionResult, execute_pipeline
from mindsos_capacity.needs_input import NeedsInput
from .dispatch import L4Dispatcher
from .chain_artifacts import ChainArtifactWriter
from .ingress import InputEnvelope
from .phase1_profile import Phase1Profile
from .phase_1 import (
    InterpretationError,
    InterpretationResult,
    interpret,
)
from .orchestrator import LifecyclePhase, Orchestrator, RequestOutcome
from .signal_sources import register_signal_sources
from .als_subsystems import register_als_subsystems

__all__ = [
    "L4Dispatcher",
    "Orchestrator",
    "TaskOutcome",
    "LifecyclePhase",
    "ChainArtifactWriter",
    # ADR-0195 — Phase-1 interpretation seam.
    "Phase1Profile",
    "interpret",
    "InterpretationResult",
    "InterpretationError",
    # ADR-0197 — modality-aware input ingress.
    "InputEnvelope",
    # ADR-0196 — user-clarification verdict (re-exported from L3).
    "NeedsInput",
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
    "KnowledgeMMSource",
    "MonitorSubscriptionRegistry",
    "ALSSubsystemRegistry",
    "ALSSubsystemRegistration",
    "SignalTriageWorker",
    "passthrough_classifier",
    "IntelligenceLayer",
    "DreamCycleTimer",
    # feat/subminds (Slice 1) — SubMind runtime + scheduler + registry.
    "SubMind",
    "SubMindDefinition",
    "SubMindSignal",
    "SubMindState",
    "ActivationState",
    "VitalDirection",
    "CadenceLaw",
    "SubMindScheduler",
    "SubMindRegistry",
    # feat/subminds (Slice 2) — resource model + arbiter + pipeline executor.
    "SubMindArbiter",
    "ResourceLedger",
    "ResourceHold",
    "Contention",
    "PipelineExecutionResult",
    "execute_pipeline",
]
