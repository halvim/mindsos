"""Real-PLAID appliance recognition — through the BRAIN (#3 demo).

This is an operator harness (loads CSVs, splits train/test, tallies) — but the
recognition it calls is mindsos capacities executing: `teach_appliance` /
`fit_appliance` / `recognize_appliance` run the finder-composed signature
segment via `execute_pipeline`, the dispatched onset/assemble/distance
capacities, and the `recognize` decision capacity. Unlike `classify_eval.py`
(which reimplemented the features in standalone numpy), the signal->signature->
match->verdict path here IS the brain. Results are session observations, not
persisted brain truth.

    PYTHONPATH=.:projects/amii_study python \
      projects/amii_study/nilm_brain/scripts/appliance_recognize_demo.py \
      --data /home/sanmyaku/_plaid_full/_sample_expanded

Runs the brain (execute_pipeline per window), so allow a couple of minutes.
Scale the library with --train / --max-windows; fit is O(n^2) in exemplars.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
from collections import Counter, defaultdict

import numpy as np

from nilm_brain.control import Solver


def label_of(path: str) -> str:
    return re.sub(r"_\d+$", "", os.path.basename(path)[:-4])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--train", type=int, default=6, help="instances/class to teach")
    ap.add_argument("--test", type=int, default=4, help="held-out instances/class to recognize")
    ap.add_argument("--max-windows", type=int, default=8)
    ap.add_argument("--k", type=int, default=5)
    a = ap.parse_args()

    by_label = defaultdict(list)
    for f in sorted(glob.glob(os.path.join(a.data, "*.csv"))):
        by_label[label_of(f)].append(f)
    labels = sorted(by_label)
    if not labels:
        raise SystemExit(f"no records in {a.data}")

    s = Solver("nilm-plaid-recognize")

    # ── teach: the taught instance library (each teach runs the signature segment)
    train_files, test_files = [], []
    print("teaching (brain: signature segment per window):")
    for lab in labels:
        fs = by_label[lab]
        tr = fs[:a.train]
        te = fs[a.train:a.train + a.test]
        train_files += [(lab, f) for f in tr]
        test_files += [(lab, f) for f in te]
        print(f"  {lab:28s} train={len(tr)} test={len(te)}")
    for lab, f in train_files:
        s.teach_appliance(lab, np.loadtxt(f, delimiter=","), max_windows=a.max_windows)

    # ── fit the L2 normalizer + negative-aware cutoff (brain: signature_distance)
    print("\nfitting normalizer + cutoff (brain: signature_distance over the library)...")
    s.fit_appliance()
    print(f"  library exemplars={len(s.appliance_library)}  cutoff={s.match_cutoff}")

    # ── recognize held-out instances (brain: segment + k-NN + recognize verdict)
    conf = {lab: Counter() for lab in labels}
    print("\nrecognizing held-out instances (brain: recognize_appliance):")
    for lab, f in test_files:
        outs = s.recognize_appliance(np.loadtxt(f, delimiter=","),
                                     max_windows=a.max_windows, k=a.k)
        got = [o["verdict"]["appliance"] for o in outs
               if o["verdict"]["state"] == "recognized"]
        pred = Counter(got).most_common(1)[0][0] if got else "unknown"
        conf[lab][pred] += 1

    # ── confusion + accuracy (operator bookkeeping) ──────────────────────────
    def sh(x):
        return x.split("_")[0][:9]

    cols = labels + ["unknown"]
    total = correct = 0
    print("\n=== confusion (true \\ predicted) — BRAIN on real PLAID ===")
    print("true".ljust(12) + "".join(sh(c).ljust(10) for c in cols))
    for lab in labels:
        row = "".join(f"{conf[lab][c]:<10d}" for c in cols)
        n = sum(conf[lab].values()) or 1
        rec = conf[lab][lab] / n
        total += n
        correct += conf[lab][lab]
        print(sh(lab).ljust(12) + row + f"  recall={rec:.2f}")
    print(f"\noverall accuracy = {correct}/{total} = {correct / max(1, total):.3f}")
    print("(kettle: single-house instances — its score is optimistic, as flagged)")


if __name__ == "__main__":
    main()
