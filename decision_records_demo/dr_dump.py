"""dr_dump — dump every grounding graph a Decision Records run leaves, raw.

This is the RULES §12 command for the Decision Records lane: it runs the real
core machinery (`execution.run` → `execute_pipeline`, an in-memory
`MentalModel`, no FalkorDB) over a small demo fixture and prints what lands in
`capacity_mm`, unedited. Until this existed, every check was the build lane
reading its own output.

RULES §11 seam, stated up front: the section headers, the `graph[n]` /
`node` / `edge` prefixes, the stage labels and the field ordering are THIS
SCRIPT'S framing. Every value after a colon is `repr()` of what the system
emitted — node types, IRIs, properties, values, edge types — with nothing
translated, prettified or omitted. Ugly is information.

Shapes (the demo-critical sweep's evidence set, coordination §20–§22):

    leaf        one pipeline run: exposure → verdict
    claim       a map over three exposures + the fold that concludes the claim
    noroute     an unroutable request: the run raises, and the graph left
                behind is manifest-only (run 4's shape)
    replan      the claim run twice — run_attempt 0 then 1, same MM: every
                re-attempt grounds fresh graphs, nothing is overwritten (R2)
    retry       one member fails once then succeeds (run-ref suffix :r1), then
                a TARGETED re-exec of that member at run_attempt 1 splices its
                fresh verdict and re-folds (R3). A rejected attempt's graph
                stays in capacity_mm but not in the collected/persisted list —
                the delta is printed, not hidden
    memberpartial
                a member fails at MEMBER_RETRY_CAP: it STOPS IN PLACE with its
                final attempt's graph retained, its siblings run, and the fold
                stops pre-dispatch with RunStopped(partial_domain) over the
                full member-id list (ADR-0201 am-6, which retired
                MemberAbortError as a raiser; this shape replaces the aborting
                memberabort shape that pinned R4's old behaviour)
    needsinput  a step returns the NeedsInput verdict: the walk halts and the
                graph records RunStopped(needs_input) with the missing IRI (R7)
    refusal     the policy lookup finds NO edition in force: the run SUCCEEDS
                and the limit's origin record carries the refusal — in-band,
                never an exception (R8, leaf level; member-level in-band
                refusal is core-supported since ADR-0209 — its demo
                consumption is the routing content, a later slice)
    outage      the store cannot be consulted: (a) no store at all, (b) the
                store contradicts itself (AmbiguousEditionsError). Both RAISE
                and the graph records RunStopped — an outage is never a
                finding about the case (R6, both raising paths)
    boundary    the input-boundary axis: a claim with ZERO exposures — the
                FOLD stops pre-dispatch with RunStopped(empty_domain), the
                reducer is never asked (ADR-0201 am-5; the demo reducer's own
                zero-verdict guard stays as defence in depth but no longer
                fires here) — and a claim with ONE exposure
    codec       encoder-only; no round-trip. Walks EVERY graph every other
                shape leaves and runs the persistence encoder over every node
                value (the live FalkorDB round-trip is the persistence-smoke
                item, not the sweep's)
    all         every shape above, in order

Not built, on purpose: a `cancel` shape. `cancel_token` never threads through
`execution.run` (it enters at `execute_pipeline` / the submind arbiter), so a
cancellation shape would have to bypass the run path and would demonstrate the
executor while wearing the demo's name — recorded empty-with-reason
(coordination §21 Q2, §22.4).

Run it from a checkout root (the demo's own worktree) with the core packages
importable:

    PYTHONPATH=. python decision_records_demo/dr_dump.py all

This file is demo code. It registers its own DataStates and capacities into a
Local realm and never edits `mindsos_*` (RULES §3).
"""

from __future__ import annotations

import sys

from mindsos_capacity import CapacityLayer
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import CATEGORY_DERIVATION, capacity_iri, datastate_iri
from mindsos_capacity.needs_input import NeedsInput
from mindsos_intelligence import execution
from mindsos_intelligence.capacity_persister import make_node_value_encoder
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.execution import LeafPipelineNotFound
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import PlanResult
from mindsos_knowledge.identifiers import ROLE_POLICIES
from mindsos_knowledge.knowledge_layer import KnowledgeLayer
from mindsos_knowledge.policies import write_policy_edition

