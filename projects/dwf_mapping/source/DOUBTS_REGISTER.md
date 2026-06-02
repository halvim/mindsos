# Doubtful-Mappings Register — Overview

**Date:** 2026-04-22
**Deliverable:** `doubtful-mappings-register.tsv` (full, 10,650 rows) + `doubtful-mappings-priority.tsv` (top 2,000 rows by `priority_score`)
**Purpose:** Database of every synset where the pipeline had to break a tie between two or more defensible DULplus classes. Each row records the class chosen, the reason for the choice, the alternative, and the reason the alternative is also defensible. The `decision` and `decision_comment` columns are blank for you to fill in during review.

## 1. What a "doubt" is

A doubt is a synset where **more than one DULplus class is evidentially defensible** under the pipeline's rules, and the pipeline picked one. The picks are never arbitrary — they follow documented methodology — but the alternatives are often reasonable too. The register makes those trade-offs visible.

Each row answers: *"For this synset X, the pipeline mapped it to Y because of reason Z, but it could be mapped to A for reason B."*

## 2. Six doubt categories

| Code | Category | Count | What triggers it |
|---|---|---:|---|
| **C1** | `rule_conflict` | 1,228 | Phase 3.5 rule fired a different class than Phase 3 assigned (verb-specific) |
| **C2** | `hypernym_vs_gloss` | 4,230 | Mapping inherited from hypernym propagation, but synset's own gloss keywords suggest a different class |
| **C3** | `multiclass_framester` | 1,752 | Framester OntoWordNet originally assigned two DULplus classes; we collapsed to one |
| **C4** | `satellite_vs_gloss` | 205 | Adjective satellite inherited head's class, but its own gloss suggests a different class |
| **C5** | `pertainym_vs_referent` | 2,978 | Pertainym adjective mapped uniformly to `dul:Quality`, but its referent noun has a more specific class |
| **C6** | `gapfill_vs_gloss` | 257 | Phase 5-alt propagated class from hypernym, but gap-fill synset's own gloss suggests a different class |
| **Total** | | **10,650** | |

Class-distance distribution (0 = same class, 3 = disjoint DOLCE tops):

| Distance | Count |
|---:|---:|
| 1 (same DOLCE top group) | 2,340 |
| 2 (close but different groups) | 459 |
| 3 (disjoint DOLCE tops) | 7,851 |

## 3. Priority scoring

`priority_score = class_distance × method_weight × (1 + downstream_count / 10)`

- **class_distance** — higher when the two candidate classes are more semantically distant. A State↔Event doubt (distance 1) is less consequential than an Organism↔Description doubt (distance 3).
- **method_weight** — higher when the original method was less confident (a Tier 3 default deserves more scrutiny than a Tier 1 direct derivation).
- **downstream_count** — number of OEWN hyponyms that inherit from this synset; higher means the doubt propagates to more descendants.

### Priority tiers

| Tier | Score range | Count | Suggested review depth |
|---|---|---:|---|
| **Very high (top ~1%)** | ≥ 40 | 57 | Review every one; these have max impact |
| **High (1–10%)** | 20–40 | 71 | Review every one |
| **Medium (10–50%)** | 5–20 | 8,156 | Sample or batch |
| **Low** | < 5 | 2,366 | Can defer |

## 4. Honest caveat — C2 has a noise floor

The C2 (hypernym_vs_gloss) rules use keyword matching in glosses to suggest alternative classes. Keyword matching is noisy. Expect ~30–40% false positives in C2 of the form:

- `psychological feature` ("a feature of the mental life of a **living organism**") — flagged as `Description → Organism` because "organism" appears in the gloss, but the lemma is *feature*, not *organism*. The synset is correctly a Description.
- `liquid` ("a substance that is liquid at **room** temperature") — flagged as `Substance → Place` because "room" appears. The synset is correctly a Substance.
- `American` ("a native or inhabitant of a North American or Central American or South American **country**") — flagged as `Person → Place` because "country" appears. The synset is correctly a Person.
- `garment` ("an **article** of clothing") — flagged as `PhysicalObject → InformationRealization` because "article" can mean document. The synset is correctly a PhysicalObject.

