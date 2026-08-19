"""S149.5(3): is slice 2's span validation set sufficient to carry break (1)?

CORE-SIDE probe (imports mindsos_capacity only) — run from a core checkout, or
from the demo home once core is installed:
    PYTHONPATH=. python scripts/critic/probe_span_validation.py

Slice 2's stated checks are in-bounds, disjoint, non-empty, and each span
containing the values read from it. This runs a CORRECT split and a MISALIGNED
one whose boundary falls a single sentence early — both are pairs of integers
into the real text, so both are legal spans.

Composed by the critic: the two-claimant email, the two span sets, and the
scripted model (which quotes the first off-work phrase visible inside its own
span). locate_quote, the reader and the origin record are the tree's.
Repr-only; verdicts in coordination S150."""
from types import SimpleNamespace

from mindsos_capacity.builtins.comprehension_v0 import build_reader
from mindsos_capacity.datastate import ShapeDescriptor

EMAIL = ("C. Mensah was taken to hospital. His doctor says he will be "
         "off work for at least two weeks.\n"
         "D. Laurent hurt her wrist. Her doctor says she will be "
         "off work for at least six weeks.\n")
CUT_OK = EMAIL.index("D. Laurent")
CUT_BAD = EMAIL.index("His doctor")
CORRECT = [(0, CUT_OK), (CUT_OK, len(EMAIL))]
MISALIGNED = [(0, CUT_BAD), (CUT_BAD, len(EMAIL))]
FILED = ["C. Mensah", "D. Laurent"]


def validate(spans, doc, reads):
    """The four checks S149.5(3) names."""
    return {
        "in_bounds": all(0 <= s < e <= len(doc) for s, e in spans),
        "non_empty": all(doc[s:e].strip() for s, e in spans),
        "disjoint": all(spans[i][1] <= spans[i + 1][0]
                        for i in range(len(spans) - 1)),
        "contains_its_values": all(r is None or r in doc[s:e]
                                   for r, (s, e) in zip(reads, spans)),
    }


def read_span(text, quote):
    cap = build_reader(
        name="r", source_datastate_iri="datastate:drdemo.span",
        value_datastate_iri="datastate:drdemo.period", prompt_iri="p",
        prompt_version=1, field_name="off_work_period",
        question="the off-work period this exposure states", description="d",
        origin_party_phrase="the claimant",
        source_identity_phrase="the claim email", expected_basis="stated",
        value_shape=ShapeDescriptor.scalar("str"))
    response = {"fields": [{"name": "off_work_period", "value": quote,
                            "quote": quote, "basis": "stated"}]}
    out = cap.implementation(
        context=SimpleNamespace(llm=SimpleNamespace(read=lambda **kw: response)),
        **{"datastate:drdemo.span": text})
    record = out["datastate:drdemo.period_origin"]
    return (out["datastate:drdemo.period"], record.get("refusal_reason"),
            record.get("quote_verified"))


print("== raw output below this line ==")
for label, spans in (("CORRECT_split", CORRECT), ("MISALIGNED_split", MISALIGNED)):
    print(repr(("[" + label + "]",)))
    reads = []
    for i, (start, end) in enumerate(spans):
        text = EMAIL[start:end]
        quote = next((c for c in ("off work for at least two weeks",
                                  "off work for at least six weeks")
                      if c in text), None)
        value, refusal, verified = (read_span(text, quote) if quote
                                    else (None, "no phrase in span", None))
        reads.append(quote)
        print(repr(("   member", i, "span_text:", text.strip()[:46],
                    "| filed_as:", FILED[i], "| read:", value,
                    "| refusal:", refusal, "| verified:", verified)))
    print(repr(("   VALIDATION:", validate(spans, EMAIL, reads))))
    print(repr(("   ATTRIBUTION CORRECT:",
                reads[0] == "off work for at least two weeks"
                and reads[1] == "off work for at least six weeks")))

# The fifth check that DOES separate them: a quote must fall between the filed
# claimant's own name and the next claimant's name, in DOCUMENT coordinates.
names = {"C. Mensah": EMAIL.index("C. Mensah"),
         "D. Laurent": EMAIL.index("D. Laurent")}


def owns(filed, quote_offset):
    start = names[filed]
    later = [o for o in names.values() if o > start]
    return start < quote_offset < (min(later) if later else len(EMAIL))


print(repr(("name offsets:", names,
            "two_weeks@", EMAIL.index("off work for at least two weeks"),
            "six_weeks@", EMAIL.index("off work for at least six weeks"))))
print(repr(("ORDERING CHECK  correct(D. Laurent, six_weeks):",
            owns("D. Laurent", EMAIL.index("off work for at least six weeks")))))
print(repr(("ORDERING CHECK misaligned(D. Laurent, two_weeks):",
            owns("D. Laurent", EMAIL.index("off work for at least two weeks")))))
print(repr(("name-containment check on the misaligned span:",
            "D. Laurent" in EMAIL[CUT_BAD:])))
