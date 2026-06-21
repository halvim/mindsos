"""M1 spike entry point.

1. Stands up a live in-memory CapacityLayer, registers the arc-realm
   DataStates + perceive/profile capacities.
2. Proves find_pipeline DISCOVERS the perceive chain (no router).
3. Builds the TaskProfile for every train task and writes the debug data
   the human interface (arc_debug.html) renders.

Usage (via the launcher):
    ./run_spike [N]
where N = number of train tasks to dump (default: all 400).
"""

from __future__ import annotations

if __package__ in (None, ""):
    import os as _os
    import runpy as _runpy
    import sys as _sys
    _pkg_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", ".."))
    _repo_root = _os.path.abspath(_os.path.join(_pkg_root, "..", ".."))
    for _p in (_repo_root, _pkg_root):
        if _p not in _sys.path:
            _sys.path.insert(0, _p)
    _runpy.run_module("intelligence_demo.arc1.spike.run_spike", run_name="__main__")
    _sys.exit(0)

import datetime as _dt
import json
import os
import sys

from . import arc_capacities as ac
from . import arc_grids, arc_metagraph, arc_profile, arc_search, arc_solver

_HERE = os.path.dirname(os.path.abspath(__file__))
_OUT_JS = os.path.join(_HERE, "arc_debug_data.js")


def main(argv: list) -> int:
    limit = int(argv[1]) if len(argv) > 1 else None

    cl = ac.fresh_layer()

    # ── (2) dataflow proof ──────────────────────────────────────────────
    report = arc_profile.discovery_report(cl)
    print("find_pipeline discovery (PRODUCES/CONSUMES walk, no dispatcher):")
    for route, chain in report.items():
        print(f"  {route:24s} = {' -> '.join(c.split(':')[-1] for c in chain)}")

    # assertions: the chain is exactly the expected perceive composition
    assert report["raw_task -> shape"] == [
        ac.CAP_COMPREHEND, ac.CAP_BUILD_GRID,
        ac.CAP_EXTRACT_OBJECTS, ac.CAP_EXTRACT_SHAPES,
    ], report["raw_task -> shape"]
    assert report["raw_task -> palette"] == [
        ac.CAP_COMPREHEND, ac.CAP_BUILD_GRID, ac.CAP_EXTRACT_PALETTE,
    ], report["raw_task -> palette"]
    print("  [ok] discovered chains match the locked perceive composition.")

    # ── (3) build profiles + dump debug data ────────────────────────────
    dataset = arc_grids.load_dataset()
    # Canonical ARC order = task IDs sorted ascending (matches arc_viewer.html).
    ids = sorted(dataset["train"])
    if limit is not None:
        ids = ids[:limit]
    tasks = [arc_profile.build_profile(dataset, "train", tid) for tid in ids]

    # Solver run (read-only, option A) — scoped to task #8 (the use case).
    solver = None
    if arc_solver.TASK8 in dataset["train"]:
        prof8 = next((t for t in tasks if t["task_id"] == arc_solver.TASK8), None)
        if prof8 is None:
            prof8 = arc_profile.build_profile(dataset, "train", arc_solver.TASK8)
        raw8 = arc_grids.get_task(dataset, "train", arc_solver.TASK8)
        solver = arc_solver.build_solver(prof8, raw_task=raw8)

    payload = {
        "generated": _dt.datetime.now().isoformat(timespec="seconds"),
        "n_tasks": len(tasks),
        "discovery": report,
        "capacities": ac.ordered_catalog(),
        "search": {
            "facets": arc_search.FACETS,
            "availability": arc_search.build_availability(tasks),
        },
        "arc_metagraph": arc_metagraph.summary(),
        "solver": solver,
        "tasks": tasks,
    }
    with open(_OUT_JS, "w") as fh:
        fh.write("window.ARC_DATA = ")
        json.dump(payload, fh, separators=(",", ":"))
        fh.write(";\n")
    size_kb = os.path.getsize(_OUT_JS) // 1024
    print(f"  [ok] wrote {len(tasks)} task profiles -> "
          f"{os.path.basename(_OUT_JS)} ({size_kb} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
