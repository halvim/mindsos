# MindsOS Use Cases — Text Realm

**Purpose.** Concrete end-to-end use cases exercising all five layers of the MindsOS system in the text domain. Two realms are covered: **natural language understanding (NLU)** and **code understanding**. A cross-realm use case ties them together. These use cases are the test suite against which L3 implementation, L4 design, and L5 retention policy are validated.

**Scope.** Text-only by design — no vision, audio, or sensorimotor modalities. This keeps the examples concrete and testable while still exercising every layer of the architecture.

**Status.** Companion to `layer3_system_design_plan.md`, `layer4_intelligence_design_notes.md`, and `layer5_mental_model_design_notes.md`. All three documents point back here.

---

## Format

Each use case specifies:

- **Input.** What the system receives.
- **Expected output.** What success looks like.
- **L1 substrate.** What Core primitives are touched (usually trivial).
- **L2 knowledge consulted.** Role-graphs and kinds of entries read.
- **L3 capacities invoked.** Concrete capacity nodes (with the `<category>.<name>` convention).
- **L4 intelligence required.** Pipeline-finding, strategy, confidence, orchestration, triage, dreaming.
- **L5 Mental Model.** What is written to working memory and retained after.
- **Stress-tests.** Which design risks this case exposes, and which gaps to watch for.

Capacity names below are illustrative — the vertical slice will settle final naming.

---

## Realm 1: Natural Language Understanding

### UC-NLU-1 — Winograd-style pronoun resolution

**Input.** A sentence with an ambiguous pronoun, e.g. *"The city councillors refused the demonstrators a permit because they feared violence."*

**Expected output.** "they → the councillors" with a confidence score and a justification (the propositions consulted, the frame matched).

**L1 substrate.** Identity for the parsed sentence structure; instancing for the Mental Model.

**L2 knowledge consulted.**

- `lexicon` — pronoun agreement features, word-sense senses for `refuse`, `permit`, `fear`, `violence`.
- `ontology` — concept hierarchy: `councillor ⊏ civic_authority`, `demonstrator ⊏ civic_actor`, `permit ⊏ legal_document`.
- `concepts` — frame-like knowledge: "authorities denying permits because they fear violence" is a known schema; FrameNet's `Refusal`, `Fear` frames.
- Optional: `world_priors` — civic-interaction priors (authorities exercise denial power; fears expressed in institutional contexts more commonly attributed to decision-maker).

**L3 capacities invoked.**

- `perception.text_ingest` (raw_text → raw_text DataState)
- `text.tokenize`, `text.sentence_split`, `text.pos_tag`, `text.dependency_parse`
- `comprehension.wsd` (word-sense disambiguation against `lexicon`)
- `comprehension.ner`, `comprehension.relation_extract`
- `derivation.coreference_candidate_gen` (surface pronoun → candidate antecedents)
- `derivation.frame_match` (sentence → matching FrameNet frames)
- `derivation.plausibility_score` (for each candidate, compute frame-fit score against L2)
- `path-finding.a_star` (find reasoning path from candidate to supporting L2 proposition)
- `scoring.confidence` (aggregate into final confidence)
- `interaction.ask_user` (if confidence below threshold)

**L4 intelligence required.**

- **Task-pattern recognition.** L4 recognises this shape as "Winograd coreference" and runs a `capacity:retrieval.by_task_type("winograd_coref")` over L2's `memories` role-graph to use similar past runs as seeds.
- **Pipeline-finding.** Pick a shallow pipeline first (syntactic + agreement-only); if confidence low, escalate to the semantic pipeline (frame-match + plausibility-score).
- **Scorer composition.** Compose the plausibility score across candidates using a multi-objective scorer (frame-fit, propositional support, agreement).
- **Human-in-the-loop.** If the top two candidates are within a confidence-delta threshold, ask the user.
- **Triage.** Was this resolution correct? If yes, L4 may promote the pipeline path used; if no, update confidence downward.

**L5 Mental Model produced.**

- Pipeline DAG (shallow or escalated).
- Each candidate antecedent as a `NodeInstance` with its score.
- L2 propositions consulted as `ref:global_*` node instances.
- The chosen frame match as a `CompositeInstance`.
- Outcome metadata: confidence, escalation flag, human-consulted flag.

