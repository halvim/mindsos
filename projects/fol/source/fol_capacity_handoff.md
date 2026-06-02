# First Order Logic Capacity Family — MindsOS L3 Design Handoff

**Status:** Design-in-progress ("why / what" scoping complete; "how" not yet started)
**Created:** 2026-04-23
**Parent architecture:** MindsOS layered intelligence system (formerly `falkormg`)
**This document location:** `/Users/henriquealvim/Documents/Claude/Projects/First Order Logic Layer for MindsOS/fol_capacity_handoff.md`
**Related codebase:** `/Users/henriquealvim/Documents/Claude/Projects/Layered Intelligence/` (L3 code still uses the historical `falkormg_` package prefix pending a coordinated rename)

---

## 0. How to use this document

This pack consolidates every architectural decision reached while scoping the First Order Logic capacity family for MindsOS Layer 3. It is meant to be uploaded to a fresh chat (ideally a more capable model) with the instruction: **"check these decisions end-to-end for coherence, internal contradictions, and against the rest of the MindsOS architecture."**

The design is deliberately not in "how" territory yet. There is no code, no concrete FOL syntax commitment, no theorem-prover choice, no Python API. What is committed is the *shape* — which capacities exist, where they live in the layered architecture, what data they consume and produce, and what invariants they must respect.

For full context, the reviewer should also have access to:

- `falkormg_capacity_handoff.md` — the L3 (Intellectual Capacity) handoff for the parent layer
- `falkormg_capacity_adrs.md` — 24 ADRs (plus 2 proposed) covering the L3 design
- `layer4_intelligence_design_notes.md` — L4 (Intelligence) design notes, including the GAN-analogous coherence loop and the three-tier memory model
- `layer5_mental_model_design_notes.md` — L5 (Mental Model) design
- `falkormg_knowledge_handoff.md` — L2 (Knowledge) handoff
- `mindsos_future_plans.md` — post-v1 items deferred from the L4 session
- `DOLCE_FOUST_2022.pdf` — the DOLCE foundational ontology paper (the FOL-based ontology this layer depends on)

---

## 1. The vision — why FOL, and what it is in this architecture

**The human cognitive move being modelled.** When people read text or witness events, they silently generate assumptions to fill gaps that the observation itself doesn't specify. "Mary entered the kitchen and poured coffee" — the reader assumes there is a coffee pot, a floor, an adult, a walkable route. Some assumptions later get validated by additional information; others get revised or overturned. This assumption-and-revision machinery is a load-bearing part of everyday comprehension.

**What the FOL family does.** It gives the MindsOS system an explicit version of this machinery: translate inputs into first-order-logic statements; track what is observed versus inferred versus assumed versus hypothesised; check coherence mechanically; run revisions when contradictions arise; surface gaps for downstream reasoning to address.

**Framing.** Not "a reasoning engine." An **epistemic ledger with a reasoning engine attached**. The ledger is the substrate — a growing record of tagged FOL statements. The capacities are operations on the ledger: translation, gap-filling, consistency checking, entailment, abduction, revision, introspection.

**Academic analogue (vocabulary, not implementation).** The closest prior art is an **Assumption-based Truth Maintenance System (ATMS)** wrapped in an **AGM-style belief revision** layer. Naming these as an anchor gives the design a shared vocabulary without committing to a specific ATMS or AGM implementation.

**What this layer does not do.**
- It does not *invent* translation from thin air — it applies the L2 ontology's existing axiom templates to sense-annotated inputs. Translation is largely ontology-driven lookup + template instantiation.
- It does not own the ledger's content — the live ledger is L5 working memory for the current task. FOL capacities are stateless: they read L2 + L5 and return results.
- It does not make strategic decisions — choosing which translator, which inference backend, which priority rule, when to ask a human, which rule to promote — those are L4 intelligence responsibilities.
- It does not leave first-order logic — defeasibility, abduction, belief revision, and sense revision are all achieved via epistemic tags on statements + rule transformations, not by switching to a non-monotonic or higher-order logic.

---

## 2. Where it fits — the layered architecture

```
┌──────────────────────────────────────────────────────────────┐
│  5. Mental Model Layer     (live working memory — per task)   │
│  4. Intelligence Layer     (applied knowledge, orchestration) │
│  3. Intellectual Capacity  ◄── FOL family adds capacities here│
│  2. Knowledge Layer        (ontology, lexicon, concepts, …)   │
│  1. Core Layer             (graphs, metagraphs, persistence)  │
└──────────────────────────────────────────────────────────────┘
```

