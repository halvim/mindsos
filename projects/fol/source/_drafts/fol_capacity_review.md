# FOL Capacity Handoff — Architectural Review

**Reviewer:** Claude Opus 4.6 (successor model)
**Reviewing:** `fol_capacity_handoff.md` (v 2026-04-23)
**Cross-checked against:** `mindsos_capacity_handoff.md`, `mindsos_capacity_adrs.md` (ADR-001–022 accepted, 023/024 proposed), `layer4_intelligence_design_notes.md`, `layer5_mental_model_design_notes.md`, `mindsos_knowledge_handoff.md`.
**Stance:** Aggressive — pushes the fixed/learned split further, challenges framings, proposes new capacities.
**Review date:** 2026-04-23

---

## Executive summary

The handoff is, on the whole, well-conceived. The central bet — *classical FOL + epistemic tags on a per-task ledger + rule falsification/refinement* — is a coherent and implementable shape, and the decomposition discipline it inherits from the parent L3 work is visibly applied (most loudly in the priority-ranking family and the gap-handling trio). The layer placements hold up under scrutiny in the large. The ingestion-role distinction is the most important architectural contribution of this pass, and it is sound.

What is not yet safe to implement:

1. **Two framings are load-bearing but misleading.** "No non-monotonic logic" (§4.5) and the "GAN-analogous" WSD loop (§4.8) will lead implementers astray. Fix the naming, keep the architecture.
2. **`now` as a "variable updated each cycle" (§4.3) is not FOL.** It is a parameter with a substitution schedule. This matters because the ledger's stored statements have to record which `now`-value they were minted under, or revision breaks.
3. **Strict-rules-with-exception-antecedents (§4.1) silently assumes a closed-world mechanism.** Making it explicit is a missing L3 capacity, not a footnote.
4. **Several capacities in §5 are still parametric-over-strategy** and violate the decomposition discipline the doc preaches — most notably `fol.classify_ingestion_role`, `fol.generate_hypothetical_rule`, and `fol.check_consistency`.
5. **The L3 inventory is missing primitives** that real inference requires (unification, universal instantiation, bounded-proof variants, exception-closure population, retracted-as-tag, equality handling).
6. **Cross-layer claims ride on proposed-but-not-accepted ADRs** (023, 024) and on a `context` schema L4 has flagged as open (D3).

Full details below, then a prioritised punch list in §G.

---

## A. What is sound and should be preserved

These are the load-bearing commitments the rest of the design rests on, and each checks out.

**A1. Epistemic-ledger framing (§1).** "Not a reasoning engine — a ledger with a reasoning engine attached" correctly locates the value. The ATMS + AGM vocabulary is the right shared anchor without committing to either implementation.

**A2. Fixed/learned decomposition as the guiding principle (§3).** The handoff is correct that the recursive application of this pattern is where the design's cleanness comes from. The three examples called out (revision, gap detection, ingestion) are genuinely decomposed at the right level.

**A3. Ledger in L5, rules in L2, capacities in L3 (§4.6).** The three-way placement is consistent with canonical L3 invariants I1–I2 and with the L5 design note that "L4 is the only writer" to the MM. No drift.

**A4. Ingestion-role distinction as a write boundary (§4.7, §13).** Canonical-may-write-L2 / operational-never-does is the single most load-bearing new decision. It maps cleanly onto the existing `CAN_WRITE_GLOBAL` capability pattern (ADR-019) and gives L4 a natural authority gate. Keep.

**A5. Translation is ontology-driven (§4.8 prelude, §13 meta).** Grounding most translation rules in the L2 ontology rather than in L3 is the right move; it makes the FOL family largely a consumer of DOLCE/WordNet alignment work and avoids recreating a translation vocabulary in L3.

**A6. Derivative forms as explicit rule transformations (§4.5, §5.3).** `fol.derive_alternative_forms` as a rewrite capacity (not as a logic-level extension) is the right place to keep contrapositive / re-indexing. Clean.

**A7. The twelve-category placement map (§5).** With the exceptions noted in §C below, the distribution of FOL capacities across the existing categories is sensible — no new category needed.

---

## B. Real inconsistencies and tensions

These are places the document contradicts itself or contradicts the canonical sibling docs, not merely places where it could be improved.

### B1. "No non-monotonic logic" is a misnomer (§4.5)