**Stress-tests.**

- Does the DataState type system cleanly separate "parsed sentence" from "candidate antecedent list" without needing richness tags?
- Does `path-finding.a_star` over the L3 metagraph actually find the escalation pipeline without an explicit script?
- Can L4 use a retrieved memory as a seed, or does cold-start require a hand-written strategy?
- When the correct answer requires propositional knowledge not in L2, does the system gracefully fall through to asking the user?

---

### UC-NLU-2 — Novel-word meaning inference from context

**Input.** A sentence with an unknown lexeme, e.g. *"The glorp burst across the horizon at dawn."*

**Expected output.** A plausible meaning hypothesis for `glorp` (e.g. "a sunrise-adjacent visible phenomenon — candidate senses: sun, light beam, vessel, flock"), with per-candidate confidence. Optionally, a proposal to add `glorp` as a Local lexicon entry aligned to the best sense.

**L2 knowledge consulted.**

- `lexicon` — all lexemes that fit the structural slot (subject of `burst across horizon at dawn`).
- `FrameNet` — frames matching "X burst across Y at time-of-day", e.g. `Motion`, `Emanation`.
- `concepts` — entities that plausibly "burst across the horizon at dawn" (sun, armies, fleets, dawn-phenomena).
- `ontology` — type candidates for `glorp` given the frame.

**L3 capacities invoked.**

- `text.tokenize`, `text.dependency_parse`
- `comprehension.frame_match`
- `derivation.slot_filler_candidates` (given frame + slot, enumerate L2 entities that fit)
- `derivation.abductive_hypothesis_gen` (given candidate, propose "X could mean Y" hypothesis)
- `scoring.frame_fit`, `scoring.prior_plausibility`
- `interaction.ask_user` (optional — confirm the best candidate)

**L4 intelligence required.**

- **Abduction as an L4 move.** Abduction is not a single L3 capacity — it's a composition L4 constructs (frame-match → slot-candidates → rank → confirm).
- **Confidence thresholding.** If the top candidate is clear, auto-propose; otherwise defer to user.
- **Proposal routing.** If confirmed, L4 writes a Local lexicon entry for `glorp` to L2 with `ref:global_<sense>` pointing at the confirmed sense.

**L5 Mental Model produced.**

- Frame match and slot analysis.
- Candidate senses as ranked `NodeInstance`s.
- The user's confirmation (if asked) recorded as an interaction event.
- The new Local lexicon entry referenced via `ref:local_lexicon`.

**Stress-tests.**

- Does L4 successfully decompose "infer meaning" into a pipeline without having been explicitly taught this decomposition?
- Does the Global/Local KL split handle "glorp" being written only to Local?
- Can the system distinguish between "I am confident" and "I have one candidate" — different failure modes of a short candidate list?

---

### UC-NLU-3 — Question answering over the knowledge base

**Input.** A natural-language question, e.g. *"What animals eat plants and live in water?"*

**Expected output.** A list of candidates (e.g. `{manatee, tadpole, iguana, hippopotamus}`) with confidence scores and their supporting L2 entries.

**L2 knowledge consulted.**

- `ontology` — `animal` hierarchy, diet relations, habitat relations.
- `lexicon` — parsing "eat plants" and "live in water" to their relation forms.
- `concepts` — herbivory, aquatic habitat.

**L3 capacities invoked.**

- `text.tokenize`, `text.dependency_parse`
- `comprehension.question_decompose` (decompose into constraints: `subject: animal`, `diet: plant`, `habitat: water`)
- `comprehension.ner`, `comprehension.relation_extract`
- `derivation.constraint_translate` (natural language → L2 graph query)
- `path-finding.constraint_satisfaction` (over L2 graph)
- `scoring.relevance`, `scoring.confidence`
- `interaction.ask_user` (for ambiguous constraints)

**L4 intelligence required.**

- **Question decomposition.** Break the question into independent L2-queryable constraints; recognise that "eat plants AND live in water" is a conjunction.
- **Pipeline selection.** For simple constraints, direct L2 query; for vague ones, hybrid (L2 + inference).
- **Fallback.** If no results, broaden (e.g. drop "live in water"); if too many, narrow.

