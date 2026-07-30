"""Open-tolerant Episode reader (Dream PRE-0 Slice 3).

The FIRST reader over the streaming Episode (Slice 1b lifecycle + Slice 2 streamed
grounding). Given an ``episode_id`` it loads the Episode node and resolves its
grounding, whether the request closed normally or crashed:

* **chain** (``intelligence_mm`` plan / task tree) -- by ``mm_root_ref`` when set
  (closed episode), else by the deterministic chain-graph name
  (``chain:...:{episode_id}``) via :func:`graph_anchors_by_role` (crashed /
  not-yet-refed episode).
* **capacity run graphs** (per-run L5 grounding) -- via the capacity index at
  ``capacity_root_ref`` when set, else by the deterministic run-graph role prefix
  ``capacity:run:{episode_id}:``.

Why the fallback: a crashed request wrote its grounding to Falkor as it streamed
(Slice 2), but D2-A never wrote the refs onto the Episode node, and after a restart
the writing session's metagraph_id is gone -- so the refs are ``None`` and the
graphs are located by their deterministic ``role``/``name`` instead
(:func:`graph_anchors_by_role`). Recovery is left untouched (it only closes
``state=open`` -> ``closed``/``failed``); this reader does the lookup.

Tolerates OPEN / incomplete / partial episodes: any grounding that is missing or
unloadable is skipped and ``partial=True`` is set (never raises on a missing
graph). Latest replan attempt wins for the run graphs (best-effort dedup by the
per-run ref-path position -- :func:`_latest_by_position`).

Loading is graph-scoped ``load_graph`` (by id, cross-session). Efficient
index-scoped querying is PRE-3 (deferred); ``knowledge_mm`` is PRE-6.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .capacity_mm_writer import RUN_GRAPH_ROLE_PREFIX
from .capacity_persister import NODE_TYPE_CAPACITY_RUN_REF
from .chain_artifacts import CHAIN_GRAPH_ROLE


@dataclass
class EpisodeView:
    """Resolved view of one Episode (Dream PRE-0 Slice 3).

    ``partial`` is ``True`` when any expected grounding could not be located or
    loaded (an open/crashed episode read before its work completed, a dropped
    stream-flush, or no Falkor client) -- the dream must tolerate this."""

    episode_id: str
    state: Optional[str] = None
    outcome_classification: Optional[str] = None
    request_input_ref: Optional[str] = None
    request_input_root_ref: Optional[str] = None
    crash_marker: Optional[Any] = None
    chain_graph: Optional[Any] = None
    capacity_run_graphs: List[Any] = field(default_factory=list)
    partial: bool = False


def _find_episode_node(kl: Any, user_id: str, episode_id: str) -> Optional[Any]:
    """Locate the Episode node (``value == episode_id``) in the user's live Local
    ``episodic_memories`` role-graph (boot-installed). ``None`` if absent."""
    from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
    from mindsos_knowledge.metagraph_view import MetagraphView
    from mindsos_knowledge.schemas.episodic_memories import NODE_EPISODE

    try:
        local_mg = kl.local_metagraph(user_id)
    except Exception:
        return None
    graphs = MetagraphView(local_mg).graphs_by_role(ROLE_EPISODIC_MEMORIES)
    if not graphs:
        return None
    for node in graphs[0].nodes.values():
        if node.type_name == NODE_EPISODE and getattr(node, "value", None) == episode_id:
            return node
    return None


def _decode_crash_marker(raw: Any) -> Any:
    """``crash_marker`` is stored JSON-encoded (L1 props are primitives-only);
    decode it back to a dict. Pass through ``None`` / already-decoded values."""
    if raw is None or isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        import json

        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return raw
    return raw


def _attempt_key(role: str) -> Tuple[str, Tuple[int, int]]:
    """``(position, recency)`` for a capacity run-graph role -- latest-attempt-wins.

    A run role is ``capacity:run:{rid}:{token}`` whose ``token`` trails with the
    replan ``-{run_attempt}`` and, for a map member, a ``-r{retry}`` (accepted
    attempt only). Strip those trailing numeric segments to get the stable
    ref-path position; the stripped ints order recency. Unparseable -> the whole
    role is its own position (kept)."""
    token = role
    retry = -1
    attempt = -1
    m = re.search(r"-r(\d+)$", token)
    if m:
        retry = int(m.group(1))
        token = token[: m.start()]
    m = re.search(r"-(\d+)$", token)
    if m:
        attempt = int(m.group(1))
        token = token[: m.start()]
    return token, (attempt, retry)


def _latest_by_position(anchors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Best-effort latest-replan-attempt-wins over run-graph anchors
    (``{id, role, name}``): keep, per ref-path position, the highest
    ``(attempt, retry)``. Anchors with no role are kept as-is."""
    best: Dict[str, Tuple[Tuple[int, int], Dict[str, Any]]] = {}
    keep_all: List[Dict[str, Any]] = []
    for a in anchors:
        role = a.get("role")
        if not role:
            keep_all.append(a)
            continue
        pos, recency = _attempt_key(role)
        cur = best.get(pos)
        if cur is None or recency > cur[0]:
            best[pos] = (recency, a)
    return keep_all + [entry[1] for entry in best.values()]


