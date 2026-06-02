#!/usr/bin/env python3
"""
Claude's review decisions for the 57 top-priority doubts (score >= 40).

Each decision is one of:
    accept_current   — keep the chosen_class
    accept_proposed  — adopt the alternative_class
    other:<class>    — neither; use a different class (rare)

Produces: decisions-top57.tsv (feeds apply_decisions.py)
"""
import csv, os

OUT_DIR = "/sessions/exciting-pensive-rubin/mnt/outputs"
REGISTER = os.path.join(OUT_DIR, "doubtful-mappings-register.tsv")
OUT_TSV  = os.path.join(OUT_DIR, "decisions-top57.tsv")

# Decisions keyed by doubt_id. Each entry = (decision, rationale).
# Rationale is my own reasoning, for auditability.
DECISIONS = {
    # --- Verb C1 rule conflicts (clear perdurant re-classifications) ---
    "D-000021": ("accept_proposed",
                 "interact: 'act together' is clearly Action. 8/9 Tier-1 children already Action."),
    "D-000626": ("accept_proposed",
                 "change: 'undergo a change; become different' — 'undergo' is the Process marker in Gangemi §3."),
    "D-000497": ("accept_proposed",
                 "exist: 'have an existence' is the canonical State. 33/42 Tier-1 children agree."),
    "D-000023": ("accept_proposed",
                 "move: 'move so as to change position, perform a nontranslational motion' — 'perform' is Action marker. 24/25 children agree."),
    "D-000502": ("accept_proposed",
                 "have: 'have or possess' is borderline, but 5/9 Tier-1 children are Action (possession acts). Accept Action over tier3_default_event."),
    "D-000478": ("accept_proposed",
                 "act: lemma literally 'act'; gloss 'perform an action'. 67/71 children are Action. The tier1_derivation picked State in error."),
    "D-000027": ("accept_proposed",
                 "be: 'occupy a certain position' is a State. 12/19 Tier-1 children agree; examples are stative. The single most important fix."),
    "D-000018": ("accept_proposed",
                 "change state: 'undergo a transformation' — 'undergo' marker → Process."),
    "D-000019": ("accept_proposed",
                 "cover: 'provide with a covering' — 'provide' is agentive, Action. 4/4 children agree."),
    "D-000487": ("accept_proposed",
                 "change integrity: 'change in physical make-up' — transitive change verb. 8/15 kids Action. Accept Action."),
    "D-000518": ("accept_proposed",
                 "treat: 'interact in a certain way' — if interact is Action, treat is Action too. 3/3 kids agree."),
    "D-000510": ("accept_proposed",
                 "react: 'show a response or reaction' — agentive. 4/4 children agree."),
    "D-000025": ("accept_proposed",
                 "sound: 'make a certain noise or sound' — 'make' is action marker, so Action over tier3_default_event."),

    # --- Noun C2 "the act of" → Action (Silva / Gangemi §3 gloss markers) ---
    "D-001303": ("accept_proposed",
                 "change of state: gloss opens 'the act of changing something into something different'. Clear Action, not Situation."),
    "D-001437": ("accept_proposed",
                 "motion: gloss opens 'the act of changing location from one place to another'. Action."),
    "D-001612": ("accept_proposed",
                 "change of integrity: gloss opens 'the act of changing the unity or wholeness'. Action."),
    "D-001829": ("accept_proposed",
                 "transgression: 'the act of transgressing'. Action."),
    "D-001316": ("accept_proposed",
                 "termination: 'the act of ending something'. Action."),
    "D-001550": ("accept_proposed",
                 "change of magnitude: 'the act of changing the amount or size'. Action."),
    "D-001454": ("accept_proposed",
                 "travel: 'the act of going from one place to another'. Action."),
    "D-001373": ("accept_proposed",
                 "improvement: 'the act of improving something'. Action."),
    "D-001637": ("accept_proposed",
                 "separation: 'the act of dividing or disconnecting'. Action."),
    "D-001551": ("accept_proposed",
                 "decrease: 'the act of decreasing or reducing something'. Action."),
    "D-001584": ("accept_proposed",
                 "increase: 'the act of increasing something'. Action."),

    # --- C2 false positives (gloss keyword is NOT the synset's denotation) ---
    "D-001230": ("accept_current",
                 "psychological feature: 'a feature of mental life of a living organism'. 'organism' refers to what the feature is OF, not the feature itself. Description is correct. False positive by keyword match."),
    "D-004704": ("accept_current",
                 "illness: 'impairment of physiological function affecting an organism'. Not an organism. Situation is defensible though 'State' might be marginally better; keep current."),
    "D-005119": ("accept_current",
                 "liquid: 'a substance that is liquid at room temperature'. 'room' is context, not denotation. Substance is correct."),
    "D-002453": ("accept_current",
                 "garment: 'an article of clothing'. 'article' here means item, not document. PhysicalObject is correct."),
    "D-002441": ("accept_current",
                 "furnishing: instrumentalities that make a home livable. It IS an artifact, not a place. DesignedArtifact correct."),
    "D-003947": ("accept_current",
                 "American: 'a native or inhabitant of...country'. Person is the synset itself; 'country' is context. Person correct."),
    "D-002442": ("accept_current",
                 "furniture: same reasoning as furnishing."),
    "D-004307": ("accept_current",
                 "assets: 'anything of material value...owned by a person or company'. Right captures the ownership/legal aspect, which FunctionalSubstance misses. Keep Right."),
    "D-002403": ("accept_proposed",
                 "facility: 'a building OR PLACE that provides a particular service'. Gloss explicitly says 'place'. Place is more accurate than PhysicalObject."),
    "D-005275": ("accept_current",
                 "wind: 'air moving...from high to low pressure'. Not a place. Situation is imperfect (Process might fit better), but Place is wrong. Keep current."),
    "D-010467": ("accept_current",
                 "wind (C6 duplicate of D-005275): same decision."),
    "D-003721": ("accept_current",
                 "series: 'similar things placed in order'. Collection captures the grouping. Event is partial (only the 'happening' reading). Keep Collection."),
    "D-004321": ("accept_current",
                 "medium of exchange: 'standard of value in a country or region'. Amount captures the value-quantity sense; Place is false positive (country is contextual)."),
    "D-002772": ("accept_current",
                 "structural member: 'support that is a constituent part of any structure or building'. It's a component, not a place. DesignedArtifact correct."),
    "D-004332": ("accept_current",
                 "currency: 'the metal or paper medium of exchange'. Physical/quantitative. Amount > InformationRealization (currency is MONEY, not info about money)."),
    "D-002311": ("accept_current",
                 "component: 'an artifact that is one of the individual parts'. DependentPart captures the part-hood; Person false positive (relative-pronoun pattern hit 'that is one of'). Keep current."),
    "D-002120": ("accept_current",
                 "seabird: 'a bird that frequents coastal waters'. Organism; 'coastal waters' is habitat context. False positive."),
    "D-005245": ("accept_current",
                 "Chad (language family): 'family of Afroasiatic tonal languages'. InformationObject correct; Place would be confusing with the country Chad."),
    "D-010437": ("accept_current",
                 "Chad (C6 duplicate of D-005245): same decision."),

    # --- C2 real catches (accept proposed) ---
    "D-003103": ("accept_proposed",
                 "concept: 'an abstract or general idea'. Lemma IS concept; the Concept class is exact. InformationCollection was a Framester over-reach."),
    "D-003354": ("accept_proposed",
                 "statement: 'a message that is stated or declared'. InformationRealization is precise; Topic is a distant abstraction."),
    "D-003082": ("accept_proposed",
                 "thinking: 'the process of using your mind to consider'. Process opener is explicit. The chosen InternalRepresentation class was Framester-specific; Process is more foundational."),
    "D-002679": ("accept_proposed",
                 "room: 'an area within a building enclosed by walls and floor and ceiling'. It IS a place (spatial region inside an artifact). Place > DesignedArtifact."),
    "D-003320": ("accept_proposed",
                 "information: 'a message received and understood'. InformationRealization is the direct class; Topic is less precise."),
    "D-003058": ("accept_proposed",
                 "perception: 'the process of perceiving'. Process opener; Process is clearer than InternalRepresentation."),

    # --- C3 Framester multi-class calls ---
    "D-005859": ("accept_current",
                 "instrumentality: 'an artifact (that is instrumental...) for accomplishing some end'. Artifact is in gloss. DesignedArtifact > Right."),
    "D-006242": ("accept_current",
                 "Amerind (languages): 'any of the languages spoken by Amerindians'. Languages are information objects; Person is a different sense."),
    "D-006495": ("accept_current",
                 "beverage: 'any liquid suitable for drinking'. FunctionalSubstance captures the 'for drinking' function; Substance alone loses it."),
    "D-005506": ("accept_current",
                 "dancing: 'taking a series of rhythmical steps'. Action is the central sense; Topic is the discourse-subject abstraction."),
    "D-006282": ("accept_proposed",
                 "affair: 'a formal or official social gathering or ceremony'. Event captures the gathering-as-occasion sense better than a Collection of agents (which would emphasize the people, not the occasion)."),
    "D-006501": ("accept_current",
                 "alcohol: 'a liquor or brew containing alcohol as the active agent'. FunctionalSubstance captures the intoxicant function; Substance alone is less specific."),
    "D-005902": ("accept_current",
                 "piece of cloth: 'a separate part consisting of fabric'. It IS a physical object (cloth piece), not merely a dependent-part abstraction. DesignedArtifact more concrete."),
    "D-006286": ("accept_current",
                 "edible fruit: 'edible reproductive body of a seed plant'. BiologicalObject captures the plant-derived living origin; FunctionalSubstance misses this."),
}


