"""Decision Records v0 — the day-one route probe.

**This is a probe, not the run driver.** It calls ``ConjunctionFinder``
directly on purpose, to answer one question both lanes are blocked on and
that nothing in either lane has ever tested: *can the finder wire a
decision capacity's three inputs to their producers, and does the run
reach the grounding graph?* Every pipeline in ``tests/llm_seam/`` is
hand-built; nothing has ever invoked a finder.

Selecting a finder is **L4's** (``mindsos_intelligence.execution._select_finder``;
``find_pipeline``'s own docstring: *"selected by L4"*). A run driver in this
lane that hard-selected ``ConjunctionFinder`` would be a subsystem owning a
core mechanism (RULES §8, ADR-0205). So this file owns nothing: it is a
diagnostic that reports on core's open defect **D-A**
(``CORE_VERIFIED_FINDINGS.md``: *"the sound finder was never wired to
anything that executes"* — a sentence that is itself stale; see the
handoff §1.3).

⚠ CORRECTED 2026-08-11 — an earlier revision ended *"and the real driver
waits on the L4 change."* **It does not.** A caller may construct a
``PlanResult`` carrying plural ``leaf_targets[...]["start_datastates"]``
and hand it to ``execution.run(..., mm=...)``, which selects
``ConjunctionFinder`` by arity and grounds the run —
``tests/phase_48/test_map_member_multiinput.py`` does exactly that and is
gated. The run driver therefore needs no core change and does not call
the finder directly. Detail:
``confirmation_docs/DECISION_RECORDS_V0_PLAN.md`` §1.1.

**Realms.** Everything Local (owner decision, 2026-08-09), superseding the
slice plan's mixed-realm table — that table is unbuildable as written:
``register_capacity`` validates inputs/outputs against the *target realm's*
DataState graph and ``_mirror_global_datastates`` mirrors Global→Local only,
so a Global capacity cannot declare a Local-only DataState. Consequence:
plan guard **G8** goes vacuous (nothing Global to shadow) and is replaced
here by **G8′** — assert nothing is registered Global at the lookup or
decision IRIs, so a later realm move fails loud instead of silently
shadowing the authority.

**IRI shape.** ``capacity:decision:*`` (owner decision, 2026-08-09), on the
grounds that it was the only shape where both rules agree: ``family_rule_for``
returns VERDICT via the category key, and ``origin_v0.DECISION_SHAPED_CATEGORIES``
— which matches on **category only** — sees the capacity, so the D15 opaque
guard can fire. ``capacity:dec_rec:*`` would silently get ``DATASTATE_MARKER``
and the guard would pass vacuously.

⚠ PARTLY SUPERSEDED 2026-08-12 by **ADR-0208 §D1**, and only for the LOOKUP.
``family_rule_for`` has no caller in any shipped module, so what it returns is
not load-bearing; and ``DECISION_SHAPED_CATEGORIES`` guards the capacity that
COMPARES a value, which is the criterion, not the lookup. The shipped lookup is
``capacity:retrieval:*`` and gets ``OPTIONAL_RETURN``. **The criterion stays
``capacity:decision:*`` and the assertions below are unchanged** — they are
about this file's own constants, which are the probe's, not the ship's. Cost
noted and unchanged for the criterion: ``decision`` is not one of
``FUNCTIONAL_CATEGORIES``' thirteen, so registering one mints a category graph
lazily (``phase1_v0`` and ``orchestration_v0`` already do).

**The two configurations exist because the plan contradicts itself.** Its
§Shape says *one* lookup capacity producing the limit and the version as
separate DataStates (⟹ 3 inputs, **2** producers); its route-check
paragraph says *"the four capacities"* and *"three inputs to their three
producers"* (⟹ 2 lookups). Config A is the Shape; config B is the
route-check sentence. A is the design and is also the shape most likely to
trip core defect **D-E** (a capacity reached twice while under
construction can be appended to ``steps`` twice, and ``execute_pipeline``
would then run the lookup twice with a one-slot blackboard silently
overwriting). Both are asserted so the answer is not a guess.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    Capacity,
    CapacityLayer,
    ConjunctionFinder,
    DataState,
    INPUT_GROUP_ALL_REQUIRED,
    ShapeDescriptor,
    family_rule_for,
)
from mindsos_capacity.family_rules import FamilyDontKnowShape
from mindsos_capacity.identifiers import (
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_DATASTATE_INSTANCE,
    PROP_CAPACITY_INSTANCE_TYPE,
    PROP_DATASTATE_INSTANCE_TYPE,
)
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.pipeline_execution import execute_pipeline


# ── DataState vocabulary ──────────────────────────────────────────────
#
# Every distinct value gets its own type: the blackboard is one value per
# DataState IRI and ``CapacityMMWriter.index[...]`` overwrites. Reusing a
# type for two values is the nilm blocker.

DS_DOCUMENT = "datastate:dr.document"
DS_POLICY_ID = "datastate:dr.policy_id"
DS_AS_OF_DATE = "datastate:dr.as_of_date"
DS_GROSS_INCOME = "datastate:dr.gross_income"
DS_GROSS_INCOME_ORIGIN = "datastate:dr.gross_income_origin"
DS_FILING_THRESHOLD = "datastate:dr.filing_threshold"
DS_POLICY_VERSION = "datastate:dr.policy_version"
DS_FILING_VERDICT = "datastate:dr.filing_verdict"

CAP_READER = "capacity:comprehension:dr_read_gross_income"
CAP_LOOKUP = "capacity:decision:dr_lookup_filing_threshold"
CAP_LOOKUP_LIMIT = "capacity:decision:dr_lookup_limit"
CAP_LOOKUP_VERSION = "capacity:decision:dr_lookup_version"
CAP_DECISION = "capacity:decision:dr_filing_requirement"

USER = "dr_probe_user"


class _Session:
    """Minimal SessionProtocol stand-in (mirrors tests/phase_30/_fixtures)."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.session_id = f"sess:{user_id}"

    def has(self, capability: str) -> bool:
        return True


