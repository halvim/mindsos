"""arc-viz — produce the human visual for a task.

    python -m arc_solver.viz.show [task_id ...]        (default: 00d62c1b 05f2a901)

Runs the live brain (solve -> ingest_solve -> express through one L4), then the
human adapter renders the resulting artifact to a self-contained HTML page under
`arc_solver/viz/out/` (gitignored).
"""

from __future__ import annotations

import os
import sys

from arc_solver.spike.arc_grids import load_dataset
from arc_solver.spike.arc_l4 import build_instance

from .capabilities import install_viz
from .combined import artifact_for
from .human import render_html

_OUT = os.path.join(os.path.dirname(__file__), "out")


def main(argv=None) -> int:
    task_ids = list(argv if argv is not None else sys.argv[1:]) or ["00d62c1b", "05f2a901"]
    inst = build_instance()
    install_viz(inst.layer)
    dataset = load_dataset()
    os.makedirs(_OUT, exist_ok=True)
    for task_id in task_ids:
        artifact = artifact_for(inst, task_id, dataset)
        path = os.path.join(_OUT, f"{task_id}.html")
        with open(path, "w") as fh:
            fh.write(render_html(artifact))
        print(f"  [ok] arc-viz human adapter: {task_id} "
              f"({artifact['header']['outcome']}) -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
