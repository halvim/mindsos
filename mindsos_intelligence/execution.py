"""LifecyclePhase 3-5 — execution (DFS Milestone order, ADR-0171).

Walks the Plan's leaf Milestones in DFS order; per leaf emits a
PipelineRun and runs the leaf Pipeline.

**Two modes (out-of-CR Step 5).**

* *Notional (v0 / no solve target).* When the plan names no ``solve_target``
  (the v0 placeholder planner, and any consumer that doesn't declare one), the
  leaf has no real pipeline to run: emit a single notional StepExecutionRecord
  so the PipelineRun has provenance, and mark it completed. This is the
  byte-identical Phase-47 behaviour.
* *Real solve.* When the plan names ``solve_target`` (``{start_datastate,
  target_datastate}``) AND an ``mm`` + seed are supplied by the orchestrator,
  the leaf runs for real: the bipartite ``find_pipeline`` (ADR-0156) composes a
  Pipeline from the currently-registered capacities, and ``execute_pipeline``
  runs it — grounding the run into ``capacity_mm`` (the resolved task lands as
  the seeded start DataStateInstance; each invocation adds its grounding DAG)
  and threading the per-run graph out for Slice-B persistence. This is what
  makes the L5 capacity writer + persist non-inert (Steps 1-4 built them inert).

**Cross-milestone value bus (collection-iteration Slice 1a).**

The run holds one attempt-scoped ``blackboard`` — created here at the top of
``run`` and discarded when it returns — that threads DataState *values* across
milestones. A leaf seeds its pipeline from the blackboard (filtered to the
pipeline's ``start_datastates``) and merges its outputs back, so a downstream
stage can consume what an upstream stage produced (e.g. ``raw_task -> raw_grids``
then ``raw_grids -> ...``). Because the blackboard is created per ``run`` call,
a replan (a fresh ``run`` at the next ``run_attempt``) re-enters from clean
state — no stale reads. ``capacity_mm`` still grounds each leaf's run for audit;
the blackboard only carries the live values between stages.

A multi-stage plan names per-leaf endpoints via ``PlanResult.leaf_targets``
(``{leaf_ref: {start_datastate, target_datastate}}``); a leaf with no entry
falls back to the plan-global ``solve_target``. With a single-leaf plan and no
``leaf_targets`` (today's v0 / Step-5 path) the behaviour is byte-identical: the
sole leaf seeds from the blackboard initialised to ``solve_seed`` and merges
outputs no one reads.

**Map / fold primitive (collection-iteration Slice 1b).**

A milestone may carry a ``PlanResult.milestone_specs`` entry marking it a **map**
or a **fold** (the consumer's planner emits the shape — locked decision 3; core
provides only the kinds + executor + value bus). A map fans a uniform
sub-pipeline out over the ordered members of a collection DataState (ADR-0199 —
L4 owns the unpack loop), sequentially (v1), each member in an isolated
sub-blackboard seeded with just the member value and under a fresh per-member
run-ref (isolated grounding). It applies bounded retry (``MEMBER_RETRY_CAP``)
and — since the partial-record CR (ADR-0201 am-6) — **partial results instead
of an all-or-nothing barrier**: a member that still fails at the cap (or asks
for input, or finds no route) STOPS IN PLACE — its final attempt's graph is
retained so the page can name the stop — and its siblings run. The map writes
the completed members' ordered outputs to the blackboard plus the full member
grounding-id list; a fold over a truncated domain stops ``partial_domain``
pre-dispatch rather than concluding from less than everything. A milestone
with no spec is a plain leaf (the 1a path, unchanged).

**Nesting (collection-iteration Slice 2).**

A map's per-member work may itself be a whole sub-plan rather than a single
``find_pipeline`` leaf — and that sub-plan may itself contain a map/fold (e.g.
objects within grids within a task). A map spec carries this via an optional
``sub_plan`` key (a mini plan: ``{leaf_milestone_refs, pipeline_refs,
milestone_specs, leaf_targets?, solve_target?}``); when present, each member runs
that sub-plan in its own isolated sub-blackboard (seeded with the member value)
instead of the flat 1b leaf, and the map collects ``sub_target`` from that
sub-blackboard. When absent, the member runs the flat 1b path — byte-identical.

The milestone loop is factored into :func:`_run_milestone_sequence`, which both
``run`` (top level) and a map member (its sub-plan) invoke. Every executed leaf's
per-run ref is a **path** — ``pipelinerun:{scope}:{ref_path}[...]`` — that
accumulates a ``{milestone_idx}`` segment per level and an ``m{member_idx}``
segment per map fan-out, so a nested run's grounding graph stays isolated from
its siblings and the provenance tree (the set of per-run graphs, keyed by role)
is walkable by path. At depth 0 the path is just ``{leaf_idx}`` → the refs are
byte-identical to Slice 1a/1b. (Cross-stage grounding *continuity* — linking a
consumer's seeded start to the producer's instance across per-run graphs — is
NOT resolved here: it would reverse the Slice-A per-run-graph / intra-graph-edge
model and is deferred to its own slice. The ref-path gives isolation + a
locatable tree, not connected cross-stage edges.)

Bounded retry + partial results apply at map-member granularity at **every**
level: a nested map enforces its own retry cap over its members and stops its
own fold ``partial_domain`` when truncated; a sub-plan member whose sub-run's
terminal milestone stopped is a STOPPED member of ITS parent (minimum-viable
propagation, coordination §63 Q5 — decided from the sub-run's own record,
never from a ``None`` in the value channel). A sub-plan member itself is not
retried (retry lives at the flat find+execute leaf where transient load
failure actually occurs); a plain sub-plan stage fails soft exactly as a
top-level plain stage does (1a behaviour, unchanged).

**Multi-input members / leaves (map-member multi-input CR).**

Through Slice 3b a member's and a plain leaf's pipeline was composed with the
single-input ``find_pipeline`` (``BFSFinder``), which fires each capacity off one
``via`` datastate and leaves its other declared inputs unwired — so a member
whose work is a genuinely multi-input composed segment could not run. Two
additive spec keys lift that, and neither is read unless the plan sets it:

* ``leaf_targets[ref]["start_datastates"]`` (plural) — a leaf may declare several
  available start DataStates instead of the singular ``start_datastate``.
* a map spec's ``shared_inputs: [DataState IRI, ...]`` — values copied from the
  parent blackboard into every member's sub-blackboard alongside the member
  value, so a member capacity's non-member inputs (domain constants, or a
  per-map shared value like a query signature) have a source inside the member
  run. A declared key absent from the parent blackboard is a hard ``ValueError``
  naming the key and the map — never a silent skip, which would resurface much
  later as an opaque "required input unproducible" from the finder.

**Finder selection is derived from arity** (:func:`_select_finder`): more than
one start DataState ⇒ :class:`~mindsos_capacity.pipeline.ConjunctionFinder` (the
sound multi-input finder); exactly one ⇒ ``BFSFinder``, byte-identical to every
pre-CR path. Plural starts is a spec shape no consumer emits today, so no shipped
consumer changes behaviour. An explicit ``"finder"`` key on the leaf endpoints or
the map spec overrides the derivation; asking for ``"bfs"`` with plural starts is
a ``ValueError`` rather than a silently under-wired pipeline.

A map's member pipeline is **composed once, on the first member, and reused** for
the remaining members and retries (the starts and target are identical across
members). Composition stays lazy: an empty collection composes nothing and still
completes with an empty output list, exactly as before.

MSUR + SCMS Plan/Milestone orchestration hooks are still absent; the loop
stays sibling-sequential v1. (Unbuilt CORE work — ADR-0206, CORE-C4R4.)
"""

from __future__ import annotations

from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from mindsos_capacity.identifiers import (
    EDGE_PRODUCES,
    NODE_TYPE_DATASTATE_INSTANCE,
    PROP_DATASTATE_INSTANCE_TYPE,
    RUN_STOPPED_EMPTY_DOMAIN,
    RUN_STOPPED_PARTIAL_DOMAIN,
)

