"""Probe 119.2: the only shapes available for a collection-from-prose reader,
and what quote-verification does to them.

Runs against origin/main ead3bd1:
    PYTHONPATH=. python scripts/critic/probe_collection_reader.py
Fixture email and the scripted reply (two real people, one invented claimant,
one invented peril) are COMPOSED by the critic. Repr-only; verdicts in
coordination S120."""
from types import SimpleNamespace
from mindsos_capacity.builtins.comprehension_v0 import build_reader
from mindsos_capacity.datastate import ShapeDescriptor

EMAIL = ("Two of our people were hurt when the delivery van hit the loading "
         "dock. J. Park was taken to hospital directly from the scene. "
         "R. Adeyemi hurt his wrist; his doctor says he will be off work for "
         "at least six weeks. The van itself needs a new door.")

def reader(shape):
    return build_reader(
        name="drdemo.read_exposures",
        source_datastate_iri="datastate:drdemo.claim_email",
        value_datastate_iri="datastate:drdemo.exposure_set",
        prompt_iri="prompt:drdemo.extract_exposures", prompt_version=1,
        field_name="exposures",
        question="the exposures this email describes",
        description="reads the exposure collection",
        origin_party_phrase="the claimant",
        source_identity_phrase="the claim email",
        expected_basis="stated",
        value_shape=shape)

FABRICATED = [
    {"claimant": "J. Park", "kind": "injury"},
    {"claimant": "R. Adeyemi", "kind": "injury"},
    {"claimant": "K. Invented", "kind": "injury"},   # nobody in the email
    {"claimant": "The van", "kind": "flood damage"}, # invented peril
]

def run(label, shape):
    cap = reader(shape)
    resp = {"fields": [{"name": "exposures", "value": FABRICATED,
                        "quote": "Two of our people", "basis": "stated"}]}
    llm = SimpleNamespace(read=lambda **kw: resp)
    out = cap.implementation(context=SimpleNamespace(llm=llm),
                             **{"datastate:drdemo.claim_email": EMAIL})
    rec = out["datastate:drdemo.exposure_set_origin"]
    print(repr(("[" + label + "]", "admitted:", rec.get("admitted"),
                "quote_verified:", rec.get("quote_verified"),
                "refusal:", rec.get("refusal_reason"),
                "value:", out["datastate:drdemo.exposure_set"])))

print("== raw output below this line ==")
run("opaque_fabricated_members_true_quote", ShapeDescriptor.opaque("exposure_set"))
run("list_shape_fabricated_members_true_quote", ShapeDescriptor.list_of("str"))
run("record_shape_fabricated_members_true_quote", ShapeDescriptor.record({"claimant": "str"}))
