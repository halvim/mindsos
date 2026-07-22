"""Pull K instances/class of the six target appliances from PLAID submetered
into an expanded sample dir. Diagnostic/operator — NOT brain truth, do not persist.

    python projects/amii_study/nilm_brain/scripts/pull_instances.py \
        --meta /home/sanmyaku/_plaid_full/metadata_submetered.json \
        --src  /home/sanmyaku/_plaid_full/submetered_raw/submetered_new \
        --out  /home/sanmyaku/_plaid_full/_sample_expanded \
        --per-class 6
"""
from __future__ import annotations

import argparse
import json
import os
import shutil

# canonical label -> substring matched in the (lowercased) PLAID appliance type
TARGETS = {
    "Compact_Fluorescent_Lamp": "compact fluorescent",
    "Fridge": "fridge",
    "Hairdryer": "hairdryer",
    "Laptop": "laptop",
    "Microwave": "microwave",
    "Water_kettle": "kettle",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", required=True)
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-class", type=int, default=6)
    a = ap.parse_args()

    meta = json.load(open(a.meta))
    recs = []
    for rid, m in meta.items():
        t = (m.get("appliance", {}).get("type", "") or "").strip().lower()
        loc = m.get("location", "") or ""
        recs.append((rid, t, loc))

    os.makedirs(a.out, exist_ok=True)
    print(f"{'class':28s} available  pulled  (houses)")
    for label, sub in TARGETS.items():
        cand = [(rid, loc) for (rid, t, loc) in recs
                if sub in t and os.path.exists(os.path.join(a.src, rid + ".csv"))]
        # prefer one per distinct location first (real cross-instance diversity),
        # then top up with the rest
        seen, picked = set(), []
        for rid, loc in cand:
            if loc and loc in seen:
                continue
            seen.add(loc)
            picked.append(rid)
            if len(picked) >= a.per_class:
                break
        for rid, loc in cand:
            if len(picked) >= a.per_class:
                break
            if rid not in picked:
                picked.append(rid)
        for rid in picked:
            shutil.copy(os.path.join(a.src, rid + ".csv"),
                        os.path.join(a.out, f"{label}_{rid}.csv"))
        houses = len({loc for rid, loc in cand if rid in picked})
        print(f"{label:28s} {len(cand):9d}  {len(picked):6d}  ({houses})")
    print("out:", a.out)


if __name__ == "__main__":
    main()