#: Slice 1b — hard cap on per-member sub-run attempts (initial + retries) inside
#: a map fan-out. Owner's call (CR §Bounded retry): 2 total attempts. A named
#: constant (mirrors ``DEFAULT_PER_TASK_REPLAN_BUDGET``), trivially tunable. A
#: member still failing (``success=False``) at the cap STOPS IN PLACE (partial
#: results, ADR-0201 am-6 — was the ∀-abort trigger).
MEMBER_RETRY_CAP = 2


def member_graph_ids_key(out_ds: str) -> str:
    """The blackboard key carrying a map's ordered member grounding-graph ids
    for its fold (ADR-0201 amendment 5).

    Blackboard-resident on purpose: a Slice-3b targeted re-run reuses the
    RETAINED blackboard and re-executes only one member, so any carrier that
    lives in a local would lose the untargeted siblings' ids — the ids must
    survive exactly as long as the ``out_ds`` values they correlate to, which
    is what riding the same blackboard guarantees. The ``__``-prefixed key
    cannot collide with a DataState IRI, is never named by any pipeline's
    ``start_datastates`` (so it never seeds a run), and ``run`` returns
    PipelineRun IRIs, not the blackboard — it does not leak to consumers.
    """
    return f"__member_graph_ids__:{out_ds}"


def member_completed_key(out_ds: str) -> str:
    """The blackboard key carrying a map's per-member completed mask (ADR-0201
    amendment 6), parallel to :func:`member_graph_ids_key` and with the same
    lifetime argument: a Slice-3b targeted re-run must splice completion state
    exactly as it splices outputs and ids. Needed because the completed
    members' outputs list is COMPACT (stopped members contribute no value —
    a machinery failure has no value, and a hole marker would be
    absence-as-a-special-value), so positional re-alignment at splice time
    requires knowing WHICH members completed."""
    return f"__member_completed__:{out_ds}"


class _MemberOutcome(NamedTuple):
    """One map member's result (coordination §63 Q1: an explicit structural
    flag, never a sentinel in the value channel). ``value`` is meaningful only
    when ``completed`` is True; ``graph_id`` is the member's grounding graph —
    the accepted attempt's when completed, the final (stopped) attempt's when
    not (the ADR-0209 D3 definition as amended by am-6)."""

    value: Any
    graph_id: Optional[str]
    completed: bool


#: The closed PipelineRun status vocabulary the conceded classifier consumes
#: (ADR-0201 am-6). ``stopped`` = a milestone that stopped pre-dispatch
#: (empty/partial domain) or a map with >=1 stopped member. An unknown word
#: RAISES in :func:`terminal_attempt_stopped_short` — never defaults — so a
#: silent misclassification cannot happen quietly (§63 Q3).
PIPELINE_RUN_STATUSES = frozenset({"running", "completed", "failed", "stopped"})


def terminal_attempt_stopped_short(chain_graph, request_run) -> bool:
    """True iff the TERMINAL attempt reached a stop-decision short of the ask:
    at least one of its PipelineRuns is ``"stopped"`` and none is ``"failed"``
    (ADR-0201 am-6 — the ``conceded`` rule, uniform over partial AND empty
    domains by owner ruling, coordination §65).

    Reads the RECORD, not shadow state: the chain graph holds the artifact
    OBJECTS as node values, and ``replan_check.invalidate_at_and_below``
    CLEARS invalidated refs from ``request_run.pipeline_runs``, so that list
    is always exactly the terminal attempt's live runs. Raises on a ref the
    chain graph does not hold or a status outside
    :data:`PIPELINE_RUN_STATUSES`.
    """
    saw_stopped = False
    for iri in request_run.pipeline_runs:
        node = chain_graph.nodes.get(iri)
        if node is None:
            raise ValueError(
                f"pipeline run {iri!r} is not in the chain graph - the record "
                "and the RequestRun disagree"
            )
        status = getattr(node.value, "status", None)
        if status not in PIPELINE_RUN_STATUSES:
            raise ValueError(
                f"unknown PipelineRun status {status!r} on {iri!r}; the "
                f"classifier's vocabulary is closed: "
                f"{sorted(PIPELINE_RUN_STATUSES)}"
            )
        if status == "failed":
            return False
        if status == "stopped":
            saw_stopped = True
    return saw_stopped


def _stopped_graph_id(graphs) -> Optional[str]:
    """The ``graph_id`` of the last graph in ``graphs`` carrying a terminal
    ``RunStopped`` — the am-6 fallback for a stopped sub-plan member's id when
    no ``sub_target`` producer exists (D3 as amended)."""
    from mindsos_capacity.identifiers import NODE_TYPE_RUN_STOPPED

    for graph in reversed(list(graphs)):
        if any(
            n.type_name == NODE_TYPE_RUN_STOPPED for n in graph.nodes.values()
        ):
            return graph.graph_id
    return None


def _produced_graph_id(graphs, ds_iri: str) -> Optional[str]:
    """The ``graph_id`` of the last graph in ``graphs`` whose run PRODUCED an
    instance of ``ds_iri`` (ADR-0209 D3: a sub-plan member's id is the graph
    of the run that produced its ``sub_target``).

    Read off the graphs themselves — a PRODUCES edge into a
    ``DataStateInstance`` of that type — never off a ref-path or role name
    (S-F2). Last wins: a nested sequence may thread the value through more
    than one stage, and the member's verdict is the one its final producer
    grounded. ``None`` when no graph produced it (a seeded-only or misauthored
    sub-plan) — the caller decides how loud that is.
    """
    for graph in reversed(list(graphs)):
        for edge in graph.edges.values():
            if edge.type_name != EDGE_PRODUCES:
                continue
            target = edge.target
            if (
                target.type_name == NODE_TYPE_DATASTATE_INSTANCE
                and (target.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE)
                == ds_iri
            ):
                return graph.graph_id
    return None


class MemberAbortError(Exception):
    """RETIRED as a raiser (partial-record CR, ADR-0201 am-6) — kept as API.

    Was the all-or-nothing abort signal (Slice 1b): one exhausted member
    skipped every sibling, the fold never ran, and the whole request aborted
    — losing four correct answers because the fifth crashed, the opposite of
    what the product claims. Under partial results NOTHING in ``mindsos_*``
    raises it: a failing member stops IN PLACE and its siblings run. The
    class remains so external callers' ``except`` clauses do not break; the
    absence of raisers is PINNED by the census test
    (``tests/architecture/test_execution_surface_inventory.py``) — reintroduce
    a raise and the sentinel names it."""

    def __init__(self, leaf_ref: str, member_index: int, message: str = ""):
        self.leaf_ref = leaf_ref
        self.member_index = member_index
        super().__init__(
            message
            or f"map {leaf_ref!r}: member {member_index} failed after "
            f"{MEMBER_RETRY_CAP} attempt(s) (legacy all-or-nothing abort - "
            "retired as a raiser by ADR-0201 am-6)"
        )


#: Finder-strategy names accepted by an explicit ``"finder"`` spec key.
FINDER_BFS = "bfs"
FINDER_CONJUNCTION = "conjunction"


def _endpoint_starts(endpoints) -> Tuple[str, ...]:
    """The available start DataStates a leaf's endpoints declare.

    Accepts the plural ``start_datastates`` (multi-input CR) or the original
    singular ``start_datastate``; the singular form yields a 1-tuple, so every
    pre-CR plan resolves exactly as before. Declaring both is a ``ValueError`` —
    silently preferring one would hide a plan-authoring mistake."""
    plural = endpoints.get("start_datastates")
    single = endpoints.get("start_datastate")
    if plural is not None and single is not None:
        raise ValueError(
            "leaf endpoints declare both 'start_datastate' and "
            "'start_datastates'; use exactly one"
        )
    if plural is not None:
        starts = tuple(plural)
        if not starts:
            raise ValueError("leaf endpoints declare an empty 'start_datastates'")
        return starts
    if single is None:
        raise ValueError(
            "leaf endpoints declare neither 'start_datastate' nor "
            "'start_datastates'"
        )
    return (single,)


