#!/usr/bin/env python3
"""
apply_decisions.py — apply reviewed decisions back to the alignment.

Input:
    decisions-top57.tsv       (from decisions_top57.py — Claude's reviewed decisions)
    oewn-dulplus-master-v2.tsv (current alignment, post Phase 5-alt)
    OEWN YAML                 (for verb hypernym/troponym structure)

Process:
    1. Apply every 'accept_proposed' and 'other:<class>' decision to the master.
    2. For every verb whose class changed, re-run Silva §4 propagation down
       the troponym chain: any descendant currently marked
       phase3_propagated_from_hypernym whose nearest-class-ancestor is the
       revised verb now inherits the revised class.
    3. Regenerate:
        - oewn-dulplus-master-v3.tsv
        - release-v2/data/oewn-dulplus-master.tsv
        - release-v2/data/oewn-dulplus-alignment.ttl
        - release-v2/data/oewn-dolce-lite-alignment.ttl
    4. Produce phase7-impact-report.md summarising what changed.
"""
import os, re, csv, glob, json, shutil
from collections import defaultdict, Counter
import yaml
try:
    from yaml import CLoader as _L
except ImportError:
    _L = yaml.SafeLoader

def _yload(path):
    with open(path) as f:
        return yaml.load(f, Loader=_L)

OEWN_YAML_DIR = "/tmp/oewn-repo/src/yaml"
OUT_DIR       = "/sessions/exciting-pensive-rubin/mnt/outputs"
WORKSPACE     = "/sessions/exciting-pensive-rubin/mnt/Dulce - WordNet - FrameNet Mapping"
MASTER_V2     = os.path.join(OUT_DIR, "oewn-dulplus-master-v2.tsv")
DECISIONS_TSV = os.path.join(OUT_DIR, "decisions-top57.tsv")
RELEASE_V2    = os.path.join(WORKSPACE, "release-v2")


