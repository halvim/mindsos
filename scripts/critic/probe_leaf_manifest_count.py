"""CRITIC PROBE 2 — after the mint moved into execute_pipeline, does a plain
leaf run carry exactly ONE manifest (no double-mint), and does the no-route
path leave a manifest-only graph?"""
from __future__ import annotations
from mindsos_capacity import CapacityLayer
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import CATEGORY_DERIVATION, capacity_iri, datastate_iri
from mindsos_intelligence import execution
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import PlanResult

DS_A = datastate_iri("plf.given"); DS_B = datastate_iri("plf.answer")
DS_NOPE = datastate_iri("plf.unreachable")
CAP = capacity_iri(CATEGORY_DERIVATION, "plf_solve")

class S:
    session_id="s"; user_id="u"; actor_role="user"; capabilities:set=set()
    def has(self,c): return False

def harness():
    sess=S(); layer=CapacityLayer()
    for n in ("plf.given","plf.answer","plf.unreachable"):
        layer.register_datastate(DataState(name=n, shape=ShapeDescriptor.opaque(n),
            description=f"description of {n}", provenance_category=CATEGORY_DERIVATION),
            session=sess, allow_new_realm=True)
    layer.register_capacity(Capacity(name="plf_solve", category=CATEGORY_DERIVATION,
        inputs=(DS_A,), outputs=(DS_B,), implementation=lambda **kw: {DS_B: 42},
        description="solve", printable_phrase="working out the answer"), session=sess)
    mm=MentalModel(session_id="s", user_id="u"); disp=L4Dispatcher(layer, session=sess)
    w=ChainArtifactWriter(mm,"t"); rr=w.emit_request_run()
    return mm,disp,w,rr

def plan(target):
    return PlanResult(plan_ref="p", root_milestone_ref="m0",
        leaf_milestone_refs=["mL"], pipeline_refs={"mL":"pL"},
        leaf_targets={"mL": {"start_datastate": DS_A, "target_datastate": target}})

def count(graphs):
    m=[[n for n in g.nodes.values() if n.type_name=="RunManifest"] for g in graphs]
    return [len(x) for x in m]

mm,disp,w,rr = harness(); graphs=[]
execution.run(disp,w,plan(DS_B),rr,mm=mm,solve_seed={DS_A: 7},capacity_graphs=graphs)
print("clean leaf run: graphs:", len(graphs), "manifests per graph:", count(graphs))

mm,disp,w,rr = harness(); graphs=[]
try:
    execution.run(disp,w,plan(DS_NOPE),rr,mm=mm,solve_seed={DS_A: 7},capacity_graphs=graphs)
    print("no-route: did NOT raise")
except execution.LeafPipelineNotFound as e:
    print("no-route: raised LeafPipelineNotFound (expected)")
print("no-route: graphs:", len(graphs), "manifests per graph:", count(graphs))
for g in graphs:
    print("  nodes:", {n.type_name: 1 for n in g.nodes.values()},
          "| manifest starts:", [n.value.get("declared_starts") for n in g.nodes.values() if n.type_name=="RunManifest"])
