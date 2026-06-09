"""L4 MM consolidation write path (ADR-0176 §1).

At task completion the orchestrator freezes the live MM (acquires the MM
writer lock), assembles the 6-field D-B47 Episode record from the TaskRun
chain, and dispatches ``capacity:consolidate:mm`` — the L3 write surface
(ADR-0146) that writes the Episode and materialises the Memory composite
(ADR-0176 §3). Retain-by-default on success / failure / abort (Chat B §4.1).

v1 stores ``mm_root_ref`` as a reference to the MM's intelligence sub-graph
identifier; the MM metagraph itself is persisted by the L0 Falkor persister
(Phase 44), so the Episode points at it rather than embedding a deep snapshot
(the heavy full-MM serialization is deferred — consistent with the Phase-48
instrument-now posture). Consolidation is **skipped** in simplified mode and
gracefully skipped when no consolidate capacity / KL is wired (e.g. the v0
orchestrator smoke), per the opt-out-per-task contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from mindsos_capacity.builtins.consolidate import DS_MM_COMPOSITE_INSTANCE

CONSOLIDATE_MM_IRI = "capacity:consolidate:mm"


def consolidation_enabled(dispatcher: Any) -> bool:
    """True iff ``dispatcher`` can perform a consolidation write — the
    ``consolidate:mm`` capacity is registered and a KL is bound. Lets the
    orchestrator run in contexts without L2 wiring (the v0 smoke) without
    failing the lifecycle."""
    cl = getattr(dispatcher, "_cl", None)
    if cl is None:
        return False
    try:
        cl.get_declaration(CONSOLIDATE_MM_IRI)
    except Exception:
        return False
    return getattr(dispatcher, "_kl", None) is not None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def consolidate_task(
    dispatcher: Any,
    mm: Any,
    task_run: Any,
    *,
    task_pattern_iri: Optional[str],
    outcome_classification: str,
    crash_marker: Optional[Any] = None,
):
    """Freeze the MM + assemble the Episode record + dispatch ``consolidate:mm``.

    Returns the consolidate ``InvocationResult``, or ``None`` if consolidation
    is not wired (graceful skip). Idempotent on ``episode_id = task_run.iri``
    (ADR-0176 §4 — the crash-recovery startup scan relies on it).
    """
    if not consolidation_enabled(dispatcher):
        return None
    with mm.lock.write_locked():
        task_input_ref = task_run.task_input_ref or f"taskinput:{task_run.iri}"
        episode_value = {
            "task_input_ref": task_input_ref,
            "mm_root_ref": mm.intelligence_mm.metagraph_id,
            "task_pattern_iri": task_pattern_iri,
            "outcome_classification": outcome_classification,
            "crash_marker": crash_marker,
            "consolidated_at": _utc_now_iso(),
        }
    record = {
        DS_MM_COMPOSITE_INSTANCE: {
            "episode_id": task_run.iri,
            "value": episode_value,
        }
    }
    return dispatcher.dispatch(CONSOLIDATE_MM_IRI, record, task_id=task_run.iri)


__all__ = ["consolidate_task", "consolidation_enabled", "CONSOLIDATE_MM_IRI"]