The claim *"Classical FOL + epistemic tags on assumptions + rule falsification = defeasibility without leaving first-order logic"* is subtly wrong. The **object-level** inference calculus stays classical; that much is true. But the **meta-level** machinery that adds, retracts, and revises tagged statements on the ledger is exactly the non-monotonic part — standard ATMS is non-monotonic by construction, and the handoff names ATMS as the analogue without flinching. Calling the combined system "classical FOL only" will mislead an implementer into thinking the ledger can be handed to an off-the-shelf FOL prover and left alone.

**Fix.** Re-phrase §4.5 as: *"Classical FOL at the proof layer + non-monotonic ledger dynamics at the meta-layer = defeasibility without modifying the proof calculus."* The architectural commitment is unchanged; the framing stops lying to the reader.

### B2. `now` is not a "variable updated each reasoning cycle" (§4.3)

In FOL, variables are either bound by a quantifier or free; they don't have mutable state across inferences. Treating `now` as mutable makes every previously-inferred statement that mentions `now` retroactively re-interpretable, which silently breaks the dependency graph (§6.2) — an inference justified by `age(Mary, now) = 2` at t₁ should not become an inference about t₂ when the clock ticks.

What is actually meant is one of two things, and the doc should pick:

- **(i) `now` is a substitution parameter.** Each ingestion round substitutes a fresh constant `t_k` for `now` in all new translations. Stored statements retain `t_k` verbatim; the name "now" is a translation-time convenience only.
- **(ii) `now` is a constant anchor with an explicit successor relation.** `now_k`, `now_{k+1}`, with `before(now_k, now_{k+1})` asserted each tick. Stored statements reference the specific anchor.

(i) is simpler; (ii) permits reasoning about cycle ordering. Either is fine. The current wording is neither.

**Related:** §6.2's `DS_FOL_STATEMENT.time_bindings: [(var, constraint)]` doesn't record which `now` was current at mint time. Add `minted_at: time_anchor_iri`.

### B3. Strict-rules-with-antecedent-exceptions silently assumes closed-world completion (§4.1)

A rule of the form `∀x. bird(x) ∧ ¬flightless_bird(x) → fly(x)` fires for Tweety only if the ledger proves `¬flightless_bird(tweety)`. In a pure open-world FOL, absence of `flightless_bird(tweety)` does *not* entail its negation; you must have the negation on the ledger. The handoff does not say who puts it there.

There are only three honest options:

- **CWA on a named predicate set** (cheap, powerful, non-monotonic at the meta-level) — effectively what the system needs; violates the "pure classical FOL" framing unless reframed per B1.
- **Eager population of exception closures** as `assumed`-tagged negations whenever a rule is fetched — this is an L3 mechanism the design currently lacks.
- **Assume-then-check-then-retract at inference time** — implicit abduction of `¬flightless_bird` every time `fly` is queried; expensive, but clean.

**Fix.** Add an L3 capacity:

```
fol.populate_exception_closure(rule, binding) → DS_ASSUMPTION_CANDIDATES
```

Given a rule and a specific entity binding, it enumerates the negated exception antecedents as `assumed`-tagged statements. L4 picks when to invoke (per-query, per-ingestion, batched). This surfaces what is currently hidden and lets Example 1's walkthrough actually run: the current walk-through (§12) requires `¬prodigy(Mary, now)` to be in the ledger before S3 can fire a contradiction, and the document doesn't say who put it there.

### B4. Falsification vs refinement — the criterion is missing (§4.2)

The doc gives `fol.falsify_rule` and `fol.extend_rule_with_exception` as separate capacities but does not say which applies when. Classical example: the first black swan observed. Do you (a) falsify `∀x. swan(x) → white(x)` or (b) refine it to `∀x. swan(x) ∧ ¬australian(x) → white(x)`? These are logically equivalent given the right exception predicate, but epistemically they are very different moves, and an L4 chooser needs a criterion.

**Fix.** Pin a structural criterion in L3, not a learned policy. Proposed: refinement is valid iff the counterexample shares a distinguishing predicate with a proper subclass in the L2 ontology; otherwise, falsification. Encode as:

```
fol.propose_rule_resolution(rule, contradicting_observation, ontology)
  → {kind: refine, exception_predicate: pred} |
    {kind: falsify} |
    {kind: ambiguous, candidates: [...]}
```

