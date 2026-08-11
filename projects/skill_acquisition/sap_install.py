"""SAP install adapter — approved report → MindsOS register-plan (v0.1).

Runs ONLY on an approved, passing report (the commit boundary, Stage C). It does NOT
re-implement install — it emits the ordered `register_datastate` / `register_capacity` /
`add_constraint` call plan (in the report's Kahn order) and hands off to MindsOS's real
functions, which re-check. Default = dry-run (prints the plan); `--execute` calls MindsOS
(needs a running instance + admin session — not available in a bare sandbox).

CLI:  python3 sap_install.py <input.json> <report.json> [--execute]
"""
from __future__ import annotations

import json
import sys
from typing import Dict, List


def build_plan(inp: dict, report: dict) -> List[dict]:
    """One register step per component, in the report's validated build order."""
    comps: Dict[str, dict] = {c["id"]: c for c in inp["components"]}
    plan: List[dict] = []
    for cid in report["order"]:
        c = comps[cid]
        if c["kind"] == "datastate":
            plan.append({"call": "register_datastate", "iri": cid,
                         "realm": c.get("realm"), "allow_new_realm": True})
        elif c["kind"] == "capacity":
            plan.append({"call": "register_capacity", "iri": cid,
                         "inputs": c.get("inputs", []), "outputs": c.get("outputs", []),
                         "family": c.get("family")})
        elif c["kind"] == "relation":
            plan.append({"call": "add_constraint", "endpoints": c.get("endpoints", [])})
        # meta / param → no register step
    return plan


def guard(report: dict) -> None:
    if not report.get("ok"):
        sys.exit("REFUSED: report has unresolved gaps (ok=false). Fix them first.")
    if not report.get("approved"):
        sys.exit("REFUSED: report not approved. Set \"approved\": true after review.")


def execute(plan: List[dict]) -> None:
    # Real MindsOS handoff. Imports are local so dry-run never needs mindsos installed.
    from mindsos_capacity import CapacityLayer  # noqa: F401
    raise SystemExit("--execute needs a live MindsOS instance + admin session; "
                     "wire CapacityLayer.register_* here at commit time.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: python3 sap_install.py <input.yaml|json> <report.json> [--execute]")
    import sap_io                       # accept the same friendly YAML the backend reads
    inp = sap_io.load(sys.argv[1])
    report = json.load(open(sys.argv[2]))
    guard(report)
    plan = build_plan(inp, report)
    if "--execute" in sys.argv:
        execute(plan)
    else:
        print(f"DRY-RUN — {len(plan)} register steps (approved, in build order):\n")
        for i, s in enumerate(plan, 1):
            print(f"{i:2}. {s['call']:20} {s.get('iri','') or s.get('endpoints','')}")