def _select_finder(starts: Tuple[str, ...], explicit, where: str) -> str:
    """Pick the finder strategy for a composition (multi-input CR).

    Derived from **arity**: more than one start DataState ⇒ the sound
    ``ConjunctionFinder``; exactly one ⇒ ``BFSFinder`` (the pre-CR path, so every
    shipped consumer is byte-identical — plural starts is a spec shape no
    consumer emits today). An explicit ``"finder"`` key overrides the derivation.

    Asking for ``"bfs"`` with plural starts raises: BFS wires only the single
    ``via`` datastate it arrived on, so it would quietly drop the other declared
    inputs — exactly the failure this CR exists to remove. Fail loud instead."""
    if explicit is None:
        return FINDER_CONJUNCTION if len(starts) > 1 else FINDER_BFS
    if explicit not in (FINDER_BFS, FINDER_CONJUNCTION):
        raise ValueError(
            f"{where}: unknown finder {explicit!r} "
            f"(expected {FINDER_BFS!r} or {FINDER_CONJUNCTION!r})"
        )
    if explicit == FINDER_BFS and len(starts) > 1:
        raise ValueError(
            f"{where}: finder={FINDER_BFS!r} cannot compose {len(starts)} start "
            f"datastates {list(starts)!r} soundly — it wires only one and leaves "
            f"the rest unwired. Use {FINDER_CONJUNCTION!r} (the default at this "
            f"arity) or declare a single start."
        )
    return explicit


class LeafPipelineNotFound(RuntimeError):
    """Composition yielded no pipeline for a leaf.

    **Why an exception here, when the finder stopped raising.** L3 no longer
    raises for "no route" — that is a verdict about the world (shim S4,
    ADR-0206 §3). What L4 does with a don't-know is a separate question, and
    what ``execution.py`` does today is fail the leaf, because nothing here
    catches. Converting that to a returned failure would be **new behaviour**,
    which CORE-C3R1 is explicitly not (faithful conversion, no new failure
    modes). So the propagation is preserved and the diagnosis improves.

    **Replacement:** the planning loop at **C4R3**, which moves this caller.
    Composing a pipeline per leaf is itself the defect ADR-0206 §3 names —
    finding belongs to planning, not execution — so this class dies with the
    call site rather than being fixed in place.

    Carries **one** verdict. It used to carry two — see
    :func:`_compose_pipeline` for why there is now only one call to hold a
    verdict for.
    """

    def __init__(self, verdict, starts, target) -> None:
        self.verdict = verdict
        super().__init__(
            f"no pipeline to {target!r} from {list(starts)!r}: "
            f"[{verdict.reason}] {verdict.detail}"
        )


def _compose_pipeline(dispatcher, starts: Tuple[str, ...], target: str, finder_name: str):
    """Compose one pipeline from the currently-registered capacities.

    The finder is role-blind; L4 binds operands at dispatch (ADR-0071/0156).
    **One session-scoped find.** ``pipeline._view_for`` now hands the finder a
    Local-preferring UNION of Global and the session's Local, so a single call
    already searches both realms and a Local override composes inside an
    otherwise-Global chain.

    **This supersedes CORE-C3R1 D5** (ADR-0071 §amendment-5). D5 had this
    function call ``find`` twice — Local view, then Global — and hold both
    verdicts, because ``_view_for`` returned one realm at a time and a
    consumer's solve capacities are typically Local. With a union view the
    second call is not a fallback, it is a **bypass**: when a Local override is
    refused by step admission (say its ``operand_arity`` is unroutable), the
    union correctly reports no route, and re-running Global-only then composes
    the very chain the user overrode — silently, with no signal that their
    capacity was skipped. Local-over-Global has to mean the Local one is
    authoritative *including when it is broken*; anything else makes an
    override advisory. So the retry goes, and with it D5's second verdict.

    ``session=None`` callers are unaffected: ``_view_for`` still resolves them
    to Global alone.
    """
    from mindsos_capacity.pipeline import BFSFinder, ConjunctionFinder

    finder = (
        ConjunctionFinder() if finder_name == FINDER_CONJUNCTION else BFSFinder()
    )
    verdict = finder.find(
        dispatcher.capacity_layer,
        session=dispatcher.session,
        start_datastates=starts,
        target_datastate=target,
    )
    if verdict.found:
        return verdict
    raise LeafPipelineNotFound(verdict, starts, target)


def _resolve_shared_inputs(spec, blackboard, leaf_ref: str) -> Dict[str, Any]:
    """Snapshot a map spec's ``shared_inputs`` off the parent blackboard.

    Returns ``{}`` when the key is absent — the whole multi-input path is then
    inert and the map is byte-identical to Slice 1b/2/3b. A declared key with no
    value on the parent blackboard raises ``ValueError`` naming both the key and
    the map: skipping it would surface much later as an opaque "required input
    unproducible" from the finder, or (with BFS) as a capacity body failing on a
    missing kwarg. Validated once, before the fan-out, so an empty collection
    still reports a mis-authored spec."""
    keys = spec.get("shared_inputs") or ()
    shared: Dict[str, Any] = {}
    for ds in keys:
        if ds not in blackboard:
            raise ValueError(
                f"map {leaf_ref!r}: shared input {ds!r} is not on the parent "
                f"blackboard (available: {sorted(blackboard)!r}). A shared input "
                f"must be produced by an upstream milestone or seeded into the "
                f"run before this map."
            )
        shared[ds] = blackboard[ds]
    return shared


def _parse_member_target(target_ref):
    """Parse a bare top-level map-member ref-path ``"{leaf_idx}:m{member_idx}"``
    into ``(leaf_idx, member_idx)``; ``None`` for anything else.

    Slice 3b targets **only** the unambiguous top-level structural form (exactly
    two segments — a leaf index and an ``m<member>`` segment). A full
    ``pipelinerun:{scope}:…`` grounding ref (the Slice-3 *advisory* address, whose
    scope segment may itself contain ``:``) or a deeper **nested** path
    (``"{i}:m{j}:{k}:m{l}"``, whose members emit interleaved PipelineRuns so the
    flat-list index alignment does not hold) both return ``None`` → the caller
    falls back to a safe whole-pipeline replan (byte-identical to Slice 3)."""
    if not isinstance(target_ref, str) or not target_ref:
        return None
    parts = target_ref.split(":")
    if len(parts) != 2:
        return None
    head, mem = parts
    if not head.isdigit() or not (mem.startswith("m") and mem[1:].isdigit()):
        return None
    return int(head), int(mem[1:])


def resolve_member_target(plan_result, target_ref):
    """Resolve a replan verdict's advisory ``target_ref`` to a re-runnable
    ``(map_leaf_idx, member_idx)`` — Slice 3b, top-level flat map only.

    Returns ``None`` (→ whole-pipeline replan, byte-identical to Slice 3) unless
    ``target_ref`` is a bare ``"{idx}:m{j}"`` path (see :func:`_parse_member_target`)
    AND the named milestone is a ``map`` carrying no ``sub_plan``. Nested targeting
    is deferred with the B/continuity slice: a nested map's members append
    interleaved PipelineRuns, so ``invalidate_at_and_below``'s position-based clear
    would not isolate them."""
    parsed = _parse_member_target(target_ref)
    if parsed is None:
        return None
    map_idx, member_idx = parsed
    leaf_refs = getattr(plan_result, "leaf_milestone_refs", None) or []
    if not (0 <= map_idx < len(leaf_refs)):
        return None
    specs = getattr(plan_result, "milestone_specs", None) or {}
    spec = specs.get(leaf_refs[map_idx])
    if not spec or spec.get("kind") != "map" or spec.get("sub_plan"):
        return None
    return map_idx, member_idx