L4 still dispatches, but the structural split ensures the choice is grounded.

### B5. `retracted` is a transition target but not a tag (§4.4)

§4.4 says `assumed → retracted`, `inferred → retracted`. But the four tags listed are `observed | inferred | assumed | hypothesised` — no `retracted`. Either retraction means deletion (and `fol.cascade_retract` produces a `retracted_set` that is no longer addressable, breaking `justifications_for` for anything that used to depend on it), or retraction is a fifth tag with archived statements retained.

The doc needs a fifth tag. `retracted` statements should remain in the ledger with their original provenance and a retraction reason, so that (a) justifications stay resolvable, (b) revival on cause-restoration is possible, (c) the consolidated memory has the full epistemic history. Ledger growth is a separate concern (§B9).

### B6. `source_trust: opaque_tag` on `DS_FOL_STATEMENT` is either dead weight or violates I2 (§6.2)

I2 says DataStates carry only structural fields: no confidence, no weights. A field called `source_trust` on a statement is semantically loaded. The only reading that preserves I2 is: it is an *opaque identifier* of a trust source, and the actual scores are looked up elsewhere (context, L2 role-graph). But then §5.6's `fol.priority.source_trust(conflict_set, trust_scores_via_context)` takes scores from `context`, not from the statement, so the statement-level field is unread.

**Fix.** Rename to `source_id: iri` (pure identifier) or remove it entirely and let the translator attach the source IRI as part of `provenance.source_utterance`. If you keep it, document that no L3 capacity reads it.

### B7. `fol.archive_falsified_rule` labelled "L2 write helper" is an L3 statelessness smell (§5.4)

ADR-001 and I1 require L3 capacities to be pure. A capacity returning a "write handle" is fine — but the name and the description ("write helper into L2") invite implementers to let it do the write. Make it structurally impossible by typing the return as `DS_WRITE_INTENT` with an explicit L4-executes convention. Same fix applies, on review, to any capacity whose job description is "archive", "record", "emit to problem-trace" — the emissions must be values, not effects.

Specifically in this doc: `fol.flag_analytic_contradiction`, `fol.emit_wsd_training_signal`, and `fol.signal_sense_confirmed` all describe themselves as "firing" or "emitting". In L3 they must *return a record* that L4 routes to the appropriate sink.

### B8. Cross-layer claims ride on proposed-but-not-accepted foundations

Three places where the FOL handoff assumes something the sibling canon has not yet ratified:

- **ADR-023 (pipeline-generation as L3 capacity) is Proposed.** The FOL handoff's gesture toward L4 "pipeline promotion for frequently useful FOL sequences" (§9) is fine as a promise, but any FOL-level capacity that assumes pipeline-generation is an L3 primitive is jumping the gun. None currently do — but `fol.compose_statement_from_parse` as an "orchestrator" is directionally adjacent. Keep orchestration strictly out of L3.
- **`context` schema (L4 open-concern D3).** The handoff threads `context` through multiple capacities (`trust_scores_via_context`, `task_context`, `input_context`). L4 has not locked the schema beyond `session_user_id` and `session_id` (ADR-022). List every `context`-keyed field the FOL family needs as a contribution to D3, rather than implying they exist.
- **Canonical / operational authority check.** The doc says "L4 authority check ties into Server-Layer capability checks (likely `can_write_canonical` or similar, analogous to `can_write_global`)." This capability does not exist; ADR-019 only grants `CAN_WRITE_GLOBAL`. Explicitly label this as a Server-Layer ADR to be filed, not a capability to rely on.

### B9. Ledger growth is acknowledged but unbounded in design

§13 flags performance; §10 defers to L4 pruning. Both are legitimate. But retaining falsified rules (§4.2), retracted statements (once tag-ified per B5), and all sense-alternative assumptions (§4.8) is an O(inputs × sense_alternatives × dependency-depth) footprint. Worth explicitly stating an L3 capacity for compaction:

```
fol.compact_dead_branches(ledger, policy) → compacted_ledger, archive_delta
```

L4 picks the policy. Without this, L4's "pruning" is a phantom.

---

## C. Capacities that still need decomposition

Per the standing guidance: if a capacity name contains "apply", "classify", "generate", "score", "pick", "judge" — decompose. The following are still parametric-over-strategy and should split.

