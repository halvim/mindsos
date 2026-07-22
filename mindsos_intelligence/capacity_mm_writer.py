"""Capacity-MM writer — the runtime instance projection of L3 (ADR-0201;
CR#4 Slice 2 origin, reshaped by CR: capacity_mm persist Slice A).

``execute_pipeline`` records each capacity invocation's outputs into
``capacity_mm`` as a **grounding DAG** (ADR-0201): DataStateInstance payloads
and CapacityInstance nodes, wired by ``PRODUCES`` (capacity→datastate) /
``CONSUMES`` (datastate→capacity) edges. This is the "L5 IS the blackboard"
writer (DQ-3): a produced value becomes a node payload here instead of living
only on the executor's transient dict.

**Per-run graph (D-A, CR: capacity_mm persist Slice A).** The writer keys ONE
graph per pipeline run on ``(task_id, pipeline_run_ref)`` — replacing the two
shared fixed-role graphs the origin slice used. Consequences:

* **Replan is fixed by construction.** A second run under the same task gets a
  fresh graph (fresh ``role`` → fresh instance space), so it can never overwrite
  the first run's nodes. (The origin slice namespaced only by IRI and defaulted
  ``pipeline_run_ref`` to ``task_id`` — a silent replan collision, now removed at
  the ``execute_pipeline`` boundary.)
* **PRODUCES/CONSUMES are intra-graph edges.** Both instance node-types live in
  the single per-run graph, so the topology is ``Graph.add_edge`` (not the
  metagraph-level ``add_intergraph_edge`` the two-graph split needed). This
  sidesteps *intergraph*-edge persistence; the per-run graph is a single object
  the Slice-B persister takes whole (edges included).
* **Isolation is real, not just naming.** Two concurrent runs (e.g. a submind
  resolver and a main-task solve) write disjoint graphs.

**Live/persist note:** Slice A writes the live per-run graph only. Persistence of
that graph into the Episode (``capacity_root_ref`` + the per-DataState inspectable
encoding) is Slice B; nothing here persists.

Minting uses the ``ElementRegistry`` attached per sub-MM; instance IRIs bypass the
L3 type validators (they carry a ``#`` fragment out of the type charset — a
structural type-vs-instance guard). ``capacity_mm`` carries no schema
(``Metagraph.schema is None``), so free-form instance ``type_name``s and
PRODUCES/CONSUMES edge types need no type registration.

**Lock discipline (ADR-0201 DQ-6):** every write takes ``mm.lock`` (write); the
lock is NEVER held across a dispatch — the executor calls :meth:`record` *between*
steps, after each dispatch returns. ``RWLock`` is not reentrant, so a
held-across-dispatch lock would be a live defect; :meth:`record`/:meth:`seed`/
:meth:`root` each acquire and release.

**Provenance XRef (DQ-1 / T2 / M1 — Slice 3).** :meth:`link_provenance` writes the
nullable first-class ``capacity_mm``→``knowledge_mm`` XRef (``ref_type=INSTANCE_OF``)
from the ``raw_task`` grounding-DAG root to the pinned corpus-entry instance the
knowledge writer (``MMResolver``) minted. It is nullable: arc1 supplies the target;
the arc3 "None" case is simply **no XRef row**. The XRef is a metagraph-level row
(ADR-0128), not a routed node — no ``sub_mm_for_iri`` concern; ``validate_xref``
(KL-scoped) is untouched. ``add_xref`` self-validates the source in ``capacity_mm``'s
identity (the root node registered on :meth:`root`) and, when the target metagraph is
passed, the target's existence under its role.
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

#: Role prefix for a per-``(task_id, pipeline_run_ref)`` capacity instance graph
#: (D-A). One graph per run replaces the origin slice's two shared fixed-role
#: graphs, giving replan a fresh instance space and Slice-B persistence a single
#: per-run object to take.
RUN_GRAPH_ROLE_PREFIX = "capacity:run:"

_PIPELINERUN_PREFIX = "pipelinerun:"


def run_graph_role(task_id: str, pipeline_run_ref: str) -> str:
    """Deterministic role for a run's instance graph.

    Same ``(task_id, pipeline_run_ref)`` → same role (so a run's writer finds its
    own graph); different runs → different roles (replan / concurrent isolation).
    The ``pipelinerun:`` prefix is stripped and any remaining ``:`` folded to
    ``-`` for a clean role token.
    """
    if not isinstance(task_id, str) or not task_id:
        raise ValueError(f"task_id must be a non-empty string, got {task_id!r}")
    if not isinstance(pipeline_run_ref, str) or not pipeline_run_ref:
        raise ValueError(
            f"pipeline_run_ref must be a non-empty string, got {pipeline_run_ref!r}"
        )
    run = pipeline_run_ref
    if run.startswith(_PIPELINERUN_PREFIX):
        run = run[len(_PIPELINERUN_PREFIX):]
    run = run.replace(":", "-")
    return f"{RUN_GRAPH_ROLE_PREFIX}{task_id}:{run}"


class CapacityMMWriter:
    """Writes one pipeline run's grounding DAG into a single per-run graph in
    ``mm.capacity_mm``.

    One per pipeline run. :attr:`index` maps a DataState *type* IRI to the
    *instance* IRI currently carrying its value, so a downstream consumer's
    CONSUMES edge points at the producing instance.
    """

    def __init__(self, mm: MentalModel, task_id: str, pipeline_run_ref: str) -> None:
        self._mm = mm
        self._task_id = task_id
        self._run_ref = pipeline_run_ref
        self._graph_role = run_graph_role(task_id, pipeline_run_ref)
        self._graph: Optional[Graph] = None
        self._seq: Dict[str, int] = {}
        #: DataState type IRI -> current instance IRI (run-local routing index).
        self.index: Dict[str, str] = {}

    # ── graph find-or-create (caller already holds the write lock) ────────

    def _run_graph(self) -> Graph:
        if self._graph is None:
            for g in self._mm.capacity_mm.graphs.values():
                if g.role == self._graph_role:
                    self._graph = g
                    break
            else:
                g = Graph(name=self._graph_role, role=self._graph_role)
                self._mm.capacity_mm.add_graph(g)
                self._graph = g
        return self._graph

    @property
    def graph(self) -> Optional[Graph]:
        """This run's instance graph, or ``None`` if the run wrote nothing.
        Exposed for the Slice-B persister (persist exactly this run's graph)."""
        return self._graph

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
            self._run_graph().add_node(
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
        output and wire PRODUCES, updating the index. All nodes + edges live in
        this run's single graph (intra-graph edges). Returns the CapacityInstance IRI."""
        with self._mm.lock.write_locked():
            graph = self._run_graph()
            cap_inst = capacity_instance_iri(
                capacity_iri, self._task_id, self._run_ref,
                self._next_seq(f"cap:{capacity_iri}"),
            )
            cap_node = graph.add_node(
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
                    graph.add_edge(graph.nodes[producer], cap_node, EDGE_CONSUMES)
            # PRODUCES: capacity-instance -> datastate-instance, per output.
            for out_iri, value in outputs.items():
                out_inst = self._mint_datastate(out_iri, value)
                graph.add_edge(cap_node, graph.nodes[out_inst], EDGE_PRODUCES)
            return cap_inst

    def link_provenance(
        self,
        raw_task_root_iri: str,
        *,
        target_id: Optional[str],
        target_role: str,
        target_metagraph_id: Optional[str] = None,
    ) -> Any:
        """Write the DQ-1 provenance XRef ``capacity_mm``→``knowledge_mm``.

        From the ``raw_task`` grounding-DAG root (minted by :meth:`root`) to the
        pinned corpus-entry instance the knowledge writer put in ``knowledge_mm``
        (``target_id`` under ``target_role`` — the ``MMResolver`` instance graph
        role). ``ref_type=INSTANCE_OF`` (M1). **Nullable (T2):** ``target_id=None``
        (arc3) writes nothing and returns ``None``; a concrete target (arc1) writes
        one first-class :class:`XRef` row on ``capacity_mm`` and returns it.

        ``add_xref`` validates the source id in ``capacity_mm``'s identity (the root
        node registered on :meth:`root`) and — since ``knowledge_mm`` is passed as
        the target metagraph — the target's existence under ``target_role`` before
        the WAL (P59). Takes ``mm.lock`` (write); never held across a dispatch.
        """
        if target_id is None:
            return None  # arc3 — no XRef row (T2)
        with self._mm.lock.write_locked():
            return self._mm.capacity_mm.add_xref(
                source_id=raw_task_root_iri,
                target_metagraph_id=(
                    target_metagraph_id or self._mm.knowledge_mm.metagraph_id
                ),
                target_role=target_role,
                target_id=target_id,
                ref_type="INSTANCE_OF",
                target_metagraph=self._mm.knowledge_mm,
            )

    # ── internal (lock already held by the caller) ───────────────────────

    def _mint_datastate(self, datastate_iri: str, value: Any) -> str:
        inst = datastate_instance_iri(
            datastate_iri, self._task_id, self._run_ref,
            self._next_seq(f"ds:{datastate_iri}"),
        )
        self._run_graph().add_node(
            value=value,
            type_name=NODE_TYPE_DATASTATE_INSTANCE,
            properties={PROP_DATASTATE_INSTANCE_TYPE: datastate_iri},
            node_id=inst,
        )
        self.index[datastate_iri] = inst
        return inst


__all__ = [
    "CapacityMMWriter",
    "RUN_GRAPH_ROLE_PREFIX",
    "run_graph_role",
]