def run(
    dispatcher,
    writer,
    plan_result,
    request_run,
    *,
    mm: Any = None,
    run_scope: Optional[str] = None,
    solve_seed: Optional[dict] = None,
    capacity_graphs: Optional[list] = None,
    run_attempt: int = 0,
    blackboard: Optional[dict] = None,
    targeted: Optional[tuple] = None,
    case_label: Optional[str] = None,
) -> List[str]:
    """Run each leaf Pipeline; return the top-level PipelineRun IRIs.

    ``mm`` / ``run_scope`` / ``solve_seed`` are supplied by the orchestrator on
    the solve path (Step 5). ``solve_seed`` maps the plan's ``start_datastate``
    to the resolved-task value (Phase-1 ``resolved_reference``) and seeds the
    run-scoped blackboard. When ``mm``/``solve_seed`` are absent — or the plan
    names neither ``solve_target``, a ``leaf_targets`` entry, nor a map/fold
    ``milestone_specs`` entry — that leaf falls back to the notional record.
    ``capacity_graphs`` (when a list is passed) collects each real run's
    ``capacity_mm`` grounding graph for consolidation persistence. ``run_attempt``
    (the orchestrator's replan counter) makes each replan re-run's per-run ref
    fresh, so a re-dispatch grounds an isolated graph instead of overwriting the
    prior attempt's (Slice A isolation). A map milestone whose member exhausts
    ``MEMBER_RETRY_CAP`` stops IN PLACE (partial results, ADR-0201 am-6) — its
    siblings run and the fold stops ``partial_domain``; nothing raises.

    The per-leaf work is delegated to :func:`_run_milestone_sequence` (Slice 2),
    entered here with an empty ``ref_path`` so a top-level leaf's per-run ref is
    ``{leaf_idx}`` — byte-identical to Slice 1a/1b.

    ``case_label`` is written verbatim onto every run manifest this call mints
    (leaf, member, and no-route alike) and is **never invented by core**: which
    of a consumer's cases a run is, is the consumer's fact. Absent — the default,
    and every existing caller — means the manifest records no label, which a
    renderer must be able to tell apart from a label it could not read."""
    solve_target = getattr(plan_result, "solve_target", None)
    leaf_targets = getattr(plan_result, "leaf_targets", None) or {}
    milestone_specs = getattr(plan_result, "milestone_specs", None) or {}
    # ADR-0209 — the shape-(a) decode contract also holds on this path: a
    # consumer that hand-builds a PlanResult (every current demo driver does)
    # never passes through plan_construction.build, and a contract enforced on
    # one of two entry roads is a convention. Static: reads declarations only.
    if milestone_specs:
        from .plan_construction import check_fold_reducer_decode

        check_fold_reducer_decode(dispatcher, milestone_specs)
    # Real-solve mode is active when the orchestrator supplies the MM + seed and
    # the plan names at least one endpoint (a plan-global ``solve_target`` or any
    # per-leaf entry) or a map/fold milestone spec (Slice 1b). v0 / no-endpoint
    # plans stay on the notional path.
    real_mode = (
        mm is not None
        and solve_seed is not None
        and (
            solve_target is not None
            or bool(leaf_targets)
            or bool(milestone_specs)
        )
    )
    # Slice 1a — one attempt-scoped blackboard threaded across milestones, seeded
    # from ``solve_seed``. Slice 3b — the orchestrator may instead pass a
    # ``blackboard`` retained from the prior attempt so a *targeted* replan reuses
    # the completed siblings' values; ``targeted`` = ``(map_leaf_idx, member_idx)``
    # then resumes the sequence AT that top-level map and re-runs only that one
    # member (splicing it into the retained member outputs), followed by the fold
    # + any downstream. With ``blackboard=None``/``targeted=None`` (every
    # v0/1a/1b/2/3 path) a fresh blackboard is seeded and the whole sequence runs
    # from index 0 — byte-identical.
    bb: dict = blackboard if blackboard is not None else dict(solve_seed or {})
    start_idx, target_member = targeted if targeted is not None else (0, None)
    prs = _run_milestone_sequence(
        dispatcher, writer, request_run,
        leaf_refs=plan_result.leaf_milestone_refs,
        pipeline_refs=plan_result.pipeline_refs,
        milestone_specs=milestone_specs,
        leaf_targets=leaf_targets,
        solve_target=solve_target,
        blackboard=bb,
        mm=mm,
        scope=run_scope or request_run.iri,
        ref_path="",
        run_attempt=run_attempt,
        capacity_graphs=capacity_graphs,
        real_mode=real_mode,
        start_idx=start_idx,
        target_member=target_member,
        case_label=case_label,
    )
    return [pr.iri for pr in prs]


def _run_milestone_sequence(
    dispatcher, writer, request_run, *,
    leaf_refs, pipeline_refs, milestone_specs, leaf_targets, solve_target,
    blackboard, mm, scope: str, ref_path: str, run_attempt: int,
    capacity_graphs: Optional[list], real_mode: bool,
    start_idx: int = 0, target_member: Optional[int] = None,
    case_label: Optional[str] = None,
) -> list:
    """Run one ordered sequence of milestones over a shared ``blackboard`` and
    return the emitted PipelineRun OBJECTS, in order (collection-iteration
    Slice 2 factoring; objects since am-6 — a sub-plan member's completion is
    decided from its sub-run's terminal status, and ``run`` maps them to IRIs
    for its public return, so no public signature changes).

    Shared by ``run`` (top level, ``ref_path=""``) and each map member's sub-plan
    (``ref_path`` = the member's path). Each milestone's per-run ref path is
    ``{ref_path}:{leaf_idx}`` (or ``{leaf_idx}`` at the top), so grounding graphs
    stay isolated per position and the provenance tree is walkable. The
    ``leaf_targets``/``solve_target``/``milestone_specs`` are read exactly as the
    top-level loop did; ``real_mode`` gates the real-vs-notional branch (a nested
    sub-plan is inherently real — ``mm`` is present). Every emitted PipelineRun is
    appended to ``request_run.pipeline_runs`` (a flat list; the tree lives in the
    ref-path — Slice 2 decision)."""
    pipeline_runs: list = []
    for leaf_idx, leaf_ref in enumerate(leaf_refs):
        # Slice 3b — on a targeted re-execution the prefix milestones (before the
        # named map at ``start_idx``) already ran in the prior attempt and their
        # values are retained on the reused blackboard; skip them (no re-emit, no
        # re-run). With ``start_idx=0`` (every non-targeted call) nothing is
        # skipped — byte-identical.
        if leaf_idx < start_idx:
            continue
        pipeline_ref = pipeline_refs.get(leaf_ref)
        pr = writer.emit_pipeline_run(pipeline_ref, leaf_ref, request_run.iri)
        spec = milestone_specs.get(leaf_ref)
        kind = spec.get("kind") if spec else None
        leaf_path = f"{ref_path}:{leaf_idx}" if ref_path else f"{leaf_idx}"
        endpoints = leaf_targets.get(leaf_ref) or solve_target
        if real_mode and kind == "map":
            # Slice 1b/2 — fan out a uniform sub-plan over the collection's
            # members (bounded retry + stop-in-place, am-6); a member's work
            # is either the flat 1b leaf or a nested sub-plan (Slice 2). Writes
            # the ordered member outputs to the blackboard for the fold. Raises
            # An exhausted member stops in place; siblings run (am-6).
            # Slice 3b — when this is the targeted map (``leaf_idx == start_idx``
            # and a member was named) re-run only that one member; else the full
            # fan-out (``only_member=None`` → byte-identical).
            only_member = (
                target_member
                if (target_member is not None and leaf_idx == start_idx)
                else None
            )
            _run_map_milestone(
                dispatcher, writer, request_run, pr, leaf_ref, spec, blackboard,
                mm, scope, leaf_path, run_attempt, capacity_graphs,
                only_member=only_member,
                case_label=case_label,
            )
        elif real_mode and kind == "fold":
            # Slice 1b — the L3 reducer over the ordered member outputs, routed
            # through ``execute_pipeline`` (fold-grounding CR) so the fold run
            # GROUNDS: before this it dispatched the reducer directly, took no
            # ``mm``, and left NOTHING in the grounding graph — no manifest, no
            # reducer CapacityInstance, no conclusion DataStateInstance — so the
            # claim-level answer lived only on this in-memory blackboard and was
            # unrenderable.
            _run_fold_milestone(
                dispatcher, writer, pr, leaf_ref, spec, blackboard,
                mm, scope, leaf_path, run_attempt, capacity_graphs,
                case_label=case_label,
            )
        elif real_mode and endpoints is not None:
            outputs = _run_leaf_pipeline(
                dispatcher, writer, pr, leaf_ref, endpoints, blackboard,
                mm, scope, leaf_path, run_attempt, capacity_graphs,
                case_label,
            )
            # Thread this stage's produced values to downstream stages.
            blackboard.update(outputs)
        else:
            # Notional step record (no real capacity steps at v0) — unchanged
            # Phase-47 behaviour.
            writer.emit_step_execution_record(
                pipeline_ref,
                pipeline_run_ref=pr.iri,
                milestone_ref=leaf_ref,
                confidence=1.0,
            )
            pr.status = "completed"
        pipeline_runs.append(pr)
        request_run.pipeline_runs.append(pr.iri)
    return pipeline_runs