**L3 (this layer's host)** holds the fixed repertoire of abilities the system can call — pure, stateless, deterministic functions, monitors, and adapters. Organised as a Global metagraph plus per-user Local metagraphs, with capacities grouped under twelve functional categories.

**The FOL family plugs into L3** as a set of capacities distributed across several of the existing twelve categories (primarily *comprehension*, *derivation*, *combination*, *retrieval*, *scoring*, *trace*, *signalling*, *interaction*, and *learning_methods*). It is not a new category; it is a cross-category family that shares a DataState vocabulary and a set of L2 role-graphs.

**Upstream dependencies (things FOL needs already in place):**
- L3 perception + comprehension capacities: tokenisation, sentence splitting, word-sense disambiguation (WSD) against a WordNet-aligned lexicon
- L2 ontology role-graph: DOLCE (foundational) plus any domain extensions
- L2 lexicon role-graph: WordNet-aligned sense inventory with DOLCE category mappings
- L2 concepts role-graph: domain concepts
- L2 memories role-graph: for consolidated task ledgers

**New L2 role-graphs this design introduces:**
- `fol-rules` — rules as first-class entities, metalinked to ontology + lexicon
- `sense-correlations` — co-occurrence patterns between lemma senses (learned from consolidated memories)
- `wsd-model` (tentative) — learnable parameters for the WSD sense-ranking model

---

## 3. The fixed-vs-learned discipline — what goes where

This is the single most important architectural principle guiding this design. Quoted from `layer4_intelligence_design_notes.md`:

> L3 is fixed things you can do; L4 is the learned use of them.
> A capability is in L3 if it is fixed — behaves deterministically. Either the system has it, or it doesn't.
> A capability is in L4 if it depends on confidence learned from experience — applying, composing, choosing among, or optimising L3 capacities.

**Applied aggressively.** During design, whenever a candidate L3 capacity involves "applying a rule", "picking among options", "judging salience", or anything that could plausibly be parametric over a strategy, the pattern is to **decompose further**: each strategy becomes its own L3 capacity (fixed), and the *choice* among them becomes an L4 responsibility (learned). This pattern applies recursively.

**Examples of the discipline at work:**
- Revision by priority → many priority-ranking capacities (L3) + one `apply_revision` mechanic (L3) + L4 picks the ranker for this conflict.
- Gap detection → `enumerate_unbound_predicates` (L3) + `score_gap_relevance` (L3) + L4 picks which gaps matter.
- Ingestion → `fol.classify_ingestion_role` (L3) + L4 dispatches the appropriate ingestion pipeline.
- Sense commitment → WSD produces candidates (L3); FOL validation promotes/retracts (L3); L4 decides when to accept narrowing.

**Two L3 invariants from the parent handoff that constrain everything here:**
- **I1** — every L3 capacity is a pure function of its declared inputs plus an immutable `context` dict. No learned state in L3.
- **I2** — DataStates are purely structural. No confidence, no "semantic class", no weights on the data itself.

**L5 holds the live state.** The FOL ledger, sense distributions, open gaps, and recent validation results all live in L5 working memory inside the current task's Mental Model. L3 capacities read L5 but do not own its content.

**L2 holds the stable knowledge.** Ontology, lexicon, concepts, rules, correlations, learned model parameters, and consolidated memories all live in L2 as versioned role-graphs.

---

## 4. Core design commitments

### 4.1. Rules are strict; defeasibility lives on assumptions

**Commitment.** All FOL rules are strict (monotonic). There is no "defeasible" flavour.

**Where defeasibility lives.** On **assumptions** in L5's ledger — they are provisional beliefs that get promoted, retracted, or revised as the ledger grows. And on synthetic rules' **status field** — synthetic rules can be falsified (see §4.2).

**Rationale.** Classical-logic literature treats "defeasible rules" as a workaround for not being able to state all exceptions upfront. The cleaner move: state rules strictly *with known exceptions* as antecedent clauses; when new unknown exceptions arise, either refine the rule or falsify it. No middle state.

**Mechanical consequence.** No non-monotonic logic required. Rule exceptions are conjuncts in the antecedent:

```
∀x. bird(x) ∧ ¬flightless_bird(x) → fly(x)   [strict]
```

When a new exception is discovered (say, "wounded birds don't fly"), two L3 capacities handle it mechanically:

- `fol.extend_rule_with_exception(rule, exception_clause) → refined_rule`
- `fol.compose_rule_with_exception(A, B) → A'` — combines a general rule A with an exception rule B into a refined general rule A' with the exception explicit in the antecedent.

### 4.2. Analytic vs synthetic rules; falsification, not weakening

**Provenance taxonomy.** Every rule in the `fol-rules` role-graph carries a **provenance** field with one of two values:

- **analytic** — true by virtue of what the concepts mean. Derived from ontology class relationships (e.g., `∀x. human(x) → mortal(x)` follows from `human ⊏ mortal` in the ontology's taxonomy).
- **synthetic** — true by virtue of how the world is. Added by observation, reasoning, or learning.

**Status field (synthetic rules only).** Synthetic rules carry a status:

- `active` — currently believed
- `hypothetical` — on trial; generated from patterns, not yet validated
- `pending_validation` — observations accumulating; not yet confirmed or falsified
- `falsified` — proven wrong by a specific observation; archived with the falsifying evidence

**Analytic rules have no status field.** They are immutable within the FOL layer. If an observation contradicts an analytic rule, that is an ontology incoherence, not a falsification — a flag is raised to trigger the ontology-revision workflow (which lives outside the FOL layer).

**Falsification, not weakening.** When a stronger observation contradicts a synthetic rule, the rule is **falsified** (moved to `falsified` status with the falsifying observation recorded), not weakened. This matches scientific methodology. Falsified rules stay in the graph as learning fodder — dreaming (L4) can mine them for patterns.

**Supporting L3 capacities:**
- `fol.falsify_rule(rule, contradicting_observation)` — marks rule falsified, archives evidence
- `fol.generate_hypothetical_rule(observations, template)` — proposes a new rule from patterns
- `fol.validate_rule_against_ledger(rule, ledger)` — returns supporting + contradicting statements
- `fol.archive_falsified_rule(rule, observation)` — write helper into L2
- `fol.flag_analytic_contradiction(rule, observation)` — emits an anomaly with `ontology_revision_pending` tag to the problem-trace sink

### 4.3. Time is explicit

**Commitment.** Every time-variant predicate takes a time argument. A `now` anchor is a first-class variable updated each reasoning cycle. The tense of an utterance is translated into temporal constraints on event variables.

**Examples.**
```
age(Mary, now) = 2                              ← time-variant: time-indexed
human(Mary)                                     ← time-invariant: not indexed
PC(Mary, e1, t1) ∧ t1 < now                    ← past-tense utterance
```

**Structural flag.** Each predicate declaration in L2 carries `is_time_variant: bool`. The translator reads this flag and adds the time argument automatically when true.

**Supporting L3 capacity:**
- `fol.tense_to_temporal_anchor` — reads utterance tense features, emits temporal constraints relative to `now`

**DOLCE alignment.** DOLCE already commits to time-indexed primitives (temporary parthood `P(x, y, t)`, participation `PC(x, y, t)`, presence `PRE(x, t)`, temporal quale `qlT`). This design follows suit for any domain predicate the ontology marks as time-variant.

### 4.4. Epistemic tagging

**Commitment.** Every FOL statement in the ledger carries an **epistemic tag** marking its standing:

- **observed** — directly asserted by an authoritative source or the current input
- **inferred** — derived from observed statements via strict rules
- **assumed** — provisionally added to fill a gap or carry a sense alternative
- **hypothesised** — entertained as a candidate without commitment

**Priority order for revision** (built into `fol.priority.observed_first`): observed > inferred > assumed > hypothesised. Other priority-ranking capacities (e.g., `fol.priority.source_trust`, `fol.priority.recency`) apply different orderings.

**Mechanical promotions (L3) — follow from the ledger state alone:**
- *assumed → inferred*: when the rest of the ledger now entails the assumption
- *assumed → retracted*: when the assumption contradicts an observation
- *inferred → retracted*: when the supporting observations die (cascade)

**Policy promotions (L4) — require trust or confidence judgment:**
- *assumed → inferred on weak evidence*: learned threshold
- *inferred → observed*: source-trust on the reasoning chain
- *observed → doubted/retracted*: source-trust decline

**Rule of thumb.** If the tag change follows from logical relations alone, it's L3; if it requires trust or confidence judgment, it's L4.

### 4.5. Classical FOL + tags + rule transformations — no non-monotonic logic

**Commitment slogan.** *Classical FOL + epistemic tags on assumptions + rule falsification machinery = defeasibility without leaving first-order logic.*

The machinery we need for realistic reasoning — defaults, belief revision, abduction, sense revision — is built from:

1. Strict FOL rules (the logic itself stays classical)
2. Epistemic tags on statements (the dynamic layer)
3. Mechanical rule transformations (composition, exception extension, derivative form generation)
4. Falsification of synthetic rules (when observation contradicts)

**No** non-monotonic logic, no default logic, no circumscription, no description logic extensions. The expressiveness we'd get from those is recovered via the tag/revision discipline at the ledger layer.

**Derivative forms.** `fol.derive_alternative_forms(rule) → list<rule>` produces contrapositive and re-indexed variants of a rule. Different forms chain with different other rules; carrying multiple forms speeds up entailment queries without changing truth content.

### 4.6. Ledger in L5, rules in L2, capacities in L3

**Layer placement of FOL-related artifacts:**

| Artifact | Layer | Notes |
|---|---|---|
| FOL capacities (functions) | L3 | Stateless; read L2 + L5, return results via `InvocationResult` |
| FOL rules graph | L2 | New role-graph `fol-rules`, metalinked to ontology + lexicon |
| Sense correlations | L2 | New role-graph `sense-correlations`, learned from memories |
| WSD model parameters | L2 | Tentative new role-graph `wsd-model` |
| Live ledger (observed + inferred + assumed + hypothesised) | L5 | Part of the current task's Mental Model |
| Sense distributions (per-lemma priors) | L5 | Part of MM |
| Open gap list | L5 | Part of MM |
| Recent validation results | L5 | Part of MM |
| Consolidated ledgers from completed tasks | L2 `memories` | Written on task completion; used for dreaming |

**L4 responsibility.** Choose which L3 capacity to invoke; manage L5 state (read + write); dispatch validation passes; route conflicts; decide canonical-vs-operational ingestion.

### 4.7. Ingestion-role distinction — canonical vs operational

**Commitment.** Every incoming statement is classified by its **ingestion role** — the role under which the system should treat it:

- **Canonical** (tentative name; alternatives: authoritative, teaching, constitutive, ground) — the speaker is presenting the statement as truth; the system should trust it and may update L2 accordingly (via the appropriate revision pipelines).
- **Operational** (tentative name; alternatives: evaluative, working, regulative, claim) — the speaker is making a claim to be evaluated against current knowledge; the system may produce verdicts but **never writes L2**.

**Example** — "a cat is a fish":
- *As operational:* system checks → inconsistent with ontology (`cat ⊏ mammal`, `mammal ⊏ ¬fish`) → returns verdict "inconsistent". No L2 change.
- *As canonical:* system checks → contradicts analytic rule → `fol.flag_analytic_contradiction` fires → L2 ontology-revision workflow picks up the flag. The flag is reviewed explicitly; no auto-apply to L2.

**Provenance field added.** Every `DS_FOL_STATEMENT` carries `ingestion_role: canonical | operational` in its provenance.

**L3 capacity.** `fol.classify_ingestion_role(input_context) → canonical | operational` — uses explicit mode markers, speech-act cues, session context.

**Default.** Conservative — operational unless clearly canonical. Treating an operational statement as canonical could corrupt L2 from unauthorised input.

**L4 authority check.** Is the current session permitted to ingest canonical? Most sessions: operational only. Admins or trusted-source sessions: canonical allowed. Ties into Server-Layer capability checks (likely a `can_write_canonical` or similar, analogous to the existing `can_write_global`).

**Training-signal implication.** Canonical confirmations are high-quality training signal for the GAN-analogous coherence loop (§4.8); operational confirmations are lower quality (they only reflect the system's internal consistency). Weight them differently in the training update.

### 4.8. WSD candidates-as-assumptions with feedback

**Commitment.** WSD does not commit to a single sense when ambiguous. It produces a set of candidates with priors. The FOL layer carries each candidate as an **assumed** statement and lets ledger validation narrow them.

**Pipeline:**
1. Upstream WSD (L3 comprehension) produces `DS_SENSE_CANDIDATES` — per lemma, a set of candidate (sense, prior) pairs. Ideally a singleton; multiple when ambiguous.
2. FOL translation produces one statement set per coherent sense combination, each tagged **assumed** with the sense commitment in the provenance.
3. Assumption statements land in L5's ledger.
4. `fol.validate_assumption` (core L3 capacity, runs after every ledger update) promotes or retracts sense-bound assumptions based on consistency with newly arrived observations.
5. When a sense-assumption is promoted to **inferred**, L4 writes the confirmation back to L5's sense distribution (lemma's candidates narrow).
6. `fol.apply_sense_correlation(confirmed_sense, co_occurring_lemmas)` reads L2's `sense-correlations` role-graph and updates priors for correlated lemmas.

**Walked example — "organism was growing" → "it is alive":**
- Initial: `organism` carries senses a) biological, b) social; `growing` carries a) cell-multiplication, b) adding-members.
- Ledger holds four sense-combination assumptions; two (mixed-category) fail consistency and are retracted immediately.
- Surviving: (organism:a + growing:a), (organism:b + growing:b).
- "it is alive" observed → entails `biological(it)` → promotes organism:a to inferred, retracts organism:b.
- Correlation propagates: growing:a confirmed, growing:b retracted.
- Both senses narrowed in one pass.

