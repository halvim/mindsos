"""Capacity-MM writer — the runtime instance projection of L3 (ADR-0201;
CR#4 Slice 2 origin, reshaped by CR: capacity_mm persist Slice A).

``execute_pipeline`` records each capacity invocation's outputs into
``capacity_mm`` as a **grounding DAG** (ADR-0201): DataStateInstance payloads
and CapacityInstance nodes, wired by ``PRODUCES`` (capacity→datastate) /
``CONSUMES`` (datastate→capacity) edges. This is the "L5 IS the blackboard"
writer (DQ-3): a produced value becomes a node payload here instead of living
only on the executor's transient dict.

**Per-run graph (D-A, CR: capacity_mm persist Slice A).** The writer keys ONE
graph per pipeline run on ``(request_id, pipeline_run_ref)`` — replacing the two
shared fixed-role graphs the origin slice used. Consequences:

* **Replan is fixed by construction.** A second run under the same task gets a
  fresh graph (fresh ``role`` → fresh instance space), so it can never overwrite
  the first run's nodes. (The origin slice namespaced only by IRI and defaulted
  ``pipeline_run_ref`` to ``request_id`` — a silent replan collision, now removed at
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
    MANIFEST_CAPACITY_PHRASES,
    MANIFEST_CASE_LABEL,
    MANIFEST_DECLARED_STARTS,
    MANIFEST_MEMBER_GRAPH_IDS,
    MANIFEST_STOP_REASON_PHRASES,
    NODE_TYPE_RUN_MANIFEST,
    RUN_STOPPED_PHRASES,
    run_manifest_iri,
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    EDGE_STOPPED_AT,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_DATASTATE_INSTANCE,
    NODE_TYPE_RUN_STOPPED,
    PROP_CAPACITY_INSTANCE_TYPE,
    PROP_DATASTATE_INSTANCE_TYPE,
    PROP_RUN_STOPPED_BEFORE,
    PROP_RUN_STOPPED_DETAIL,
    RUN_STOPPED_CANCELLED,
    RUN_STOPPED_EMPTY_DOMAIN,
    RUN_STOPPED_REASONS,
    capacity_instance_iri,
    datastate_instance_iri,
    datastate_instance_root_iri,
    run_stopped_iri,
)

from .mm import MentalModel

#: Role prefix for a per-``(request_id, pipeline_run_ref)`` capacity instance graph
#: (D-A). One graph per run replaces the origin slice's two shared fixed-role
#: graphs, giving replan a fresh instance space and Slice-B persistence a single
#: per-run object to take.
RUN_GRAPH_ROLE_PREFIX = "capacity:run:"

_PIPELINERUN_PREFIX = "pipelinerun:"


def run_graph_role(request_id: str, pipeline_run_ref: str) -> str:
    """Deterministic role for a run's instance graph.

    Same ``(request_id, pipeline_run_ref)`` → same role (so a run's writer finds its
    own graph); different runs → different roles (replan / concurrent isolation).
    The ``pipelinerun:`` prefix is stripped and any remaining ``:`` folded to
    ``-`` for a clean role token.
    """
    if not isinstance(request_id, str) or not request_id:
        raise ValueError(f"request_id must be a non-empty string, got {request_id!r}")
    if not isinstance(pipeline_run_ref, str) or not pipeline_run_ref:
        raise ValueError(
            f"pipeline_run_ref must be a non-empty string, got {pipeline_run_ref!r}"
        )
    run = pipeline_run_ref
    if run.startswith(_PIPELINERUN_PREFIX):
        run = run[len(_PIPELINERUN_PREFIX):]
    run = run.replace(":", "-")
    return f"{RUN_GRAPH_ROLE_PREFIX}{request_id}:{run}"


class CapacityMMWriter:
    """Writes one pipeline run's grounding DAG into a single per-run graph in
    ``mm.capacity_mm``.

    One per pipeline run. :attr:`index` maps a DataState *type* IRI to the
    *instance* IRI currently carrying its value, so a downstream consumer's
    CONSUMES edge points at the producing instance.
    """

    def __init__(self, mm: MentalModel, request_id: str, pipeline_run_ref: str) -> None:
        self._mm = mm
        self._request_id = request_id
        self._run_ref = pipeline_run_ref
        self._graph_role = run_graph_role(request_id, pipeline_run_ref)
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
            inst = datastate_instance_root_iri(raw_task_datastate_iri, self._request_id)
            self._run_graph().add_node(
                value=value,
                type_name=NODE_TYPE_DATASTATE_INSTANCE,
                properties={PROP_DATASTATE_INSTANCE_TYPE: raw_task_datastate_iri},
                node_id=inst,
            )
            self.index[raw_task_datastate_iri] = inst
            return inst

    def manifest(
        self,
        *,
        declared_starts: Mapping[str, Optional[str]],
        capacity_phrases: Mapping[str, str],
        case_label: Optional[str] = None,
        member_graph_ids: Optional[Iterable[str]] = None,
    ) -> str:
        """Mint this run's manifest node — the three things the run's own
        nodes cannot say about it.

        **Minted before anything else, including before the route is found.**
        That ordering is the whole point: ``execution.run`` raises
        ``LeafPipelineNotFound`` out of ``_compose_pipeline`` and writes
        nothing, so an unroutable request had no graph at all — not even a
        ``RunStopped``. With the manifest minted first, every run leaves a
        graph, and run 4 of ``DECISION_RECORDS_V0_PLAN.md`` becomes
        renderable without a caller-supplied grounding root (item 4a, which
        this absorbs).

        ``declared_starts`` maps each start's DataState IRI to its **registered
        phrase**, not to nothing. Bare IRIs were the first version and they
        printed straight onto the no-route page, where the starts are the only
        thing there is to say — a G6 leak on the one page with nothing else on
        it. The mapping is what makes a **parentless ``DataStateInstance``
        decidable**: inside the set it is a premise the
        run was given, outside it, a gap where a producer should have been.
        Without it a renderer prints a deleted conclusion as a premise —
        observed, not theorised (guard **G2**).

        ``capacity_phrases`` maps capacity IRI → its registered
        ``printable_phrase`` (ADR-0207 amendment 1), for exactly the
        capacities this run composed. **A snapshot, deliberately.** That
        amendment rejects reading the phrase from the catalog at render
        time: the catalog is mutable and separately persisted, so an
        archived Episode would render prose that has since changed with no
        drift signal. Empty when no route was found — there is nothing to
        name.

        The stop-reason phrases are written unconditionally from the closed
        core set, because whether the run will stop is not known here and a
        renderer must never translate a token itself.

        ``member_graph_ids`` (ADR-0201 amendment 5) is supplied on a FOLD
        run only: the ordered ``graph_id`` of each map member's grounding
        graph, in member order, so a reader correlates member <-> verdict by
        position instead of by verdict-value equality (which two identical
        refusals defeat). ``None`` — every non-fold caller — means the key is
        ABSENT, which a reader must distinguish from an empty list: an empty
        list is a fold over zero members (its run stops ``empty_domain``); an
        absent key is not a fold this writer was told about.

        Everything lives in the node's **value**, as a dict:
        ``Graph.add_node`` validates ``properties`` as primitives only, and
        all the fields are collections.
        """
        with self._mm.lock.write_locked():
            graph = self._run_graph()
            value = {
                MANIFEST_DECLARED_STARTS: dict(declared_starts),
                MANIFEST_CAPACITY_PHRASES: dict(capacity_phrases),
                MANIFEST_STOP_REASON_PHRASES: dict(RUN_STOPPED_PHRASES),
                MANIFEST_CASE_LABEL: case_label,
            }
            if member_graph_ids is not None:
                value[MANIFEST_MEMBER_GRAPH_IDS] = [
                    str(gid) for gid in member_graph_ids
                ]
            return graph.add_node(
                value=value,
                type_name=NODE_TYPE_RUN_MANIFEST,
                node_id=run_manifest_iri(self._request_id, self._run_ref),
            ).node_id

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
                capacity_iri, self._request_id, self._run_ref,
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

    def record_stopped(
        self,
        capacity_iri: str,
        input_datastate_iris: Iterable[str],
        reason: str,
        detail: Optional[str] = None,
    ) -> str:
        """Record a run that stopped **at an invocation that happened** (L-2).

        For the two non-success returns where the body actually ran: it raised
        (``step_failed``) or it deliberately asked (``needs_input``, ADR-0196).
        Mints the :data:`NODE_TYPE_CAPACITY_INSTANCE` and its CONSUMES edges
        exactly as :meth:`record` does — the invocation is real and belongs in
        the graph — then mints the terminal :data:`NODE_TYPE_RUN_STOPPED` node
        and wires ``RunStopped --STOPPED_AT--> CapacityInstance``.

        **No DataStateInstance and no PRODUCES**: the step produced nothing.
        The CONSUMES edges are the load-bearing part — they are what hangs the
        stop off the values that led to it, which is what makes a refusal
        renderable at all rather than a bare "something failed".

        Returns the RunStopped IRI. Use :meth:`record_cancelled` when the step
        never dispatched.
        """
        if reason not in RUN_STOPPED_REASONS:
            raise ValueError(
                f"unknown run-stopped reason {reason!r}; "
                f"expected one of {sorted(RUN_STOPPED_REASONS)}"
            )
        if reason == RUN_STOPPED_CANCELLED:
            raise ValueError(
                "use record_cancelled() for a cancellation: the step never "
                "dispatched, so minting a CapacityInstance would claim a "
                "capacity executed when it did not"
            )
        if reason == RUN_STOPPED_EMPTY_DOMAIN:
            raise ValueError(
                "use record_empty_domain() for an empty fold domain: the "
                "reducer never dispatched, so minting a CapacityInstance "
                "would claim a capacity executed when it did not"
            )
        with self._mm.lock.write_locked():
            graph = self._run_graph()
            cap_inst = capacity_instance_iri(
                capacity_iri, self._request_id, self._run_ref,
                self._next_seq(f"cap:{capacity_iri}"),
            )
            cap_node = graph.add_node(
                value=capacity_iri,
                type_name=NODE_TYPE_CAPACITY_INSTANCE,
                properties={PROP_CAPACITY_INSTANCE_TYPE: capacity_iri},
                node_id=cap_inst,
            )
            for in_iri in input_datastate_iris:
                producer = self.index.get(in_iri)
                if producer is not None:
                    graph.add_edge(graph.nodes[producer], cap_node, EDGE_CONSUMES)
            stop_node = self._mint_run_stopped(graph, reason, detail)
            graph.add_edge(stop_node, cap_node, EDGE_STOPPED_AT)
            return stop_node.node_id

    def record_cancelled(
        self, before_capacity_iri: Optional[str] = None, detail: Optional[str] = None
    ) -> str:
        """Record a run cancelled **before a step dispatched** (L-2).

        Deliberately NOT a mode of :meth:`record_stopped`. The cancel check in
        ``execute_pipeline`` runs *before* ``dispatcher.dispatch``, so no
        invocation occurred: this mints the terminal
        :data:`NODE_TYPE_RUN_STOPPED` node **alone**, with no CapacityInstance
        and no ``STOPPED_AT`` edge, carrying the capacity it stopped before as
        :data:`PROP_RUN_STOPPED_BEFORE`.

        Hiding that behind an ``invoked=False`` flag would put a node in the
        grounding graph for a capacity that never ran, which is the exact class
        of claim guard G3 exists to refuse.
        """
        with self._mm.lock.write_locked():
            graph = self._run_graph()
            node = self._mint_run_stopped(
                graph, RUN_STOPPED_CANCELLED, detail,
                extra={PROP_RUN_STOPPED_BEFORE: before_capacity_iri}
                if before_capacity_iri else None,
            )
            return node.node_id

    def record_empty_domain(
        self, before_capacity_iri: Optional[str] = None, detail: Optional[str] = None
    ) -> str:
        """Record a fold run stopped because its domain was EMPTY (ADR-0201
        amendment 5): the collection to decide from had no members, so the
        reducer was never dispatched.

        Same shape as :meth:`record_cancelled`, for the same G3 reason: no
        invocation occurred, so this mints the terminal
        :data:`NODE_TYPE_RUN_STOPPED` node **alone** — no CapacityInstance, no
        ``STOPPED_AT`` edge — carrying the reducer it stopped before as
        :data:`PROP_RUN_STOPPED_BEFORE`. Deliberately its own method rather
        than a mode of either neighbour: :meth:`record_stopped` refuses this
        reason (it would mint a false invocation), and a cancellation is a
        different fact (someone chose to stop; here there was nothing to
        decide from).

        ``detail`` is prose-by-contract (S-3): it renders on the page, so it
        must carry no IRI and no internal ref — name the emptiness in words,
        not the DataState that was empty.
        """
        with self._mm.lock.write_locked():
            graph = self._run_graph()
            node = self._mint_run_stopped(
                graph, RUN_STOPPED_EMPTY_DOMAIN, detail,
                extra={PROP_RUN_STOPPED_BEFORE: before_capacity_iri}
                if before_capacity_iri else None,
            )
            return node.node_id

    def _mint_run_stopped(self, graph, reason: str, detail, extra=None):
        """Mint the run's single terminal node. Caller holds the write lock.

        The node's ``value`` is the reason **token**, a primitive — so the
        Slice-B persister's default encoder takes it unchanged (it dispatches
        only on ``DataStateInstance``) and no persister change is needed. The
        IRI is deterministic per run, so *"exactly one RunStopped node per
        run"* is a structural assertion.
        """
        props: Dict[str, Any] = {}
        if detail is not None:
            props[PROP_RUN_STOPPED_DETAIL] = str(detail)
        if extra:
            props.update({k: v for k, v in extra.items() if v is not None})
        return graph.add_node(
            value=reason,
            type_name=NODE_TYPE_RUN_STOPPED,
            properties=props or None,
            node_id=run_stopped_iri(self._request_id, self._run_ref),
        )

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
            datastate_iri, self._request_id, self._run_ref,
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

# ── what a manifest is made of ─────────────────────────────────────────
#
# These live beside the writer rather than in the executor because both run
# paths and the no-route path need them, and duplicating them is how
# ``_run_member_pipeline`` came to have no manifest at all while
# ``_run_leaf_pipeline`` did.


def capacity_phrases(dispatcher: Any, pipeline: Any) -> Dict[str, str]:
    """Snapshot ``printable_phrase`` for every capacity this run composed.

    Resolution is **scope-correct** — ``resolve_declaration(..., session=)``,
    the call ``L4Dispatcher.dispatch`` itself uses. ``get_declaration`` is
    sessionless and Global-only *by design*, and a consumer's capacities are
    routinely Local, so it would return nothing for exactly the runs this
    serves.

    A capacity with no declared phrase is simply absent: the field is optional
    (ADR-0207 am-1) and a renderer that finds no phrase must say so rather than
    invent one. Same for a declaration that will not resolve — the manifest is a
    snapshot of what was knowable when the run started, never a place to guess.
    """
    phrases: Dict[str, str] = {}
    layer = getattr(dispatcher, "capacity_layer", None)
    if layer is None:
        return phrases
    session = getattr(dispatcher, "session", None)
    for step in getattr(pipeline, "steps", ()) or ():
        iri = getattr(step, "capacity_iri", None)
        if not iri or iri in phrases:
            continue
        try:
            declaration = layer.resolve_declaration(iri, session=session)
        except Exception:  # noqa: BLE001 — an unresolvable name is not a phrase
            continue
        phrase = getattr(declaration, "printable_phrase", "")
        if phrase:
            phrases[iri] = phrase
    return phrases


def start_phrases(dispatcher: Any, start_iris: Iterable[str]) -> Dict[str, Optional[str]]:
    """Snapshot each start's registered ``description``, Local before Global.

    Local first for the same reason ``resolve_declaration`` is scope-correct: a
    consumer's own DataStates are Local, and a Global-only read would return
    nothing for them.

    **A start with no description maps to ``None``, never to its own IRI.** The
    IRI was the first version of this fallback and it was wrong for the reason
    the whole mapping exists: bare IRIs printing onto the page is the leak this
    replaced, and a fallback that re-inserts them puts the leak back on exactly
    the runs that have no prose to dilute it. ``None`` cannot leak, and it is
    unambiguous — a renderer reads "given, and we have no words for it", which
    it must say rather than paper over. The **key is still present**, which is
    what matters structurally: the start stays inside the declared set, so a
    parentless instance is still decidable as a premise rather than a gap.
    """
    out: Dict[str, Optional[str]] = {}
    layer = getattr(dispatcher, "capacity_layer", None)
    views = []
    if layer is not None:
        session = getattr(dispatcher, "session", None)
        user_id = getattr(session, "user_id", None)
        try:
            if user_id and layer.has_local(user_id):
                views.append(layer.local_view(user_id))
            views.append(layer.global_view())
        except Exception:  # noqa: BLE001 — a view we cannot build is no phrase
            views = []
    for iri in start_iris:
        phrase = None
        for view in views:
            node = view.get_datastate(iri)
            if node is not None:
                phrase = (node.properties or {}).get("description") or None
                break
        out[iri] = phrase
    return out
