"""S131.6: routing_policy_file claims stored words only — which are not?

Run from a checkout of demo/dr-routing-policy (edb2749):
    PYTHONPATH=. python scripts/critic/probe_policy_file.py

Prints the file for three dates beside the stored editions themselves, so any
character the function supplies is visible by comparison rather than by
argument. Composed by the critic: the three dates. Repr-only; verdicts in
coordination S132."""
from decision_records_demo.dr_routing import (
    ROUTING_EDITION_2023, ROUTING_EDITION_2024, routing_policy_file,
)

print("== raw output below this line ==")
for label, as_of in (("as_of_2026", "2026-06-03"),
                     ("as_of_2023", "2023-06-03"),
                     ("as_of_uncovered", "2019-01-01")):
    print(repr((label, routing_policy_file(as_of))))
print(repr(("stored_2023:", ROUTING_EDITION_2023)))
print(repr(("stored_2024:", ROUTING_EDITION_2024)))
try:
    print(repr(("as_of_malformed:", routing_policy_file("June 3rd 2026"))))
except Exception as exc:
    print(repr(("as_of_malformed RAISED", type(exc).__name__, str(exc)[:140])))