**L5 Mental Model produced.**

- The constraint decomposition.
- The L2 queries issued.
- The candidate set with supporting entries.
- Broadening/narrowing decisions.

**Stress-tests.**

- Does L3 have the capacities for constraint-translation and constraint-satisfaction, or does this collapse into L4 custom code?
- Do DataStates cleanly represent a "partial constraint set" without needing a new type each time?
- Does dreaming pre-compute answers to common questions, or does it rebuild from scratch every time?

---

## Realm 2: Code Understanding

### UC-CODE-1 — Describe what this function does

**Input.** A Python function source, e.g.

```python
def publish_digest(users, since):
    events = load_events(since=since)
    digests = {u.id: format_digest(u, events) for u in users if u.subscribed}
    for uid, body in digests.items():
        send_email(user_id=uid, body=body)
    return len(digests)
```

**Expected output.** A one-sentence summary ("Builds per-user digests from events since a given time and emails subscribed users, returning the count sent") plus a list of side-effects ("network I/O via `send_email`", "reads from `load_events`").

**L2 knowledge consulted.**

- `ontology` — programming concepts: function, loop, dict-comprehension, side-effect categories.
- `lexicon` — decompose identifiers: `publish_digest` → `publish`, `digest`; `load_events` → `load`, `events`.
- `concepts` — what "publish", "digest", "subscribe", "email" mean in software context.
- Project-specific knowledge (if present): module boundaries, function owners, import graph.

**L3 capacities invoked.**

- `code.ast_parse`
- `code.identifier_split` (snake_case, camelCase)
- `code.call_graph_walk`
- `code.side_effect_detect` (I/O operations, mutation, exception-raising)
- `comprehension.identifier_glossary_lookup` (identifier → L2 concept)
- `derivation.intent_infer` (function body → functional intent)
- `derivation.paraphrase_gen` (intent → one-sentence summary)
- `scoring.summary_quality`

**L4 intelligence required.**

- **Pipeline selection.** For short, obvious functions: identifier-based heuristic. For complex ones: full call-graph walk + side-effect analysis.
- **Retrieval seeding.** `capacity:retrieval.by_input_shape(function_ast)` pulls memories of similar past function-summarisation tasks to seed the pipeline.
- **Confidence gating.** If summary quality score is low, ask the user to confirm or correct.

**L5 Mental Model produced.**

- AST and call-graph fragments as `NodeInstance`s.
- Identifier decomposition and L2 concept mappings.
- Intermediate intent representation.
- Final summary and side-effects list.

**Stress-tests.**

- Does the DataState type system distinguish "AST" from "call-graph" from "intent" cleanly without richness tags?
- Does auto-discovery produce the right type-compat edges for the code pipeline, or does this require many manual constraint edges?
- Does `capacity:retrieval.by_input_shape` actually find useful neighbours among past function-summary memories, or does AST fingerprint similarity need its own tuning per code realm?

---

### UC-CODE-2 — Localise a bug from stack trace + bug report

**Input.** A stack trace and a natural-language bug report. Example:

```
Report: "Dashboard fails to render for enterprise users."
Trace:
  File "billing/plans.py", line 87, in features_for
    return self._features[plan_tier]
KeyError: 'enterprise'
```

**Expected output.** A ranked list of candidate fix sites (with the top candidate being `billing/plans.py:80-95`, the `_features` initialisation), a proposed diagnosis ("missing `enterprise` key in `_features` dict"), and a suggested minimal patch.

**L2 knowledge consulted.**

- `ontology` — error-type hierarchy (`KeyError ⊏ LookupError`).
- `concepts` — "missing key" as a fault pattern; common causes (new tier added to enum but not to lookup).
- Project-specific: module ownership, recent changes, known-similar bugs.

**L3 capacities invoked.**

- `perception.stack_trace_parse`
- `comprehension.bug_report_extract` (NL → structured {symptom, affected_user_class})
- `code.ast_parse`, `code.import_graph_walk`, `code.symbol_resolve`
- `derivation.symptom_to_cause_gen` (fault-pattern matcher)
- `path-finding.bfs` (call graph from top-of-stack)
- `scoring.relevance`, `scoring.likelihood`
- `derivation.patch_suggest`

