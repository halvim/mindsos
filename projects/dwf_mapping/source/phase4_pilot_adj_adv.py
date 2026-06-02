#!/usr/bin/env python3
"""
Phase 4 pilot — 100-synset adjective + adverb mapping pilot.

Neither Gangemi 2003 nor Silva 2018 covered adjectives/adverbs, so this is
genuinely unpublished territory. The rules below are grounded in DOLCE's
Quality / Quale / Region distinction (Gangemi 2003 §"Quality vs Quale") and
in the published Open English WordNet structure.

Deliverable: a 100-row review TSV with the proposed class for each synset
and the rule that fired, for user sign-off before scaling to all 21,833
adj + adv synsets.

Scope:
   adj.all  — 14,496 synsets (3,779 heads + 10,717 satellites via `similar`)
   adj.pert — 3,663 pertainym adjectives (gloss opens "of or relating to…")
   adj.ppl  — 60 participial adjectives
   adv.all  — 3,614 adverbs (many pertain to adjectives)

Target classes (DULplus, per user's Q1:C choice):
   dul:Quality           — adjectival attribute (inhering particular)
   dul:PhysicalAttribute — physical measurable quality
   dul:Region            — value in a quality space (quale)
   dul:TimeInterval      — temporal adverb
   dul:SpaceRegion       — spatial adverb
   dul:Abstract          — modal / epistemic adverb

Rules — ADJECTIVES
   A1: Satellite inherits from its `similar` head (if head already mapped here)
   A2: `adj.pert` default: dul:Quality (relational; note pertainym target if known)
   A3: `adj.ppl`  default: dul:Quality (participial; deverbal quality)
   A4: Gloss color/shape/size/temperature markers → dul:PhysicalAttribute
   A5: Default for adj.all heads: dul:Quality

Rules — ADVERBS
   R1_adv: Gloss opens "in a"/"in an"/"in the … manner" → dul:Region (manner)
   R2_adv: Temporal markers (era, period, past/present/future, day, year) → dul:TimeInterval
   R3_adv: Spatial markers (place, position, direction, at X, to X) → dul:SpaceRegion
   R4_adv: Frequency markers (often, rarely, always, never, sometimes)  → dul:Region (frequency)
   R5_adv: Degree markers (to a X degree, extent; extremely, slightly)   → dul:Region (degree)
   R6_adv: Modal/epistemic markers (possibly, probably, certainly, likely) → dul:Abstract
   R7_adv: Default → dul:Region
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

OEWN_YAML_DIR = "/tmp/oewn-repo/src/yaml"
OUT_DIR       = "/sessions/exciting-pensive-rubin/mnt/outputs"

# ------------- Adjective rules -------------
PHYSICAL_ATTR_KEYWORDS = re.compile(
    r'\b(color|colou?red|hue|shade|pigment|'
    r'size|shape|dimension|length|width|height|depth|volume|area|'
    r'weight|mass|heavy|light(?!\s+(on|of))|dense|'
    r'temperature|hot|cold|warm|cool|'
    r'texture|rough|smooth|soft|hard|'
    r'taste|sweet|salty|bitter|sour|'
    r'smell|scent|odou?r|fragrance|'
    r'sound|loud|quiet|volume|'
    r'bright|dark|dim|luminous|'
    r'speed|fast|slow)\b', re.I)

GLOSS_RELATIONAL_OPENER = re.compile(r'^\s*of\s+or\s+(relating|pertaining|belonging|having)\b', re.I)


def map_adjective(sid, body, head_map, satellite_has_head):
    """Return (dul_class, rule, rationale)."""
    pos = body.get("partOfSpeech")
    gloss = (body.get("definition") or [""])[0] if body.get("definition") else ""
    members = body.get("members") or []
    lexfile = body.get("lexfile", "")  # not always present in these yamls; handled at call site

    # A1: satellite inherits from head
    if pos == "s":
        similar = body.get("similar") or []
        head_candidate = None
        for h in similar:
            if h in head_map:  # head already mapped (processed earlier)
                head_candidate = h
                break
        if head_candidate:
            head_cls = head_map[head_candidate]
            return head_cls, "A1_satellite_inherits_head", f"inherited from head {head_candidate}"
        # If head not yet processed, fall through; post-pass will re-resolve.
        return "dul:Quality", "A1_satellite_no_head_fallback", "satellite with no-yet-processed head; defaulted"

    # A4: physical-attribute gloss
    if PHYSICAL_ATTR_KEYWORDS.search(gloss):
        return "dul:PhysicalAttribute", "A4_physical_attr_keyword", f"gloss has physical-attribute marker"

    # Default for heads
    return "dul:Quality", "A5_adj_head_default", "adj.all head default"


def map_adj_pert(sid, body):
    gloss = (body.get("definition") or [""])[0] if body.get("definition") else ""
    if GLOSS_RELATIONAL_OPENER.match(gloss):
        return "dul:Quality", "A2_pertainym_relational", "gloss opens 'of or relating to' — relational adjective"
    return "dul:Quality", "A2_pertainym_default", "adj.pert default"


def map_adj_ppl(sid, body):
    return "dul:Quality", "A3_participial_default", "participial adjective (adj.ppl) — deverbal quality"


# ------------- Adverb rules -------------
ADV_MANNER       = re.compile(r'^\s*in\s+(a|an|the)\s+\w+(\s+\w+)?\s+(manner|way|style|fashion)\b', re.I)
ADV_IN_A_GENERIC = re.compile(r'^\s*in\s+(a|an)\s+\w+\s+(manner|way|style|fashion|state|condition)', re.I)
ADV_TEMPORAL     = re.compile(r'\b(era|period|age|before|after|during|past|present|future|'
                              r'yesterday|today|tomorrow|morning|afternoon|evening|night|'
                              r'century|decade|year|month|week|day|hour|minute|second|'
                              r'historically|formerly|currently|recently|'
                              r'ago|earlier|later|always|continually|temporarily)\b', re.I)
ADV_SPATIAL      = re.compile(r'\b(place|location|position|direction|upward|downward|'
                              r'forward|backward|sideways|inward|outward|here|there|'
                              r'above|below|nearby|faraway|distant|far|near|everywhere|'
                              r'somewhere|nowhere|north|south|east|west)\b', re.I)
ADV_FREQUENCY    = re.compile(r'\b(always|often|frequently|regularly|usually|sometimes|occasionally|'
                              r'rarely|seldom|hardly|scarcely|never|once|twice|repeatedly|'
                              r'intermittently|continually)\b', re.I)
ADV_DEGREE       = re.compile(r'\b(degree|extent|extremely|slightly|moderately|somewhat|'
                              r'very|highly|greatly|mildly|utterly|thoroughly|completely|'
                              r'partially|fully|entirely)\b', re.I)
ADV_MODAL        = re.compile(r'\b(possibly|probably|certainly|likely|unlikely|maybe|perhaps|'
                              r'definitely|surely|clearly|evidently|apparently|supposedly|'
                              r'reportedly|allegedly)\b', re.I)


def map_adverb(sid, body):
    gloss = (body.get("definition") or [""])[0] if body.get("definition") else ""
    gl = gloss.lower()

    if ADV_MANNER.match(gl) or ADV_IN_A_GENERIC.match(gl):
        return "dul:Region", "R1_adv_manner", f"manner adverb; gloss opens '{gl[:30]}…'"
    # Order matters: temporal before spatial because "always" triggers both frequency and temporal
    if ADV_FREQUENCY.search(gl) and not ADV_TEMPORAL.search(gl):
        return "dul:Region", "R4_adv_frequency", "frequency marker in gloss"
    if ADV_TEMPORAL.search(gl):
        return "dul:TimeInterval", "R2_adv_temporal", "temporal marker in gloss"
    if ADV_SPATIAL.search(gl):
        return "dul:SpaceRegion", "R3_adv_spatial", "spatial marker in gloss"
    if ADV_DEGREE.search(gl):
        return "dul:Region", "R5_adv_degree", "degree/intensity marker in gloss"
    if ADV_MODAL.search(gl):
        return "dul:Abstract", "R6_adv_modal", "modal/epistemic marker in gloss"
    return "dul:Region", "R7_adv_default", "adverb default (quality region)"


# ------------- Main -------------
def main():
    random.seed(4242)

    print("[1/4] Loading adjective + adverb YAMLs...", flush=True)
    yamls = {
        "adj.all":  _yload(os.path.join(OEWN_YAML_DIR, "adj.all.yaml")),
        "adj.pert": _yload(os.path.join(OEWN_YAML_DIR, "adj.pert.yaml")),
        "adj.ppl":  _yload(os.path.join(OEWN_YAML_DIR, "adj.ppl.yaml")),
        "adv.all":  _yload(os.path.join(OEWN_YAML_DIR, "adv.all.yaml")),
    }
    for name, d in yamls.items():
        print(f"      {name}: {len(d):,}", flush=True)

    # ---- Stratified sampling ----
    # Adj (50 total):
    adj_all = list(yamls["adj.all"].items())
    heads = [(k, v) for k, v in adj_all if v.get("partOfSpeech") == "a"]
    sats  = [(k, v) for k, v in adj_all if v.get("partOfSpeech") == "s"]
    adj_pert_list = list(yamls["adj.pert"].items())
    adj_ppl_list  = list(yamls["adj.ppl"].items())
    adv_list      = list(yamls["adv.all"].items())

    sample_heads = random.sample(heads, 25)
    sample_sats  = random.sample(sats, 15)
    sample_pert  = random.sample(adj_pert_list, 8)
    sample_ppl   = random.sample(adj_ppl_list, 2)
    sample_adv   = random.sample(adv_list, 50)

    print(f"[2/4] Sampled {len(sample_heads)+len(sample_sats)+len(sample_pert)+len(sample_ppl)} adj + {len(sample_adv)} adv", flush=True)

    # ---- Build partial head map by running heads first ----
    # Apply adjective rules. For satellites, we need already-mapped heads, so order matters.
    head_map = {}  # oewn_id -> class
    # First pass: run all heads in adj.all for the ENTIRE yaml, so satellites can look up.
    for sid, body in yamls["adj.all"].items():
        if body.get("partOfSpeech") == "a":
            cls, rule, _ = map_adjective(sid, body, head_map={}, satellite_has_head=False)
            head_map[f"oewn-{sid}"] = cls

    # ---- Apply rules to pilot sample ----
    pilot_rows = []
    for sid, body in sample_heads:
        cls, rule, rationale = map_adjective(sid, body, head_map, False)
        pilot_rows.append(("adjective_head", sid, body, cls, rule, rationale))
    for sid, body in sample_sats:
        # resolve via head lookup using normalized IRIs
        sim_ids = [f"oewn-{s}" for s in (body.get("similar") or [])]
        head_cls = None
        head_ref = None
        for hid in sim_ids:
            if hid in head_map:
                head_cls = head_map[hid]
                head_ref = hid
                break
        if head_cls:
            cls, rule, rationale = head_cls, "A1_satellite_inherits_head", f"inherited from head {head_ref}"
        else:
            cls, rule, rationale = "dul:Quality", "A1_satellite_no_head_fallback", "satellite head not found in adj.all heads"
        pilot_rows.append(("adjective_satellite", sid, body, cls, rule, rationale))
    for sid, body in sample_pert:
        cls, rule, rationale = map_adj_pert(sid, body)
        pilot_rows.append(("adjective_pertainym", sid, body, cls, rule, rationale))
    for sid, body in sample_ppl:
        cls, rule, rationale = map_adj_ppl(sid, body)
        pilot_rows.append(("adjective_participial", sid, body, cls, rule, rationale))
    for sid, body in sample_adv:
        cls, rule, rationale = map_adverb(sid, body)
        pilot_rows.append(("adverb", sid, body, cls, rule, rationale))

    # ---- Write pilot TSV ----
    out = os.path.join(OUT_DIR, "phase4-pilot-adj-adv.tsv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["synset_type", "oewn_id", "pos", "primary_lemma", "all_lemmas",
                    "proposed_class", "rule", "rationale",
                    "gloss", "attribute", "similar", "domain_topic", "user_decision"])
        for stype, sid, body, cls, rule, rationale in pilot_rows:
            gl = (body.get("definition") or [""])[0] if body.get("definition") else ""
            w.writerow([
                stype,
                f"oewn-{sid}",
                body.get("partOfSpeech", ""),
                (body.get("members") or [""])[0],
                "|".join(body.get("members") or []),
                cls, rule, rationale,
                gl[:250],
                ",".join(str(a) for a in (body.get("attribute") or [])),
                ",".join(str(s) for s in (body.get("similar") or [])[:3]),
                ",".join(str(d) for d in (body.get("domain_topic") or [])),
                "",  # user decision
            ])

    # ---- Stats on the full inventories (what rules would fire on the full set) ----
    # This shows the expected distribution when we scale.
    print("[3/4] Projecting rule distribution across FULL adj/adv inventory...", flush=True)
    projected_adv = Counter()
    for sid, body in adv_list:
        cls, rule, _ = map_adverb(sid, body)
        projected_adv[rule] += 1
    projected_adj_head = Counter()
    projected_adj_sat  = Counter()
    for sid, body in yamls["adj.all"].items():
        if body.get("partOfSpeech") == "a":
            cls, rule, _ = map_adjective(sid, body, {}, False)
            projected_adj_head[rule] += 1
        else:
            projected_adj_sat["A1_satellite_inherits_head"] += 1
    projected_pert = len(adj_pert_list)
    projected_ppl  = len(adj_ppl_list)

    stats = {
        "pilot_rows_total":  len(pilot_rows),
        "pilot_breakdown":   dict(Counter(r[0] for r in pilot_rows)),
        "projected_full_coverage": {
            "adj.all_heads":      dict(projected_adj_head),
            "adj.all_satellites": dict(projected_adj_sat),
            "adj.pert_total":     projected_pert,
            "adj.ppl_total":      projected_ppl,
            "adv.all":            dict(projected_adv),
            "grand_total_synsets": (sum(projected_adj_head.values()) + sum(projected_adj_sat.values())
                                     + projected_pert + projected_ppl + sum(projected_adv.values())),
        },
    }
    with open(os.path.join(OUT_DIR, "phase4-pilot-stats.json"), "w") as f:
        json.dump(stats, f, indent=2)
    print(f"[4/4] Wrote {out}")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
