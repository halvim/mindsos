"""L4 crash recovery — checkpoint markers + L4-startup unconsolidated scan
(ADR-0179; Chat B D-B50).

v1 mechanism = **tombstone marker** (not a live-MM flush). At each D-B50
trigger (LifecyclePhase transition + per-replan) the orchestrator records a
small marker; on ``IntelligenceLayer.start`` the unconsolidated markers are
scanned and each produces a ``crash_marker`` Episode (``outcome_classification
= "failed"``, ``mm_root_ref = None``) — delivering clean startup, a crash
record, and ``task_input_ref`` preservation. Partial-MM **content** recovery
is deferred to v1.5 (ADR-0179 §3).

The marker store is an injectable abstraction. v1 ships ``InMemoryCheckpoint
Store``; a durable Falkor-backed store (so markers survive process death) is
the persister-wiring follow-up — the scan/contract is testable now by leaving
an unconsolidated marker and running :func:`recover_unconsolidated`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mindsos_capacity.builtins.consolidate import DS_MM_COMPOSITE_INSTANCE
from mindsos_knowledge.identifiers import episode_iri

CONSOLIDATE_MM_IRI = "capacity:consolidate:mm"


@dataclass
class CrashInfo:
    """Stamped on a recovered Episode (Chat B §4.3 ``crash_marker``)."""

    last_phase: Optional[str] = None
    last_milestone: Optional[str] = None
    detected_at: str = ""
    recovered: bool = False


@dataclass
class CheckpointMarker:
    request_id: str
    task_input_ref: Optional[str] = None
    task_pattern_iri: Optional[str] = None
    last_phase: Optional[str] = None
    last_milestone: Optional[str] = None
    consolidated: bool = False


class InMemoryCheckpointStore:
    """v1 checkpoint store — keyed by ``task_id`` (upsert; latest trigger wins).

    A durable Falkor-backed store is the persister-wiring follow-up (ADR-0179
    §marker store); this in-memory store makes the scan contract testable.
    """

    def __init__(self) -> None:
        self._markers: Dict[str, CheckpointMarker] = {}

    def record(self, marker: CheckpointMarker) -> None:
        existing = self._markers.get(marker.request_id)
        if existing is not None and existing.consolidated:
            return
        self._markers[marker.request_id] = marker

    def mark_consolidated(self, request_id: str) -> None:
        m = self._markers.get(request_id)
        if m is not None:
            m.consolidated = True

    def iter_unconsolidated(self) -> List[CheckpointMarker]:
        return [m for m in self._markers.values() if not m.consolidated]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_checkpoint(
    store: Any,
    *,
    request_id: str,
    last_phase: Optional[str] = None,
    last_milestone: Optional[str] = None,
    task_input_ref: Optional[str] = None,
    task_pattern_iri: Optional[str] = None,
) -> None:
    """Record/update a checkpoint marker at a D-B50 trigger (no-op if no store)."""
    if store is None:
        return
    store.record(
        CheckpointMarker(
            request_id=request_id,
            task_input_ref=task_input_ref,
            task_pattern_iri=task_pattern_iri,
            last_phase=last_phase,
            last_milestone=last_milestone,
        )
    )


def recover_unconsolidated(store: Any, dispatcher: Any) -> List[str]:
    """L4-startup scan: for each unconsolidated marker, write a ``crash_marker``
    Episode via ``consolidate:mm`` unless one already exists for that task
    (idempotent — ADR-0176 §4). Returns the recovered task_ids. No-op when the
    store or the consolidate capacity / KL is unavailable.
    """
    if store is None:
        return []
    from .consolidation import consolidation_enabled

    if not consolidation_enabled(dispatcher):
        return []
    kl = getattr(dispatcher, "_kl", None)
    session = getattr(dispatcher, "_session", None)
    user_id = getattr(session, "user_id", "user")

    recovered: List[str] = []
    for marker in store.iter_unconsolidated():
        epi_iri = episode_iri("v1", user_id, marker.request_id)
        if kl is not None and kl.read_at_version(epi_iri, 1) is not None:
            store.mark_consolidated(marker.request_id)  # already consolidated
            continue
        crash = CrashInfo(
            last_phase=marker.last_phase,
            last_milestone=marker.last_milestone,
            detected_at=_utc_now_iso(),
            recovered=False,
        )
        record = {
            DS_MM_COMPOSITE_INSTANCE: {
                "episode_id": marker.request_id,
                "value": {
                    "task_input_ref": marker.task_input_ref
                    or f"taskinput:{marker.task_id}",
                    "mm_root_ref": None,
                    "task_pattern_iri": marker.task_pattern_iri,
                    "outcome_classification": "failed",
                    "crash_marker": asdict(crash),
                    "consolidated_at": _utc_now_iso(),
                },
            }
        }
        result = dispatcher.dispatch(CONSOLIDATE_MM_IRI, record, request_id=marker.request_id)
        if result is not None and getattr(result, "success", False):
            store.mark_consolidated(marker.request_id)
            recovered.append(marker.request_id)
    return recovered


__all__ = [
    "CrashInfo",
    "CheckpointMarker",
    "InMemoryCheckpointStore",
    "record_checkpoint",
    "recover_unconsolidated",
]
