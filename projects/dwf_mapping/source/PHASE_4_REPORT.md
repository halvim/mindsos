# Phase 4 Report — Adjective + Adverb full scale-up

**Date:** 2026-04-22
**Status:** Complete — 100% coverage of all OEWN adjective + adverb synsets.

## What was done

Applied the approved rule set (a=idiom guard R0, b=DULplus coarse targets, c=pertainym annotations) to all 21,833 adjective and adverb synsets in Open English WordNet 2025. This completes the POS coverage of the alignment — **every adjective, satellite, and adverb in OEWN now has a DULplus class.**

## Results

### Coverage

| POS | Mapped | OEWN Universe | Coverage |
|---|---:|---:|---:|
| Adjective head (`a`) | 7,502 | 7,502 | **100%** |
| Adjective satellite (`s`) | 10,717 | 10,717 | **100%** |
| Adverb (`r`) | 3,614 | 3,614 | **100%** |
| **Phase 4 total** | **21,833** | 21,833 | **100%** |

### Rule distribution

| Rule | Hits | % of Phase 4 |
|---|---:|---:|
| A1 — satellite inherits head | 10,717 | 49.1% |
| A2 — pertainym (adj.pert) default | 3,663 | 16.8% |
| A5 — adj.all head default | 3,562 | 16.3% |
| A4 — physical-attribute keyword | 217 | 1.0% |
| A3 — participial (adj.ppl) default | 60 | 0.3% |
| R1_adv — manner adverb | 1,336 | 6.1% |
| R7_adv — default | 1,764 | 8.1% |
| R3_adv — spatial | 185 | 0.8% |
| R5_adv — degree | 174 | 0.8% |
| R2_adv — temporal | 108 | 0.5% |
| R4_adv — frequency | 39 | 0.2% |
| R6_adv — modal | 8 | 0.04% |

### DULplus class distribution

| Class | Count |
|---|---:|
| `dul:Quality` | 16,818 |
| `dul:Region` | 3,313 |
| `dul:PhysicalAttribute` | 1,401 |
| `dul:SpaceRegion` | 185 |
| `dul:TimeInterval` | 108 |
| `dul:Abstract` | 8 |

### Pertainym annotations

**5,601 adjective synsets carry `dct:relation` annotations** pointing to their referent synset (the noun/concept the adjective is "of or relating to"). Examples:

- `putrid → dul:Quality ; dct:relation → putrefaction`
- `gestational → dul:Quality ; dct:relation → pregnancy`
- `infernal → dul:Quality ; dct:relation → hell`
- `frugally → dul:Region ; dct:relation → economical`
- `stemmatic → dul:Quality ; dct:relation → stemma`

This preserves the semantic relationship that would otherwise be lost in a pure class-assignment format — it's the "annotation" approach you approved (c=annotation).

### R0 idiom guard validation

The guard worked as intended. Verified on the pilot's false-positive case:

- `at a loss` (gloss: *"below cost"*) — pilot classified as `dul:SpaceRegion` (false positive on "below"). Full scale-up correctly classifies as `dul:Region` via R7 default because the guard detected the economic idiom (`cost` keyword near the spatial marker).

Net effect on spatial rule hit rate: 185 (full) vs 190 (projected without guard) — 5 idiomatic false positives averted.

## Overall alignment status (all phases to date)

| POS | Mapped | OEWN Universe | Coverage | Source |
|---|---:|---:|---:|---|
| Noun (`n`) | 67,322 | 71,864 | 93.68% | Phase 1 (OntoWordNet migration) |
| Verb (`v`) | 13,821 | 13,821 | 100% | Phase 3 (Silva 2018 three-tier) |
| Adjective (`a`) | 7,502 | 7,502 | 100% | Phase 4 (novel) |
| Adjective-sat (`s`) | 10,717 | 10,717 | 100% | Phase 4 (novel) |
| Adverb (`r`) | 3,614 | 3,614 | 100% | Phase 4 (novel) |
| **Total** | **102,976** | **107,518** | **95.77%** | — |

The remaining 4,542 unmapped synsets are all nouns where OEWN added, renamed, or merged synsets since PWN 3.0 — out of scope for the legacy migration, and candidates for Phase 5 gap-filling.

## Deliverables

| File | Contents |
|---|---|
| [`phase4-adj-adv-alignment.tsv`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/phase4-adj-adv-alignment.tsv) | 21,833 adj/adv mappings with rule, rationale, gloss, pertainym lemmas. |
| [`phase4-adj-adv-alignment.ttl`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/phase4-adj-adv-alignment.ttl) | Turtle with `skos:broadMatch` + `dct:provenance` + `dct:relation` for pertainyms. |
| [`oewn-dulplus-master.tsv`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/oewn-dulplus-master.tsv) | **Updated combined alignment: 102,976 rows** across all four POS. This is now the single authoritative file for the whole alignment. |
| [`phase4-full-stats.json`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/phase4-full-stats.json) | Machine-readable stats. |
| [`phase4_full_adj_adv.py`](computer:///Users/henriquealvim/Documents/Claude/Projects/Dulce - WordNet - FrameNet Mapping/phase4_full_adj_adv.py) | Reproducible script. |

## Known minor issues

1. **Duplicate `dct:relation` in TTL** — when an adjective has multiple senses all pointing to the same pertainym target, the TTL emits the annotation multiple times. Cosmetic; doesn't change semantics. Fix is one-line dedup; I can do it in Phase 5 clean-up.
2. **Pertainym annotation coverage** is 5,601 of 7,248 sense-level pertainym links — some lemmas have sense-level links to senses that resolve to the same target but get de-duplicated at synset level. This is correct behaviour.
3. **`at a loss` — the adjective sense** ("filled with bewilderment") correctly stays as `dul:Quality` inherited via satellite; only the adverb sense was the idiom case.

## Where we are in the original plan

From `EXPANSION_PLAN.md` §5 phasing:

- ✅ Phase 1 — ID bridge (Framester → OEWN)
- ✅ Phase 2 — Top-200 revalidation (840 synsets reviewed, 82 flagged)
- ✅ Phase 3 — Verb mapping via Silva 2018
- ✅ Phase 3.5 — Verb revalidation (1,228 flagged for your review)
- ✅ Phase 4 — Adjective + adverb full coverage (this)
- ⏳ Phase 5 — Verification & quality gates (OWL reasoner pass, diff vs. OntoWordNet, random-sample audit)
- ⏳ Phase 6 — Final deliverables (master Turtle in both DULplus and DOLCE-Lite forms, methodology doc)

## What's next

Two reasonable directions:

**(A) Phase 5 — Verification & quality gates.** Load `DOLCE-Lite.owl` + `DLP3971` + the 102,976-row alignment into an OWL reasoner (HermiT or ELK via `owlready2`), detect contradictions, run a 200-synset random-sample audit, and diff our coverage against the original OntoWordNet to enumerate agreements and divergences. This is the QA step before freezing the alignment.

**(B) Phase 5 alt — Gap-fill the 4,542 unmapped nouns.** These are OEWN-native synsets (added or renamed since PWN 3.0) that had no legacy mapping to migrate. We could propagate from their OEWN hypernym chain (where the hypernym *is* mapped), or apply the Phase 2-style noun rules we already have.

My recommendation is **(A) first, then (B)**: knowing the alignment is consistent (no contradictions, coverage quantified) is more valuable than marginal coverage gain before you review. Gap-filling can happen last and doesn't change the majority answer.

Which do you want — Phase 5 verification next, or fill the noun gaps first?
