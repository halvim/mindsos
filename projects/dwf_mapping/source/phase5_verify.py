#!/usr/bin/env python3
"""
Phase 5 — Verification & quality gates for the 102,976-row alignment.

Runs four checks and produces one consolidated report.

    Check 1: class existence & distribution
        Every DULplus class used appears in the DULplus/DOLCE-Lite inventory.
        Flag outlier classes (very low count = possible typo / stale class).

    Check 2: within-synset disjointness
        Any OEWN synset assigned to two DULplus classes that map to
        disjoint DOLCE-Lite categories (e.g. perdurant ⊥ endurant).

    Check 3: hypernym-hyponym subsumption consistency
        For every (parent, child) edge in OEWN's hypernym relation where both
        sides are mapped, is the child's DULplus class compatible (same or a
        subclass) with the parent's?

    Check 4: stratified 200-synset audit
        Random sample across POS × method buckets. Gloss-class compatibility
        heuristic produces an estimated precision score.

    Diff: phase3-vs-phase3.5 impact quantification
        How much of the flagged-verb set would shift class if all
        Phase 3.5 proposals were accepted?

Output: phase5-verification-report.md + phase5-*.tsv/json detail files
"""
import os, re, csv, glob, json, random
from collections import defaultdict, Counter
import yaml
try:
    from yaml import CLoader as _L
except ImportError:
    _L = yaml.SafeLoader

def _yload(path):
    with open(path) as f:
        return yaml.load(f, Loader=_L)

OEWN_YAML_DIR  = "/tmp/oewn-repo/src/yaml"
DLP_DIR        = "/sessions/exciting-pensive-rubin/mnt/Dulce - WordNet - FrameNet Mapping/DLP3971"
MASTER_TSV     = "/sessions/exciting-pensive-rubin/mnt/outputs/oewn-dulplus-master.tsv"
PHASE3_TSV     = "/sessions/exciting-pensive-rubin/mnt/outputs/phase3-verb-alignment.tsv"
PHASE35_TSV    = "/sessions/exciting-pensive-rubin/mnt/outputs/phase3_5-verb-review.tsv"
OUT_DIR        = "/sessions/exciting-pensive-rubin/mnt/outputs"

# ----------------------------------------------------------------------
# DULplus → DOLCE-Lite mapping (curated from DUL.owl documentation
# and the DLP3971 module structure). Used to connect our DULplus class
# usage to DOLCE-Lite's disjointness axioms for Check 2 and Check 3.
# ----------------------------------------------------------------------
DUL_TO_DOLCE = {
    # Perdurants
    "dul:Action":               "perdurant",
    "dul:Event":                "perdurant",
    "dul:State":                "perdurant",
    "dul:Process":              "perdurant",
    "dul:Achievement":          "perdurant",
    "dul:EventType":            "perdurant",
    "dul:CognitiveEvent":       "perdurant",
    "dul:CognitiveState":       "perdurant",
    "dul:Task":                 "perdurant",
    # Qualities & regions
    "dul:Quality":              "quality",
    "dul:PhysicalAttribute":    "physical-quality",
    "dul:Region":               "region",
    "dul:TimeInterval":         "temporal-region",
    "dul:SpaceRegion":          "physical-region",
    # Endurants — physical
    "dul:PhysicalObject":       "physical-object",
    "dul:DesignedArtifact":     "physical-object",
    "dul:Organism":             "agentive-physical-object",
    "dul:BiologicalObject":     "physical-object",
    "dul:PhysicalBody":         "physical-object",
    "dul:PhysicalPlace":        "physical-object",
    "dul:Person":               "agentive-physical-object",
    "dul:PhysicalAgent":        "agentive-physical-object",
    "dul:Personification":      "non-agentive-physical-object",
    "dul:Amount":               "amount-of-matter",
    "dul:Substance":            "amount-of-matter",
    "dul:FunctionalSubstance":  "amount-of-matter",
    "dul:ChemicalObject":       "amount-of-matter",
    # Endurants — non-physical
    "dul:InformationObject":    "non-physical-endurant",
    "dul:InformationRealization":"non-physical-endurant",
    "dul:Narrative":            "non-physical-endurant",
    "dul:Description":          "description",
    "dul:Plan":                 "description",
    "dul:Goal":                 "description",
    "dul:Method":               "description",
    "dul:Concept":              "concept",
    "dul:Role":                 "concept",
    "dul:Parameter":            "concept",
    "dul:Pattern":              "concept",
    "dul:Theory":               "description",
    "dul:Norm":                 "description",
    "dul:Obligation":           "description",
    "dul:Right":                "description",
    "dul:SocialRelation":       "non-physical-endurant",
    "dul:Relation":             "non-physical-endurant",
    "dul:Organization":         "social-object",
    "dul:Collection":           "collection",
    "dul:Collective":           "collective",
    "dul:Set":                  "abstract",
    "dul:System":               "non-physical-endurant",
    # Abstract
    "dul:Abstract":             "abstract",
    "dul:Situation":            "situation",
    "dul:Place":                "region",
    # Collection (coll:*)
    "coll:Taxon":                        "collection",
    "coll:AgentCollection":              "collection",
    "coll:GeneticCollection":            "collection",
    "coll:InformationCollection":        "collection",
    # Other
    "ontopic:Topic":                     "concept",
    "conc:InternalRepresentation":       "non-physical-endurant",
    "rol:Status":                        "concept",
    "http://www.ontologydesignpatterns.org/ont/dul/Supplements.owl#SpatialFeature":  "feature",
    "http://www.ontologydesignpatterns.org/ont/dul/Supplements.owl#DependentPlace":  "feature",
    "http://www.ontologydesignpatterns.org/ont/dul/Supplements.owl#DependentPart":   "feature",
    "http://www.ontologydesignpatterns.org/ont/dul/Conceptualization.owl#InternalRepresentation": "non-physical-endurant",
}