def _ds(iri: str, elem: str, description: str) -> DataState:
    name = iri.split(":", 1)[1]
    return DataState(
        name=name,
        shape=ShapeDescriptor.scalar(elem),
        description=description,
    )


def _cap(iri: str, inputs, outputs, impl) -> Capacity:
    category, name = iri[len("capacity:"):].split(":", 1)
    return Capacity(
        name=name,
        category=category,
        inputs=tuple(inputs),
        outputs=tuple(outputs),
        input_group=INPUT_GROUP_ALL_REQUIRED,
        implementation=impl,
    )


class _Dispatcher:
    """Calls each capacity's bound implementation. Records every call.

    Deliberately thin: the probe is about the finder and the grounding
    graph, and a real ``L4Dispatcher`` would drag session/KL/MM-handle
    construction in without changing either answer. It DOES go through the
    registered declaration, so a capacity the finder wired to the wrong
    inputs still shows up here as a wrong ``inputs`` dict.
    """

    def __init__(self, capacity_layer, session) -> None:
        self._cl = capacity_layer
        self._session = session
        self.calls = []

    def dispatch(self, capacity_iri, inputs, *, cancel_token=None,
                 request_id=None, step_id=None):
        declaration = self._cl.resolve_declaration(
            capacity_iri, session=self._session
        )
        self.calls.append((capacity_iri, dict(inputs)))
        outputs = declaration.implementation(**inputs)
        return _Result(success=True, outputs=outputs)


class _Result:
    def __init__(self, success, outputs=None, error=None):
        self.success = success
        self.outputs = outputs or {}
        self.error = error
        self.needs_input = None


# ── fixtures ──────────────────────────────────────────────────────────


def _register_datastates(cl, session):
    for iri, elem, desc in (
        (DS_DOCUMENT, "str", "the filed return"),
        (DS_POLICY_ID, "str", "the policy consulted"),
        (DS_AS_OF_DATE, "str", "the date the question is asked about"),
        (DS_GROSS_INCOME, "int", "the filer's gross income"),
        (DS_GROSS_INCOME_ORIGIN, "str", "how the gross income was established"),
        (DS_FILING_THRESHOLD, "int", "the filing threshold in force"),
        (DS_POLICY_VERSION, "str", "the edition of the policy consulted"),
        (DS_FILING_VERDICT, "str", "whether a return must be filed"),
    ):
        cl.register_datastate(
            _ds(iri, elem, desc), session=session, allow_new_realm=True
        )