def _member_starts(member_ds: str, shared) -> Tuple[str, ...]:
    """The start set one map member composes from.

    Member value first, so a spec that (wrongly) also lists ``member_ds`` as a
    shared input cannot shadow the member being iterated. Factored out because
    :func:`_run_one_member` needs the same tuple to describe a member that found
    no route, and re-deriving it in a second place is exactly how the member path
    drifted from the leaf path to begin with.
    """
    shared = shared or {}
    return (member_ds,) + tuple(ds for ds in shared if ds != member_ds)


def _mint_no_route_graph(
    dispatcher, mm, request_id: str, run_ref: str,
    starts: Tuple[str, ...], capacity_graphs: Optional[list],
    case_label: Optional[str],
) -> Optional[str]:
    """Leave a manifest-only grounding graph for a run that found no route;
    return its ``graph_id`` (am-6: a no-route MEMBER's id in the fold
    manifest), or ``None`` when nothing was written.

    :func:`_compose_pipeline` raises :class:`LeafPipelineNotFound` before
    anything is written, so without this an unroutable request leaves NO graph —
    not even L-2's ``RunStopped`` — and the only renderable artifact is a caught
    exception, which contradicts rendering from the graph and nothing else.

    Called from **both** run paths. The leaf path had this inline and the member
    path had nothing at all: ``_run_member_pipeline`` never caught the exception,
    so an unroutable member left no graph and then ``MemberAbortError`` took the
    whole request's Record with it. One helper, two callers, is the point of it.

    There is no pipeline here, so there are no capacity phrases to snapshot and
    the starts are what the run was **asked** for rather than what a composed
    pipeline declared. On this page that is the entire content, which is why the
    starts are phrases and not bare IRIs — bare IRIs printed straight onto the
    one page that has nothing else on it.

    ``mm=None`` returns without writing: the no-MM path is value-only and has no
    graph to leave.
    """
    if mm is None:
        return None
    from .capacity_mm_writer import CapacityMMWriter, start_phrases

    mm_writer = CapacityMMWriter(mm, request_id, run_ref)
    mm_writer.manifest(
        declared_starts=start_phrases(dispatcher, starts),
        capacity_phrases={},
        case_label=case_label,
    )
    if capacity_graphs is not None and mm_writer.graph is not None:
        capacity_graphs.append(mm_writer.graph)
        return mm_writer.graph.graph_id
    return None


def _run_leaf_pipeline(
    dispatcher, writer, pr, leaf_ref, endpoints, blackboard,
    mm, request_id: str, leaf_path: str, run_attempt: int,
    capacity_graphs: Optional[list],
    case_label: Optional[str] = None,
) -> dict:
    """Find + run the real leaf pipeline; ground it into ``capacity_mm``, collect
    its per-run graph, and return its outputs (for the caller to thread onto the
    run blackboard). Local imports keep this module's import graph light and
    cycle-free (``pipeline_execution`` reaches ``capacity_mm_writer`` → ``mm`` →
    core, none of which import ``execution``). ``leaf_path`` (Slice 2) is the
    milestone's ref-path position; at depth 0 it is ``str(leaf_idx)`` so the ref
    is byte-identical to Slice 1a/1b.

    Multi-input CR: ``endpoints`` may declare plural ``start_datastates`` instead
    of the singular ``start_datastate``, in which case the sound
    ``ConjunctionFinder`` composes the leaf (arity-derived — see
    :func:`_select_finder`). With a single start this is the pre-CR path
    unchanged."""
    from .pipeline_execution import execute_pipeline

    starts = _endpoint_starts(endpoints)
    target = endpoints["target_datastate"]
    finder_name = _select_finder(
        starts, endpoints.get("finder"), f"leaf {leaf_ref!r}"
    )
    # A fresh per-run ref per leaf gives each run its own isolated grounding
    # graph (Slice A: replan / concurrent isolation).
    run_ref = f"pipelinerun:{request_id}:{leaf_path}:{run_attempt}"
    try:
        pipeline = _compose_pipeline(dispatcher, starts, target, finder_name).pipeline
    except LeafPipelineNotFound:
        # No route, so no capacity to name and no pipeline to read starts from —
        # the endpoints are what the run was asked for. Shared with the member
        # path; see :func:`_mint_no_route_graph`.
        _mint_no_route_graph(
            dispatcher, mm, request_id, run_ref, starts, capacity_graphs,
            case_label,
        )
        raise
    # Slice 1a — seed only the values the pipeline declares as starts, drawn from
    # the shared blackboard (an upstream stage may have produced them). Filtering
    # to ``start_datastates`` keeps ``execute_pipeline`` from minting unrelated
    # blackboard values as grounding roots (it seeds every initial input).
    seed = {
        ds: blackboard[ds]
        for ds in pipeline.start_datastates
        if ds in blackboard
    }
    # NOTE: this function no longer mints the manifest, and nothing here replaces
    # it. Minting moved into ``execute_pipeline`` — the one function BOTH run
    # paths call — because minting it here gave the leaf a manifest and left
    # every map member without one.
    result = execute_pipeline(
        dispatcher,
        pipeline,
        seed,
        request_id=request_id,
        mm=mm,
        pipeline_run_ref=run_ref,
        case_label=case_label,
    )
    # Real provenance: one StepExecutionRecord per executed capacity step
    # (replaces the single notional record).
    for step in getattr(pipeline, "steps", ()) or ():
        writer.emit_step_execution_record(
            step.capacity_iri,
            pipeline_run_ref=pr.iri,
            milestone_ref=leaf_ref,
            confidence=1.0 if result.success else 0.0,
        )
    pr.status = "completed" if result.success else "failed"
    if capacity_graphs is not None and result.capacity_graph is not None:
        capacity_graphs.append(result.capacity_graph)
    return dict(result.outputs)


