# Phase 5 Report — Verification & quality gates

**Date:** 2026-04-22
**Status:** Complete — four consistency checks + 200-synset audit sample delivered.

## What Phase 5 did

Ran four automated consistency checks on the 102,976-row alignment, using DLP3971 (DOLCE-Lite-Plus library, 207 classes, 36 disjointness axioms) as the ground-truth ontology. Output is a verification report you can read, plus TSVs of the specific issues for optional hand-review.

## Overall verdict

**The alignment is structurally sound.** 98.5% of the 81,802 hypernym/hyponym pairs checked are DOLCE-consistent. The issues that surfaced are either (a) a small number of genuine classification errors (~516 pairs), (b) legitimate multi-class assignments inherited from Framester's original data (~791 synsets), or (c) limitations of the simplified DULplus↔DOLCE-Lite translation layer used for the check (not errors in the alignment itself).

## Check 1 — Class existence & distribution

**Status: ✅ clean (2 minor items to note)**

- 64 distinct DULplus classes used across 102,976 assignments.
- 62 map cleanly onto DOLCE-Lite categories via the DUL→DOLCE translation table.
- 2 outliers:
  - **`owl:Thing`** — 13 uses. These are the most abstract synsets where Framester couldn't commit to a specific class: `thing`, `causal agent`, `change` (the abstract sense), `pacifier`, `motor` (as "nonspecific agent"), etc. Acceptable default; you may want to replace with `dul:Entity` for stylistic consistency.
  - **`Supplements.owl#GeographicalFeature`** — 180 uses. This is a legitimate DOLCE `Supplements.owl` class (used for geographical entities), just not in my DUL→DOLCE translation table. Cosmetic; a one-line addition to the table would catch it in future runs.

Top 10 classes by usage (gives a shape-of-the-alignment view):

| Class | Count | % of alignment |
|---|---:|---:|
| `dul:Quality` | 19,939 | 19.4% |
| `dul:Action` | 14,905 | 14.5% |
| `dul:Organism` | 8,823 | 8.6% |
| `dul:DesignedArtifact` | 6,923 | 6.7% |
| `dul:Person` | 6,806 | 6.6% |
| `dul:Situation` | 5,318 | 5.2% |
| `dul:FunctionalSubstance` | 4,768 | 4.6% |
| `dul:Region` | 3,330 | 3.2% |
| `dul:InformationRealization` | 2,894 | 2.8% |
| `dul:BiologicalObject` | 2,333 | 2.3% |

## Check 2 — Within-synset disjointness

**Status: ⚠️ 791 cases, most are legitimate Framester multi-class assignments**

Found 791 synsets with two or more DULplus classes that map to DOLCE-Lite *disjoint* categories (e.g., `perdurant ⊥ concept`).

Almost all these come from Phase 1's source data — Framester's `own2dulplus.ttl` often assigns the same synset to both an event-type class AND a concept-type class, reflecting the fact that one WordNet synset can denote both the action and the topic it's about (e.g., "lecture" = the act AND the topic). The master alignment already resolves these by picking one per synset (the `topmapping > propagated > inferred` priority from Phase 1), so they don't appear as contradictions in the final deliverable — but if you want to preserve the multi-class information somewhere, we'd need to decide how.

Example of the most common pattern (`ontopic:Topic` ⊥ `dul:Action`): Framester tagged synsets like `oewn-00101073-n` ("activity that has been engaged in") as both a Topic (it's a subject of discourse) and an Action (it's an activity). DOLCE would force a choice; we made one.

## Check 3 — Hypernym-hyponym subsumption consistency

**Status: ✅ 98.5% compatible**

| Outcome | Count | % |
|---|---:|---:|
| Same DULplus class on both sides | 79,233 | 96.9% |
| Child is a DOLCE-Lite subclass of parent | 33 | <0.1% |
| Classes differ but map to same DOLCE-Lite category | 1,312 | 1.6% |
| **Compatible total** | **80,578** | **98.5%** |
| **Disjoint violations** | **516** | **0.63%** |
| Unrelated (too distant in DOLCE to decide) | 653 | 0.8% |
| **Pairs checked** | **81,802** | — |

The 516 disjoint violations are where a child synset's class contradicts its parent's under DOLCE. Worth a closer look — these are candidate real errors.

### Top violation patterns

| Parent class | Child class | Count |
|---|---|---:|
| `dul:DesignedArtifact` | `dul:FunctionalSubstance` | 24 |
| `dul:PhysicalPlace` | `dul:Place` | 17 |
| `dul:BiologicalObject` | `dul:FunctionalSubstance` | 16 |
| `dul:PhysicalObject` | `dul:FunctionalSubstance` | 13 |
| `dul:SpaceRegion` | `Supplements#DependentPlace` | 13 |
| `dul:DesignedArtifact` | `dul:InformationRealization` | 12 |
| `dul:DesignedArtifact` | `Supplements#DependentPart` | 11 |
| `dul:Substance` | `dul:Quality` | 10 |
| `dul:InformationObject` | `dul:Place` | 10 |

