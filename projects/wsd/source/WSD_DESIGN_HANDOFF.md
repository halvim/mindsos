# WSD Component for MindsOS — Design Handoff

**Date:** 2026-04-26
**Status:** Pre-code design discussion. Several MindsOS-internal decisions block the WSD capacity spec; see §6.
**Companion:** `Layered Intelligence/_source_backup/root/mindsos_intelligence_handoff_current.md` (current-state intelligence handoff, 2026-04-25).

---

## 1. Why this document exists

A WSD design discussion was held over a single chat in the design-review mode (extreme-critique posture, push back over agree). This document captures the resulting state — settled, cut, contested — so a new chat can resume without replaying the back-and-forth. Its structure mirrors MindsOS's own handoff format.

This is a diagnostic document. Where conclusions are uncertain or depend on MindsOS-internal decisions, it says so.

---

## 2. TL;DR

The WSD work is **not a standalone project**. It decomposes into three deliverables inside MindsOS:

1. **L3 `wsd` capacity** — fixed, deterministic, reads `sense-correlations` and `learned-parameters` via context threading; outputs ranked candidate senses with multi-candidate emission allowed.
2. **L4 dream-time miner** — writes `sense-correlations` from consolidated `memories` during exploration/maintenance dreams. Independent of the (contested) coherence dream.
3. **Bootstrap importer** — pre-populates `sense-correlations` from SemCor 3.0 + WordNet GlossTag so v1 has signal before any memories exist.

Knowledge base reuses MindsOS's existing role-graphs: DOLCE (`ontology`), OEWN (`lexicon`), FrameNet (`concepts`), pre-computed alignments (`alignment:*`).

**Do not start code.** Four MindsOS-internal decisions (§6) are blocking the WSD capacity contract. Resolve those first.

---

## 3. What the WSD work actually is in MindsOS terms

Original framing was "build a system that detects what sense each word has." Reframed against MindsOS's L3/L4/L5 architecture:

- The user-visible "WSD pipeline" is an **L4 pipeline** that composes several L3 capacities — including the new `wsd` capacity, the existing `text.tokenize` / `text.dependency_parse` / `frame_match` / `slot_filler_candidates`, plus retrieval/scoring.
- The novel L3 contribution is just the `wsd` capacity itself — a stateless function that ranks sense candidates given parsed context + L2 reads.
- The "learning over time" is **L4's job**: dream-time mining of consolidated memories produces co-occurrence statistics in `sense-correlations`; the WSD capacity reads them on the next run.
- Per MindsOS L3's I1 invariant: **the `wsd` capacity is fixed and deterministic**. No mutable internal state. No self-modification. Behaviour change requires removal + re-registration under a different IRI.

This separation is *cleaner* than treating WSD as one monolithic learning system.

---

## 4. Settled decisions

### 4.1 Knowledge base

- **Reuse MindsOS's existing imports:** DOLCE (full OWL importer), OEWN (Open English WordNet), FrameNet, plus the pre-computed alignment role-graphs that ship with the box.
- **Verify alignment density** before specifying the capacity. Specifically: what fraction of OEWN verb senses have a FrameNet frame alignment? This is the actual ceiling on the verb-side generalisation. Blocking number; obtain before design.

### 4.2 Training corpora

- **SemCor 3.0** as the primary sense-tagged corpus despite size limits (~200k tokens, ~25k sense-tagged content words).
- **WordNet GlossTag** is *contaminated data* for selectional-preference learning — glosses are dictionary definitions, not natural argument structure. Use only as supplementary, heavily down-weighted, or drop entirely.
- **Consider OntoNotes 5.0** as a second primary corpus once it's confirmed it can align with OEWN sense IDs.

### 4.3 Output contract

- **Multi-candidate output is mandatory**, not a degenerate case. Per the `sense-correlations` spec in `layer4_intelligence_design_notes.md`: "preserve multiple candidates when correlations don't decisively prefer one (so WSD can promote multiple sense-assumptions when truly ambiguous)."
- Output format: ranked list of `(sense_iri, score, justification_refs)` with explicit "ambiguity preserved" flag when no candidate dominates.
- **No "winning sense" guarantee.** Architecture is built to surface ambiguity.

### 4.4 Frame parsing

- **Do not build frame parsing inside `wsd`.** The cookbook (`docs/usage/cookbook/nlu-slice.md`) shows `frame_match` and `slot_filler_candidates` are L3 capacities composed by L4 *around* WSD. Use them.
- **Do not write a frame parser from scratch.** If MindsOS's existing `frame_match` capacity is insufficient, wrap an existing parser (SEMAFOR, SLING, Open-SESAME, BERT-based) as an L3 capacity. Building one from scratch is a 6-month detour.

