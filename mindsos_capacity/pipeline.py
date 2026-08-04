"""Pipeline-finder seam + DAG result type (ADR-0071 + §amendment-2).

L3 owns the ``Finder`` **interface** plus each concrete **algorithm**
(BFS, conjunction/fold) — they are computation, and ``find_pipeline``
already lives at L3. *Which* strategy fires is an **L4** selection
policy (ADR-0071 §amendment-2). No L4 "real finder" exists to extend
(``plan_construction.py`` is a v0 stub), so the conjunction finder is
net-new at L3.

**Result is a converging DAG, the type ``Pipeline``** (named
``PipelineDAG`` through Slice 1; the "DAG" suffix was a migration-only
marker and has been dropped — the converging plan *is* the pipeline).
The earlier *linear* pipeline type (``Pipeline`` + ``PipelineStep``)
retired here could not represent a converging hyperpath (a capacity
consuming several inputs each produced by a different upstream path, or
a fold over N producers of one type). The replacement was safe — the
linear type had **zero production consumers** (verified: no
L4/Server/L2/L0 import; the L5-chain ``Pipeline`` in
``chain_artifacts.py`` is an unrelated dataclass; the L2
``promoted_pipelines`` schema has no live writer).

**Two real strategies ship** (so the seam is not premature):

* :class:`BFSFinder` — the original ADR-0071 shortest-by-capacity-count
  walk, re-expressed to emit a *degenerate-linear* ``Pipeline``
  (ADR-0071 §am-2 PB-F). Single-input semantics retained: it fires a
  capacity off **one** reachable input (the ``via`` datastate) and does
  not resolve the capacity's other declared inputs — that latent
  multi-input unsoundness is exactly what the conjunction finder fixes.
* :class:`ConjunctionFinder` — the sound multi-input finder. A backward
  hyperpath search whose per-capacity resolution is driven **per typed
  input-group** (``_CapacityBase.input_group``, ADR-0159 §amendment-1):
  ``all_required`` (AND over inputs), ``any_of`` (optional-union), or
  ``fold`` (aggregate over **all** producers of an input) — each crossed
  with **OR over the producers** of a consumed DataState. Reads the
  input-group from the **declaration registry** (Decision 8 — no graph
  hyperedge at v1), mirroring ``views.inputs_of``'s declaration-primary
  read.

**Constraints are deliberately ignored** at this layer per ADR-0071;
L4 does the post-hoc filtering pass via ``iter_constraints``.

**Deferred (consumer discipline):** the promoted-path-lookup strategy
(``promoted-pipelines`` has no writer — verified) and the *graph* form of
the input-group (a type-layer typed hyperedge + a hyperedge-aware view
walk, ADR-0156 §am) are out of scope until their consumers land.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    Deque,
    Dict,
    FrozenSet,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
)

from .identifiers import (
    INPUT_GROUP_ALL_REQUIRED,
    INPUT_GROUP_ANY_OF,
    INPUT_GROUP_FOLD,
)
from .types import SessionArg

if TYPE_CHECKING:  # pragma: no cover — circular-import guard
    from .capacity_layer import CapacityLayer
    from .views import CapacityLayerView


# ── DAG result type (ADR-0071 §amendment-2, part 4) ───────────────────

#: Edge ``producer`` sentinel: the datastate is a *start* datastate
#: (an available input to the whole pipeline), not the output of a step.
START: int = -1


@dataclass(frozen=True)
class DAGStep:
    """One capacity invocation (a node in the pipeline DAG).

    Attributes:
        capacity_iri: The capacity to run at this step.
        input_datastates: DataState IRIs the capacity consumes (its full
            declared input set — the finder records *all* of them, even
            for ``BFSFinder`` where only the ``via`` input is wired).
        output_datastates: DataState IRIs the capacity produces.
    """

    capacity_iri: str
    input_datastates: Tuple[str, ...]
    output_datastates: Tuple[str, ...]


@dataclass(frozen=True)
class DAGEdge:
    """A dataflow edge in the pipeline DAG.

    ``datastate`` produced by step index ``producer`` (or :data:`START`
    when it is a start datastate) is consumed by step index ``consumer``.
    A ``fold`` consumer has several edges sharing one ``datastate`` with
    distinct ``producer`` indices (fan-in); a converging consumer has
    edges with distinct ``datastate`` values.
    """

    producer: int
    consumer: int
    datastate: str


@dataclass(frozen=True)
class Pipeline:
    """A converging capacity DAG producing ``target_datastate`` from the
    available ``start_datastates``.

    ``steps`` are **topologically ordered**: every step appears after the
    steps that produce its consumed inputs. An empty ``steps`` tuple means
    the target is already among ``start_datastates`` (no-op).

    ``__iter__`` / ``__len__`` range over ``steps`` so callers that
    treated the retired linear pipeline type as a step sequence keep
    working. (This type was named ``PipelineDAG`` through Slice 1; the
    "DAG" suffix was a migration-only marker and has been dropped.)
    """

    start_datastates: Tuple[str, ...]
    target_datastate: str
    steps: Tuple[DAGStep, ...]
    edges: Tuple[DAGEdge, ...] = ()

    def __iter__(self):
        return iter(self.steps)

    def __len__(self) -> int:
        return len(self.steps)

    # ── serialization (composite-persistence residual, ADR-0182 codec) ──

    def to_dict(self) -> Dict[str, Any]:
        """Plain-``dict`` form for the ``learned-parameters`` descriptor.

        Round-trips through the ADR-0182 node-value codec (lists +
        primitives only). See :meth:`from_dict`.
        """
        return {
            "start_datastates": list(self.start_datastates),
            "target_datastate": self.target_datastate,
            "steps": [
                {
                    "capacity_iri": s.capacity_iri,
                    "input_datastates": list(s.input_datastates),
                    "output_datastates": list(s.output_datastates),
                }
                for s in self.steps
            ],
            "edges": [
                {
                    "producer": e.producer,
                    "consumer": e.consumer,
                    "datastate": e.datastate,
                }
                for e in self.edges
            ],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Pipeline":
        """Rebuild a :class:`Pipeline` from its :meth:`to_dict` form."""
        return cls(
            start_datastates=tuple(data["start_datastates"]),
            target_datastate=data["target_datastate"],
            steps=tuple(
                DAGStep(
                    capacity_iri=s["capacity_iri"],
                    input_datastates=tuple(s["input_datastates"]),
                    output_datastates=tuple(s["output_datastates"]),
                )
                for s in data["steps"]
            ),
            edges=tuple(
                DAGEdge(
                    producer=e["producer"],
                    consumer=e["consumer"],
                    datastate=e["datastate"],
                )
                for e in data.get("edges", ())
            ),
        )


# ── view resolution shared by the strategies ─────────────────────────


# ── find verdict (CORE-C3R1 / shim S4; ADR-0206 §3) ───────────────────

#: BFS exhausted the frontier without reaching the target.
FIND_BFS_EXHAUSTED = "bfs_exhausted"
#: No producer of the target is satisfiable from the start set (phase 1).
FIND_NO_SATISFIABLE_PRODUCER = "no_satisfiable_producer"
#: Construction recursed past ``max_depth``.
FIND_MAX_DEPTH_EXCEEDED = "max_depth_exceeded"
#: An ``all_required`` input of a selected capacity cannot be produced.
FIND_REQUIRED_INPUT_UNPRODUCIBLE = "required_input_unproducible"
#: The target IRI is not registered. Never raised by a finder — the views
#: return ``[]`` for an unknown IRI and never raise — but callers that do
#: check need a reason to name.
FIND_UNREGISTERED_TARGET = "unregistered_target"

#: The closed set. Consumers branch on ``reason``; nothing parses ``detail``.
FIND_REASONS: FrozenSet[str] = frozenset(
    {
        FIND_BFS_EXHAUSTED,
        FIND_NO_SATISFIABLE_PRODUCER,
        FIND_MAX_DEPTH_EXCEEDED,
        FIND_REQUIRED_INPUT_UNPRODUCIBLE,
        FIND_UNREGISTERED_TARGET,
    }
)


class _FindAbort(Exception):
    """Internal unwind for ``ConjunctionFinder.find``. Never escapes.

    ``fire`` is recursive and used a raise to unwind. Threading an optional
    return through every recursion step would change the algorithm; raising a
    private exception and converting it to a :class:`FindVerdict` at the method
    boundary keeps the conversion **faithful** — no new checks, no new failure
    modes, identical control flow. This class is not exported and no consumer
    can catch it.
    """

    def __init__(self, reason: str, detail: str, unproducible=None) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail
        self.unproducible = unproducible or {}


@dataclass(frozen=True)
class FindVerdict:
    """What a finder answers: a route, or an honest don't-know.

    Replaces ``PipelineNotFoundError`` (shim **S4**). No-route is a verdict
    about the world, not a technical failure, so it is returned rather than
    raised (ADR-0206 §3).

    Attributes:
        pipeline: the DAG, or ``None`` when no route was found.
        reason: one of :data:`FIND_REASONS`, or ``None`` when found. A
            **closed set** — consumers branch on it, and the dream must not
            parse English.
        detail: human-readable, for logs and CLI output. Never parsed.
        unproducible: **grouped** ``capacity_iri -> (datastate_iri, ...)``.
            The capacity is the grouping key that separates AND from OR:
            one capacity short of two DataStates needs **both**; two
            capacities each short of one are **alternatives**. A flat list
            of pairs cannot express that. Empty unless ``reason`` is
            :data:`FIND_REQUIRED_INPUT_UNPRODUCIBLE`.

    **No ``__bool__``** (CR §4). A result type meaning "found or not" invites
    ``if verdict:`` and a silent wrong branch. Use :attr:`found`, or
    ``verdict.pipeline is None``. Note the residual hazard this leaves: with
    no ``__bool__`` a dataclass is *always* truthy, so ``if verdict:`` still
    reads as success. The guard is review, not the type.

    Reasons retiring: :data:`FIND_BFS_EXHAUSTED` goes with ``BFSFinder`` and
    :data:`FIND_MAX_DEPTH_EXCEEDED` goes with ``max_depth``, both at the
    Capacity Graph Traversal rewrite (`CORE_CAPACITY_GRAPH_TRAVERSAL.md`).
    The end state is two reasons: target unreachable, target unregistered.
    """

    pipeline: Optional[Pipeline] = None
    reason: Optional[str] = None
    detail: str = ""
    unproducible: Mapping[str, Tuple[str, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "unproducible", MappingProxyType(dict(self.unproducible))
        )

    @property
    def found(self) -> bool:
        """True when a route was found."""
        return self.pipeline is not None



def _view_for(
    capacity_layer: "CapacityLayer", session: SessionArg
) -> "CapacityLayerView":
    """Resolve the Global or per-user Local view (R3 PB-44(a) inline)."""
    target_uid = session.user_id if session is not None else None
    return (
        capacity_layer.global_view()
        if target_uid is None
        else capacity_layer.local_view(target_uid)
    )


def _input_group_of(capacity_layer: "CapacityLayer", capacity_iri: str) -> str:
    """Read a capacity's ``input_group`` from the declaration registry.

    Decision 8: the finder reads the declaration, not the graph. Defaults
    to ``all_required`` when no declaration is registered (a graph-only
    node, e.g. a bare reference) — the sound-composer default.
    """
    try:
        decl = capacity_layer.get_declaration(capacity_iri)
    except Exception:  # noqa: BLE001 — missing declaration → default
        return INPUT_GROUP_ALL_REQUIRED
    return getattr(decl, "input_group", INPUT_GROUP_ALL_REQUIRED)


# ── Finder interface (ADR-0071 §amendment-2, part 1) ──────────────────


class Finder(ABC):
    """An L3 pipeline-finder strategy.

    The algorithm is L3 (computation); *which* strategy fires is an L4
    selection policy. Every strategy returns a :class:`FindVerdict` — a route
    or an honest don't-know. No strategy raises for "no route" (shim S4).
    """

    @abstractmethod
    def find(
        self,
        capacity_layer: "CapacityLayer",
        *,
        session: SessionArg = None,
        start_datastates: Tuple[str, ...],
        target_datastate: str,
        max_depth: int = 8,
    ) -> "FindVerdict":
        """Return a :class:`FindVerdict` for ``target_datastate`` from
        ``start_datastates``."""
        raise NotImplementedError


# ── BFS strategy (original ADR-0071; degenerate-linear DAG, PB-F) ──────


class BFSFinder(Finder):
    """Shortest-by-capacity-count forward walk → degenerate-linear DAG.

    Identical reachability to the Phase 30/42 BFS: frontier is keyed on
    DataState IRIs; ``consumers_of`` advances by CONSUMES, ``outputs_of``
    by PRODUCES (ADR-0156). It fires each capacity off the **single**
    ``via`` datastate it arrived on and wires only that one input — the
    capacity's other declared inputs are recorded on the
    :class:`DAGStep` but left unwired. That single-input composition is
    the latent unsoundness :class:`ConjunctionFinder` exists to fix.
    """

    def find(
        self,
        capacity_layer: "CapacityLayer",
        *,
        session: SessionArg = None,
        start_datastates: Tuple[str, ...],
        target_datastate: str,
        max_depth: int = 8,
    ) -> FindVerdict:
        view = _view_for(capacity_layer, session)

        if target_datastate in set(start_datastates):
            return FindVerdict(
                pipeline=Pipeline(
                    start_datastates=tuple(start_datastates),
                    target_datastate=target_datastate,
                    steps=(),
                    edges=(),
                )
            )

        # Queue entries: (current_ds, steps, edges, producer_idx_of_current_ds)
        Entry = Tuple[str, Tuple[DAGStep, ...], Tuple[DAGEdge, ...], int]
        queue: Deque[Entry] = deque()
        visited: Set[str] = set()
        for sds in start_datastates:
            queue.append((sds, (), (), START))
            visited.add(sds)

        while queue:
            current_ds, steps, edges, prod_idx = queue.popleft()
            if len(steps) >= max_depth:
                continue
            for cap in view.consumers_of(current_ds):
                cap_iri = cap.node_id
                outputs = tuple(view.outputs_of(cap_iri))
                new_idx = len(steps)
                new_step = DAGStep(
                    capacity_iri=cap_iri,
                    input_datastates=tuple(view.inputs_of(cap_iri)),
                    output_datastates=outputs,
                )
                new_steps = steps + (new_step,)
                new_edges = edges + (
                    DAGEdge(producer=prod_idx, consumer=new_idx, datastate=current_ds),
                )
                for out in outputs:
                    if out == target_datastate:
                        return FindVerdict(
                            pipeline=Pipeline(
                                start_datastates=tuple(start_datastates),
                                target_datastate=target_datastate,
                                steps=new_steps,
                                edges=new_edges,
                            )
                        )
                    if out not in visited:
                        visited.add(out)
                        queue.append((out, new_steps, new_edges, new_idx))

        return FindVerdict(
            reason=FIND_BFS_EXHAUSTED,
            detail=(
                f"No pipeline found from {list(start_datastates)!r} to "
                f"{target_datastate!r} (max_depth={max_depth})"
            ),
        )


# ── Conjunction/fold strategy (ADR-0071 §am-2 part 2; ADR-0159 §am-1) ──


class ConjunctionFinder(Finder):
    """Sound multi-input finder over the typed input-groups.

    Backward hyperpath search from ``target_datastate``. To produce a
    datastate the finder selects a producer capacity (**OR over
    producers** — deterministic first-by-IRI; no backtracking on a deep
    failure at v1, ARC's three cases are unambiguous), then resolves that
    capacity's declared inputs by its ``input_group``:

    * ``all_required`` — every input must be producible (AND); one edge
      per input from the chosen upstream producer.
    * ``any_of`` — at least one input must be producible (optional-union);
      edges only for the producible inputs.
    * ``fold`` — each input is fanned-in from **all** of its satisfiable
      producers (aggregate); one edge per producer.

    A two-phase design avoids partial-DAG leaks: a pure reachability
    check (``ds_reachable`` / ``cap_satisfiable``) runs first, then
    ``fire`` only constructs over admissible producers. Shared upstream
    producers fire once (memoised), so diamonds and folds converge to a
    single step.

    ----

    **RATIONALE RECORD — two cycle guards in phase 2** (CORE-C3R1,
    ADR-0071 §am-2, ADR-0205 §1 "each level is verified by the level
    below"). *Read this before changing* :func:`eligible` *or* :func:`fire`.

    *What changed, conceptually.* This class makes the same claim at two
    resolutions — "a route exists" (phase 1) and "here is the route"
    (phase 2) — so the two phases must agree. They did not.

    **D-B.** Phase 1 threads a cycle ``stack`` and refuses to rely on a
    DataState producing itself. Phase 2 re-tested producers with an
    **empty** stack, so a producer phase 1 had refused could still be
    selected during construction, including to feed itself. Composition
    was **non-monotonic in the start set**: adding an available input
    could make a compose *fail*. Fixed by threading the live stack into
    ``fire`` and admitting producers only through :func:`eligible`.

    **D-E.** The ``fired`` memo is written *after* a capacity's inputs are
    built, so during ``fire(c)`` the capacity ``c`` is in neither ``fired``
    nor the DataState stack — the stack tracks DataStates under
    resolution, not capacities under construction. A capacity could
    therefore be selected to produce one of its own transitive inputs
    while still being built, and either recurse to ``max_depth`` **or
    complete and be appended to** ``steps`` **twice**. The second outcome
    returned a ``Pipeline`` naming one capacity as two distinct steps with
    no error; ``execute_pipeline`` then ran it twice and, because the
    blackboard holds one value per DataState IRI, the second run silently
    overwrote the first. **D-B raises; D-E lied.** Fixed by the
    ``in_flight`` set.

    *Evidence, not argument.*
    ``confirmation_docs/finder_variants_model.py`` reproduces both phases
    exactly and swaps only the phase-2 admission rule. Over 20,000
    generated capacity graphs: shipped-with-empty-stack and
    threaded-stack-alone leave **369 max_depth blowups + 20 duplicate-step
    pipelines**; with the ``in_flight`` guard, **0 and 0**. The three
    conformance shapes (``all_required`` AND, diamond convergence, fold
    fan-in) are byte-identical across all variants.

    *What was rejected.* (a) Guarding in phase 1 only — phase 2 is where
    the DAG is built, so the leak is there. (b) Treating the ``fired``
    short-circuit in :func:`eligible` as a correctness clause — measured
    identical with and without it in all 20,000 graphs; it is a cost
    optimisation and is documented as one. (c) Parameterising ``max_depth``
    per map spec (the prior CR's D10) — superseded; see below.

    *What a subsystem must do differently.* Nothing is added to any
    capacity declaration. Catalogs that composed only because of the leak
    will now report the input as unproducible, which is the honest answer.
    nilm and arc1 should run the divergence sweep
    (``mindsos_capacity.catalog_check``) over their own catalogs before
    declaring a ``shared_inputs`` map.

    *Where this is going.* This is a **patch, not the design.** Both
    defects exist because the walk is a top-down recursion that needs
    ad-hoc guards. The agreed replacement computes reachability
    **bottom-up as a fixpoint** across four dispatched capacities
    (``path-finding.reachable_strata`` → ``path-finding.producer_candidates``
    → ``decision.select_producers`` → ``path-finding.construct_dag``),
    which makes both defects impossible by construction and retires the
    cycle stack, ``in_flight`` **and** ``max_depth``. ``BFSFinder`` is
    deleted there and BFS becomes a ``selection_policy`` value. The tests
    guarding this patch assert behaviour, not implementation, and are that
    rewrite's acceptance bar. Spec:
    ``confirmation_docs/CORE_CR_FINDER_AS_CAPACITIES.md`` — §8 lists eight
    already-rejected alternatives; read it before proposing a ninth.

    *ADRs.* Amends **ADR-0071 §am-2** (§am-3, this change). Supersedes the
    fix shape in ``CORE_CR_FINDER_CYCLE_SOUNDNESS.md``; its D8, D9 and D11
    stand, D10 is retired with ``max_depth``.
    """

    def find(
        self,
        capacity_layer: "CapacityLayer",
        *,
        session: SessionArg = None,
        start_datastates: Tuple[str, ...],
        target_datastate: str,
        max_depth: int = 8,
    ) -> FindVerdict:
        view = _view_for(capacity_layer, session)
        starts: FrozenSet[str] = frozenset(start_datastates)

        if target_datastate in starts:
            return FindVerdict(
                pipeline=Pipeline(
                    start_datastates=tuple(start_datastates),
                    target_datastate=target_datastate,
                    steps=(),
                    edges=(),
                )
            )

        # ── phase 1: reachability (no mutation) ──
        def ds_reachable(ds: str, stack: FrozenSet[str]) -> bool:
            if ds in starts:
                return True
            if ds in stack:  # cycle — cannot rely on producing self
                return False
            nxt = stack | {ds}
            return any(
                cap_satisfiable(cap.node_id, nxt) for cap in view.producers_of(ds)
            )

        def cap_satisfiable(cap_iri: str, stack: FrozenSet[str]) -> bool:
            inputs = view.inputs_of(cap_iri)
            if not inputs:
                return True
            mode = _input_group_of(capacity_layer, cap_iri)
            if mode == INPUT_GROUP_ANY_OF:
                return any(ds_reachable(ds, stack) for ds in inputs)
            # all_required and fold both need every declared input producible
            return all(ds_reachable(ds, stack) for ds in inputs)

        if not any(
            cap_satisfiable(cap.node_id, frozenset())
            for cap in view.producers_of(target_datastate)
        ):
            return FindVerdict(
                reason=FIND_NO_SATISFIABLE_PRODUCER,
                detail=(
                    f"No pipeline found to {target_datastate!r} from "
                    f"{list(start_datastates)!r} (no satisfiable producer)"
                ),
            )

        # ── phase 2: construct over satisfiable producers ──
        steps: List[DAGStep] = []
        edges: List[DAGEdge] = []
        fired: Dict[str, int] = {}  # capacity_iri -> step index
        #: Capacities whose ``fire`` call has started but not finished. The
        #: ``fired`` memo cannot serve this purpose: it is written *after*
        #: construction, so during ``fire(c)`` the capacity ``c`` is in
        #: neither map and is invisible to both guards. That is D-E.
        in_flight: Set[str] = set()

        def eligible(cap_iri: str, stack: FrozenSet[str]) -> bool:
            """Phase-2 producer admission — both cycle guards.

            Three clauses:

            * **in flight** — a capacity whose ``fire`` has started and not
              returned is refused outright. Without this a capacity can be
              selected to produce one of its own transitive inputs while it
              is still being built; ``fired`` does not stop it, because the
              memo is written only on the way *out* of ``fire``. This is the
              **D-E** guard and it is the one the cycle ``stack`` cannot
              cover: the stack tracks DataStates under resolution, not
              capacities under construction.
            * **already fired** — a capacity with a step index has a
              materialised subtree built from starts and concrete producers,
              so it is admissible and reuses its step. This clause is a
              **cost optimisation, not a correctness clause** — measured over
              20,000 generated graphs, results are identical with and without
              it (``confirmation_docs/finder_variants_model.py``). It is kept
              because it skips a full reachability walk per already-built
              producer, and because it makes the memo's authority explicit.
            * **satisfiable under the live stack** — otherwise fall through to
              phase 1's own predicate, with the *current* cycle stack rather
              than the empty one the pre-fix code passed. This is the **D-B**
              guard.
            """
            if cap_iri in in_flight:
                return False
            return cap_iri in fired or cap_satisfiable(cap_iri, stack)

        def fire(cap_iri: str, depth: int, stack: FrozenSet[str]) -> int:
            if cap_iri in fired:
                return fired[cap_iri]
            if depth > max_depth:
                raise _FindAbort(
                    FIND_MAX_DEPTH_EXCEEDED,
                    f"max_depth={max_depth} exceeded resolving {cap_iri!r}",
                )
            in_flight.add(cap_iri)
            inputs = tuple(view.inputs_of(cap_iri))
            outputs = tuple(view.outputs_of(cap_iri))
            mode = _input_group_of(capacity_layer, cap_iri)
            incoming: List[Tuple[int, str]] = []
            for ds in inputs:
                if ds in starts:
                    incoming.append((START, ds))
                    continue
                # Mirror phase 1's ``ds_reachable``: ``ds`` joins the stack
                # before its producers are tested, so a producer that can
                # only be reached back through ``ds`` is refused instead of
                # being admitted to feed itself.
                nxt = stack | {ds}
                producers = sorted(
                    view.producers_of(ds), key=lambda n: n.node_id
                )
                satisfiable = [p for p in producers if eligible(p.node_id, nxt)]
                if mode == INPUT_GROUP_FOLD:
                    for p in satisfiable:  # fan-in: every producer
                        incoming.append((fire(p.node_id, depth + 1, nxt), ds))
                elif satisfiable:  # all_required / any_of: OR → first producer
                    incoming.append(
                        (fire(satisfiable[0].node_id, depth + 1, nxt), ds)
                    )
                elif mode == INPUT_GROUP_ALL_REQUIRED:
                    raise _FindAbort(
                        FIND_REQUIRED_INPUT_UNPRODUCIBLE,
                        f"required input {ds!r} of {cap_iri!r} is unproducible",
                        {cap_iri: (ds,)},
                    )
                # any_of with no producible producer for this input: skip it

            step_idx = len(steps)
            steps.append(
                DAGStep(
                    capacity_iri=cap_iri,
                    input_datastates=inputs,
                    output_datastates=outputs,
                )
            )
            fired[cap_iri] = step_idx
            # Construction finished: the capacity moves from in-flight to
            # fired in one step, so it is never in neither set. No cleanup is
            # needed on the abort paths above — every ``_FindAbort`` raised
            # inside ``fire`` unwinds to ``find``, which discards the whole
            # walk (and ``in_flight`` with it) and returns a verdict.
            in_flight.discard(cap_iri)
            for prod_idx, ds in incoming:
                edges.append(
                    DAGEdge(producer=prod_idx, consumer=step_idx, datastate=ds)
                )
            return step_idx

        target_producers = sorted(
            (
                p
                for p in view.producers_of(target_datastate)
                if cap_satisfiable(p.node_id, frozenset())
            ),
            key=lambda n: n.node_id,
        )
        # Empty initial stack, exactly as phase 1's top-level check above:
        # the target is what we are trying to *produce*, so it is not yet
        # "under resolution" and must not guard against its own producers.
        try:
            fire(target_producers[0].node_id, 0, frozenset())
        except _FindAbort as abort:
            # ``_FindAbort`` never escapes: the whole walk is discarded here,
            # which is why ``in_flight`` needs no cleanup on the abort paths.
            return FindVerdict(
                reason=abort.reason,
                detail=abort.detail,
                unproducible=abort.unproducible,
            )

        return FindVerdict(
            pipeline=Pipeline(
                start_datastates=tuple(start_datastates),
                target_datastate=target_datastate,
                steps=tuple(steps),
                edges=tuple(edges),
            )
        )


# ── back-compat free function (BFS strategy entry point) ──────────────


def find_pipeline(
    capacity_layer: "CapacityLayer",
    *,
    session: SessionArg = None,
    start_datastate: str,
    target_datastate: str,
    max_depth: int = 8,
) -> Pipeline:
    """Find the shortest capacity chain from ``start_datastate`` to
    ``target_datastate`` (the ADR-0071 BFS strategy).

    Back-compat entry point: keeps the singular ``start_datastate=``
    keyword and delegates to :class:`BFSFinder`, returning a
    degenerate-linear :class:`Pipeline`. For sound multi-input
    composition use :class:`ConjunctionFinder` directly (selected by L4).

    Returns:
        FindVerdict: the chain, or a don't-know carrying
        :data:`FIND_BFS_EXHAUSTED`.
    """
    return BFSFinder().find(
        capacity_layer,
        session=session,
        start_datastates=(start_datastate,),
        target_datastate=target_datastate,
        max_depth=max_depth,
    )


__all__ = [
    "START",
    "DAGStep",
    "DAGEdge",
    "Pipeline",
    "Finder",
    "BFSFinder",
    "ConjunctionFinder",
    "find_pipeline",
]
