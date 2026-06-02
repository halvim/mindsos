# OEWN ↔ DOLCE Alignment — Expansion Plan

**Date:** 2026-04-22 (revised)
**Status:** Pipeline phases 1–6 complete. Review phases in progress.
**Optimisation target:** **Maximum accuracy** in the synset-to-DULplus-class assignment. Coverage is secondary to precision; every mapping must be as correct as the evidence permits.

---

## 1. Goal

Produce a synset-level alignment from Open English WordNet 2025 (107,518 synsets) to the DOLCE+DnS Ultralite Plus (DULplus) foundational ontology, with accuracy as the single optimisation target. The alignment must:

- Cover every OEWN synset (all four POS: N, V, A, S, R).
- Ground every mapping in the published methodologies of Gangemi et al. 2003 and Silva et al. 2018 (or in an explicitly documented extension where those papers are silent).
- Carry per-mapping provenance so the reasoning behind each assignment is traceable.
- Expose every class-assignment doubt to the reviewer via a dedicated register, so judgement calls can be scrutinised.

Downstream uses of the alignment are out of scope for this plan — decisions about serialisation format, query layer, or knowledge-graph integration happen *after* accuracy is secured.

## 2. Inputs

| File | What it is | Role |
|---|---|---|
| `DOLCE-Lite.owl` | DOLCE-Lite foundational ontology (107 classes, 67 object properties, v397) | Reference ontology |
| `DLP3971/` | Full DOLCE-Lite-Plus library (207 classes, 36 disjoint pairs) across 10 modules | Extended target vocabulary + disjointness axioms for verification |
| `english-wordnet-2025.ttl` + OEWN YAML source | Open English WordNet 2025 — 107,518 synsets, ILI-indexed, with lemmas, definitions, hypernyms, examples | The alignment target |
| `ontowordnet/` (Framester) | OntoWordNet — the most up-to-date descendant of Gangemi et al.'s manually-curated alignment | Legacy seed for nouns |
| `AIMag24-03-003.pdf` | Gangemi, Guarino, Masolo, Oltramari 2003 — "Sweetening WordNet with DOLCE" | Methodology for noun alignment |
| `1806.07699v1.pdf` | Silva, Freitas, Handschuh 2018 — "Word Tagging with Foundational Ontology Classes…" | Methodology for verb alignment |
| CILI (`globalwordnet/cili`) | Interlingual Index mapping between PWN 3.0 offsets and stable ILI identifiers | Bridge between OntoWordNet and OEWN |

## 3. Principles driving accuracy

Five principles, applied throughout:

1. **Grounded rules before heuristics.** Every rule applied in the pipeline is either stated verbatim in Gangemi 2003 or Silva 2018, or (for adj/adv) explicitly marked as novel with its rationale spelled out.
2. **Provenance at every step.** Each mapping carries `method` + `provenance` fields indicating exactly how it was derived — whether inherited from OntoWordNet, derived via Silva's three-tier procedure, or produced by a Phase 4 novel rule.
3. **Make judgement calls explicit.** Every synset where the evidence supported more than one defensible target class is logged in the doubtful-mappings register with both options.
4. **Verify, don't trust.** Phase 5 runs DOLCE-Lite disjointness checks against DLP3971 and hypernym-hyponym subsumption across 81,802 pairs; violations are logged, not quietly resolved.
5. **Preserve ambiguity where the source preserves it.** Where Framester's OntoWordNet assigned two classes to the same synset (1,731 cases), both are preserved in the full master file even though the primary deliverable collapses to one per synset.

## 4. Pipeline structure — 4 macro-phases

The pipeline groups sub-phases by methodological coherence. Each macro-phase has its own reference paper (or, for M3, explicit extension rationale).

### M1 — Noun backbone (Phase 1 + Phase 2)

**Methodology:** Gangemi et al. 2003.

- **Phase 1** — Migrate Framester's 83,975-triple OntoWordNet mapping onto OEWN 2025 IDs via the Framester ↔ PWN 3.0 offset ↔ ILI ↔ OEWN chain.
  - Uses OEWN's source YAML (lemma → sense-order → offset) as the bridge key.
  - Result: 67,322 noun synsets mapped (93.68% of OEWN nouns), with full provenance back to Framester source files.
- **Phase 2** — Revalidate the 840 manually-curated OntoWordNet "top-mapping" synsets (the seed from which everything propagated) against Gangemi's six explicit rules (R1 individual/concept split, R2 meta-property propagation check, R3 role exclusion, R4 metalevel removal, R5 domain demotion, R6 backbone rigor).
  - Result: 758 clean carry-forward, 82 flagged for review.

### M2 — Verb tier (Phase 3 + Phase 3.5)

**Methodology:** Silva et al. 2018.