DS_CLAIM_EXPOSURES = datastate_iri("drdemo.claim_exposures")
DS_EXPOSURE = datastate_iri("drdemo.exposure")
DS_VERDICT = datastate_iri("drdemo.exposure_verdict")
DS_VERDICTS = datastate_iri("drdemo.exposure_verdicts")
DS_CONCLUSION = datastate_iri("drdemo.claim_conclusion")
DS_UNREACHED = datastate_iri("drdemo.nothing_produces_this")
DS_POLICY_AS_OF = datastate_iri("drdemo.policy_as_of")
DS_DWELLING_LIMIT = datastate_iri("drdemo.dwelling_limit")

CAP_DECIDE = capacity_iri(CATEGORY_DERIVATION, "drdemo_decide_exposure")
CAP_CONCLUDE = capacity_iri(CATEGORY_DERIVATION, "drdemo_conclude_claim")

POLICY_ID = "policy:drdemo.dwelling_limit"
POLICY_PHRASE = "the dwelling-coverage limit policy"

DESCRIPTIONS = {
    "drdemo.claim_exposures": "the exposures the claim was split into",
    "drdemo.exposure": "one exposure, as filed",
    "drdemo.exposure_verdict": "what was decided about one exposure",
    "drdemo.exposure_verdicts": "each exposure's verdict, in order",
    "drdemo.claim_conclusion": "what the claim's verdicts add up to",
    "drdemo.nothing_produces_this": "something nothing registered can produce",
}
COLLECTIONS = {
    "drdemo.claim_exposures": dict(collection=True, member_ds=DS_EXPOSURE),
    "drdemo.exposure_verdicts": dict(collection=True, member_ds=DS_VERDICT),
}

EXPOSURES = [
    {"claimant": "A. Silva", "coverage": "dwelling", "loss": "hail, 12 March"},
    {"claimant": "A. Silva", "coverage": "contents", "loss": "water, 12 March"},
    {"claimant": "B. Osei", "coverage": "dwelling", "loss": "hail, 12 March"},
]

EDITION_2023 = dict(
    version="2023.1",
    in_force_from="2023-01-01",
    in_force_to="2023-12-31",
    stated_value=350000,
    text="The dwelling coverage limit is 350,000.",
)
EDITION_2024 = dict(
    version="2024.1",
    in_force_from="2024-01-01",
    in_force_to=None,
    stated_value=375000,
    text="The dwelling coverage limit is 375,000.",
)
EDITION_2025_OVERLAPPING = dict(
    version="2025.1",
    in_force_from="2025-01-01",
    in_force_to=None,
    stated_value=390000,
    text="The dwelling coverage limit is 390,000.",
)


class _Session:
    session_id = "drdemo-session"
    user_id = "drdemo-user"
    actor_role = "user"
    capabilities: set = set()

    def has(self, capability: str) -> bool:
        return False


def _decide(**kwargs):
    exposure = kwargs.get(DS_EXPOSURE)
    return {DS_VERDICT: {"exposure": exposure, "decision": "payable"}}


def _make_flaky_decide(failures_left: dict):
    """A decide body that RAISES while ``failures_left[claimant/coverage] > 0``.

    The raise is L-2's step-failure path: the walk records ``RunStopped``
    (``step_failed``), the member attempt is rejected, and the retry loop
    re-runs it under the next ``:r{idx}`` ref.
    """

    def _flaky(**kwargs):
        exposure = kwargs.get(DS_EXPOSURE) or {}
        key = f"{exposure.get('claimant')}/{exposure.get('coverage')}"
        if failures_left.get(key, 0) > 0:
            failures_left[key] -= 1
            raise RuntimeError(
                f"simulated compute failure deciding {key} (deterministic for this attempt)"
            )
        return {DS_VERDICT: {"exposure": exposure, "decision": "payable"}}

    return _flaky


def _conclude(**kwargs):
    verdicts = kwargs.get(DS_VERDICTS)
    if not verdicts:
        raise ValueError("refusing to conclude a claim from zero exposure verdicts")
    return {DS_CONCLUSION: {"claim_decision": "payable"}}


def _ask(**kwargs):
    return NeedsInput(
        question="Which policy edition applies to this exposure?",
        missing=DS_POLICY_AS_OF,
    )


def _build_kl(*editions):
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(None, ROLE_POLICIES, "global")
    for edition in editions:
        write_policy_edition(handle, policy_id=POLICY_ID, **edition)
    return kl