def read_episode(
    kl: Any, client: Any, *, episode_id: str, user_id: str = "user"
) -> Optional[EpisodeView]:
    """Load Episode ``episode_id`` and resolve its grounding (open-tolerant).

    ``kl`` provides the boot-installed Local holding the Episode node; ``client``
    is the Falkor client for graph loads (``None`` -> node/props only, grounding
    skipped, ``partial=True``). Returns ``None`` if no such Episode node exists.
    """
    node = _find_episode_node(kl, user_id, episode_id)
    if node is None:
        return None
    props = getattr(node, "properties", None) or {}
    view = EpisodeView(
        episode_id=episode_id,
        state=props.get("state"),
        outcome_classification=props.get("outcome_classification"),
        request_input_ref=props.get("request_input_ref"),
        request_input_root_ref=props.get("request_input_root_ref"),
        crash_marker=_decode_crash_marker(props.get("crash_marker")),
    )
    if client is None:
        view.partial = True
        return view

    from mindsos_core.reconstruction import graph_anchors_by_role, load_graph

    def _try_load(graph_id: str) -> Optional[Any]:
        try:
            return load_graph(client, graph_id)
        except Exception:
            return None

    # ── chain (plan / task tree): ref first, else by deterministic name ──
    chain = None
    mm_root_ref = props.get("mm_root_ref")
    if mm_root_ref:
        chain = _try_load(mm_root_ref)
    if chain is None:
        anchors = graph_anchors_by_role(
            client, role_prefix=CHAIN_GRAPH_ROLE, name_suffix=f":{episode_id}"
        )
        if anchors:
            chain = _try_load(anchors[0]["id"])
    view.chain_graph = chain
    if chain is None:
        view.partial = True

    # ── capacity run graphs: index ref first, else by role prefix ──
    run_ids: List[str] = []
    capacity_root_ref = props.get("capacity_root_ref")
    if capacity_root_ref:
        index = _try_load(capacity_root_ref)
        if index is None:
            view.partial = True
        else:
            run_ids = [
                n.value
                for n in index.nodes.values()
                if n.type_name == NODE_TYPE_CAPACITY_RUN_REF and n.value
            ]
    if not run_ids:
        anchors = _latest_by_position(
            graph_anchors_by_role(
                client, role_prefix=f"{RUN_GRAPH_ROLE_PREFIX}{episode_id}:"
            )
        )
        run_ids = [a["id"] for a in anchors if a.get("id")]

    runs: List[Any] = []
    for gid in run_ids:
        g = _try_load(gid)
        if g is None:
            view.partial = True
        else:
            runs.append(g)
    view.capacity_run_graphs = runs
    return view


__all__ = ["EpisodeView", "read_episode"]