**L4 intelligence required.**

- **Pipeline selection** between three strategies: top-frame-first (follow the stack), message-match (find sites that raise this error), recent-diff (which recent commits touched relevant code). L4 learns which strategy works for which bug class.
- **Fallback composition.** If the top strategy finds nothing, fall through.
- **Human-in-the-loop.** If confidence on the fix site is low, ask the user before proposing a patch.

**L5 Mental Model produced.**

- Parsed trace and bug report.
- The strategy chosen and the candidates it produced.
- The alternatives considered and their scores.
- The suggested patch.

**Stress-tests.**

- Does L3 have the code-analysis capacities to support all three strategies, or does implementation stall on capacity gaps?
- Can L4 track per-strategy-per-bug-class confidence via `promoted-pipelines` records (one record per strategy + bug class) without per-capacity confidence-pollution in L3?
- Does the consolidated memory in L2 support later comparison via `capacity:retrieval.by_pipeline_shape`: "the same bug in a sibling module was localised via a different strategy — why?"

---

### UC-CODE-3 — Find similar code (pattern-based retrieval)

**Input.** A code snippet the user highlights and the question *"Where else in the codebase is this pattern used?"*

**Expected output.** A ranked list of locations (file, line range, similarity score) plus a description of the shared pattern.

**L2 knowledge consulted.**

- `ontology` — code-pattern taxonomy (loops, dispatch, context-manager, etc.).
- Project-specific: file index, AST cache.

**L3 capacities invoked.**

- `code.ast_parse`, `code.normalise_ast`
- `derivation.pattern_extract` (AST → pattern fingerprint)
- `path-finding.structural_isomorphism` (over the AST index)
- `scoring.similarity`
- `derivation.pattern_describe_nl` (fingerprint → NL description)

**L4 intelligence required.**

- **Similarity threshold tuning.** L4 learns what "similar enough" means for this user's codebase.
- **Index use.** If the AST index exists, use it; otherwise scan (expensive).
- **Result pruning.** Return top N by learned preference.

**L5 Mental Model produced.**

- The input pattern fingerprint.
- Each match as a `NodeInstance` with its similarity score.
- The pattern description.

**Stress-tests.**

- Does the architecture accommodate "structural isomorphism" as a reusable L3 capacity, or does it live only in code understanding?
- Can this capacity be repurposed for analogy (see `layer3_concerns.md`) — or is structural isomorphism inherently per-realm?

---

## Cross-realm

### UC-X-1 — "Where in the codebase do we handle X?" (NL question about code)

**Input.** A natural-language question combining NLU and code understanding, e.g. *"Where does the billing system retry failed charges?"*

**Expected output.** A list of call sites with confidence scores and a short explanation of how each one implements retry.

**L2 knowledge consulted.**

- `lexicon`, `ontology`, `concepts` — to decompose "billing system", "retry", "failed charges".
- Project-specific: module glossary (which modules are "billing"), term mappings (codebase-specific name for "retry" may be `backoff`, `rekick`, etc.).

**L3 capacities invoked.**

- NLU capacities: `text.tokenize`, `comprehension.question_decompose`, `comprehension.ner`.
- Code capacities: `code.module_find`, `code.symbol_search`, `code.ast_pattern_match`.
- Bridging: `derivation.concept_to_codebase_term_map` (consults the codebase glossary in L2).
- `scoring.relevance`.

**L4 intelligence required.**

- **Two-phase pipeline-finding.** Phase 1 uses NLU capacities; phase 2 uses code capacities. L4 must orchestrate the hand-off — the DataState produced by phase 1 (structured-question) must flow into phase 2 as a code-search spec.
- **Cross-realm DataState design.** The output of `comprehension.question_decompose` must be consumable by `code.module_find`. This is the stress test for whether the DataState type system is expressive enough without richness tags.
- **Cross-realm retrieval.** `capacity:retrieval.by_task_type("nl_code_bridge")` pulls past cross-realm memories as seeds; `capacity:retrieval.by_pipeline_shape` surfaces the NLU→code hand-off patterns that have previously worked.

**L5 Mental Model produced.**