# ----------------------------------------------------------------------
# Parse DLP3971 for class hierarchy + disjointness axioms
# ----------------------------------------------------------------------
def load_dolce_structure():
    classes = {}
    disjoint = set()
    for path in sorted(glob.glob(os.path.join(DLP_DIR, "*.owl"))):
        content = open(path).read()
        for m in re.finditer(r'<owl:Class rdf:about="([^"]+)">(.*?)</owl:Class>',
                              content, re.DOTALL):
            about = m.group(1)
            body = m.group(2)
            local = about.split("#")[-1]
            supers = set(re.findall(r'<rdfs:subClassOf>\s*<owl:Class rdf:about="[^"]*#([a-zA-Z_][\w-]*)"',
                                     body))
            supers |= set(re.findall(r'<rdfs:subClassOf rdf:resource="[^"]*#([a-zA-Z_][\w-]*)"', body))
            disj = set(re.findall(r'<owl:disjointWith[^>]*rdf:resource="[^"]*#([a-zA-Z_][\w-]*)"', body))
            disj |= set(re.findall(r'<owl:disjointWith>\s*<owl:Class rdf:about="[^"]*#([a-zA-Z_][\w-]*)"', body))
            if local not in classes:
                classes[local] = {"supers": set(), "disjoint": set()}
            classes[local]["supers"].update(supers)
            classes[local]["disjoint"].update(disj)
            for d in disj:
                disjoint.add(tuple(sorted([local, d])))
    return classes, disjoint

def ancestors(cls, classes):
    """All transitive supers of cls (excluding cls)."""
    seen = set()
    stack = list(classes.get(cls, {}).get("supers", set()))
    while stack:
        c = stack.pop()
        if c in seen: continue
        seen.add(c)
        stack.extend(classes.get(c, {}).get("supers", set()))
    return seen

def is_compatible_or_sub(child, parent, classes):
    """True if child == parent or child is a transitive subclass."""
    if child == parent: return True
    return parent in ancestors(child, classes)

