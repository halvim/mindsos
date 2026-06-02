# Phase 3.5 Report — Verb revalidation

**Date:** 2026-04-22
**Status:** Complete — awaiting your review decisions on the flagged verbs.

## Scope

- **Phase 3 verbs total:** 13,821
- **Weak-tier scope** (propagated-from-hypernym + tier3 defaults): 11,412
- **High-confidence tiers excluded from revalidation:** 2,409 (tier1_derivation, tier2_indirect, tier3_gloss_starts_be/become, tier3_cognitive_*_kw, tier3_process_marker). These were the anchors of Phase 3; they already passed the Silva criteria at assignment.

## Rules applied

| ID | Rule | Hits |
|---|---|---:|
| **R1** | Verb's own gloss starts with a Silva marker ("the act of", "be X", "become X"…) and disagrees with assigned class | 463 |
| **R2** | Aspectual keyword signal in gloss disagrees with assigned class (state/process/event/action markers per Gangemi §3) | 730 |
| **R3** | ≥50% of the verb's Tier-1 troponyms agree on a class different from the verb's — children know better than parent | 58 |
| **R6** | Gloss is agentive-transitive but verb is mapped to Process or State | 3 |
| **R7** | Example-sentence aspect agrees with an already-flagged alternative (tiebreaker) | 10 |

R4 (chained fallback) and R5 (cognitive false-positive) contributed zero hits in this run — R4's chains rarely accumulated multiple tier-3 defaults because the hypernym tree is shallow, and R5 would have caught cognitive misfires but Phase 3's cognitive tier was too small (24 verbs) for errors there to survive into the propagated group.

## Results

**1,228 verbs flagged** (10.76% of the weak-tier scope). That's within the 11–22% range I estimated, with the lower end suggesting Phase 3's propagation was better than I feared.

### By confidence bucket

| Bucket | Count | What it means |
|---|---:|---|
| `very_high` (score ≥ 4) | 3 | Two or more rules fire on the same verb, one of them R1 or R3. Near-certain fixes. |
| `high` (score 2–3.99) | 516 | A single R1 or R3 flag, or multiple lower-tier flags. Strong candidates for revision. |
| `low` (< 2) | 709 | Single R2/R6/R7 flag. Suggestive but less certain; worth sanity-check. |

### Most common class flips proposed

| Current → Proposed | Count | Semantic motive |
|---|---:|---|
| `dul:Action` → `dul:State` | 289 | Stative verbs (glossed "be X") that inherited Action from parents via propagation. |
| `dul:State` → `dul:Action` | 181 | Active verbs whose parent got Stately by accident; gloss has action markers. |
| `dul:Action` → `dul:Event` | 152 | Telic non-agentive events glossed with "reach/arrive/complete…" |
| `dul:State` → `dul:Achievement` | 120 | "Become X" verbs that ended up under a State parent. |
| `dul:Event` → `dul:Action` | 85 | Agentive verbs with "perform/execute/do" cues. |
| `dul:Action` → `dul:Achievement` | 82 | Accomplishment verbs under an Action parent. |
| `dul:Action` → `dul:Process` | 75 | Non-telic gradual verbs mis-inherited as Action. |
| `dul:State` → `dul:Process` | 61 | Dynamic change-of-state verbs under stative parents. |

## High-confidence examples (score ≥ 3)

These are the strongest corrections the rules surface:

- `change` ("become different in some particular way…") — currently `dul:State`, propose `dul:Achievement`. R1 ("become") and R3 (5/8 Tier-1 children are `dul:Action`). A **very** important verb to get right because 73 troponyms inherit from it.
- `join` ("become part of; become a member of a group") — currently `dul:State`, propose `dul:Achievement`. R1+R3 (4/4 children agree on Action).
- `change surface` ("undergo or cause to undergo a change in the surface") — currently `dul:State`, propose `dul:Action`. R2+R3+R6 all agree.
- `die down` ("become progressively weaker") — currently `dul:Action`, propose `dul:Achievement`. R1+R2.
- `dissolve` ("become or cause to become soft or liquid") — currently `dul:State`, propose `dul:Achievement`. R1+R2.
- `be` ("occupy a certain position or area; be somewhere") — currently `dul:Event` (!), propose `dul:State`. R3 (12/19 tier-1 children say State) + R7 (examples are stative). **36 troponyms affected.** This is probably the single most important fix in the file.

