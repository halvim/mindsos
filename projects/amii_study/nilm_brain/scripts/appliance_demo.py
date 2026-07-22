"""Appliance-signature recognition on the CURRENT channel (#3) — DIAGNOSTIC.

Prints, per record, the verdict tally and the feature ranges (conf / spec / temp
/ residual_energy) plus the learned gates, so we can see *why* each appliance
lands where it does before teaching. Then attempts teach->recognize (guarded).

    PYTHONPATH=.:projects/amii_study \
      python projects/amii_study/nilm_brain/scripts/appliance_demo.py \
      --data /home/sanmyaku/_sample --teach Laptop --seed Water_kettle
"""

from __future__ import annotations

import argparse
import glob
import os

import numpy as np

from nilm_brain.control import Solver


def _load(base: str, name: str) -> np.ndarray:
    matches = [x for x in glob.glob(os.path.join(base, "*.csv"))
               if os.path.basename(x).startswith(name)]
    if not matches:
        raise SystemExit(f"no record starting with {name!r} in {base}")
    return np.loadtxt(matches[0], delimiter=",")


def _synthetic_clean_current(fs=30000.0, f0=60.0, n_cycles=40, v_nom=170.0):
    """A perfectly-resistive (pure-sinusoid) current — the zero-distortion
    baseline. No real appliance supplies this (all carry some harmonics), so the
    current-gate seed is synthetic (sanctioned; held out from the test set).
    col0=current, col1=voltage (matches the default channel_map)."""
    n = int(round(n_cycles * fs / f0))
    t = np.arange(n) / fs
    cur = np.sin(2 * np.pi * f0 * t)
    volt = v_nom * np.sin(2 * np.pi * f0 * t)
    return np.stack([cur, volt], axis=1)


def _mm(outs, key):
    xs = [float(o[key]) for o in outs]
    return f"{min(xs):.3f}/{sum(xs) / len(xs):.3f}/{max(xs):.3f}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--teach", default="Laptop")
    ap.add_argument("--seed", default="Water_kettle")
    ap.add_argument("--max-windows", type=int, default=16)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.data, "*.csv")))
    records = {os.path.basename(f)[:-4]: np.loadtxt(f, delimiter=",") for f in files}

    s = Solver("appliance-demo")
    s.fit_calibrate(_synthetic_clean_current(), channel="current")
    print(f"seed(current)=synthetic pure sinusoid   gates={s.thresholds}\n")

    terms = ("cycle", "recognized", "request_reference", "held_ambiguity")
    print(f"{'record':30s} tally  |  (min/mean/max) conf · spec · temp · resid")
    for name, raw in records.items():
        outs = s.recognize(raw, max_windows=args.max_windows, channel="current")
        tally = {t: sum(o["verdict"]["state"] == t for o in outs) for t in terms}
        print(f"{name:30s} {tally}\n"
              f"{'':30s} conf={_mm(outs, 'confidence')}  spec={_mm(outs, 'spectral')}  "
              f"temp={_mm(outs, 'temporal')}  resid={_mm(outs, 'residual_energy')}")

    print()
    try:
        ref = s.teach(args.teach, _load(args.data, args.teach), channel="current")
        print(f"taught {args.teach!r} (template {len(ref['template'])} samples)")
        for name, raw in records.items():
            outs = s.recognize(raw, max_windows=args.max_windows, channel="current")
            matched = sum(o["verdict"].get("reference") == args.teach for o in outs)
            print(f"  matched[{args.teach}] on {name:28s} = {matched}")
    except RuntimeError as e:
        print(f"teach skipped: {e}")


if __name__ == "__main__":
    main()
