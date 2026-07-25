"""Capacity-MM persistence — per-run grounding graphs → Episode (CR: capacity_mm
persist Slice B; reopens DQ-8 / ADR-0202).

Slice A made the capacity writer emit **one grounding graph per pipeline run**
(``(request_id, pipeline_run_ref)``) holding CapacityInstance + DataStateInstance
nodes wired by intra-graph ``PRODUCES`` / ``CONSUMES`` edges. This module makes
those graphs durable at consolidation, reversing ADR-0202's "capacity_mm
live-only until WSD" clause for capacity_mm (knowledge_mm stays live-only).

Two mechanisms live here; both are **Core mechanism only** — no brain policy:

* **PB-1 inspectable encoding.** A DataStateInstance node's runtime value is an
  arbitrary domain object the ADR-0182 codec rejects unless it is already a
  primitive / dict / list. :func:`make_node_value_encoder` dispatches on the
  per-DataState ``encode`` hint (brain-supplied, keyed by DataState type IRI):
  present → call it and require the result be codec-safe; absent → default (A),
  require the value already be primitive / dict / list, else
  :class:`PersistenceError` at persist. The encoders map is supplied by the
  caller that holds the DataState declarations (Step 5 / a brain); core never
  invents encoders.
* **PB-2 task-level index.** Replan yields N per-run graphs under one task, but
  the Episode carries a single ``capacity_root_ref``. :func:`persist_capacity_mm`
  persists every run graph, then persists a **task-level index graph** — one
  ``CapacityRunRef`` node per run graph — and returns that index graph's
  ``graph_id`` as the ``capacity_root_ref`` (mirrors ``mm_root_ref`` → the chain
  graph). A reader loads the index, then each referenced run graph. No v1 reader
  exists yet (PB-5, accepted): the ref dangles exactly as ``mm_root_ref`` does
  until dream reconstruction (WSD).

Inert until Step 5 (PB-3): the submind resolver runs the writer but never
consolidates, and the solve path's ``execution.run`` → ``execute_pipeline``
consolidation of a capacity graph is out-of-CR Step 5. Nothing in this CR
threads run graphs into :func:`consolidate_task`; synthetic phase-48 tests
exercise this module directly.
"""

from __future__ import annotations

from typing import Any, Callable, List, Mapping, Optional

from mindsos_core import Graph
from mindsos_core.exceptions import PersistenceError

from mindsos_capacity.identifiers import (
    NODE_TYPE_DATASTATE_INSTANCE,
    PROP_DATASTATE_INSTANCE_TYPE,
)

#: Role prefix for a task's capacity **index** graph (PB-2). One index graph per
#: task; ``capacity_root_ref`` on the Episode points at its ``graph_id``.
INDEX_GRAPH_ROLE_PREFIX = "capacity:index:"

#: ``type_name`` of an index node: one per persisted run graph. Its ``value`` is
#: the run graph's ``graph_id`` (a primitive — codec fast path); its
#: :data:`PROP_RUN_GRAPH_ROLE` property carries the run graph's role for audit.
NODE_TYPE_CAPACITY_RUN_REF = "CapacityRunRef"

#: Index-node property holding the referenced run graph's role.
PROP_RUN_GRAPH_ROLE = "run_graph_role"

#: JSON-native value types the ADR-0182 node-value codec accepts (rule 4). A
#: DataStateInstance value must reduce to one of these — the encoded structure
#: stays inspectable (D-C), never an opaque blob.
_CODEC_SAFE_TYPES = (str, int, float, bool, dict, list)


def index_graph_role(request_id: str) -> str:
    """Deterministic role for a task's capacity index graph."""
    if not isinstance(request_id, str) or not request_id:
        raise ValueError(f"request_id must be a non-empty string, got {request_id!r}")
    return f"{INDEX_GRAPH_ROLE_PREFIX}{request_id}"


