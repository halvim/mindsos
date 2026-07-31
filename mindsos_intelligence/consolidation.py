"""L4 MM consolidation write path (ADR-0176 §1).

At task completion the orchestrator freezes the live MM (acquires the MM
writer lock), assembles the 6-field D-B47 Episode record from the RequestRun
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
This reverses the ADR-0202 "capacity_mm live-only until WSD" clause
(a misattribution — RULES §8). ``None`` when
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
from mindsos_knowledge.schemas.episodic_memories import (
    EPISODE_STATE_CLOSED,
    EPISODE_STATE_OPEN,
    EPISODE_STATE_SUSPENDED,
)

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


def open_episode(
    dispatcher: Any,
    *,
    episode_id: str,
    request_input_ref: Optional[str] = None,
    request_input_root_ref: Optional[str] = None,
):
    """Open the streaming Episode at Request START (Dream PRE-0 Slice 1b, D2).

    Creates the ``Episode`` node ``state=open`` carrying the reload anchors
    (``request_input_ref`` / ``request_input_root_ref`` from PRE-1). Idempotent —
    the capacity no-ops if the node already exists. Graceful skip when
    consolidation is unwired (v0 smoke / no KL). The open Episode IS the crash
    bookmark (subsumes the legacy InMemoryCheckpointStore): a crash before the
    terminal ``close`` leaves this ``state=open`` node for the startup scan.
    """
    if not consolidation_enabled(dispatcher):
        return None
    record = {
        DS_MM_COMPOSITE_INSTANCE: {
            "episode_id": episode_id,
            "value": {
                "op": "open",
                "props": {
                    "state": EPISODE_STATE_OPEN,
                    "request_input_ref": request_input_ref
                    or f"requestinput:{episode_id}",
                    "request_input_root_ref": request_input_root_ref,
                },
            },
        }
    }
    return dispatcher.dispatch(CONSOLIDATE_MM_IRI, record, request_id=episode_id)


def suspend_episode(dispatcher: Any, *, episode_id: str):
    """Mark the open Episode SUSPENDED (needs-input / pending-confirmation).

    A suspended Episode is NOT a crash — it resumes. The startup crash scan
    ignores it (it scans ``state=open`` only). Graceful skip when unwired.
    """
    if not consolidation_enabled(dispatcher):
        return None
    record = {
        DS_MM_COMPOSITE_INSTANCE: {
            "episode_id": episode_id,
            "value": {
                "op": "suspend",
                "props": {"state": EPISODE_STATE_SUSPENDED},
            },
        }
    }
    return dispatcher.dispatch(CONSOLIDATE_MM_IRI, record, request_id=episode_id)


def consolidate_request(
    dispatcher: Any,
    mm: Any,
    request_run: Any,
    *,
    episode_id: str,
    request_pattern_iri: Optional[str],
    outcome_classification: str,
    crash_marker: Optional[Any] = None,
    chain_graph: Any = None,
    mm_persister: Any = None,
    capacity_graphs: Any = None,
    capacity_encoders: Any = None,
):
    """CLOSE the Episode: freeze the MM + stamp the terminal content + ``state=closed``.

    Upserts the open Episode (Dream PRE-0 Slice 1b): updates its ``state`` and the
    now-known content fields (``mm_root_ref`` / ``capacity_root_ref`` /
    ``request_pattern_iri`` / ``outcome_classification`` / ``consolidated_at``) via
    the lazy-inline edit, or writes it whole if no open node exists (a crash
    write, or open was unwired). Returns the consolidate ``InvocationResult``, or
    ``None`` if consolidation is not wired (graceful skip). Idempotent on
    ``episode_id`` (ADR-0176 §4).
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
    # capacity_mm persistence. Dream PRE-0 Slice 2: run graphs are streamed
    # durably as each run completes (CapacityStreamSink), so here we build the
    # task-level index ONLY over them (``capacity_root_ref``). A non-streamed
    # caller (plain list) falls back to persist-run-graphs-then-index
    # (byte-identical to the pre-Slice-2 path). Empty/None leaves it ``None``.
    capacity_root_ref = None
    if mm_persister is not None and capacity_graphs:
        from .capacity_persister import build_capacity_index, persist_capacity_mm

        graphs = list(capacity_graphs)
        if getattr(capacity_graphs, "streamed", False):
            capacity_root_ref = build_capacity_index(
                mm_persister, mm.capacity_mm, graphs, request_id=request_run.iri
            )
        else:
            capacity_root_ref = persist_capacity_mm(
                mm_persister,
                mm.capacity_mm,
                graphs,
                request_id=request_run.iri,
                encoders=capacity_encoders,
            )
    with mm.lock.write_locked():
        request_input_ref = request_run.request_input_ref or f"requestinput:{episode_id}"
        request_input_root_ref = getattr(request_run, "request_input_root_ref", None)
        episode_props = {
            "state": EPISODE_STATE_CLOSED,
            "request_input_ref": request_input_ref,
            "request_input_root_ref": request_input_root_ref,
            "mm_root_ref": mm_root_ref,
            "capacity_root_ref": capacity_root_ref,
            "request_pattern_iri": request_pattern_iri,
            "outcome_classification": outcome_classification,
            "crash_marker": crash_marker,
            "consolidated_at": _utc_now_iso(),
        }
    record = {
        DS_MM_COMPOSITE_INSTANCE: {
            "episode_id": episode_id,
            "value": {"op": "close", "props": episode_props},
        }
    }
    return dispatcher.dispatch(CONSOLIDATE_MM_IRI, record, request_id=episode_id)


__all__ = [
    "open_episode",
    "suspend_episode",
    "consolidate_request",
    "consolidation_enabled",
    "CONSOLIDATE_MM_IRI",
]
