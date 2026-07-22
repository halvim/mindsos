"""Cycle recognition demo — YOU run this to see the brain's verdicts.

Boots the NILM brain, fits `calibrate` off a clean-cycle seed, then runs the
finder-composed + `execute_pipeline`-executed cycle recognition over a real
PLAID record, printing the per-window verdict. Nothing is persisted.

Run (with mindsos importable + numpy), from the MindsOS repo root::

    PYTHONPATH=.:projects/amii_study \
      python projects/amii_study/nilm_brain/scripts/cycle_demo.py \
      --data datasets/PLAID_2018/_sample --record Water_kettle

`--seed` picks the clean-cycle record calibrate learns its normal band from
(defaults to the same record's early windows).
"""

from __future__ import annotations

import argparse
import glob
import os

import numpy as np

from nilm_brain.control import Solver


def load_record(base: str, name: str) -> np.ndarray:
    matches = [x for x in glob.glob(os.path.join(base, "*.csv"))
               if os.path.basename(x).startswith(name)]
    if not matches:
        raise SystemExit(f"no record starting with {name!r} in {base}")
    return np.loadtxt(matches[0], delimiter=",")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="dir of PLAID *.csv records")
    ap.add_argument("--record", default="Water_kettle")
    ap.add_argument("--seed", default=None, help="clean-cycle seed record (default: --record)")
    ap.add_argument("--max-windows", type=int, default=20)
    args = ap.parse_args()

    raw = load_record(args.data, args.record)
    seed = load_record(args.data, args.seed) if args.seed else raw

    solver = Solver("nilm-demo")
    print(f"segment composed by ConjunctionFinder: {len(solver.segment)} steps "
          f"-> {solver.segment.target_datastate}")
    params = solver.fit_calibrate(seed)
    print(f"calibrate params fit off seed: {params['provenance']} "
          f"(energy_mean={params['energy_mean']:.3f}, energy_std={params['energy_std']:.3f})")

    print(f"\nrecognizing {args.record} ({args.max_windows} windows):")
    print(f"{'start':>7} {'freq':>9} {'resid':>8} {'spec':>7} {'temp':>7} "
          f"{'conf':>6}  verdict")
    for o in solver.recognize(raw, max_windows=args.max_windows):
        v = o["verdict"]
        print(f"{o['start']:7d} {o['freq']:9.4f} {o['residual_energy']:8.3f} "
              f"{o['spectral']:7.3f} {o['temporal']:7.3f} {o['confidence']:6.3f}  "
              f"{v['state']}" + (f" [{v.get('axis')}]" if v.get('axis') else ""))


if __name__ == "__main__":
    main()
