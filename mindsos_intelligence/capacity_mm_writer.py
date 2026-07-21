"""Capacity-MM writer — the runtime instance projection of L3 (CR#4 Slice 2).

``execute_pipeline`` records each capacity invocation's outputs into
``capacity_mm`` as a bipartite **grounding DAG** (ADR-0201): DataStateInstance
payloads in one graph, CapacityInstance nodes in another, wired by ``PRODUCES``
(capacity→datastate) / ``CONSUMES`` (datastate→capacity) IntergraphEdges. This is
the "L5 IS the blackboard" writer (DQ-3): a produced value becomes a node payload
here instead of living only on the executor's transient dict.

**Live-only (ADR-0201):** capacity_mm instances are not persisted. Minting uses the
``ElementRegistry`` attached per sub-MM; instance IRIs bypass the L3 type validators
(they carry a ``#`` fragment out of the type charset — a structural type-vs-instance
guard). ``capacity_mm`` carries no schema (``Metagraph.schema is None``), so free-form
instance ``type_name``s and PRODUCES/CONSUMES edges need no type registration.

**Lock discipline (ADR-0201 DQ-6):** every write takes ``mm.lock`` (write); the lock is
NEVER held across a dispatch — the executor calls :meth:`record` *between* steps, after
each dispatch returns. ``RWLock`` is not reentrant, so a held-across-dispatch lock would
be a live defect; :meth:`record`/:meth:`seed`/:meth:`root` each acquire and release.

Scope key = ``(task_id, pipeline_run_ref)`` (ADR-0201 §Minting): survives replan and stays
groupable by task. The provenance XRef (raw_task → knowledge_mm corpus entry) is **not**
written here — it needs the knowledge-MM target that Slice 3 mints (``add_xref`` requires a
concrete target; the arc3 "None" case is simply no XRef row).
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional

from mindsos_core import Graph

from mindsos_capacity.identifiers import (
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_DATASTATE_INSTANCE,
    PROP_CAPACITY_INSTANCE_TYPE,
    PROP_DATASTATE_INSTANCE_TYPE,
    capacity_instance_iri,
    datastate_instance_iri,
    datastate_instance_root_iri,
)

from .mm import MentalModel

#: Roles for the two bipartite capacity_mm instance graphs (ADR-0201 D-3),
#: mirroring L3's shared-datastates-graph / category-graph split.
DATASTATE_INSTANCE_GRAPH_ROLE = "capacity:instances:datastates"
CAPACITY_INSTANCE_GRAPH_ROLE = "capacity:instances:capacities"


class CapacityMMWriter:
    """Writes the per-task grounding DAG into ``mm.capacity_mm``.

    One per pipeline run. :attr:`index` maps a DataState *type* IRI to the
    *instance* IRI currently carrying its value, so a downstream consumer's
    CONSUMES edge points at the producing instance.
    """

    def __init__(self, mm: MentalModel, task_id: str, pipeline_run_ref: str) -> None:
        self._mm = mm
        self._task_id = task_id
        self._run_ref = pipeline_run_ref
        self._ds_graph: Optional[Graph] = None
        self._cap_graph: Optional[Graph] = None
        self._seq: Dict[str, int] = {}
        #: DataState type IRI -> current instance IRI (run-local routing index).
        self.index: Dict[str, str] = {}

    # ── graph find-or-create (caller already holds the write lock) ────────

    def _ds_instance_graph(self) -> Graph:
        if self._ds_graph is None:
            self._ds_graph = self._find_or_create(DATASTATE_INSTANCE_GRAPH_ROLE)
        return self._ds_graph

    def _cap_instance_graph(self) -> Graph:
        if self._cap_graph is None:
            self._cap_graph = self._find_or_create(CAPACITY_INSTANCE_GRAPH_ROLE)
        return self._cap_graph

    def _find_or_create(self, role: str) -> Graph:
        for g in self._mm.capacity_mm.graphs.values():
            if g.role == role:
                return g
        g = Graph(name=role, role=role)
        self._mm.capacity_mm.add_graph(g)
        return g

    def _next_seq(self, key: str) -> int:
        n = self._seq.get(key, 0)
        self._seq[key] = n + 1
        return n

    # ── public API (each takes the MM write lock; never across a dispatch) ─

    def seed(self, datastate_iri: str, value: Any) -> str:
        """Mint a DataStateInstance for a pipeline start input and index it."""
        with self._mm.lock.write_locked():
            return self._mint_datastate(datastate_iri, value)

    def root(self, raw_task_datastate_iri: str, value: Any) -> str:
        """Mint the grounding-DAG root (``raw_task``) instance (ADR-0201 DQ-1)
        and index it. Task-level; minted once before any pipeline run. Exposed
        for the solve-path caller (Step 5); ``execute_pipeline`` uses :meth:`seed`."""
        with self._mm.lock.write_locked():
            inst = datastate_instance_root_iri(raw_task_datastate_iri, self._task_id)
            self._ds_instance_graph().add_node(
                value=value,
                type_name=NODE_TYPE_DATASTATE_INSTANCE,
                properties={PROP_DATASTATE_INSTANCE_TYPE: raw_task_datastate_iri},
                node_id=inst,
            )
            self.index[raw_task_datastate_iri] = inst
            return inst

    def record(
        self,
        capacity_iri: str,
        input_datastate_iris: Iterable[str],
        outputs: Mapping[str, Any],
    ) -> str:
        """Record one capacity invocation: mint the CapacityInstance, wire
        CONSUMES from each already-instanced input, mint a DataStateInstance per
        output and wire PRODUCES, updating the index. Returns the CapacityInstance IRI."""
        with self._mm.lock.write_locked():
            cap_graph = self._cap_instance_graph()
            ds_graph = self._ds_instance_graph()
            cap_gid, ds_gid = cap_graph.graph_id, ds_graph.graph_id

            cap_inst = capacity_instance_iri(
                capacity_iri, self._task_id, self._run_ref,
                self._next_seq(f"cap:{capacity_iri}"),
            )
            cap_graph.add_node(
                value=capacity_iri,
                type_name=NODE_TYPE_CAPACITY_INSTANCE,
                properties={PROP_CAPACITY_INSTANCE_TYPE: capacity_iri},
                node_id=cap_inst,
            )
            # CONSUMES: datastate-instance -> capacity-instance, for each input
            # whose producing instance we know (seeded start or upstream output).
            for in_iri in input_datastate_iris:
                producer = self.index.get(in_iri)
                if producer is not None:
                    self._mm.capacity_mm.add_intergraph_edge(
                        ds_gid, producer, cap_gid, cap_inst, EDGE_CONSUMES
                    )
            # PRODUCES: capacity-instance -> datastate-instance, per output.
            for out_iri, value in outputs.items():
                out_inst = self._mint_datastate(out_iri, value)
                self._mm.capacity_mm.add_intergraph_edge(
                    cap_gid, cap_inst, ds_gid, out_inst, EDGE_PRODUCES
                )
            return cap_inst

    # ── internal (lock already held by the caller) ───────────────────────

    def _mint_datastate(self, datastate_iri: str, value: Any) -> str:
        inst = datastate_instance_iri(
            datastate_iri, self._task_id, self._run_ref,
            self._next_seq(f"ds:{datastate_iri}"),
        )
        self._ds_instance_graph().add_node(
            value=value,
            type_name=NODE_TYPE_DATASTATE_INSTANCE,
            properties={PROP_DATASTATE_INSTANCE_TYPE: datastate_iri},
            node_id=inst,
        )
        self.index[datastate_iri] = inst
        return inst


__all__ = [
    "CapacityMMWriter",
    "DATASTATE_INSTANCE_GRAPH_ROLE",
    "CAPACITY_INSTANCE_GRAPH_ROLE",
]