def _policy_datastates():
    from mindsos_capacity.builtins.policy_lookup_v0 import policy_limit_datastates

    limit, origin = policy_limit_datastates(
        limit_name="drdemo.dwelling_limit",
        limit_elem="int",
        limit_description="the dwelling coverage limit in force",
    )
    as_of = DataState(
        name="drdemo.policy_as_of",
        shape=ShapeDescriptor.scalar("str"),
        description="the date the coverage question is asked about",
    )
    return [limit, origin, as_of]


def _lookup_declaration():
    from mindsos_capacity.builtins.policy_lookup_v0 import build_policy_limit_lookup

    return build_policy_limit_lookup(
        name="drdemo_lookup_dwelling_limit",
        policy_id=POLICY_ID,
        source_identity_phrase=POLICY_PHRASE,
        question="What dwelling coverage limit was in force on {as_of}?",
        limit_datastate_iri=DS_DWELLING_LIMIT,
        as_of_datastate_iri=DS_POLICY_AS_OF,
    )


def _decide_declaration(implementation):
    return Capacity(
        name="drdemo_decide_exposure",
        category=CATEGORY_DERIVATION,
        inputs=(DS_EXPOSURE,),
        outputs=(DS_VERDICT,),
        implementation=implementation,
        description="one exposure -> its verdict",
        printable_phrase="deciding one exposure on its coverage",
    )


def _conclude_declaration():
    return Capacity(
        name="drdemo_conclude_claim",
        category=CATEGORY_DERIVATION,
        inputs=(DS_VERDICTS,),
        outputs=(DS_CONCLUSION,),
        implementation=_conclude,
        description="the ordered verdicts -> the claim conclusion",
        printable_phrase="concluding the claim from its exposure verdicts",
    )


def _harness(capacities=None, extra_datastates=(), kl=None):
    """Register the demo vocabulary + exactly ``capacities``, return the rig.

    ``capacities`` defaults to the decide + conclude pair. Passing an explicit
    list keeps each shape's route unambiguous — a shape that needs the asking
    capacity must not also register the answering one for the same target.
    """
    session = _Session()
    layer = CapacityLayer()
    for name, description in DESCRIPTIONS.items():
        layer.register_datastate(
            DataState(
                name=name,
                shape=ShapeDescriptor.opaque(name),
                description=description,
                provenance_category=CATEGORY_DERIVATION,
                **COLLECTIONS.get(name, {}),
            ),
            session=session,
            allow_new_realm=True,
        )
    for datastate in extra_datastates:
        layer.register_datastate(datastate, session=session, allow_new_realm=True)
    if capacities is None:
        capacities = [_decide_declaration(_decide), _conclude_declaration()]
    for cap in capacities:
        layer.register_capacity(cap, session=session)
    mm = MentalModel(session_id="drdemo-session", user_id="drdemo-user")
    dispatcher = L4Dispatcher(layer, session=session, kl=kl)
    writer = ChainArtifactWriter(mm, "drdemo-task")
    return mm, dispatcher, writer, writer.emit_request_run()


def _leaf_plan(plan_ref: str, target: str, start: str = DS_EXPOSURE) -> PlanResult:
    return PlanResult(
        plan_ref=plan_ref,
        root_milestone_ref="m0",
        leaf_milestone_refs=["mLeaf"],
        pipeline_refs={"mLeaf": "pLeaf"},
        leaf_targets={"mLeaf": {
            "start_datastate": start,
            "target_datastate": target,
        }},
    )


def _claim_plan() -> PlanResult:
    return PlanResult(
        plan_ref="plan:drdemo-claim",
        root_milestone_ref="m0",
        leaf_milestone_refs=["mMap", "mFold"],
        pipeline_refs={"mMap": "pMap", "mFold": "pFold"},
        milestone_specs={
            "mMap": {
                "kind": "map",
                "collection_ds": DS_CLAIM_EXPOSURES,
                "member_ds": DS_EXPOSURE,
                "sub_target": DS_VERDICT,
                "out_ds": DS_VERDICTS,
            },
            "mFold": {
                "kind": "fold",
                "reducer_iri": CAP_CONCLUDE,
                "in_ds": DS_VERDICTS,
            },
        },
    )


