#!/usr/bin/env python3
"""
Build the full doubtful-mappings register.

A "doubt" = a synset where the evidence supported more than one defensible
DULplus class, and the pipeline had to break the tie. We log every such case
with: chosen_class + reason, alternative_class + reason, class distance,
priority score.

Categories:
    C1 — rule_conflict          multiple rules proposed different classes
    C2 — hypernym_vs_gloss      child's propagated class disagrees with its own gloss
    C3 — multiclass_framester   Framester assigned multiple classes; we collapsed to one
    C4 — satellite_vs_gloss     satellite's inherited class vs its own gloss
    C5 — pertainym_vs_referent  pertainym mapped to generic Quality vs referent's finer class
    C6 — gapfill_vs_gloss       Phase 5-alt propagated class vs synset's own gloss

Output:
    doubtful-mappings-register.tsv      full register
    doubtful-mappings-priority.tsv      sorted by priority_score descending
    doubtful-register-stats.json        counts by category + by priority tier
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
MASTER_TSV    = "/sessions/exciting-pensive-rubin/mnt/outputs/oewn-dulplus-master-v2.tsv"
PHASE1_TSV    = "/sessions/exciting-pensive-rubin/mnt/outputs/oewn-dulplus-alignment.tsv"
PHASE35_TSV   = "/sessions/exciting-pensive-rubin/mnt/outputs/phase3_5-verb-review.tsv"
PHASE4_TSV    = "/sessions/exciting-pensive-rubin/mnt/outputs/phase4-adj-adv-alignment.tsv"
DISJOINT_TSV  = "/sessions/exciting-pensive-rubin/mnt/outputs/phase5-disjoint-pairs.tsv"
OUT_DIR       = "/sessions/exciting-pensive-rubin/mnt/outputs"

# ----------------------------------------------------------------------
# DOLCE hierarchy for computing class-distance
# ----------------------------------------------------------------------
# Top-level DOLCE-Lite branches
DOLCE_TOPS = {
    "perdurant":    {"dul:Action", "dul:Event", "dul:State", "dul:Process",
                     "dul:Achievement", "dul:EventType", "dul:CognitiveEvent",
                     "dul:CognitiveState", "dul:Task"},
    "quality":      {"dul:Quality", "dul:PhysicalAttribute"},
    "region":       {"dul:Region", "dul:TimeInterval", "dul:SpaceRegion", "dul:Place"},
    "physical-endurant": {"dul:PhysicalObject", "dul:DesignedArtifact", "dul:Organism",
                          "dul:BiologicalObject", "dul:PhysicalBody", "dul:PhysicalPlace",
                          "dul:Person", "dul:PhysicalAgent", "dul:Personification",
                          "dul:Amount", "dul:Substance", "dul:FunctionalSubstance",
                          "dul:ChemicalObject"},
    "non-physical-endurant": {"dul:InformationObject", "dul:InformationRealization",
                              "dul:Narrative", "dul:SocialRelation", "dul:Relation",
                              "dul:System", "conc:InternalRepresentation"},
    "description":  {"dul:Description", "dul:Plan", "dul:Goal", "dul:Method",
                     "dul:Theory", "dul:Norm", "dul:Obligation", "dul:Right"},
    "concept":      {"dul:Concept", "dul:Role", "dul:Parameter", "dul:Pattern",
                     "ontopic:Topic", "rol:Status"},
    "social":       {"dul:Organization"},
    "collection":   {"dul:Collection", "dul:Collective", "coll:Taxon",
                     "coll:AgentCollection", "coll:GeneticCollection",
                     "coll:InformationCollection"},
    "abstract":     {"dul:Set", "dul:Abstract", "owl:Thing"},
    "situation":    {"dul:Situation"},
    "feature":      {"http://www.ontologydesignpatterns.org/ont/dul/Supplements.owl#SpatialFeature",
                     "http://www.ontologydesignpatterns.org/ont/dul/Supplements.owl#DependentPlace",
                     "http://www.ontologydesignpatterns.org/ont/dul/Supplements.owl#DependentPart",
                     "http://www.ontologydesignpatterns.org/ont/dul/Supplements.owl#GeographicalFeature"},
}
# Endurant group = everything that's non-perdurant/non-quality/non-region
ENDURANT_GROUPS = {"physical-endurant", "non-physical-endurant"}
# Similar groups collapse together for distance-1
CLOSE_GROUPS = [
    {"quality", "region"},                  # both are quality-related
    {"description", "concept"},             # both are descriptive abstracts
    {"physical-endurant", "social", "collection"}, # all substantive endurants
    {"non-physical-endurant", "description", "concept"}, # abstract endurants family
]

def top_group(cls):
    for group, members in DOLCE_TOPS.items():
        if cls in members:
            return group
    return "unknown"

def class_distance(a, b):
    """0 = same class. 1 = same top group. 2 = close groups. 3 = disjoint tops."""
    if a == b: return 0
    ga, gb = top_group(a), top_group(b)
    if ga == gb: return 1
    for close_set in CLOSE_GROUPS:
        if ga in close_set and gb in close_set:
            return 2
    return 3

# Method confidence weight — lower-priority methods (defaults) get higher weight
# because the "chosen" class is less certain, so the doubt deserves more scrutiny.
METHOD_WEIGHT = {
    "phase1_topmapping":                        1,
    "phase1_propagated":                        2,
    "phase1_inferred":                          3,
    "phase3_tier1_derivation":                  1,
    "phase3_tier2_indirect":                    2,
    "phase3_tier3_gloss_starts_be":             2,
    "phase3_tier3_gloss_starts_become":         2,
    "phase3_tier3_cognitive_event_kw":          3,
    "phase3_tier3_cognitive_state_kw":          3,
    "phase3_propagated_from_hypernym":          4,
    "phase3_tier3_default_event":               5,
    "phase3_tier3_default_action":              5,
    "phase4_A1_satellite_inherits_head":        3,
    "phase4_A1_satellite_fallback":             5,
    "phase4_A2_pertainym_default":              4,
    "phase4_A5_adj_head_default":               3,
    "phase4_A4_physical_attr_keyword":          2,
    "phase4_A3_participial_default":            3,
    "phase4_R1_adv_manner":                     2,
    "phase4_R2_adv_temporal":                   2,
    "phase4_R3_adv_spatial":                    2,
    "phase4_R4_adv_frequency":                  3,
    "phase4_R5_adv_degree":                     3,
    "phase4_R6_adv_modal":                      3,
    "phase4_R7_adv_default":                    5,
    "phase5alt_propagated_from_hypernym":       4,
    "phase5alt_propagated_transitively":        5,
}

# ----------------------------------------------------------------------
# Keyword sets for re-applying noun rules across all nouns (not just topmappings)
# ----------------------------------------------------------------------
PERDURANT_OPENERS = {
    "the act of":        "dul:Action",
    "the activity of":   "dul:Action",
    "the process of":    "dul:Process",
    "the state of":      "dul:State",
    "the event of":      "dul:Event",
    "the occurrence of": "dul:Event",
    "an act of":         "dul:Action",
    "a process of":      "dul:Process",
    "a state of":        "dul:State",
}
METALEVEL_LEMMAS = {"attribute", "relation", "property", "predicate", "concept"}
ORGANISM_GLOSS = re.compile(
    r'\b(plant|tree|animal|bird|fish|insect|mammal|reptile|organism|species|'
    r'fungus|bacterium|virus|flower|herb|shrub|vine)\b', re.I)
SUBSTANCE_GLOSS = re.compile(
    r'\b(liquid|fluid|gas|compound|mixture|material|element|mineral|alloy|powder|vapou?r)\b', re.I)
ARTIFACT_GLOSS = re.compile(
    r'\b(tool|device|machine|instrument|appliance|equipment|apparatus|vehicle|'
    r'weapon|container|furniture|garment|implement)\b', re.I)
PLACE_GLOSS = re.compile(
    r'\b(region|area|zone|territory|district|country|city|town|village|park|forest|'
    r'mountain|river|lake|ocean|building|room|hall)\b', re.I)
PERSON_GLOSS = re.compile(r'\b(person|individual|someone)\b.*\b(who|that|which)\b', re.I)
EVENT_GLOSS = re.compile(r'\b(happening|incident|occurrence|phenomenon)\b', re.I)
INFO_GLOSS = re.compile(r'\b(document|text|book|article|paper|report|description|message)\b', re.I)


def perdurant_opener_class(gloss):
    g = (gloss or "").lower().strip()
    for marker, cls in PERDURANT_OPENERS.items():
        if g.startswith(marker):
            return cls, f"gloss opens '{marker}'"
    return None, None

def noun_gloss_suggests(gloss, primary_lemma):
    """Return a list of (suggested_class, reason) from the gloss."""
    suggestions = []
    g = (gloss or "").lower()
    # Perdurant opener
    cls, reason = perdurant_opener_class(gloss)
    if cls:
        suggestions.append((cls, reason))
    # Metalevel
    if (primary_lemma or "").lower() in METALEVEL_LEMMAS:
        suggestions.append(("dul:Concept", f"lemma '{primary_lemma}' is metalevel"))
    # Content families
    if ORGANISM_GLOSS.search(g):
        suggestions.append(("dul:Organism", "organism keyword in gloss"))
    if SUBSTANCE_GLOSS.search(g):
        suggestions.append(("dul:FunctionalSubstance", "substance keyword in gloss"))
    if ARTIFACT_GLOSS.search(g):
        suggestions.append(("dul:DesignedArtifact", "artifact keyword in gloss"))
    if PLACE_GLOSS.search(g):
        suggestions.append(("dul:Place", "place keyword in gloss"))
    if PERSON_GLOSS.search(g):
        suggestions.append(("dul:Person", "person+relative-pronoun pattern"))
    if EVENT_GLOSS.search(g):
        suggestions.append(("dul:Event", "event keyword in gloss"))
    if INFO_GLOSS.search(g):
        suggestions.append(("dul:InformationRealization", "information keyword in gloss"))
    return suggestions


# ----------------------------------------------------------------------
# Verb-specific gloss suggestions (for C2 hypernym_vs_gloss on verbs)
# ----------------------------------------------------------------------
GLOSS_BE_OPEN   = re.compile(r'^\s*be\b', re.I)
GLOSS_BECOME    = re.compile(r'^\s*become\b', re.I)
COG_STATE_KW    = re.compile(r'\b(know|believe|think|understand|hold|assume|consider|trust|doubt)\b', re.I)
COG_EVENT_KW    = re.compile(r'\b(realize|recognize|discover|learn|notice|grasp|comprehend)\b', re.I)
GLOSS_ACTION    = re.compile(r'\b(perform|execute|carry out|do\s+something|act|undertake|engage)\b', re.I)
GLOSS_PROCESS   = re.compile(r'\b(gradually|progressively|undergo|decompose|evolve|erode|decay)\b', re.I)
GLOSS_EVENT     = re.compile(r'\b(reach|arrive at|attain|come to|complete|finish|happen|occur)\b', re.I)

def verb_gloss_suggests(gloss):
    """Return a list of (suggested_class, reason)."""
    suggestions = []
    g = (gloss or "").lower().strip()
    # Silva tier-3 markers
    for marker, cls in PERDURANT_OPENERS.items():
        if g.startswith(marker):
            suggestions.append((cls, f"gloss opens '{marker}'"))
    if GLOSS_BE_OPEN.match(g):   suggestions.append(("dul:State",       "gloss opens 'be'"))
    if GLOSS_BECOME.match(g):    suggestions.append(("dul:Achievement", "gloss opens 'become'"))
    if COG_STATE_KW.search(g):   suggestions.append(("dul:CognitiveState", "cognitive-state keyword"))
    if COG_EVENT_KW.search(g):   suggestions.append(("dul:CognitiveEvent", "cognitive-event keyword"))
    if GLOSS_ACTION.search(g):   suggestions.append(("dul:Action", "action marker"))
    if GLOSS_PROCESS.search(g):  suggestions.append(("dul:Process", "process marker"))
    if GLOSS_EVENT.search(g):    suggestions.append(("dul:Event", "event marker"))
    return suggestions


# ----------------------------------------------------------------------
# Adjective-specific gloss suggestions (physical-attribute keywords)
# ----------------------------------------------------------------------
PHYSICAL_ATTR_KW = re.compile(
    r'\b(colou?r|hue|shade|size|shape|dimension|length|width|height|depth|volume|'
    r'weight|mass|density|temperature|texture|taste|smell|sound|brightness|speed)\b',
    re.I)

def adj_gloss_suggests(gloss):
    suggestions = []
    if PHYSICAL_ATTR_KW.search(gloss or ""):
        suggestions.append(("dul:PhysicalAttribute", "physical-attribute keyword in gloss"))
    return suggestions


# ----------------------------------------------------------------------
# Adverb-specific gloss suggestions
# ----------------------------------------------------------------------
ADV_MANNER = re.compile(r'^\s*in\s+(a|an|the)\s+\w*\s*(manner|way|style|fashion)', re.I)
ADV_TEMPORAL = re.compile(r'\b(era|period|before|after|during|yesterday|today|tomorrow|per\s+annum)\b', re.I)
ADV_SPATIAL  = re.compile(r'\b(place|location|position|direction|upward|downward|here|there|above|below)\b', re.I)
ADV_MODAL    = re.compile(r'\b(possibly|probably|certainly|likely|maybe|perhaps|clearly)\b', re.I)

def adv_gloss_suggests(gloss):
    suggestions = []
    g = (gloss or "").lower()
    if ADV_MANNER.match(g):   suggestions.append(("dul:Region", "manner-adverb pattern"))
    if ADV_TEMPORAL.search(g): suggestions.append(("dul:TimeInterval", "temporal marker"))
    if ADV_SPATIAL.search(g):  suggestions.append(("dul:SpaceRegion", "spatial marker"))
    if ADV_MODAL.search(g):    suggestions.append(("dul:Abstract", "modal marker"))
    return suggestions


# ======================================================================
# Main
# ======================================================================
def main():
    print("[1/9] Loading master alignment + OEWN metadata...", flush=True)
    # Load master v2 (includes Phase 5-alt gap-fill)
    master = {}
    with open(MASTER_TSV) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            # Some synsets have multiple rows; keep the first we see (dedup later)
            if r["oewn_id"] not in master:
                master[r["oewn_id"]] = r
    print(f"      loaded {len(master):,} unique synsets from master", flush=True)

    # Load all OEWN synset metadata
    synset_meta = {}
    for pat in ("noun.*.yaml", "verb.*.yaml", "adj.*.yaml", "adv.*.yaml"):
        for path in sorted(glob.glob(os.path.join(OEWN_YAML_DIR, pat))):
            d = _yload(path)
            for sid, body in d.items():
                oid = f"oewn-{sid}"
                synset_meta[oid] = body
    print(f"      loaded {len(synset_meta):,} synset bodies", flush=True)

    # Build hyponym index (reverse of hypernym)
    hyponyms = defaultdict(list)
    for sid, body in synset_meta.items():
        for h in (body.get("hypernym") or []):
            hyponyms[f"oewn-{h}"].append(sid)

    def downstream_count(oid):
        """Count all descendants through hyponymy. Cap at 1000 to avoid blowup."""
        seen = set()
        stack = list(hyponyms.get(oid, []))
        while stack and len(seen) < 1000:
            c = stack.pop()
            if c in seen: continue
            seen.add(c)
            stack.extend(hyponyms.get(c, []))
        return len(seen)

    # ------------------------------------------------------------------
    # Build sense→synset + sense→pertainym indexes (for C5)
    # ------------------------------------------------------------------
    print("[2/9] Building sense/pertainym indexes...", flush=True)
    sense_to_synset = {}
    pertainyms_by_adj_synset = defaultdict(list)  # adj_oewn_id -> [referent_oewn_id, ...]
    for path in sorted(glob.glob(os.path.join(OEWN_YAML_DIR, "entries-*.yaml"))):
        d = _yload(path)
        for lemma, poses in d.items():
            for pos, entry in poses.items():
                for sense in (entry.get("sense") or []):
                    skey = sense.get("id")
                    sid = sense.get("synset")
                    if skey and sid:
                        sense_to_synset[skey] = f"oewn-{sid}"
    # Second pass: now resolve pertainym targets
    for path in sorted(glob.glob(os.path.join(OEWN_YAML_DIR, "entries-*.yaml"))):
        d = _yload(path)
        for lemma, poses in d.items():
            for pos, entry in poses.items():
                for sense in (entry.get("sense") or []):
                    skey = sense.get("id")
                    sid  = sense.get("synset")
                    if not (skey and sid): continue
                    adj_oid = f"oewn-{sid}"
                    for per_skey in (sense.get("pertainym") or []):
                        ref_oid = sense_to_synset.get(per_skey)
                        if ref_oid:
                            pertainyms_by_adj_synset[adj_oid].append(ref_oid)
    print(f"      pertainym adj synsets indexed: {len(pertainyms_by_adj_synset):,}", flush=True)

    # ------------------------------------------------------------------
    # Prepare doubt list
    # ------------------------------------------------------------------
    doubts = []
    next_doubt_id = 1
    def new_doubt(oid, chosen, chosen_reason, alternative, alt_reason, category):
        nonlocal next_doubt_id
        meta = synset_meta.get(oid, {})
        m = master.get(oid, {})
        pos = meta.get("partOfSpeech", m.get("pos", ""))
        lemma = (meta.get("members") or [""])[0] if meta.get("members") else m.get("primary_lemma", "")
        gloss = (meta.get("definition") or [""])[0] if meta.get("definition") else m.get("gloss", "")
        cd = class_distance(chosen, alternative)
        mw = METHOD_WEIGHT.get(m.get("method", ""), 3)
        dc = downstream_count(oid) if pos in ("n", "v") else 0
        priority = cd * mw * (1 + dc / 10.0)
        doubts.append({
            "doubt_id":           f"D-{next_doubt_id:06d}",
            "oewn_id":            oid,
            "pos":                pos,
            "primary_lemma":      lemma,
            "gloss":               (gloss or "")[:200],
            "chosen_class":       chosen,
            "chosen_reason":      chosen_reason,
            "alternative_class":  alternative,
            "alternative_reason": alt_reason,
            "class_distance":     cd,
            "doubt_category":     category,
            "method":             m.get("method", ""),
            "priority_score":     round(priority, 2),
            "downstream_count":   dc,
            "decision":           "",
            "decision_comment":   "",
        })
        next_doubt_id += 1

    # ------------------------------------------------------------------
    # C1 — rule_conflict  (Phase 3.5 already has 1,228 verb cases)
    # ------------------------------------------------------------------
    print("[3/9] C1 — verb rule conflicts (from Phase 3.5 review)...", flush=True)
    with open(PHASE35_TSV) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if not r.get("top_proposal"): continue
            cur = r["current_class"]
            prop = r["top_proposal"]
            if prop == cur: continue
            new_doubt(
                r["oewn_id"],
                cur,
                f"Phase 3 tier: {r['current_tier']}",
                prop,
                f"Phase 3.5 rules {r['rules_triggered']}: {r.get('rationale', '')[:200]}",
                "C1_rule_conflict",
            )
    print(f"      C1 doubts: {sum(1 for d in doubts if d['doubt_category'] == 'C1_rule_conflict'):,}",
          flush=True)

    # ------------------------------------------------------------------
    # C2 — hypernym_vs_gloss (nouns: chosen class disagrees with own gloss)
    # Apply noun gloss rules to all mapped nouns; flag where rule disagrees.
    # ------------------------------------------------------------------
    print("[4/9] C2 — noun hypernym-vs-gloss (applying noun rules to all mapped nouns)...", flush=True)
    n_checked = 0
    for oid, m in master.items():
        if m["pos"] != "n": continue
        meta = synset_meta.get(oid, {})
        gloss = (meta.get("definition") or [""])[0] if meta.get("definition") else ""
        lemma = (meta.get("members") or [""])[0] if meta.get("members") else ""
        suggestions = noun_gloss_suggests(gloss, lemma)
        chosen = m["dulplus_class"]
        method = m["method"]
        # Only flag if chosen was propagated (not Phase 1 topmapping which is manually seeded)
        if "topmapping" in method: continue
        for suggested_cls, reason in suggestions:
            if suggested_cls == chosen: continue
            # Only flag if distance >= 2 (meaningful disagreement)
            if class_distance(chosen, suggested_cls) >= 2:
                new_doubt(oid, chosen,
                          f"propagated via {method}",
                          suggested_cls,
                          f"own gloss suggests: {reason}",
                          "C2_hypernym_vs_gloss")
                break  # one doubt per synset in this category
        n_checked += 1
    print(f"      C2 nouns checked: {n_checked:,}, "
          f"doubts: {sum(1 for d in doubts if d['doubt_category'] == 'C2_hypernym_vs_gloss'):,}",
          flush=True)

    # Also verbs: C2' for verbs where propagated class disagrees with verb own gloss
    print("      C2 — verb hypernym-vs-gloss...", flush=True)
    for oid, m in master.items():
        if m["pos"] != "v": continue
        if m["method"] != "phase3_propagated_from_hypernym": continue
        meta = synset_meta.get(oid, {})
        gloss = (meta.get("definition") or [""])[0] if meta.get("definition") else ""
        suggestions = verb_gloss_suggests(gloss)
        chosen = m["dulplus_class"]
        # Skip if already covered by C1 (Phase 3.5 already flagged it)
        if any(d["oewn_id"] == oid and d["doubt_category"] == "C1_rule_conflict" for d in doubts):
            continue
        for suggested_cls, reason in suggestions:
            if suggested_cls == chosen: continue
            if class_distance(chosen, suggested_cls) >= 2:
                new_doubt(oid, chosen,
                          f"propagated via {m['method']}",
                          suggested_cls,
                          f"own gloss suggests: {reason}",
                          "C2_hypernym_vs_gloss")
                break
    print(f"      C2 total doubts: {sum(1 for d in doubts if d['doubt_category'] == 'C2_hypernym_vs_gloss'):,}",
          flush=True)

    # ------------------------------------------------------------------
    # C3 — multiclass_framester  (1,731 synsets Framester gave 2+ classes)
    # ------------------------------------------------------------------
    print("[5/9] C3 — Framester multi-class collapses...", flush=True)
    multi_syn = defaultdict(list)
    with open(PHASE1_TSV) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            multi_syn[r["oewn_id"]].append({
                "class": r["dulplus_class"],
                "source": r["source"],
                "framester_id": r["framester_id"],
            })
    for oid, rs in multi_syn.items():
        if len(rs) < 2: continue
        if oid not in master: continue
        chosen = master[oid]["dulplus_class"]
        # Emit one doubt per alternative class not chosen
        for alt in rs:
            if alt["class"] != chosen:
                new_doubt(oid, chosen,
                          f"collapsed from Framester multi-class via method priority",
                          alt["class"],
                          f"Framester {alt['source']} also assigned this class ({alt['framester_id']})",
                          "C3_multiclass_framester")
    print(f"      C3 doubts: {sum(1 for d in doubts if d['doubt_category'] == 'C3_multiclass_framester'):,}",
          flush=True)

    # ------------------------------------------------------------------
    # C4 — satellite_vs_gloss  (satellites where own gloss contradicts head class)
    # ------------------------------------------------------------------
    print("[6/9] C4 — satellite vs gloss...", flush=True)
    for oid, m in master.items():
        if m["pos"] != "s": continue
        if "satellite_inherits_head" not in m["method"]: continue
        meta = synset_meta.get(oid, {})
        gloss = (meta.get("definition") or [""])[0] if meta.get("definition") else ""
        suggestions = adj_gloss_suggests(gloss)
        # Also check for perdurant-in-adj (rare but happens)
        chosen = m["dulplus_class"]
        for suggested_cls, reason in suggestions:
            if suggested_cls == chosen: continue
            if class_distance(chosen, suggested_cls) >= 1:  # adj distances are subtle
                new_doubt(oid, chosen,
                          f"inherited from head via wn:similar",
                          suggested_cls,
                          f"own gloss suggests: {reason}",
                          "C4_satellite_vs_gloss")
                break
    print(f"      C4 doubts: {sum(1 for d in doubts if d['doubt_category'] == 'C4_satellite_vs_gloss'):,}",
          flush=True)

    # ------------------------------------------------------------------
    # C5 — pertainym_vs_referent (5,601 pertainym adj mapped uniformly to Quality)
    # If the referent noun is NOT a quality/abstract class, the pertainym adj
    # could alternatively inherit the referent's more specific class.
    # ------------------------------------------------------------------
    print("[7/9] C5 — pertainym vs referent class...", flush=True)
    for adj_oid, ref_oids in pertainyms_by_adj_synset.items():
        if adj_oid not in master: continue
        chosen = master[adj_oid]["dulplus_class"]
        if chosen != "dul:Quality": continue  # only flag the uniform-Quality cases
        # Look at referent class
        for ref_oid in ref_oids[:1]:  # only consider the primary referent
            ref = master.get(ref_oid)
            if not ref: continue
            ref_cls = ref["dulplus_class"]
            if ref_cls == "dul:Quality": continue
            # If referent has a more specific class (e.g. Organism, Event), record doubt
            # Propose that the adjective could bind to the referent's class
            if class_distance("dul:Quality", ref_cls) >= 2:
                new_doubt(adj_oid, chosen,
                          "A2_pertainym_default = dul:Quality uniform",
                          ref_cls,
                          f"pertainym referent {ref_oid} ({ref.get('primary_lemma', '')}) has class {ref_cls}",
                          "C5_pertainym_vs_referent")
    print(f"      C5 doubts: {sum(1 for d in doubts if d['doubt_category'] == 'C5_pertainym_vs_referent'):,}",
          flush=True)

    # ------------------------------------------------------------------
    # C6 — gapfill_vs_gloss  (Phase 5-alt propagated class vs own gloss)
    # ------------------------------------------------------------------
    print("[8/9] C6 — gap-fill propagated vs own gloss...", flush=True)
    for oid, m in master.items():
        if "phase5alt" not in m["method"]: continue
        meta = synset_meta.get(oid, {})
        gloss = (meta.get("definition") or [""])[0] if meta.get("definition") else ""
        lemma = (meta.get("members") or [""])[0] if meta.get("members") else ""
        chosen = m["dulplus_class"]
        suggestions = noun_gloss_suggests(gloss, lemma)
        for suggested_cls, reason in suggestions:
            if suggested_cls == chosen: continue
            if class_distance(chosen, suggested_cls) >= 2:
                new_doubt(oid, chosen,
                          f"Phase 5-alt propagated via {m['method']}",
                          suggested_cls,
                          f"own gloss suggests: {reason}",
                          "C6_gapfill_vs_gloss")
                break
    print(f"      C6 doubts: {sum(1 for d in doubts if d['doubt_category'] == 'C6_gapfill_vs_gloss'):,}",
          flush=True)

    # ------------------------------------------------------------------
    # Write outputs
    # ------------------------------------------------------------------
    print("[9/9] Writing register...", flush=True)
    out_full = os.path.join(OUT_DIR, "doubtful-mappings-register.tsv")
    cols = ["doubt_id", "oewn_id", "pos", "primary_lemma", "gloss",
            "chosen_class", "chosen_reason", "alternative_class", "alternative_reason",
            "class_distance", "doubt_category", "method",
            "priority_score", "downstream_count",
            "decision", "decision_comment"]
    with open(out_full, "w", newline="") as f:
        w = csv.DictWriter(f, delimiter="\t", fieldnames=cols)
        w.writeheader()
        for d in doubts:
            w.writerow(d)
    print(f"      wrote {out_full} ({len(doubts):,} doubts)", flush=True)

    # Stats
    cat_counter = Counter(d["doubt_category"] for d in doubts)
    dist_counter = Counter(d["class_distance"] for d in doubts)
    top_priority = sorted(doubts, key=lambda d: -d["priority_score"])
    stats = {
        "total_doubts":                len(doubts),
        "by_category":                 dict(cat_counter),
        "by_class_distance":           dict(dist_counter),
        "priority_tiers": {
            "very_high(top 1%)":  sum(1 for d in doubts if d["priority_score"] >= 40),
            "high(1-10%)":         sum(1 for d in doubts if 20 <= d["priority_score"] < 40),
            "medium(10-50%)":      sum(1 for d in doubts if 5 <= d["priority_score"] < 20),
            "low":                 sum(1 for d in doubts if d["priority_score"] < 5),
        },
    }
    with open(os.path.join(OUT_DIR, "doubtful-register-stats.json"), "w") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