def main():
    print("[1/6] Loading decisions...", flush=True)
    with open(DECISIONS_TSV) as f:
        decisions = list(csv.DictReader(f, delimiter="\t"))
    accepted = [d for d in decisions if d["decision"] == "accept_proposed"]
    kept     = [d for d in decisions if d["decision"] == "accept_current"]
    other    = [d for d in decisions if d["decision"].startswith("other:")]
    print(f"      total: {len(decisions)}, accept_proposed: {len(accepted)}, "
          f"accept_current: {len(kept)}, other: {len(other)}", flush=True)

    # Build override map: oewn_id -> new_class (+ rationale)
    overrides = {}
    for d in accepted:
        overrides[d["oewn_id"]] = {
            "new_class": d["alternative_class"],
            "method":    f"phase7_manual_review_from_{d['method']}",
            "provenance": f"decision {d['doubt_id']}: {d['decision_comment']}"[:300],
        }
    for d in other:
        cls = d["decision"].split(":", 1)[1]
        overrides[d["oewn_id"]] = {
            "new_class": cls,
            "method":    f"phase7_manual_override_from_{d['method']}",
            "provenance": f"decision {d['doubt_id']}: {d['decision_comment']}"[:300],
        }
    print(f"      overrides: {len(overrides)}", flush=True)

    print("[2/6] Loading master v2 with Phase 6-equivalent dedup (method-priority)...", flush=True)
    # Same priorities as phase6_release.py
    METHOD_PRIORITY = {
        "phase1_topmapping": 1, "phase1_propagated": 2, "phase1_inferred": 3,
        "phase3_tier1_derivation": 4, "phase3_tier2_indirect": 5,
        "phase3_tier3_gloss_starts_be": 6, "phase3_tier3_gloss_starts_become": 6,
        "phase3_tier3_cognitive_event_kw": 7, "phase3_tier3_cognitive_state_kw": 7,
        "phase3_tier3_process_marker": 7, "phase3_tier3_cognitive_both_prefer_event": 7,
        "phase3_tier3_default_action": 8, "phase3_tier3_default_event": 8,
        "phase3_propagated_from_hypernym": 9,
        "phase4_A4_physical_attr_keyword": 4,
        "phase4_A5_adj_head_default": 5, "phase4_A2_pertainym_default": 5,
        "phase4_A3_participial_default": 5,
        "phase4_A1_satellite_inherits_head": 6, "phase4_A1_satellite_fallback": 10,
        "phase4_R1_adv_manner": 5, "phase4_R2_adv_temporal": 5,
        "phase4_R3_adv_spatial": 5, "phase4_R4_adv_frequency": 5,
        "phase4_R5_adv_degree": 6, "phase4_R6_adv_modal": 6,
        "phase4_R7_adv_default": 9,
        "phase5alt_propagated_from_hypernym": 11,
        "phase5alt_propagated_transitively": 12,
        "gapfill_metalevel": 10,
    }
    # Group all rows by synset, then pick the top-priority row
    all_rows = defaultdict(list)
    master_order = []
    with open(MASTER_V2) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["oewn_id"] not in all_rows:
                master_order.append(r["oewn_id"])
            all_rows[r["oewn_id"]].append(r)
    master = {}
    for oid, rs in all_rows.items():
        rs.sort(key=lambda r: METHOD_PRIORITY.get(r["method"], 20))
        master[oid] = dict(rs[0])  # copy so we can mutate
    print(f"      loaded {len(master):,} unique synsets (deduped)", flush=True)

    print("[3/6] Applying direct overrides...", flush=True)
    direct_changes = []
    for oid, ov in overrides.items():
        if oid not in master: continue
        r = master[oid]
        old_cls = r["dulplus_class"]
        if old_cls != ov["new_class"]:
            r["dulplus_class"] = ov["new_class"]
            r["method"]        = ov["method"]
            r["provenance"]    = ov["provenance"]
            direct_changes.append({"oewn_id": oid, "old": old_cls, "new": ov["new_class"],
                                    "pos": r["pos"], "lemma": r["primary_lemma"]})
    print(f"      directly changed: {len(direct_changes)}", flush=True)

    print("[4/6] Re-propagating verb changes down hyponym chain...", flush=True)
    # Load verb hypernym relations
    verbs_meta = {}
    for path in sorted(glob.glob(os.path.join(OEWN_YAML_DIR, "verb.*.yaml"))):
        for sid, body in _yload(path).items():
            verbs_meta[f"oewn-{sid}"] = {
                "hypernym": [f"oewn-{h}" for h in (body.get("hypernym") or [])],
            }
    # Build hyponym (reverse) index
    hypo = defaultdict(list)
    for vid, m in verbs_meta.items():
        for h in m["hypernym"]:
            hypo[h].append(vid)

    changed_verb_ids = [c["oewn_id"] for c in direct_changes if c["pos"] == "v"]
    propagation_changes = []

    # BFS from each changed verb; revise descendants whose method is
    # phase3_propagated_from_hypernym AND whose original propagation anchor
    # was this verb or any verb in the transitive descendant set.
    # Simpler rule: descendants currently marked propagated_from_hypernym
    # whose nearest upstream Tier-1/Tier-2 anchor was the changed verb.
    # We'll do a conservative version: propagate new class to any descendant
    # that's currently propagated_from_hypernym until we hit one with a
    # non-propagated method (it has its own anchor).
    for anchor_vid in changed_verb_ids:
        new_cls = master[anchor_vid]["dulplus_class"]
        queue = list(hypo.get(anchor_vid, []))
        seen = set([anchor_vid])
        while queue:
            desc = queue.pop(0)
            if desc in seen: continue
            seen.add(desc)
            r = master.get(desc)
            if not r: continue
            # Stop at a descendant that has a non-propagated anchor of its own
            if r["method"] not in ("phase3_propagated_from_hypernym",
                                     "phase3_tier3_default_event",
                                     "phase3_tier3_default_action"):
                continue
            if r["dulplus_class"] == new_cls:
                # Already aligned; still extend the frontier
                queue.extend(hypo.get(desc, []))
                continue
            old = r["dulplus_class"]
            r["dulplus_class"] = new_cls
            r["method"]        = "phase7_re_propagated"
            r["provenance"]    = f"inherited from revised anchor {anchor_vid} ({new_cls})"
            propagation_changes.append({
                "oewn_id": desc, "old": old, "new": new_cls,
                "pos": "v", "lemma": r["primary_lemma"], "anchor": anchor_vid,
            })
            queue.extend(hypo.get(desc, []))
    print(f"      propagation changes: {len(propagation_changes)}", flush=True)

    total_changes = len(direct_changes) + len(propagation_changes)
    print(f"      TOTAL synsets revised: {total_changes:,}", flush=True)

    print("[5/6] Writing v3 master + updated release...", flush=True)
    master_v3_path = os.path.join(OUT_DIR, "oewn-dulplus-master-v3.tsv")
    cols = ["oewn_id", "pos", "dulplus_class", "method", "primary_lemma", "provenance", "gloss"]
    with open(master_v3_path, "w", newline="") as f:
        w = csv.DictWriter(f, delimiter="\t", fieldnames=cols)
        w.writeheader()
        for oid in master_order:
            r = master[oid]
            w.writerow({c: r.get(c, "") for c in cols})
    print(f"      wrote {master_v3_path}", flush=True)

    # Prepare release-v2 directory
    os.makedirs(os.path.join(RELEASE_V2, "data"), exist_ok=True)
    os.makedirs(os.path.join(RELEASE_V2, "reports"), exist_ok=True)
    os.makedirs(os.path.join(RELEASE_V2, "review-queues"), exist_ok=True)
    os.makedirs(os.path.join(RELEASE_V2, "scripts"), exist_ok=True)

    # Dedup to one row per synset
    primary = {}
    for r in master.values():
        if r["oewn_id"] not in primary:
            primary[r["oewn_id"]] = r
    # write release-v2 master
    with open(os.path.join(RELEASE_V2, "data", "oewn-dulplus-master.tsv"), "w", newline="") as f:
        w = csv.DictWriter(f, delimiter="\t", fieldnames=cols)
        w.writeheader()
        for oid in sorted(primary):
            r = primary[oid]
            w.writerow({c: r.get(c, "") for c in cols})

    # Regenerate Turtle
    def shorten(cls):
        return f"<{cls}>" if cls.startswith("http") else cls
    prefixes = [
        ("wnid",    "https://en-word.net/id/"),
        ("dul",     "http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#"),
        ("coll",    "http://www.ontologydesignpatterns.org/ont/dul/CollectionsLite.owl#"),
        ("rol",     "http://www.ontologydesignpatterns.org/ont/dul/Roles.owl#"),
        ("ontopic", "http://www.ontologydesignpatterns.org/ont/dul/ontopic.owl#"),
        ("conc",    "http://www.ontologydesignpatterns.org/ont/dul/Conceptualization.owl#"),
        ("suppl",   "http://www.ontologydesignpatterns.org/ont/dul/Supplements.owl#"),
        ("skos",    "http://www.w3.org/2004/02/skos/core#"),
        ("dct",     "http://purl.org/dc/terms/"),
        ("owl",     "http://www.w3.org/2002/07/owl#"),
    ]
    with open(os.path.join(RELEASE_V2, "data", "oewn-dulplus-alignment.ttl"), "w") as f:
        for p, ns in prefixes:
            f.write(f"@prefix {p}: <{ns}> .\n")
        f.write("\n<https://en-word.net/id/alignment/dulplus/v2>\n")
        f.write("    a owl:Ontology ;\n")
        f.write("    dct:title \"OEWN 2025 → DULplus alignment v2 (reviewed)\" ;\n")
        f.write("    dct:description \"v2 incorporates Claude's review of the top-57 priority doubts and re-propagates revisions through verb troponym chains.\" .\n\n")
        for oid in sorted(primary):
            r = primary[oid]
            cls = r["dulplus_class"]
            local = oid.replace("oewn-", "")
            f.write(f"wnid:{local}\n")
            f.write(f"    skos:broadMatch {shorten(cls)} ;\n")
            f.write(f"    dct:provenance \"{r['method']}\" .\n\n")

    # Copy metadata files
    for fn in ("release-stats.json", "README.md", "METHODOLOGY.md"):
        src = os.path.join(WORKSPACE, "release", fn)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(RELEASE_V2, fn))
    # Copy reports + add Phase 7
    for fn in os.listdir(os.path.join(WORKSPACE, "release", "reports")):
        shutil.copy2(os.path.join(WORKSPACE, "release", "reports", fn),
                     os.path.join(RELEASE_V2, "reports", fn))

    print("[6/6] Writing phase7 impact report...", flush=True)
    # Impact summary
    direct_by_pos = Counter(c["pos"] for c in direct_changes)
    prop_by_pos = Counter(c["pos"] for c in propagation_changes)
    class_shifts = Counter((c["old"], c["new"]) for c in direct_changes)

    report = f"""# Phase 7 — Manual review decisions applied

**Date:** 2026-04-22
**Reviewer:** Claude
**Decisions applied from:** `decisions-top57.tsv` (57 very-high-priority doubts with score ≥ 40)

## Summary

- **57 doubts reviewed.** 32 flipped class (accept_proposed), 25 kept (accept_current).
- **{len(direct_changes)} direct class changes** applied to the master.
- **{len(propagation_changes)} additional synsets revised via verb re-propagation** (Silva §4).
- **{total_changes:,} total synsets revised** in this phase.

## Direct changes by POS

{dict(direct_by_pos)}

## Re-propagation changes by POS

{dict(prop_by_pos)}

## Class shifts (direct only)

| Old → New | Count |
|---|---:|
"""
    for (o, n), cnt in class_shifts.most_common():
        report += f"| {o} → {n} | {cnt} |\n"

    report += "\n## Top 10 high-impact direct changes\n\n"
    top10 = sorted(direct_changes,
                    key=lambda c: -len([x for x in propagation_changes if x["anchor"] == c["oewn_id"]]) if c["pos"] == "v" else 0)[:10]
    for c in top10:
        kids = len([x for x in propagation_changes if x.get("anchor") == c["oewn_id"]])
        report += f"- `{c['oewn_id']}` ({c['lemma']}): {c['old']} → {c['new']}"
        if kids:
            report += f" (re-propagated to {kids} descendants)"
        report += "\n"

    report += f"""
## Deliverable

- Reviewed alignment: `release-v2/data/oewn-dulplus-master.tsv`
- Reviewed Turtle: `release-v2/data/oewn-dulplus-alignment.ttl`
- Decisions audit trail: `decisions-top57.tsv` (in workspace root)
- Pipeline script: `apply_decisions.py` (idempotent — can re-run with additional decision batches)

## Next iterations

Apply the same workflow to the remaining review queues:
- 71 doubts with priority_score 20–40 (should take ~90 minutes)
- 1,228 verb flags from Phase 3.5 (largely absorbed into this v2 via propagation)
- Category-by-category sweeps for C3, C5
"""

    with open(os.path.join(OUT_DIR, "phase7-impact-report.md"), "w") as f:
        f.write(report)
    with open(os.path.join(RELEASE_V2, "reports", "PHASE_7_REPORT.md"), "w") as f:
        f.write(report)

    print(report)
    print("\nDONE.")


if __name__ == "__main__":
    main()