def _run_map_milestone(
    dispatcher, writer, request_run, pr, leaf_ref, spec, blackboard,
    mm, request_id: str, leaf_path: str, run_attempt: int,
    capacity_graphs: Optional[list],
    only_member: Optional[int] = None,
    case_label: Optional[str] = None,
) -> None:
    """Map fan-out (collection-iteration Slice 1b; nesting Slice 2).

    Read the ordered collection value from the shared blackboard (ADR-0199: L4
    owns the unpack loop) and, for each member **sequentially** (v1), produce its
    ``sub_target`` output. A member's work is one of:

    * **Flat leaf (1b)** — compose ``(member_ds, *shared_inputs) -> sub_target``
      and ``execute_pipeline`` in an isolated sub-blackboard seeded with the
      member value plus the shared inputs, under a fresh per-member run-ref so
      its ``capacity_mm`` grounding graph stays isolated. Bounded retry on a
      plain step failure only (a needs_input result is never re-asked and a
      no-route member is deterministic — am-6); accept the first attempt with
      ``success=True``. **Partial results (am-6, replacing ∀-abort):** a
      member still failing at ``MEMBER_RETRY_CAP`` STOPS IN PLACE — its final
      attempt's graph is retained (the stop the page names) — and its
      siblings run.
    * **Sub-plan (Slice 2)** — when ``spec["sub_plan"]`` is present, the member
      runs that nested milestone sequence in its own isolated sub-blackboard
      (seeded with the member value) under the member's ref-path, and the map
      collects ``sub_target`` from that sub-blackboard. The sub-plan may itself
      contain a nested map/fold; a sub-plan whose terminal milestone stopped
      makes THIS member a stopped member of its parent (minimum-viable
      propagation, §63 Q5). The sub-plan member itself is not retried — retry
      lives at the flat find+execute leaf inside it.

    Writes the COMPLETED members' ``sub_target`` outputs (ordered, compact) to
    ``blackboard[out_ds]``, the full N-length grounding-id list and completed
    mask to the am-5/am-6 carriers, and sets its PipelineRun status to
    ``"stopped"`` when any member stopped (``"completed"`` otherwise). The
    fold decides what a truncated domain means; the map never does.

    Multi-input CR: ``spec["shared_inputs"]`` (optional) names parent-blackboard
    keys copied into **every** member's sub-blackboard alongside the member
    value, so a member capacity's non-member inputs have a source. They are
    snapshotted once, before the fan-out, so a mis-authored key fails loudly even
    for an empty collection. The member pipeline is composed lazily on the first
    member and reused (``compose_cache``) — starts and target are identical
    across members, and an empty collection must still compose nothing."""
    collection_ds = spec["collection_ds"]
    out_ds = spec["out_ds"]
    shared = _resolve_shared_inputs(spec, blackboard, leaf_ref)
    compose_cache: Dict[str, Any] = {}
    members = list(blackboard.get(collection_ds) or [])
    if only_member is not None:
        # Slice 3b — targeted: re-run just this one member and splice its output
        # into the retained ordered outputs; the untargeted siblings (and their
        # grounding graphs) are left untouched. The orchestrator bumps
        # ``run_attempt`` for the re-run, so its grounding ref is fresh and never
        # overwrites the prior attempt's (Slice-A isolation).
        existing = list(blackboard.get(out_ds) or [])
        outcome = _run_one_member(
            dispatcher, writer, request_run, pr, leaf_ref, spec, mm,
            request_id, leaf_path, only_member, members[only_member],
            run_attempt, capacity_graphs, shared, compose_cache, case_label,
        )
        mask = blackboard.get(member_completed_key(out_ds))
        if mask is not None:
            # ADR-0201 am-6 — the completed-outputs list is COMPACT, so the
            # splice position is the count of completed members BEFORE this
            # one; the retained mask says which those are. The record and the
            # list must agree or this raises (the §63 Q3 discipline).
            mask = list(mask)
            if only_member >= len(mask):
                mask.extend([False] * (only_member + 1 - len(mask)))
            if len(existing) != sum(mask):
                raise ValueError(
                    f"retained outputs ({len(existing)}) disagree with the "
                    f"completed mask ({sum(mask)}) for {out_ds!r}"
                )
            pos = sum(1 for c in mask[:only_member] if c)
            was_completed = mask[only_member]
            if outcome.completed and was_completed:
                existing[pos] = outcome.value
            elif outcome.completed and not was_completed:
                existing.insert(pos, outcome.value)
            elif not outcome.completed and was_completed:
                del existing[pos]
            mask[only_member] = outcome.completed
            blackboard[member_completed_key(out_ds)] = mask
        else:
            # Legacy positional splice (a retained blackboard from before the
            # mask existed).
            if only_member < len(existing):
                existing[only_member] = outcome.value
            else:
                existing.append(outcome.value)
        blackboard[out_ds] = existing
        # ADR-0201 amendment 5 — the retained id list splices EXACTLY as the
        # retained outputs do, so position i keeps correlating: the re-run
        # member's fresh graph replaces its prior id, untargeted siblings keep
        # theirs.
        if mm is not None and capacity_graphs is not None:
            ids = list(blackboard.get(member_graph_ids_key(out_ds)) or [])
            if only_member < len(ids):
                ids[only_member] = outcome.graph_id
            else:
                ids.append(outcome.graph_id)
            blackboard[member_graph_ids_key(out_ds)] = ids
        pr.status = (
            "completed" if (mask is None or all(mask)) else "stopped"
        )
        return
    member_outputs: List[Any] = []
    member_gids: List[Optional[str]] = []
    member_mask: List[bool] = []
    for member_idx, member_value in enumerate(members):
        outcome = _run_one_member(
            dispatcher, writer, request_run, pr, leaf_ref, spec, mm,
            request_id, leaf_path, member_idx, member_value,
            run_attempt, capacity_graphs, shared, compose_cache, case_label,
        )
        # ADR-0201 am-6 (partial results): a stopped member contributes NO
        # output — a machinery failure has no value, and a hole marker would
        # be absence-as-a-special-value (§63 Q1). Its grounding id still
        # lands at its position, so the page can name the stop.
        if outcome.completed:
            member_outputs.append(outcome.value)
        member_gids.append(outcome.graph_id)
        member_mask.append(outcome.completed)
    blackboard[out_ds] = member_outputs
    # ADR-0201 amendment 5 — the ordered member grounding-graph ids ride the
    # same blackboard as the ordered outputs they correlate to, for the fold's
    # manifest. Only when the run grounds AND collects graphs: an id pointing
    # at a graph nobody keeps would be a reference into nothing. am-6 adds the
    # parallel completed mask (see member_completed_key).
    if mm is not None and capacity_graphs is not None:
        blackboard[member_graph_ids_key(out_ds)] = member_gids
    # The mask is EXECUTION state, not persistence state: the fold must see
    # a truncation even on a run that collects no graphs, or the reducer
    # would conclude from a gapped list on exactly that path. Written
    # unconditionally by every real-mode map.
    blackboard[member_completed_key(out_ds)] = member_mask
    pr.status = "completed" if all(member_mask) else "stopped"


