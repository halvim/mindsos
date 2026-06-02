#!/usr/bin/env python3
"""
Phase 9c — Cognitive verb re-seeding.

Silva 2018 mapped 854 verbs to dul:CognitiveEvent and 20 to dul:CognitiveState.
Our Phase 3 keyword-detection only caught 24 in total. Root cause: conservative
keyword matching. Fix: OEWN's verb.cognition.yaml lexical file BY DEFINITION
contains all cognitive verbs; seed every synset there as cognitive perdurant,
distinguishing state vs event by Silva's stative-gloss test.

Strategy:
    1. Load all synsets from verb.cognition.yaml → these are cognitive by definition.
    2. For each: determine sub-class.
        dul:CognitiveState ← gloss opens "be X", or stative markers
                             (know, believe, hold, trust, doubt, understand, consider)
        dul:CognitiveEvent ← everything else (aligns with Silva's 854:20 ratio)
    3. Apply as overrides; re-propagate down through troponyms.
    4. Write master-v3c.tsv + stats.
"""
import os, re, csv, glob
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
V3_MASTER     = os.path.join(WORKSPACE, "release-v3", "data", "oewn-dulplus-master.tsv")
OUT_MASTER    = os.path.join(OUT_DIR, "oewn-dulplus-master-v3c.tsv")

STATIVE_GLOSS = re.compile(r'^\s*be\b', re.I)
STATIVE_VERBS = re.compile(
    r'\b(know|believe|think|consider|understand|comprehend|hold\s+(that|the)|'
    r'trust|doubt|suspect|assume|presume|imagine|figure|reckon|deem)\b', re.I)

def main():
    print("[1/5] Loading OEWN cognitive verb synsets...", flush=True)
    cognitive = _yload(os.path.join(OEWN_YAML_DIR, "verb.cognition.yaml"))
    print(f"      cognitive verb synsets (from verb.cognition.yaml): {len(cognitive):,}", flush=True)

    # Classify each cognitive synset
    sub_map = {}
    for sid, body in cognitive.items():
        oid = f"oewn-{sid}"
        gloss = (body.get("definition") or [""])[0] if body.get("definition") else ""
        if STATIVE_GLOSS.match(gloss) or STATIVE_VERBS.search(gloss):
            sub_map[oid] = ("dul:CognitiveState", "stative gloss pattern")
        else:
            sub_map[oid] = ("dul:CognitiveEvent", "default cognitive perdurant")
    event_n = sum(1 for v, _ in sub_map.values() if v == "dul:CognitiveEvent")
    state_n = sum(1 for v, _ in sub_map.values() if v == "dul:CognitiveState")
    print(f"      classified: {event_n} CognitiveEvent + {state_n} CognitiveState", flush=True)

    # Also load OEWN's hyponym index for verbs to propagate down
    all_verbs = {}
    for path in sorted(glob.glob(os.path.join(OEWN_YAML_DIR, "verb.*.yaml"))):
        for sid, body in _yload(path).items():
            all_verbs[f"oewn-{sid}"] = {
                "hypernym": [f"oewn-{h}" for h in (body.get("hypernym") or [])],
            }
    hypo = defaultdict(list)
    for vid, m in all_verbs.items():
        for h in m["hypernym"]:
            hypo[h].append(vid)

    print("[2/5] Loading current master (v3)...", flush=True)
    master = {}
    order = []
    with open(V3_MASTER) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            master[r["oewn_id"]] = r
            order.append(r["oewn_id"])
    print(f"      loaded {len(master):,} synsets", flush=True)

    print("[3/5] Applying cognitive overrides...", flush=True)
    direct_changes = []
    for oid, (new_cls, rationale) in sub_map.items():
        if oid not in master: continue
        r = master[oid]
        if r["dulplus_class"] != new_cls:
            direct_changes.append({"oewn_id": oid, "old": r["dulplus_class"], "new": new_cls,
                                     "lemma": r["primary_lemma"]})
            r["dulplus_class"] = new_cls
            r["method"]        = "phase9c_cognitive_reseed"
            r["provenance"]    = f"verb.cognition.yaml + {rationale}"
    print(f"      direct changes: {len(direct_changes):,}", flush=True)

    print("[4/5] Propagating down through verb troponyms...", flush=True)
    propagation_changes = []
    # For each cognitive anchor, walk descendants; update if currently propagated_from_hypernym
    ACCEPTABLE_METHOD_FOR_OVERRIDE = {
        "phase3_propagated_from_hypernym",
        "phase3_tier3_default_event",
        "phase3_tier3_default_action",
        "phase7_re_propagated",
        "phase8_re_propagated",
        "phase8_systematic_review_from_phase3_propagated_from_hypernym",
        "phase8_systematic_review_from_phase3_tier3_default_event",
        "phase8_systematic_review_from_phase3_tier3_default_action",
    }
    for anchor_vid, (new_cls, _) in sub_map.items():
        if anchor_vid not in master: continue
        queue = list(hypo.get(anchor_vid, []))
        seen = set([anchor_vid])
        while queue:
            desc = queue.pop(0)
            if desc in seen: continue
            seen.add(desc)
            r = master.get(desc)
            if not r: continue
            if r["method"] not in ACCEPTABLE_METHOD_FOR_OVERRIDE:
                continue
            if r["dulplus_class"] == new_cls:
                queue.extend(hypo.get(desc, []))
                continue
            old = r["dulplus_class"]
            r["dulplus_class"] = new_cls
            r["method"]        = "phase9c_re_propagated_cognitive"
            r["provenance"]    = f"inherited from cognitive anchor {anchor_vid}"
            propagation_changes.append({"oewn_id": desc, "old": old, "new": new_cls,
                                          "lemma": r["primary_lemma"]})
            queue.extend(hypo.get(desc, []))
    print(f"      propagation changes: {len(propagation_changes):,}", flush=True)

    print("[5/5] Writing master-v3c.tsv...", flush=True)
    cols = ["oewn_id", "pos", "dulplus_class", "method", "primary_lemma", "provenance", "gloss"]
    with open(OUT_MASTER, "w", newline="") as f:
        w = csv.DictWriter(f, delimiter="\t", fieldnames=cols)
        w.writeheader()
        for oid in order:
            r = master[oid]
            w.writerow({c: r.get(c, "") for c in cols})
    total = len(direct_changes) + len(propagation_changes)
    print(f"\n=== Phase 9c summary ===")
    print(f"  direct cognitive reseeding:         {len(direct_changes):,}")
    print(f"  downstream troponym re-propagation: {len(propagation_changes):,}")
    print(f"  total synsets revised:              {total:,}")

    # Show sample
    print("\nSample direct changes (first 10):")
    for c in direct_changes[:10]:
        print(f"  {c['oewn_id']}  {c['lemma']:25s}  {c['old']}  →  {c['new']}")


if __name__ == "__main__":
    main()