**GAN-analogous training (see §5.3 of L4 notes):**
- **Generator:** WSD's sense-ranking model
- **Discriminator:** FOL validation pipeline in L5
- **Signal:** confirmed sense → positive gradient on (context, sense) prior; retracted → negative; undetermined → no signal
- **Training cadence:** during dream-maintenance, fed from *consolidated memories* (L2), not live ledger, for clean causality
- **Weighting:** canonical confirmations weighted higher than operational

**L3 capacities revealed:**
- `fol.enumerate_sense_alternatives(token) → list<sense>` (retrieval)
- `fol.re_translate_with_sense_hint(ledger, sentence_id, hinted_sense) → new_ledger` (comprehension)
- `fol.apply_sense_correlation(confirmed_sense, co_occurring_lemmas)` (retrieval + combination)
- `fol.signal_sense_confirmed` (signalling) — fires on promotion
- `fol.emit_wsd_training_signal(lemma, sense, verdict)` (learning_methods + signalling)

---

## 5. L3 capacity inventory

Organised by the existing twelve-category L3 vocabulary. Each capacity is a fixed, stateless function; none owns state. All read L2 + L5 and return results.

### 5.1. Comprehension (sense-level interpretation + translation)

- `fol.compose_statement_from_parse(parse_with_senses) → DS_FOL_SET` — orchestrates translation
- `fol.tense_to_temporal_anchor(parse) → temporal_constraints` — reads tense features
- `fol.re_translate_with_sense_hint(ledger, sentence_id, sense) → new_ledger`
- `fol.extract_implicit_assumptions(statement, ledger) → DS_ASSUMPTION_CANDIDATES`
- `fol.tag_epistemic_status(statement, tag) → DS_FOL_STATEMENT` (applies structural tag)

