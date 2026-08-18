"""S131.6's untested door: an injury member with NO routed_as_of at all.

Run from a checkout of demo/dr-routing-policy (edb2749):
    PYTHONPATH=. python scripts/critic/probe_step2_nodate.py

The as-of reader has nothing to read, so the dated threshold lookup has no
date. Dumps the raw graph state, then renders under each plausible episode
classification. Composed by the critic: the exposure edit (dropping
routed_as_of from the injury member) and the episode fixtures. Every graph,
stop and rendered line is the tree's. Repr-only; verdicts in coordination S132."""
from mindsos_intelligence import execution
from decision_records_demo.dr_routing import (
    CASE_A_EXPOSURES, DS_CLAIM_EXPOSURES, routing_harness, routing_plan,
)
from decision_records_demo.dr_render import render_from_graphs

NO_DATE = [dict(e) for e in CASE_A_EXPOSURES]
for exposure in NO_DATE:
    if exposure.get("off_work_weeks"):
        exposure.pop("routed_as_of", None)

mm, dispatcher, writer, request_run = routing_harness()
graphs = []
execution.run(dispatcher, writer, routing_plan(), request_run, mm=mm,
              solve_seed={DS_CLAIM_EXPOSURES: NO_DATE},
              capacity_graphs=graphs, case_label="claim CLM-4188")

print("== raw output below this line ==")
print(repr(("graphs returned:", len(graphs))))
for graph in graphs:
    types = {}
    stopped = []
    for node in graph.nodes.values():
        kind = getattr(node, "type_name", None)
        types[kind] = types.get(kind, 0) + 1
        if kind == "RunStopped":
            stopped.append(node.properties or {})
    print(repr(("graph:", graph.graph_id, "types:", sorted(types.items()))))
    for props in stopped:
        print(repr(("  RunStopped props:", props)))

for outcome in ("completed", "partial", "stopped", "failed"):
    episode = {"capacity_root_ref": "x",
               "consolidated_at": "2026-08-17T12:00:00.000000+00:00",
               "outcome_classification": outcome}
    try:
        page = render_from_graphs(graphs, episode)
        print(repr(("[outcome=" + outcome + "] RENDERED:")))
        for line in page.splitlines():
            print(repr(line))
    except Exception as exc:
        print(repr(("[outcome=" + outcome + "] RAISED",
                    type(exc).__name__, str(exc)[:200])))
