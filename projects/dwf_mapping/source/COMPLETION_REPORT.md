# Completion Report — OEWN ↔ DOLCE Alignment

**Date:** 2026-04-22
**Final version:** v3 (in `release-v3/`)
**Status:** Complete — every OEWN synset mapped, every doubt in the register reviewed.

## Journey summary

Starting from the two reference PDFs (Gangemi et al. 2003, Silva et al. 2018) + DOLCE-Lite.owl + english-wordnet-2025.ttl, I built:

1. **Macro-phase M1** — Noun backbone via OntoWordNet migration (Phases 1 + 2).
2. **Macro-phase M2** — Verb tier via Silva's three-tier method (Phases 3 + 3.5).
3. **Macro-phase M3** — Adjective + adverb extension (novel — Phase 4 pilot + full).
4. **Macro-phase M4** — Verification + gap-fill + release (Phases 5 + 5-alt + 6).
5. **Review** — Doubtful-mappings register built (Phase 6.5), top 57 hand-reviewed (Phase 7), full register systematically decided (Phase 8).

Total pipeline: **~10 scripts, ~2,500 lines of code, 107,518 synsets mapped, 10,650 doubts catalogued and decided.**

## Coverage

| POS | Mapped | OEWN | Coverage |
|---|---:|---:|---:|
| Noun (`n`) | 71,864 | 71,864 | 100% |
| Verb (`v`) | 13,821 | 13,821 | 100% |
| Adjective head (`a`) | 7,502 | 7,502 | 100% |
| Adjective satellite (`s`) | 10,717 | 10,717 | 100% |
| Adverb (`r`) | 3,614 | 3,614 | 100% |
| **Total** | **107,518** | **107,518** | **100%** |

## v3 class distribution (top 15)

| Class | Count |
|---|---:|
| `dul:Quality` | 20,035 |
| `dul:Action` | 17,476 |
| `dul:Organism` | 9,135 |
| `dul:DesignedArtifact` | 7,604 |
| `dul:Person` | 7,623 |
| `dul:Situation` | 4,647 |
| `dul:FunctionalSubstance` | 5,077 |
| `dul:Region` | 3,332 |
| `dul:InformationRealization` | 3,215 |
| `dul:BiologicalObject` | 2,581 |
| `dul:Process` | 1,964 |
| `dul:Amount` | 1,723 |
| `dul:PhysicalObject` | 1,706 |
| `dul:PhysicalAttribute` | 1,651 |
| `dul:Event` | 1,609 |

## Quality indicators

From Phase 5 verification on v3:

- **Within-synset disjointness conflicts:** 790 (all Framester-original multi-class assignments — by design, not errors).
- **Hypernym-hyponym compatibility:** 96.31% of 88,075 checkable pairs (1,205 violations now exposed as the next QA surface).
- **Distinct DULplus classes used:** 65.
- **Decisions in the register:** 10,650 (100% decided).
- **Precision estimate:** 90–96% per spot-checks across phases; formal measurement awaits the completion of `phase5v3-audit-sample.tsv` (200 stratified random synsets).

## The review process

The review was structured as a doubtful-mappings register with 6 categories:

| Category | Total | accept_proposed | accept_current |
|---|---:|---:|---:|
| C1 rule_conflict (Phase 3.5 flags) | 1,228 | 1,228 | 0 |
| C2 hypernym_vs_gloss (noun gloss-keyword heuristics) | 4,230 | 1,295 | 2,935 |
| C3 multiclass_framester (design calls) | 1,752 | 2 | 1,750 |
| C4 satellite_vs_gloss | 205 | 199 | 6 |
| C5 pertainym_vs_referent | 2,978 | 0 | 2,978 |
| C6 gapfill_vs_gloss | 257 | 57 | 200 |
| **Total** | **10,650** | **2,781** | **7,869** |

Accepted proposals resulted in **2,724 direct class changes** and **1,954 additional downstream revisions** via verb troponym re-propagation, for a total of **4,678 synset changes between v1 and v3**.

## Directory layout of the completed work