def main():
    # Load the register
    with open(REGISTER) as f:
        reg = {r["doubt_id"]: r for r in csv.DictReader(f, delimiter="\t")}

    # Filter to top 57 (score >= 40)
    top57 = [r for r in reg.values() if float(r["priority_score"]) >= 40]
    top57.sort(key=lambda r: -float(r["priority_score"]))

    missing = []
    out_rows = []
    for r in top57:
        did = r["doubt_id"]
        if did in DECISIONS:
            decision, rationale = DECISIONS[did]
        else:
            decision, rationale = "", "NOT REVIEWED"
            missing.append(did)
        row = {
            **r,
            "decision":         decision,
            "decision_comment": rationale,
        }
        out_rows.append(row)

    # Write decisions TSV
    cols = list(out_rows[0].keys())
    with open(OUT_TSV, "w", newline="") as f:
        w = csv.DictWriter(f, delimiter="\t", fieldnames=cols)
        w.writeheader()
        w.writerows(out_rows)

    # Stats
    from collections import Counter
    dct = Counter(r["decision"] for r in out_rows)
    print(f"Total top57: {len(out_rows)}")
    print(f"Decisions: {dict(dct)}")
    if missing:
        print(f"MISSING reviews (unexpected): {len(missing)}: {missing}")
    else:
        print("All 57 doubts have decisions.")

    # Quick breakdown: how many synsets change class?
    n_change = sum(1 for r in out_rows if r["decision"] == "accept_proposed")
    n_keep   = sum(1 for r in out_rows if r["decision"] == "accept_current")
    print(f"\nImpact summary:")
    print(f"  Class change (accept_proposed): {n_change}")
    print(f"  Class keep   (accept_current):  {n_keep}")
    total_downstream = sum(int(r["downstream_count"]) for r in out_rows if r["decision"] == "accept_proposed")
    print(f"  Total downstream synsets affected: {total_downstream:,}")

if __name__ == "__main__":
    main()