### C1. `fol.classify_ingestion_role(input_context)` (§5.7)

Classification is typically learned. The doc frames it as "uses explicit mode markers, speech-act cues, session context." Each of those is a distinct signal, and the combination rule is a policy.

**Proposed decomposition:**
```
fol.detect_explicit_mode_marker(input) → {canonical, operational, none}   (L3)
fol.extract_speech_act_features(parse) → DS_SPEECH_ACT_FEATURES              (L3)
fol.extract_session_role_context(context) → DS_SESSION_ROLE_CONTEXT          (L3)
fol.combine_ingestion_signals(signals, policy) → canonical | operational    (L3, policy fixed)
  + one fol.policy.ingestion.* capacity per canonical combination rule      (L3 options)
```
L4 picks the policy. This also makes the default ("conservative — operational unless clearly canonical") one specific policy capacity, not a hidden constant.

### C2. `fol.generate_hypothetical_rule(observations, template)` (§5.10)

"Generate" is doing a lot of work here. Which template? How are observations matched to it? This hides a learned ranking.

**Proposed decomposition:**
```
fol.enumerate_rule_templates_matching(observations) → [template]    (L3)
fol.instantiate_rule_template(template, observations) → rule        (L3, mechanical)
fol.assess_template_coverage(template, observations) → coverage     (L3, structural)
```
L4 picks which template to instantiate, using coverage + learned weights. The name `generate_hypothetical_rule` becomes an L4 pipeline, not an L3 capacity.

### C3. `fol.check_consistency(ledger)` (§5.3)

Consistency checking has many algorithms (resolution, tableaux, SMT-bounded, model-enumeration for finite fragments). Picking one on a hot path is exactly an L4 decision.

**Proposed decomposition:**
```
fol.consistency.resolution(ledger, bound) → DS_CONSISTENCY_VERDICT          (L3)
fol.consistency.tableau(ledger, bound) → DS_CONSISTENCY_VERDICT             (L3)
fol.consistency.smt_bounded(ledger, smt_fragment, bound) → DS_..._VERDICT   (L3)
```
`fol.check_consistency` as a facade belongs in L4 (it picks). Same pattern for `fol.entails` (§5.3) — `fol.entails.resolution`, `fol.entails.tableau`, etc.

### C4. `fol.score_gap_relevance(gap, task_context)` (§5.6)

Gap relevance scoring in the doc gets a single name. But "relevance to what" has at least three distinct answers:

- relevance to the *current pipeline's next predicted input*
- relevance to the *task's stated goal*
- relevance to *previously-satisfied patterns* (memory-weighted)

**Proposed decomposition:**
```
fol.score_gap.next_input_alignment(gap, predicted_shape) → score     (L3)
fol.score_gap.goal_alignment(gap, goal_spec) → score                 (L3)
fol.score_gap.memory_weighted(gap, memory_pattern) → score           (L3)
```
L4 picks which scorer(s) to run and how to combine.

### C5. `fol.tense_to_temporal_anchor(parse)` (§5.1)

The conversion tense → temporal constraint depends on a choice of tense semantics (Reichenbach's reference/speech/event-time triad, Allen's interval algebra, a simple relative-to-now scheme). Each is a distinct mechanical transform.

**Proposed decomposition:**
```
fol.tense_to_temporal.reichenbach(parse, now) → constraints   (L3)
fol.tense_to_temporal.allen_interval(parse, now) → constraints (L3)
fol.tense_to_temporal.relative_to_now(parse, now) → constraints (L3)
```
L4 picks which scheme for this sentence's features (e.g., past-perfect forces Reichenbach if Allen is being used elsewhere).

### C6. `fol.abduce(ledger, target)` (§5.3)

Abduction has several strategies: minimal abduction, weighted minimum-cost, prime implicates, KB-directed. Same decomposition pattern.

---

## D. Missing primitives

The inference calculus needs mechanics that aren't in §5.

### D1. Unification and substitution

```
fol.unify(term_a, term_b) → DS_SUBSTITUTION | fail
fol.apply_substitution(formula, substitution) → formula
```
Required for any non-trivial `entails` / `abduce` and for `fol.re_translate_with_sense_hint`'s re-indexing.

### D2. Universal instantiation

