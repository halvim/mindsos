"""CRITIC PROBE 1 — does a map+fold run leave the claim-level conclusion in ANY grounding graph?

Throwaway. Runs against a tarball extract of a ref; writes nothing to the repo.
Method: drive execution.run with a map+fold plan (same shape as
tests/phase_48/test_slice1b_map_fold.py), with mm= and capacity_graphs=, then
dump raw node inventories of every graph the run left.
"""
from __future__ import annotations
import sys

from mindsos_capacity import CapacityLayer
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_DERIVATION, capacity_iri, datastate_iri,
)
from mindsos_intelligence import execution
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import PlanResult

DS_COLL = datastate_iri("pf.exposures")
DS_MEMBER = datastate_iri("pf.exposure")
DS_SUB = datastate_iri("pf.exposure_verdict")
DS_OUT = datastate_iri("pf.exposure_verdicts")
DS_AGG = datastate_iri("pf.claim_conclusion")
CAP_SOLVE = capacity_iri(CATEGORY_DERIVATION, "pf_member_solve")
CAP_REDUCE = capacity_iri(CATEGORY_DERIVATION, "pf_reduce")


class FakeSession:
    session_id = "s"; user_id = "u"; actor_role = "user"; capabilities: set = set()
    def has(self, capability: str) -> bool: return False


def _member_body(**kw): return {DS_SUB: {"verdict": kw.get(DS_MEMBER)}}
def _reduce_body(**kw): return {DS_AGG: {"conclusion": kw.get(DS_OUT)}}


def main() -> None:
    sess = FakeSession(); layer = CapacityLayer()
    colls = {"pf.exposures": dict(collection=True, member_ds=DS_MEMBER),
             "pf.exposure_verdicts": dict(collection=True, member_ds=DS_SUB)}
    for name in ("pf.exposures", "pf.exposure", "pf.exposure_verdict",
                 "pf.exposure_verdicts", "pf.claim_conclusion"):
        layer.register_datastate(DataState(
            name=name, shape=ShapeDescriptor.opaque(name),
            description=f"description of {name}",
            provenance_category=CATEGORY_DERIVATION, **colls.get(name, {})),
            session=sess, allow_new_realm=True)
    kw = dict(session=sess)
    try:
        layer.register_capacity(Capacity(
            name="pf_member_solve", category=CATEGORY_DERIVATION,
            inputs=(DS_MEMBER,), outputs=(DS_SUB,), implementation=_member_body,
            description="member: exposure -> verdict",
            printable_phrase="deciding one exposure"), **kw)
        layer.register_capacity(Capacity(
            name="pf_reduce", category=CATEGORY_DERIVATION,
            inputs=(DS_OUT,), outputs=(DS_AGG,), implementation=_reduce_body,
            description="reducer: verdicts -> claim conclusion",
            printable_phrase="concluding the claim from its exposures"), **kw)
    except TypeError:
        # main tree: Capacity may not accept printable_phrase kwarg mismatch safety
        raise
    mm = MentalModel(session_id="s", user_id="u")
    disp = L4Dispatcher(layer, session=sess)
    writer = ChainArtifactWriter(mm, "t")
    request_run = writer.emit_request_run()
    plan = PlanResult(
        plan_ref="plan:pf", root_milestone_ref="m0",
        leaf_milestone_refs=["mMap", "mFold"],
        pipeline_refs={"mMap": "pMap", "mFold": "pFold"},
        milestone_specs={
            "mMap": {"kind": "map", "collection_ds": DS_COLL,
                     "member_ds": DS_MEMBER, "sub_target": DS_SUB, "out_ds": DS_OUT},
            "mFold": {"kind": "fold", "reducer_iri": CAP_REDUCE, "in_ds": DS_OUT},
        })
    graphs: list = []
    kwargs = dict(mm=mm, solve_seed={DS_COLL: ["e1", "e2", "e3"]},
                  capacity_graphs=graphs)
    try:
        execution.run(disp, writer, plan, request_run, case_label="claim CLM-1", **kwargs)
        label_support = True
    except TypeError:
        execution.run(disp, writer, plan, request_run, **kwargs)
        label_support = False

    print(f"case_label kwarg supported: {label_support}")
    print(f"graphs returned: {len(graphs)}")
    reducer_seen = agg_seen = manifests = 0
    for i, g in enumerate(graphs):
        types = {}
        for n in g.nodes.values():
            types[n.type_name] = types.get(n.type_name, 0) + 1
        print(f"graph[{i}] role={getattr(g,'role',None)!r} node_type_counts={types}")
        for n in g.nodes.values():
            if n.type_name == "RunManifest":
                manifests += 1
                print(f"  manifest value: {n.value!r}")
            if n.type_name == "CapacityInstance" and "pf_reduce" in str(n.node_id):
                reducer_seen += 1
            if "claim_conclusion" in str(n.node_id):
                agg_seen += 1
    print(f"TOTALS: manifests={manifests} reducer_CapacityInstance={reducer_seen} "
          f"claim_conclusion_DataStateInstance={agg_seen}")
    # also: every graph in the MM, not only the returned list
    all_graphs = []
    for attr in ("graphs", "_graphs"):
        gs = getattr(getattr(mm, "capacity_mm", mm), attr, None)
        if gs: all_graphs = list(gs.values() if isinstance(gs, dict) else gs); break
    print(f"mm-side graphs discovered: {len(all_graphs)}")
    for g in all_graphs:
        ids = [str(n.node_id) for n in g.nodes.values()]
        hit = [i for i in ids if "claim_conclusion" in i or "pf_reduce" in i]
        if hit: print("  MM-side reducer/conclusion nodes:", hit)
    print("VERDICT:", "conclusion IS grounded" if (reducer_seen or agg_seen) else
          "conclusion ABSENT from every grounding graph (claim-level answer unrenderable)")


if __name__ == "__main__":
    sys.exit(main())