def _dump_graphs(graphs) -> None:
    print(f"graphs collected: {len(graphs)}")
    for i, graph in enumerate(graphs):
        print(f"graph[{i}] role={graph.role!r}")
        for node in graph.nodes.values():
            print(f"  node type={node.type_name!r}")
            print(f"       properties={node.properties!r}")
            print(f"       value={node.value!r}")
        for edge in graph.edges.values():
            print(
                f"  edge {edge.source.type_name!r}"
                f" -[{edge.type_name}]-> {edge.target.type_name!r}"
            )


def _dump_mm_delta(mm, collected) -> None:
    """Print capacity_mm's graph count and any graph the collected list lacks.

    On the happy shapes the two are equal (pinned by
    ``test_dr_dump_printer_guard.py``). A rejected member attempt's graph
    stays in ``capacity_mm`` but is deliberately absent from the
    collected/persisted list — that delta is evidence, so it is printed.
    """
    mm_graphs = list(mm.capacity_mm.graphs.values())
    print(f"graphs in capacity_mm: {len(mm_graphs)} (collected: {len(collected)})")
    collected_ids = {id(g) for g in collected}
    extras = [g for g in mm_graphs if id(g) not in collected_ids]
    if extras:
        print(
            "capacity_mm-only graphs (rejected attempts: present in the MM, "
            "absent from the collected/persisted list):"
        )
        _dump_graphs(extras)


def dump_leaf(_collect_mms=None) -> None:
    print("== shape: leaf (exposure -> verdict, one pipeline run) ==")
    mm, dispatcher, writer, request_run = _harness()
    _note_mm(_collect_mms, mm)
    graphs: list = []
    execution.run(
        dispatcher, writer,
        _leaf_plan("plan:drdemo-leaf", DS_VERDICT),
        request_run,
        mm=mm,
        solve_seed={DS_EXPOSURE: EXPOSURES[0]},
        capacity_graphs=graphs,
        case_label="claim CLM-2041, exposure 1 of 1",
    )
    _dump_graphs(graphs)
    _dump_mm_delta(mm, graphs)


def dump_claim(_collect_mms=None) -> None:
    print("== shape: claim (map over 3 exposures + fold to the conclusion) ==")
    mm, dispatcher, writer, request_run = _harness()
    _note_mm(_collect_mms, mm)
    graphs: list = []
    execution.run(
        dispatcher, writer, _claim_plan(), request_run,
        mm=mm,
        solve_seed={DS_CLAIM_EXPOSURES: list(EXPOSURES)},
        capacity_graphs=graphs,
        case_label="claim CLM-2041",
    )
    _dump_graphs(graphs)
    _dump_mm_delta(mm, graphs)


def dump_noroute(_collect_mms=None) -> None:
    print("== shape: noroute (unroutable target; the run raises, a manifest-only graph remains) ==")
    mm, dispatcher, writer, request_run = _harness()
    _note_mm(_collect_mms, mm)
    graphs: list = []
    try:
        execution.run(
            dispatcher, writer,
            _leaf_plan("plan:drdemo-noroute", DS_UNREACHED),
            request_run,
            mm=mm,
            solve_seed={DS_EXPOSURE: EXPOSURES[0]},
            capacity_graphs=graphs,
            case_label="claim CLM-2041, unroutable ask",
        )
    except LeafPipelineNotFound as exc:
        print(f"raised (by design): {type(exc).__name__}")
    _dump_graphs(graphs)
    _dump_mm_delta(mm, graphs)


def dump_replan(_collect_mms=None) -> None:
    print("== shape: replan (the claim run at run_attempt 0, then re-run at run_attempt 1, same MM) ==")
    mm, dispatcher, writer, request_run = _harness()
    _note_mm(_collect_mms, mm)
    graphs: list = []
    for attempt in (0, 1):
        print(f"-- run_attempt {attempt} --")
        before = len(graphs)
        execution.run(
            dispatcher, writer, _claim_plan(), request_run,
            mm=mm,
            solve_seed={DS_CLAIM_EXPOSURES: list(EXPOSURES)},
            capacity_graphs=graphs,
            run_attempt=attempt,
            case_label="claim CLM-2041",
        )
        print(f"graphs added this attempt: {len(graphs) - before}")
        for graph in graphs[before:]:
            print(f"  role={graph.role!r}")
    _dump_graphs(graphs)
    _dump_mm_delta(mm, graphs)


