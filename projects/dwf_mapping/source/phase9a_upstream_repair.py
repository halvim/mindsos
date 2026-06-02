#!/usr/bin/env python3
"""
Phase 9a — Upstream consistency repair.

v3's Phase 5 verification found 1,205 hypernym-hyponym disjoint violations,
up from v1's 516. The increase reflects Phase 8 corrections propagating
DOWNWARD from anchor verbs but not UPWARD to ancestors. This phase walks
each violation pair and, where the child was corrected to a Silva/Gangemi-
supported class and the parent is still on a weak-evidence method,
propagates the child's class upward until a Tier-1 anchor is hit or a
fixed point is reached.

Strategy:
    1. Load v3c master (after Phase 9c cognitive re-seeding).
    2. Load hypernym graph.
    3. For each (child, parent) pair where their DULplus classes map to
       disjoint DOLCE categories:
          - if child's method is phase7_*, phase8_*, phase9c_* (corrected)
            AND parent's method is weak (propagated, tier3_default, gapfill)
          - propagate child's class up to parent
    4. Iterate until fixed point.
    5. Output master-v3ca.tsv + stats.
"""
import os, re, csv, glob, json
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
IN_MASTER     = os.path.join(OUT_DIR, "oewn-dulplus-master-v3c.tsv")
OUT_MASTER    = os.path.join(OUT_DIR, "oewn-dulplus-master-v3ca.tsv")

# DULplus → DOLCE (same as Phase 5)
DUL_TO_DOLCE = {
    "dul:Action": "perdurant", "dul:Event": "perdurant", "dul:State": "perdurant",
    "dul:Process": "perdurant", "dul:Achievement": "perdurant",
    "dul:EventType": "perdurant", "dul:CognitiveEvent": "perdurant",
    "dul:CognitiveState": "perdurant", "dul:Task": "perdurant",
    "dul:Quality": "quality", "dul:PhysicalAttribute": "physical-quality",
    "dul:Region": "region", "dul:TimeInterval": "temporal-region",
    "dul:SpaceRegion": "physical-region", "dul:Place": "region",
    "dul:PhysicalObject": "physical-object", "dul:DesignedArtifact": "non-agentive-physical-object",
    "dul:Organism": "agentive-physical-object", "dul:BiologicalObject": "physical-object",
    "dul:PhysicalBody": "physical-object", "dul:PhysicalPlace": "physical-object",
    "dul:Person": "agentive-physical-object", "dul:PhysicalAgent": "agentive-physical-object",
    "dul:Personification": "non-agentive-physical-object",
    "dul:Amount": "amount-of-matter", "dul:Substance": "amount-of-matter",
    "dul:FunctionalSubstance": "amount-of-matter", "dul:ChemicalObject": "amount-of-matter",
    "dul:InformationObject": "non-physical-endurant",
    "dul:InformationRealization": "non-physical-endurant",
    "dul:Narrative": "non-physical-endurant", "dul:Description": "description",
    "dul:Plan": "description", "dul:Goal": "description", "dul:Method": "description",
    "dul:Theory": "description", "dul:Norm": "description",
    "dul:Obligation": "description", "dul:Right": "description",
    "dul:Concept": "concept", "dul:Role": "concept",
    "dul:Parameter": "concept", "dul:Pattern": "concept",
    "dul:SocialRelation": "non-physical-endurant", "dul:Relation": "non-physical-endurant",
    "dul:Organization": "social-object",
    "dul:Collection": "collection", "dul:Collective": "collective",
    "coll:Taxon": "collection", "coll:AgentCollection": "collection",
    "coll:GeneticCollection": "collection", "coll:InformationCollection": "collection",
    "dul:Set": "abstract", "dul:Abstract": "abstract",
    "dul:Situation": "situation", "dul:System": "non-physical-endurant",
    "ontopic:Topic": "concept", "conc:InternalRepresentation": "non-physical-endurant",
    "rol:Status": "concept",
    "http://www.ontologydesignpatterns.org/ont/dul/Supplements.owl#SpatialFeature": "feature",
    "http://www.ontologydesignpatterns.org/ont/dul/Supplements.owl#DependentPlace": "feature",
    "http://www.ontologydesignpatterns.org/ont/dul/Supplements.owl#DependentPart": "feature",
    "http://www.ontologydesignpatterns.org/ont/dul/Supplements.owl#GeographicalFeature": "feature",
    "http://www.ontologydesignpatterns.org/ont/dul/Conceptualization.owl#InternalRepresentation": "non-physical-endurant",
    "owl:Thing": "particular",
}

DISJOINT_TOPS = {
    frozenset(["perdurant", "physical-object"]),
    frozenset(["perdurant", "non-physical-endurant"]),
    frozenset(["perdurant", "amount-of-matter"]),
    frozenset(["perdurant", "quality"]),
    frozenset(["perdurant", "region"]),
    frozenset(["perdurant", "abstract"]),
    frozenset(["perdurant", "concept"]),
    frozenset(["perdurant", "collection"]),
    frozenset(["perdurant", "collective"]),
    frozenset(["perdurant", "description"]),
    frozenset(["perdurant", "situation"]),
    frozenset(["physical-object", "non-physical-endurant"]),
    frozenset(["physical-object", "abstract"]),
    frozenset(["physical-object", "region"]),
    frozenset(["physical-object", "quality"]),
    frozenset(["physical-object", "concept"]),
    frozenset(["amount-of-matter", "non-physical-endurant"]),
    frozenset(["amount-of-matter", "region"]),
    frozenset(["amount-of-matter", "quality"]),
    frozenset(["amount-of-matter", "concept"]),
    frozenset(["quality", "concept"]),
    frozenset(["quality", "description"]),
    frozenset(["region", "concept"]),
    frozenset(["physical-region", "temporal-region"]),
    frozenset(["physical-quality", "temporal-quality"]),
}