### 4.5 Confidence topology (per MindsOS I-rely-4)

- **No per-capacity confidence anywhere.** The `wsd` capacity does not store its own confidence.
- **Per-run output confidence** lives on the MM root composite and is computed fresh each run.
- **Pipeline-level confidence** lives on `promoted-pipelines` records keyed by `(pipeline, task_type)`.
- The "system learns to be more confident in WSD over time" is, in MindsOS terms, L4 learning *which pipeline-using-WSD performs best for which task type*, plus L4 mining `sense-correlations` to improve future inputs to WSD.

### 4.6 Architectural separation

- WSD capacity = L3 = **fixed**.
- WSD's "learning" = L4 dream miner writing `sense-correlations`.
- Bootstrap = one-time admin script (or KL importer) populating `sense-correlations` from SemCor.

These three are owned, tested, and shipped separately.

---

## 5. Decisions cut from v1 scope

### 5.1 Cut from the user's original plan

- **"100% accuracy organically over time"** — category error. Human inter-annotator agreement on fine-grained WordNet senses is ~70–80%. The architecture explicitly preserves multi-candidate output when ambiguous. Drop the target. Replace with: "match human IAA on chosen sense inventory; honestly surface ambiguity."
- **"Coherence Loop drives WSD accuracy"** — wrong on two counts. The loop trains plan stability, not task accuracy; and the loop is under active critique for removal from v1 (intelligence handoff §4.3, 2026-04-25).
- **"Eliminate impossible combinations"** — drop the boolean-filter framing. True impossibilities don't exist in data; only unobserved combinations do. Replace with conditional probability + smoothing + fallback chain.
- **"All frame elements must be filled for a frame"** — drop. Most predicate instances have most FEs unfilled in real text (FrameNet's null-instantiation labels DNI/INI/CNI exist precisely for this). Counting filled-FEs measures sentence length, not sense coherence.
- **"Constantly fill Time / Duration / Place FEs"** — drop. These are extra-thematic FEs that almost never disambiguate sense; they're typed by NER/TIMEX taggers. Wasted effort for sense-discrimination.
- **"Lifelong learning inside the WSD capacity"** — violates L3's fixed-capacity invariant. L3 capacities don't learn. Learning is L4's responsibility, via dream-time mining.

### 5.2 Pushed to v3+

- **Multi-domain ontology support (medical, legal, technology)** — not currently designed in MindsOS. Would require: domain detection capacity, swappable/parallel ontology role-graphs in KL, alignment role-graphs per domain, sense-inventory versioning across domains. Substantial KL work, not WSD work. **General English only in v1.**
- **Ontology learning (relation induction, hierarchy inference)** — not in any MindsOS doc. Open IE / ontology induction is a 25-year-old field with mediocre state-of-the-art (~50–70% precision on simple relations, much worse for ontology classes). Adding new lexicon entries (UC-NLU-2 in cookbook) is the closest thing MindsOS designs for. **Not a v1 capability.**
- **Cross-sentence FE filling** — needs event coreference and discourse structure. Open research. v1 within-clause; v2 within-sentence.

### 5.3 Decisions not made (avoid premature commitment)

- **All-words WSD scope.** v1 should target **verbs only**, restricted to verbs with ≥3 SemCor occurrences. Expand from there. Don't promise all-words coverage in v1.
- **Joint inference algorithm.** Beam search is enough for prototyping; full joint inference (factor graph, ILP) is v2 if needed.

---

## 6. Contested — needs MindsOS-internal resolution first

These are blockers. The WSD capacity contract depends on the answers.

### 6.1 Coherence loop fate (intelligence handoff §4.3)

The L4 notes say `learned-parameters` is written "on Coherence Loop convergence." If the coherence loop is cut from v1 (recommendation under review), **`learned-parameters` has no writer.**

Three resolutions, each with a different impact on WSD:

- **(a)** `learned-parameters` written by maintenance dreams instead. WSD capacity reads it as before. Cleanest minimal-change.
- **(b)** `learned-parameters` dropped from v1. WSD sense-ranker weights become static config in the capacity declaration (admin-tunable, not learned).
- **(c)** Future-plan Entry 3 (assumption-violation grounding) ships and writes `learned-parameters` based on per-step assumption-pass patterns.

**Resolve before specifying the WSD capacity inputs.**

### 6.2 FOL Layer design doc — phantom dependency

The L4 notes say `sense-correlations` and `learned-parameters` were "added 2026-04-23, from FOL Layer design." Grepping the `Layered Intelligence/` workspace turns up no FOL Layer design doc. The decisions either live in a session whose notes weren't captured, or in a doc that wasn't added to the workspace.

**Locate the FOL Layer design or write the WSD capacity spec from scratch.** The latter requires a small ADR to formalise the decisions implicit in the L4 notes.

### 6.3 Multi-domain ontology support — in-scope or v3+?

User stated as a v1 goal earlier: "senses can be recognised based on different specific ontologies vocabulary (medical, legal, technology)." The MindsOS docs do not design for this. If it's a real v1 goal, it requires KL work (swappable ontology role-graphs, per-domain alignment graphs, domain detection capacity) that is not currently scoped.

**Recommendation: defer to v3+.** Confirm or refute.

### 6.4 Ontology learning — in-scope or v3+?

User stated as a v1 goal: "when the relationship between senses are not recognised, the system would be able to learn new ones and improve known ontologies, or develop new ones." No MindsOS mechanism designs for this. Open IE, ontology induction, and relation discovery are research-grade with poor empirical track records.

**Recommendation: defer to v3+ as a research direction with its own ADR and L3 capacity family (`derivation:ontology_induction.*`).** Confirm or refute.

---

## 7. Failure modes — test buckets

These are sentence categories where the proposed approach has known coverage gaps. Use them as evaluation buckets.

- **Light verbs / copulas** — *be, have, do, make, take, get*. No real selectional preferences.
- **Adjectives / adverbs** — different disambiguation signal entirely (modified-noun co-occurrence). ~30% of content words.
- **Metaphor / figurative** — "the economy is heating up," "he killed the proposal."
- **Metonymy / coercion** — "the ham sandwich wants the check," "Washington announced," "the kettle is boiling."
- **Nouns in non-argument positions** — predicate nominals, appositions, modifiers, nouns inside non-argument PPs.
- **Idioms / MWEs** — "kicked the bucket," "spilled the beans."
- **Fine-grained senses with overlapping SP** — *run* (manage / move-fast / operate) all take human subjects; SP can't separate them.
- **Anaphora / world knowledge (Winograd-style)** — "the trophy didn't fit in the suitcase because it was too big."
- **Domain mismatch with SemCor** — medical, legal, technical, modern web text.
- **Generics / habituals** — "birds fly south."
- **Negation / modality / counterfactuals** — SP signal still fires but event didn't occur.
- **Coordination / control / raising / causatives** — "she wants to play," "I made him laugh."

A v1 system that handles SVO-clean general English well is a success. Failure on the buckets above is a known scope limit, not a defect.

---

## 8. Pitfalls — traps to avoid

### 8.1 Statistical / ML pitfalls

- **SemCor sparseness.** Most WordNet senses have 0–3 examples. You're not learning preferences; you're memorising specific phrases. Generalisation through DOLCE classes + FrameNet frames is the response, but it's not free.
- **GlossTag is dictionary text.** Verb-containing glosses are short, register-skewed, lexicographer-style — atypical of natural argument structure. Don't rely on it.
- **DOLCE may be too coarse.** Most concrete nouns collapse to "Physical Object" or "Animate Physical Object" — losing discriminating power. Alternatives worth considering: WordNet hypernym hierarchy (already aligned to senses, finer-grained), SUMO (larger), BFO (medical-friendly). DOLCE is defensible only because formal-ontology output is a stated goal.
- **MFS baseline is brutal.** Always picking WordNet sense #1 hits ~65–70% F1 on SemEval. Make MFS the explicit floor — beat it or the project failed.
- **Resnik's selectional association measure** is the right scoring function; raw conditional probability ignores class priors.

### 8.2 Process pitfalls

- **Manual pilot before code.** Pick 10 polysemous verbs. Hand-extract SP from SemCor. Try to disambiguate 50 test sentences manually using only that SP info. If you can't reliably do it by hand, the automated system won't either.
- **Don't write a frame parser.** Wrap an existing one as an L3 capacity. Six-month detour avoided.
- **Don't bootstrap on the system's own predictions.** Self-training without confidence thresholds and validation compounds errors. MindsOS's `sense-correlations` design uses *consolidated memories from completed tasks* (which include the outcome filter) — not raw predictions. Preserve that.

### 8.3 Architectural pitfalls

- **The WSD capacity is fixed.** Don't sneak mutable state into it. If you need state, it lives in L2 role-graphs written by L4.
- **Pipeline-level confidence only.** Don't add per-capacity confidence. Violates I-rely-4.
- **Don't hardcode coherence-loop assumptions.** It may be cut from v1 (§6.1).
- **MindsOS docs are a moving target.** When the user cites MindsOS as authoritative, verify against the *current* handoff (`mindsos_intelligence_handoff_current.md`), not the original. The current handoff explicitly flags ~half the original decisions as contested.

---

## 9. Recommended v1 scope

The smallest defensible v1 that delivers value and validates the architecture:

- **Verbs only.** Verbs with ≥3 SemCor occurrences.
- **General English only.** No medical / legal / tech extension.
- **Static knowledge base in v1.** No online learning at the WSD-capacity level.
- **Multi-candidate output as primary.** Single-sense commitment is a special case.
- **L4 dream miner ships in v1** if `sense-correlations` is a v1 role-graph (gated on §6.1 resolution).
- **Bootstrap importer ships in v1** as the first writer of `sense-correlations`.
- **Evaluation:** SemEval-2013 or SemEval-2015 verb subset, with MFS as floor and an interpretable BERT-based parser (optional) as ceiling.
- **Realistic effort:** 4–8 months for the three deliverables, assuming MindsOS-internal blockers in §6 resolve first.

---

## 10. Open questions to resolve before code

Things the next conversation should pin down. Numbered for reference.

1. **Sense inventory granularity.** Fine-grained OEWN synsets, or coarse-grained sense clusters (OntoNotes-style)? Fine-grained makes sparseness much worse but matches existing imports.
2. **Argument extraction policy.** Just `nsubj`+`dobj`, or full UD argument set (including obliques)? How do FrameNet roles map to UD relations?
3. **Generalisation layer.** DOLCE leaf classes only, full DOLCE hierarchy, or also WordNet hypernyms? Multi-level lookup is more powerful but explodes the parameter space.
4. **Scoring function.** Resnik's selectional association vs raw conditional probability vs a learned scorer (depends on §6.1).
5. **Joint inference.** Per-token ranking with pairwise constraints (v1) vs full joint inference (v2)?
6. **Bootstrap data scope.** SemCor only, SemCor + GlossTag (down-weighted), SemCor + OntoNotes?
7. **L4 dream miner scope.** Co-occurrence statistics over what window? Same-sentence, same-clause, same-document?
8. **WSD capacity IRI and signature.** Concrete capacity declaration shape (inputs, outputs, capability requirements, context threading) — needs an ADR.

---

## 11. Reference reading

In recommended order for someone resuming this work in a new conversation:

**MindsOS context (must-read before WSD design):**

1. `Layered Intelligence/CLAUDE.md` — 5-layer architecture summary.
2. `Layered Intelligence/_source_backup/root/mindsos_intelligence_handoff_current.md` — current state of L4 design with contested decisions explicitly flagged. **Read §3 (settled), §4 (contested), §6 (open critique).**
3. `Layered Intelligence/layer4_intelligence_design_notes.md` — search for `sense-correlations` and `learned-parameters` for the WSD-relevant L2 role-graphs.
4. `Layered Intelligence/layer5_mental_model_design_notes.md` — what L5 is and what L4 writes to it.
5. `Layered Intelligence/docs/concepts/capacity-vs-intelligence.md` — the L3/L4 split. The "fixed vs learned" rule.
6. `Layered Intelligence/docs/decisions/adr/0110-l4-coherence-dream.md` — what the Coherence Dream actually is (under critique).
7. `Layered Intelligence/docs/usage/intelligence/dreaming.md` — the four dream intents.
8. `Layered Intelligence/docs/usage/cookbook/text-realm.md` and `nlu-slice.md` — UC-NLU-1/2/3 use cases that exercise WSD.
9. `Layered Intelligence/docs/knowledge-sources/dolce.md` — DOLCE importer (note: it's the generic full-OWL importer; can import any OWL ontology).
10. `Layered Intelligence/_source_backup/root/mindsos_future_plans.md` — Entries 2 and 3 (assumption-grounded coherence) are candidates for v1 promotion and would change §6.1's resolution.

**FOL Layer design** — referenced as the source of `sense-correlations` and `learned-parameters` decisions but not located in the workspace as of 2026-04-26. Locate before specifying the WSD capacity contract.

---

## 12. Process notes for the resuming conversation

- **The previous chat operated under "extreme critique, push back over agree"** instructions. This handoff was written under that posture. If the new chat uses different instructions, treat this document as evidence — challenge or accept items individually rather than wholesale.
- **The user has, in earlier exchanges, cited MindsOS decisions as settled when they're contested.** Always verify cited decisions against `mindsos_intelligence_handoff_current.md` §3 (settled) vs §4 (contested) before building dependencies on them.
- **The v1 scope can shrink further.** If the §6 blockers resolve adversely (e.g., `learned-parameters` dropped, sense-correlations deferred), the WSD work might be just an L3 capacity with static weights + bootstrap. Reassess after §6 resolution.
- **Don't write code yet.** §6 blockers + manual-pilot recommendation in §8.2 mean code is premature.

---

**End of handoff.** Update with date and revision pointer when §6 items resolve or new MindsOS design sessions occur.