**Interpretation:** C2 rows are "**suggested alternatives to consider**", not "**definitely wrong mappings**". When reviewing a C2 doubt, ask: *does the keyword in the gloss denote the synset itself or merely something related?* If related, `decision = accept_current`.

C1, C3, C5, C6 are cleaner signals:

- **C1** (Phase 3.5 rule conflicts) — ~90% true positives based on Phase 3.5 spot-checks.
- **C3** (Framester multi-class) — by-design doubts; every row is a real design choice.
- **C5** (pertainym) — by-design; every pertainym was uniformly mapped, so the register surfaces what a referent-informed alternative would look like.
- **C6** (gap-fill) — same keyword-heuristic noise as C2 but smaller scope (257 rows, all OEWN-native).

## 5. Top 20 priority doubts — exemplars

These are the register's highest-priority entries, showing what "really worth reviewing" looks like:

| Rank | Synset | POS | Lemma | Chosen → Alternative | Category | Notes |
|---:|---|---|---|---|---|---|
| 1 | `oewn-00023280-n` | n | psychological feature | Description → Organism | C2 | **likely false positive** (keyword "organism" in gloss refers to what the feature belongs to) |
| 2 | `oewn-14085287-n` | n | illness | Situation → Organism | C2 | **likely false positive** (same pattern) |
| 3 | `oewn-02382049-v` | v | interact | State → Action | C1 | **real** — gloss "act together" clearly an Action |
| 4 | `oewn-00109468-v` | v | change | State → Process | C1 | **real** — "undergo a change" is a Process |
| 5 | `oewn-05844071-n` | n | concept | InformationCollection → Concept | C2 | **real** — the lemma *is* "concept" |
| 6 | `oewn-03580409-n` | n | instrumentality | DesignedArtifact → Right | C3 | Framester's secondary class — design call |
| 7 | `oewn-14964524-n` | n | liquid | Substance → Place | C2 | **false positive** ("room temperature") |
| 8 | `oewn-00199979-n` | n | change of state | Situation → Action | C2 | **real** — gloss opens "the act of" |
| 9 | `oewn-02609706-v` | v | exist | Event → State | C1 | **real** — "have an existence" is a State |
| 10 | `oewn-00280679-n` | n | motion | Situation → Action | C2 | **real** — "the act of changing location" |
| 11 | `oewn-13350663-n` | n | assets | Right → FunctionalSubstance | C2 | debatable; could be Collection |
| 12 | `oewn-03423924-n` | n | garment | PhysicalObject → InformationRealization | C2 | **false positive** ("article of clothing") |
| 13 | `oewn-06735202-n` | n | statement | Topic → InformationRealization | C2 | **real** — "a message" strongly implies IR |
| 14 | `oewn-05778923-n` | n | thinking | InternalRepresentation → Process | C2 | **real** — "the process of using your mind" |
| 15 | `oewn-03410175-n` | n | furnishing | DesignedArtifact → Place | C2 | **false positive** (furniture is an artifact, "room" is in gloss) |
| 16 | `oewn-09757749-n` | n | American | Person → Place | C2 | **false positive** ("country" is in gloss) |
| 17 | `oewn-01835473-v` | v | move | State → Action | C1 | **real** — "move so as to change position" |
| 18 | `oewn-03410635-n` | n | furniture | DesignedArtifact → Place | C2 | **false positive** (same as 15) |
| 19 | `oewn-04112987-n` | n | room | DesignedArtifact → Place | C2 | **debatable** — a room arguably IS a place |
| 20 | `oewn-02208144-v` | v | have | Event → Action | C1 | questionable — possession is more stative |

