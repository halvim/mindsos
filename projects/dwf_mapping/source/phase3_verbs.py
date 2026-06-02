#!/usr/bin/env python3
"""
Phase 3 — Verb mapping via Silva et al. 2018 three-tier method
("Word Tagging with Foundational Ontology Classes: Extending the WordNet-DOLCE Mapping to Verbs")

Approach:
  1. Load OEWN verb synsets + lexical-sense derivation/antonym/verb-group links.
  2. Load Phase 1 noun alignment.
  3. For every verb synset, apply in order:
      Tier 1 — direct derivational link to a mapped noun + gloss marker ("the act/state/process of").
      Tier 2 — indirect link via antonym / verb-group / 'similar' to a mapped noun.
      Tier 3 — gloss-based heuristics:
            "be X"            → dul:State
            "become X"        → dul:Achievement / dul:Event
            cognitive verbs   → dul:CognitiveEvent / dul:CognitiveState
            default           → dul:Event
  4. Propagate upward and downward along the hyponym/hypernym chain — any unmapped verb
     inherits its hypernym's class (Silva 2018 §4 propagation rule).

Target DOLCE-Lite-Plus perdurant classes (Silva 2018 §3.1):
     dul:Event, dul:State, dul:Process, dul:Action, dul:CognitiveEvent, dul:CognitiveState, dul:Achievement
"""
import os, re, sys, csv, glob, json
from collections import defaultdict, Counter, deque
import yaml
try:
    from yaml import CLoader as _L
except ImportError:
    _L = yaml.SafeLoader

def _yload(path):
    with open(path) as f:
        return yaml.load(f, Loader=_L)

OEWN_YAML_DIR = "/tmp/oewn-repo/src/yaml"
ALIGN_TSV     = "/sessions/exciting-pensive-rubin/mnt/outputs/oewn-dulplus-alignment.tsv"
OUT_DIR       = "/sessions/exciting-pensive-rubin/mnt/outputs"

# ------------------------------------------------------------------
# Step 1: load existing Phase 1 noun alignment
# ------------------------------------------------------------------
def load_noun_alignment():
    m = {}
    with open(ALIGN_TSV) as f:
        for rec in csv.DictReader(f, delimiter="\t"):
            if rec["pos"] == "n":
                m[rec["oewn_id"]] = rec["dulplus_class"]
    return m

# ------------------------------------------------------------------
# Step 2: Load verb synsets from verb.*.yaml
# ------------------------------------------------------------------
def load_verb_synsets():
    synsets = {}
    for path in sorted(glob.glob(os.path.join(OEWN_YAML_DIR, "verb.*.yaml"))):
        for sid, body in _yload(path).items():
            oid = f"oewn-{sid}"
            synsets[oid] = {
                "pos":        "v",
                "ili":        body.get("ili"),
                "members":    body.get("members") or [],
                "definition": (body.get("definition") or [""])[0] if body.get("definition") else "",
                "hypernym":   [f"oewn-{h}" for h in (body.get("hypernym") or [])],
                "similar":    [f"oewn-{h}" for h in (body.get("similar") or [])],
                "entails":    [f"oewn-{h}" for h in (body.get("entails") or [])],
            }
    # Build hyponym reverse index (children)
    hypo = defaultdict(list)
    for child, meta in synsets.items():
        for h in meta["hypernym"]:
            hypo[h].append(child)
    return synsets, hypo