- Two sub-pipelines (NLU and code) with their hand-off DataState.
- Both L2 realms' knowledge consulted.
- The final ranked results.

**Stress-tests.**

- Does one DataState cleanly bridge the two sub-pipelines, or does it need a dedicated `code_search_spec` DataState and an adapter?
- Does L4's pipeline-finder propose this hybrid, or does it fall back to asking the user how to bridge?
- Does the Global/Local L3 split handle one capacity being Global-only (e.g. `comprehension.question_decompose`) and another being Local (e.g. project-specific `code.module_find`)?

---

## Dreaming use cases

**A dream is a task.** Each dream below is a task with its own pipeline, its own live Mental Model, and its own consolidated memory on completion. Every dream pipeline begins with a `capacity:retrieval` step over L2's `memories` role-graph; the retrieved memories feed downstream L3 capacities (re-run, compare, propose, mine).

- **Dream-1 (Maintenance).** Pipeline: `retrieval.by_task_type("winograd_coref")` → re-score each retrieved memory's pipeline against the current L2 version → `derivation.diff_detect` → if drift found, emit a maintenance proposal (update confidence on the relevant `promoted-pipelines` record, or flag the frame/lexicon entry that changed).
- **Dream-2 (Exploration).** Pipeline: `retrieval.by_capacity_used("code.ast_pattern_match")` → for each memory, `derivation.alternative_pipeline_gen` → re-run → compare against the original outcome → if the alternative wins on cached inputs, propose a new Local adapter (e.g. cross-codebase structural isomorphism for UC-CODE-3).
- **Dream-3 (Retry).** Pipeline: `retrieval.by_result("failed")` → follow each memory's `ref:problem_trace` to understand the failure → `derivation.alternative_pipeline_gen` (guided by the problem-trace) → re-execute → on success, update the memory (`outcome: succeeded_on_retry`) and propose promotion of the alternative.
- **Dream-4 (Analogy).** Pipeline: `retrieval.by_pipeline_shape(structural_isomorphism)` across realms → mine for sub-pipelines reused across code and NLU tasks → propose a general-purpose `structural.*` capacity in Local L3. The dream itself produces a memory whose `capacity-used` list includes `retrieval.by_pipeline_shape`, so future dreams can retrieve *this dream* and iterate on analogy-detection — dreams over dreams fall out for free.

---

## Gaps exposed by these use cases

Issues to watch for during implementation:

1. **Cross-realm DataState design (UC-X-1).** The bridging DataState between NLU and code pipelines is a design risk. May force an adapter or a dedicated `structured_query` DataState.
2. **Retrieval capacity coverage (UC-NLU-1, UC-CODE-1, UC-CODE-2, UC-X-1).** The use cases lean on five retrieval contexts — `by_task_type`, `by_input_shape`, `by_capacity_used`, `by_result`, `by_pipeline_shape`. Each needs a concrete implementation and a concrete similarity function. Coverage may need to grow as new use cases surface.
3. **Constraint-satisfaction over L2 (UC-NLU-3).** This is a specific kind of path-finding that the L3 path-finding category should include as a first-class capacity.
4. **Abductive hypothesis generation (UC-NLU-2).** Abduction is currently implicit in "derivation" — should it be its own functional-category graph?
5. **Side-effect analysis (UC-CODE-1).** A code-realm capacity with cross-cutting relevance — lives in `code.*` or in a shared `analysis.*`?
6. **Patch generation (UC-CODE-2).** Producing code from inferred intent is an additional L3 capacity category (`generation.code_*`) not yet in the design.
7. **Structural isomorphism (UC-CODE-3, Dream-4).** Likely shared between code and analogy — a good candidate for a general-purpose `structural.*` category.

These gaps become the checklist for the vertical slice and subsequent L3 build-out.

**Resolved in 2026-04-21 design session (no longer gaps):** retrieval-by-similarity of past tasks is not a gap — it is `capacity:retrieval` (L3 functional category), reading memories consolidated from completed MMs into L2's `memories` role-graph. Each use case above has been updated to call the relevant retrieval capacity explicitly.

---

**End of use cases.** Add new ones as additional realms or cross-realm tasks emerge.
