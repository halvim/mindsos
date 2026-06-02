# Handoff Document — OEWN ↔ DOLCE/DULplus Alignment

**Purpose of this document:** Give a fresh Claude session (or any reviewer) every decision, rationale, artefact, and open issue from the project, so the work can be audited or continued without loss of context.

**Last session date:** 2026-04-22 to 2026-04-24 (multi-day single conversation)
**Final deliverable:** `release-v4/` — 107,518 OEWN synsets mapped to DULplus classes

---

## 1. Project goal

Build a synset-level ontological alignment from **Open English WordNet 2025** (107,518 synsets, all four POS) to the **DOLCE+DnS Ultralite Plus (DULplus)** foundational ontology, grounded in the published methodologies of Gangemi et al. 2003 and Silva et al. 2018, with maximum achievable accuracy on per-synset classification.

The alignment will eventually be imported into **MindsOS** (user's layered intelligence system, property-graph / metagraph architecture), where DOLCE ontology and OEWN lexicon are already loaded as typed subgraphs. The alignment provides the synset→class edges linking those two subgraphs.

**Optimisation target:** max accuracy. Coverage was secondary but achieved 100% anyway.

---

## 2. Inputs (files in the workspace)

| File | Role |
|---|---|
| `DOLCE-Lite.owl` | DOLCE-Lite foundational ontology (107 classes, v397) |
| `DLP3971/` | Extended DOLCE-Lite-Plus library (207 classes, 10 modules, 36 disjointness axioms) |
| `english-wordnet-2025.ttl` | Open English WordNet 2025 in GWN Turtle format (107,518 synsets, ILI-indexed) |
| `ontowordnet-c983f2a9.zip` | Framester OntoWordNet — extracted and used as legacy noun seed |
| `AIMag24-03-003.pdf` | Gangemi, Guarino, Masolo, Oltramari 2003 — *"Sweetening WordNet with DOLCE"* (AI Magazine). Methodology for nouns. |
| `1806.07699v1.pdf` | Silva, Freitas, Handschuh 2018 — *"Word Tagging with Foundational Ontology Classes: Extending the WordNet-DOLCE Mapping to Verbs"*. Methodology for verbs. |
| `Framenet/` | Unused in this pipeline; reserved for future work. |

**External data fetched during pipeline** (not in workspace, cloned to `/tmp/`):
- `globalwordnet/english-wordnet` — OEWN YAML source (for lemma→sense-ordering bridge).
- `globalwordnet/cili` — Collaborative Interlingual Index, `ili-map-pwn30.tab`.

---

## 3. Final deliverable

**`release-v4/`** — the reviewed alignment, in multiple formats:

```
release-v4/
├── README.md, METHODOLOGY.md, MINDSOS_IMPORT.md
├── release-stats.json
├── data/
│   ├── oewn-dulplus-master.tsv        107,518 rows, primary deliverable
│   └── oewn-dulplus-alignment.ttl     Turtle with skos:broadMatch
├── reports/
│   ├── EXPANSION_PLAN.md
│   ├── PHASE_1_REPORT.md … PHASE_5_REPORT.md
│   ├── PHASE_7_REPORT.md              top-57 hand review
│   ├── PHASE_8_REPORT.md              full systematic review
│   └── PHASE_9_REPORT.md              cognitive reseed + LLM validation
├── mindsos-imports/                   5 formats for MindsOS ingestion
│   ├── mindsos-alignment.cypher
│   ├── mindsos-alignment.metta
│   ├── mindsos-alignment.jsonld
│   ├── mindsos-alignment.nt
│   └── mindsos-alignment-edges.csv
└── scripts/
    └── export_mindsos.py
```

**Audit trail artefacts** (in workspace root, not in `release-v4/`):
- `doubtful-mappings-register.tsv` — 10,650 per-synset judgement calls
- `doubtful-mappings-priority.tsv` — top 2,000 by priority score
- `decisions-top57.tsv` — 57 hand-reviewed decisions
- `decisions-full.tsv` — 10,650 systematic decisions
- `phase9f-judgements-consolidated.tsv` — 500 LLM-judge decisions
- `phase9f-sample.tsv` — the 500-synset stratified sample
- `dulplus-reference.md` — DULplus class reference used by the LLM judges

**Formal precision measurement (from Phase 9f):**
- **75.6% strict agreement** with LLM judge
- **89.2% acceptable** (agreement + debatable)
- **10.8% clear disagreement** — this is the "real error" surface

---

## 4. Pipeline — 4 macro-phases, completed

All four were executed successfully.

| Macro-phase | Phases | Methodology | Result |
|---|---|---|---|
| **M1 — Noun backbone** | Phase 1 + Phase 2 | Gangemi 2003 | 67,322 noun synsets via OntoWordNet migration; 840 topmapping seed revalidated |
| **M2 — Verb tier** | Phase 3 + Phase 3.5 | Silva 2018 three-tier | 13,821 verb synsets (100%) |
| **M3 — Novel adj/adv** | Phase 4 pilot + full | Novel rules grounded in Gangemi's Quality/Quale | 21,833 synsets (100%) |
| **M4 — Verify + gap-fill + release** | Phase 5 + 5-alt + 6 + 7 + 8 + 9 | Internal consistency + review cycles | 107,518 total (100%) |

Detailed per-phase reports: `release-v4/reports/PHASE_*.md`.

---

## 5. Every major decision made, with rationale

This is the audit surface. A reviewer should check these.

### 5a. Design decisions (project-level)

| # | Decision | Rationale | Alternative not chosen |
|---|---|---|---|
| D-01 | **Target DULplus as primary** (not DOLCE-Lite-fine) | Framester OntoWordNet is natively DULplus; consistency across pipeline | Fine-grained DOLCE-Lite-Plus (205 classes) would preserve more distinctions |
| D-02 | **Coverage target: all 4 POS, 100%** | User confirmed Q3=C (all POS) in the EXPANSION_PLAN Q&A | Nouns-only (closer to original OntoWordNet) |
| D-03 | **Seed from OntoWordNet, then extend** (Q5=B) | Trust manually-curated seed; revalidate; extend to novel POS | Build from scratch |
| D-04 | **Multi-class Framester synsets collapsed to single class via method priority** | Single-class is standard ontology-alignment convention; multi-class preserved in `-full.tsv` for research | Keep multi-class as SKOS relatedMatch or explicit facets |
| D-05 | **Pertainym adjectives → dul:Quality + dct:relation annotation** | DULplus has no "RelationalQuality" class; annotation preserves referent info | Custom RelationalQuality subclass, or inherit referent's class |
| D-06 | **Method-priority dedup ordering** | Gangemi-curated > Silva-derived > propagated > gapfill | Empirical precision-based (not measurable until Phase 9f) |
| D-07 | **Revisit only `max accuracy` (dropped FalkorMG targeting)** | User clarified the accuracy goal mid-project; MindsOS targeting deferred | Keep downstream-optimised; would have collapsed multi-class differently |

### 5b. Methodological decisions (per-phase)

**Phase 1 — ID bridge (Framester name-based IDs → OEWN offset-based IDs):**
- D-P1-1: Use OEWN source YAML (`entries-*.yaml`) sense-ordering to resolve Framester's `synset-LEMMA-POS-SENSE` IRIs to PWN 3.0 offsets, which are identical to OEWN synset IDs. **Rationale:** direct lemma-match was too noisy; ILI alone insufficient; sense-ordering via OEWN YAML is authoritative.
- D-P1-2: Join via ILI where possible, fall back to lemma+sense-number matching. **Result:** 69,074 unique (oewn_id, class) pairs from 83,975 Framester triples (82.3% resolution).

**Phase 2 — Top-mapping revalidation (840 synsets):**
- Applied Gangemi R1-R6 rules verbatim from §5-6 of *"Sweetening WordNet with DOLCE"*. Flag types: metalevel, perdurant_gloss, role_lemma, class_singleton, full_iri_class. 82 flagged, 758 auto-accepted.

**Phase 3 — Silva three-tier for verbs:**
- Tier 1 (derivation + "the act/state/process of" marker): **strict opener match required**. Result: 15.1% (Silva got 36.25%). Our strictness reduced false positives.
- Tier 2 (antonym/verb-group): 1.2%.
- Tier 3 (gloss heuristic, "be X" → State, cognitive keywords, etc.): 4%.
- Propagation (Silva §4 rule): 79.8%. **Known limitation:** WordNet hypernymy isn't type-preserving.
- Target classes: dul:{Action, State, Process, Event, Achievement, CognitiveEvent, CognitiveState, Task}.

**Phase 3.5 — Verb revalidation (7 rules R1-R7):**
- R1: verb's own gloss opens with Silva marker
- R2: aspectual keyword mismatch (Gangemi §3 state/process/event/action markers)
- R3: troponym-parent consistency (≥50% of Tier-1 children disagree with parent)
- R4: chained fallback (≥2 tier3 defaults in provenance chain)
- R5: cognitive false-positive (physical-sensation keyword in gloss but class is Cognitive*)
- R6: gloss-derived transitivity (agentive + transitive pattern → Action)
- R7: example-sentence aspect (tiebreaker, only used when another rule fires)
- Result: 1,228 flagged (10.76% of weak-tier scope).

**Phase 4 — Novel adj/adv rules (unpublished methodology):**
- A1: satellite inherits head class via `wn:similar`
- A2: pertainym → dul:Quality + dct:relation annotation (D-05)
- A3: participial → dul:Quality
- A4: physical-attribute keyword → dul:PhysicalAttribute
- A5: adj.all head default → dul:Quality
- R0: idiom guard (economic/figurative markers block spatial rule)
- R1-R7 adv rules (manner, temporal, spatial, frequency, degree, modal, default)
- Pilot showed 95-97% quality on 100-synset stratified sample.

**Phase 5 — Verification:**
- DUL → DOLCE-Lite translation table (64 classes) used for disjointness checks.
- Hypernym subsumption: 98.5% compatible (v1), 96.31% (v3) — v3 exposed latent inconsistency.
- 200-synset stratified audit sample prepared but not manually scored.

**Phase 5-alt — Gap-fill:**
- 4,542 OEWN-native nouns (added/renamed since PWN 3.0) propagated via OEWN hypernym chain. Zero remaining orphans.

### 5c. Concrete class decisions (the judgement calls)

Three places where individual synset classes were decided against explicit alternatives:

**5c-i. Phase 7 hand review — 57 top-priority doubts (`decisions-top57.tsv`):**
- 32 accept_proposed (class flip), 25 accept_current (no change)
- Every decision has a written rationale in `decision_comment` column
- Top-leverage fixes: `be` (Event → State, 46 descendants affected), `act` (State → Action, 564 descendants), `change` (State → Process, 439), `move` (State → Action, 153), `cover`, `exist`, `interact`, `treat`, etc.
- Also fixed 23 "the act of X" nouns that were wrongly Situation → Action

**5c-ii. Phase 8 systematic decisions — 10,650 doubts (`decisions-full.tsv`):**
- Category rules encoded in `decisions_full.py`:
  - **C1 (rule_conflict, 1,228):** default accept_proposed (trust Phase 3.5)
  - **C2 (hypernym_vs_gloss, 4,230):** conservative — accept_proposed only on Silva markers + lemma-class matches; accept_current by default (1,295 accepted, 2,935 kept)
  - **C3 (multiclass_framester, 1,752):** accept_current by default; one pattern (`AgentCollection → Event` for social gatherings) flipped
  - **C4 (satellite_vs_gloss, 205):** accept_proposed when physical-attr keyword present (199 accepted)
  - **C5 (pertainym_vs_referent, 2,978):** accept_current (preserve design D-05)
  - **C6 (gapfill_vs_gloss, 257):** same as C2

**5c-iii. Phase 9f LLM judge — 53 corrections (`phase9f-judgements-consolidated.tsv`):**
- 500 synsets stratified sample, 10 parallel Claude subagent judges
- Notable flip patterns:
  - `InternalRepresentation → CognitiveState` (4): emotional states
  - `FunctionalSubstance → Substance` (3): less-functional matter
  - `PhysicalPlace → DesignedArtifact` (3): engineered conduits (air-intake, duct, main)
  - `Action → Role` (2): job titles (secretary of energy, magistracy)
  - `Right → Amount` (2): monetary fees (mintage, linage)

### 5d. Phase 9 improvements attempted

| Sub-phase | Outcome | Why |
|---|---|---|
| **9c cognitive re-seeding** | ✅ applied | 697 cognitive verbs reseeded from `verb.cognition.yaml`; 1,054 synsets revised (direct + troponym propagation). Lifted cognitive coverage from 24 (v3) to 1,079 (v4), matching Silva's scale. |
| **9b C2 head-noun re-audit** | ❌ rolled back | Regex-based head extraction had ~67% false-positive rate on 30-synset audit (e.g., "lieutenant governor" → State because "state" in gloss). Would need real NLP dependency parsing. |
| **9a upstream consistency repair** | ❌ rolled back | Local cascade added ~4 new violations per repair. Root cause: OEWN's hypernym graph isn't type-preserving (Gangemi's R2 flagged exactly this). Local rule-based cascades can't fix it; would need graph-level restructuring. |
| **9f LLM-assisted validator** | ✅ applied | 500-synset stratified sample judged by parallel Claude subagents; 53 disagreements applied as corrections; formal 89.2% acceptable precision measured. |

### 5e. MindsOS import design decisions

| # | Decision | Rationale |
|---|---|---|
| D-MI-1 | Alignment is purely additive — adds synset→class edges only | Assumes DOLCE and OEWN already loaded as typed subgraphs |
| D-MI-2 | `skos:broadMatch` as default predicate | Standard SKOS for cross-vocabulary alignment where target is broader than source |
| D-MI-3 | Confidence score 0-1 derived from method priority | Lets MindsOS weight GraphRAG retrievals by source reliability |
| D-MI-4 | 5 output formats (Cypher, MeTTa, JSON-LD, N-Triples, CSV) | Covers FalkorDB, Neo4j, Memgraph, Hyperon AtomSpace, and any RDF store |
| D-MI-5 | Idempotent via `MERGE` / dedup | Re-runnable; safe |
| D-MI-6 | Configuration via 4 knobs (ALIGNMENT_PREDICATE, OEWN_BASE_IRI, DUL_BASE_IRI, CYPHER_REL_TYPE) | Adapts to MindsOS naming without code changes |

**Assumptions NOT yet verified against MindsOS:**
- OEWN synset IRI scheme in MindsOS matches `https://en-word.net/id/oewn-{offset}-{pos}`
- DULplus class IRI scheme in MindsOS matches canonical DOLCE IRIs
- Edge-property naming convention (confidence, method, provenance)

---

## 6. What should be audited

Ordered by likely impact on accuracy:

### High-priority audits

1. **Phase 8 C1 decisions (1,228 verbs).** All were auto-accepted based on trust in Phase 3.5 rules. The top 13 were hand-reviewed in Phase 7 (all accepted); the remaining 1,215 are untested. Stratified sampling of 50 would validate.

2. **Phase 8 C2 `accept_current` decisions (2,935 nouns).** My conservative default likely kept some real errors unchanged because the keyword heuristic couldn't distinguish "keyword denotes the synset" from "keyword appears in context." LLM-assisted or dependency-parsing validation would catch these.

3. **Phase 9c cognitive re-seeding.** 697 cognitive verbs reseeded. 596 → CognitiveEvent, 101 → CognitiveState. The State/Event split was based on stative-gloss detection; some borderline cases (e.g., `touch` = "feel as if" → CognitiveState) are debatable.

4. **Pertainym treatment (D-05, 2,978 C5 synsets).** All mapped to `dul:Quality` with relation annotation. A reviewer with a DULplus background should confirm this is preferable to a custom subclass or referent-inheritance approach.

5. **Phase 9f LLM judge single-bias.** Only one LLM (Claude subagents with a shared prompt template) produced the 89.2% acceptable measurement. A second independent judge (different model, or human expert) would give a more robust precision number.

### Lower-priority audits

6. **Phase 4 novel adj/adv rules.** Neither reference paper covered these POS. The 95-97% pilot number is self-measured; external peer review required for publication-grade validation.

7. **Phase 5-alt gap-fill** (4,542 nouns). Propagated from hypernyms without spot-check. Usually reliable for OEWN-native synsets but never audited.

8. **Hypernym-violation list** (`phase5v3-disjoint-pairs.tsv`, 1,205 rows). Half are translation-layer artefacts in my DUL→DOLCE translation table; the rest are real WordNet hypernymy quirks (Gangemi R2 issues).

---

## 7. How to verify or continue the work

### To verify a specific class assignment

1. Find the synset in `release-v4/data/oewn-dulplus-master.tsv`.
2. The `method` column tells which phase produced it.
3. The `provenance` column gives the rationale (Framester ID, rule name, sense derivation, etc.).
4. Cross-reference `decisions-full.tsv` to see if this synset was a Phase 8 doubt and what decision was made.
5. Cross-reference `phase9f-judgements-consolidated.tsv` to see if the LLM judge evaluated it.

### To audit a whole category

- C1 verbs: `grep C1_rule_conflict decisions-full.tsv`
- C5 pertainyms: `grep C5_pertainym_vs_referent decisions-full.tsv`
- Top-57: open `decisions-top57.tsv` directly
- LLM judge sample: open `phase9f-judgements-consolidated.tsv`

### To produce a new v5 release after audit decisions

The pipeline is idempotent:

1. Edit `decisions-full.tsv` — change `decision` column on any row.
2. Run `apply_decisions_full.py` (in workspace root) — regenerates master + Turtle + release bundle.
3. Run `phase5_verify.py` to get updated consistency metrics.

### To extend the coverage or method

New scripts should follow the existing pattern:
- Read current master TSV
- Apply changes with explicit `method = "phaseN_..."` and `provenance` strings
- Write new master TSV
- Run Phase 5 verification

### To integrate with MindsOS

- See `release-v4/MINDSOS_IMPORT.md` for full details.
- Five import formats are pre-generated in `release-v4/mindsos-imports/`.
- If MindsOS uses different IRI schemes or a different predicate, edit the four config knobs at the top of `release-v4/scripts/export_mindsos.py` and re-run.

---

## 8. Reference papers and their role

- **Gangemi, Guarino, Masolo, Oltramari (2003). "Sweetening WordNet with DOLCE."** AI Magazine 24(3), 13–24. → Methodology for nouns (Phase 2, 8, 9b). Specifically: OntoClean meta-properties (Rigidity, Identity, Unity, Dependence), R1-R6 rewriting rules, backbone-taxonomy approach.

- **Silva, Freitas, Handschuh (2018). "Word Tagging with Foundational Ontology Classes: Extending the WordNet-DOLCE Mapping to Verbs."** arXiv:1806.07699. → Methodology for verbs (Phase 3, 3.5). Specifically: three-tier derivation/indirect/gloss procedure, Silva §4 propagation rule.

Both PDFs are in the workspace root.

---

## 9. Open questions for the reviewer

These are genuine open questions the work raises. A better model with fresh eyes may have answers I didn't.

1. **Is `dul:Quality` the right class for ALL pertainyms?** Or does the referent's ontological category warrant a finer distinction (e.g., `solar` = Quality-of-PhysicalObject vs. `medical` = Quality-of-Profession)?

2. **Should the 791 within-synset multi-class Framester assignments be preserved as `skos:relatedMatch` secondary edges in MindsOS?** Currently they're collapsed to single-class in primary, preserved in `-full.tsv` only.

3. **Are the Phase 4 novel adj/adv rules ontologically defensible for publication?** DOLCE's Quality/Quale framework extends naturally to adjectives, but the adverb rules (manner = `dul:Region`, temporal = `dul:TimeInterval`, etc.) are my design.

4. **Is the method → confidence score calibration correct?** Phase 9f gave us a precision number; we could derive better-calibrated confidences by splitting precision per method bucket.

5. **What's the right MindsOS predicate?** `skos:broadMatch`, `rdf:type`, or a custom `mindsos:hasOntologicalType`? Depends on whether MindsOS treats synsets as concepts narrower than the class, or as instances of the class.

6. **Should the pipeline add upstream consistency repair in a way that works?** Phase 9a failed because OEWN's hypernymy isn't type-preserving. A graph-level restructuring pass (re-curating problem branches like Gangemi did for the 9 unique beginners) could resolve the 1,205 remaining violations, but is a substantial methodology undertaking.

---

## 10. Scripts (all in workspace root and `release-v4/scripts/`)

| Script | Phase | What it does |
|---|---|---|
| `build_bridge.py` | 1 | Framester → OEWN ID bridge |
| `phase2_revalidate.py` | 2 | Top-mapping revalidation |
| `phase3_verbs.py` | 3 | Silva verb mapping |
| `phase3_5_revalidate_verbs.py` | 3.5 | Verb revalidation (R1-R7) |
| `phase4_pilot_adj_adv.py`, `phase4_full_adj_adv.py` | 4 | Adj/adv mapping |
| `phase5_verify.py`, `phase5_verify_v3.py` | 5 | Consistency verification |
| `phase5alt_gapfill.py` | 5-alt | Gap-fill OEWN-native nouns |
| `phase6_release.py` | 6 | Build release bundle |
| `build_doubtful_register.py` | - | Generate 10,650-row doubtful register |
| `decisions_top57.py` | 7 | Claude's hand review of top 57 |
| `decisions_full.py` | 8 | Systematic decisions for all 10,650 |
| `apply_decisions.py`, `apply_decisions_full.py` | 7, 8 | Apply decisions → regenerate master |
| `phase9c_cognitive.py` | 9c | Cognitive re-seeding |
| `phase9b_c2_reaudit.py` | 9b | Abandoned head-noun re-audit (kept for reference) |
| `phase9a_upstream_repair.py` | 9a | Abandoned upstream cascade (kept for reference) |
| `phase9f_sampler.py`, `phase9f_apply.py` | 9f | LLM validator pipeline |
| `export_mindsos.py` | — | Multi-format MindsOS import export |

---

## 11. Starting a new conversation

Paste this into the first message of the new chat, along with this HANDOFF.md:

> I have a completed OEWN-to-DOLCE/DULplus alignment project (v4, 107,518 synsets, 100% POS coverage). I'd like you to audit the decisions made during the pipeline. The handoff document `HANDOFF.md` at the workspace root gives you all the context. The final deliverable is in `release-v4/`. Every judgement call made during review is in `decisions-full.tsv` (10,650 rows with per-decision rationale).
>
> Please [specific audit request — e.g., "verify the Phase 9c cognitive re-seeding by sampling 50 synsets from verb.cognition.yaml and checking the State/Event split against the verb glosses" or "audit the pertainym design decision (D-05) against published DOLCE practice" or "prepare the MindsOS import configuration after reviewing a MindsOS sample node I'll attach"].

Suggested first audits in decreasing leverage:

1. **Sample 50 random Phase 8 C2 `accept_current` decisions** (`grep C2.*accept_current decisions-full.tsv | shuf -n 50`) and check whether the keyword-kept-as-is decision was correct.
2. **Sample 30 cognitive re-seedings** from `phase9c_cognitive_reseed` method rows and verify the State vs Event classification.
3. **Full audit of the 53 Phase 9f LLM corrections** in `phase9f-judgements-consolidated.tsv` where `judgement = disagree`. Small, tractable, and each one was a specific class flip.
4. **Sample 20 pertainym adjectives** (method = `phase4_A2_pertainym_default`) and evaluate whether `dul:Quality + dct:relation` is the right design vs. a referent-inherited class.

---

## 12. Final coverage snapshot (v4)

| POS | Mapped | Coverage |
|---|---:|---:|
| Noun (`n`) | 71,864 | 100% |
| Verb (`v`) | 13,821 | 100% |
| Adjective head (`a`) | 7,502 | 100% |
| Adjective satellite (`s`) | 10,717 | 100% |
| Adverb (`r`) | 3,614 | 100% |
| **Total** | **107,518** | **100%** |

**Distinct DULplus classes used:** 65.

**Top 10 classes by frequency:**
| Class | Count |
|---|---:|
| `dul:Quality` | 20,005 |
| `dul:Action` | 15,487 |
| `dul:Organism` | 9,144 |
| `dul:Person` | 7,622 |
| `dul:DesignedArtifact` | 7,615 |
| `dul:FunctionalSubstance` | 5,083 |
| `dul:Situation` | 4,625 |
| `dul:Region` | 3,332 |
| `dul:InformationRealization` | 3,215 |
| `dul:BiologicalObject` | 2,581 |

**Measured precision:** 75.6% strict agreement / 89.2% acceptable (Phase 9f, 500-synset stratified sample, Claude subagent judges).

---

*End of handoff document. All decisions captured above are traceable through the phase reports and TSV audit files referenced.*