def _reader(**kw):
    return {DS_GROSS_INCOME: 61000, DS_GROSS_INCOME_ORIGIN: "read_by_model"}


def _lookup_both(**kw):
    return {DS_FILING_THRESHOLD: 29200, DS_POLICY_VERSION: "2024.1"}


def _lookup_limit(**kw):
    return {DS_FILING_THRESHOLD: 29200}


def _lookup_version(**kw):
    return {DS_POLICY_VERSION: "2024.1"}


def _decision(**kw):
    return {DS_FILING_VERDICT: "must file"}


def _layer_config_a():
    """The plan's §Shape: one lookup, two outputs. 3 inputs, 2 producers."""
    cl = CapacityLayer()
    session = _Session(USER)
    _register_datastates(cl, session)
    cl.register_capacity(
        _cap(CAP_READER, (DS_DOCUMENT,),
             (DS_GROSS_INCOME, DS_GROSS_INCOME_ORIGIN), _reader),
        session=session,
    )
    cl.register_capacity(
        _cap(CAP_LOOKUP, (DS_POLICY_ID, DS_AS_OF_DATE),
             (DS_FILING_THRESHOLD, DS_POLICY_VERSION), _lookup_both),
        session=session,
    )
    cl.register_capacity(
        _cap(CAP_DECISION,
             (DS_GROSS_INCOME, DS_FILING_THRESHOLD, DS_POLICY_VERSION),
             (DS_FILING_VERDICT,), _decision),
        session=session,
    )
    return cl, session


def _layer_config_b():
    """The plan's route-check sentence: four capacities, 3 distinct producers."""
    cl = CapacityLayer()
    session = _Session(USER)
    _register_datastates(cl, session)
    cl.register_capacity(
        _cap(CAP_READER, (DS_DOCUMENT,),
             (DS_GROSS_INCOME, DS_GROSS_INCOME_ORIGIN), _reader),
        session=session,
    )
    cl.register_capacity(
        _cap(CAP_LOOKUP_LIMIT, (DS_POLICY_ID, DS_AS_OF_DATE),
             (DS_FILING_THRESHOLD,), _lookup_limit),
        session=session,
    )
    cl.register_capacity(
        _cap(CAP_LOOKUP_VERSION, (DS_POLICY_ID, DS_AS_OF_DATE),
             (DS_POLICY_VERSION,), _lookup_version),
        session=session,
    )
    cl.register_capacity(
        _cap(CAP_DECISION,
             (DS_GROSS_INCOME, DS_FILING_THRESHOLD, DS_POLICY_VERSION),
             (DS_FILING_VERDICT,), _decision),
        session=session,
    )
    return cl, session


STARTS = (DS_DOCUMENT, DS_POLICY_ID, DS_AS_OF_DATE)

INITIAL = {
    DS_DOCUMENT: "gross income of 61,000 for tax year 2024",
    DS_POLICY_ID: "policy:filing_threshold",
    DS_AS_OF_DATE: "2024-04-15",
}


def _find(cl, session):
    return ConjunctionFinder().find(
        cl, session=session,
        start_datastates=STARTS,
        target_datastate=DS_FILING_VERDICT,
    )


def _step_for(pipeline, capacity_iri):
    matches = [s for s in pipeline.steps if s.capacity_iri == capacity_iri]
    assert matches, (
        f"{capacity_iri} absent from the composed route: "
        f"{[s.capacity_iri for s in pipeline.steps]}"
    )
    assert len(matches) == 1, (
        f"{capacity_iri} appears {len(matches)} times in one Pipeline — "
        "core defect D-E (a capacity reached twice while under construction "
        "is appended twice; execute_pipeline then runs it twice and the "
        "one-slot blackboard overwrites the first result)"
    )
    return matches[0]


# ── 1. the finder wires all three inputs ──────────────────────────────


@pytest.mark.parametrize(
    "build,label",
    [(_layer_config_a, "config-A-one-lookup"),
     (_layer_config_b, "config-B-two-lookups")],
)
def test_conjunction_finder_wires_all_three_decision_inputs(build, label):
    """THE question. If this is red, every downstream item in the plan is void."""
    cl, session = build()
    verdict = _find(cl, session)

    assert verdict.found, (
        f"[{label}] no route to the verdict from three starts: "
        f"{getattr(verdict, 'reason', None)} / {getattr(verdict, 'detail', None)}"
    )
    step = _step_for(verdict.pipeline, CAP_DECISION)
    assert set(step.input_datastates) == {
        DS_GROSS_INCOME, DS_FILING_THRESHOLD, DS_POLICY_VERSION
    }, f"[{label}] decision inputs under-wired: {step.input_datastates}"