def dump_retry(_collect_mms=None) -> None:
    print("== shape: retry (member 2 fails once -> retried under :r1; then a TARGETED re-exec of that member) ==")
    failures = {"A. Silva/contents": 1}
    mm, dispatcher, writer, request_run = _harness(
        capacities=[
            _decide_declaration(_make_flaky_decide(failures)),
            _conclude_declaration(),
        ],
    )
    _note_mm(_collect_mms, mm)
    graphs: list = []
    blackboard = {DS_CLAIM_EXPOSURES: list(EXPOSURES)}
    print("-- stage A: full run, run_attempt 0 (member 2's first attempt raises) --")
    execution.run(
        dispatcher, writer, _claim_plan(), request_run,
        mm=mm,
        solve_seed={DS_CLAIM_EXPOSURES: list(EXPOSURES)},
        blackboard=blackboard,
        capacity_graphs=graphs,
        case_label="claim CLM-2041",
    )
    _dump_graphs(graphs)
    _dump_mm_delta(mm, graphs)
    print("-- stage B: targeted re-exec of member index 1 at run_attempt 1 (retained blackboard; siblings untouched) --")
    before = len(graphs)
    execution.run(
        dispatcher, writer, _claim_plan(), request_run,
        mm=mm,
        solve_seed={DS_CLAIM_EXPOSURES: list(EXPOSURES)},
        blackboard=blackboard,
        targeted=(0, 1),
        run_attempt=1,
        capacity_graphs=graphs,
        case_label="claim CLM-2041",
    )
    print(f"graphs added by the targeted re-exec: {len(graphs) - before}")
    _dump_graphs(graphs[before:])
    _dump_mm_delta(mm, graphs)


def dump_memberpartial(_collect_mms=None) -> None:
    print("== shape: memberpartial (member 2 fails at MEMBER_RETRY_CAP: it stops IN PLACE, siblings run, the fold stops partial_domain) ==")
    failures = {"A. Silva/contents": 99}
    mm, dispatcher, writer, request_run = _harness(
        capacities=[
            _decide_declaration(_make_flaky_decide(failures)),
            _conclude_declaration(),
        ],
    )
    _note_mm(_collect_mms, mm)
    graphs: list = []
    execution.run(
        dispatcher, writer, _claim_plan(), request_run,
        mm=mm,
        solve_seed={DS_CLAIM_EXPOSURES: list(EXPOSURES)},
        capacity_graphs=graphs,
        case_label="claim CLM-2041",
    )
    _dump_graphs(graphs)
    _dump_mm_delta(mm, graphs)


def dump_needsinput(_collect_mms=None) -> None:
    print("== shape: needsinput (the step returns the NeedsInput verdict; the walk halts and records it) ==")
    mm, dispatcher, writer, request_run = _harness(
        capacities=[_decide_declaration(_ask), _conclude_declaration()],
    )
    _note_mm(_collect_mms, mm)
    graphs: list = []
    execution.run(
        dispatcher, writer,
        _leaf_plan("plan:drdemo-needsinput", DS_VERDICT),
        request_run,
        mm=mm,
        solve_seed={DS_EXPOSURE: EXPOSURES[0]},
        capacity_graphs=graphs,
        case_label="claim CLM-2041, exposure 1 of 1",
    )
    _dump_graphs(graphs)
    _dump_mm_delta(mm, graphs)


def dump_refusal(_collect_mms=None) -> None:
    print("== shape: refusal (no edition in force on the asked date; the run SUCCEEDS, the origin record carries the refusal) ==")
    mm, dispatcher, writer, request_run = _harness(
        capacities=[_lookup_declaration()],
        extra_datastates=_policy_datastates(),
        kl=_build_kl(EDITION_2023),
    )
    _note_mm(_collect_mms, mm)
    graphs: list = []
    execution.run(
        dispatcher, writer,
        _leaf_plan("plan:drdemo-refusal", DS_DWELLING_LIMIT, start=DS_POLICY_AS_OF),
        request_run,
        mm=mm,
        solve_seed={DS_POLICY_AS_OF: "2026-07-01"},
        capacity_graphs=graphs,
        case_label="claim CLM-2041, dwelling limit as of 2026-07-01",
    )
    _dump_graphs(graphs)
    _dump_mm_delta(mm, graphs)


