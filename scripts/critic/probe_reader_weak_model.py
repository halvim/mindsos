"""Probe: comprehension_v0 under a WEAK model — which replies are admitted?

Runs against origin/main ead3bd1 (mindsos_capacity.llm + comprehension_v0 live
there, not in the demo pin df57033):
    PYTHONPATH=. python scripts/critic/probe_reader_weak_model.py
Fixture email and scripted model replies are COMPOSED by the critic; all
mechanism behavior is the tree's. Repr-only output below a seam line;
verdicts live in coordination S118, never here."""
from types import SimpleNamespace
from mindsos_capacity.builtins.comprehension_v0 import build_reader
from mindsos_capacity.datastate import ShapeDescriptor

SOURCE = (
    "Dear team,\n\nMy husband was taken to County General directly from the "
    "scene. The paramedic assessment happened at the roadside. His doctor "
    "says he will be off work for at least six weeks.\n\nMrs. F. Okafor"
)

def reader():
    return build_reader(
        name="drdemo.read_off_work_weeks",
        source_datastate_iri="datastate:drdemo.claim_email",
        value_datastate_iri="datastate:drdemo.off_work_weeks",
        prompt_iri="prompt:drdemo.extract_components",
        prompt_version=1,
        field_name="off_work_weeks",
        question="how many weeks off work the document states",
        description="reads the stated off-work duration",
        origin_party_phrase="the claimant",
        source_identity_phrase="the claim email",
        expected_basis="stated",
        value_shape=ShapeDescriptor.scalar("int"),
    )

def run(label, field):
    cap = reader()
    resp = {"fields": [dict(field, name="off_work_weeks")],
            "model_id": "probe-weak-model", "model_version": "0",
            "temperature": 0.0, "request_key": "k", "recorded": False}
    llm = SimpleNamespace(read=lambda **kw: resp)
    out = cap.implementation(context=SimpleNamespace(llm=llm),
                             **{"datastate:drdemo.claim_email": SOURCE})
    val = out["datastate:drdemo.off_work_weeks"]
    rec = out["datastate:drdemo.off_work_weeks_origin"]
    keep = {k: rec.get(k) for k in ("admitted", "refusal_reason", "quote_verified",
                                    "quote", "claimed_quote", "basis", "expected_basis")}
    print(repr(("[" + label + "]", "value:", val, keep)))

print("== raw output below this line ==")
run("A_correct", {"value": "6", "quote": "off work for at least six weeks", "basis": "stated"})
run("B_invented_quote", {"value": "6", "quote": "off work for six months", "basis": "stated"})
run("C_wrong_value_true_quote", {"value": "2", "quote": "off work for at least six weeks", "basis": "stated"})
run("D_irrelevant_true_quote", {"value": "6", "quote": "Dear team,", "basis": "stated"})
run("E_basis_mismatch", {"value": "6", "quote": "off work for at least six weeks", "basis": "inferred"})
run("F_not_coercible", {"value": "about seven", "quote": "off work for at least six weeks", "basis": "stated"})
