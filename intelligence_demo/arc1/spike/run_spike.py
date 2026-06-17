"""M1 spike entry point.

1. Stands up a live in-memory CapacityLayer, registers the arc-realm
   DataStates + perceive/profile capacities.
2. Proves find_pipeline DISCOVERS the perceive chain (no router).
3. Builds the TaskProfile for every train task and writes the debug data
   the human interface (arc_debug.html) renders.

Usage (from repo root):
    python -m intelligence_demo.arc1.spike.run_spike [N]
where N = number of train tasks to dump (default: all 400).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import sys

from . import arc_capacities as ac
from . import arc_grids, arc_metagraph, arc_profile, arc_search

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