```
fol.instantiate_universal(rule, binding) → ground_instance
```
Required for applying a `∀x. P(x) → Q(x)`-shape rule to a specific Mary. The doc hints at this via `fol.instantiate_axiom_template` but that capacity consumes axiom *templates* (meta-level constructs from the ontology), not generic ∀-quantified rules.

### D3. Skolemization

```
fol.skolemize(formula) → skolem_formula
```
Required to turn existentials in antecedents into Skolem constants for proof procedures. Not strictly necessary if you commit to proof-search without Skolemization, but then say so.

### D4. Bounded-proof variants

```
fol.entails.bounded(ledger, candidate, bound) → {entails, contradicts, unknown_within_bound}
```
FOL entailment is semi-decidable (confirmable but not refutable). The doc's promotion rule "assumed → inferred when ledger entails the assumption" (§4.4) is therefore *one-sided in practice*: you can promote when proof is found, never demote a non-promotion. Call this out and use the bounded variant on hot paths.

### D5. Exception closure population

See B3.

### D6. Retracted-as-tag plumbing

See B5. A fifth tag needs a carrier field, retraction reason, and revival mechanics:
```
fol.revive_retracted(statement_id, ledger) → ledger  (when cause re-enters)
fol.retraction_reason(statement_id, ledger) → reason_record
```

### D7. Equality handling

FOL without equality is anaemic for ontology work. DOLCE depends on equality constraints (mereology axioms use `=`). The doc never names equality. Options: (a) equality axioms (reflexivity, symmetry, transitivity, substitution) as analytic rules in the `fol-rules` graph; (b) built-in equality with paramodulation in the prover. Pick and state.

### D8. Sortedness

DOLCE is many-sorted (ED, PD, Q, AB). The handoff does not say whether the FOL is many-sorted or single-sorted-with-type-predicates. This matters for translator output shape, for performance (sorted proofs prune aggressively), and for what `fol.lookup_category_for_sense` actually returns. Pin this.

---

## E. Semantic and framing refinements

Not contradictions, but places the framing will cost you credibility or correctness.

### E1. "GAN-analogous" is a stretch (§4.8)

In a GAN, both generator and discriminator are parameterised and trained adversarially. Here the "discriminator" is a fixed logical-validation pipeline — it does not train. The correct name for this shape is **oracle-supervised learning** or, more precisely, **distant-supervision via downstream consistency** (the generator learns from labels emitted by a logical oracle). The "gradient" the doc describes (positive on confirmed, negative on retracted) is a supervised-learning signal, not an adversarial loss.

Why it matters: implementers reading "GAN" will reach for a GAN training loop and an adversarial loss, which is wrong. Rename and the design is clearer, not weaker.

**Proposed re-framing:** *"WSD's sense-ranker is trained under oracle-distant-supervision by the FOL validation pipeline. Confirmed senses are positive labels; retracted senses are negative labels; consolidated-memory replay supplies the training stream."*

### E2. "Analytic" vs "synthetic" drags in Kantian baggage that doesn't fit (§4.2)

Real ontology entries rarely decompose cleanly into *true-by-meaning* vs *true-by-observation*. Colour terms, kinship terms, biological species, legal concepts — all contested, all partly definitional, partly empirical. The doc handles edge cases by triggering "ontology revision" on analytic contradictions, which is fine, but the binary framing will cost you cleanliness downstream.

**Proposed replacement:** a provenance tag `source: ontology_taxonomy | ontology_axiom | observation | learned_pattern | human_declared`. Each source implies its own revision workflow. More precision, less philosophy.

### E3. "Canonical" vs "operational" — the list of alternatives is too narrow (§4.7)

None of the offered pairs (canonical/operational, authoritative/evaluative, teaching/working, constitutive/regulative, ground/claim) captures a third case that the L4 design actually generates: **self-generated hypotheses from dreaming** and **sensor observations**. These are neither taught by an external source nor operational-query-against-knowledge. Two possibilities:

- Promote the binary to an enum: `{taught, queried, observed, hypothesised}` — taught and observed may both permit L2 writes under different authority checks; queried never does; hypothesised writes only to L5 sandbox graphs.
- Keep binary and broaden "canonical" to include sensor/self: provenance sub-field carries the finer origin.

The binary-plus-provenance route is simpler.

### E4. "Defeasibility lives on assumptions" — a tighter version (§4.1)