def dump_outage(_collect_mms=None) -> None:
    print("== shape: outage (the store cannot be consulted; the step FAILS and RunStopped records it) ==")
    for sublabel, kl in (
        ("no store at all (kl=None)", None),
        (
            "the store contradicts itself (two editions in force -> AmbiguousEditionsError)",
            _build_kl(EDITION_2024, EDITION_2025_OVERLAPPING),
        ),
    ):
        print(f"-- outage: {sublabel} --")
        mm, dispatcher, writer, request_run = _harness(
            capacities=[_lookup_declaration()],
            extra_datastates=_policy_datastates(),
            kl=kl,
        )
        _note_mm(_collect_mms, mm)
        graphs: list = []
        execution.run(
            dispatcher, writer,
            _leaf_plan("plan:drdemo-outage", DS_DWELLING_LIMIT, start=DS_POLICY_AS_OF),
            request_run,
            mm=mm,
            solve_seed={DS_POLICY_AS_OF: "2026-07-01"},
            capacity_graphs=graphs,
            case_label="claim CLM-2041, dwelling limit as of 2026-07-01",
        )
        _dump_graphs(graphs)
        _dump_mm_delta(mm, graphs)


def dump_boundary(_collect_mms=None) -> None:
    print("== shape: boundary (the input-boundary axis: zero exposures REFUSED, one exposure decided) ==")
    for sublabel, exposures in (
        ("n=0 (the fold stops pre-dispatch: the reducer is never asked)", []),
        ("n=1", EXPOSURES[:1]),
    ):
        print(f"-- boundary: {sublabel} --")
        mm, dispatcher, writer, request_run = _harness()
        _note_mm(_collect_mms, mm)
        graphs: list = []
        execution.run(
            dispatcher, writer, _claim_plan(), request_run,
            mm=mm,
            solve_seed={DS_CLAIM_EXPOSURES: list(exposures)},
            capacity_graphs=graphs,
            case_label="claim CLM-2041",
        )
        _dump_graphs(graphs)
        _dump_mm_delta(mm, graphs)


def dump_codec(_collect_mms=None) -> None:
    print("== shape: codec (encoder-only; no round-trip) ==")
    print(
        "runs every other shape quietly, then applies the persistence encoder "
        "(make_node_value_encoder({}), the default path) to EVERY node value "
        "of EVERY graph in each shape's capacity_mm; a rejection prints the "
        "raw error. The live FalkorDB round-trip is the persistence-smoke "
        "item, not the sweep's."
    )
    import contextlib
    import io

    encode = make_node_value_encoder({})
    total_graphs = 0
    total_nodes = 0
    total_rejected = 0
    for name, fn in SHAPES.items():
        if name == "codec":
            continue
        mms: list = []
        with contextlib.redirect_stdout(io.StringIO()):
            fn(_collect_mms=mms)
        for mm in mms:
            for graph in mm.capacity_mm.graphs.values():
                total_graphs += 1
                for node in graph.nodes.values():
                    total_nodes += 1
                    try:
                        encode(node)
                    except Exception as exc:  # noqa: BLE001 — the raw error IS the output
                        total_rejected += 1
                        print(f"shape={name!r} graph={graph.role!r}")
                        print(f"  node type={node.type_name!r} value={node.value!r}")
                        print(f"  REJECTED: {type(exc).__name__}: {exc}")
    print(
        f"graphs walked: {total_graphs}; nodes encoded: {total_nodes}; "
        f"rejected: {total_rejected}"
    )


def _note_mm(mms, mm) -> None:
    if mms is not None:
        mms.append(mm)


SHAPES = {
    "leaf": dump_leaf,
    "claim": dump_claim,
    "noroute": dump_noroute,
    "replan": dump_replan,
    "retry": dump_retry,
    "memberpartial": dump_memberpartial,
    "needsinput": dump_needsinput,
    "refusal": dump_refusal,
    "outage": dump_outage,
    "boundary": dump_boundary,
    "codec": dump_codec,
}


def main(argv: list) -> int:
    which = argv[1] if len(argv) > 1 else "all"
    if which == "all":
        for fn in SHAPES.values():
            fn()
            print()
        return 0
    if which not in SHAPES:
        print(f"unknown shape {which!r}; choose one of {sorted(SHAPES)} or 'all'")
        return 2
    SHAPES[which]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
