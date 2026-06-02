#!/usr/bin/env python3
"""
Phase 3.5 — Rule-based revalidation of Phase 3 verb mappings.

Targets the 11,034 "propagated_from_hypernym" verbs + the tier3 default fallbacks
(the weakest parts of Phase 3), applying 7 rules grounded in
Silva et al. 2018 and Gangemi et al. 2003 to flag likely misclassifications.

Output:
    phase3_5-verb-review.tsv — one row per FLAGGED verb with aggregated rule
                               triggers, proposed class, rationale, decision slot.
    phase3_5-stats.json

Rules (see Phase 3 report for full discussion):
    R1  verb_own_gloss_silva   — re-apply Silva Tier-3 markers to verb's own gloss
    R2  aspectual_mismatch     — Gangemi state/process/event/action signal disagrees
                                  with current class
    R3  troponym_parent_inconsistent — >=50% of Tier-1 troponyms agree on class Y ≠ X
    R4  chained_fallback       — chain back to anchor passes through >=2 tier3 nodes
    R5  cognitive_false_pos    — class is Cognitive* but gloss has physical-sensation marker
    R6  transitivity_suggests_action — gloss is agentive transitive but class is Process/State
    R7  example_aspect         — aspectual markers in wn:example disagree with class
                                  (only used as a tiebreaker; low weight)
"""
import os, re, csv, glob, json
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
PHASE3_TSV    = "/sessions/exciting-pensive-rubin/mnt/outputs/phase3-verb-alignment.tsv"
OUT_DIR       = "/sessions/exciting-pensive-rubin/mnt/outputs"

PERDURANT_CLASSES = {
    "dul:Action", "dul:Event", "dul:State", "dul:Process",
    "dul:Achievement", "dul:CognitiveEvent", "dul:CognitiveState",
}

# ---------- Keyword sets ----------

GLOSS_ACTION_MARKERS = re.compile(
    r'\b(perform|execute|carry out|carry-out|do\s+something|do\s+an?|'
    r'cause\s+(someone|something|to|a|an)|make\s+(a|an|someone|something)|'
    r'produce|engage in|deliver|act|undertake)\b', re.I)
GLOSS_STATE_MARKERS = re.compile(
    r'\b(remain|stay|continue|persist|lie|exist|be\s+in\b|be\s+at\b|'
    r'be\s+shown|be\s+such|be\s+characterized|hold|consist\s+of|'
    r'have the property|have the quality|be\s+true|be\s+present)\b', re.I)
GLOSS_PROCESS_MARKERS = re.compile(
    r'\b(gradually|progressively|steadily|slowly|undergo|decompose|'
    r'evolve|accumulate|deteriorate|decay|transform|mature|develop|'
    r'ferment|erode)\b', re.I)
GLOSS_EVENT_MARKERS = re.compile(
    r'\b(reach|arrive at|attain|come to|complete|finish|achieve|'
    r'accomplish|happen|occur|begin|end|start|stop)\b', re.I)

SILVA_PERDURANT_OPENERS = {
    "the act of":        "dul:Action",
    "the activity of":   "dul:Action",
    "the process of":    "dul:Process",
    "the state of":      "dul:State",
    "the event of":      "dul:Event",
    "the occurrence of": "dul:Event",
}

COG_STATE_WORDS = re.compile(
    r'\b(know|believe|think|consider|feel|trust|doubt|be aware|'
    r'understand|hold|assume|suspect)\b', re.I)
COG_EVENT_WORDS = re.compile(
    r'\b(realize|recognize|discover|learn|notice|perceive|grasp|'
    r'comprehend|remember|recall|forget|become aware|come to know)\b', re.I)

PHYSICAL_SENSATION = re.compile(
    r'\b(itch|tingle|burn|sting|pain|ache|sore|hot|cold|warm|chilly|'
    r'wet|dry|sharp|tender|numb|sweaty|prickly|shiver|shudder|'
    r'crawling|tickle|twitch|throb)\b', re.I)

TRANSITIVE_PATTERN = re.compile(
    r'\b(to\s+\w+\s+(the|a|an|one|someone|something))\b|'
    r'\bcause\s+\w+\s+to\s+\w+\b', re.I)

GLOSS_BE_OPENING = re.compile(r'^\s*be\b', re.I)
GLOSS_BECOME_OPENING = re.compile(r'^\s*become\b', re.I)


