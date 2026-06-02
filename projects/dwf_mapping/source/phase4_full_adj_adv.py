#!/usr/bin/env python3
"""
Phase 4 — Full scale-up of adj/adv mapping over all 21,833 OEWN synsets.

Approved rules (user sign-off 2026-04-22):
    a=yes: add R0_adv idiom guard (reject spatial interpretation if gloss is
           idiomatic — "cost", "price", "money", "value" near the spatial marker)
    b=DULplus coarse: dul:Quality / dul:Region / dul:PhysicalAttribute /
                      dul:TimeInterval / dul:SpaceRegion / dul:Abstract
    c=annotation: pertainyms stay as dul:Quality with dct:relation annotation
                  to the referent lemma (sense-level pertainym link resolved
                  via entries-*.yaml → synset → primary lemma)

Output:
    phase4-adj-adv-alignment.tsv
    phase4-adj-adv-alignment.ttl   (SKOS + dct:relation for pertainyms)
    phase4-full-stats.json
    oewn-dulplus-master.tsv        (updated: nouns + verbs + adj + adv)
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
MASTER_TSV    = "/sessions/exciting-pensive-rubin/mnt/outputs/oewn-dulplus-master.tsv"
OUT_DIR       = "/sessions/exciting-pensive-rubin/mnt/outputs"

# ==================== ADJECTIVE RULES ====================
PHYSICAL_ATTR_KEYWORDS = re.compile(
    r'\b(colou?r|colou?red|hue|shade|pigment|chromati|wavelength|'
    r'size|shape|dimension|length|width|height|depth|volume|area|'
    r'weight|mass|heavy|light(?!\s+(on|of))|dense|density|'
    r'temperature|hot|cold|warm|cool|'
    r'texture|rough|smooth|soft|hard(?!ly)|'
    r'taste|sweet|salty|bitter|sour|'
    r'smell|scent|odou?r|fragrance|'
    r'sound|loud|quiet|volume|'
    r'bright|dark|dim|luminous|'
    r'speed|fast|slow)\b', re.I)

def map_adj_head(body):
    gloss = (body.get("definition") or [""])[0] if body.get("definition") else ""
    if PHYSICAL_ATTR_KEYWORDS.search(gloss):
        return "dul:PhysicalAttribute", "A4_physical_attr_keyword", "gloss has physical-attribute marker"
    return "dul:Quality", "A5_adj_head_default", "adj.all head default"

# ==================== ADVERB RULES ====================

# R0 idiom guard — cues that a "below / above / under / at" marker is idiomatic,
# not spatial. Matches Phase 4 pilot false positives like "at a loss" → below cost.
IDIOM_ECON_MARKERS = re.compile(
    r'\b(cost|price|money|value|wage|salary|income|debt|profit|'
    r'loss|deficit|surplus|earnings|expense|fee|rate|interest|'
    r'market|currency|dollar|pound|euro|par)\b', re.I)
IDIOM_FIGURATIVE_MARKERS = re.compile(
    r'\b(question|issue|matter|problem|point|subject|topic|'
    r'attention|consideration|concern|mind|risk|fault)\b', re.I)

ADV_MANNER_TIGHT = re.compile(r'^\s*in\s+(a|an|the)\s+\w+(\s+\w+)?\s+(manner|way|style|fashion)\b', re.I)
# Loose version catches "in a manner X-characteristic" too (pilot R7-false-negatives)
ADV_MANNER_LOOSE = re.compile(r'^\s*in\s+(a|an|the)\s+\w*\s*(manner|way|style|fashion)\b', re.I)
ADV_TEMPORAL     = re.compile(r'\b(era|period|age|before|after|during|past|present|future|'
                              r'yesterday|today|tomorrow|morning|afternoon|evening|night|'
                              r'century|decade|year|month|week|day|hour|minute|second|'
                              r'historically|formerly|currently|recently|'
                              r'ago|earlier|later|always|continually|temporarily|'
                              r'per\s+annum|per\s+day|per\s+year)\b', re.I)
ADV_SPATIAL      = re.compile(r'\b(place|location|position|direction|upward|downward|'
                              r'forward|backward|sideways|inward|outward|here|there|'
                              r'above|below|nearby|faraway|distant|far|near|everywhere|'
                              r'somewhere|nowhere|north|south|east|west|onshore|offshore)\b', re.I)
ADV_FREQUENCY    = re.compile(r'\b(always|often|frequently|regularly|usually|sometimes|occasionally|'
                              r'rarely|seldom|hardly|scarcely|never|once|twice|repeatedly|'
                              r'intermittently|continually)\b', re.I)
ADV_DEGREE       = re.compile(r'\b(degree|extent|extremely|slightly|moderately|somewhat|'
                              r'very|highly|greatly|mildly|utterly|thoroughly|completely|'
                              r'partially|fully|entirely|totally)\b', re.I)
ADV_MODAL        = re.compile(r'\b(possibly|probably|certainly|likely|unlikely|maybe|perhaps|'
                              r'definitely|surely|clearly|evidently|apparently|supposedly|'
                              r'reportedly|allegedly|presumably|arguably)\b', re.I)

def map_adv(body):
    gloss = (body.get("definition") or [""])[0] if body.get("definition") else ""
    gl = gloss.lower()
    # R1 first (manner) — most common adverb type
    if ADV_MANNER_TIGHT.match(gl) or ADV_MANNER_LOOSE.match(gl):
        return "dul:Region", "R1_adv_manner", "manner adverb"
    # R4 frequency (before R2, because "always" also triggers temporal)
    if ADV_FREQUENCY.search(gl) and not ADV_TEMPORAL.search(gl):
        return "dul:Region", "R4_adv_frequency", "frequency marker in gloss"
    # R2 temporal
    if ADV_TEMPORAL.search(gl):
        return "dul:TimeInterval", "R2_adv_temporal", "temporal marker in gloss"
    # R3 spatial — but first R0 guard against idioms
    if ADV_SPATIAL.search(gl):
        if IDIOM_ECON_MARKERS.search(gl) or IDIOM_FIGURATIVE_MARKERS.search(gl):
            # Guard triggered — spatial marker looks idiomatic; fall through
            pass
        else:
            return "dul:SpaceRegion", "R3_adv_spatial", "spatial marker in gloss"
    # R5 degree
    if ADV_DEGREE.search(gl):
        return "dul:Region", "R5_adv_degree", "degree/intensity marker in gloss"
    # R6 modal
    if ADV_MODAL.search(gl):
        return "dul:Abstract", "R6_adv_modal", "modal/epistemic marker in gloss"
    # R7 default
    return "dul:Region", "R7_adv_default", "adverb default (quality region)"

# ==================== PERTAINYM RESOLUTION ====================
def build_sense_indexes():
    """Scan entries-*.yaml and extract:
        sense_key → synset_id
        adj_sense_key → [referent_sense_keys] (pertainym)
    """
    sense_to_synset = {}
    pertainym_links = {}  # adj_sense_key -> list of referent sense keys
    for path in sorted(glob.glob(os.path.join(OEWN_YAML_DIR, "entries-*.yaml"))):
        data = _yload(path)
        for lemma, poses in data.items():
            for pos, entry in poses.items():
                for sense in (entry.get("sense") or []):
                    skey = sense.get("id")
                    sid  = sense.get("synset")
                    if skey and sid:
                        sense_to_synset[skey] = f"oewn-{sid}"
                    per = sense.get("pertainym") or []
                    if per and skey:
                        pertainym_links[skey] = per
    return sense_to_synset, pertainym_links

def get_synset_primary_lemma(synset_id, all_synset_meta):
    """Look up primary lemma for an OEWN synset ID."""
    meta = all_synset_meta.get(synset_id, {})
    members = meta.get("members") or []
    return members[0] if members else None

# ==================== MAIN ====================
def main():
    print("[1/7] Loading adj/adv YAMLs and other lexical files...", flush=True)
    yamls = {
        "adj.all":  _yload(os.path.join(OEWN_YAML_DIR, "adj.all.yaml")),
        "adj.pert": _yload(os.path.join(OEWN_YAML_DIR, "adj.pert.yaml")),
        "adj.ppl":  _yload(os.path.join(OEWN_YAML_DIR, "adj.ppl.yaml")),
        "adv.all":  _yload(os.path.join(OEWN_YAML_DIR, "adv.all.yaml")),
    }
    # Build a flat {oewn_id: body} index for lemma lookups
    all_synset_meta = {}
    for group, d in yamls.items():
        for sid, body in d.items():
            all_synset_meta[f"oewn-{sid}"] = body
    # Also load nouns for pertainym referent lemma lookup
    for pat in ("noun.*.yaml", "verb.*.yaml"):
        for path in sorted(glob.glob(os.path.join(OEWN_YAML_DIR, pat))):
            d = _yload(path)
            for sid, body in d.items():
                oid = f"oewn-{sid}"
                if oid not in all_synset_meta:
                    all_synset_meta[oid] = body

    print("[2/7] Scanning entries-*.yaml for sense-level pertainym links...", flush=True)
    sense_to_synset, pertainym_links = build_sense_indexes()
    print(f"      sense keys indexed: {len(sense_to_synset):,}", flush=True)
    print(f"      senses with pertainym link: {len(pertainym_links):,}", flush=True)

    # Build synset-level pertainym map: adj_synset_oewn_id → [referent_lemma_list]
    # We also keep referent synset IDs for the TTL's dct:relation target.
    synset_pertainyms = defaultdict(list)
    for adj_skey, refs in pertainym_links.items():
        adj_syn = sense_to_synset.get(adj_skey)
        if not adj_syn: continue
        for ref_skey in refs:
            ref_syn = sense_to_synset.get(ref_skey)
            if not ref_syn: continue
            ref_lemma = get_synset_primary_lemma(ref_syn, all_synset_meta)
            synset_pertainyms[adj_syn].append({
                "ref_synset": ref_syn,
                "ref_lemma":  ref_lemma,
                "ref_sense_key": ref_skey,
            })

    # ==================== Pass 1: map adjective heads ====================
    print("[3/7] Mapping adjective heads (pass 1)...", flush=True)
    head_map = {}  # oewn_id -> (class, rule, rationale)
    # adj.all heads
    for sid, body in yamls["adj.all"].items():
        if body.get("partOfSpeech") == "a":
            head_map[f"oewn-{sid}"] = map_adj_head(body)
    # adj.pert
    for sid, body in yamls["adj.pert"].items():
        head_map[f"oewn-{sid}"] = ("dul:Quality", "A2_pertainym_default",
                                    "adj.pert head — relational adjective")
    # adj.ppl
    for sid, body in yamls["adj.ppl"].items():
        head_map[f"oewn-{sid}"] = ("dul:Quality", "A3_participial_default",
                                    "adj.ppl head — participial adjective")

    # ==================== Pass 2: satellites inherit from head ====================
    print("[4/7] Mapping adjective satellites (pass 2)...", flush=True)
    sat_map = {}  # oewn_id -> (class, rule, rationale)
    for sid, body in yamls["adj.all"].items():
        if body.get("partOfSpeech") == "s":
            my_id = f"oewn-{sid}"
            similars = [f"oewn-{s}" for s in (body.get("similar") or [])]
            head_match = None
            for h in similars:
                if h in head_map:
                    head_match = h
                    break
            if head_match:
                head_cls = head_map[head_match][0]
                sat_map[my_id] = (head_cls, "A1_satellite_inherits_head",
                                   f"inherited from head {head_match}")
            else:
                sat_map[my_id] = ("dul:Quality", "A1_satellite_fallback",
                                   "no head found in adj.all; defaulted to dul:Quality")

    # ==================== Pass 3: adverbs ====================
    print("[5/7] Mapping adverbs (pass 3)...", flush=True)
    adv_map = {}
    for sid, body in yamls["adv.all"].items():
        adv_map[f"oewn-{sid}"] = map_adv(body)

    # Combine
    total_map = {}
    for d in (head_map, sat_map, adv_map):
        total_map.update(d)

    # ==================== Pass 4: write outputs ====================
    print(f"[6/7] Writing outputs for {len(total_map):,} synsets...", flush=True)

    # Output 1: phase4-adj-adv-alignment.tsv
    out_tsv = os.path.join(OUT_DIR, "phase4-adj-adv-alignment.tsv")
    with open(out_tsv, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["oewn_id", "pos", "dulplus_class", "rule", "rationale",
                    "primary_lemma", "all_lemmas", "gloss", "pertainym_lemmas"])
        for oid in sorted(total_map):
            cls, rule, rationale = total_map[oid]
            meta = all_synset_meta.get(oid, {})
            pos = meta.get("partOfSpeech", "")
            members = meta.get("members") or []
            gloss = (meta.get("definition") or [""])[0] if meta.get("definition") else ""
            perts = synset_pertainyms.get(oid, [])
            pert_str = ",".join(p["ref_lemma"] for p in perts if p["ref_lemma"])
            w.writerow([
                oid, pos, cls, rule, rationale,
                members[0] if members else "",
                "|".join(members), gloss[:250], pert_str,
            ])
    print(f"      wrote {out_tsv}", flush=True)

    # Output 2: phase4-adj-adv-alignment.ttl with dct:relation for pertainyms
    out_ttl = os.path.join(OUT_DIR, "phase4-adj-adv-alignment.ttl")
    with open(out_ttl, "w") as f:
        f.write("@prefix oewn:    <https://en-word.net/id/> .\n")
        f.write("@prefix wnid:    <https://en-word.net/id/> .\n")
        f.write("@prefix dul:     <http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#> .\n")
        f.write("@prefix skos:    <http://www.w3.org/2004/02/skos/core#> .\n")
        f.write("@prefix dct:     <http://purl.org/dc/terms/> .\n")
        f.write("@prefix owl:     <http://www.w3.org/2002/07/owl#> .\n\n")
        f.write("<https://en-word.net/id/alignment/dulplus/phase4/v1>\n")
        f.write("    a owl:Ontology ;\n")
        f.write("    dct:title \"OEWN 2025 adjective+adverb → DULplus alignment (Phase 4)\" .\n\n")
        for oid in sorted(total_map):
            cls, rule, rationale = total_map[oid]
            # Use localname oewn-XXXXXXXX-p
            f.write(f"wnid:{oid.replace('oewn-', '')}\n")
            f.write(f"    skos:broadMatch {cls} ;\n")
            f.write(f"    dct:provenance \"phase4/{rule}\"")
            perts = synset_pertainyms.get(oid, [])
            if perts:
                rels = "; ".join([
                    f"dct:relation wnid:{p['ref_synset'].replace('oewn-', '')}"
                    for p in perts if p["ref_synset"]
                ])
                if rels:
                    f.write(" ;\n    ")
                    f.write(rels.replace("; ", " ;\n    "))
            f.write(" .\n\n")
    print(f"      wrote {out_ttl}", flush=True)

    # Output 3: update master TSV (append adj+adv rows)
    master_rows = []
    with open(MASTER_TSV) as f:
        master_rows = list(csv.DictReader(f, delimiter="\t"))
    existing_ids = {r["oewn_id"] for r in master_rows}

    new_master = os.path.join(OUT_DIR, "oewn-dulplus-master.tsv")
    with open(new_master, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["oewn_id", "pos", "dulplus_class", "method",
                    "primary_lemma", "provenance", "gloss"])
        for r in master_rows:
            w.writerow([r["oewn_id"], r["pos"], r["dulplus_class"], r["method"],
                         r["primary_lemma"], r["provenance"], r["gloss"]])
        for oid in sorted(total_map):
            if oid in existing_ids: continue
            cls, rule, rationale = total_map[oid]
            meta = all_synset_meta.get(oid, {})
            pos = meta.get("partOfSpeech", "")
            members = meta.get("members") or []
            gloss = (meta.get("definition") or [""])[0] if meta.get("definition") else ""
            w.writerow([oid, pos, cls, f"phase4_{rule}",
                         members[0] if members else "",
                         rationale, gloss[:250]])
    print(f"      updated master {new_master}", flush=True)

    # ==================== Pass 5: stats ====================
    print("[7/7] Computing stats...", flush=True)
    by_rule = Counter(rule for _, (_, rule, _) in total_map.items())
    by_class = Counter(cls for _, (cls, _, _) in total_map.items())
    by_pos = Counter()
    for oid in total_map:
        meta = all_synset_meta.get(oid, {})
        p = meta.get("partOfSpeech", "?")
        by_pos[p] += 1

    # Overall universe count
    universe = Counter()
    for group, d in yamls.items():
        for sid, body in d.items():
            p = body.get("partOfSpeech") or sid.rsplit("-", 1)[-1]
            universe[p] += 1

    stats = {
        "mapped_total":            len(total_map),
        "by_pos":                  dict(by_pos),
        "oewn_universe_by_pos":    dict(universe),
        "coverage_pct_by_pos":     {p: round(100 * by_pos[p] / universe[p], 2)
                                     for p in universe if universe[p]},
        "by_rule":                 dict(by_rule.most_common()),
        "by_class":                dict(by_class.most_common()),
        "pertainym_annotations":   sum(1 for oid in total_map if synset_pertainyms.get(oid)),
    }
    with open(os.path.join(OUT_DIR, "phase4-full-stats.json"), "w") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