def _run_one_member(
    dispatcher, writer, request_run, pr, leaf_ref, spec, mm,
    request_id: str, leaf_path: str, member_idx: int, member_value: Any,
    run_attempt: int, capacity_graphs: Optional[list],
    shared: Optional[Dict[str, Any]] = None,
    compose_cache: Optional[Dict[str, Any]] = None,
    case_label: Optional[str] = None,
) -> "_MemberOutcome":
    """Run one map member; return a :class:`_MemberOutcome`
    ``(value, graph_id, completed)`` (Slice 3b factoring; the id is ADR-0201
    am-5, the flag is am-6 / §63 Q1).

    The id is the member's grounding graph — completed flat member: the
    ACCEPTED attempt's graph (rejected retries persist nothing); STOPPED flat
    member: the FINAL attempt's graph, retained so the page can name the stop
    (a no-route member's manifest-only graph included — the run-4 precedent:
    manifest-only IS the no-route stop); completed sub-plan member: the graph
    that PRODUCED ``sub_target`` (ADR-0209 D3); stopped sub-plan member: its
    sub-run's last stopped graph (D3 as amended by am-6). ``None`` when the
    run does not ground/collect (``mm`` or ``capacity_graphs`` absent).

    Extracted from the map loop so the full fan-out and a targeted
    single-member re-run (:func:`_run_map_milestone`) share one code path.
    Retry policy (am-6): retry to ``MEMBER_RETRY_CAP`` on a plain step
    failure ONLY. A needs_input result is stopped on the FIRST ask — inputs
    do not change between attempts, so re-asking is re-asking; a cancelled
    result is someone's decision, not a transient; a no-route member is
    deterministic (the capacity set does not change between attempts).
    Nothing raises: an exhausted or stopped member returns
    ``completed=False`` and its siblings run.

    Multi-input CR: ``shared`` (the map's snapshotted ``shared_inputs``) is merged
    into the member's sub-blackboard **under** the member value — a spec that
    named ``member_ds`` as a shared input would otherwise shadow the member it is
    iterating. ``compose_cache`` carries the once-composed member pipeline across
    members and retries. With ``shared={}`` (no ``shared_inputs``) behaviour is
    unchanged from the inline Slice-1b/2 loop."""
    member_ds = spec["member_ds"]
    sub_target = spec["sub_target"]
    sub_plan = spec.get("sub_plan")  # Slice 2 — nested plan (optional)
    member_path = f"{leaf_path}:m{member_idx}"
    shared = shared or {}
    if sub_plan is not None:
        # Slice 2 — the member's work is a whole sub-plan (which may nest a
        # further map/fold). Run it once in an isolated sub-blackboard seeded with
        # the member value; a stopped sub-run makes this a stopped member
        # (am-6 minimum-viable propagation, decided from the sub-run's record).
        # Multi-input CR: the shared inputs seed it too, so every leaf and nested
        # map inside the sub-plan can see them (a nested map re-declares the ones
        # it needs — there is no implicit inheritance past the sub-blackboard).
        sub_blackboard: dict = {**shared, member_ds: member_value}
        graphs_before = len(capacity_graphs) if capacity_graphs is not None else 0
        sub_prs = _run_milestone_sequence(
            dispatcher, writer, request_run,
            leaf_refs=sub_plan["leaf_milestone_refs"],
            pipeline_refs=sub_plan.get("pipeline_refs") or {},
            milestone_specs=sub_plan.get("milestone_specs") or {},
            leaf_targets=sub_plan.get("leaf_targets") or {},
            solve_target=sub_plan.get("solve_target"),
            blackboard=sub_blackboard,
            mm=mm,
            scope=request_id,
            ref_path=member_path,
            run_attempt=run_attempt,
            capacity_graphs=capacity_graphs,
            real_mode=True,
            case_label=case_label,
        )
        # am-6 / §63 Q5 (minimum-viable nested propagation): this member is
        # COMPLETED iff its sub-run's terminal milestone completed AND the
        # sub-plan actually produced ``sub_target`` — decided from the
        # sub-run's own RECORD, never from a None in the value channel. The
        # two signals must agree or this raises (§63 Q3's discipline).
        terminal_ok = bool(sub_prs) and sub_prs[-1].status == "completed"
        produced = sub_target in sub_blackboard
        if terminal_ok != produced:
            raise ValueError(
                f"sub-plan member {member_path!r}: terminal milestone status "
                f"({sub_prs[-1].status if sub_prs else 'none'!r}) and "
                f"{sub_target!r} presence ({produced}) disagree - the record "
                "and the value bus are out of step"
            )
        member_slice = (
            capacity_graphs[graphs_before:]
            if (mm is not None and capacity_graphs is not None)
            else []
        )
        if terminal_ok:
            return _MemberOutcome(
                sub_blackboard.get(sub_target),
                _produced_graph_id(member_slice, sub_target) or None,
                True,
            )
        return _MemberOutcome(
            None,
            _stopped_graph_id(member_slice)
            or (member_slice[-1].graph_id if member_slice else None),
            False,
        )
    # Flat 1b member (no sub_plan): bounded retry + accept-first-clean.
    accepted = None
    result = None
    last_pipeline = None
    for retry_idx in range(MEMBER_RETRY_CAP):
        run_ref = (
            f"pipelinerun:{request_id}:{member_path}"
            f":{run_attempt}:r{retry_idx}"
        )
        try:
            result, last_pipeline = _run_member_pipeline(
                dispatcher, member_ds, member_value, sub_target,
                request_id, run_ref, mm,
                shared=shared, spec=spec, leaf_ref=leaf_ref,
                compose_cache=compose_cache, case_label=case_label,
            )
        except LeafPipelineNotFound:
            # An unroutable member leaves its manifest-only graph (the run-4
            # precedent: manifest-only IS the no-route stop) and — am-6 —
            # STOPS IN PLACE instead of aborting the request. No route is not
            # retryable: the capacity set does not change between attempts.
            no_route_gid = _mint_no_route_graph(
                dispatcher, mm, request_id, run_ref,
                _member_starts(member_ds, shared), capacity_graphs, case_label,
            )
            return _MemberOutcome(None, no_route_gid, False)
        if result.success:
            accepted = result
            break  # accept the first clean attempt
        if result.needs_input is not None or result.cancelled:
            # am-6: never re-ask (inputs do not change between attempts —
            # the rule is in the amendment's text), and a cancellation is a
            # decision, not a transient. Stop on the first such terminal.
            break
    if accepted is None:
        # am-6 (partial results, replacing ∀-abort): this member STOPS IN
        # PLACE. Its FINAL attempt's graph is retained — it grounded a
        # manifest and a terminal ``RunStopped`` — so the page can name the
        # stop at this member's position; siblings run.
        member_gid = None
        final_graph = result.capacity_graph if result is not None else None
        if capacity_graphs is not None and final_graph is not None:
            capacity_graphs.append(final_graph)
            member_gid = final_graph.graph_id
        for step in getattr(last_pipeline, "steps", ()) or ():
            writer.emit_step_execution_record(
                step.capacity_iri,
                pipeline_run_ref=pr.iri,
                milestone_ref=leaf_ref,
                confidence=0.0,
            )
        return _MemberOutcome(None, member_gid, False)
    # Accepted attempt only: persist its grounding graph + per-step records.
    member_gid = None
    if capacity_graphs is not None and accepted.capacity_graph is not None:
        capacity_graphs.append(accepted.capacity_graph)
        member_gid = accepted.capacity_graph.graph_id
    for step in getattr(last_pipeline, "steps", ()) or ():
        writer.emit_step_execution_record(
            step.capacity_iri,
            pipeline_run_ref=pr.iri,
            milestone_ref=leaf_ref,
            confidence=1.0,
        )
    return _MemberOutcome(accepted.outputs.get(sub_target), member_gid, True)


def _run_member_pipeline(
    dispatcher, start_ds, seed_value, target_ds,
    request_id: str, run_ref: str, mm,
    *,
    shared: Optional[Dict[str, Any]] = None,
    spec: Optional[dict] = None,
    leaf_ref: str = "",
    compose_cache: Optional[Dict[str, Any]] = None,
    case_label: Optional[str] = None,
):
    """Find + run one member's sub-pipeline, isolated per member (Slice 1b).

    Pure — no writer / ``capacity_graphs`` side effects: the caller
    (:func:`_run_map_milestone`) decides accept/reject, so a rejected retry
    attempt leaves nothing persisted. Seeds the member value under ``start_ds``
    into a fresh sub-blackboard (per-member grounding isolated by the fresh
    ``run_ref``). Returns ``(PipelineExecutionResult, pipeline)``.

    Multi-input CR: ``shared`` adds the map's ``shared_inputs`` values to that
    sub-blackboard and to the composition's start set, so the arity-derived
    finder wires a multi-input member soundly. ``compose_cache`` (one slot,
    owned by the map) composes on the first member and reuses it for the rest —
    starts and target are identical across members. With no ``shared`` and no
    cache this composes exactly what ``find_pipeline`` did."""
    from .pipeline_execution import execute_pipeline

    shared = shared or {}
    starts = _member_starts(start_ds, shared)
    pipeline = compose_cache.get("pipeline") if compose_cache is not None else None
    if pipeline is None:
        finder_name = _select_finder(
            starts,
            (spec or {}).get("finder"),
            f"map {leaf_ref!r} member",
        )
        pipeline = _compose_pipeline(
            dispatcher, starts, target_ds, finder_name
        ).pipeline
        if compose_cache is not None:
            compose_cache["pipeline"] = pipeline
    available = {**shared, start_ds: seed_value}
    seed = {
        ds: value
        for ds, value in available.items()
        if ds in pipeline.start_datastates
    }
    result = execute_pipeline(
        dispatcher,
        pipeline,
        seed,
        request_id=request_id,
        mm=mm,
        pipeline_run_ref=run_ref,
        case_label=case_label,
    )
    return result, pipeline