# ------------------------------------------------------------------
# Step 3: Build sense-key → synset and sense-derivation / antonym / verb-group indexes
#         Scan entries-*.yaml; only keep data for verb & noun senses.
# ------------------------------------------------------------------
def build_sense_indexes():
    # sense_key -> oewn_id
    sense_to_synset = {}
    # oewn_verb_id -> set of noun_sense_keys (via derivation)
    verb_sense_derivs = defaultdict(set)
    # oewn_verb_id -> set of verb_oewn_ids (via antonym, verb_group)
    verb_antonyms = defaultdict(set)
    verb_groups = defaultdict(set)

    entries_paths = sorted(glob.glob(os.path.join(OEWN_YAML_DIR, "entries-*.yaml")))
    for path in entries_paths:
        data = _yload(path)
        for lemma, poses in data.items():
            for pos, entry in poses.items():
                if pos not in ("n", "v"):
                    continue
                for sense in (entry.get("sense") or []):
                    skey = sense.get("id")
                    sid  = sense.get("synset")
                    if not skey or not sid:
                        continue
                    full_id = f"oewn-{sid}"
                    sense_to_synset[skey] = full_id
                    if pos == "v":
                        derivs = sense.get("derivation") or []
                        if derivs:
                            verb_sense_derivs[full_id].update(derivs)
                        ants = sense.get("antonym") or []
                        for a in ants:
                            verb_antonyms[full_id].add(a)
                        vg = sense.get("verb_group") or []
                        for v in vg:
                            verb_groups[full_id].add(v)

    # Turn verb_antonyms / verb_groups (sets of sense keys) into sets of oewn_ids once we have the map
    def resolve(sets_of_keys):
        out = defaultdict(set)
        for v_oid, keys in sets_of_keys.items():
            for k in keys:
                target = sense_to_synset.get(k)
                if target:
                    out[v_oid].add(target)
        return out

    return sense_to_synset, verb_sense_derivs, resolve(verb_antonyms), resolve(verb_groups)

# ------------------------------------------------------------------
# Step 4: Silva Tier rules
# ------------------------------------------------------------------
PERDURANT_MARKERS = {
    "the act of":         "dul:Action",
    "the activity of":    "dul:Action",
    "the process of":     "dul:Process",
    "the state of":       "dul:State",
    "the event of":       "dul:Event",
    "the occurrence of":  "dul:Event",
}

def gloss_to_perdurant_class(gloss):
    g = (gloss or "").lower().strip()
    for marker, cls in PERDURANT_MARKERS.items():
        if g.startswith(marker):
            return cls, marker
    return None, None

# Tier 3: gloss-based
COGN_KEYWORDS = {
    "think", "believe", "know", "consider", "ponder",
    "understand", "comprehend", "realize", "recognize",
    "remember", "recall", "forget", "doubt", "trust", "assume",
    "perceive", "sense", "feel", "experience", "be aware",
}
COGN_EVENT_KEYWORDS = {
    "realize", "recognize", "discover", "learn", "figure out",
    "notice", "perceive", "grasp", "comprehend", "remember",
    "recall", "forget", "become aware", "come to know",
}
COGN_STATE_KEYWORDS = {
    "know", "believe", "think", "consider", "feel", "trust",
    "doubt", "be aware", "understand", "hold", "assume", "suspect",
}
STATE_VERBS_BE = re.compile(r'^\s*be\b')
BECOME_VERBS   = re.compile(r'^\s*become\b|^\s*get\s+(angry|tired|sad|happy|big|small|hot|cold)\b')
PROCESS_MARKERS = {"gradually", "slowly", "progressively", "decompose", "erode", "grow", "develop", "mature"}

def gloss_based_assign(gloss, hyponyms_count=0):
    """Tier 3: gloss-based heuristic for verbs. Returns (class, rule_name)."""
    g = (gloss or "").lower().strip()
    if not g:
        return "dul:Event", "tier3_default_empty_gloss"

    # Silva 2018 explicit: gloss opens with 'be' → state
    if STATE_VERBS_BE.match(g):
        return "dul:State", "tier3_gloss_starts_be"

    if BECOME_VERBS.match(g):
        return "dul:Achievement", "tier3_gloss_starts_become"

    # Perdurant markers
    cls, marker = gloss_to_perdurant_class(g)
    if cls:
        return cls, f"tier3_marker:{marker}"

    # Cognitive-state vs cognitive-event keyword overlap
    cognitive_state_hit = any(kw in g for kw in COGN_STATE_KEYWORDS)
    cognitive_event_hit = any(kw in g for kw in COGN_EVENT_KEYWORDS)
    if cognitive_event_hit and not cognitive_state_hit:
        return "dul:CognitiveEvent", "tier3_cognitive_event_kw"
    if cognitive_state_hit and not cognitive_event_hit:
        return "dul:CognitiveState", "tier3_cognitive_state_kw"
    if cognitive_state_hit and cognitive_event_hit:
        return "dul:CognitiveEvent", "tier3_cognitive_both_prefer_event"

    # Process markers
    if any(kw in g for kw in PROCESS_MARKERS):
        return "dul:Process", "tier3_process_marker"

    # Default: action for transitive-sounding, event otherwise
    # Very rough heuristic: "to X something" cues action; otherwise event
    if re.search(r'\bto\s+\w+(?:s|ed|ing)?\s+(the|a|an|some|something|someone)\b', g):
        return "dul:Action", "tier3_default_action"

    return "dul:Event", "tier3_default_event"