**Interpretation:**

- `DesignedArtifact → FunctionalSubstance` (24): These are legitimate subtype relationships where the child is a substance used in or by an artifact (e.g., "gasoline" under "fuel" under some artifact class). DULplus keeps these disjoint but WordNet's hypernymy conflates them. This is a documented issue — Gangemi's R5 in the 2003 paper mentions this pattern.
- `PhysicalPlace → Place` (17): **false positive from my translation layer.** My DUL→DOLCE map puts `dul:Place`=region and `dul:PhysicalPlace`=physical-object, which are disjoint in DOLCE, but in DULplus they have a `locatedIn` relationship rather than strict disjointness. The alignment itself is fine here.
- `Substance → Quality` (10): Likely real errors where a material (water, dust) was mapped to Quality when it should be Amount.
- `InformationObject → Place` (10): Borderline — "a place to store information" being a child of an information concept.

Full list in [`phase5-disjoint-pairs.tsv`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/phase5-disjoint-pairs.tsv) (first 500 rows).

## Check 4 — 200-synset stratified audit

**Status: ✅ sample written — ready for your review if wanted**

Sampled 200 synsets stratified across POS and method:

- 60 nouns (mix of topmapping / propagated / inferred from Phase 1)
- 50 verbs (mix of Tier 1 / Tier 2 / propagated / Tier 3 from Phase 3)
- 60 adjectives (mix of adj.all heads / satellites / adj.pert)
- 30 adverbs (mix of manner / temporal / spatial / default)

Delivered as [`phase5-audit-sample.tsv`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/phase5-audit-sample.tsv) with a blank `manual_agreement` column. If you want a formal precision estimate, spend an hour going down the list and marking `yes/no/debatable`; I can then compute precision/recall numbers. Not required for the alignment to be usable — the spot-checks in Phases 1, 3, and 4 reports already showed ~90–95% quality — but it's the standard evaluation artefact for this kind of work.

## Diff — Phase 3 → Phase 3.5 impact

If you accept all Phase 3.5 proposals:

- **1,228 verbs would have their class changed**, representing 8.88% of the verb alignment.
- Main shifts: `dul:Action → dul:State` (289), `dul:State → dul:Action` (181), `dul:Action → dul:Event` (152), `dul:State → dul:Achievement` (120). These are the rebalancings the Silva/Gangemi rules suggest — most are the propagation of `be`, `change`, `join` fixes discussed in the Phase 3.5 report.

Whether to apply these automatically, manually, or selectively is still your call.

## Outputs from Phase 5

| File | Contents |
|---|---|
| [`phase5-audit-sample.tsv`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/phase5-audit-sample.tsv) | 200 random stratified synsets with blank `manual_agreement` column for hand-audit. |
| [`phase5-disjoint-pairs.tsv`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/phase5-disjoint-pairs.tsv) | Top 500 hypernym pairs with disjoint classes (of 516 total). |
| [`phase5-unrelated-pairs.tsv`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/phase5-unrelated-pairs.tsv) | Top 500 hypernym pairs where the DUL→DOLCE map can't decide (653 total). |
| [`phase5-stats.json`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/phase5-stats.json) | Machine-readable summary. |
| [`phase5_verify.py`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/phase5_verify.py) | Reproducible script. |

## Summary of the quality picture

Combining all phases:

| Metric | Value |
|---|---|
| Total synsets mapped | 102,976 / 107,518 (95.77%) |
| Distinct DULplus classes used | 64 |
| Hypernym-hyponym consistency rate | **98.5%** |
| Within-synset disjointness (master TSV, one class per synset) | 0 violations |
| Pilot/spot-check estimated precision | 90–96% across POS |
| Flagged for Phase 3.5 revalidation (verbs) | 1,228 (10.8% of verb weak-tier scope) |
| Flagged for Phase 2 revalidation (noun topmappings) | 82 (9.8% of topmapping layer) |

This is a defensible alignment. The remaining issues are:

1. **4,542 unmapped nouns** (OEWN-native synsets added/renamed since PWN 3.0) — Phase 5-alt can fill these.
2. **516 hypernym violations** — worth targeted review; maybe half are my translation-layer artefacts, the other half likely real.
3. **Phase 2 + Phase 3.5 review queues** — waiting for your sign-off decisions.

## What's next

Original plan has two items remaining:

- **Phase 5-alt — Gap-fill the 4,542 unmapped nouns** via OEWN hypernym propagation and the Phase 2-style heuristics we already have.
- **Phase 6 — Final deliverables**:
  - Master alignment Turtle in *both* DULplus (primary) and DOLCE-Lite (derived) serializations
  - A consolidated CSV for spreadsheet-level editing
  - `METHODOLOGY.md` traceable to the two reference papers
  - A release-ready bundle

My recommendation is to do Phase 5-alt (gap-fill) and Phase 6 back-to-back: the gap-fill produces the final 100% coverage (or near it), then Phase 6 packages everything into a release. Both together are ~1 substantial script + a README.

Shall I proceed with Phase 5-alt + Phase 6 as a combined push?