```
Dulce - WordNet - FrameNet Mapping/
├── EXPANSION_PLAN.md            the max-accuracy plan (§ current state at bottom)
├── REVIEW_PLAN.md               6-group review plan (largely executed)
├── DOUBTS_REGISTER.md           narrative overview of the register
├── COMPLETION_REPORT.md         ← this file
│
├── DOLCE-Lite.owl               input: DOLCE-Lite ontology
├── DLP3971/                     input: extended DOLCE-Lite-Plus library
├── english-wordnet-2025.ttl     input: OEWN 2025
├── ontowordnet-c983f2a9.zip     input: Framester OntoWordNet
├── AIMag24-03-003.pdf           input: Gangemi 2003
├── 1806.07699v1.pdf             input: Silva 2018
│
├── doubtful-mappings-register.tsv   10,650 doubts, all decided
├── doubtful-mappings-priority.tsv   top 2,000 by priority score
├── doubtful-register-stats.json
├── decisions-top57.tsv              Claude's hand review of top 57
├── decisions-full.tsv               systematic decisions for all 10,650
│
├── phase*-*.tsv / phase*-*.json     per-phase outputs (pilot, audit, stats)
├── build_bridge.py                  Phase 1 script
├── phase2_revalidate.py             Phase 2
├── phase3_verbs.py                  Phase 3
├── phase3_5_revalidate_verbs.py     Phase 3.5
├── phase4_pilot_adj_adv.py          Phase 4 pilot
├── phase4_full_adj_adv.py           Phase 4 full
├── phase5_verify.py                 Phase 5 v1
├── phase5_verify_v3.py              Phase 5 v3
├── phase5alt_gapfill.py             Phase 5-alt
├── phase6_release.py                Phase 6
├── build_doubtful_register.py       register builder
├── decisions_top57.py               top-57 hand decisions
├── decisions_full.py                systematic decision rules
├── apply_decisions.py               applies top-57 to v2
├── apply_decisions_full.py          applies full decisions to v3
│
├── release/                         v1 release (unchanged)
│   ├── README.md
│   ├── METHODOLOGY.md
│   ├── data/
│   │   ├── oewn-dulplus-master.tsv          (v1)
│   │   ├── oewn-dulplus-master-full.tsv
│   │   ├── oewn-dulplus-alignment.ttl
│   │   └── oewn-dolce-lite-alignment.ttl
│   └── reports/
│
├── release-v2/                      v2 release (top-57 applied)
│   ├── data/
│   │   ├── oewn-dulplus-master.tsv          (v2)
│   │   └── oewn-dulplus-alignment.ttl
│   └── reports/ PHASE_7_REPORT.md added
│
└── release-v3/                      v3 release ← FINAL
    ├── README.md                    (updated to note v3)
    ├── METHODOLOGY.md               (still accurate)
    ├── data/
    │   ├── oewn-dulplus-master.tsv          (v3, 107,518 rows)
    │   └── oewn-dulplus-alignment.ttl       (v3 Turtle)
    └── reports/
        ├── EXPANSION_PLAN.md
        ├── PHASE_1 through PHASE_5 reports
        ├── PHASE_7_REPORT.md        top-57 hand decisions
        └── PHASE_8_REPORT.md        full systematic decisions
```

## What you're reviewing

When you audit v3, the primary artefacts are:

1. **`release-v3/data/oewn-dulplus-master.tsv`** — the alignment itself (107,518 rows).
2. **`release-v3/data/oewn-dulplus-alignment.ttl`** — the Turtle serialisation.
3. **`decisions-full.tsv`** — every decision Claude made, with rationale. Each row has `oewn_id`, `chosen_class`, `alternative_class`, my `decision`, and a `decision_comment` explaining the reasoning.

Key categories for skeptical audit (in priority order):

1. **C2 accept_current decisions (2,935 rows).** My conservative default likely kept some real errors unchanged. An independent review with LLM-assisted gloss analysis could surface them.
2. **C5 (2,978 rows).** All kept as `dul:Quality`. This is a schema-design choice that the user may want to revisit.
3. **C1 accept_proposed decisions (1,228 rows).** Trusted Phase 3.5 rules wholesale. A hand-audit of, say, 50 random rows would validate this trust.
4. **C3 (1,750 accept_current).** Framester multi-class design calls; alternatives are preserved in `oewn-dulplus-master-full.tsv` for research use.

## What's out of scope for v3

- **Upstream consistency repair.** When a verb's class was corrected, its descendants (troponyms) were re-propagated. Its ancestors (hypernyms) were NOT. This is why v3 shows 1,205 hypernym violations vs. v1's 516 — the corrections exposed latent inconsistency in upstream chains. A Phase 9 could add parent-upward repair.
- **LLM-assisted semantic check.** A validator that embeds glosses and compares to DOLCE class descriptions could catch errors my rules missed. Would need a separate Phase 10.
- **Peer review of Phase 4 (adj/adv).** The novel methodology (particularly the quality/quale framework applied to adverbs) has not been externally validated. Required for publication-grade use.

## How to use the alignment

```python
import csv
alignment = {}
with open("release-v3/data/oewn-dulplus-master.tsv") as f:
    for r in csv.DictReader(f, delimiter="\t"):
        alignment[r["oewn_id"]] = r["dulplus_class"]

# Look up the DULplus class of any OEWN synset:
alignment["oewn-00001740-n"]   # → 'dul:Entity' or similar
```

For RDF/Turtle:

```sparql
PREFIX wnid: <https://en-word.net/id/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?synset ?class WHERE {
    ?synset skos:broadMatch ?class .
}
```

## Citation

If you use this alignment, please cite the two reference papers it is grounded in:

```
Gangemi, A., Guarino, N., Masolo, C., & Oltramari, A. (2003).
Sweetening WordNet with DOLCE. AI Magazine, 24(3), 13–24.

Silva, V. S., Freitas, A., & Handschuh, S. (2018).
Word Tagging with Foundational Ontology Classes: Extending the
WordNet-DOLCE Mapping to Verbs. arXiv:1806.07699.
```

Plus the input ontologies: DOLCE-Lite / DOLCE+DnS Ultralite / DLP3971 (ISTC-CNR), OEWN 2025 (Global WordNet Association), Framester (ISTC-CNR STLab), CILI (Global WordNet Association).

## Final coverage statement

**Every one of the 107,518 synsets in Open English WordNet 2025 has been assigned a DULplus class. Every one of the 10,650 judgement calls made during the pipeline has been explicitly decided and documented. The alignment is complete and ready for your audit.**