def _fold_pipeline(dispatcher, reducer_iri: str, in_ds: str):
    """A single-step :class:`~mindsos_capacity.pipeline.Pipeline` for the
    plan-named fold reducer (fold-grounding CR).

    This is **not** a hand-assembled route, and it deliberately does not go
    through a finder. The "composed by the finder" rule protects route
    *finding*; a fold has no route to find — its reducer is **plan-named by
    contract** (``spec["reducer_iri"]``, Slice 1b), and a finder run from
    ``in_ds`` could substitute a different capacity for the one the plan named.
    The single step IS the spec's own shape, expressed as the object
    :func:`~mindsos_intelligence.pipeline_execution.execute_pipeline` grounds.

    ``output_datastates`` are the reducer's **declared** outputs, resolved
    scope-correctly (``resolve_declaration(..., session=)`` — the call
    ``capacity_phrases`` itself uses; ``get_declaration`` is Global-only and a
    consumer's reducer is routinely Local). An unresolvable declaration yields
    ``()`` rather than raising here: the dispatch inside ``execute_pipeline``
    will fail on its own terms and leave a ``RunStopped``, which is the
    renderable failure — an exception from this helper would leave nothing.
    """
    from mindsos_capacity.pipeline import START, DAGEdge, DAGStep, Pipeline

    declared_outputs: Tuple[str, ...] = ()
    layer = getattr(dispatcher, "capacity_layer", None)
    if layer is not None:
        try:
            declaration = layer.resolve_declaration(
                reducer_iri, session=getattr(dispatcher, "session", None)
            )
        except Exception:  # noqa: BLE001 — unresolvable is the dispatcher's find
            declaration = None
        if declaration is not None:
            declared_outputs = tuple(getattr(declaration, "outputs", ()) or ())
    return Pipeline(
        start_datastates=(in_ds,),
        target_datastate=declared_outputs[0] if declared_outputs else in_ds,
        steps=(DAGStep(reducer_iri, (in_ds,), declared_outputs),),
        edges=(DAGEdge(START, 0, in_ds),),
    )


def _run_fold_milestone(
    dispatcher, writer, pr, leaf_ref, spec, blackboard,
    mm, request_id: str, leaf_path: str, run_attempt: int,
    capacity_graphs: Optional[list],
    case_label: Optional[str] = None,
) -> None:
    """Fold / aggregate (collection-iteration Slice 1b; partial results am-6).

    The fold is where a truncated domain is DECIDED, because the map never
    decides it (am-6): when every member completed, run the plan-named L3
    **reducer** capacity over the ordered member outputs on the blackboard
    (``in_ds`` = the map's ``out_ds``) and merge its outputs back for
    downstream stages. A reducer that concludes "no consistent rule" produces
    a legitimate value (→ ``dont_know`` via the existing
    ``sufficient_predicate`` path), NOT a stop.

    **Fold-grounding CR: the reducer runs through ``execute_pipeline``**, under
    a fresh per-fold run ref, so the fold grounds exactly the way a leaf and a
    member do — manifest first, the ordered member outputs seeded as the fold's
    one parentless ``DataStateInstance``, reducer ``CapacityInstance`` +
    CONSUMES, conclusion ``DataStateInstance`` + PRODUCES, ``RunStopped`` on a
    non-success, graph collected for persistence. Before this CR the function
    dispatched the reducer directly and did not take ``mm``: the claim-level
    conclusion existed only on the in-memory blackboard (unrenderable), a
    failed reducer left no terminal node, and no edge tied the member verdicts
    to the conclusion. The fix is the one #157 set the precedent for — route
    through the ONE function that grounds; a hand-mint here would be a third
    copy of the drift that made the member path differ from the leaf path.

    L4-side semantics: a crashed reducer sets ``pr.status = "failed"``; a
    pre-dispatch stop (empty/partial domain) sets ``"stopped"`` — the closed
    vocabulary the conceded classifier consumes
    (:data:`PIPELINE_RUN_STATUSES`); the step record's confidence is ``0.0``
    on any non-success; nothing aborts the sequence.

    **Which member produced which verdict is a manifest field** (ADR-0201
    amendment 5): the fold's manifest carries ``member_graph_ids`` — the
    ordered member grounding-graph ids the map recorded — so position *i* of
    the seeded list correlates to member graph *i* structurally. This
    REPLACES the earlier ruling that correlation "stays structural via the
    ref-path": value-equality correlation is defeated by two identical
    in-band refusals (shape (a) makes those legal — demo finding N-F2), and
    ref-path parsing was already rejected as core-private (S-F2). The seeded
    collection's order is still the members' order; the manifest is how a
    reader may rely on it.

    **An empty domain never reaches the reducer** (ADR-0201 amendment 5,
    owner ruling on ``core-empty-fold-domain``): a fold whose ``in_ds`` has
    no members stops BEFORE dispatch — the run still grounds (manifest with
    ``member_graph_ids=[]``, seeded empty list, ``RunStopped`` alone with
    reason ``empty_domain``) — because a reducer "concluding" from nothing
    would manufacture an epistemic claim out of machinery state, and leaving
    the refusal to each reducer body means the next consumer reintroduces
    it. Ruled at the fold, not per reducer.

    **A TRUNCATED domain never reaches the reducer either** (ADR-0201
    amendment 6, owner ruling on the machinery half): when the map's
    completed mask says fewer members completed than exist — including NONE
    of them — the fold stops ``partial_domain`` pre-dispatch, manifest
    carrying the FULL N-length id list so every stopped member's position
    renders its stop block. Concluding from a machinery-truncated domain is
    the empty-domain doctrine generalized; the healing path is a Slice-3b
    targeted re-exec of the stopped member. ``empty_domain`` stays "the map
    had ZERO members"; the values list and the mask must agree or this
    raises (§63 Q3)."""
    from .pipeline_execution import execute_pipeline

    reducer_iri = spec["reducer_iri"]
    in_ds = spec["in_ds"]
    run_ref = f"pipelinerun:{request_id}:{leaf_path}:{run_attempt}"
    domain = blackboard.get(in_ds)
    member_gids = (
        blackboard.get(member_graph_ids_key(in_ds))
        if (mm is not None and capacity_graphs is not None)
        else None
    )
    member_mask = blackboard.get(member_completed_key(in_ds))
    stop_reason = None
    stop_detail = None
    if member_mask is not None:
        # am-6 coherence: the compact values list must match the mask's
        # completed count — the record and the value bus in step, or loud.
        values_count = len(domain or [])
        if values_count != sum(1 for c in member_mask if c):
            raise ValueError(
                f"fold {leaf_ref!r}: {values_count} values in {in_ds!r} but "
                f"the completed mask says {sum(1 for c in member_mask if c)} "
                "members completed - the carriers are out of step"
            )
        if not all(member_mask):
            stop_reason = RUN_STOPPED_PARTIAL_DOMAIN
            stop_detail = (
                "some of what was needed could not be completed, so no "
                "overall conclusion was drawn"
            )
    if stop_reason is None and not domain:
        stop_reason = RUN_STOPPED_EMPTY_DOMAIN
        stop_detail = (
            "the collection to decide from had no members, so no "
            "conclusion was drawn"
        )
        # Deliberately NO coercion of a missing carrier to [] here (critic
        # s60 point 2): key presence must mean exactly one thing - A MAP
        # SUPPLIED IDS - with [] only when a map ran and yielded zero
        # members. A fold-only plan (in_ds seeded directly, no map) gets no
        # key on EITHER emptiness, so the key can serve as a fold-with-map
        # marker without lying on a legal plan shape.
    result = execute_pipeline(
        dispatcher,
        _fold_pipeline(dispatcher, reducer_iri, in_ds),
        {in_ds: blackboard.get(in_ds)},
        request_id=request_id,
        mm=mm,
        pipeline_run_ref=run_ref,
        case_label=case_label,
        member_graph_ids=member_gids,
        stop_before_dispatch=stop_reason,
        stop_detail=stop_detail,
    )
    success = bool(result.success)
    if success:
        blackboard.update(dict(result.outputs))
    if capacity_graphs is not None and result.capacity_graph is not None:
        capacity_graphs.append(result.capacity_graph)
    writer.emit_step_execution_record(
        reducer_iri,
        pipeline_run_ref=pr.iri,
        milestone_ref=leaf_ref,
        confidence=1.0 if success else 0.0,
    )
    if success:
        pr.status = "completed"
    elif result.stopped_before_dispatch is not None:
        # am-6: a pre-dispatch domain stop is a reached stop-DECISION, not a
        # crash - the conceded classifier's "stopped" (never "failed": no
        # capacity ran, nothing broke).
        pr.status = "stopped"
    else:
        pr.status = "failed"


__all__ = [
    "run",
    "MemberAbortError",
    "PIPELINE_RUN_STATUSES",
    "terminal_attempt_stopped_short",
    "MEMBER_RETRY_CAP",
    "resolve_member_target",
    "FINDER_BFS",
    "FINDER_CONJUNCTION",
]