def silva_marker_class(gloss):
    g = (gloss or "").lower().strip()
    for marker, cls in SILVA_PERDURANT_OPENERS.items():
        if g.startswith(marker):
            return cls, f"gloss_starts_'{marker}'"
    if GLOSS_BE_OPENING.match(g):   return "dul:State",       "gloss_starts_'be'"
    if GLOSS_BECOME_OPENING.match(g): return "dul:Achievement", "gloss_starts_'become'"
    return None, None


def aspectual_signal(gloss):
    """Return (class, triggered_marker_category) or None if no strong signal."""
    g = gloss or ""
    scores = {
        "dul:Action":  len(GLOSS_ACTION_MARKERS.findall(g)),
        "dul:State":   len(GLOSS_STATE_MARKERS.findall(g)),
        "dul:Process": len(GLOSS_PROCESS_MARKERS.findall(g)),
        "dul:Event":   len(GLOSS_EVENT_MARKERS.findall(g)),
    }
    top_class = max(scores, key=scores.get)
    if scores[top_class] == 0:
        return None
    # Only return if the top signal is uniquely strong
    second = sorted(scores.values(), reverse=True)[1]
    if scores[top_class] >= 1 and scores[top_class] > second:
        return (top_class, f"{top_class}_signals:{scores[top_class]}")
    return None


def example_aspect(examples):
    """Very rough: past simple = event/achievement; 'was X-ing' = process/action;
    present simple with object = state-ish. Weak signal."""
    if not examples: return None
    # Some OEWN examples are dicts like {"text": "...", "source": "..."} instead of plain strings.
    flat = []
    for ex in examples:
        if isinstance(ex, str):
            flat.append(ex)
        elif isinstance(ex, dict):
            # take the 'text' field if present, else stringify
            flat.append(ex.get("text") or ex.get("value") or "")
    text = " ".join(flat).lower()
    event_hits = len(re.findall(r'\b(was|were|did|had|got|became|broke|'
                                 r'stopped|started|finished|reached|arrived)\b', text))
    progressive_hits = len(re.findall(r'\bwas\s+\w+ing\b|\bis\s+\w+ing\b', text))
    stative_hits = len(re.findall(r'\b(is|are|remains|stands|knows|seems|contains)\b', text))
    scores = {"dul:Event": event_hits, "dul:Action": progressive_hits, "dul:State": stative_hits}
    top_class = max(scores, key=scores.get)
    if scores[top_class] == 0: return None
    second = sorted(scores.values(), reverse=True)[1]
    if scores[top_class] >= 2 and scores[top_class] > second:
        return (top_class, f"example_aspect:{top_class}={scores[top_class]}")
    return None


# ---------- Main ----------

