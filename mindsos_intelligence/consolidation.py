"""L4 MM consolidation write path (ADR-0176 §1).

At task completion the orchestrator freezes the live MM (acquires the MM
writer lock), assembles the 6-field D-B47 Episode record from the TaskRun
chain, and dispatches ``capacity:consolidate:mm`` — the L3 write surface
(ADR-0146) that writes the Episode and materialises the Memory composite
(ADR-0176 §3). Retain-by-default on success / failure / abort (Chat B §4.1).

``mm_root_ref`` points at *this task's* chain graph_id (DQ-8 / CR#4). The
per-task chain graph is persisted here via the injected ``MMPersister`` (only
that one graph, so consolidation stays O(this task) — not a full-MM re-walk);
the heavy full-MM serialization is deferred.

``capacity_root_ref`` (CR: reopen DQ-8, Slice B) mirrors ``mm_root_ref`` for
capacity_mm: when a caller passes this task's per-run capacity grounding graphs,
they persist (edges included) and the Episode's ``capacity_root_ref`` points at
their task-level index graph (see :mod:`mindsos_intelligence.capacity_persister`).
This reverses the ADR-0202 "capacity_mm live-only until WSD" clause. ``None`` when
no capacity graphs are supplied — the case today: no in-CR path threads them
(the submind never consolidates; the solve path's ``execution.run`` →
``execute_pipeline`` consolidation is out-of-CR Step 5), so the capacity
persist is **inert until Step 5**. ``knowledge_mm`` stays live-only (Slice 3).

Consolidation is **skipped** in simplified mode and gracefully skipped when no
consolidate capacity / KL is wired (e.g. the v0 orchestrator smoke), per the
opt-out-per-task contract.
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


def consolidate_request(
    dispatcher: Any,
    mm: Any,
    request_run: Any,
    *,
    task_pattern_iri: Optional[str],
    outcome_classification: str,
    crash_marker: Optional[Any] = None,
    chain_graph: Any = None,
    mm_persister: Any = None,
    capacity_graphs: Any = None,
    capacity_encoders: Any = None,
):
    """Freeze the MM + assemble the Episode record + dispatch ``consolidate:mm``.

    Returns the consolidate ``InvocationResult``, or ``None`` if consolidation
    is not wired (graceful skip). Idempotent on ``episode_id = request_run.iri``
    (ADR-0176 §4 — the crash-recovery startup scan relies on it).
    """
    if not consolidation_enabled(dispatcher):
        return None
    # Persist THIS task's chain graph BEFORE the Episode references it (DQ-8 /
    # CR#4) so ``mm_root_ref`` never dangles. Persisting a single graph keeps
    # this O(this task). No-op when unwired (ephemeral / no persister) or when
    # no chain graph was produced. Done outside the MM lock: the graph is
    # frozen at the terminal path (no further emits) and other tasks write only
    # their own graphs, so nothing mutates it concurrently.
    if mm_persister is not None and chain_graph is not None:
        mm_persister.persist(mm.intelligence_mm, chain_graph)
    mm_root_ref = (
        chain_graph.graph_id if chain_graph is not None
        else mm.intelligence_mm.metagraph_id
    )
    # capacity_mm persistence (CR: reopen DQ-8, Slice B). Persist this task's
    # per-run grounding graphs (edges included) + a task-level index graph;
    # ``capacity_root_ref`` mirrors ``mm_root_ref``. Inert until Step 5: no
    # in-CR caller supplies ``capacity_graphs`` yet, so this stays ``None``.
    capacity_root_ref = None
    if mm_persister is not None and capacity_graphs:
        from .capacity_persister import persist_capacity_mm

        capacity_root_ref = persist_capacity_mm(
            mm_persister,
            mm.capacity_mm,
            list(capacity_graphs),
            request_id=request_run.iri,
            encoders=capacity_encoders,
        )
    with mm.lock.write_locked():
        task_input_ref = request_run.task_input_ref or f"taskinput:{request_run.iri}"
        episode_value = {
            "task_input_ref": task_input_ref,
            "mm_root_ref": mm_root_ref,
            "capacity_root_ref": capacity_root_ref,
            "task_pattern_iri": task_pattern_iri,
            "outcome_classification": outcome_classification,
            "crash_marker": crash_marker,
            "consolidated_at": _utc_now_iso(),
        }
    record = {
        DS_MM_COMPOSITE_INSTANCE: {
            "episode_id": request_run.iri,
            "value": episode_value,
        }
    }
    return dispatcher.dispatch(CONSOLIDATE_MM_IRI, record, request_id=request_run.iri)


__all__ = ["consolidate_task", "consolidation_enabled", "CONSOLIDATE_MM_IRI"]
