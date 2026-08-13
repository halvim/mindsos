"""CRITIC PROBE 3 — RAW dump of every graph a map+fold run leaves.

Self-contained: registers its own fixtures, drives execution.run, then prints
repr() of every node and edge. No counts, no verdicts, no summaries — the one
print before the dump labels the seam (RULES §11 + owner rule 2026-08-13:
conclusions never live inside probe output). Run from a repo checkout root:
    PYTHONPATH=. python scripts/critic/probe_fold_raw_dump.py
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



def run_map_fold(members, case_label=None):
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
    layer.register_capacity(Capacity(
        name="pf_member_solve", category=CATEGORY_DERIVATION,
        inputs=(DS_MEMBER,), outputs=(DS_SUB,), implementation=_member_body,
        description="member: exposure -> verdict",
        printable_phrase="deciding one exposure"), session=sess)
    layer.register_capacity(Capacity(
        name="pf_reduce", category=CATEGORY_DERIVATION,
        inputs=(DS_OUT,), outputs=(DS_AGG,), implementation=_reduce_body,
        description="reducer: verdicts -> claim conclusion",
        printable_phrase="concluding the claim from its exposures"), session=sess)
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
    graphs = []
    execution.run(disp, writer, plan, request_run, mm=mm,
                  solve_seed={DS_COLL: list(members)},
                  capacity_graphs=graphs, case_label=case_label)
    return graphs


if __name__ == "__main__":
    graphs = run_map_fold(["e1", "e2", "e3"], case_label="claim CLM-1")
    print("SEAM: lines above are mine; every line below is repr() of system state")
    for i, g in enumerate(graphs):
        print(f"--- graph[{i}] role={g.role!r}")
        for n in g.nodes.values():
            print(f"NODE {n.type_name} {n.node_id!r} value={n.value!r}")
        for e in g.edges.values():
            print(f"EDGE {e.type_name} {e.source.node_id!r} -> {e.target.node_id!r}")