def is_disjoint(cls_a, cls_b):
    a = DUL_TO_DOLCE.get(cls_a, "unknown")
    b = DUL_TO_DOLCE.get(cls_b, "unknown")
    if a == "unknown" or b == "unknown": return False
    return frozenset([a, b]) in DISJOINT_TOPS

STRONG_METHODS = {
    "phase1_topmapping",
    "phase3_tier1_derivation",
    "phase3_tier2_indirect",
    "phase3_tier3_gloss_starts_be",
    "phase3_tier3_gloss_starts_become",
    "phase3_tier3_cognitive_event_kw",
    "phase3_tier3_cognitive_state_kw",
    "phase4_A2_pertainym_default",  # deliberate design choice
    "phase7_hand_review",
    "phase7_systematic_review_from_phase3_propagated_from_hypernym",
    "phase7_manual_review_from_phase3_propagated_from_hypernym",
    "phase7_manual_review_from_phase1_propagated",
    "phase7_manual_review_from_phase3_tier3_default_event",
    "phase7_manual_review_from_phase1_inferred",
    "phase7_manual_override_from_phase3_propagated_from_hypernym",
    "phase8_systematic_review_from_phase1_propagated",
    "phase8_systematic_review_from_phase3_propagated_from_hypernym",
    "phase8_systematic_review_from_phase5alt_propagated_from_hypernym",
    "phase8_systematic_review_from_phase3_tier3_default_event",
    "phase9c_cognitive_reseed",
    "phase9a_upstream_repair",   # cascade upward repairs
}

WEAK_METHODS = {
    "phase1_propagated",
    "phase1_inferred",
    "phase3_propagated_from_hypernym",
    "phase3_tier3_default_event",
    "phase3_tier3_default_action",
    "phase5alt_propagated_from_hypernym",
    "phase5alt_propagated_transitively",
    "phase7_re_propagated",
    "phase8_re_propagated",
    "phase9c_re_propagated_cognitive",
}


def main():
    print("[1/5] Loading master (v3c state)...", flush=True)
    master = {}
    order = []
    with open(IN_MASTER) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            master[r["oewn_id"]] = r
            order.append(r["oewn_id"])
    print(f"      {len(master):,} synsets", flush=True)

    print("[2/5] Loading hypernym edges...", flush=True)
    hyp_edges = []  # (child, parent)
    for pat in ("noun.*.yaml", "verb.*.yaml", "adj.*.yaml", "adv.*.yaml"):
        for path in sorted(glob.glob(os.path.join(OEWN_YAML_DIR, pat))):
            for sid, body in _yload(path).items():
                child = f"oewn-{sid}"
                for h in (body.get("hypernym") or []):
                    hyp_edges.append((child, f"oewn-{h}"))
    print(f"      {len(hyp_edges):,} hypernym edges", flush=True)

    print("[3/5] Iteratively repairing upstream consistency...", flush=True)

    rounds = 0
    changed_total = 0
    stats_per_round = []
    while rounds < 10:
        rounds += 1
        changes_this_round = []
        violations_before = 0
        for child, parent in hyp_edges:
            c = master.get(child); p = master.get(parent)
            if not c or not p: continue
            if not is_disjoint(c["dulplus_class"], p["dulplus_class"]): continue
            violations_before += 1
            # Child strong + parent weak → propagate upward
            if c["method"] in STRONG_METHODS and p["method"] in WEAK_METHODS:
                old = p["dulplus_class"]
                new = c["dulplus_class"]
                # Avoid flipping parent into a class that's still disjoint with its OWN parent
                # (we'll catch that in the next round if needed)
                p["dulplus_class"] = new
                p["method"]        = "phase9a_upstream_repair"
                p["provenance"]    = f"parent aligned to strong-anchor child {child} ({new})"
                changes_this_round.append({"parent": parent, "old": old, "new": new, "child": child})

        stats_per_round.append({"round": rounds, "violations_found": violations_before,
                                 "repairs_made": len(changes_this_round)})
        print(f"      Round {rounds}: {violations_before:,} violations → {len(changes_this_round):,} repaired",
              flush=True)
        if len(changes_this_round) == 0: break
        changed_total += len(changes_this_round)

    print(f"      Total repairs across {rounds} rounds: {changed_total:,}", flush=True)

    # Final verification
    print("[4/5] Verifying: recomputing hypernym violations after repair...", flush=True)
    final_viol = 0
    for child, parent in hyp_edges:
        c = master.get(child); p = master.get(parent)
        if not c or not p: continue
        if is_disjoint(c["dulplus_class"], p["dulplus_class"]):
            final_viol += 1
    print(f"      Final disjoint violations: {final_viol:,}", flush=True)

    print("[5/5] Writing master-v3ca.tsv...", flush=True)
    cols = ["oewn_id", "pos", "dulplus_class", "method", "primary_lemma", "provenance", "gloss"]
    with open(OUT_MASTER, "w", newline="") as f:
        w = csv.DictWriter(f, delimiter="\t", fieldnames=cols)
        w.writeheader()
        for oid in order:
            r = master[oid]
            w.writerow({c: r.get(c, "") for c in cols})

    # Stats
    stats = {
        "phase": "9a_upstream_repair",
        "rounds": rounds,
        "total_repairs": changed_total,
        "per_round": stats_per_round,
        "final_violations": final_viol,
    }
    with open(os.path.join(OUT_DIR, "phase9a-stats.json"), "w") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps({k: v for k, v in stats.items() if k != "per_round"}, indent=2))


if __name__ == "__main__":
    main()