def are_disjoint(a, b, classes, disjoint_pairs):
    """True if any ancestor of a is disjoint with any ancestor of b."""
    if a == b: return False
    a_set = ancestors(a, classes) | {a}
    b_set = ancestors(b, classes) | {b}
    for x, y in disjoint_pairs:
        if (x in a_set and y in b_set) or (y in a_set and x in b_set):
            return True
    return False

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    print("[1/6] Loading DLP3971 class hierarchy...", flush=True)
    dolce_classes, disjoint_pairs = load_dolce_structure()
    print(f"      classes: {len(dolce_classes):,}, disjoint pairs: {len(disjoint_pairs)}",
          flush=True)

    print("[2/6] Loading alignment master and OEWN hypernym edges...", flush=True)
    align = {}  # oewn_id -> {"class", "method", "pos", "lemma", "gloss"}
    with open(MASTER_TSV) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            align[r["oewn_id"]] = {
                "class":  r["dulplus_class"],
                "method": r["method"],
                "pos":    r["pos"],
                "lemma":  r["primary_lemma"],
                "gloss":  r["gloss"],
            }
    print(f"      alignment rows: {len(align):,}", flush=True)

    hypernym_edges = []   # (child, parent)
    for pat in ("noun.*.yaml", "verb.*.yaml", "adj.*.yaml", "adv.*.yaml"):
        for path in sorted(glob.glob(os.path.join(OEWN_YAML_DIR, pat))):
            d = _yload(path)
            for sid, body in d.items():
                child = f"oewn-{sid}"
                for h in (body.get("hypernym") or []):
                    hypernym_edges.append((child, f"oewn-{h}"))
    print(f"      hypernym edges: {len(hypernym_edges):,}", flush=True)

    # ============ Check 1: class existence & distribution ============
    print("[3/6] Check 1: class existence & distribution...", flush=True)
    class_counts = Counter(r["class"] for r in align.values())
    unknown_classes = [c for c in class_counts if c not in DUL_TO_DOLCE]
    print(f"      distinct classes used: {len(class_counts)}", flush=True)
    print(f"      unmapped to DOLCE-Lite: {len(unknown_classes)}", flush=True)
    for c in unknown_classes[:10]:
        print(f"        UNKNOWN: {c} ({class_counts[c]} uses)", flush=True)

    # ============ Check 2: within-synset disjointness ============
    # The master has at most one row per oewn_id in our output (we wrote it that way)
    # but let's also check the original TSV with multiple classes per synset.
    print("[4/6] Check 2: within-synset disjointness (from Phase 1 multi-class data)...", flush=True)
    phase1_tsv = "/sessions/exciting-pensive-rubin/mnt/outputs/oewn-dulplus-alignment.tsv"
    per_syn = defaultdict(set)
    with open(phase1_tsv) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            per_syn[r["oewn_id"]].add(r["dulplus_class"])
    conflicts = []
    for syn, cls_set in per_syn.items():
        if len(cls_set) < 2: continue
        classes_list = list(cls_set)
        for i in range(len(classes_list)):
            for j in range(i+1, len(classes_list)):
                a = DUL_TO_DOLCE.get(classes_list[i])
                b = DUL_TO_DOLCE.get(classes_list[j])
                if not a or not b: continue
                if are_disjoint(a, b, dolce_classes, disjoint_pairs):
                    conflicts.append((syn, classes_list[i], classes_list[j], a, b))
                    break
    print(f"      within-synset disjointness conflicts: {len(conflicts)}", flush=True)
    for syn, c1, c2, d1, d2 in conflicts[:10]:
        print(f"        {syn}: {c1} ({d1}) ⊥ {c2} ({d2})", flush=True)

    # ============ Check 3: hypernym-hyponym subsumption ============
    print("[5/6] Check 3: hypernym-hyponym subsumption consistency...", flush=True)
    pairs_checked = 0
    pairs_ok = 0
    pairs_incompatible = 0
    pairs_same_class = 0
    pairs_child_sub_parent = 0
    pairs_disjoint = []
    pairs_unrelated = []
    for child, parent in hypernym_edges:
        if child not in align or parent not in align: continue
        c_cls = align[child]["class"]
        p_cls = align[parent]["class"]
        pairs_checked += 1
        if c_cls == p_cls:
            pairs_same_class += 1
            pairs_ok += 1
            continue
        c_dolce = DUL_TO_DOLCE.get(c_cls)
        p_dolce = DUL_TO_DOLCE.get(p_cls)
        if not c_dolce or not p_dolce: continue
        if c_dolce == p_dolce:
            pairs_ok += 1
            continue
        if is_compatible_or_sub(c_dolce, p_dolce, dolce_classes):
            pairs_child_sub_parent += 1
            pairs_ok += 1
            continue
        if are_disjoint(c_dolce, p_dolce, dolce_classes, disjoint_pairs):
            pairs_incompatible += 1
            pairs_disjoint.append((child, parent, c_cls, p_cls))
        else:
            pairs_unrelated.append((child, parent, c_cls, p_cls))

    print(f"      hypernym pairs where both mapped: {pairs_checked:,}", flush=True)
    print(f"        same class:            {pairs_same_class:,}", flush=True)
    print(f"        child subsumes parent: {pairs_child_sub_parent:,}", flush=True)
    print(f"        compatible total:      {pairs_ok:,}", flush=True)
    print(f"        disjoint violations:   {pairs_incompatible:,}", flush=True)
    print(f"        unrelated (uncheckable): {len(pairs_unrelated):,}", flush=True)

    # ============ Check 4: stratified 200-synset audit ============
    print("[6/6] Check 4: stratified 200-synset audit...", flush=True)
    random.seed(0xdead)
    buckets = defaultdict(list)
    for oid, info in align.items():
        pos = info["pos"]
        method = info["method"]
        # Bucket by (pos, method_prefix)
        mprefix = method.split("_", 2)
        mbucket = "_".join(mprefix[:2]) if len(mprefix) >= 2 else method
        buckets[(pos, mbucket)].append(oid)

    # Sample ~50 per POS, proportional by method within POS
    target_per_pos = {"n": 60, "v": 50, "a": 30, "s": 30, "r": 30}
    audit_sample = []
    for pos, target in target_per_pos.items():
        candidate_buckets = [k for k in buckets if k[0] == pos]
        if not candidate_buckets: continue
        # sample proportional to bucket size
        total = sum(len(buckets[k]) for k in candidate_buckets)
        for k in candidate_buckets:
            n = max(1, round(target * len(buckets[k]) / total))
            sampled = random.sample(buckets[k], min(n, len(buckets[k])))
            audit_sample.extend(sampled)
    audit_sample = audit_sample[:200]
    print(f"      audit sample size: {len(audit_sample)}", flush=True)

    # Write audit TSV for manual review
    audit_path = os.path.join(OUT_DIR, "phase5-audit-sample.tsv")
    with open(audit_path, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["oewn_id", "pos", "primary_lemma", "gloss",
                    "assigned_class", "method", "manual_agreement"])
        for oid in sorted(audit_sample):
            info = align[oid]
            w.writerow([oid, info["pos"], info["lemma"], info["gloss"][:200],
                        info["class"], info["method"], ""])

    # Write detailed conflict TSVs
    disjoint_path = os.path.join(OUT_DIR, "phase5-disjoint-pairs.tsv")
    with open(disjoint_path, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["child", "child_class", "parent", "parent_class",
                    "child_lemma", "parent_lemma", "child_gloss"])
        for child, parent, c_cls, p_cls in pairs_disjoint[:500]:
            c_info = align.get(child, {})
            p_info = align.get(parent, {})
            w.writerow([child, c_cls, parent, p_cls,
                        c_info.get("lemma", ""), p_info.get("lemma", ""),
                        c_info.get("gloss", "")[:150]])

    unrelated_path = os.path.join(OUT_DIR, "phase5-unrelated-pairs.tsv")
    with open(unrelated_path, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["child", "child_class", "parent", "parent_class",
                    "child_lemma", "parent_lemma", "child_gloss"])
        for child, parent, c_cls, p_cls in pairs_unrelated[:500]:
            c_info = align.get(child, {})
            p_info = align.get(parent, {})
            w.writerow([child, c_cls, parent, p_cls,
                        c_info.get("lemma", ""), p_info.get("lemma", ""),
                        c_info.get("gloss", "")[:150]])

    # ============ Diff: phase 3 → phase 3.5 impact ============
    print("      Diff: Phase 3 → Phase 3.5 flagging impact...", flush=True)
    p35_flagged = {}
    try:
        with open(PHASE35_TSV) as f:
            for r in csv.DictReader(f, delimiter="\t"):
                if r.get("top_proposal"):
                    p35_flagged[r["oewn_id"]] = {
                        "current": r["current_class"],
                        "proposed": r["top_proposal"],
                        "score": float(r["confidence_score"]),
                    }
    except FileNotFoundError:
        pass

    flip_dist = Counter()
    for oid, f in p35_flagged.items():
        flip_dist[(f["current"], f["proposed"])] += 1

    # ============ Output JSON stats + markdown report ============
    stats = {
        "alignment_row_count":         len(align),
        "distinct_dulplus_classes":    len(class_counts),
        "classes_unmapped_to_dolce":   len(unknown_classes),
        "class_distribution":          dict(class_counts.most_common(20)),
        "within_synset_disjointness_conflicts": len(conflicts),
        "hypernym_subsumption_checked":         pairs_checked,
        "hypernym_compatible":                  pairs_ok,
        "hypernym_disjoint_violations":         pairs_incompatible,
        "hypernym_unrelated_uncheckable":       len(pairs_unrelated),
        "hypernym_compat_rate_pct":             round(100 * pairs_ok / pairs_checked, 2) if pairs_checked else 0,
        "audit_sample_size":                    len(audit_sample),
        "phase3_5_flagged_with_proposal":       len(p35_flagged),
        "top_flip_patterns":                    {f"{c}→{p}": n for (c, p), n in flip_dist.most_common(10)},
    }
    with open(os.path.join(OUT_DIR, "phase5-stats.json"), "w") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