Of the top 20, I count roughly **10 clear real-error candidates, 6 false positives, 4 debatable**. That ratio is consistent with C1 having the cleanest signal, C2 being noisiest, and C3/C5 being design calls rather than errors.

## 6. Suggested workflow

Three sensible approaches:

### Approach A — By category (recommended)

Work through the register one category at a time. Different categories need different mental models:

1. **C1 first** (1,228 rows, highest signal). Filter the priority TSV to `doubt_category == C1_rule_conflict`; work top-down by score. Expected accept rate on proposals: ~80%.
2. **C3 second** (1,752 rows, all design calls). Decide for each whether the collapsed-to class or Framester's secondary is preferred. This also informs Track G (multi-class design decision) from the review plan.
3. **C5 third** (2,978 rows, pertainym refinement). Consider whether to introduce a `dul:RelationalQuality` subclass or subclass pertainyms by referent. This is more of a schema-design decision than a per-row review.
4. **C2 fourth** (4,230 rows, noisy). Sample heavily, don't review exhaustively. If a sample shows ~40% false-positive rate, treat the remainder as optional spot-checks.
5. **C4 + C6** (462 rows combined). Small volume; can be reviewed in one sitting.

### Approach B — By priority score (simpler)

Open `doubtful-mappings-priority.tsv` (the top 2,000 rows by score) in a spreadsheet. Work top-down. Stop when you hit your time budget. This gives you the highest-impact decisions regardless of category.

### Approach C — By impact (biggest changes first)

Filter by `class_distance = 3` (disjoint DOLCE tops) and `downstream_count > 50`. These are the decisions where changing your mind flips both the synset's ontological category and dozens of descendants. ~500 rows.

## 7. How decisions flow back to the alignment

Every row has a `decision` column. Valid values:

- `accept_current` — keep the chosen class.
- `accept_proposed` — adopt the alternative class.
- `other:<class>` — neither was right; you prefer a different class (free-text).
- `defer` — revisit later.

When you're done (or at any checkpoint), run `apply_decisions.py` (to be written) which reads the register's `decision` column and regenerates `release-v2/` with the accepted revisions applied, including re-propagation from any corrected hypernym anchors.

## 8. Relationship to other review artefacts

The doubtful-mappings register **subsumes** several earlier review queues:

- `phase2-topmapping-review.tsv` (82 flagged Phase 2 nouns) → the subset where `doubt_category = C2_hypernym_vs_gloss OR C1_rule_conflict` AND `method = phase1_topmapping`.
- `phase3_5-verb-review.tsv` (1,228 flagged verbs) → exactly the C1 category.
- `phase5-disjoint-pairs.tsv` (516 hypernym violations) → partially covered by C2.

The register is a unified view across the pipeline. You can still work from the per-phase queues if you prefer smaller surfaces, but the register is the single source of truth.

## 9. Files

- [`doubtful-mappings-register.tsv`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/doubtful-mappings-register.tsv) — 10,650 rows, the full register.
- [`doubtful-mappings-priority.tsv`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/doubtful-mappings-priority.tsv) — top 2,000 rows by priority score.
- [`doubtful-register-stats.json`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/doubtful-register-stats.json) — machine-readable counts.
- [`build_doubtful_register.py`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/build_doubtful_register.py) — the script that produced all of the above.

## 10. Recommendation for "most important ones to review first"

Based on the top-20 exemplars above, the **concrete list of ~57 very-high-priority doubts** is a reasonable "review first" target:

- They're score ≥ 40 — each has large class-distance × high downstream count.
- Filter the priority TSV to `priority_score >= 40` for the exact list.
- Expected time: ~2–3 minutes per doubt × 57 = ~2–3 hours of focused review.
- Expected outcome: correcting even the real ~30 of them (half are C2 false positives) revises hundreds of descendants via re-propagation.

If that's too much, the **top 20** alone yields a disproportionate share of the impact. The pattern is: a few dozen parent synsets in the top-decile anchor thousands of downstream inheritances; fixing the parents fixes the descendants automatically.
