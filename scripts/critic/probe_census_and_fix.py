"""Probe 119.6 + the 119.1 proposed fix: (i) registered-set vs source-grep
census divergence; (ii) value-in-span, as stated, against S118.1's replies.

Runs against origin/main ead3bd1:
    PYTHONPATH=. python scripts/critic/probe_census_and_fix.py
Repr-only; verdicts in coordination S120."""
from mindsos_capacity.builtins.comprehension_v0 import build_reader
from mindsos_capacity.datastate import ShapeDescriptor

def reader(n):
    return build_reader(
        name=f"drdemo.read_{n}",
        source_datastate_iri="datastate:drdemo.claim_email",
        value_datastate_iri=f"datastate:drdemo.{n}",
        prompt_iri="prompt:drdemo.extract_components", prompt_version=1,
        field_name=n, question=f"the {n} the document states",
        description=f"reads {n}", origin_party_phrase="the claimant",
        source_identity_phrase="the claim email", expected_basis="stated",
        value_shape=ShapeDescriptor.scalar("int"))

print("== raw output below this line ==")
caps = [reader("off_work_weeks"), reader("hospital_transfer_days")]
print(repr(("registered-set census:",
            [(c.name, c.consults_llm) for c in caps],
            "count_with_flag:", sum(1 for c in caps if c.consults_llm))))
# source grep companion (run in the tree):
#   grep -rn "consults_llm=True" --include="*.py" . | grep -v test
# returns exactly one code line: comprehension_v0.py:578 — the FACTORY.

CASES = [
    ("A_correct",               "6", "off work for at least six weeks"),
    ("C_wrong_value_true_quote", "2", "off work for at least six weeks"),
    ("D_irrelevant_true_quote",  "6", "Dear team,"),
]
for label, value, span in CASES:
    print(repr((label, "value_in_span:", str(value) in span)))