### 5.2. Retrieval (reads L2)

- `fol.lookup_category_for_sense(sense) → dolce_category` (reads ontology)
- `fol.lookup_axiom_template_for_relation(relation, category) → axiom_template` (reads ontology)
- `fol.enumerate_sense_alternatives(token) → list<sense>` (reads lexicon)
- `fol.apply_sense_correlation(confirmed_sense, co_occurring_lemmas) → updated_priors` (reads sense-correlations)
- `fol.classify_axiom_strictness(rule) → {analytic, synthetic}` (reads fol-rules)

### 5.3. Derivation (deductive inference)

- `fol.check_consistency(ledger) → DS_CONSISTENCY_VERDICT`
- `fol.check_addition_consistent(ledger, candidate_statement) → DS_CONSISTENCY_VERDICT`
- `fol.localise_conflict(inconsistent_ledger) → DS_CONFLICT_LOCALISATION`
- `fol.entails(ledger, candidate) → DS_ENTAILMENT_RESULT`
- `fol.abduce(ledger, target) → DS_ASSUMPTION_CANDIDATES`
- `fol.justifications_for(ledger, conclusion) → list<stmt_ids>`
- `fol.derive_alternative_forms(rule) → list<equivalent_rule>`
- `fol.validate_rule_against_ledger(rule, ledger) → {supporting, contradicting}`
- `fol.detect_exception_relationship(rule_A, rule_B) → bool`

### 5.4. Combination (synthesis over multiple inputs)

- `fol.instantiate_axiom_template(template, args) → DS_FOL_STATEMENT`
- `fol.extend_rule_with_exception(rule, exception_clause) → refined_rule`
- `fol.compose_rule_with_exception(A, B) → A'`
- `fol.rewrite_strict_as_exception_permitting(rule) → rule` (ontology-maintenance transform)
- `fol.apply_revision(conflict_set, priority_ordering) → revised_ledger`
- `fol.cascade_retract(statement_id, ledger) → retracted_set`
- `fol.falsify_rule(rule, observation) → falsified_rule`
- `fol.archive_falsified_rule(rule, observation) → write_handle` (L2 write helper)
- `fol.assign_default_category(unmapped_sense) → DS_FOL_STATEMENT` (gap-handling)

### 5.5. Decomposition

- `fol.enumerate_unbound_predicates(ledger) → DS_GAP_REPORT`

### 5.6. Scoring

- `fol.score_gap_relevance(gap, task_context) → score`
- `fol.priority.observed_first(conflict_set) → ordering`
- `fol.priority.source_trust(conflict_set, trust_scores_via_context) → ordering`
- `fol.priority.recency(conflict_set) → ordering`
- (additional priority-ranking capacities as needed — each its own L3 capacity)

### 5.7. Trace

- `fol.classify_ingestion_role(input_context) → canonical | operational`

### 5.8. Signalling

- `fol.signal_sense_confirmed(lemma, sense)` — fires on sense-assumption promotion
- `fol.emit_uncertainty_marker(unmapped_sense) → DS_UNCERTAINTY_MARKER` (gap-handling)
- `fol.flag_analytic_contradiction(rule, observation)` — emits to problem-trace with `ontology_revision_pending` tag

### 5.9. Interaction

- `fol.ask_human_for_category(unmapped_sense) → DS_CATEGORY_ASSIGNMENT` (gap-handling)

### 5.10. Learning methods

