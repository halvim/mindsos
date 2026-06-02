#!/usr/bin/env python3
"""
Phase 9f — Stratified sample for LLM-assisted validation.

Sample 500 synsets stratified across (POS × method) from the v4 state
(master-v3c.tsv = v3 + cognitive reseeding). Each sample row becomes
input to an LLM-judge subagent.

Output:
    phase9f-sample-batches/batch-01.tsv ... batch-10.tsv  (50 synsets each)
    phase9f-sample.tsv                                      (full 500)
"""
import os, csv, random, json
from collections import defaultdict, Counter

OUT_DIR = "/sessions/exciting-pensive-rubin/mnt/outputs"
MASTER  = os.path.join(OUT_DIR, "oewn-dulplus-master-v3c.tsv")
SAMPLE_DIR = os.path.join(OUT_DIR, "phase9f-sample-batches")

def main():
    random.seed(0x9F9F)
    os.makedirs(SAMPLE_DIR, exist_ok=True)

    print("Loading master (v4 = v3c)...", flush=True)
    rows = []
    with open(MASTER) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            rows.append(r)
    print(f"  loaded {len(rows):,} synsets", flush=True)

    # Stratify by (POS, method_prefix)
    buckets = defaultdict(list)
    for r in rows:
        pos = r["pos"]
        # Collapse method to its high-level phase/tier
        m = r["method"]
        if m.startswith("phase1"):
            mb = "phase1"
        elif m.startswith("phase3_tier1"):
            mb = "phase3_tier1"
        elif m.startswith("phase3_tier2"):
            mb = "phase3_tier2"
        elif m.startswith("phase3_tier3"):
            mb = "phase3_tier3"
        elif m.startswith("phase3_propagated"):
            mb = "phase3_propagated"
        elif m.startswith("phase4_A1"):
            mb = "phase4_A1_sat"
        elif m.startswith("phase4_A2"):
            mb = "phase4_A2_pert"
        elif m.startswith("phase4_A4") or m.startswith("phase4_A5") or m.startswith("phase4_A3"):
            mb = "phase4_A3_A4_A5"
        elif m.startswith("phase4_R"):
            mb = "phase4_adv"
        elif m.startswith("phase5alt") or m.startswith("gapfill"):
            mb = "phase5alt_gapfill"
        elif m.startswith("phase7"):
            mb = "phase7_review"
        elif m.startswith("phase8_systematic"):
            mb = "phase8_systematic"
        elif m.startswith("phase8_re_propagated"):
            mb = "phase8_re_propagated"
        elif m.startswith("phase9c"):
            mb = "phase9c_cognitive"
        else:
            mb = "other"
        buckets[(pos, mb)].append(r)

    print(f"\nStrata (pos, method_bucket):")
    for k in sorted(buckets.keys()):
        print(f"  {str(k):>50s}  {len(buckets[k]):>6,}")

    # Target 500 synsets, proportional allocation with a minimum floor of 5 per stratum
    total = 500
    sizes = {k: len(v) for k, v in buckets.items()}
    total_pop = sum(sizes.values())
    prop_alloc = {k: max(5, round(total * sz / total_pop)) for k, sz in sizes.items()}
    # Cap at bucket size
    prop_alloc = {k: min(prop_alloc[k], sizes[k]) for k in prop_alloc}
    print(f"\nProposed per-stratum sample sizes:")
    for k, n in sorted(prop_alloc.items()):
        print(f"  {str(k):>50s}  {n:>5}")

    # Sample
    sample = []
    for k, n in prop_alloc.items():
        sample.extend(random.sample(buckets[k], n))
    random.shuffle(sample)
    # Trim or pad to exactly 500
    sample = sample[:500]
    print(f"\nFinal sample size: {len(sample)}")

    # Write full sample
    cols = list(sample[0].keys())
    with open(os.path.join(OUT_DIR, "phase9f-sample.tsv"), "w", newline="") as f:
        w = csv.DictWriter(f, delimiter="\t", fieldnames=cols)
        w.writeheader()
        w.writerows(sample)

    # Write per-batch files (50 each)
    batch_size = 50
    for i in range(0, len(sample), batch_size):
        batch = sample[i:i+batch_size]
        bnum = (i // batch_size) + 1
        path = os.path.join(SAMPLE_DIR, f"batch-{bnum:02d}.tsv")
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, delimiter="\t", fieldnames=cols)
            w.writeheader()
            w.writerows(batch)
        print(f"  wrote {path} ({len(batch)} rows)")

    print(f"\nDONE. Total batches: {(len(sample) + batch_size - 1) // batch_size}")


if __name__ == "__main__":
    main()