@pytest.mark.parametrize(
    "build,label",
    [(_layer_config_a, "config-A-one-lookup"),
     (_layer_config_b, "config-B-two-lookups")],
)
def test_every_producer_is_wired_to_the_decision(build, label):
    """Each decision input is fed by an edge from the step that produces it."""
    cl, session = build()
    pipeline = _find(cl, session).pipeline
    idx = {s.capacity_iri: i for i, s in enumerate(pipeline.steps)}
    consumer = idx[CAP_DECISION]
    incoming = {e.datastate for e in pipeline.edges if e.consumer == consumer}
    assert incoming == {
        DS_GROSS_INCOME, DS_FILING_THRESHOLD, DS_POLICY_VERSION
    }, f"[{label}] DAG edges into the decision: {sorted(incoming)}"


def test_a_single_start_finds_no_route_at_all():
    """Why three starts — and it is NOT the reason the plan gives.

    **Observed in a pre-filter run, 2026-08-09 — NOT gated.** The assertion
    below is the real check; if the Linux gate disagrees with the paragraph
    that follows, this test goes red and the paragraph is what is wrong.

    The plan says a single start selects BFS and
    the decision's *"three inputs from three producers would be silently
    dropped"*. In this topology it does not silently drop anything: BFS
    returns ``bfs_exhausted``, **not found**. ``policy_id`` and
    ``as_of_date`` are not reachable from the document, so the lookup can
    never fire and there is no route to under-wire.

    The silent-under-wiring hazard D-A describes is real in general — a
    capacity whose other inputs *are* reachable gets fired on one of them.
    It is simply not the failure mode this slice would have hit. So three
    starts is about being able to compose **at all**, not about dodging a
    silent drop. Corrected here because the plan's version of this is the
    kind of inherited claim that gets repeated into a design doc.
    """
    from mindsos_capacity import find_pipeline
    from mindsos_capacity.pipeline import FIND_BFS_EXHAUSTED

    cl, session = _layer_config_a()
    verdict = find_pipeline(
        cl, session=session,
        start_datastate=DS_DOCUMENT,
        target_datastate=DS_FILING_VERDICT,
    )
    assert not verdict.found
    assert verdict.reason == FIND_BFS_EXHAUSTED


# ── 2. the route executes and reaches the grounding graph ─────────────


def _run(cl, session, pipeline):
    mm = MentalModel(session_id=session.session_id, user_id=session.user_id)
    dispatcher = _Dispatcher(cl, session)
    result = execute_pipeline(
        dispatcher, pipeline, INITIAL,
        request_id="dr-probe",
        mm=mm,
        pipeline_run_ref="pipelinerun:dr-probe-1",
    )
    return result, dispatcher


@pytest.mark.parametrize(
    "build,label",
    [(_layer_config_a, "config-A-one-lookup"),
     (_layer_config_b, "config-B-two-lookups")],
)
def test_found_route_executes_end_to_end(build, label):
    cl, session = build()
    pipeline = _find(cl, session).pipeline
    result, dispatcher = _run(cl, session, pipeline)

    assert result.success, (
        f"[{label}] failed at {result.failed_step}: {result.error}"
    )
    assert result.outputs[DS_FILING_VERDICT] == "must file"
    decision_calls = [c for c in dispatcher.calls if c[0] == CAP_DECISION]
    assert len(decision_calls) == 1
    assert set(decision_calls[0][1]) == {
        DS_GROSS_INCOME, DS_FILING_THRESHOLD, DS_POLICY_VERSION
    }, f"[{label}] decision dispatched with {sorted(decision_calls[0][1])}"