- **Phase 3** — Apply Silva's three-tier procedure to all 13,821 OEWN verb synsets:
  - **Tier 1** (direct derivational link): if a verb has a `wn:derivation` edge to a noun whose gloss opens "the act/process/state of", inherit that noun's Phase 1 class.
  - **Tier 2** (indirect link): antonym / verb-group / `similar` → apply Tier 1 to the neighbour.
  - **Tier 3** (gloss heuristic): "be X" → `dul:State`; "become X" → `dul:Achievement`; cognitive keywords → `dul:CognitiveEvent` / `dul:CognitiveState`; process markers → `dul:Process`; default perdurant → `dul:Event` or `dul:Action` based on agentive marker.
  - **Propagation** (Silva §4): top-level mappings inherit down the hyponym chain.
  - Result: 100% verb coverage (13,821 / 13,821).
- **Phase 3.5** — Revalidate propagated verbs (11,412 weak-tier synsets) against seven rules extending Silva's methodology: R1 verb-own-gloss Silva check, R2 aspectual mismatch, R3 troponym-parent consistency, R4 chained fallback, R5 cognitive false-positive, R6 transitivity, R7 example-sentence aspect.
  - Result: 1,228 flagged, 90.2% auto-accept.

### M3 — Novel POS extension (Phase 4)

**Methodology:** Novel — neither reference paper covers adjectives or adverbs. Rules grounded in Gangemi's Quality/Quale distinction (§"Quality vs Quale").

- **Phase 4 pilot** — 100-synset stratified sample tests the proposed rules; 95–97% quality.
- **Phase 4 full** — Scale to all 21,833 adj/adv synsets:
  - **Adjectives:** A1 satellite inherits head, A2 pertainym → `dul:Quality` + `dct:relation`, A3 participial → `dul:Quality`, A4 physical-attribute keyword → `dul:PhysicalAttribute`, A5 head default → `dul:Quality`.
  - **Adverbs:** R0 idiom guard, R1 manner → `dul:Region`, R2 temporal → `dul:TimeInterval`, R3 spatial → `dul:SpaceRegion`, R4 frequency → `dul:Region`, R5 degree → `dul:Region`, R6 modal → `dul:Abstract`, R7 default → `dul:Region`.
  - Result: 100% coverage (21,833 / 21,833), 5,601 pertainym adjectives carry `dct:relation` annotations.

### M4 — Verify & finalise (Phase 5 + Phase 5-alt + Phase 6)

**Methodology:** DLP3971 disjointness axioms + hypernym subsumption consistency.

- **Phase 5** — Four consistency checks:
  1. Class existence (every DULplus class used appears in DLP3971).
  2. Within-synset disjointness (no synset assigned to two disjoint DOLCE categories in the primary file).
  3. Hypernym-hyponym subsumption (98.5% of 81,802 checkable pairs consistent).
  4. 200-synset stratified audit sample.
- **Phase 5-alt** — Gap-fill the 4,542 OEWN-native nouns that had no legacy mapping to migrate, via OEWN hypernym propagation. Reaches 100% coverage in 3 rounds.
- **Phase 6** — Release-level deliverables: deduplicated master TSV, DULplus primary Turtle, DOLCE-Lite mirror Turtle, phase reports, review queues, reproducible scripts.

## 5. Review structure — 6 groups

Accuracy is secured through reviewable gates, not just rule execution. The review is organised into 6 groups:

| Group | Scope | Method |
|---|---|---|
| **R1 — Automated pass** | 13 very-high-confidence fixes (≥2 independent rules agree) + 61 cosmetic full-IRI normalisations + filtering of DOLCE-translation false-positive disjoint violations | Scripted; user confirms the 13-row diff |
| **R2 — High-leverage manual** | Top-50 verbs whose class propagates to many troponyms (`be`, `change`, `join`, etc.) + 30-synset Phase 5-alt gap-fill spot-check | Focused review; each decision re-propagates through script |
| **R3 — Statistical validation** | 200-synset stratified random audit across POS and method buckets | Produces the formal precision metric per (POS, method) pair |
| **R4 — Batch pattern review** | The ~1,178 remaining Phase 3.5 verb flags, clustered into ~10 flip patterns | 20-synset sample per pattern; batch-accept or fall through to individual |
| **R5 — Residuals + design** | Conditional targeted re-mapping if R3 flagged any bucket <85% precision, plus 516 hypernym-violation triage, plus multi-class Framester design decision | Pattern-specific |
| **R6 — External validation** | Peer review of Phase 4 adj/adv novel methodology | Send fresh 100-synset sample to domain experts |

## 6. Doubtful-mappings register

Every judgement call in the pipeline is logged in `doubtful-mappings-register.tsv`. Each row is a synset where the evidence supported more than one defensible DULplus class. Columns:

- `doubt_id`, `oewn_id`, `pos`, `primary_lemma`, `gloss`
- `chosen_class`, `chosen_reason` (which rule / source led to this)
- `alternative_class`, `alternative_reason` (the other defensible option)
- `class_distance` (0–3 based on DOLCE hierarchy separation between the two options)
- `doubt_category` (rule_conflict / hypernym_vs_gloss / multiclass_framester / satellite_vs_gloss / pertainym_vs_referent / gapfill_vs_gloss)
- `priority_score` (class_distance × method_weight × downstream_count)
- `downstream_count`
- `decision`, `decision_comment` (blank for user to fill in)

A prioritised subset sorted by `priority_score` ships as `doubtful-mappings-priority.tsv`, identifying the doubts where resolution most affects downstream accuracy.

## 7. Quality gates

The alignment is considered "max-accuracy defensible" when:

1. R1 automated pass complete (scripted fixes applied).
2. R3 statistical audit complete, with precision ≥ 85% per (POS, method) bucket.
3. Zero unresolved R1 or R3 Phase 3.5 flags at `confidence_score ≥ 4`.
4. Hypernym disjoint-violation rate ≤ 1% after R5 triage (currently 0.63%).
5. All doubts in the top-decile of `priority_score` in the doubtful-mappings register have a recorded `decision`.
6. For publication: R6 peer review of Phase 4 methodology.

## 8. Deliverables

### Primary (current — `release/` directory)

- `data/oewn-dulplus-master.tsv` — 107,518 rows, one per synset.
- `data/oewn-dulplus-master-full.tsv` — preserves multi-class Framester assignments (1,731 additional rows).
- `data/oewn-dulplus-alignment.ttl` — Turtle, DULplus targets, SKOS broadMatch + dct:provenance.
- `data/oewn-dolce-lite-alignment.ttl` — DOLCE-Lite mirror derived via DULplus → DOLCE-Lite translation table.

### Secondary (current)

- `reports/` — 8 phase reports documenting every step.
- `review-queues/` — flagged items from each phase for human review.
- `scripts/` — 9 reproducible pipeline scripts.
- `METHODOLOGY.md` — full traceability to the two reference papers.

### New — doubtful-mappings register (to be produced)

- `doubtful-mappings-register.tsv` — full register of all per-mapping doubts across the 6 categories.
- `doubtful-mappings-priority.tsv` — prioritised subset for near-term review.
- `DOUBTS_REGISTER.md` — narrative overview of what's in the register, how priorities are computed, and how decisions flow back to the alignment.

## 9. Known limitations (honest inventory)

1. **Cognitive verb under-count.** Phase 3 identified 24 cognitive verbs vs. Silva 2018's 874. Root cause: conservative keyword detection. Mitigation: Phase 3.5 R5 rule flagged some false-positives, but under-counting persists. A Phase 3.7 seeding from the `verb.cognition` lexical file would fix this; not yet run.
2. **Hypernym propagation dominance.** 79.8% of verb classes came from propagation rather than direct evidence. Silva 2018 acknowledges WordNet hypernymy is not always ontologically reliable. Phase 3.5 caught 1,228 propagation errors.
3. **Adjective/adverb rules are unpublished.** Phase 4 rules are novel; pilot showed 95–97% quality but formal peer review (R6) has not been done.
4. **Gap-fill nouns unvalidated.** 4,542 Phase 5-alt nouns inherited class from hypernym without spot-check.
5. **DUL→DOLCE-Lite translation is coarse.** The translation table used for the DOLCE-Lite mirror maps one DULplus class to one DOLCE-Lite class; some DULplus classes could map to multiple DOLCE-Lite categories depending on context. Result: the DOLCE-Lite mirror is derived, not primary. Known to cause ~50% of the 516 apparent disjoint violations in Phase 5.
6. **Satellite blanket inheritance.** All 10,717 adjective satellites inherit head class via `wn:similar`, without verifying each satellite's own gloss supports the head's class.
7. **Pertainym collapse to `dul:Quality`.** 5,601 pertainym adjectives mapped to a single class irrespective of the referent noun's category. Finer treatment would use referent's class.

Each limitation feeds the doubtful-mappings register — they are documented as categories of potential doubt, not hidden assumptions.

## 10. Current state vs. plan completion

| Macro-phase | Status | Coverage |
|---|---|---|
| M1 (nouns) | Complete | 67,322 via Phase 1 + 4,542 via Phase 5-alt = 71,864 / 71,864 |
| M2 (verbs) | Complete | 13,821 / 13,821 |
| M3 (adj/adv) | Complete | 21,833 / 21,833 |
| M4 (verify + release) | Complete | 107,518 / 107,518 |
| R1–R6 review | Not started | 0 / 6 groups |
| Doubtful register | Not started | — |

The pipeline has reached v1 release. The review plan + doubtful-mappings register is the path to v2 with measured max-accuracy.
