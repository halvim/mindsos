"""dr_dump — dump every grounding graph a Decision Records run leaves, raw.

This is the RULES §12 command for the Decision Records lane: it runs the real
core machinery (`execution.run` → `execute_pipeline`, an in-memory
`MentalModel`, no FalkorDB) over a small demo fixture and prints what lands in
`capacity_mm`, unedited. Until this existed, every check was the build lane
reading its own output.

RULES §11 seam, stated up front: the section headers, the `graph[n]` /
`node` / `edge` prefixes and the field ordering are THIS SCRIPT'S framing.
Every value after a colon is `repr()` of what the system emitted — node types,
IRIs, properties, values, edge types — with nothing translated, prettified or
omitted. Ugly is information.

Shapes:

    leaf     one pipeline run: exposure → verdict
    claim    a map over three exposures + the fold that concludes the claim
             (one graph per exposure, PLUS the fold's own graph — the shape
             PR #157 and PR #158 existed to make renderable)
    noroute  an unroutable request: the run raises, and the graph left behind
             is manifest-only (run 4's shape)
    all      the three above, in order

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
from mindsos_intelligence import execution
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.execution import LeafPipelineNotFound
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import PlanResult

DS_CLAIM_EXPOSURES = datastate_iri("drdemo.claim_exposures")
DS_EXPOSURE = datastate_iri("drdemo.exposure")
DS_VERDICT = datastate_iri("drdemo.exposure_verdict")
DS_VERDICTS = datastate_iri("drdemo.exposure_verdicts")
DS_CONCLUSION = datastate_iri("drdemo.claim_conclusion")
DS_UNREACHED = datastate_iri("drdemo.nothing_produces_this")

CAP_DECIDE = capacity_iri(CATEGORY_DERIVATION, "drdemo_decide_exposure")
CAP_CONCLUDE = capacity_iri(CATEGORY_DERIVATION, "drdemo_conclude_claim")

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


def _conclude(**kwargs):
    verdicts = kwargs.get(DS_VERDICTS)
    return {DS_CONCLUSION: {"claim_decision": "payable", "from": verdicts}}


def _harness():
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
    layer.register_capacity(
        Capacity(
            name="drdemo_decide_exposure",
            category=CATEGORY_DERIVATION,
            inputs=(DS_EXPOSURE,),
            outputs=(DS_VERDICT,),
            implementation=_decide,
            description="one exposure -> its verdict",
            printable_phrase="deciding one exposure on its coverage",
        ),
        session=session,
    )
    layer.register_capacity(
        Capacity(
            name="drdemo_conclude_claim",
            category=CATEGORY_DERIVATION,
            inputs=(DS_VERDICTS,),
            outputs=(DS_CONCLUSION,),
            implementation=_conclude,
            description="the ordered verdicts -> the claim conclusion",
            printable_phrase="concluding the claim from its exposure verdicts",
        ),
        session=session,
    )
    mm = MentalModel(session_id="drdemo-session", user_id="drdemo-user")
    dispatcher = L4Dispatcher(layer, session=session)
    writer = ChainArtifactWriter(mm, "drdemo-task")
    return mm, dispatcher, writer, writer.emit_request_run()


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


def dump_leaf() -> None:
    print("== shape: leaf (exposure -> verdict, one pipeline run) ==")
    mm, dispatcher, writer, request_run = _harness()
    graphs: list = []
    execution.run(
        dispatcher, writer,
        PlanResult(
            plan_ref="plan:drdemo-leaf",
            root_milestone_ref="m0",
            leaf_milestone_refs=["mDecide"],
            pipeline_refs={"mDecide": "pDecide"},
            leaf_targets={"mDecide": {
                "start_datastate": DS_EXPOSURE,
                "target_datastate": DS_VERDICT,
            }},
        ),
        request_run,
        mm=mm,
        solve_seed={DS_EXPOSURE: EXPOSURES[0]},
        capacity_graphs=graphs,
        case_label="claim CLM-2041, exposure 1 of 1",
    )
    _dump_graphs(graphs)


def dump_claim() -> None:
    print("== shape: claim (map over 3 exposures + fold to the conclusion) ==")
    mm, dispatcher, writer, request_run = _harness()
    graphs: list = []
    execution.run(
        dispatcher, writer,
        PlanResult(
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
        ),
        request_run,
        mm=mm,
        solve_seed={DS_CLAIM_EXPOSURES: list(EXPOSURES)},
        capacity_graphs=graphs,
        case_label="claim CLM-2041",
    )
    _dump_graphs(graphs)


def dump_noroute() -> None:
    print("== shape: noroute (unroutable target; the run raises, a manifest-only graph remains) ==")
    mm, dispatcher, writer, request_run = _harness()
    graphs: list = []
    try:
        execution.run(
            dispatcher, writer,
            PlanResult(
                plan_ref="plan:drdemo-noroute",
                root_milestone_ref="m0",
                leaf_milestone_refs=["mImpossible"],
                pipeline_refs={"mImpossible": "pImpossible"},
                leaf_targets={"mImpossible": {
                    "start_datastate": DS_EXPOSURE,
                    "target_datastate": DS_UNREACHED,
                }},
            ),
            request_run,
            mm=mm,
            solve_seed={DS_EXPOSURE: EXPOSURES[0]},
            capacity_graphs=graphs,
            case_label="claim CLM-2041, unroutable ask",
        )
    except LeafPipelineNotFound as exc:
        print(f"raised (by design): {type(exc).__name__}")
    _dump_graphs(graphs)


SHAPES = {"leaf": dump_leaf, "claim": dump_claim, "noroute": dump_noroute}


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
