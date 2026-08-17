"""Probe: the ROOM EDITS THE EMAIL — do value and its source co-move?

Runs against origin/main ead3bd1 (mindsos_capacity.llm + comprehension_v0 live
there, not in the demo pin df57033):
    PYTHONPATH=. python scripts/critic/probe_email_edit.py
Reader-record level — the Form B page/renderer does not exist yet, so ship C's
stage-2 must re-run this as a PAGE diff (probe_gate_diff pattern). Fixture
emails and the scripted honest model are COMPOSED by the critic; all mechanism
behavior is the tree's. Repr-only; verdicts live in coordination S118."""
import difflib
from types import SimpleNamespace
from mindsos_capacity.builtins.comprehension_v0 import build_reader
from mindsos_capacity.datastate import ShapeDescriptor

EMAIL_V1 = ("My husband was taken to County General directly from the scene. "
            "His doctor says he will be off work for at least six weeks.")
EMAIL_V2 = ("My husband was taken to County General directly from the scene. "
            "His doctor says he will be off work for at least two weeks.")
EMAIL_V3 = ("My husband was taken to County General directly from the scene. "
            "His doctor did not say anything about time off work.")

def reader():
    return build_reader(
        name="drdemo.read_off_work_weeks",
        source_datastate_iri="datastate:drdemo.claim_email",
        value_datastate_iri="datastate:drdemo.off_work_weeks",
        prompt_iri="prompt:drdemo.extract_components", prompt_version=1,
        field_name="off_work_weeks",
        question="how many weeks off work the document states",
        description="reads the stated off-work duration",
        origin_party_phrase="the claimant",
        source_identity_phrase="the claim email",
        expected_basis="stated",
        value_shape=ShapeDescriptor.scalar("int"))

def honest_model(source):
    # An honest extractor: quotes the off-work sentence if present, else no field.
    if "six weeks" in source:
        return {"fields": [{"name": "off_work_weeks", "value": "6",
                            "quote": "off work for at least six weeks", "basis": "stated"}]}
    if "two weeks" in source:
        return {"fields": [{"name": "off_work_weeks", "value": "2",
                            "quote": "off work for at least two weeks", "basis": "stated"}]}
    return {"fields": []}

def record(source):
    cap = reader()
    llm = SimpleNamespace(read=lambda **kw: honest_model(source))
    out = cap.implementation(context=SimpleNamespace(llm=llm),
                             **{"datastate:drdemo.claim_email": source})
    val = out["datastate:drdemo.off_work_weeks"]
    rec = out["datastate:drdemo.off_work_weeks_origin"]
    lines = [f"value: {val!r}"]
    for k in sorted(rec):
        if rec[k] is not None and k not in ("recorded","request_key","temperature",
                                            "model_id","model_version","prompt_iri","prompt_version"):
            lines.append(f"{k}: {rec[k]!r}")
    return lines

print("== raw output below this line ==")
for label, b in (("edit_6w_to_2w", EMAIL_V2), ("edit_remove_component", EMAIL_V3)):
    print(repr("[" + label + "]"))
    for line in difflib.unified_diff(record(EMAIL_V1), record(b), lineterm=""):
        print(repr(line))
