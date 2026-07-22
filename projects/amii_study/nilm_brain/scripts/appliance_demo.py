"""Appliance-signature recognition on the CURRENT channel (#3) — YOU run this.

Teach one appliance's current signature, then recognize every record on current
and report which windows match the taught reference. The appliance fingerprint
lives in the current waveform shape: fit the fundamental sinusoid -> the residual
is the harmonic signature. Switching loads (laptop / CFL / microwave) have rich,
distinctive signatures; resistive loads (kettle / hairdryer) draw near-sinusoidal
current, so their residual is faint and they read as clean current cycles.

The calibrate seed is a *resistive* appliance's current (a clean current cycle),
so a switching appliance departs from that band -> request_reference -> teachable.

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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="dir of PLAID *.csv records")
    ap.add_argument("--teach", default="Laptop", help="appliance to teach (a switching load)")
    ap.add_argument("--seed", default="Water_kettle",
                    help="resistive appliance for the clean-current calibrate seed")
    ap.add_argument("--max-windows", type=int, default=16)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.data, "*.csv")))
    records = {os.path.basename(f)[:-4]: np.loadtxt(f, delimiter=",") for f in files}

    s = Solver("appliance-demo")
    s.fit_calibrate(_load(args.data, args.seed), channel="current")
    ref = s.teach(args.teach, _load(args.data, args.teach), channel="current")
    print(f"seed(current)={args.seed!r}  taught={args.teach!r} "
          f"(template {len(ref['template'])} samples)")
    print(f"gates={s.thresholds}\n")

    terms = ("cycle", "recognized", "request_reference", "held_ambiguity")
    print(f"{'record':30s} {'tally':46s} matched[{args.teach}]")
    for name, raw in records.items():
        outs = s.recognize(raw, max_windows=args.max_windows, channel="current")
        tally = {t: sum(o["verdict"]["state"] == t for o in outs) for t in terms}
        matched = sum(o["verdict"].get("reference") == args.teach for o in outs)
        flag = "  <-- TAUGHT" if name.startswith(args.teach) else ""
        print(f"{name:30s} {str(tally):46s} {matched}{flag}")


if __name__ == "__main__":
    main()
