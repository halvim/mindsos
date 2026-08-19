"""S155.5 Q4: is (4)'s structural licence defeatable?

No imports — runnable anywhere:
    python scripts/critic/probe_licence_defeat.py

Part 1 tests S155.3's condition as written (the document presents discrete
units; one proposed span per unit) against three documents that satisfy it and
still produce a wrong Record. Part 2 tests a NARROWER predicate — each unit
names exactly one claimant and no claimant appears twice — against the same
documents plus S153.1's prose case.

Composed by the critic: every document, and both predicates. Repr-only;
verdicts in coordination S156."""
import re

NAME = re.compile(r"\b[A-Z]\. [A-Z][a-z]+\b")
NAMES = ["C. Mensah", "D. Laurent"]

DOCS = {
    "control": (
        "Claim CLM-4188.\n"
        "- C. Mensah, bruising; off work for at least two weeks.\n"
        "- D. Laurent, right wrist; off work for at least six weeks.\n"),
    "A_two_people_in_one_bullet": (
        "Claim CLM-4188.\n"
        "- C. Mensah was driving; his passenger D. Laurent is off work for at least six weeks.\n"
        "- C. Mensah returned to work on Monday.\n"),
    "B_continuation_bullet": (
        "Claim CLM-4188.\n"
        "- D. Laurent, right wrist, taken to hospital from the scene.\n"
        "- Off work for at least six weeks per her GP.\n"
        "- C. Mensah, bruising, no transfer.\n"),
    "C_bullets_are_not_exposures": (
        "Claim CLM-4188. Two people were hurt.\n"
        "- Policy: HH-99213\n- Date of loss: 12 March\n"
        "- Both claimants attended A&E\n- Adjuster: R. Ngo\n"),
    "S153_1_B_prose": (
        "C. Mensah and D. Laurent were both hurt in the loading-dock collision. "
        "Mensah will be off work for at least two weeks; Laurent for at least "
        "six weeks.\n"),
    "D_document_contradicts_its_own_format": (
        "Claim CLM-4188.\n"
        "- C. Mensah, driver. The six weeks below applies to him.\n"
        "- D. Laurent, passenger, off work for at least six weeks.\n"),
}


def units(doc):
    return [line for line in doc.split("\n") if line.startswith("- ")]


def licence_v1(doc, spans):
    """S155.3 as written: discrete units, one span per unit."""
    u = units(doc)
    return bool(u) and len(spans) == len(u) and all(s in u for s in spans)


def first_name(span):
    hits = [(span.index(n), n) for n in NAMES if n in span]
    return min(hits)[1] if hits else None


def licence_v2(doc):
    """Narrower: each unit names exactly one claimant, none twice."""
    u = units(doc)
    if not u:
        return False, "no discrete units"
    per = [sorted(set(NAME.findall(x))) for x in u]
    if any(len(p) != 1 for p in per):
        return False, f"a unit names {[len(p) for p in per]} claimants, not exactly one"
    flat = [p[0] for p in per]
    if len(set(flat)) != len(flat):
        return False, "a claimant appears in two units"
    return True, "licensed: " + str(flat)


print("== raw output below this line ==")
print(repr("[part 1 — S155.3's condition as written]"))
for label in ("control", "A_two_people_in_one_bullet", "B_continuation_bullet",
              "C_bullets_are_not_exposures"):
    doc = DOCS[label]
    spans = units(doc)
    filed = [first_name(s) for s in spans]
    carries = [("six weeks" in s or "two weeks" in s) for s in spans]
    print(repr((label, "licensed:", licence_v1(doc, spans), "units:", len(spans),
                "filed_as:", filed, "unit_carries_a_period:", carries)))
    for i, span in enumerate(spans, start=1):
        print(repr(("   unit", i, "filed:", filed[i - 1], "|", span[:72])))

print(repr("[part 2 — the narrower predicate]"))
for label, doc in DOCS.items():
    ok, why = licence_v2(doc)
    print(repr((label, "LICENSED:", ok, why)))
