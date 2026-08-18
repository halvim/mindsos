"""S140.3's one unverified assumption: can dr_render reach the SOURCE TEXT a
quote was verified against?

Needs a PIN-BUMPED tree — origin/main's mindsos_capacity (which has
comprehension_v0) with decision_records_demo/ from demo/decision-records copied
in, which is what step 3's pin bump produces:

    cp -r <demo-checkout>/decision_records_demo <main-checkout>/
    cd <main-checkout> && PYTHONPATH=. python scripts/critic/probe_source_reachable.py

Runs ONE reader on the LEAF road with the document as the start, then prints
what dr_render._Analysis sees. Composed by the critic: the two-claimant email,
the plan and the scripted model. The graph, the reader and _Analysis are the
tree's. Repr-only; verdicts in coordination S141."""
from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins.comprehension_v0 import (
    register_reader, source_text_datastate,
)
from mindsos_capacity.datastate import ShapeDescriptor
from mindsos_capacity.identifiers import datastate_iri
from mindsos_intelligence import execution
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import PlanResult

EMAIL = ("C. Mensah was taken to hospital. His doctor says he will be "
         "off work for at least six weeks.\n"
         "D. Laurent hurt his wrist. Her doctor says she will be "
         "off work for at least six weeks.\n")
QUOTE = "His doctor says he will be off work for at least six weeks"

DS_SRC = datastate_iri("drdemo.claim_email")
DS_VAL = datastate_iri("drdemo.off_work_period")


class _Session:
    session_id = "drdemo-session"
    user_id = "drdemo-user"
    actor_role = "user"
    capabilities: set = set()

    def has(self, capability):
        return False


class _FakeLLM:
    def read(self, **kwargs):
        return {"fields": [{"name": "off_work_period", "value": QUOTE,
                            "quote": QUOTE, "basis": "stated"}],
                "model_id": "probe", "model_version": "0"}


session = _Session()
layer = CapacityLayer()
layer.register_datastate(
    source_text_datastate("drdemo.claim_email", "the claim email"),
    session=session, allow_new_realm=True)
register_reader(
    layer, name="drdemo_read_off_work",
    source_datastate_iri=DS_SRC, value_datastate_iri=DS_VAL,
    value_description="The off-work period the message states",
    prompt_iri="prompt:x", prompt_version=1, field_name="off_work_period",
    question="the off-work period this message states",
    description="reads the stated off-work period",
    origin_party_phrase="the claimant",
    source_identity_phrase="the claim email",
    expected_basis="stated", value_shape=ShapeDescriptor.scalar("str"),
    session=session)

mm = MentalModel(session_id="drdemo-session", user_id="drdemo-user")
dispatcher = L4Dispatcher(layer, session=session, llm=_FakeLLM())
writer = ChainArtifactWriter(mm, "drdemo-task")
plan = PlanResult(
    plan_ref="plan:drdemo-prose", root_milestone_ref="m0",
    leaf_milestone_refs=["mLeaf"], pipeline_refs={"mLeaf": "pLeaf"},
    leaf_targets={"mLeaf": {"start_datastate": DS_SRC,
                            "target_datastate": DS_VAL,
                            "finder": "conjunction"}})
graphs = []
execution.run(dispatcher, writer, plan, writer.emit_request_run(), mm=mm,
              solve_seed={DS_SRC: EMAIL}, capacity_graphs=graphs,
              case_label="claim CLM-1")

print("== raw output below this line ==")
from decision_records_demo.dr_render import _Analysis  # noqa: E402

for graph in graphs:
    analysis = _Analysis(graph)
    print(repr(("graph:", graph.graph_id)))
    for node in analysis.parentless:
        print(repr(("  PARENTLESS", analysis.ds_type(node), repr(node.value)[:70])))
    for node in analysis.produced:
        value = node.value
        shown = sorted(value)[:6] if isinstance(value, dict) else repr(value)[:70]
        print(repr(("  produced", analysis.ds_type(node), shown)))
