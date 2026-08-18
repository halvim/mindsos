"""S136.2(B): the spans-not-structures plan, attacked before it is built.

Run from a checkout carrying mindsos_capacity (origin/main):
    PYTHONPATH=. python scripts/critic/probe_span_split.py

The plan is: the model marks one text RANGE per exposure, each range becomes
that exposure's source document, every reader carries its own located quote.
This runs three shapes through the real comprehension_v0 reader: a WHOLE-
DOCUMENT span used for two different members, correctly split spans, and a
span that is not a contiguous range of the email at all.

Composed by the critic: the email (two claimants stating the SAME off-work
phrase), the spans, the scripted replies. locate_quote and the reader body are
the tree's. Repr-only; verdicts in coordination S137."""
from types import SimpleNamespace

from mindsos_capacity.builtins.comprehension_v0 import build_reader, locate_quote
from mindsos_capacity.datastate import ShapeDescriptor

EMAIL = (
    "Two of our people were hurt in the loading-dock collision.\n"
    "C. Mensah was taken to hospital. His doctor says he will be "
    "off work for at least six weeks.\n"
    "D. Laurent hurt his wrist. Her doctor says she will be "
    "off work for at least six weeks.\n"
)
PHRASE = "off work for at least six weeks"


def reader():
    return build_reader(
        name="drdemo.read_off_work_period",
        source_datastate_iri="datastate:drdemo.exposure_span",
        value_datastate_iri="datastate:drdemo.off_work_period",
        prompt_iri="prompt:x", prompt_version=1,
        field_name="off_work_period",
        question="the off-work period this exposure states",
        description="reads one exposure's off-work period",
        origin_party_phrase="the claimant",
        source_identity_phrase="the claim email",
        expected_basis="stated",
        value_shape=ShapeDescriptor.scalar("str"))


def run(label, source_text, quote, value):
    cap = reader()
    response = {"fields": [{"name": "off_work_period", "value": value,
                            "quote": quote, "basis": "stated"}]}
    llm = SimpleNamespace(read=lambda **kw: response)
    out = cap.implementation(context=SimpleNamespace(llm=llm),
                             **{"datastate:drdemo.exposure_span": source_text})
    record = out["datastate:drdemo.off_work_period_origin"]
    print(repr((label, "admitted:", record.get("admitted"),
                "quote_verified:", record.get("quote_verified"),
                "offsets:", record.get("quote_offsets"),
                "value:", out["datastate:drdemo.off_work_period"])))


print("== raw output below this line ==")
print(repr(("all occurrences of the shared phrase:",
            [i for i in range(len(EMAIL)) if EMAIL.startswith(PHRASE, i)])))
print(repr(("locate_quote returns:", locate_quote(EMAIL, PHRASE))))

run("member_Mensah_whole_doc_span", EMAIL, PHRASE, PHRASE)
run("member_Laurent_whole_doc_span", EMAIL, PHRASE, PHRASE)

run("member_Mensah_own_span", EMAIL.split("\n")[1], PHRASE, PHRASE)
run("member_Laurent_own_span", EMAIL.split("\n")[2], PHRASE, PHRASE)

run("member_fabricated_span",
    "C. Mensah was off work for at least six weeks and is cleared to return.",
    PHRASE, PHRASE)