def main():
    print("[1/6] Loading Phase 3 verb alignment...", flush=True)
    phase3 = {}
    with open(PHASE3_TSV) as f:
        for rec in csv.DictReader(f, delimiter="\t"):
            phase3[rec["oewn_id"]] = rec
    print(f"      verbs loaded: {len(phase3):,}", flush=True)

    print("[2/6] Loading verb YAML for gloss, examples, hypernyms...", flush=True)
    meta = {}
    for path in sorted(glob.glob(os.path.join(OEWN_YAML_DIR, "verb.*.yaml"))):
        for sid, body in _yload(path).items():
            oid = f"oewn-{sid}"
            meta[oid] = {
                "gloss":     (body.get("definition") or [""])[0] if body.get("definition") else "",
                "examples":  body.get("example") or [],
                "hypernym":  [f"oewn-{h}" for h in (body.get("hypernym") or [])],
                "members":   body.get("members") or [],
            }
    print(f"      loaded verb metadata: {len(meta):,}", flush=True)

    # Build reverse troponym index
    troponyms = defaultdict(list)
    for vid, m in meta.items():
        for h in m["hypernym"]:
            troponyms[h].append(vid)

    # Tier classification of each Phase 3 mapping
    def is_anchor_tier(tier):
        return tier in ("tier1_derivation", "tier2_indirect", "tier3_gloss_starts_be",
                        "tier3_gloss_starts_become", "tier3_cognitive_event_kw",
                        "tier3_cognitive_state_kw", "tier3_process_marker",
                        "tier3_cognitive_both_prefer_event")

    # ---------- Scope: revalidate only weak-tier verbs ----------
    # (propagated_from_hypernym, tier3_default_event, tier3_default_action)
    WEAK_TIERS = {"propagated_from_hypernym", "tier3_default_event", "tier3_default_action"}
    scope = [vid for vid, r in phase3.items() if r["tier"] in WEAK_TIERS]
    print(f"      revalidation scope (weak tiers): {len(scope):,}", flush=True)

    # ---------- Apply rules ----------
    print("[3/6] Applying rules R1–R7 ...", flush=True)
    flags = defaultdict(list)  # oewn_id -> list of (rule_id, proposed_class, detail)

    for vid in scope:
        rec = phase3[vid]
        current = rec["dulplus_class"]
        m = meta.get(vid, {})
        gloss = m.get("gloss", "")
        examples = m.get("examples", [])

        # -------- R1: Verb own gloss Silva check --------
        r1_cls, r1_detail = silva_marker_class(gloss)
        if r1_cls and r1_cls != current:
            flags[vid].append(("R1", r1_cls, r1_detail))

        # -------- R2: Aspectual mismatch --------
        asp = aspectual_signal(gloss)
        if asp and asp[0] and asp[0] != current:
            # Don't re-flag if R1 already proposed it
            if not any(f[1] == asp[0] for f in flags[vid]):
                flags[vid].append(("R2", asp[0], asp[1]))

        # -------- R5: Cognitive false positive --------
        if current in {"dul:CognitiveEvent", "dul:CognitiveState"}:
            if PHYSICAL_SENSATION.search(gloss) and not (
                    COG_STATE_WORDS.search(gloss) or COG_EVENT_WORDS.search(gloss)):
                proposed = "dul:State" if current == "dul:CognitiveState" else "dul:Event"
                flags[vid].append(("R5", proposed,
                                    f"physical_sensation:{PHYSICAL_SENSATION.search(gloss).group(0)}"))

        # -------- R6: Transitivity suggests action --------
        if current in {"dul:State", "dul:Process"}:
            if TRANSITIVE_PATTERN.search(gloss) and GLOSS_ACTION_MARKERS.search(gloss):
                if not any(f[1] == "dul:Action" for f in flags[vid]):
                    flags[vid].append(("R6", "dul:Action", "transitive_+action_marker"))

        # -------- R7: Example aspect (only if already flagged by some other rule) --------
        # This is only a tiebreaker. Apply lazily below.

    # -------- R3: Troponym-parent consistency --------
    # For every verb P (regardless of scope) with >=3 tier-1 children agreeing on class Y ≠ P's class,
    # flag P. This reaches beyond the WEAK_TIERS scope because mis-anchored parents
    # spoiled propagation.
    print("[4/6] Applying R3 (troponym-parent consistency)...", flush=True)
    r3_flags = {}
    for parent, kids in troponyms.items():
        p_rec = phase3.get(parent)
        if not p_rec: continue
        p_cls = p_rec["dulplus_class"]
        # Only count children mapped via Tier 1/2
        kid_classes = []
        for k in kids:
            kr = phase3.get(k)
            if kr and is_anchor_tier(kr["tier"]):
                kid_classes.append(kr["dulplus_class"])
        if len(kid_classes) >= 3:
            ctr = Counter(kid_classes)
            top_cls, top_n = ctr.most_common(1)[0]
            if top_cls != p_cls and top_n / len(kid_classes) >= 0.5:
                r3_flags[parent] = (top_cls, f"{top_n}/{len(kid_classes)}_tier1_kids_agree_on_{top_cls}")
    for vid, (proposed, detail) in r3_flags.items():
        flags[vid].append(("R3", proposed, detail))
    print(f"      R3 flagged parents: {len(r3_flags):,}", flush=True)

    # -------- R4: Chained fallback --------
    print("[5/6] Applying R4 (chained fallback)...", flush=True)
    def trace_chain(vid, depth=0, max_depth=12):
        """Return list of (oewn_id, tier) from this verb up to the first anchor tier."""
        chain = []
        cur = vid
        for _ in range(max_depth):
            rec = phase3.get(cur)
            if not rec: break
            chain.append((cur, rec["tier"]))
            if is_anchor_tier(rec["tier"]):
                break
            # propagated_from_hypernym — look at provenance
            prov = rec.get("provenance", "")
            m = re.match(r'from (oewn-\S+?)\[', prov)
            if not m: break
            cur = m.group(1)
        return chain

    for vid in scope:
        rec = phase3[vid]
        if rec["tier"] != "propagated_from_hypernym": continue
        chain = trace_chain(vid)
        # Count tier3 nodes in the chain between vid and the anchor
        tier3_count = sum(1 for _, t in chain if t.startswith("tier3_default"))
        if tier3_count >= 1 and len(chain) >= 3:
            flags[vid].append(("R4", "",
                               f"chain_len={len(chain)}_with_{tier3_count}_tier3_defaults"))

    # -------- R7: Example aspect (tiebreaker only) --------
    print("      Applying R7 (example aspect tiebreaker)...", flush=True)
    for vid in list(flags.keys()):
        m = meta.get(vid, {})
        ex = m.get("examples", [])
        if not ex: continue
        sig = example_aspect(ex)
        if sig and sig[0]:
            current = phase3[vid]["dulplus_class"]
            if sig[0] != current and any(f[1] == sig[0] for f in flags[vid]):
                flags[vid].append(("R7", sig[0], sig[1]))

    # ---------- Aggregate and write ----------
    print(f"[6/6] Writing output. Total flagged verbs: {len(flags):,}", flush=True)
    out_path = os.path.join(OUT_DIR, "phase3_5-verb-review.tsv")
    fields = ["oewn_id", "primary_lemma", "all_lemmas", "pos",
              "current_class", "current_tier", "current_provenance",
              "rules_triggered", "top_proposal", "rule_proposals", "rationale",
              "gloss", "examples", "hypernyms", "troponym_count",
              "confidence_score", "decision"]

    rows = []
    for vid, rule_list in flags.items():
        rec = phase3[vid]
        m = meta.get(vid, {})
        rules_triggered = ",".join(sorted(set(r[0] for r in rule_list)))
        # Score: each rule = 1; but R3 and R1 are higher-confidence = 2
        score = 0
        for r, _, _ in rule_list:
            if r in ("R1", "R3"): score += 2
            elif r == "R7": score += 0.5
            else: score += 1
        # Top proposal = mode of proposals (ignoring empty)
        props = [r[1] for r in rule_list if r[1]]
        top_proposal = Counter(props).most_common(1)[0][0] if props else ""
        rule_proposals = ";".join(f"{r}:{p}" for r, p, _ in rule_list if p)
        rationale = ";".join(f"{r}={d}" for r, p, d in rule_list)
        rows.append({
            "oewn_id": vid,
            "primary_lemma": m.get("members", [""])[0] if m.get("members") else "",
            "all_lemmas": "|".join(m.get("members", [])),
            "pos": "v",
            "current_class": rec["dulplus_class"],
            "current_tier": rec["tier"],
            "current_provenance": rec.get("provenance", ""),
            "rules_triggered": rules_triggered,
            "top_proposal": top_proposal,
            "rule_proposals": rule_proposals,
            "rationale": rationale,
            "gloss": (m.get("gloss") or "")[:280],
            "examples": (" | ".join([(e if isinstance(e, str) else (e.get("text") or ""))
                                      for e in m.get("examples", [])]) or "")[:250],
            "hypernyms": ",".join(m.get("hypernym", [])),
            "troponym_count": len(troponyms.get(vid, [])),
            "confidence_score": score,
            "decision": "",
        })

    # Sort by confidence score desc, then by rules_triggered
    rows.sort(key=lambda r: (-r["confidence_score"], r["rules_triggered"], r["primary_lemma"]))

    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, delimiter="\t", fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"      wrote {out_path}", flush=True)

    # Stats
    by_rule = Counter()
    for rule_list in flags.values():
        for r, _, _ in rule_list:
            by_rule[r] += 1

    by_score_bucket = Counter()
    for r in rows:
        s = r["confidence_score"]
        if s >= 4:   by_score_bucket["very_high (>=4)"] += 1
        elif s >= 2: by_score_bucket["high (2-3.99)"] += 1
        else:        by_score_bucket["low (<2)"] += 1

    # Also: for flagged verbs, what class flip is most common?
    flips = Counter()
    for r in rows:
        if r["top_proposal"]:
            flips[f"{r['current_class']} → {r['top_proposal']}"] += 1

    stats = {
        "phase3_verbs_total":          len(phase3),
        "weak_tier_scope":             len(scope),
        "flagged_verbs":               len(flags),
        "flagged_pct_of_weak_scope":   round(100 * len(flags) / len(scope), 2) if scope else 0,
        "rule_hits":                   dict(by_rule),
        "confidence_buckets":          dict(by_score_bucket),
        "top_flip_patterns":           dict(flips.most_common(10)),
    }
    with open(os.path.join(OUT_DIR, "phase3_5-stats.json"), "w") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
