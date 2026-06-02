#!/usr/bin/env python3
"""
Phase 9f apply — apply the LLM-judge disagreements to the master.

Input: phase9f-judgements-consolidated.tsv (500 rows)
Process: For every row with judgement = 'disagree', update master using
the proposed_alternative (take first option if "X or Y" syntax).

Output: oewn-dulplus-master-v4.tsv (final)
"""
import os, re, csv
from collections import Counter

OUT_DIR = "/sessions/exciting-pensive-rubin/mnt/outputs"
WORKSPACE = "/sessions/exciting-pensive-rubin/mnt/Dulce - WordNet - FrameNet Mapping"
IN_MASTER = os.path.join(OUT_DIR, "oewn-dulplus-master-v3c.tsv")
JUDGE_TSV = os.path.join(OUT_DIR, "phase9f-judgements-consolidated.tsv")
OUT_MASTER = os.path.join(OUT_DIR, "oewn-dulplus-master-v4.tsv")

def parse_alternative(alt_str):
    """Parse 'dul:X or dul:Y' into the first option. Accept plain strings too."""
    s = alt_str.strip()
    # Split on ' or ' (case-insensitive)
    parts = re.split(r'\s+or\s+', s, flags=re.I)
    first = parts[0].strip()
    # Strip brackets if present
    if first.startswith("<") and first.endswith(">"):
        first = first[1:-1]
    return first

def main():
    print("[1/4] Loading LLM judgements...", flush=True)
    disagreements = []
    with open(JUDGE_TSV) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["judgement"] == "disagree" and r.get("proposed_alternative"):
                cls = parse_alternative(r["proposed_alternative"])
                if cls and cls != r["assigned_class"]:
                    disagreements.append({
                        "oewn_id":  r["oewn_id"],
                        "new_class": cls,
                        "batch":    r.get("batch", ""),
                        "rationale": r.get("rationale", ""),
                    })
    print(f"      {len(disagreements)} disagreements to apply", flush=True)

    print("[2/4] Loading master v3c...", flush=True)
    master = {}
    order = []
    with open(IN_MASTER) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            master[r["oewn_id"]] = r
            order.append(r["oewn_id"])
    print(f"      {len(master):,} synsets", flush=True)

    print("[3/4] Applying LLM-judge corrections...", flush=True)
    applied = []
    skipped = []
    for d in disagreements:
        oid = d["oewn_id"]
        if oid not in master:
            skipped.append(d)
            continue
        r = master[oid]
        old = r["dulplus_class"]
        new = d["new_class"]
        if old == new:
            continue
        r["dulplus_class"] = new
        r["method"]        = "phase9f_llm_judge_correction"
        r["provenance"]    = f"LLM batch {d['batch']}: {d['rationale'][:200]}"
        applied.append({"oewn_id": oid, "lemma": r["primary_lemma"],
                         "old": old, "new": new})
    print(f"      applied {len(applied)}, skipped {len(skipped)}", flush=True)

    # Class-shift summary
    shifts = Counter((a["old"], a["new"]) for a in applied)
    print("\n      Top shifts:")
    for (o, n), c in shifts.most_common(10):
        print(f"        {c:>3}  {o} → {n}")

    print("\n[4/4] Writing v4 master...", flush=True)
    cols = ["oewn_id", "pos", "dulplus_class", "method", "primary_lemma", "provenance", "gloss"]
    with open(OUT_MASTER, "w", newline="") as f:
        w = csv.DictWriter(f, delimiter="\t", fieldnames=cols)
        w.writeheader()
        for oid in order:
            r = master[oid]
            w.writerow({c: r.get(c, "") for c in cols})
    print(f"      wrote {OUT_MASTER}")

    # Stats
    print("\nSample applied corrections:")
    for a in applied[:10]:
        print(f"  {a['oewn_id']}  {a['lemma']:25s}  {a['old']:25s} → {a['new']}")


if __name__ == "__main__":
    main()
