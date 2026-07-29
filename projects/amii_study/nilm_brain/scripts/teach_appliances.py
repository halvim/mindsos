"""Teach nilm's appliance library over real PLAID and PERSIST it durably.

Run this ONCE (or whenever you want to re-teach): it boots the durable resident
brain, teaches each PLAID class through the mindsos signature segment
(``teach_appliance`` -> ``fit_appliance``), snapshots the learned library +
normalizer + cutoff into the Local ``learned-parameters`` role, and ``save``s
to Falkor. Afterwards ``python -m nilm_brain.repl`` boots already knowing them.

    PYTHONPATH=.:projects/amii_study python \
      projects/amii_study/nilm_brain/scripts/teach_appliances.py \
      --data /home/sanmyaku/_plaid_full/_sample_expanded

Runs the brain (execute_pipeline per window), so allow a couple of minutes;
fit is O(n^2) in exemplars — scale with --train / --max-windows.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
from collections import defaultdict

import numpy as np

from mindsos_server.boot import boot_brain
from nilm_brain.control import Solver
from nilm_brain.persistence import persist_appliance_state


def label_of(path: str) -> str:
    return re.sub(r"_\d+$", "", os.path.basename(path)[:-4])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="dir of PLAID <label>_<n>.csv")
    ap.add_argument("--user", default="nilm")
    ap.add_argument("--train", type=int, default=6, help="instances/class to teach")
    ap.add_argument("--max-windows", type=int, default=8)
    a = ap.parse_args()

    by_label = defaultdict(list)
    for f in sorted(glob.glob(os.path.join(a.data, "*.csv"))):
        by_label[label_of(f)].append(f)
    labels = sorted(by_label)
    if not labels:
        raise SystemExit(f"no records in {a.data}")

    from mindsos_core.config import FalkorConfig
    from mindsos_core.persistence.client import FalkorClient
    client = FalkorClient(FalkorConfig.from_env())
    try:
        stack = boot_brain(client, user=a.user)
        s = Solver(a.user, cl=stack.cl, session=stack.session)  # install nilm L3

        print("teaching (brain: signature segment per window):")
        for lab in labels:
            fs = by_label[lab][:a.train]
            for f in fs:
                s.teach_appliance(lab, np.loadtxt(f, delimiter=","),
                                  max_windows=a.max_windows)
            print(f"  {lab:28s} taught {len(fs)} instance(s)")

        s.fit_appliance()
        print(f"fit: {len(s.appliance_library)} exemplars  cutoff={s.match_cutoff}")

        persist_appliance_state(stack.cl, stack.session, s)
        stack.save()
        print(f"persisted appliance_state and saved Local for {a.user!r}. "
              "Boot: python -m nilm_brain.repl")
    finally:
        client.close()


if __name__ == "__main__":
    main()