# ------------------------------------------------------------------
# Step 5: Tier 1 and Tier 2 resolution
# ------------------------------------------------------------------
def tier1(verb_id, verb_meta, verb_derivs, sense_to_synset, noun_align, noun_meta):
    """Follow derivational links to nouns; if any noun's gloss starts with a
    perdurant marker, inherit that class. Return (class, rule_name, provenance_str) or None.
    """
    candidate_classes = []
    evidence = []
    for noun_skey in verb_derivs.get(verb_id, []):
        noun_syn = sense_to_synset.get(noun_skey)
        if not noun_syn or noun_syn not in noun_align:
            continue
        noun_gloss = (noun_meta.get(noun_syn, {}).get("definition") or "").lower().strip()
        cls, marker = gloss_to_perdurant_class(noun_gloss)
        if cls:
            candidate_classes.append(cls)
            evidence.append(f"deriv→{noun_syn}(marker='{marker}')")
    if candidate_classes:
        # Silva: take the most common if multiple
        top = Counter(candidate_classes).most_common(1)[0][0]
        return top, "tier1_derivation", "|".join(evidence[:3])
    return None

def tier2(verb_id, verb_antonyms, verb_groups, noun_align, noun_meta,
          sense_to_synset, verb_derivs, verb_mapping):
    """Look up derivational link via antonym or verb-group peers.

    A verb v's antonym/verb-group neighbour often has a derivational noun that
    already yields a Tier-1 result. We try that and return the class.
    """
    evidence = []
    candidate_classes = []
    related = verb_antonyms.get(verb_id, set()) | verb_groups.get(verb_id, set())
    for peer in related:
        # Does peer have a known class?
        if peer in verb_mapping:
            peer_class = verb_mapping[peer][0]
            candidate_classes.append(peer_class)
            evidence.append(f"peer={peer}({peer_class})")
            continue
        # Or can we reach one through peer's derivations?
        t1 = tier1(peer, None, verb_derivs, sense_to_synset, noun_align, noun_meta)
        if t1:
            candidate_classes.append(t1[0])
            evidence.append(f"peer_deriv={peer}({t1[0]})")
    if candidate_classes:
        top = Counter(candidate_classes).most_common(1)[0][0]
        return top, "tier2_indirect", "|".join(evidence[:3])
    return None

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    print("[1/6] Loading Phase 1 noun alignment...", flush=True)
    noun_align = load_noun_alignment()
    print(f"      mapped nouns: {len(noun_align):,}", flush=True)

    print("[2/6] Loading verb synsets...", flush=True)
    verbs, hypo = load_verb_synsets()
    print(f"      verb synsets: {len(verbs):,}", flush=True)

    print("[3/6] Loading noun synset metadata for gloss lookup...", flush=True)
    noun_meta = {}
    for path in sorted(glob.glob(os.path.join(OEWN_YAML_DIR, "noun.*.yaml"))):
        for sid, body in _yload(path).items():
            oid = f"oewn-{sid}"
            noun_meta[oid] = {"definition": (body.get("definition") or [""])[0] if body.get("definition") else ""}
    print(f"      noun metadata entries: {len(noun_meta):,}", flush=True)

    print("[4/6] Building sense-key / derivation / antonym / verb-group indexes...", flush=True)
    sense_to_synset, verb_derivs, verb_antonyms, verb_groups = build_sense_indexes()
    print(f"      sense keys:   {len(sense_to_synset):,}", flush=True)
    print(f"      verbs w/ derivations: {len(verb_derivs):,}", flush=True)
    print(f"      verbs w/ antonyms:    {len(verb_antonyms):,}", flush=True)
    print(f"      verbs w/ verb_group:  {len(verb_groups):,}", flush=True)

    print("[5/6] Applying Silva three-tier mapping...", flush=True)
    verb_mapping = {}  # oewn_id -> (class, tier, provenance)

    # Tier 1 pass (all verbs)
    for vid, meta in verbs.items():
        t = tier1(vid, meta, verb_derivs, sense_to_synset, noun_align, noun_meta)
        if t:
            verb_mapping[vid] = t

    # Tier 2 pass (unmapped verbs)
    for vid, meta in verbs.items():
        if vid in verb_mapping: continue
        t = tier2(vid, verb_antonyms, verb_groups, noun_align, noun_meta,
                  sense_to_synset, verb_derivs, verb_mapping)
        if t:
            verb_mapping[vid] = t

    # Tier 3 pass (apply ONLY to top-level-ish verbs to avoid polluting deep tree)
    # A "seed" verb is one with no mapped ancestor. We'll iteratively extend upward.
    # Simpler approach: compute depth (distance to a verb with no hypernym) and run tier3
    # on every verb. Then in propagation step, prefer mappings whose tier is smaller.
    for vid, meta in verbs.items():
        if vid in verb_mapping: continue
        gloss = meta.get("definition", "")
        cls, rule = gloss_based_assign(gloss, len(hypo.get(vid, [])))
        verb_mapping[vid] = (cls, rule, "gloss")

    # Propagate: for verbs that ended up at tier3 (default) and whose hypernym is at tier1/tier2,
    # prefer the hypernym's class (more reliable). Silva §4 propagation rule.
    # Iterate until no change.
    TIER_PRIORITY = {"tier1_derivation": 1, "tier2_indirect": 2}  # lower is more reliable
    def is_tier3(entry):
        return entry[1].startswith("tier3")

    changed = True
    prop_rounds = 0
    while changed and prop_rounds < 10:
        changed = False
        prop_rounds += 1
        for vid, meta in verbs.items():
            cur = verb_mapping.get(vid)
            if not cur or not is_tier3(cur):
                continue
            # Look at hypernym ancestors; pick the nearest tier1/tier2 ancestor
            for hv in meta["hypernym"]:
                anc = verb_mapping.get(hv)
                if anc and not is_tier3(anc):
                    verb_mapping[vid] = (anc[0], "propagated_from_hypernym", f"from {hv}[{anc[1]}]")
                    changed = True
                    break

    print(f"      propagation rounds: {prop_rounds}", flush=True)

    # Breakdown
    tier_ct = Counter()
    class_ct = Counter()
    for vid, (cls, tier, _) in verb_mapping.items():
        tier_ct[tier] += 1
        class_ct[cls] += 1

    print("[6/6] Writing outputs...", flush=True)
    # Add verb mappings to a new TSV
    out_tsv = os.path.join(OUT_DIR, "phase3-verb-alignment.tsv")
    with open(out_tsv, "w") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["oewn_id", "dulplus_class", "tier", "provenance",
                    "primary_lemma", "all_lemmas", "gloss", "hypernyms"])
        for vid in sorted(verb_mapping):
            cls, tier, prov = verb_mapping[vid]
            meta = verbs[vid]
            lemmas = meta["members"]
            w.writerow([
                vid, cls, tier, prov,
                lemmas[0] if lemmas else "",
                "|".join(lemmas),
                (meta["definition"] or "")[:300],
                ",".join(meta["hypernym"]),
            ])

    stats = {
        "verb_synsets_total":  len(verbs),
        "verbs_mapped":        len(verb_mapping),
        "coverage_percent":    round(100 * len(verb_mapping) / len(verbs), 2),
        "tier_breakdown":      dict(tier_ct),
        "class_breakdown":     dict(class_ct),
        "propagation_rounds":  prop_rounds,
    }
    with open(os.path.join(OUT_DIR, "phase3-stats.json"), "w") as f:
        json.dump(stats, f, indent=2)

    print(json.dumps(stats, indent=2))
    print(f"\nWrote: {out_tsv}")


if __name__ == "__main__":
    main()