def default_encode(value: Any) -> Any:
    """Default (A) DataStateInstance encoding: require the value already be a
    JSON-native primitive / dict / list (ADR-0182), else fail loud at persist.

    The codec still deep-checks the interior of a dict/list at ``json.dumps``
    time; this only rejects a top-level non-JSON-native value with a clearer,
    DataState-oriented message than the raw codec error.
    """
    if value is None or isinstance(value, _CODEC_SAFE_TYPES):
        return value
    raise PersistenceError(
        f"capacity_mm DataStateInstance value of type {type(value).__name__!r} "
        "is not persistable: it is neither a JSON primitive nor dict/list, and "
        "its DataState declares no `encode` hint (PB-1 default A). Give the "
        "DataState an `encode` that reduces the value to an inspectable "
        "dict/list, or persist a primitive/dict/list value."
    )


def make_node_value_encoder(
    encoders: Mapping[str, Callable[[Any], Any]],
) -> Callable[[Any], Any]:
    """Build the ``node_value_encoder`` :class:`FalkorMMPersister.persist` takes.

    ``encoders`` maps a DataState **type** IRI → its brain-supplied ``encode``
    callable. The returned function, given a live capacity graph node:

    * DataStateInstance → dispatch on the node's DataState type: a registered
      encoder runs and its result must be codec-safe (:func:`default_encode`
      re-checks); otherwise the value itself must already be codec-safe.
    * anything else (CapacityInstance, index nodes) → value passes through the
      default check unchanged (a CapacityInstance value is its capacity IRI, a
      primitive).
    """

    def _encode(node: Any) -> Any:
        if node.type_name == NODE_TYPE_DATASTATE_INSTANCE:
            ds_iri = (node.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE)
            enc = encoders.get(ds_iri) if ds_iri is not None else None
            if enc is not None:
                return default_encode(enc(node.value))
        return default_encode(node.value)

    return _encode


def persist_capacity_mm(
    persister: Any,
    capacity_metagraph: Any,
    run_graphs: List[Any],
    *,
    request_id: str,
    encoders: Optional[Mapping[str, Callable[[Any], Any]]] = None,
) -> Optional[str]:
    """Persist this task's per-run capacity grounding graphs + a task-level
    index graph; return the index graph's ``graph_id`` (the Episode's
    ``capacity_root_ref``), or ``None`` when there is nothing to persist.

    Args:
        persister: an :class:`MMPersister` (edge-aware ``persist``).
        capacity_metagraph: ``mm.capacity_mm`` — the metagraph these graphs and
            the index live under.
        run_graphs: this task's per-run grounding graphs (the writer's
            ``.graph`` for each run). Empty / all-``None`` → returns ``None``.
        request_id: the task these runs belong to (the index graph's role key).
        encoders: DataState-type-IRI → ``encode`` callable (PB-1). ``None`` /
            empty ⇒ every DataStateInstance value must already be codec-safe.

    Each run graph persists **including its intra-graph edges** (PB-4); the
    grounding DAG's ``PRODUCES`` / ``CONSUMES`` structure is preserved.
    """
    graphs = [g for g in (run_graphs or []) if g is not None and g.nodes]
    if not graphs:
        return None

    node_encoder = make_node_value_encoder(encoders or {})
    for g in graphs:
        persister.persist(
            capacity_metagraph, g, node_value_encoder=node_encoder
        )

    # Task-level index: one CapacityRunRef node per persisted run graph. Node
    # value = the run graph's graph_id (a primitive → codec fast path), so the
    # index persists with the default encoder (no per-DataState dispatch).
    index = Graph(name=index_graph_role(request_id), role=index_graph_role(request_id))
    for g in graphs:
        index.add_node(
            value=g.graph_id,
            type_name=NODE_TYPE_CAPACITY_RUN_REF,
            properties={PROP_RUN_GRAPH_ROLE: g.role} if g.role else None,
        )
    persister.persist(capacity_metagraph, index)
    return index.graph_id


__all__ = [
    "INDEX_GRAPH_ROLE_PREFIX",
    "NODE_TYPE_CAPACITY_RUN_REF",
    "PROP_RUN_GRAPH_ROLE",
    "index_graph_role",
    "default_encode",
    "make_node_value_encoder",
    "persist_capacity_mm",
]
