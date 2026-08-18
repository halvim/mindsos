"""Is the date-road fixture guard's DOMAIN mechanical or enumerated?

Run from a checkout of demo/dr-routing-policy (a60a22c):
    PYTHONPATH=. python scripts/critic/probe_fixture_guard_domain.py

S133.1 closes the missing-date road by fixture. This simulates a fourth
exposure fixture arriving the way a later ship would add one, then runs the
shipped guard's predicate beside a derived one that finds its domain by
scanning the module. Composed by the critic: CASE_C_EXPOSURES and both
predicate copies. The fixtures and the module are the tree's. Repr-only;
verdicts in coordination S134."""
from decision_records_demo import dr_routing

dr_routing.CASE_C_EXPOSURES = [
    {"claimant": "E. Nakamura", "coverage": dr_routing.COVERAGE_INJURY,
     "loss": "collision", "off_work_weeks": 9},
]


def shipped_guard_predicate():
    """The shipped guard's own dict, copied verbatim from the guard body."""
    fixtures = {
        "CASE_A_EXPOSURES": dr_routing.CASE_A_EXPOSURES,
        "CASE_A_EXPOSURES_2023": dr_routing.CASE_A_EXPOSURES_2023,
        "CASE_B_EXPOSURES": dr_routing.CASE_B_EXPOSURES,
    }
    bad = [(name, exposure) for name, exposures in fixtures.items()
           for exposure in exposures if not exposure.get("routed_as_of")]
    return sorted(name for name, _ in bad), sorted(fixtures)


def derived_predicate():
    """The same claim with its domain derived from the module instead."""
    found = {}
    for name in dir(dr_routing):
        value = getattr(dr_routing, name)
        if (isinstance(value, list) and value
                and all(isinstance(x, dict) and "coverage" in x for x in value)):
            found[name] = value
    bad = [(name, exposure) for name, exposures in found.items()
           for exposure in exposures if not exposure.get("routed_as_of")]
    return sorted(name for name, _ in bad), sorted(found)


print("== raw output below this line ==")
print(repr(("shipped_guard: dateless_fixtures, domain =", shipped_guard_predicate())))
print(repr(("derived_scan:  dateless_fixtures, domain =", derived_predicate())))
