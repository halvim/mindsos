"""The Decision Records run driver — plan in, grounded run out.

**What makes this the driver and not a script.** It hands ``execution.run`` a
``PlanResult`` and nothing else: L4 reads the leaf's endpoints, derives the
finder from start **arity** (``_select_finder`` — more than one start selects
``ConjunctionFinder``), composes the pipeline, and grounds it through
``execute_pipeline``. This module imports no finder and names none. Item 3's
route test calls ``ConjunctionFinder`` directly, which was right for pinning
composition and is exactly what a driver must not do — selecting a finder is
L4's (RULES §8, ADR-0205), and a subsystem that hard-selects one owns a core
mechanism it has no business owning.

``BRAIN_ARCHITECTURE_AUDIT.md`` records arc1 registering a 1,032-line capacity
topology over a 3,756-line solver that never executed through it. A hand-wired
slice reproduces that exactly, and then every downstream number is a claim about
something that did not happen.

**No pre-minted grounding root, and that is a correction to the plan.** Item 4's
acceptance said to mint the document as the grounding root *before* the find.
That is not buildable through ``execution.run``, for three independent reasons
found by reading the code at ``7c4c313``:

1. ``CapacityMMWriter.index`` is per-instance and in-memory, and
   ``execute_pipeline`` constructs its **own** writer — so a root minted by any
   other writer is invisible to its ``if ds not in writer.index`` guard, and a
   document that is also a pipeline start gets minted **twice**, both copies
   parentless, which is the set guard **G7** counts.
2. A caller cannot construct a matching writer anyway: ``_run_leaf_pipeline``
   composes ``run_ref = f"pipelinerun:{request_id}:{leaf_path}:{run_attempt}"``
   internally, so matching it means replicating a private format string.
3. ``CapacityMMWriter.root()`` mints an **isolated node**. Nothing links it to
   the seeded starts; the only linking method, ``link_provenance``, writes an
   XRef *out* to ``knowledge_mm`` rather than an edge *down* to the run.

``root()`` is the solve path's task-level ``raw_task`` ancestor (ADR-0201 DQ-1),
a different thing from "the document", and **it has no production caller at all**
— only ``tests/phase_48/test_knowledge_mm_writer.py``. The document enters here
as an ordinary declared start, seeded by ``execute_pipeline`` like every other
start, and G7 stays green. Pre-minting is meaningful in exactly one case — run 4,
where the find fails, no pipeline runs and no competing writer exists — and that
is filed as its own item rather than smuggled into this one.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from mindsos_capacity.identifiers import (
    NODE_TYPE_DATASTATE_INSTANCE,
    PROP_DATASTATE_INSTANCE_TYPE,
)
from mindsos_intelligence import execution
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import PlanResult

from ._dr_fixtures import (
    DS_AS_OF_DATE,
    DS_DOCUMENT,
    DS_FILING_VERDICT,
    Session,
    build_capacity_layer,
)

#: The single leaf. A Decision Record is one derivation, so one milestone.
LEAF_REF = "mDecisionRecord"


def decision_record_plan(
    *,
    starts: Tuple[str, ...] = (DS_DOCUMENT, DS_AS_OF_DATE),
    target: str = DS_FILING_VERDICT,
) -> PlanResult:
    """The plan for one Decision Record.

    ``start_datastates`` is **plural on purpose**. Two starts make
    ``_select_finder`` choose ``ConjunctionFinder`` by arity — the driver states
    the endpoints and L4 states the finder. Passing ``finder=`` here would be
    the same ownership violation as calling the finder directly, so the key is
    deliberately absent.

    ⚠ No **planner-emitted** plan can express plural starts:
    ``plan_construction._read_solve_target`` and ``::_read_leaf_target`` each
    rebuild a dict holding only the singular ``start_datastate``. A directly
    constructed ``PlanResult`` can, and is gated —
    ``tests/phase_48/test_map_member_multiinput.py``. That gap is
    ``decision-records-l4-multi-input-start``; it is real, it is in the planner
    path, and it does not block this.
    """
    return PlanResult(
        plan_ref="plan:decision_record",
        root_milestone_ref="m0",
        leaf_milestone_refs=[LEAF_REF],
        pipeline_refs={LEAF_REF: f"p{LEAF_REF}"},
        leaf_targets={
            LEAF_REF: {
                "start_datastates": list(starts),
                "target_datastate": target,
            }
        },
    )


class DecisionRecordRun:
    """One driven run: the grounding graphs it produced and the values it left.

    ``graphs`` is what a renderer reads. It is deliberately the ONLY channel —
    a Record rendered from anything beside the graph is the failure the
    acceptance gate exists to catch.
    """

    __slots__ = ("graphs", "pipeline_run_iris", "request_run", "mm")

    def __init__(self, graphs, pipeline_run_iris, request_run, mm) -> None:
        self.graphs = graphs
        self.pipeline_run_iris = pipeline_run_iris
        self.request_run = request_run
        self.mm = mm

    @property
    def graph(self):
        """The single leaf's grounding graph, or ``None`` if nothing ran."""
        return self.graphs[0] if self.graphs else None

    def value_of(self, datastate_iri: str):
        """The value carried by ``datastate_iri``'s instance in the graph.

        **``execution.run`` returns PipelineRun IRIs, not values** — the run
        blackboard is internal and never handed back. That is not a gap to work
        around: a Decision Record is rendered from the grounding graph and
        nothing else, so reading a value here means reading the node the run
        actually wrote. Raises when the type has no instance, rather than
        returning ``None`` — a missing instance and a refused value are
        different facts and a Record must never confuse them.
        """
        graph = self.graph
        if graph is None:
            raise AssertionError(
                f"no grounding graph was written, so {datastate_iri} has no "
                f"instance; the run never reached execute_pipeline"
            )
        matches = [
            n for n in graph.nodes.values()
            if n.type_name == NODE_TYPE_DATASTATE_INSTANCE
            and (n.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE) == datastate_iri
        ]
        if not matches:
            raise AssertionError(
                f"{datastate_iri} has no instance in the run graph; present: "
                f"{sorted({(n.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE) for n in graph.nodes.values() if n.type_name == NODE_TYPE_DATASTATE_INSTANCE})}"
            )
        if len(matches) > 1:
            raise AssertionError(
                f"{datastate_iri} has {len(matches)} instances in one run graph "
                f"— one value per DataState IRI is the L-1 invariant"
            )
        return matches[0].value


