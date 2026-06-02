#!/usr/bin/env python3
"""
Phase 2 — Revalidate OntoWordNet's top-mapping synsets against OEWN 2025,
applying rule-based flags inspired by Gangemi et al. 2003 and Silva et al. 2018.

Input:
    oewn-dulplus-alignment.tsv  (Phase 1 output)
    OEWN YAML (for full synset metadata — members, gloss, hypernym)

Output:
    phase2-topmapping-review.tsv   one row per topmapping synset
        columns: oewn_id, pos, primary_lemma, all_lemmas, gloss, hypernyms,
                 current_dul_class, flag, proposed_class, rationale, decision

Flags:
    - "ok"                       no issue detected
    - "role_lemma"               lemma pattern suggests anti-rigid role; check rigidity
    - "individual_candidate"     lemma is a proper name (mixes instance w/ class — Gangemi R1)
    - "metalevel"                lemma mentions attribute/relation/property — Gangemi R4
    - "perdurant_gloss"          gloss starts with 'the act/state/process of' — Silva 2018
    - "role_subsumes_type"       a role-named child dominates a rigid-type parent
    - "class_singleton"          DUL class only assigned to 1 synset in the whole mapping — suspect
    - "full_iri_class"           class was emitted as a full IRI, worth reviewing
"""

import os, re, sys, csv, glob, json
from collections import defaultdict, Counter
import yaml
try:
    from yaml import CLoader as _L
except ImportError:
    _L = yaml.SafeLoader

OEWN_YAML_DIR = "/tmp/oewn-repo/src/yaml"
ALIGN_TSV     = "/sessions/exciting-pensive-rubin/mnt/outputs/oewn-dulplus-alignment.tsv"
OUT_DIR       = "/sessions/exciting-pensive-rubin/mnt/outputs"
OUT_TSV       = os.path.join(OUT_DIR, "phase2-topmapping-review.tsv")
OUT_STATS     = os.path.join(OUT_DIR, "phase2-stats.json")

def _yload(path):
    with open(path) as f:
        return yaml.load(f, Loader=_L)

# ---- Gangemi 2003 / Silva 2018 rule helpers ----

# Suffixes typical of role-like nominalisations (per Gangemi's R3: roles are anti-rigid)
ROLE_LEMMA_PATTERNS = [
    re.compile(r'.+(er|or|ist|ian|eer|ant|ent)$'),   # worker, doctor, artist, musician, engineer, servant
    re.compile(r'.+(ee)$'),                           # employee, trainee
    re.compile(r'^[a-z].* (of|to) .*$'),              # descriptive roles
]

# Lemmas whose glosses look metalevel (R4)
METALEVEL_LEMMA = {"attribute", "relation", "property", "predicate", "concept"}

# Gloss markers for perdurants per Silva 2018 §4 (Tier 1 direct-link heuristics)
PERDURANT_MARKERS = {
    "the act of":       "dul:Action",
    "the process of":   "dul:Process",
    "the state of":     "dul:State",
    "the activity of":  "dul:Action",
    "the event of":     "dul:Event",
    "the occurrence of": "dul:Event",
}

# Known DOLCE-Lite / DULplus disjoint pairs — if gloss suggests one class but current maps
# to a disjoint class, flag. (Minimal set; Phase 6 reasoner pass will catch the rest.)
DISJOINT_PAIRS = [
    ({"dul:Organism", "dul:BiologicalObject", "dul:DesignedArtifact"}, "dul:Action"),
    ({"dul:Person", "dul:Organism"}, {"dul:Quality", "dul:Amount"}),
]

# Common "individual" markers in glosses (proper nouns, specific references)
INDIVIDUAL_MARKERS = re.compile(
    r'\b(the first|the second|the third|the [A-Z]|named after|was born|founded by|located in)\b'
)


def load_oewn_synsets():
    files = []
    for pat in ("noun.*.yaml", "verb.*.yaml", "adj.*.yaml", "adv.*.yaml"):
        files += sorted(glob.glob(os.path.join(OEWN_YAML_DIR, pat)))
    synsets = {}
    for path in files:
        d = _yload(path)
        for sid, body in d.items():
            oewn_id = f"oewn-{sid}"
            synsets[oewn_id] = {
                "pos":        body.get("partOfSpeech") or sid.rsplit('-', 1)[-1],
                "ili":        body.get("ili"),
                "members":    body.get("members") or [],
                "definition": (body.get("definition") or [""])[0] if body.get("definition") else "",
                "hypernym":   body.get("hypernym") or [],
            }
    return synsets


def is_role_lemma(lemma: str) -> bool:
    if not lemma: return False
    ll = lemma.lower()
    # Very short words and common rigid types shouldn't trip the -er/-or rule
    if len(ll) <= 4: return False
    for p in ROLE_LEMMA_PATTERNS:
        if p.match(ll):
            # Extra guard: many rigid types end in -er too (beaver, river, officer...).
            # Don't flag if the current DUL class is already "Person" or a concrete artifact —
            # that's explicit role acknowledgement already.
            return True
    return False


def detect_perdurant(gloss: str):
    g = gloss.lower().strip()
    for marker, proposed in PERDURANT_MARKERS.items():
        if g.startswith(marker):
            return proposed, marker
    return None, None


