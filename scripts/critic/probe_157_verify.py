"""S157.3/S157.4 verified against MY OWN licence_v2, unmodified.

No imports — runnable anywhere:
    python scripts/critic/probe_157_verify.py

S157 asked the critic lane to run C2 and A2 itself rather than take the build
lane's word. This is that run, using the same predicate and the same regex as
probe_licence_defeat.py.

Composed by the critic: C2, A2, E and F, restated from S157's descriptions.
OWNER_email_b_txt is decision_records_demo/documents/email_b.txt at
origin/feat/dr-step3, verbatim apart from the header lines. Repr-only;
verdicts in coordination S158."""
import re

NAME = re.compile(r"\b[A-Z]\. [A-Z][a-z]+\b")


def units(doc):
    return [line for line in doc.split("\n") if line.startswith("- ")]


def licence_v2(doc):
    u = units(doc)
    if not u:
        return False, "no discrete units", []
    per = [sorted(set(NAME.findall(x))) for x in u]
    if any(len(p) != 1 for p in per):
        return (False,
                f"a unit names {[len(p) for p in per]} claimants, not exactly one",
                per)
    flat = [p[0] for p in per]
    if len(set(flat)) != len(flat):
        return False, "a claimant appears in two units", per
    return True, "licensed: " + str(flat), per


EMAIL_B = (
    "From: Renata Okonkwo <r.okonkwo@harbourline-brokers.example>\n"
    "Subject: FW: fleet incident 29 May\n\nDetails as the client filed them:\n\n"
    "- A. Silva, unit 4, the lead van: panel damage only, already booked into the bodyshop.\n"
    "- B. Osei, unit 7: panel damage only, tailgate will not close.\n"
    "- C. Mensah, driver of unit 11: he was taken to hospital from the scene, "
    "and his GP has signed him off work for at least six weeks.\n"
    "- D. Laurent, front-seat passenger in unit 11: seen by paramedics at the roadside.\n")

DOCS = {
    "OWNER_email_b_txt": EMAIL_B,
    "C2_metadata_bullets_all_name_shaped": (
        "Claim CLM-4188. Two people were hurt.\n"
        "- Handler: R. Ngo\n- Adjuster: T. Boye\n"
        "- Broker: P. Adeyemi\n- Fleet contact: S. Iwu\n"),
    "A2_second_person_by_role": (
        "Claim CLM-4188.\n"
        "- C. Mensah was driving; his passenger is off work for at least six weeks.\n"
        "- D. Laurent returned to work on Monday.\n"),
    "E_third_party_NAMED_in_unit": (
        "Claim CLM-4188.\n"
        "- C. Mensah, driver of unit 11: taken to hospital; Dr A. Bell has "
        "signed him off for six weeks.\n"
        "- D. Laurent, passenger: seen at the roadside.\n"),
    "F_same_person_two_forms": (
        "Claim CLM-4188.\n"
        "- C. Mensah, driver: taken to hospital.\n"
        "- Mensah is off work for six weeks.\n"),
}

print("== raw output below this line ==")
for label, doc in DOCS.items():
    ok, why, per = licence_v2(doc)
    print(repr((label, "LICENSED:", ok, why, "regex_hits_per_unit:", per)))