- `fol.generate_hypothetical_rule(observations, template) → hypothetical_rule`
- `fol.emit_wsd_training_signal(lemma, sense, verdict)` — feeds the coherence loop

### 5.11. Validation (runs after every ledger update)

- `fol.validate_assumption(ledger) → promoted_set, retracted_set` (core capacity — elevated from specialised use)

### Cross-category note

`fol.validate_assumption` is invoked after every ledger write. It is the connective tissue that makes the epistemic-ledger story work: assumptions don't just sit — they're continuously re-evaluated. L4 is responsible for the dispatch cadence.

---

## 6. DataState shapes (structural-only per I2)

### 6.1. Upstream inputs (produced by perception + comprehension)

```
DS_SENSE_CANDIDATES =
  { parse_tree,
    per_content_node: { lemma, candidates: [(sense_iri, prior: float)] },
    tense_features,
    utterance_context }
```

### 6.2. FOL statements and sets

```
DS_FOL_STATEMENT =
  { formula: <fol-expr>,
    epistemic_tag: observed | inferred | assumed | hypothesised,
    provenance: {
      source_utterance,
      derived_from: [stmt_ids],
      sense_commitments: [(token, sense)],
      ontology_rule_id,
      ingestion_role: canonical | operational,
      source_trust: opaque_tag },
    time_bindings: [(var, constraint)],
    is_time_variant: bool }

DS_FOL_SET = ordered list of DS_FOL_STATEMENT

DS_FOL_LEDGER =
  { statements: [DS_FOL_STATEMENT],
    dependency_graph: <stmt_id -> [derived_from]>,
    sense_distributions: <lemma -> [(sense, prior)]>,
    open_gaps: [DS_GAP_REPORT_ENTRY] }
```

### 6.3. Reasoning outputs

```
DS_CONSISTENCY_VERDICT =
  { consistent: bool,
    unsat_core: [stmt_ids] | None,
    anomaly_kind: none | ContradictionWithinLedger | AnalyticContradiction }

DS_ENTAILMENT_RESULT =
  { status: entails | contradicts | independent,
    proof_tree: structured | None }

DS_CONFLICT_LOCALISATION =
  { unsat_core: [stmt_ids],
    tags_in_core: { observed: [...], assumed: [...], inferred: [...] },
    rule_form: strict | exception_permitting,
    candidate_resolutions:
      | retract_assumption(stmt_id, cascade: [stmt_ids])
      | re_translate(sentence_id, alternative_sense)
      | abduce_assumption(missing_clause)
      | falsify_rule(rule_id) }

DS_ASSUMPTION_CANDIDATES = list of candidate DS_FOL_STATEMENT

DS_GAP_REPORT =
  { gaps: [{ predicate, free_vars, provenance }],
    relevance_scores: <gap -> float> | None }

DS_REVISION_PLAN =
  { ordered_steps: [retract | abduce | re_translate | falsify],
    expected_ledger_after_apply }
```

### 6.4. Gap-handling and signalling

```
DS_UNCERTAINTY_MARKER =
  { unmapped_sense, propagated_to: [stmt_ids], confidence_hint: opaque_tag }

DS_CATEGORY_ASSIGNMENT =
  { sense, assigned_category, source: human | default | correlation }
```

---

## 7. L2 role-graph additions

### 7.1. `fol-rules` (new)

Holds rules as first-class entities. Metalinked to `ontology` and `lexicon` via cross-graph MetaEdges.

Node shape (per rule):

```
{ antecedent: <fol-expr>,
  consequent: <fol-expr>,
  provenance: analytic | synthetic,
  status: (synthetic only) active | hypothetical | pending_validation | falsified,
  exceptions: [rule_ids],
  equivalent_forms: [rule_ids],
  source_evidence: [stmt_ids | "definition"],
  falsification_history: [{observation, timestamp}] (may be empty) }
```

**Invariants:**
- Analytic rules have no `status` field and cannot take `falsified` status.
- Analytic rules change only via explicit ontology-revision workflow (outside FOL layer).
- Synthetic rules in `active` status may be falsified by a contradicting canonical observation.
- Falsified rules stay in the graph for learning; they are not deleted.

### 7.2. `sense-correlations` (new)

Co-occurrence patterns between lemma senses. Learned from consolidated memories over time (a dream-maintenance task mines sense co-occurrence statistics from completed MMs).

Node shape:

```
{ lemma_a, sense_a, lemma_b, sense_b,
  correlation_strength: opaque_tag (structural — learned values come from L4 via context),
  evidence_count }
```

Read by `fol.apply_sense_correlation`.

### 7.3. `wsd-model` (tentative)

If committed, this holds the WSD sense-ranking model's parameters as a versioned role-graph. Plugs into the same GAN-analogous coherence loop L4 uses for scoring-capacity parameters.

Marked tentative because we haven't confirmed that the existing `promoted-pipelines` or another role-graph shouldn't host WSD parameters instead. This is a load-bearing open question.

### 7.4. Ontology extensions this design assumes

The `ontology` role-graph must mark:
- Each predicate: `is_time_variant: bool`
- Each rule (if rules are inlined in the ontology rather than in `fol-rules` — a design choice pending): `provenance: analytic | synthetic`, plus exception links

---

## 8. L5 working memory composition (for a FOL-using task)

The Mental Model for a task that uses FOL includes:

- **ledger** — observed + inferred + assumed + hypothesised statements, with tags, provenance, and dependency graph
- **sense_distributions** — per lemma, current candidate senses and priors (continuously updated by validation + correlation)
- **open_gaps** — under-determined predicates the system hasn't filled yet
- **recent_validation_results** — which assumptions were promoted/retracted in the last pass, with dependency fallout
- **pending_revisions** — candidate revision plans not yet applied (if any)

**On task completion:** this state is consolidated into L2's `memories` role-graph via the existing consolidation pipeline. The live L5 instance is released. Retention is the default.