def flag_row(oewn_id, meta, current_cls, class_counter, current_class_classes):
    """Return (flag, proposed_class, rationale). flag='ok' means no action needed."""
    if not meta:
        return "no_oewn_metadata", "", "OEWN synset not found — likely deprecated since Framester build"

    lemmas = meta.get("members") or []
    primary = lemmas[0] if lemmas else ""
    gloss   = (meta.get("definition") or "").strip()

    # 1) Metalevel (R4)
    if primary.lower() in METALEVEL_LEMMA:
        return ("metalevel", "dul:Concept",
                f"lemma '{primary}' is metalevel; Gangemi 2003 R4 excludes metalevel from object-level hierarchy")

    # 2) Perdurant gloss markers (Silva 2018 Tier 3)
    prop, marker = detect_perdurant(gloss)
    if prop and prop != current_cls:
        # If the current class is itself a perdurant subtype, don't flag
        perdurant_family = {"dul:Action", "dul:Process", "dul:State", "dul:Event",
                             "dul:EventType", "dul:Activity", "dul:Situation"}
        if current_cls not in perdurant_family:
            return ("perdurant_gloss", prop,
                    f"gloss opens with '{marker}' — Silva 2018 marker for perdurant; current class is {current_cls}")

    # 3) Full-IRI class — review whether it's stable
    if current_cls.startswith("http"):
        return ("full_iri_class", current_cls,
                "current class is a full IRI (not a prefix); confirm the class belongs in DULplus namespace")

    # 4) Class used only once — suspect outlier mapping
    if class_counter.get(current_cls, 0) <= 1:
        return ("class_singleton", "",
                f"class {current_cls} is assigned to only {class_counter.get(current_cls, 0)} synsets — "
                "may be a stale/experimental target class")

    # 5) Role lemma on a non-role class — possible rigidity violation (Gangemi R3)
    role_safe_classes = {"dul:Person", "dul:SocialAgent", "rol:Status", "rol:Role"}
    if is_role_lemma(primary) and current_cls not in role_safe_classes:
        if current_cls in {"dul:Organism", "dul:BiologicalObject",
                            "dul:DesignedArtifact", "dul:PhysicalObject"}:
            return ("role_lemma", "dul:Person/rol:Role",
                    f"lemma '{primary}' pattern suggests role (anti-rigid); current class {current_cls} is rigid")

    # 6) Individual candidates (Gangemi R1): lemmas that are capitalised proper nouns + gloss markers
    if primary and primary[0].isupper() and any(m in gloss.lower() for m in
                                                  ["capital of", "king of", "founded", "named after"]):
        return ("individual_candidate", "",
                f"lemma '{primary}' + gloss suggest a specific individual rather than a concept (Gangemi R1)")

    return ("ok", "", "")


def main():
    print("[1/3] Loading OEWN synset metadata...", flush=True)
    synsets = load_oewn_synsets()
    print(f"      loaded {len(synsets):,} OEWN synsets", flush=True)

    print("[2/3] Loading Phase 1 alignment and filtering to topmapping layer...", flush=True)
    rows = []
    class_counter = Counter()
    with open(ALIGN_TSV) as f:
        r = csv.DictReader(f, delimiter="\t")
        for rec in r:
            class_counter[rec["dulplus_class"]] += 1
            rows.append(rec)

    topmap_rows = [r for r in rows if r["source"] == "topmapping"]
    print(f"      total alignment rows: {len(rows):,}", flush=True)
    print(f"      topmapping rows:      {len(topmap_rows):,}", flush=True)

    # Per-synset: collect all classes assigned (some get multiple)
    classes_by_synset = defaultdict(set)
    for r in rows:
        classes_by_synset[r["oewn_id"]].add(r["dulplus_class"])

    print("[3/3] Flagging topmapping rows...", flush=True)
    flagged = []
    flag_counter = Counter()
    for rec in topmap_rows:
        oewn_id = rec["oewn_id"]
        current_cls = rec["dulplus_class"]
        meta = synsets.get(oewn_id, {})
        flag, proposed, rationale = flag_row(oewn_id, meta, current_cls, class_counter,
                                              classes_by_synset.get(oewn_id, set()))
        flag_counter[flag] += 1
        flagged.append({
            "oewn_id":            oewn_id,
            "pos":                meta.get("pos", rec.get("pos", "")),
            "primary_lemma":      (meta.get("members") or [""])[0] if meta else rec.get("primary_lemma", ""),
            "all_lemmas":         "|".join(meta.get("members") or []),
            "gloss":              meta.get("definition", rec.get("definition", ""))[:300],
            "hypernyms":          ",".join(meta.get("hypernym") or []),
            "current_dul_class":  current_cls,
            "flag":               flag,
            "proposed_class":     proposed,
            "rationale":          rationale,
            "decision":           "",   # user fills in
        })

    # Write TSV
    with open(OUT_TSV, "w") as f:
        w = csv.DictWriter(f, delimiter="\t", fieldnames=[
            "oewn_id", "pos", "primary_lemma", "all_lemmas", "gloss", "hypernyms",
            "current_dul_class", "flag", "proposed_class", "rationale", "decision",
        ])
        w.writeheader()
        # sort: non-ok flags first, then alphabetical
        def _sortkey(r):
            return (0 if r["flag"] != "ok" else 1, r["flag"], r["primary_lemma"])
        for row in sorted(flagged, key=_sortkey):
            w.writerow(row)
    print(f"      wrote {OUT_TSV}", flush=True)

    # Stats
    stats = {
        "topmapping_rows_reviewed": len(flagged),
        "flag_distribution":        dict(flag_counter),
        "ok_rate_percent":          round(100 * flag_counter["ok"] / len(flagged), 2),
    }
    with open(OUT_STATS, "w") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