The phrase is right-ish but blurs a real distinction: some assumptions are *candidate alternatives* (e.g., sense alternatives), others are *defaults* (gap-filled `literate(Mary)`), and others are *abduced explanations* (Mary-as-prodigy to preserve the rule). These three have different revision policies, different provenance, and different promotion criteria. Consider adding an `assumption_kind: candidate | default | abduced` sub-field to `DS_FOL_STATEMENT.provenance` to keep L4's policy space crisp.

### E5. "Rule of thumb: mechanical in L3, policy in L4" (§4.4) needs a caveat

The rule is correct *if* you can run the mechanical check in bounded time. Since FOL entailment is semi-decidable, the mechanical check may not terminate in practice, at which point the "mechanical" L3 capacity degenerates into "L4 decides whether to wait longer." Either (a) require bounded variants in L3 (per D4), or (b) explicitly document that the mechanical promotions are *attempted* in L3 and L4 decides whether the unknown-within-bound outcome counts as demotion.

### E6. The "always stretches, never breaks" meta-observation (§13) is premature

Example 1 was the softest of the six stress tests. Examples 3 (deontic) and 5 (teleological/causal) are genuinely harder; Example 6 is acknowledged to be out of scope. Claiming the design "stretches, does not break" before running the hard cases is a hostage to fortune. Rephrase as provisional: *"So far, Example 1 has been absorbed by the existing machinery. Examples 2–6 remain to be walked."*

### E7. Deontic is not as hard as §11 implies

Example 3 is flagged as "expected hard boundary of classical FOL." It is, *if* you try to capture deontic modality semantically. If you capture `May(φ)`, `Shall(φ)`, `Must(φ)` as **syntactic predicates** (uninterpreted by the prover, interpreted by a deontic-aware pipeline further downstream), classical FOL has no problem representing the legal text. The hard bit — reasoning about permissions and obligations consistently — is a separate capacity family, not a limit of FOL. Soften the expectation.

---

## F. Answers to the handoff's own review questions (§15)

**1. Do the layer placements hold up under fixed-vs-learned?** Mostly yes. Exceptions: `fol.classify_ingestion_role` (C1), `fol.generate_hypothetical_rule` (C2), `fol.check_consistency` and `fol.entails` (C3). After the decompositions in §C these hold up.

**2. Contradictions between the rule-system commitments (§4.1, §4.2) and revision mechanics (§5.3, §5.4)?** One real issue: §4.1's strict-rules-with-exception-antecedents requires negated-exception assumptions to be on the ledger before revision can fire, and no capacity produces them (§B3). One ambiguity: falsification-vs-refinement criterion is missing (§B4). Both fixable with additions, not restructuring.

**3. Is the ingestion-role distinction watertight at the L2 write boundary?** The *rule* is watertight (operational never writes L2). The *enforcement* depends on an authority capability (`can_write_canonical` or similar) that does not yet exist in the Server layer (§B8). Until filed as a Server ADR, the boundary is policy-not-mechanism.

**4. Does classical-FOL-only cover Examples 1–6?** Example 1: yes, once B3 is fixed. Example 2 (biomedical): will pressure ontology coverage more than logic; should work. Example 3 (deontic): only if deontic operators are treated as syntactic predicates (§E7). Example 4 (multi-source): yes — prioritisation capacities handle this. Example 5 (teleological/causal): abduction handles causation; DOLCE's thinness on purpose will be the binding constraint. Example 6 (practical reasoning): explicitly out of scope, correctly.

**5. Are §5 capacities complete? Redundant?** Not complete — missing unification, universal instantiation, Skolemization, bounded entailment, exception-closure population, retraction-as-tag mechanics, equality, compaction (D1–D7, B9). Mostly not redundant, with one call: `fol.check_addition_consistent` is a trivial specialisation of `fol.check_consistency` and does not need to be its own capacity unless the implementation uses incremental proof reuse, in which case document that.

**6. Do the DataStates respect I2?** Mostly yes. One infraction: `source_trust: opaque_tag` on `DS_FOL_STATEMENT.provenance` is a semantic weight wearing a structural disguise (§B6). Fix: rename or remove.

