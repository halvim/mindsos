"""L4 crash recovery — L4-startup scan for crashed (open) Episodes
(ADR-0179; Chat B D-B50; reworked Dream PRE-0 Slice 1b).

**Dream PRE-0 Slice 1b model.** The streaming Episode subsumes the legacy
tombstone-marker mechanism (``InMemoryCheckpointStore`` / ``CheckpointMarker`` /
``record_checkpoint`` — all removed). The Episode is opened ``state=open`` at
Request start and closed ``state=closed`` on every terminal decision, so:

* a normally-decided Request leaves a ``closed`` Episode;
* a needs-input Request leaves a ``suspended`` Episode (resumes; NOT a crash);
* a **crash** (process died before the terminal close) leaves the Episode
  ``state=open`` — the ONLY failure.

On ``IntelligenceLayer.start`` :func:`recover_unconsolidated` scans the user's
Local ``episodic_memories`` role-graph for ``state == open`` Episodes and stamps
each ``state=closed`` + ``outcome_classification="failed"`` + a ``crash_marker``,
**preserving whatever partial content was already written at open** (promotes
ADR-0179 §3 partial-content recovery from deferred to real — the open Episode
already holds the ``request_input_ref`` / ``request_input_root_ref`` anchors).
The close goes through the same ``consolidate:mm`` capacity (op=close upsert), so
the write path is uniform. Durable when a Local persister is supplied.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, List, Optional

from mindsos_capacity.builtins.consolidate import DS_MM_COMPOSITE_INSTANCE
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
from mindsos_knowledge.metagraph_view import MetagraphView
from mindsos_knowledge.schemas.episodic_memories import (
    EPISODE_STATE_CLOSED,
    EPISODE_STATE_OPEN,
    NODE_EPISODE,
)

CONSOLIDATE_MM_IRI = "capacity:consolidate:mm"


@dataclass
class CrashInfo:
    """Stamped on a recovered Episode's ``crash_marker`` (Chat B §4.3)."""

    last_phase: Optional[str] = None
    last_milestone: Optional[str] = None
    detected_at: str = ""
    recovered: bool = False


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _episode_state(node: Any) -> Optional[str]:
    """The Episode's lifecycle ``state`` (Dream PRE-0 Slice 1b: a real node
    property). Tolerates a missing property (returns ``None``)."""
    props = getattr(node, "properties", None) or {}
    return props.get("state")


def _episode_id_of(node: Any) -> Optional[str]:
    """Recover the ``episode_id`` from a crashed Episode node.

    The node's primary ``value`` IS the ``episode_id`` (set at open); fall back
    to nothing if that invariant does not hold (skip the node)."""
    val = getattr(node, "value", None)
    return val if isinstance(val, str) and val else None


def recover_unconsolidated(dispatcher: Any, *, local_persister: Any = None) -> List[str]:
    """L4-startup scan: close every crashed (``state=open``) Episode in place.

    For each open Episode, stamp ``state=closed`` + ``outcome_classification=
    "failed"`` + a recovered ``crash_marker`` via the ``consolidate:mm`` op=close
    upsert (merge — the open anchors are preserved). Returns the recovered
    ``episode_id``s. No-op when the KL / consolidate capacity is unavailable or
    no Episode is open. Durably flushes the Local when ``local_persister`` is
    supplied and anything was recovered.
    """
    kl = getattr(dispatcher, "_kl", None)
    session = getattr(dispatcher, "_session", None)
    if kl is None:
        return []
    from .consolidation import consolidation_enabled

    if not consolidation_enabled(dispatcher):
        return []
    user_id = getattr(session, "user_id", "user")
    try:
        local_mg = kl.local_metagraph(user_id)
    except Exception:
        return []
    graphs = MetagraphView(local_mg).graphs_by_role(ROLE_EPISODIC_MEMORIES)
    if not graphs:
        return []
    g = graphs[0]
    open_episodes = [
        n
        for n in g.nodes.values()
        if n.type_name == NODE_EPISODE and _episode_state(n) == EPISODE_STATE_OPEN
    ]

    recovered: List[str] = []
    for node in open_episodes:
        episode_id = _episode_id_of(node)
        if episode_id is None:
            continue
        crash = CrashInfo(detected_at=_utc_now_iso(), recovered=True)
        record = {
            DS_MM_COMPOSITE_INSTANCE: {
                "episode_id": episode_id,
                "value": {
                    "op": "close",
                    "props": {
                        "state": EPISODE_STATE_CLOSED,
                        "outcome_classification": "failed",
                        "crash_marker": asdict(crash),
                        "consolidated_at": _utc_now_iso(),
                    },
                },
            }
        }
        result = dispatcher.dispatch(
            CONSOLIDATE_MM_IRI, record, request_id=episode_id
        )
        if result is not None and getattr(result, "success", True):
            recovered.append(episode_id)

    if recovered and local_persister is not None:
        try:
            local_persister.save(user_id, kl.local_metagraph(user_id))
        except Exception:
            pass
    return recovered


__all__ = ["CrashInfo", "recover_unconsolidated"]