**On pause-and-resume (L4 pause-resume story):** L5 state persists inside the MM, which is persisted. On resume, the ledger is reinstated as live working memory; validation passes re-run against the current L2 to catch any knowledge drift during the pause.

---

## 9. L4 responsibilities (explicit list)

Collected from throughout this design. Each is a decision that depends on confidence learned from experience, and therefore lives in L4.

- **When to invoke FOL at all.** Not every input benefits from translation; learned.
- **Which translator / inference backend / priority rule / revision strategy.** Each strategy is an L3 capacity; L4 picks.
- **Ingestion-role classification dispatch.** Decide whether to run the canonical or operational ingestion pipeline; includes the authority check.
- **Validate-assumption dispatch cadence.** After every ledger write; L4 owns the timing and may batch in high-throughput scenarios.
- **Gap-fill threshold.** Which gaps to fill, how many candidates to accept, at what epistemic tag.
- **Conflict-resolution strategy.** Which priority-ranking capacity to invoke for this conflict; when to abduce vs retract.
- **Falsification decision.** When a contradicting observation is strong enough to falsify a synthetic rule vs. treat as an outlier worth more data.
- **Hypothetical-rule promotion.** When to promote a rule from `hypothetical` to `active`.
- **Ask-vs-default-vs-propagate.** Gap-handling trio dispatch — which to invoke for unmapped senses.
- **Sense-confirmation feedback.** Writing confirmations back to L5 sense distributions.
- **Coherence-loop training dispatch.** Feeds the WSD generator (and any other generators) from consolidated memories.
- **Weighting canonical vs operational confirmations** in the training signal.
- **Pipeline promotion** to L2 `promoted-pipelines` for frequently useful FOL sequences.
- **Mental Model management.** Read + write all of L5's FOL-related state.

---

## 10. Open questions and naming choices pending

**Names:**
- The canonical/operational pair is tentative. Alternatives offered: authoritative/evaluative, teaching/working, constitutive/regulative, ground/claim. User to pick one and we lock everywhere.

**Architectural open:**
- Should the `wsd-model` role-graph be a separate role-graph or should WSD parameters piggyback on an existing role-graph (e.g., `promoted-pipelines`)?
- Does the upstream `DS_SENSE_CANDIDATES` format live in L3 comprehension's DataState vocabulary already, or is this a new DataState the FOL family contributes?
- Always-on vs. deliberate invocation of the FOL layer. Is every input routed through FOL, or only specific task types? (L4 decision; not blocking for L3 design, but shapes when L4 dispatches.)
- Resolve-vs-raise default on conflict. When the FOL layer detects inconsistency, does it attempt automatic revision or surface the anomaly to L4? (L4 decision; shapes the default pipeline.)
- Exact shape of the upstream DOLCE-aligned parse — specifically, how the DOLCE/WordNet alignment is represented per content word.
- Rule rewriting policy — when is `fol.rewrite_strict_as_exception_permitting` invoked, and who invokes it? (Likely a dream-maintenance task; worth pinning.)
- Performance/scale — classical FOL entailment is undecidable in general. The design relies on L4 pruning + preferring decidable FOL fragments on hot paths + letting the full FOL backend handle rare cases. Concrete strategy for this deferred to implementation.

**Verification open:**
- Does DOLCE's QS5 modal logic (alethic) suffice for the epistemic tagging we want, or do we need to extend with epistemic modal operators (`Bel`, `Know`)? The current design punts on this by using tags rather than operators; worth a sanity check with a reviewer familiar with modal logic.
- Deontic reasoning (legal / normative text) — Example 3 in the stress-test queue is specifically chosen to probe this limit. Expect it to be a hard boundary of classical FOL.

---

## 11. Stress-test examples queue

The design is planned to be validated by walking through 6 example inputs end-to-end, each chosen to probe a different pressure. Example 1 has been walked (see §12). Remaining in order: 3 → 2 → 5 → 4 → 6.