**7. Places where design silently assumes non-FOL mechanism inside L3?** Three:
- `context`-passed trust scores used inside `fol.priority.source_trust` — fine under I1, but the weight source should be explicitly named (L2 role-graph? L4 process memory?) not just "via context".
- WSD's generator parameters read by the sense-ranking model — lives in L2 `wsd-model` per §7.3; currently "tentative." Pin it.
- Gap-relevance scoring weights (C4) — same story.

**8. Simpler alternatives missed?** Two modest ones:
- **Ledger-as-diff:** Instead of maintaining a full ledger per task, maintain a diff against a "current world model" snapshot. Cheaper, cleaner semantics for cross-task inference. The downside is weaker audit trail — probably not worth it, but worth discarding explicitly.
- **Drop the analytic/synthetic binary** (§E2) in favour of a provenance enum. Less philosophy, same mechanism.

---

## G. Prioritised punch list

Ordered by *blocking-for-implementation* first, then *clarifying*, then *nice-to-have*.

**Must fix before the "how" phase:**

1. **Add `fol.populate_exception_closure`** (§B3, §D5). Without it, strict-rule-with-exceptions cannot actually fire. Blocks Example 1's walkthrough.
2. **Add a fifth epistemic tag `retracted`** and the revival mechanics (§B5, §D6). Without it, cascade-retract breaks justification tracking.
3. **Decompose `fol.classify_ingestion_role`** (§C1). Currently violates the decomposition discipline; the combination policy hides an L4 decision.
4. **Pin `now` semantics** (§B2). Pick substitution-parameter or anchor-constant. Add `minted_at` to `DS_FOL_STATEMENT`.
5. **State the missing inference primitives** as committed L3 capacities: `fol.unify`, `fol.instantiate_universal`, `fol.entails.bounded` (§D1, D2, D4). Skolemization optional but document the choice.
6. **Add the falsification/refinement criterion** as `fol.propose_rule_resolution` (§B4). L4 needs a grounded choice.
7. **File a Server-Layer ADR** for `CAN_WRITE_CANONICAL` (or equivalent), or rescope §4.7's authority-check claim (§B8).

**Fix before locking v1:**

8. **Rename §4.5** to "classical FOL proof calculus + non-monotonic ledger dynamics" (§B1). Implementers will thank you.
9. **Rename §4.8's GAN analogy** to oracle-distant-supervision (§E1). Same reason.
10. **Drop or rename `source_trust: opaque_tag`** (§B6). It's either dead or it violates I2.
11. **Decompose `fol.generate_hypothetical_rule` and `fol.check_consistency` / `fol.entails`** (§C2, C3). Parametric over strategy = separate capacities.
12. **Add `fol.compact_dead_branches`** (§B9). L4's pruning story needs a mechanism.
13. **Clarify which capacities return write intents** vs executing writes (§B7). Uniform `DS_WRITE_INTENT` return type for archive/flag/emit capacities.

**Sharpen in a design-notes pass:**

14. Replace analytic/synthetic with a provenance enum (§E2).
15. Broaden ingestion roles or add assumption_kind sub-field (§E3, §E4).
16. Commit on equality handling (§D7) and sortedness (§D8).
17. Soften §13's "stretches-not-breaks" and §11's deontic-is-hard framings (§E6, §E7).
18. Decompose `fol.tense_to_temporal_anchor`, `fol.score_gap_relevance`, `fol.abduce` into strategy-families (§C5, C4, C6).

**Items the doc already flags correctly and just needs to keep on the table:**

- Ontology-coverage dependency (§13 meta).
- Performance / scale — now expanded via B9 and D4.
- `wsd-model` role-graph location (§10 open) — pin against the broader `context`/parameters discussion per B8.
- Stress tests 2–6 still to walk.

---

## H. One-paragraph verdict for the user

The design is salvageable as written but not yet safe to start coding. The fixes in §G items 1–7 are genuine prerequisites — not stylistic cleanups — because they close concrete semantic holes (exception closure, retraction tag, `now` semantics, missing inference primitives) that Example 1 already exposes if you squint. Items 8–13 are cleanup that will save you from confused implementers. The architectural shape — ledger in L5, strict rules in L2, stateless capacities in L3, ingestion-role as a write boundary, WSD-as-assumption with downstream oracle feedback — is good and should be preserved. The failure mode the doc is closest to is over-confidence in its own framings ("no non-monotonic logic", "GAN-analogous"); the fix is to rename, not to re-architect.

---

*End of review.*
