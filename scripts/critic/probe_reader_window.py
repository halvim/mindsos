"""S138.2: is there a window/base/span parameter on the reader path — and is
there a THIRD configuration that gives both properties?

Run from a checkout carrying mindsos_capacity (origin/main):
    PYTHONPATH=. python scripts/critic/probe_reader_window.py

First half introspects every signature on the reader path mechanically, so the
ABSENCE is established by running rather than by reading. Second half tries the
configuration S138.2 does not consider: the whole document as source, with the
QUOTE made unique by its own context.

Composed by the critic: the two-claimant email and the three quotes. Every
signature, offset and located span is the tree's. Repr-only; verdicts in
coordination S139."""
import inspect
import pathlib
import re
from types import SimpleNamespace

from mindsos_capacity.builtins import comprehension_v0 as C
from mindsos_capacity.datastate import ShapeDescriptor

print("== raw output below this line ==")
for fn in (C.build_reader, C.register_reader, C.reader_datastates,
           C.locate_quote, C.coerce_to_shape, C.source_text_datastate):
    print(repr((fn.__name__, sorted(inspect.signature(fn).parameters))))
print(repr(("_make_impl params:", sorted(inspect.signature(C._make_impl).parameters))))
print(repr(("window/base/span/offset mentions in mindsos_capacity:",
            sorted({(str(path), name)
                    for path in pathlib.Path("mindsos_capacity").rglob("*.py")
                    for name in re.findall(r"\b(window|base_offset|span|offsets?)\s*[:=,)]",
                                           path.read_text())})[:12])))

EMAIL = ("Two of our people were hurt in the loading-dock collision.\n"
         "C. Mensah was taken to hospital. His doctor says he will be "
         "off work for at least six weeks.\n"
         "D. Laurent hurt his wrist. Her doctor says she will be "
         "off work for at least six weeks.\n")


def reader():
    return C.build_reader(
        name="drdemo.read_off_work_period",
        source_datastate_iri="datastate:drdemo.claim_email",
        value_datastate_iri="datastate:drdemo.off_work_period",
        prompt_iri="p", prompt_version=1, field_name="off_work_period",
        question="the off-work period this exposure states",
        description="d", origin_party_phrase="the claimant",
        source_identity_phrase="the claim email", expected_basis="stated",
        value_shape=ShapeDescriptor.scalar("str"))


def run(label, quote):
    cap = reader()
    response = {"fields": [{"name": "off_work_period", "value": quote,
                            "quote": quote, "basis": "stated"}]}
    llm = SimpleNamespace(read=lambda **kw: response)
    out = cap.implementation(context=SimpleNamespace(llm=llm),
                             **{"datastate:drdemo.claim_email": EMAIL})
    record = out["datastate:drdemo.off_work_period_origin"]
    start, end = record["quote_offsets"]
    print(repr((label, "offsets:", [start, end],
                "occurrences_in_doc:", EMAIL.count(quote),
                "text_at_offsets:", EMAIL[start:end][:44])))


run("bare_phrase_Mensah", "off work for at least six weeks")
run("name_bearing_Mensah",
    "His doctor says he will be off work for at least six weeks")
run("name_bearing_Laurent",
    "Her doctor says she will be off work for at least six weeks")