@pytest.mark.parametrize(
    "build,label",
    [(_layer_config_a, "config-A-one-lookup"),
     (_layer_config_b, "config-B-two-lookups")],
)
def test_grounding_graph_wires_all_three_into_the_decision(build, label):
    """The acceptance gate in miniature: the derivation is IN the graph.

    Not "a Record could be rendered" — that the three values the money
    sentence names each have a CONSUMES edge into the decision's own
    CapacityInstance, in the per-run graph, from the instance that
    produced them.
    """
    cl, session = build()
    pipeline = _find(cl, session).pipeline
    result, _ = _run(cl, session, pipeline)
    graph = result.capacity_graph
    assert graph is not None, f"[{label}] no grounding graph was written"

    decision_nodes = [
        n for n in graph.nodes.values()
        if n.type_name == NODE_TYPE_CAPACITY_INSTANCE
        and (n.properties or {}).get(PROP_CAPACITY_INSTANCE_TYPE) == CAP_DECISION
    ]
    assert len(decision_nodes) == 1, (
        f"[{label}] {len(decision_nodes)} decision instances in the run graph"
    )
    decision = decision_nodes[0]

    # Intra-graph ``Edge`` carries ``.source`` / ``.target`` Nodes and
    # ``.type_name`` — the ``source_node_id`` / ``edge_type`` attribute names
    # belong to ``IntergraphEdge``, which is not what the run graph uses.
    consumed_types = set()
    for edge in graph.edges.values():
        if edge.type_name != EDGE_CONSUMES:
            continue
        if edge.target.node_id != decision.node_id:
            continue
        producer = edge.source
        assert producer.type_name == NODE_TYPE_DATASTATE_INSTANCE
        consumed_types.add((producer.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE))

    assert consumed_types == {
        DS_GROSS_INCOME, DS_FILING_THRESHOLD, DS_POLICY_VERSION
    }, f"[{label}] the decision's derivation names {sorted(consumed_types)}"


@pytest.mark.parametrize(
    "build,label",
    [(_layer_config_a, "config-A-one-lookup"),
     (_layer_config_b, "config-B-two-lookups")],
)
def test_g7_every_attributed_value_reaches_a_declared_start(build, label):
    """G7, restated for three starts.

    The plan words G7 as *"a path back to the grounding root"* — singular.
    With three starts there are three seeded roots, so as written it is
    unsatisfiable for anything descended from ``policy_id`` / ``as_of_date``,
    which is the limit and the version: the two values the money sentence
    leans on hardest. Restated: every attributed instance reaches **a
    declared start instance**, and the set of parentless instances is
    **exactly** the declared starts — which still catches the real failure
    (a value that should have been derived arriving as a start input,
    minted by ``seed()`` with no incoming edge and permanently
    unattributable).
    """
    cl, session = build()
    pipeline = _find(cl, session).pipeline
    result, _ = _run(cl, session, pipeline)
    graph = result.capacity_graph

    has_incoming = {e.target.node_id for e in graph.edges.values()}
    parentless = {
        (n.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE)
        for n in graph.nodes.values()
        if n.type_name == NODE_TYPE_DATASTATE_INSTANCE
        and n.node_id not in has_incoming
    }
    assert parentless == set(STARTS), (
        f"[{label}] parentless (unattributable) values: {sorted(parentless)}; "
        f"declared starts: {sorted(STARTS)}"
    )

    produced = {
        (e.target.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE)
        for e in graph.edges.values()
        if e.type_name == EDGE_PRODUCES
    }
    for attributed in (DS_GROSS_INCOME, DS_FILING_THRESHOLD, DS_POLICY_VERSION):
        assert attributed in produced, (
            f"[{label}] {attributed} is attributed by the Record but was "
            "never PRODUCED by a capacity instance"
        )


# ── 3. the registration rules the plan depends on ─────────────────────


def test_decision_iri_gets_the_verdict_family_rule():
    """``capacity:decision:*`` resolves to VERDICT; ``capacity:dec_rec:*`` does not.

    The second half is the reason the IRI shape was not a free choice: a
    ``dec_rec`` category matches no ``FAMILY_RULES`` key by either route and
    falls through to the permissive default with only a ``log.info``.
    """
    assert family_rule_for(CAP_DECISION) is FamilyDontKnowShape.VERDICT
    assert family_rule_for(CAP_LOOKUP) is FamilyDontKnowShape.VERDICT
    assert (
        family_rule_for("capacity:dec_rec:dr_filing_requirement")
        is FamilyDontKnowShape.DATASTATE_MARKER
    )


