"""Request-input persistence — the Dream's reload anchor (PRE-1).

Today a Request's input survives only as a bare label (``requestinput:<id>``)
with no backing store, so the interpret->map->plan calibration and every
downstream Task can be replayed only if the *actual* input value is
recoverable. This module persists the raw input value (+ its modality) as a
one-node graph and returns that graph's ``graph_id`` -- the Episode's
``request_input_root_ref``, the anchor the Dream reloads a Request from.

Mirrors :mod:`mindsos_intelligence.capacity_persister`:

* the same codec-safe encode discipline -- a value is persistable iff it is a
  JSON-native primitive / dict / list, or a supplied ``encode`` reduces it to
  one, else :class:`PersistenceError`;
* persists through the same narrow ``MMPersister`` surface.

Unlike ``capacity_root_ref`` (write-only until dream reconstruction, PB-5),
PRE-1 ships a reader -- :func:`load_request_input` -- plus an integration
round-trip test, because the whole justification for PRE-1 is that the anchor
reads back.

Write-site posture (the live solve path, ``Orchestrator.run_lifecycle``):
**best-effort + inert**. Skipped when no persister is wired or in simplified
mode; a non-codec-safe input with no ``encode`` is swallowed by the caller
(root ref stays ``None``) rather than failing the solve -- the Dream simply
lacks that anchor until an encoder is supplied.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Tuple

from mindsos_core import Graph
from mindsos_core.exceptions import PersistenceError

#: Role prefix for a Request's input graph. Keyed by the task-unique writer
#: scope so two Requests' input graphs never collide.
INPUT_GRAPH_ROLE_PREFIX = "request:input:"

#: ``type_name`` of the single node holding the raw input value.
NODE_TYPE_REQUEST_INPUT = "RequestInput"

#: Node property carrying the input's stamped modality (``None`` -> omitted).
PROP_INPUT_MODALITY = "modality"

#: JSON-native value types the ADR-0182 node-value codec accepts (rule 4).
_CODEC_SAFE_TYPES = (str, int, float, bool, dict, list)


def input_graph_role(scope: str) -> str:
    """Deterministic role for a Request's input graph (keyed by the task-unique
    writer scope)."""
    if not isinstance(scope, str) or not scope:
        raise ValueError(f"scope must be a non-empty string, got {scope!r}")
    return f"{INPUT_GRAPH_ROLE_PREFIX}{scope}"


def _encode_input(value: Any, encode: Optional[Callable[[Any], Any]]) -> Any:
    """Reduce ``value`` to a codec-safe form, or raise. A supplied ``encode``
    runs first; its result is re-checked (an encoder returning a non-native
    value is still a failure)."""
    if encode is not None:
        value = encode(value)
    if value is None or isinstance(value, _CODEC_SAFE_TYPES):
        return value
    raise PersistenceError(
        f"request input value of type {type(value).__name__!r} is not "
        "persistable: it is neither a JSON primitive nor dict/list, and no "
        "`encode` hint reduced it to one. Supply an `encode` that returns an "
        "inspectable primitive/dict/list."
    )


def persist_request_input(
    persister: Any,
    intelligence_metagraph: Any,
    *,
    scope: str,
    value: Any,
    modality: Optional[str] = None,
    encode: Optional[Callable[[Any], Any]] = None,
) -> str:
    """Persist ``value`` (+ ``modality``) as a one-node ``RequestInput`` graph
    under ``intelligence_metagraph``; return its ``graph_id`` (the Episode's
    ``request_input_root_ref``).

    Raises :class:`PersistenceError` when ``value`` is not codec-safe and no
    ``encode`` reduces it. The live solve path persists **best-effort** (a
    non-persistable input must not fail the solve).
    """
    encoded = _encode_input(value, encode)
    role = input_graph_role(scope)
    graph = Graph(name=role, role=role)
    graph.add_node(
        value=encoded,
        type_name=NODE_TYPE_REQUEST_INPUT,
        properties={PROP_INPUT_MODALITY: modality} if modality is not None else None,
    )
    persister.persist(intelligence_metagraph, graph)
    return graph.graph_id


def load_request_input(client: Any, root_ref: str) -> Tuple[Any, Optional[str]]:
    """Reload a persisted request input by its ``request_input_root_ref``.

    Returns ``(value, modality)`` -- the Dream's reload anchor. Raises
    :class:`PersistenceError` if the graph holds no ``RequestInput`` node.
    """
    from mindsos_core.reconstruction import load_graph

    graph = load_graph(client, root_ref)
    for node in graph.nodes.values():
        if node.type_name == NODE_TYPE_REQUEST_INPUT:
            modality = (node.properties or {}).get(PROP_INPUT_MODALITY)
            return node.value, modality
    raise PersistenceError(
        f"request_input_root_ref {root_ref!r} holds no "
        f"{NODE_TYPE_REQUEST_INPUT} node"
    )


__all__ = [
    "INPUT_GRAPH_ROLE_PREFIX",
    "NODE_TYPE_REQUEST_INPUT",
    "PROP_INPUT_MODALITY",
    "input_graph_role",
    "persist_request_input",
    "load_request_input",
]