def run_decision_record(
    kl: Any,
    seed: Dict[str, Any],
    *,
    request_id: str = "dr",
    session: Optional[Session] = None,
    plan: Optional[PlanResult] = None,
    graphs: Optional[List[Any]] = None,
) -> DecisionRecordRun:
    """Drive one Decision Record end to end and return its grounding graphs.

    ``kl`` is the :class:`~mindsos_knowledge.knowledge_layer.KnowledgeLayer`
    holding the authority — bound onto the dispatcher so the lookup body reaches
    it through ``context.kl``. Passing ``kl=None`` is the outage case and is a
    supported input, not a misuse: it is how run-4-adjacent behaviour is
    exercised without inventing a fault injector.

    ``seed`` maps start DataState IRIs to their values. ``execution.run`` enters
    real-solve mode only when ``mm`` **and** ``solve_seed`` are both present and
    the plan names an endpoint; a plan with none falls back to the notional
    record, which writes no grounding graph and would make every assertion below
    vacuous.
    """
    session = session or Session()
    capacity_layer, session = build_capacity_layer(session)
    mm = MentalModel(session_id=session.session_id, user_id=session.user_id)
    dispatcher = L4Dispatcher(capacity_layer, session=session, kl=kl)
    writer = ChainArtifactWriter(mm, request_id)
    request_run = writer.emit_request_run()
    # A caller may supply the list so it still holds the run's graph when this
    # RAISES — run 4 leaves a manifest-only graph and then propagates
    # ``LeafPipelineNotFound``, so the only way to see that graph is to own the
    # list the executor appends to.
    graphs = [] if graphs is None else graphs

    pipeline_run_iris = execution.run(
        dispatcher,
        writer,
        plan if plan is not None else decision_record_plan(),
        request_run,
        mm=mm,
        run_scope=request_id,
        solve_seed=dict(seed),
        capacity_graphs=graphs,
    )
    return DecisionRecordRun(graphs, pipeline_run_iris, request_run, mm)


__all__ = [
    "LEAF_REF",
    "DecisionRecordRun",
    "decision_record_plan",
    "run_decision_record",
]