1. **Narrative with defeasible assumptions and revision.** "Mary entered the kitchen and poured herself coffee. She sat at the table reading her book." Then later: "Mary is a two-year-old child." **Walked ✓**
2. **Biomedical process description.** "In glycolysis, hexokinase phosphorylates glucose to form glucose-6-phosphate, consuming one ATP molecule." Stresses: ontology coverage (DOLCE's PD/PC vocabulary is thin on biochemistry); forces the gap-handling trio.
3. **Legal conditional with deontic operators.** "If the tenant fails to pay rent within 30 days of the due date, the landlord may terminate the lease by giving 14 days' written notice." Stresses: classical FOL's known limit around deontic modality (may, shall, must). Expected hard boundary.
4. **Multi-source news with contradiction.** Source A: "Candidate X won 52% to 48%." Source B: "Preliminary results show Candidate Y ahead by a clear margin." Stresses: source-trust-driven revision; contradiction localisation across ledgers from different provenances.
5. **Causal/teleological commonsense.** "The plant wilted because it hadn't been watered in a week. Sarah, noticing this, filled a pitcher and watered it." Stresses: abduction, causation, purpose/intent (DOLCE doesn't primitively formalise purpose); multi-sentence reference resolution.
6. **Practical reasoning under goal constraints.** "I want to wash my car. The car wash is 50 meters away. Should I walk or drive?" Stresses: the boundary between declarative logical inference and practical reasoning / action selection; FOL can rule out walking (goal requires `at(car, car_wash)`, walking doesn't satisfy it), but the residual decision is out of FOL's scope.

---

## 12. Example 1 walk-through summary

Input sequence arriving over time:
- **S1:** "Mary entered the kitchen and poured herself coffee."
- **S2:** "She sat at the table reading her book."
- **S3:** "Mary is a two-year-old child."

**After S1.** Translation produces (roughly):
```
∃e1. PD(e1) ∧ enter.v.01(e1) ∧ PC(Mary, e1, t1) ∧ goal_location(e1, kitchen1) ∧ t1 < now
∃e2. PD(e2) ∧ pour.v.01(e2) ∧ PC(Mary, e2, t1+) ∧ theme(e2, coffee1) ∧ recipient(e2, Mary)
APO(Mary) ; NAPO(kitchen1) ; M(coffee1) ; kitchen(kitchen1) ; coffee(coffee1)
```
All observed. Gap-fill produces assumptions: `can_locomote(Mary)`, `can_manipulate_objects(Mary)`, `safe_with_hot_liquid(Mary)`, etc.

**After S2.** Translation adds sitting and reading events; gap-fill assumes `literate(Mary)` and `can_read_fluently(Mary)` from the `read.v.01` sense commitment.

**After S3.** `age(Mary, now) = 2` observed. Combined with the ontology rule (strict form with exception) `∀x. age(x, t) = 2 ∧ ¬prodigy(x, t) → ¬can_read_fluently(x, t)`, the ledger becomes inconsistent unless `prodigy(Mary, now)` is assumed or the sense of "reading" is retranslated.

**Revision branches on rule form:**
- Strict form → `fol.priority.observed_first` chooses; `fol.apply_revision` retracts `can_read_fluently(Mary)`; `fol.cascade_retract` takes down `literate(Mary)`.
- Exception-permitting form → `fol.abduce` produces `prodigy(Mary, now)` as an assumption to satisfy the exception clause, **OR** `fol.re_translate_with_sense_hint` rolls back S2's reading translation to `read.v.04` (pretend-reading). L4 picks which path.

**What this walk exposed and became committed design:**
- Re-translation is a real workflow — revision can loop back to translation.
- Rules are strict; defeasibility lives on assumptions (§4.1).
- Analytic vs synthetic rules with falsification, not weakening (§4.2).
- Time is explicit (§4.3).
- Epistemic tags drive revision priority (§4.4).
- Ledger in L5, not owned by L3 (§4.6).
- Sense alternatives carried as assumptions; `fol.validate_assumption` runs after every update (§4.8).
- Classical FOL throughout — no non-monotonic logic (§4.5).

---

## 13. Meta-architectural observations

**The design stretches, it does not break.** Every pressure from the walked example and from the design discussion has been absorbed by the existing three-lever mechanism (tags + rule transformations + falsification) without requiring a new logic. This is a strong sign that the "classical FOL + discipline" bet is sound.

**The layer discipline is the unifying principle.** Every time the design threatened to drift — "revision picks a priority rule" (L4 not L3), "find gaps" (decompose into enumerate + score + L4-choose), "rules have strength" (no — tag assumptions, not rules) — the fix was to push the fixed/learned split finer. This pattern is load-bearing enough to be worth preserving as advice for future L3 work in other families.

**Translation is largely inherited from the ontology.** The FOL project's value depends heavily on the depth of DOLCE and the DOLCE/WordNet alignment work. Richer ontology → more powerful FOL with no L3 changes. The FOL family is largely a *consumer* of the ontology work, not a parallel effort. Worth stating plainly so expectations are calibrated.

**The ingestion-role distinction is a write-boundary as much as a reasoning one.** Canonical may write L2; operational never can. This asymmetry is the architecturally load-bearing piece, because it protects L2 from unauthorised knowledge updates. The L4 authority check is the enforcement mechanism.

**Performance risk.** The ledger grows continuously (all assumptions carried forward; all sense alternatives; all their dependencies). Mitigations are L4 pruning + preferring decidable fragments on hot paths + batching validation passes. None of this is an L3 concern per se, but the design assumes it works. A concrete scale test is worth doing early.

**The WSD feedback loop unifies training.** WSD plugs into the same GAN-analogous coherence loop L4 uses for scoring parameters. One training skeleton, multiple generators. No bespoke WSD learning machinery. Clean.

---

## 14. References and related sessions

**Foundational paper:**
- Borgo, S. et al. (2022). "DOLCE: A Descriptive Ontology for Linguistic and Cognitive Engineering." Applied Ontology. Uploaded as `DOLCE_FOUST_2022.pdf`.

**Project documentation (in `/Users/henriquealvim/Documents/Claude/Projects/Layered Intelligence/`):**
- `falkormg_capacity_handoff.md` — L3 parent layer handoff
- `falkormg_capacity_adrs.md` — 24 ADRs for L3
- `falkormg_capacity_architecture.md` — L3 Mermaid diagrams
- `falkormg_knowledge_handoff.md` — L2 handoff (DOLCE alignment lives here)
- `knowledge_layer_design.md` — L2 design narrative
- `layer3_system_design_plan.md` — L3 design plan
- `layer4_intelligence_design_notes.md` — L4 design (GAN-analogous loop, three-tier memory, dreaming)
- `layer5_mental_model_design_notes.md` — L5 design (MM-as-working-memory, retention)
- `mindsos_future_plans.md` — post-v1 items from L4 session
- `use_cases_text_realm.md` — NLU and code use cases

**Related local sessions:**
- Layer 0 — Server Architecture (`local_e4add0d4-90ec-46a9-839d-54c8e579664d`)
- Layer 1 — Core Elements (`local_405892a9-958f-4581-bf84-b38281a1b7f6`)
- Layer 2 — Knowledge Layer (`local_7e9516dd-4ebe-4337-aeab-769e04803fbe`)
- Layer 3 — Intellectual Capacity (`local_0caf1b51-5b3b-4d79-8187-f0e18ec2673d`) — parent context for this FOL project
- Layer 4 — Intelligence System (`local_66f73f16-400f-4d3a-82d5-8d678904f0fe`) — GAN-analogous loop defined here
- Expand DOLCE Ontology WordNet Mapping (`local_efd887de-d588-4958-89a5-bff403d51a00`) — DOLCE/WordNet alignment work this FOL layer consumes

---

## 15. Chronological decision ledger

Each entry is a decision reached during the design conversation. Reviewers should check each against the others for coherence.

**2026-04-23 (initial scoping):**
1. FOL is a family of capacities, not one monolithic capability.
2. Framing: epistemic ledger with a reasoning engine attached (ATMS + AGM belief revision as shared vocabulary, not implementation commitment).
3. Capacity decomposition identified: representation, coherence, inference, revision, introspection.

**2026-04-23 (layer discipline applied):**
4. `fol.revise_by_priority_rule` is L4; the priority rules themselves are L3 capacities.
5. `fol.find_gaps` decomposes into L3 `enumerate_unbound_predicates` + L3 `score_gap_relevance` + L4 choice.
6. Translation does not consume raw text; it consumes sense-annotated input from upstream WSD.
7. Priority in revision is parametric — each priority rule is its own L3 capacity.
8. "Coherent" splits into three L3 capacities: logical consistency, plausibility (scoring with L4-learned weights), ontological (reads L2).
9. Boundary-3 split: mechanical epistemic promotions (L3, follow from logical relations) vs policy promotions (L4, require trust judgment).
10. Ledger lives in L5 (per-task working memory); consolidated to L2 `memories` on task completion.
11. FOL vocabulary rides on L2 ontology + lexicon + concepts (no new "FOL vocabulary" role-graph needed).

**2026-04-23 (ontology-driven translation):**
12. Most translation rules live in the L2 ontology (DOLCE provides categories + axiom templates).
13. Translation decomposes into `lookup_category_for_sense`, `lookup_axiom_template_for_relation`, `instantiate_axiom_template`, `compose_statement_from_parse`.
14. New translation rules addable via: (a) extend L2 ontology (universal rules), or (b) Local L3 capacity with `ref_to_global` + `EXTENDS`/`SPECIALISES` (user/domain-specific patterns).
15. FOL project's value depends on ontology depth — it's largely a consumer of ontology work.

**2026-04-23 (gap-handling and stress-test setup):**
16. Gap-handling trio as three L3 capacities: `ask_human_for_category`, `assign_default_category`, `emit_uncertainty_marker`. L4 chooses when to invoke each.
17. Six stress-test examples chosen, order 1 → 3 → 2 → 5 → 4 → 6.

**2026-04-23 (Example 1 walk + rule machinery):**
18. Time is explicit. Every time-variant predicate takes a time argument; `now` anchor; tense emits temporal constraints.
19. New L2 role-graph `fol-rules`, metalinked to `ontology` + `lexicon`.
20. Rules are all strict. Defeasibility lives on assumptions, not rules. (Initial "strictness: strict | defeasible" metadata field dropped.)
21. Rule provenance: analytic vs synthetic.
22. Exceptions handled as antecedent clauses (stays in classical FOL).
23. Rule composition A + B → A' as an L3 capacity.
24. Derivative rule forms (contrapositive, re-indexing) via `fol.derive_alternative_forms`.
25. Contradiction vs abduction branches on rule form: strict → retract; exception-permitting → abduce or re-translate.
26. `fol.validate_assumption` elevated from specialised to core — runs after every ledger write.
27. Sense alternatives carried as assumptions via `DS_SENSE_CANDIDATES`.
28. Re-translation is a real workflow — revision can loop back to translation.

**2026-04-23 (layer audit + falsification):**
29. Synthetic rules have status: `active | hypothetical | pending_validation | falsified`.
30. Falsification, not weakening — synthetic rules contradicted by observation are moved to `falsified` with the observation recorded, not degraded.
31. Analytic rules have no status field. Contradictions raise a flag via problem-trace with `ontology_revision_pending` tag; the ontology-revision workflow (outside FOL layer) picks up.
32. Layer discipline audit: L3 capacities are stateless; read L2 + L5; ledger is L5 working memory, not L3 artifact.
33. WSD feedback loop: sense candidates as assumptions → validation narrows → confirmations write back to L5 sense distributions; optional correlation pass updates co-occurring lemma priors.

**2026-04-23 (ingestion-role and GAN-analogous WSD):**
34. `sense-correlations` confirmed as new L2 role-graph.
35. Ingestion-role distinction: **canonical** vs **operational** (names tentative). Provenance field `ingestion_role` added to `DS_FOL_STATEMENT`.
36. Canonical ingestion may write L2 via revision pipelines (flag analytic contradictions, falsify synthetic rules, integrate consistent additions). Operational ingestion only writes L5; never writes L2.
37. `fol.classify_ingestion_role` as L3 capacity; L4 authority check required before canonical pipeline dispatch.
38. Default ingestion role is operational (conservative).
39. WSD plugs into the GAN-analogous coherence loop as generator; FOL validation pipeline as discriminator. Training fed from consolidated memories, not live ledger.
40. WSD parameters live in L2 (tentative `wsd-model` role-graph).
41. Canonical confirmations weighted higher than operational in the training signal.
42. System rename: falkormg → **MindsOS** (project-level; code packages still use `falkormg_` pending rename).

---

**End of handoff pack.**

*Instructions for the reviewer:* Check this document end-to-end for internal coherence. Specifically:

1. Do the layer placements (L3 / L4 / L5 / L2) hold up under the "fixed vs learned" discipline from §3?
2. Are there contradictions between the rule-system commitments (§4.1, §4.2) and the revision mechanics (§5.3, §5.4)?
3. Is the ingestion-role distinction (§4.7) watertight at the L2 write boundary?
4. Does the classical-FOL-only stance (§4.5) genuinely cover the cases exercised by Example 1 (§12) and anticipated in Examples 2–6 (§11)?
5. Are the L3 capacities in §5 complete for the scenarios the design claims to handle? Are any redundant?
6. Do the DataState shapes in §6 respect the structural-only invariant (I2)?
7. Are there places where the design silently assumes a non-FOL mechanism (e.g., a probability, a learned weight) inside what should be a pure L3 capacity?
8. Is there a simpler / more architecturally elegant story that was missed?

A good review will produce: a list of inconsistencies found, a list of open design choices that need sharpening before implementation, a list of places where the design is sound and can be acted on.
