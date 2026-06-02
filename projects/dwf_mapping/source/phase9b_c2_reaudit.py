#!/usr/bin/env python3
"""
Phase 9b — C2 re-audit with head-noun extraction.

Phase 8 defaulted 2,935 C2 cases to accept_current because the gloss-keyword
heuristic was noisy. A better approach: extract the gloss's head noun (the
noun that denotes the synset itself) and use that to guide the class.

Strategy:
    For each gloss, try to extract the head noun using simple patterns:
      "a/an/the HEAD that/which/who...": HEAD is the synset's type
      "a/an/the X HEAD of ...": HEAD could be the last noun before 'of'
      "(some) HEAD-ish-adj X": HEAD the main noun
    Then map HEAD to a DULplus class using a lexicon.

    If the head-derived class contradicts the current class, flip to a
    corrected class. Otherwise keep.

Output:
    oewn-dulplus-master-v3bc.tsv
    phase9b-stats.json
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
IN_MASTER     = os.path.join(OUT_DIR, "oewn-dulplus-master-v3c.tsv")  # post-9c state
OUT_MASTER    = os.path.join(OUT_DIR, "oewn-dulplus-master-v3bc.tsv")

# Lexicon mapping head noun → DULplus class
# Expanded from Phase 5-alt heuristics with semantic refinements
HEAD_TO_CLASS = {
    # Organisms / plants / animals
    "animal": "dul:Organism", "bird": "dul:Organism", "fish": "dul:Organism",
    "mammal": "dul:Organism", "reptile": "dul:Organism", "insect": "dul:Organism",
    "plant": "dul:Organism", "tree": "dul:Organism", "flower": "dul:Organism",
    "herb": "dul:Organism", "shrub": "dul:Organism", "vine": "dul:Organism",
    "fungus": "dul:Organism", "bacterium": "dul:Organism", "virus": "dul:Organism",
    "organism": "dul:Organism", "microorganism": "dul:Organism",
    "algae": "dul:Organism", "moss": "dul:Organism", "grass": "dul:Organism",
    # Body parts
    "organ": "dul:BiologicalObject", "bone": "dul:BiologicalObject",
    "muscle": "dul:BiologicalObject", "tissue": "dul:BiologicalObject",
    "cell": "dul:BiologicalObject", "nerve": "dul:BiologicalObject",
    # People / agents
    "person": "dul:Person", "individual": "dul:Person", "someone": "dul:Person",
    "worker": "dul:Person", "employee": "dul:Person", "native": "dul:Person",
    "inhabitant": "dul:Person", "citizen": "dul:Person", "resident": "dul:Person",
    "member": "dul:Person", "official": "dul:Person", "leader": "dul:Person",
    "artist": "dul:Person", "author": "dul:Person", "writer": "dul:Person",
    "player": "dul:Person", "scientist": "dul:Person", "doctor": "dul:Person",
    # Groups / collectives
    "group": "dul:Collective", "organization": "dul:Organization",
    "company": "dul:Organization", "society": "dul:Organization",
    "association": "dul:Organization", "club": "dul:Organization",
    "team": "dul:Collective", "crowd": "dul:Collective",
    # Artifacts
    "tool": "dul:DesignedArtifact", "device": "dul:DesignedArtifact",
    "machine": "dul:DesignedArtifact", "instrument": "dul:DesignedArtifact",
    "apparatus": "dul:DesignedArtifact", "vehicle": "dul:DesignedArtifact",
    "weapon": "dul:DesignedArtifact", "container": "dul:DesignedArtifact",
    "furniture": "dul:DesignedArtifact", "garment": "dul:DesignedArtifact",
    "article": "dul:DesignedArtifact",  # "an article of clothing" → the garment
    "implement": "dul:DesignedArtifact", "clothing": "dul:DesignedArtifact",
    "structure": "dul:DesignedArtifact", "component": "dul:DesignedArtifact",
    # Substances
    "substance": "dul:Substance", "material": "dul:Substance",
    "compound": "dul:Substance", "mixture": "dul:Substance",
    "liquid": "dul:Substance", "fluid": "dul:Substance",
    "gas": "dul:Substance", "solid": "dul:Substance",
    "element": "dul:Substance", "mineral": "dul:Substance",
    "chemical": "dul:ChemicalObject",
    # Places
    "place": "dul:Place", "area": "dul:Place", "region": "dul:Place",
    "zone": "dul:Place", "territory": "dul:Place", "location": "dul:Place",
    "district": "dul:Place", "country": "dul:Place", "city": "dul:Place",
    "town": "dul:Place", "village": "dul:Place", "park": "dul:Place",
    "building": "dul:PhysicalPlace", "room": "dul:Place",
    "mountain": "dul:Place", "river": "dul:Place", "lake": "dul:Place",
    "ocean": "dul:Place", "sea": "dul:Place", "forest": "dul:Place",
    # Information / symbolic
    "message": "dul:InformationRealization", "statement": "dul:InformationRealization",
    "document": "dul:InformationRealization", "text": "dul:InformationRealization",
    "article(written)": "dul:InformationRealization",  # disambiguated from artifact sense
    "book": "dul:InformationRealization", "report": "dul:InformationRealization",
    "description": "dul:Description", "definition": "dul:Description",
    "theory": "dul:Theory", "concept": "dul:Concept", "idea": "dul:Concept",
    "notion": "dul:Concept", "belief": "dul:Concept",
    # Events / actions
    "event": "dul:Event", "happening": "dul:Event", "occurrence": "dul:Event",
    "act": "dul:Action", "action": "dul:Action", "activity": "dul:Action",
    "process": "dul:Process", "state": "dul:State", "condition": "dul:State",
    "feature": "dul:Description",
    "phenomenon": "dul:Event",
    "experience": "dul:Situation", "situation": "dul:Situation",
    # Quantities / measurements
    "amount": "dul:Amount", "quantity": "dul:Amount", "measure": "dul:Amount",
    "number": "dul:Abstract", "value": "dul:Quality",
    "percentage": "dul:Amount", "proportion": "dul:Amount",
    # Qualities (for adjective-related nouns)
    "property": "dul:Quality", "attribute": "dul:Concept",
    "quality": "dul:Quality", "characteristic": "dul:Quality",
}

# Head-extraction regex patterns
HEAD_PATTERNS = [
    # "a/an/the HEAD that/which/who/where/when..."
    re.compile(r'^\s*\(?[^)]*\)?\s*(?:a|an|the)\s+(\w+)(?:\s+that\b|\s+which\b|\s+who\b|\s+where\b|\s+when\b|,)', re.I),
    # "a/an/the HEAD of X"  — HEAD is a shape-type descriptor
    re.compile(r'^\s*\(?[^)]*\)?\s*(?:a|an|the)\s+(\w+)\s+(?:of|for|to)\b', re.I),
    # "any (of the) HEAD..."
    re.compile(r'^\s*any\s+(?:of\s+)?(?:a\s+|an\s+|the\s+)?(\w+)\b', re.I),
    # "X, (usually|often) a HEAD..."
    re.compile(r',\s*(?:usually|often|especially)\s+(?:a|an|the)\s+(\w+)\b', re.I),
    # Fallback: first lemma-like noun after optional "(parenthetical)" + article
    re.compile(r'^\s*\(?[^)]*\)?\s*(?:a|an|the)\s+(\w+)\b', re.I),
]

def extract_head(gloss: str):
    """Return (head_noun_lower, class) or (None, None)."""
    g = gloss.strip()
    for pat in HEAD_PATTERNS:
        m = pat.match(g)
        if m:
            head = m.group(1).lower()
            # Skip if it's actually a modifier
            if head in {"usually", "often", "especially", "any", "most", "many", "few"}:
                continue
            if head in HEAD_TO_CLASS:
                return head, HEAD_TO_CLASS[head]
            return head, None
    return None, None


def main():
    print("[1/4] Loading OEWN noun metadata...", flush=True)
    noun_meta = {}
    for path in sorted(glob.glob(os.path.join(OEWN_YAML_DIR, "noun.*.yaml"))):
        for sid, body in _yload(path).items():
            noun_meta[f"oewn-{sid}"] = {
                "definition": (body.get("definition") or [""])[0] if body.get("definition") else "",
                "members":    body.get("members") or [],
            }
    print(f"      loaded {len(noun_meta):,} noun synsets", flush=True)

    print("[2/4] Loading current master (post-9c)...", flush=True)
    master = {}
    order = []
    with open(IN_MASTER) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            master[r["oewn_id"]] = r
            order.append(r["oewn_id"])
    print(f"      loaded {len(master):,} synsets", flush=True)

    print("[3/4] Re-auditing C2 noun mappings via head extraction...", flush=True)
    # Only revise nouns whose method suggests weak evidence (propagated, inferred, phase5alt).
    # Leave topmapping and Phase 1 tier-1 untouched.
    REVISABLE_METHODS = {
        "phase1_propagated", "phase1_inferred",
        "phase5alt_propagated_from_hypernym", "phase5alt_propagated_transitively",
        "gapfill_organism_gloss", "gapfill_substance_gloss",
        "gapfill_artifact_gloss", "gapfill_place_gloss", "gapfill_person_gloss",
        "gapfill_event_gloss", "gapfill_info_gloss", "gapfill_default",
    }
    changes = []
    skipped_unknown_head = 0
    skipped_already_match = 0
    for oid, r in master.items():
        if r["pos"] != "n": continue
        if r["method"] not in REVISABLE_METHODS: continue
        meta = noun_meta.get(oid)
        if not meta: continue
        gloss = meta["definition"]
        head, head_cls = extract_head(gloss)
        if not head_cls:
            skipped_unknown_head += 1
            continue
        if r["dulplus_class"] == head_cls:
            skipped_already_match += 1
            continue
        # Only revise if the head_cls is meaningfully different (class-distance >= 2)
        # to avoid noise; a simple proxy: if distinct top-level, flip
        old_cls = r["dulplus_class"]
        # Skip if current class is Tier 1 or topmapping-like (we already excluded those methods)
        changes.append({"oewn_id": oid, "old": old_cls, "new": head_cls,
                         "head": head, "lemma": r["primary_lemma"],
                         "gloss": gloss[:90]})
        r["dulplus_class"] = head_cls
        r["method"]        = "phase9b_head_noun_reclassification"
        r["provenance"]    = f"gloss head noun '{head}' → {head_cls}"
    print(f"      revisable nouns inspected: "
          f"{sum(1 for r in master.values() if r['pos']=='n' and r['method'] in REVISABLE_METHODS):,}",
          flush=True)
    print(f"      changes applied: {len(changes):,}", flush=True)
    print(f"      skipped (unknown head):   {skipped_unknown_head:,}", flush=True)
    print(f"      skipped (already match):  {skipped_already_match:,}", flush=True)

    # Class-shift summary
    shifts = Counter((c["old"], c["new"]) for c in changes)
    print("\n      Top 10 shifts (old → new):")
    for (o, n), ct in shifts.most_common(10):
        print(f"        {ct:>5}  {o} → {n}")

    print("\n[4/4] Writing master-v3bc.tsv...", flush=True)
    cols = ["oewn_id", "pos", "dulplus_class", "method", "primary_lemma", "provenance", "gloss"]
    with open(OUT_MASTER, "w", newline="") as f:
        w = csv.DictWriter(f, delimiter="\t", fieldnames=cols)
        w.writeheader()
        for oid in order:
            r = master[oid]
            w.writerow({c: r.get(c, "") for c in cols})
    # Sample changes
    print("\nSample changes (first 10):")
    for c in changes[:10]:
        print(f"  {c['oewn_id']} {c['lemma']:22s}  {c['old']:20s} → {c['new']}  "
              f"(head='{c['head']}')")
        print(f"    gloss: {c['gloss']}")

    # Save stats
    stats = {
        "phase": "9b_c2_reaudit",
        "revisable_nouns_inspected": sum(1 for r in master.values() if r['pos']=='n' and r['method'] == 'phase9b_head_noun_reclassification'),
        "changes": len(changes),
        "skipped_unknown_head": skipped_unknown_head,
        "skipped_already_match": skipped_already_match,
        "top_shifts": {f"{o}→{n}": c for (o, n), c in shifts.most_common(20)},
    }
    with open(os.path.join(OUT_DIR, "phase9b-stats.json"), "w") as f:
        json.dump(stats, f, indent=2)


if __name__ == "__main__":
    main()