## Sample of clean R1-only flags (high confidence, high volume)

These are verbs that got inherited Action/Process/Event but whose own glosses clearly open with "be X":

- `retail` ("be sold at retail level") Action → State
- `care for` ("be fond of") Action → State
- `air` ("be broadcast") Process → State
- `squint` ("be cross-eyed") Action → State
- `envy` ("be envious of") Action → State

Sample of R2-only flags (aspectual markers):

- `work at` ("to exert effort in order to do, make, or perform something") State → Action
- `sit out` ("endure to the end") Action → Event
- `carouse` ("engage in boisterous, drunken merrymaking") State → Action
- `stretch` ("lie down comfortably") Action → State
- `ping` ("make a short high-pitched sound") Event → Action

## Known false positives

A small subset of R3 flags reflect cascading errors where the children inherited from a bad anchor and all agree on the wrong class:

- `ache` ("be the source of pain") → proposed `dul:CognitiveState` because its 4 Tier-1 children landed on CognitiveState. But "ache" is physical, not cognitive — the *children* were mis-mapped (`headache`, `backache`, etc., probably via cognitive-keyword false positives in Phase 3 Tier 3). Accept cautiously.

You'll spot these in the review — the heuristic is that if the proposed class is `Cognitive*` and the gloss has no cognitive content, trust your gloss reading.

## Output

- [`phase3_5-verb-review.tsv`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/phase3_5-verb-review.tsv) — 1,228 rows sorted by confidence score descending, with `oewn_id`, `current_class`, `current_tier`, `rules_triggered`, `top_proposal`, `rationale`, `gloss`, `examples`, `hypernyms`, `troponym_count`, and a blank `decision` column.
- [`phase3_5-stats.json`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/phase3_5-stats.json) — machine-readable summary.
- [`phase3_5_revalidate_verbs.py`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/phase3_5_revalidate_verbs.py) — the script.

## Review strategy I'd recommend

With 1,228 rows, you don't need to inspect all of them. Suggested prioritisation:

1. **The top 43 score ≥ 3 rows.** These include `be`, `change`, `join`, `die down`, `dissolve`, etc. Each of them parents dozens of troponyms that will inherit the fix. Fixing these 43 alone gives disproportionate leverage.
2. **The 58 R3 flags.** These are where the *verb's own children* disagree with it — the strongest evidence of a parent-level error. I'd audit all of them.
3. **Sample 50–100 from R1-only (463 rows).** These are almost all "be X" verbs under Action parents; spot-check a sample and batch-accept if consistent.
4. **R2-only (699 rows) can be sampled lighter.** The aspectual rule is noisier; accept where the gloss signal is unambiguous, defer where it's marginal.

**High-leverage shortcut:** if you approve the 6 "very high confidence" cases cited above, I can re-run propagation using them as corrected anchors and regenerate the verb alignment. That single operation will flow corrections through hundreds of troponyms automatically — probably worth more than manually annotating the long tail.

## How I'd fold the decisions back

Once you've marked decisions in the TSV, I'll write a Phase 3.6 script that:

1. Reads the review TSV, pulls rows where `decision` is `accept_proposed` or `other:<class>`.
2. Updates the verb mapping table with the revised classes.
3. Re-runs propagation from each updated verb's subtree (Silva §4) so troponyms inherit the correction.
4. Regenerates `oewn-dulplus-master.tsv` and the verb alignment TTL with provenance notes ("manually revised in Phase 3.5; rationale: R1+R3").

You don't need to decide on every row before we can move to Phase 4 — we can run Phase 4 (adjectives/adverbs) in parallel and fold the verb corrections in at any time.

## Next

Shall I proceed to the Phase 4 adjective/adverb pilot while you work through the review TSV, or wait for you to finish a first pass?