def test_decision_iris_are_visible_to_the_d15_opaque_guard():
    """``DECISION_SHAPED_CATEGORIES`` matches on category, so the IRI must too.

    Guards the vacuous pass: a decision capacity outside these categories is
    invisible to ``opaque_into_decision`` and the guard reports green having
    inspected nothing.
    """
    # CORRECTED 2026-08-12 — ``origin_v0`` landed on ``main`` at ``a310958``
    # (plan item 1), so this stopped being a skip and the assertion below has
    # been running since. The guard is kept rather than turned into a plain
    # import because the module is an opt-in builtin, not a bootstrapped one.
    origin_v0 = pytest.importorskip(
        "mindsos_capacity.builtins.origin_v0",
        reason="origin_v0 is an opt-in builtin; absent only in a partial tree",
    )
    DECISION_SHAPED_CATEGORIES = origin_v0.DECISION_SHAPED_CATEGORIES

    category = CAP_DECISION[len("capacity:"):].split(":", 1)[0]
    assert category in DECISION_SHAPED_CATEGORIES
    assert "dec_rec" not in DECISION_SHAPED_CATEGORIES


def test_g8_prime_nothing_is_registered_global():
    """G8′ — replaces plan guard G8 under the all-Local decision.

    G8 asserted the lookup and decision resolve **Global**; with everything
    Local there is no Global capacity to shadow, so G8 is vacuous. What is
    still worth asserting is the inverse: nothing is registered Global at
    these IRIs, so the day realms move, the union view's shadow-not-merge
    rule (``views.py:216``) cannot silently swap the authority under us.
    """
    cl, _ = _layer_config_a()
    global_view = cl.global_view()
    for iri in (CAP_LOOKUP, CAP_DECISION, CAP_READER):
        assert global_view.get_capacity(iri) is None, (
            f"{iri} is registered Global; Local would shadow it entirely, "
            "node and edges, with no signal"
        )


# ── 4. D-A evidence for the L4 CR request ─────────────────────────────


def test_l4_selects_conjunction_on_plural_starts():
    """L4 already knows how to CHOOSE the sound finder."""
    from mindsos_intelligence.execution import _select_finder, FINDER_CONJUNCTION

    assert _select_finder(STARTS, None, "probe") == FINDER_CONJUNCTION


def test_l4_cannot_express_plural_starts_this_is_D_A():
    """...and the PLANNER cannot EXPRESS it.

    ``_read_solve_target`` and ``_read_leaf_target`` each rebuild a dict
    holding only the singular ``start_datastate``, so a planner emitting
    plural starts has them dropped before ``_select_finder`` is ever
    reached. That gap is real and this test pins it.

    ⚠ CORRECTED 2026-08-11 — an earlier revision of this docstring said
    *"``_endpoint_starts`` accepts plural; nothing can hand it any."*
    **That sentence is false**, and ``STATE.json`` and the v0 handoff both
    inherited it. ``tests/phase_48/test_map_member_multiinput.py``
    (``test_plain_leaf_plural_starts_composes_multi_input`` and three
    others) constructs a ``PlanResult`` directly with plural
    ``leaf_targets[...]["start_datastates"]`` and runs it through
    ``execution.run(..., mm=...)`` — ``_endpoint_starts`` →
    ``_select_finder`` → ``ConjunctionFinder`` → ``execute_pipeline``
    WITH grounding. Shipped and gated.

    So the accurate statement is narrower: **no planner-emitted plan can
    express plural starts.** A caller that builds its own ``PlanResult``
    can, which is why the Decision Records run driver needs no core change
    and never calls the finder directly
    (``confirmation_docs/DECISION_RECORDS_V0_PLAN.md`` §1.1).

    When core lands the planner passthrough, this test goes red. That is
    the signal to retire the probe.
    """
    from mindsos_intelligence.plan_construction import (
        _read_leaf_target,
        _read_solve_target,
    )

    plural = {
        "start_datastates": list(STARTS),
        "target_datastate": DS_FILING_VERDICT,
    }
    assert _read_solve_target({"solve_target": plural}) is None
    assert _read_leaf_target({"leaf_target": plural}) is None

    singular = {
        "start_datastate": DS_DOCUMENT,
        "target_datastate": DS_FILING_VERDICT,
    }
    assert _read_solve_target({"solve_target": singular}) == singular
