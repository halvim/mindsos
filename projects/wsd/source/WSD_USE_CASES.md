# WSD Use Cases — Architecture Stress Tests

**Date:** 2026-04-29
**Purpose:** In-depth use cases designed to stress-test the WSD subsystem architecture (SCMS + ALS + six-phase lifecycle + lexicon empirical layer). Each use case is constructed to exercise a specific architectural pressure point and surface gaps where the current design may fail or need refinement.
**Companion:** `WSD_ARCHITECTURE.md` is the canonical architecture this document tests against.

---

## 0. How to use this document

Each use case follows a consistent template:

1. **Quick facts** — which subsystems, lifecycle phases, and architectural commitments are exercised.
2. **Input** — the concrete sentence or scenario.
3. **Task** — what the system is asked to accomplish.
4. **Expected output** — what successful execution looks like, including calibration shape.
5. **Walk-through** — step-by-step through the six-phase lifecycle and SCMS BSP turns.
6. **Architectural pressures** — what specifically is being stress-tested.
7. **Coordinated-change implications** — what gaps each scenario surfaces.
8. **Variants and edge cases** — adversarial extensions.
9. **Success criteria** — how we know the test passed (and what failure looks like).

The use cases are ordered roughly by complexity and architectural depth:

  - **UC-WSD-1** through **UC-WSD-3**: foundation cases exercising normal flow with increasing ambiguity.
  - **UC-WSD-4**: capacity-gap discovery and calibrated "I don't know."
  - **UC-WSD-5**: WSD ↔ FOL feedback loop (the SCMS BSP turn under load).
  - **UC-WSD-6** *(revised 2026-04-30)*: failure-driven training cycle with dream fan-out and multi-variant admin comparison.
  - **UC-WSD-7**: cold-start vs warm system (lexicon empirical-layer growth).
  - **UC-WSD-8**: user opts out of training (L0 settings + ALS gating).
  - **UC-WSD-9**: goal misidentification (silent failure detection).
  - **UC-WSD-10**: domain shift and calibration drift.
  - **UC-WSD-11** *(2026-04-30)*: three-capacity NLU composition (WSD + FOL + Frame).
  - **UC-WSD-12** *(2026-04-30)*: multi-metric dream recomposition and admin selection.
  - **UC-WSD-13** *(2026-04-30)*: promotion under genuine metric conflict (Pareto non-dominance).
  - **UC-WSD-14** *(2026-04-30)*: capacity-limitation discovery (data-gap vs. capacity-gap).
  - **UC-WSD-15** *(2026-04-30)*: cross-consumer blame attribution (WSD vs FOL vs Frame).
  - **UC-WSD-16** *(2026-04-30)*: value-typed paths-of-paths and registry expression metadata.

These use cases are not exhaustive coverage — they are deliberate stress tests. A v1 system that handles UC-1 through UC-16 well will have validated the load-bearing parts of the architecture.

---

## UC-WSD-1 — Baseline SVO with calibrated single-sense commitment

### Quick facts

- **Subsystems exercised:** WSD-init only (no SCMS BSP turns needed for trivial case); pipeline determination; goal verification.
- **Lifecycle phases:** 1 → 2 → 3 → 4 → 5.
- **Architectural commitments tested:** calibration target; multi-candidate-mandatory output (here: degenerates to single confident sense); empirical layer reads via theoretical fallback when empirical layer is sparse.

### Input

Sentence: *"The dog barked at the postman."*

### Task

Annotate every content word with its WordNet sense plus calibrated confidence.

### Expected output

```
{
  "the":      [function word — skipped],
  "dog":      [{sense: "dog.n.01", confidence: 0.92}, {sense: "dog.n.03", confidence: 0.05}, ...],
  "barked":   [{sense: "bark.v.01", confidence: 0.95}, {sense: "bark.v.02", confidence: 0.03}, ...],
  "at":       [function word — skipped],
  "the":      [function word — skipped],
  "postman":  [{sense: "postman.n.01", confidence: 0.97}, ...]
}
```

All distributions are **calibrated**: when confidence reports 0.92, the system is right ~92% of the time on inputs of this difficulty. No multi-candidate ambiguity preserved here because correlations decisively prefer one sense per word.

### Walk-through

**Phase 1 — Task interpretation.**

  - `recognize_task_shape(input)` matches against `L2.task-patterns`. Sub-shape recognizers fire: `sense-disambiguation-needed`. Confidence: 0.95 (high — this is canonical text input).
  - `derive_task_goal(task_shape, input)` returns goal: produce `DS_SENSE_DISTRIBUTIONS` over content words. Confidence: 0.96.

**Phase 2 — Pipeline determination.**

  - `translate_goal_to_datastates`: target = `DS_SENSE_DISTRIBUTIONS`.
  - `check_path_exists`: yes — standard text→sense pipeline exists.
  - `lookup_known_pipeline`: returns the canonical `text.tokenize → text.dep_parse → wsd-init` pipeline at confidence 0.94.
  - `select_pipeline`: exploitation wins (high confidence in known); skip exploration this run.
  - `validate_pipeline`: all preconditions hold given input.

**Phase 3 — Pipeline execution.**

  - Run parsing pipeline → `DS_PARSED_TEXT` (tokens with lemma, POS, dependency parse).
  - Run `wsd-init`: reads parsed input + lexicon empirical layer + `learned-parameters` via context.
    - For each content word, queries empirical layer: `iter_layer_edges("empirical", from_node=candidate_sense, edge_type="SUBJECT_OF" | "DOBJECT_OF" | "COOCCURS_DEPARC" | ...)`.
    - For "dog" in subject position with verb "bark": empirical layer has strong `(dog.n.01, SUBJECT_OF, bark.v.01)` edge with high `metric_resnik_strength` (0.85+). No competing `SUBJECT_OF` edges for other dog senses with this verb.
    - Computes Resnik selectional association; combines with sense priors via Bayesian update.
    - Emits distribution sharply peaked on `dog.n.01`.
  - Replan after `wsd-init`: forward role asks "anything else needed for goal?" — no further capacities required for this task. Reflective role: `wsd-init`'s effect was achieved (DS_SENSE_DISTRIBUTIONS produced).
  - **No SCMS BSP turns needed** because `fol-init` doesn't fire for this task (no logical-coherence-required pattern matched). SCMS Monitors are dormant.

**Phase 4 — Goal verification.**

  - `check_goal_state_match`: target DataState produced; all content words have distributions; structurally complete.
  - `verify_goal_achievement`: confidence 0.95.
  - `external_validation`: no HITL invoked.

**Phase 5 — Outcome processing.**

  - `consolidate_outcome`: success.
  - `consolidate_mm_to_memory`: write MM to `L2.memories`. Tags: `task-pattern: sense-disambiguation-needed`, `outcome: succeeded`.
  - `emit_signals_to_als`: S6 task-outcome positive signal for `task_shape_recognition_priors`, `pipeline_lookup_match_threshold`, and `(task_shape, pipeline) confidence` parameter sets.

### Architectural pressures

This case is the simplest stress test — it validates the **happy-path lifecycle without SCMS BSP turns**. Specifically tests:

  - L4's task-to-pipeline three-step flow returning a high-confidence known pipeline (exploitation, no exploration).
  - Lexicon empirical layer's `SUBJECT_OF` edges for selectional preferences working as designed.
  - Resnik selectional association correctly preferring `dog.n.01` over rare senses.
  - Calibrated single-sense commitment when correlations decisively prefer one sense (avoid false multi-candidate output for clear cases — calibration cuts both ways).

### Coordinated-change implications

Minimal. UC-WSD-1 is a sanity check; if it fails, something foundational is broken. Surfaces:

  - Bootstrap importer must populate enough `SUBJECT_OF` edges for canonical SVO sentences with common verbs. Coverage gap = silent failure here.
  - Sense priors (per-lemma frequency from corpora) must be available; if missing, falls back to uniform prior and produces wrong-shape output.

### Variants and edge cases

  - **V1.a:** "The dog barked." (no oblique object). Same expected output; no PP to disambiguate.
  - **V1.b:** "The cat meowed." Less common verb — tests fallback when `SUBJECT_OF` edges are sparse. May produce slightly less peaked distribution.
  - **V1.c:** Same input, but with parameters in `learned-parameters` set to default uniform (cold-start system). Expected: distributions slightly less confident; calibration target says `0.7` confidence should mean 70% accurate, so degradation is expected and *honest*.

### Success criteria

  - Top sense confidence reported is ≥0.85 for each content word.
  - When held-out gold-set evaluation runs on similar inputs, calibration error (ECE) <0.05.
  - Total runtime under 100ms (approximate; v1 doesn't have hard latency targets but baseline cases should be fast).
  - SCMS Monitors do not fire (no FOL/refinement needed for trivial input).

### Failure modes this catches

  - Empirical layer not populated with `SUBJECT_OF` edges → `wsd-init` returns uniform distribution.
  - Resnik metric capacity not implemented → falls back to PMI or conditional probability with worse calibration.
  - Three-step task-to-pipeline flow returns wrong pipeline for canonical text input.
  - SCMS Monitors fire when they shouldn't, wasting compute.

---

## UC-WSD-2 — Polysemous verb with overlapping selectional preferences

### Quick facts

- **Subsystems exercised:** WSD-init; SCMS BSP turns (single iteration); MSUR for combining reinforcing signals; multi-candidate output preservation.
- **Lifecycle phases:** 1 → 2 → 3 (with SCMS) → 4 → 5.
- **Architectural commitments tested:** multi-candidate preservation when context is genuinely ambiguous; MSUR's reinforcing-signal combination via `combination.bayesian`; calibration target on multi-modal distributions.

### Input

Sentence pair (treated as a single document for SCMS context):

*"Alice runs every morning. She trains hard for the marathon."*

versus

*"Alice runs a startup. She raised series A last quarter."*

### Task

Disambiguate `runs` in each sentence.

### Expected output

For sentence 1:
```
"runs": [
  {sense: "run.v.01" (move-fast), confidence: 0.78},
  {sense: "run.v.02" (operate), confidence: 0.18},
  {sense: "run.v.05" (manage), confidence: 0.04}
]
```

For sentence 2:
```
"runs": [
  {sense: "run.v.05" (manage), confidence: 0.74},
  {sense: "run.v.02" (operate), confidence: 0.21},
  {sense: "run.v.01" (move-fast), confidence: 0.05}
]
```

Multi-candidate distributions, but with strong context-driven peaks. **Critical:** the system must *not* produce identical distributions for both sentences — the surrounding context ("morning"/"marathon" vs "startup"/"series A") disambiguates.

### Walk-through (sentence 2 — "Alice runs a startup")

**Phase 1.** `recognize_task_shape` fires: `sense-disambiguation-needed` + (because the document spans multiple sentences) `cross-sentence-coherence-needed` (admin-authored sub-shape). Pipeline composition includes SCMS Monitors active for the document scope.

**Phase 2.** Pipeline lookup returns standard text-comprehension pipeline + SCMS active. Validate.

**Phase 3.** Parsing → `DS_PARSED_TEXT` for both sentences.

`wsd-init` processes "runs" in sentence 2:

  - Queries empirical layer for `runs` candidates with subject `Alice` (already disambiguated as `Alice.PROPER_NOUN`):
    - `(run.v.01, SUBJECT_OF_VERB)` with subjects of class `human` — strong (Resnik 0.7).
    - `(run.v.02, SUBJECT_OF_VERB)` with subjects of class `human` — moderate.
    - `(run.v.05, SUBJECT_OF_VERB)` with subjects of class `human` — strong.
  - Queries empirical layer for `runs` with object `startup`:
    - `(run.v.05, DOBJECT_OF, startup.n.01)` — strong (Resnik 0.85).
    - `(run.v.02, DOBJECT_OF, startup.n.01)` — weak.
    - `(run.v.01, DOBJECT_OF, startup.n.01)` — near-zero (move-fast doesn't take startup as object).
  - Combines via Bayesian update on the joint evidence: prior * P(subject=human|sense) * P(object=startup|sense).
  - Initial distribution: `run.v.05` (manage) at ~0.65, `run.v.02` (operate) at ~0.25, `run.v.01` at ~0.05.

`fol-init` runs:

  - Builds initial FOL state with statement `Alice manages startup` (using `run.v.05` interpretation as primary, `run.v.02` as secondary `assumed`).
  - Minimizes assumptions; commits to `run.v.05` as primary because it's plurality-favored.

`wsd-update` Monitor activates with the document-level context. `cross-word` Monitor activates to propagate sense-evidence across sentences.

**SCMS BSP turn 1:**

  - `cross-word` Monitor receives signals about sentence 2's content words. Notes that `series A` (sentence 2's other sentence) co-occurs in empirical layer with `run.v.05` strongly (`(run.v.05, COOCCURS_SAMEFRAME, series_a.n.01)` edge from business-document mining). Emits a signal to `wsd-update`.
  - `wsd-update` invokes MSUR:
    - Pending signals: one from `cross-word` reinforcing `run.v.05`.
    - Independent / reinforcing / contradictory partition: this is **reinforcing** — same direction as init.
    - Combination via `combination.bayesian`: posterior shifts further toward `run.v.05` (now 0.74).
    - No threads needed (no contradictions).
  - `wsd-update` calls `update_state`: emits revised `DS_SENSE_DISTRIBUTIONS`.
  - Phase 3 broadcast: emits to `fol-update`.

**SCMS BSP turn 2:**

  - `fol-update` receives wsd-update's revised distribution. Re-evaluates FOL state. No new statement-set change (already committed to `run.v.05`). **No emission** — fol-update is state-change-driven and current state is unchanged.
  - No other Monitor has pending signals.
  - **System-wide quiescence detected.** L4 ends SCMS turns.

**Phase 4.** `check_goal_state_match`: distributions over all content words. `verify_goal_achievement`: confidence 0.88 (lower than UC-1 because the multi-candidate output is intrinsic to the input). Quality: high.

**Phase 5.** Consolidate. S6 positive signal to ALS for the parameters that contributed to correct disambiguation.

### Architectural pressures

  - **Multi-candidate preservation tested.** System produces non-degenerate distribution (0.74 / 0.21 / 0.05) — does not collapse to single sense even though one is plurality-favored.
  - **MSUR reinforcing combination tested.** Signal from `cross-word` reinforcing `wsd-init`'s evidence; `combination.bayesian` correctly compounds rather than averaging.
  - **State-change-driven `fol-update`** — when WSD's revision doesn't change FOL's commitments, FOL doesn't re-broadcast. Avoids oscillation.
  - **Cross-sentence empirical-layer signal** — `cross-word` Monitor reads `COOCCURS_SAMEFRAME` edges across sentences. Tests that frame-level co-occurrence is mined from business documents in OntoNotes/FrameNet.

### Coordinated-change implications

  - **Document-level scope for SCMS** needs to be defined — when does "the document" end? Multi-sentence input requires clarification on Monitor lifecycle (per task vs per sentence).
  - **`cross-sentence-coherence-needed` task-pattern** — admin-authored. Need to design what triggers it (any text input with >1 sentence? Only when explicit reference like "She" appears? Only for certain document classes?).
  - **`cross-word` Monitor design** — is currently a v1 stub. UC-WSD-2 is the simplest case where it has real work to do. Forces concrete design.

### Variants and edge cases

  - **V2.a:** Sentence 1 with no second-sentence context: *"Alice runs every morning."* alone. Without "marathon" context, distribution is more ambiguous: 0.55 / 0.30 / 0.15. System honestly preserves uncertainty.
  - **V2.b:** Adversarial — *"Alice runs a marathon for her startup's wellness program."* Mixed evidence; distributions should be more uncertain than either pure case. Real test of MSUR contradictory branching: `(marathon, OBJECT_OF, run.v.01)` and `(startup, COOCCURS, run.v.05)` are contradictory; assumption threads instantiated; comparator picks based on evaluator score.

### Success criteria

  - Distribution shape qualitatively matches: top sense > 0.6, second sense in 0.15–0.30 range for ambiguous cases, third sense < 0.10.
  - Calibration: when held-out gold says single-sense correctness on this difficulty class, system's reported top-sense confidence matches actual accuracy ±5%.
  - SCMS BSP turns terminate within 2-3 iterations for this scenario.
  - V2.b assumption threads correctly created and resolved by `comparator.max` of the evaluator score.

### Failure modes this catches

  - System producing identical distributions for both sentences → empirical layer queries broken.
  - System collapsing to single confident sense in V2.b → multi-candidate-mandatory commitment violated.
  - SCMS BSP turns oscillating beyond 5 iterations → state-change-driven `fol-update` not implemented correctly.

---

## UC-WSD-3 — Genuine preserved ambiguity (Winograd-style)

### Quick facts

- **Subsystems exercised:** WSD-init + WSD-update + FOL-update; SCMS BSP turns multiple iterations; MSUR contradictory-thread branching.
- **Lifecycle phases:** 1 → 2 → 3 (heavy SCMS) → 4 → 5.
- **Architectural commitments tested:** multi-candidate output mandatory when truly ambiguous; FOL detecting genuine contradiction (not silently committing wrong); calibration on uncertainty.

### Input

*"She saw the man with the binoculars."*

### Task

Resolve sense and PP-attachment ambiguity.

The PP "with the binoculars" can attach to:

  - "saw" (instrumental — *she used binoculars to see the man*) → `with` = `with.IND.IV.with` (instrumental)
  - "the man" (accompaniment / possession — *the man had binoculars*) → `with` = `with.IND.II.with` (accompaniment)

This is the canonical Winograd-style ambiguity. There is no internal evidence sufficient to resolve it.

### Expected output

```
"saw":  [{sense: "see.v.01", confidence: 0.85}, ...]    // perception sense; clear
"man":  [{sense: "man.n.01", confidence: 0.92}, ...]    // adult male; clear
"binoculars": [{sense: "binoculars.n.01", confidence: 0.97}, ...]  // clear
"with": [
  {sense: "with.IND.IV.with" (instrumental), confidence: 0.45},
  {sense: "with.IND.II.with" (accompaniment), confidence: 0.45},
  {sense: "with.IND.III.with" (manner), confidence: 0.10}
]
```

The system **must** report `with` as ambiguous. Single-sense commitment here would be wrong.

### Walk-through

**Phase 1.** task-shape: `sense-disambiguation-needed` + `pp-attachment-ambiguity-detected` (admin-authored sub-shape).

**Phase 2.** Pipeline includes WSD + FOL + frame-match (frames around "see" and "carry/possess").

**Phase 3.**

`wsd-init`:

  - Most words disambiguate clearly.
  - For `with`, queries empirical layer:
    - `(with.IND.IV.with, INSTRUMENT_OF, see.v.01)` — moderate Resnik (0.50).
    - `(with.IND.II.with, COOCCURS_SAMEFRAME, man.n.01)` — moderate (0.45).
  - Initial distribution for `with`: 0.45 / 0.45 / 0.10.

`fol-init`:

  - Tries to construct FOL statement. If it commits to instrumental, gets: `she.see(man) ∧ instrument(see, binoculars)`. If accompaniment: `she.see(man-with-binoculars)` requiring composition over the noun.
  - **Both interpretations yield consistent FOL states.** No contradiction either way.
  - `fol-init` minimizes assumptions: prefers whichever has fewer; in this case, both have similar assumption counts. **Holds both as `assumed`-tagged alternatives.**

**SCMS BSP turn 1:**

  - `frame-match` Monitor evaluates both interpretations against FrameNet frames. Frame `Perception_active` for "see" prefers an instrument; frame `Possession` for "carry" prefers a possessor. Both fire.
  - `frame-match` emits to `wsd-update` and `fol-update`. Both signals are **contradictory** with respect to `with`'s sense.
  - `wsd-update` invokes MSUR:
    - Pending signals: two on the same target (`with`), opposing.
    - **Partition: contradictory.**
    - **Branch into assumption threads:**
      - Thread A: `with` = instrumental.
      - Thread B: `with` = accompaniment.
    - Apply `evaluator.entropy_decrease` to each thread:
      - Thread A entropy: distribution becomes peaked on instrumental (lower entropy).
      - Thread B entropy: distribution becomes peaked on accompaniment (lower entropy).
      - Both threads achieve similar entropy decrease; neither dominates.
    - `comparator.max` selects winning thread by score. Tie-broken by raw evidence count (or by evaluator's secondary criterion).
    - **Losing thread's distinguishing assumption ("`with` = X" for whichever lost) emitted as `hypothesised` to MSUR ledger.**
  - `wsd-update` returns resolved_signal that *barely* shifts the distribution (because the win was marginal).
  - Updated distribution: 0.50 / 0.40 / 0.10 — slight shift but still highly ambiguous.

**SCMS BSP turn 2:**

  - `fol-update` receives wsd-update's revised distribution. FOL state has `with`-sense assumption updated to the winning thread's commitment.
  - But FOL's overall statement set is unchanged (the same propositions hold under either interpretation). **No state-change emission.**
  - `frame-match` has no new pending signals.
  - **Quiescence detected.**

**Phase 4.**

  - `check_goal_state_match`: distribution structurally complete.
  - `verify_goal_achievement`: confidence 0.55 — system is *honestly* uncertain.
  - Quality flag: "ambiguous resolution preserved."
  - The `sufficient_predicate` for `pp-attachment-ambiguity-detected` task-pattern says: **either commit to one sense at confidence > 0.8, OR preserve multi-candidate output explicitly.** Multi-candidate output meets sufficient.

**Phase 5.**

  - Consolidate with explicit "ambiguity preserved" outcome flag.
  - S6 signal to ALS is **conditional** — task succeeded by preserving honest uncertainty, not by committing.

### Architectural pressures

  - **MSUR contradictory branching working correctly** — multi-thread instantiation, evaluator scoring, comparator selection, hypothesised emission for losing thread.
  - **Honest under-commitment.** System's `verify_goal_achievement` returns 0.55, not 0.95 — calibration target enforced even at the verification layer.
  - **`hypothesised`-tagged losing-thread assumption** retained in MSUR ledger. Tests that the ledger is properly populated.
  - **Sufficient-predicate flexibility** — task-pattern's `sufficient_predicate` accepts either commitment OR multi-candidate output. Tests that admin-authored task-patterns can encode this nuance.

### Coordinated-change implications

  - **`pp-attachment-ambiguity-detected` task-pattern needs admin-authoring.** Its `sufficient_predicate` shape is non-trivial — must accept ambiguity-preserved as a successful outcome.
  - **Frame-match Monitor must be active in v1** for this UC to work, not just declared as a stub. Forces v1 design of `frame-match`.
  - **Goal-verification predicate must distinguish "ambiguity preserved (success)" from "low confidence (uncertain failure)."** This is a real distinction; admin-tunable per task-pattern.

### Variants and edge cases

  - **V3.a:** *"She saw the bird with the binoculars."* — slightly less ambiguous because birds-having-binoculars is implausible. Distribution should shift toward instrumental (~0.65 / 0.30 / 0.05). Tests selectional preferences correctly tilting against implausible accompaniment readings.
  - **V3.b:** *"The carpenter saw the man with the saw."* — extreme adversarial; `saw` is itself ambiguous (perception verb vs cutting tool); `with the saw` is highly likely to be instrumental. Tests joint disambiguation of multiple ambiguous tokens.
  - **V3.c:** External signal arrives later: HITL says "the binoculars are hers (instrumental)." Phase 6 treats this as goal-correction signal (S5). Expected: `with`-sense parameters and `pp-attachment` parameters get positive S5 signal for instrumental sense; `hypothesised`-tagged accompaniment thread is retracted.

### Success criteria

  - System outputs ambiguous distribution for `with` (no single-sense above 0.65).
  - `verify_goal_achievement` reports honest confidence < 0.7.
  - MSUR ledger contains `hypothesised`-tagged losing thread.
  - Outcome flag is "ambiguity preserved (success)."

### Failure modes this catches

  - System committing to one sense at high confidence → multi-candidate-mandatory commitment violated. **This is the canonical failure of overconfident WSD systems** — UC-WSD-3 is the calibration discriminator.
  - MSUR not branching → contradictory signals merged via combination, producing wrong-shaped output.
  - Sufficient-predicate not allowing ambiguity-preserved outcomes → system reports failure on cases it actually handled correctly.

---

## UC-WSD-4 — Capacity gap (no path exists)

### Quick facts

- **Subsystems exercised:** Phase 1 + Phase 2 (truncated); capacity-gap surfacing; calibrated honesty at task level.
- **Lifecycle phases:** 1 → 2 (early termination) → outcome with capacity-gap flag.
- **Architectural commitments tested:** "I don't know" as first-class outcome; `capacity-gaps` admin queue.

### Input

Task: *"Translate this sentence into Mandarin: 'The dog barked at the postman.'"*

### Task

Produce Mandarin translation.

### Expected output

```
{
  "outcome": "capacity_gap",
  "explanation": "No translation capacity exists in L3 for English→Mandarin",
  "capacity_gap_id": "<uuid>",
  "available_partial_results": null
}
```

### Walk-through

**Phase 1.**

  - `recognize_task_shape`: matches `translation-needed` (admin-authored sub-shape, if present) or fails to match any specific task-shape and falls back to generic `text-transformation-needed`. Confidence varies depending on admin-authored coverage.
  - `derive_task_goal`: target = `DS_TRANSLATED_TEXT(target_lang=mandarin)`.

**Phase 2.**

  - `translate_goal_to_datastates`: target = `DS_TRANSLATED_TEXT` with `target_lang=mandarin`.
  - **`check_path_exists(start=DS_RAW_TEXT, goal=DS_TRANSLATED_TEXT(target_lang=mandarin))`**: queries L3 capacity graph for path. **No path exists** — no capacity in L3 produces `DS_TRANSLATED_TEXT(target_lang=mandarin)`.
  - **Capacity gap detected.**

**Phase 2 termination:**

  - L4 writes record to `L2.capacity-gaps`:
    ```
    CapacityGap(
      task_shape_iri: "translation-needed",
      start_datastate_iri: "ds_raw_text",
      goal_datastate_iri: "ds_translated_text(target_lang=mandarin)",
      attempted_searches: [{path_finder: "BFS", result: "no_path"},
                           {path_finder: "A_star", result: "no_path"}],
      first_seen_at: <timestamp>,
      last_seen_at: <timestamp>,
      occurrence_count: 1,
      status: "open"
    )
    ```
  - L4 returns "I don't know" outcome to caller. No partial computation; honest cutoff.
  - No SCMS engagement; no Phase 3-5.

**Outcome processing (abbreviated Phase 5).**

  - `consolidate_outcome`: outcome type = `capacity_gap`.
  - **No memory entry** — capacity-gap tasks don't produce useful training data; archive to `problem-trace` instead with minimal info.
  - **No S6 signal** to ALS — task didn't run, so no parameter-learning evidence.
  - **Task-shape recognition prior gets neutral signal** (not negative) — the shape was recognized correctly; the system just lacks capability.

### Architectural pressures

  - **Calibrated honesty at task level.** System refuses to fabricate translation. Returns clear "I don't know" rather than producing garbage output.
  - **`capacity-gaps` role-graph as admin queue** — admin sees that translation is requested but unsupported; can prioritize teaching translation capacity.
  - **L4 short-circuits Phase 3-5.** Path-finding failure is recognized in Phase 2; no wasted work attempting downstream phases.
  - **Repeated occurrences increment counter.** If same task-shape arrives 100 times, the gap's `occurrence_count` reflects demand; admin can prioritize.

### Coordinated-change implications

  - **`capacity-gaps` admin tooling** — needed before this UC produces actionable output. Admin UI/API for reviewing the queue, marking status (open / resolving / resolved / out-of-scope), and recording resolutions.
  - **L4's `check_path_exists` performance** — must be fast for dead-end task-shapes. Otherwise tasks that can't be solved waste compute on path-finding before failing.
  - **`generate_pipeline` should not be invoked** when no path exists — purely structural reachability check first. L4 chat must spec this explicitly.

### Variants and edge cases

  - **V4.a:** Same task arrives 50 times across users. Each occurrence increments counter; admin sees high-demand gap surface to top of queue.
  - **V4.b:** Admin teaches a new `text.translate(target_lang=mandarin)` capacity. On next arrival of similar task, `check_path_exists` returns true; `capacity-gaps` record marked `resolved`. **Tests resolution lifecycle.**
  - **V4.c:** Partial path exists — system has English→French and French→Mandarin but no direct English→Mandarin. **Open architectural question:** does L4 attempt composition, or report gap? Current spec says path-finding handles composition (path through intermediate states), so this should succeed via a longer pipeline. Tests path-finding's composition discovery.
  - **V4.d:** Adversarial — task input includes Mandarin already; user is asking for translation that's already done. System should detect and respond differently (no-op path); tests `check_path_exists` not over-eagerly returning gap.

### Success criteria

  - Capacity-gap recorded within 100ms of task arrival.
  - User receives clear "I don't know" response, not silent failure or fabricated output.
  - Admin queue surfaces the gap immediately.
  - Repeated occurrences correctly aggregate (occurrence_count increments).

### Failure modes this catches

  - System fabricating translation by finding "any" path (e.g., chaining unrelated capacities) → unsafe. **This is the most important calibration test at the task level** — better honest gap than fabricated output.
  - Capacity-gap not recorded → admin can't see gaps; no learning loop for system extension.
  - Phase 3 invoked despite no path → wasted compute on impossible task.

---

## UC-WSD-5 — WSD ↔ FOL feedback loop with multi-iteration convergence

### Quick facts

- **Subsystems exercised:** WSD-init, FOL-init, WSD-update, FOL-update, MSUR; SCMS BSP turns iterating multiple times.
- **Lifecycle phases:** 1 → 2 → 3 (deep SCMS) → 4 → 5.
- **Architectural commitments tested:** mutual feedback between WSD and FOL; assumption-resolution events emitting state-change signals; pair-wise quiescence detection.

### Input

*"The boy played well. The melody was perfect."*

(The "play / melody" canonical example from the user's own framing.)

### Task

Disambiguate `played` in sentence 1.

### Expected output

```
"played": [
  {sense: "play.v.01" (sport/game), confidence: 0.05},
  {sense: "play.v.02" (instrument/melody), confidence: 0.92},
  {sense: "play.v.03" (drama), confidence: 0.03}
]
```

### Walk-through

**Phase 1.** `recognize_task_shape`: `sense-disambiguation-needed` + `cross-sentence-coherence-needed` + `logical-coherence-required` (the latter activates FOL).

**Phase 2.** Pipeline includes wsd-init + fol-init + SCMS Monitors active.

**Phase 3.**

`wsd-init` (sentence 1, "The boy played well"):

  - Empirical layer queries:
    - `(boy, SUBJECT_OF, play.v.01)` — strong (children play sports).
    - `(boy, SUBJECT_OF, play.v.02)` — strong (children play instruments).
    - `(boy, SUBJECT_OF, play.v.03)` — weak.
  - "Well" is an adverb; no strong selectional signal between adverb and play sense.
  - Initial distribution for `played`: 0.45 / 0.45 / 0.10. **Highly ambiguous.**

`fol-init`:

  - Holds `played(boy)` with `play.sense ∈ {play.v.01, play.v.02}` as `assumed` (multiple alternatives).
  - Minimizes assumptions: at this point, can't pick. Both stay assumed.

**SCMS BSP turn 1:**

  - `cross-word` Monitor processes sentence 2 ("The melody was perfect"). Identifies `melody` and queries empirical layer:
    - `(melody, COOCCURS_SAMEFRAME, play.v.02)` — strong (`Performing_arts` frame).
    - `(melody, COOCCURS_SAMEFRAME, play.v.01)` — near-zero.
  - Emits cross-document signal to `wsd-update` for `played` sense in sentence 1.
  - `wsd-update` invokes MSUR:
    - Pending signal: reinforcing `play.v.02`.
    - `combination.bayesian` updates distribution: now 0.20 / 0.75 / 0.05.
  - Broadcasts new distribution.

**SCMS BSP turn 2:**

  - `fol-update` receives wsd-update's signal. Re-evaluates FOL state:
    - Previously had `play.sense ∈ {play.v.01, play.v.02}` both `assumed`.
    - With new distribution favoring `play.v.02` strongly, FOL elevates `play.sense = play.v.02` from `assumed` to `inferred`.
    - **State change!** Statement set's epistemic tags changed.
  - `fol-update` emits to `wsd-update` (per its `emits_to`).

**SCMS BSP turn 3:**

  - `wsd-update` receives `fol-update`'s confirmation. New signal: FOL has elevated `play.v.02` to `inferred`, providing strong logical evidence.
  - `wsd-update` invokes MSUR:
    - Pending signal: reinforcing `play.v.02` (with high weight because it's now `inferred`, not `assumed`).
    - `combination.bayesian`: distribution shifts to 0.05 / 0.92 / 0.03.
  - Broadcasts.

**SCMS BSP turn 4:**

  - `fol-update` re-evaluates. Statement set is unchanged (already at `inferred`). **No emission.**
  - `cross-word` has no new context to share.
  - **Quiescence detected.**

**Phase 4.** `verify_goal_achievement`: confidence 0.91. Quality: high.

**Phase 5.** Consolidate. S6 + S8 (low replan-divergence — pipeline ran cleanly) signals to ALS. Empirical-layer evidence updated: `(melody, COOCCURS_SAMEFRAME, play.v.02)` edge gets `evidence_count++` and `last_observed=now`.

### Architectural pressures

  - **The full WSD ↔ FOL feedback loop.** Multiple SCMS BSP turns; each turn moves the system forward by extracting one piece of information.
  - **`fol-update` state-change-driven emission.** Turn 2 emits because epistemic tag changed; turn 4 doesn't because state is unchanged.
  - **Pair-wise quiescence detection** at turn 4 — clean termination.
  - **Cross-sentence empirical-layer reads** — `cross-word` Monitor reading sentence 2 to influence sentence 1.
  - **Bayesian combination** of evidence from multiple turns correctly compounds.

### Coordinated-change implications

  - **`logical-coherence-required` task-pattern** must trigger FOL Monitor activation. Admin-authored.
  - **Document scope for SCMS** — multi-sentence input requires SCMS to span across sentence boundaries cleanly.
  - **Empirical layer must contain `COOCCURS_SAMEFRAME` edges** at scale. FrameNet importer (extended) is the source.
  - **FOL ledger `assumed → inferred` transition events** must reliably generate `fol-update` emissions. L3 FOL capacity design must implement this.

### Variants and edge cases

  - **V5.a:** *"The boy played well. The team scored three goals."* — same first sentence; second sentence pushes toward `play.v.01` (sport) instead. Same architecture, opposite resolution. Tests symmetry.
  - **V5.b:** *"The boy played well. The audience clapped."* — `clapped` co-occurs with both `play.v.02` (concert) and `play.v.03` (drama). Less decisive. Distribution shifts but not as sharply (0.30 / 0.55 / 0.15 maybe). Tests partial-information case.
  - **V5.c:** *"The boy played well."* alone. Without sentence 2, distribution stays ambiguous (0.45 / 0.45 / 0.10). System honestly preserves uncertainty. Tests that absent context doesn't produce false confidence.
  - **V5.d:** Three sentences with mixed signals: *"The boy played well. The melody was perfect. The team won."* — contradictory evidence. MSUR contradictory thread branching activates. Tests under-determined cases at the document level.
  - **V5.e:** Adversarial — sentence 2 is misleading: *"The boy played well. The car broke down."* No relevant signal. SCMS quiesces with original ambiguity preserved.

### Success criteria

  - SCMS BSP turns terminate within 4-6 iterations for V5 base case.
  - Final distribution sharply peaked on correct sense (>0.85 confidence).
  - V5.c preserves ambiguity.
  - V5.d invokes MSUR contradictory branching at least once.
  - Empirical layer's `COOCCURS_SAMEFRAME` edges updated post-task.

### Failure modes this catches

  - SCMS BSP turns oscillating (>10 iterations) → state-change-driven emission not implemented.
  - `fol-update` re-broadcasting on no-state-change → infinite loop risk.
  - Cross-sentence signals not propagating → `cross-word` Monitor broken.
  - Empirical layer reads not finding `COOCCURS_SAMEFRAME` edges → bootstrap importer didn't extract from FrameNet correctly.

---

## UC-WSD-6 — Failure-driven training cycle (revised 2026-04-30)

> **Revision note (2026-04-30):** updated to reflect dream fan-out (multiple recomposed path variants per cycle), multi-metric outcome panels, paths-of-paths blame attribution, and the minimal user UI (knowledge/capacity/dream-priority editing + auditing) that ships in v1. The original 2026-04-29 version targeted single-parameter updates; under the revised framing, dream cycles produce a *fan* of variants and the user (as Local admin) selects via the metric panel.

### Quick facts

- **Subsystems exercised:** All six phases; Phase 6 path-blame attribution; ALS staging + dream fan-out + multi-metric validation + admin-panel audit + apply.
- **Lifecycle phases:** 1 → 2 → 3 → 4 (failure detected via HITL) → 5 → 6 → ALS staging → dream fan-out (multiple variants) → multi-metric validation → user-as-Local-admin selects via UI panel → versioned apply → re-run validates fix.
- **Architectural commitments tested:** Phase 6 blame attribution at the path-segment level; dream fan-out across multiple outcome-metric maximizers; promotion-rule capacity selection (L4 auto-selects, admin can override); calibration-aware training; minimal user UI for knowledge/capacity edit + audit; versioned rollback via reference-graph stale-flagging.

### Input

Sentence: *"The lawyer addressed the bench."*

External feedback (HITL, via user UI): "Wrong sense for `bench` — you picked `bench.n.01` (seat); the correct sense in legal context is `bench.n.04` (the judges collectively)."

### Task

Sense annotation; subsequent training cycle (with multi-variant fan-out) to fix the systematic error.

### Expected output (initial run)

```
"bench": [
  {sense: "bench.n.01" (seat), confidence: 0.78},     // wrong
  {sense: "bench.n.04" (judges), confidence: 0.15},
  ...
]
```

### Expected output (post-training, second run, after admin-selected variant applied)

```
"bench": [
  {sense: "bench.n.04" (judges), confidence: 0.65},    // corrected
  {sense: "bench.n.01" (seat), confidence: 0.25},
  ...
]
```

### Walk-through (initial run + Phase 6 + dream fan-out + admin selection)

**Initial run:**

Phases 1-5 proceed as in UC-WSD-1. WSD-init's empirical-layer query finds:

  - `(bench.n.01, DOBJECT_OF, address.v.01)` — moderate (general English).
  - `(bench.n.04, DOBJECT_OF, address.v.01)` — present but lower count (legal corpus has fewer overall observations).

System commits to `bench.n.01` at 0.78 confidence. Phase 4 verifies goal achieved. Phase 5 consolidates with S6 positive signal.

**External signal arrives (post-consolidation):**

User opens the minimal UI's audit/correction surface and submits: "wrong sense, should be `bench.n.04`."

**Phase 6 — Failure diagnosis (path-segment blame):**

  - L4 invokes `analyze_failure_provenance` against the executed path. The path is a sequence of capacity-references:
    - `text.tokenize → text.dep_parse → wsd-init-scoring (path P_score) → calibration-shape-output`
  - Each path-segment carries provenance + confidence:
    - Tokenize: high confidence; small blame.
    - Dep-parse: high confidence; small blame.
    - `P_score` (the WSD scoring sub-path): confidence 0.78 for `bench` — *moderate*; meaningful blame.
    - Calibration shaping: high confidence; small blame.
  - Blame heuristic: `(1 - confidence) × (1 + replan-divergence)`. `P_score` gets the largest share.
  - **Cross-validation by alternative path substitution:** L4 substitutes `P_score` with a candidate alternative `P_score_legal` (boosts legal-domain context weight). The substituted path produces `bench.n.04` at 0.62. Cross-validation evidence localizes blame to `P_score`.
  - **Output of attribution:** `[(P_score, 0.60), (sense-prior parameters consumed by P_score, 0.20), (other path-segments, ≤0.05 each)]`.

**Route to ALS:**

  - `route_to_als` emits S5 (HITL negative) signal weighted by path-segment blame.
  - Each signal row written to `parameter-staging` (Local L2 role-graph) for the user, tagged with the implicated path-segment ID and the affected parameter set.

**Dream-time fan-out (multiple variants):**

A maintenance dream for this user pulls staged evidence and generates a *fan* of recomposed variant paths, each maximizing a different outcome objective:

  - **Variant V1 — calibration-prioritized.** Substitutes `P_score`'s scoring sub-segment with a calibration-aware variant; updates the legal-domain context-weight parameter via `mechanism.bayesian_update`. Optimizes for ECE.
  - **Variant V2 — accuracy-prioritized.** Substitutes a different scoring sub-segment that uses sharper top-1 commitment under domain context; optimizes for top-1 accuracy on legal-domain items.
  - **Variant V3 — coverage-prioritized.** Adjusts only the prior; minimal disruption; optimizes for `Coverage@τ` so that confidence ≥0.7 commitments don't shrink relative to incumbent.

Each variant runs validation against the full metric set:

| Variant | ECE | Brier | Top-1 (legal) | Top-1 (general) | Coverage@0.7 | Gold-set drift |
| --- | --- | --- | --- | --- | --- | --- |
| Incumbent | 0.05 | 0.12 | 73% | 90% | 70% | baseline |
| V1 (cal) | 0.03 | 0.10 | 80% | 89% | 65% | +0.2 pts |
| V2 (acc) | 0.07 | 0.11 | 87% | 88% | 78% | +0.5 pts |
| V3 (cov) | 0.05 | 0.12 | 76% | 90% | 73% | +0.0 pts |

All variants pass V1 (gold-degradation) and V2 (calibration anti-regression) gates conservatively. Each variant is staged in `pending-promotions` (Local) with metrics attached.

**Admin-panel audit (user is Local admin) via minimal UI:**

  - The user opens the audit panel. Sees the table above plus per-variant "examples this would have changed" diffs (e.g., V2 changes 18 examples in last 100 tasks; V1 changes 12; V3 changes 6).
  - L4 has *auto-selected* a default promotion-rule capacity for this case — Pareto-frontier-with-tradeoff-panel — which surfaces V1 and V2 as non-dominated candidates and recommends user pick between them. V3 is dominated.
  - User reviews, picks **V1 (calibration-prioritized)** because honest confidence is the user's goal-statement priority. Decision and rationale logged to audit trail.

**Apply:**

  - L4 versioned-writes V1's new `P_score` path version + parameter snapshot to Local `learned-parameters` and `promoted-pipelines`. Previous version retained via `SUPERSEDES` edge.
  - The reference-graph cascade-flag mechanism marks any higher-level path that referenced the old `P_score` as *stale* until re-evaluation runs.

**Re-run on similar input:**

  - Input: *"The judge addressed the bench at the hearing."*
  - WSD path executes with the new `P_score`; legal-domain context weight is higher.
  - Output: `bench.n.04` at 0.65 confidence. **Correction propagated.**

### Architectural pressures

  - **Path-segment blame attribution.** Provenance walk + heuristic localizes blame at the granularity of path-segments (sub-paths), not flat parameter sets.
  - **Dream fan-out.** Single failure produces multiple recomposed variants targeting different metrics — not a single update.
  - **Multi-metric validation panel.** Admin sees the full tradeoff surface, not just a single delta.
  - **Promotion-rule capacity auto-selection.** L4 picked Pareto-frontier-with-panel for this case; admin could have overridden to e.g. shadow-deployment if traffic existed.
  - **Calibration-aware training as v1 commitment.** V1 variant exists because the calibration-aware-training capacity is a v1 capacity in the L3 stack.
  - **User-as-Local-admin audit via minimal UI.** End user reviews and selects through the same UI surface used for knowledge/capacity addition.
  - **Versioned rollback + reference-graph cascade.** SUPERSEDES edges on path versions; cascade stale-flagging on dependent paths.

### Coordinated-change implications

  - **Minimal user UI is v1 critical-path.** Audit panel + correction submission are part of the v1 minimal UI; without them, this UC can't run.
  - **Promotion-rule capacities** A–F (single-metric, Pareto, composite, statistical, shadow, admin-discretionary) all live as L3 capacities. L4 auto-selection logic + admin-override flow is v1.
  - **Cross-validation policy** in Phase 6 — when does L4 substitute path-segments to confirm blame? Too eagerly = expensive; too rarely = sparse diagnostic. Tunable parameter; admin-configurable.
  - **Reference-graph cascade re-evaluation policy** — needs explicit v1 design (which paths re-evaluate, on what schedule, with what gates).
  - **Rollback semantics** when post-promotion accuracy degrades — automatic via reference-graph cascade flagging? Admin-triggered? Decide.

### Variants and edge cases

  - **V6.a:** Same correction comes from multiple users independently. Aggregated Local approvals → Global promotion cycle. Tests Local→Global aggregation under multi-variant framing (which variant wins globally if different users picked different locals?).
  - **V6.b:** User reviews variants and *rejects all*. Rejection logged; staged variants pruned or retained for next dream cycle's seeding.
  - **V6.c:** Multiple unrelated corrections in same dream cycle. Batched-summary audit policy presents aggregate panel covering several path-segment fixes. Tests batch-audit UX.
  - **V6.d:** All variants are dominated by incumbent (none beats it on any metric). Dream produced no improvement; L4 reports "no promotion candidate" and the staged signals remain for next cycle.
  - **V6.e:** Adversarial HITL — user provides incorrect "correction." Variants trained in wrong direction; gold-set anti-regression gate (V1) catches and rejects all variants. Tests gold-set as anchor against malicious/mistaken HITL.
  - **V6.f:** L4-auto-selected promotion rule disagrees with admin's typical preference. Admin overrides on this case. Override logged; if pattern recurs, L4 learns the override and adjusts auto-selection.
  - **V6.g:** A variant's path references a sub-path that has itself been updated mid-cycle. Reference-graph stale-flag fires; variant queued for re-validation before user sees it in the panel.

### Success criteria

  - Phase 6 attribution: correct path-segment gets >50% blame weight.
  - Dream fan-out produces ≥2 distinct variants (different objective maximizers) per failure case where multiple metrics are tracked.
  - V1 (gold anti-regression) + V2 (calibration anti-regression) gates correctly reject any variant that violates them.
  - Admin panel surfaces non-dominated candidates clearly; logs rationale for selection.
  - Post-promotion re-run produces corrected output for new similar inputs.
  - Reference-graph cascade flags dependent paths stale after promotion; they re-validate before any further promotion.

### Failure modes this catches

  - Blame attribution operates only at parameter-set granularity (not path-segment) → cannot localize blame within composed paths → updates the wrong scoring sub-path.
  - Dream produces only one variant → admin can't see tradeoffs → promotion is rubber-stamping or rejection-only.
  - Metric panel doesn't show "examples this would have changed" → admin makes uninformed selection.
  - Auto-selected promotion rule is silently wrong (e.g. picks single-metric-threshold when Pareto-frontier was needed) and there's no override path.
  - Reference-graph cascade not implemented → outdated outcome history is treated as valid → bad promotions of dependent paths.
  - Adversarial HITL not caught by gold anti-regression gate → corrupts parameters across subsequent variants.

---

## UC-WSD-7 — Cold start vs warm system (lexicon empirical-layer growth)

### Quick facts

- **Subsystems exercised:** Lexicon empirical layer; bootstrap importer outputs vs dream-mined updates; ALS Track A (auto-applied correlation updates).
- **Lifecycle:** longitudinal — same task pattern run on cold-start system vs after N consolidated tasks.
- **Architectural commitments tested:** empirical layer growth via dream miner; calibration improvement over time; sparse-data fallback to class generalization.

### Setup

**Cold-start system:** lexicon empirical layer populated only by bootstrap importer. SemCor + OntoNotes + FrameNet edges loaded; no user-task-derived edges yet.

**Warm system:** same starting point, plus 1000 consolidated successful tasks across mixed inputs over the past 30 days.

### Input

Run UC-WSD-1 through UC-WSD-3 inputs on both states; compare.

### Expected output

For inputs where bootstrap-imported corpora cover well (general English SVO), cold-start system performs well (~85% calibrated accuracy). For inputs in domains underrepresented in bootstrap corpora (e.g., user's specific work-domain), warm system shows measurable improvement.

Calibration metrics:

  - Cold-start ECE: ~0.06 (slight overconfidence on rare-sense cases).
  - Warm-system ECE: ~0.04 (calibration improved as user-data correlations smooth out bootstrap biases).

### Walk-through

**Cold-start run on input "Alice runs a startup":**

  - WSD-init reads empirical layer; `(startup.n.01, DOBJECT_OF, run.v.05)` exists from OntoNotes (newswire domain) but with low evidence_count (5 observations).
  - Resnik selectional association computed against this small evidence base; metric value 0.45.
  - Initial distribution moderately favors `run.v.05` but with high entropy.
  - SCMS BSP iterations may reduce entropy via cross-document context if available.

**Warm-system run on same input:**

  - Empirical layer has accumulated 250 additional observations of `(startup.n.01, DOBJECT_OF, run.v.05)` from this user's tasks in tech/business domain.
  - Resnik metric now 0.78 (much stronger evidence).
  - Initial distribution sharply favors `run.v.05` (~0.80 vs cold-start's 0.50).
  - Calibration error reduced.

**ALS Track A activity (continuous in warm system):**

  - Each successful task with WSD output → walks inference traces → identifies empirical-layer edges used → updates `evidence_count`, `metric_resnik_strength`, `last_observed`.
  - Auto-apply audit policy: validation runs (statistical sanity); if no anomalies, applied directly.
  - Admin gets summary report (per dream cycle): "Updated 1,847 empirical-layer edges; flagged 3 anomalies for review."

### Architectural pressures

  - **Empirical layer must grow over time.** Without dream-mining, system stays at cold-start performance forever.
  - **Class generalization (DOLCE mandatory) provides fallback** when leaf-edge evidence is sparse. Cold-start system uses class-level smoothing aggressively; warm system uses leaf-edge precision.
  - **Calibration improves with data.** Calibration target requires this — overconfidence on cold-start is a known bias.
  - **Auto-apply audit policy doesn't overload admin.** Admin sees aggregate stats only.
  - **Per-domain accumulation.** User's specific domain (tech/business) gets richer evidence than other domains they don't operate in.

### Coordinated-change implications

  - **Bootstrap quality is asymmetric per consumer.** WSD's reads benefit from SemCor + OntoNotes (high-volume general English). Specific domains underrepresented; cold-start performance varies by domain. Document this expectation.
  - **Auto-apply audit threshold tuning** — what's "an anomaly" worth flagging? Admin-tunable. Default: e.g., correlation strength changes >2σ from baseline; new edges with very low confidence on rare classes; etc.
  - **Empirical layer pruning** — does old, low-confidence evidence get pruned? Storage grows; some retention policy needed. Probably tied to `last_observed` + confidence-weighted aging. v1 design TBD.
  - **Domain conditioning** — should `domain_tag` propagate from task context to staged evidence? Helps per-domain calibration. Per L2 handoff §6.4 schema, `domain_tag` is on edges; dream miner must set it.

### Variants and edge cases

  - **V7.a:** New user starts with admin-distributed Global empirical layer (warmed via Global promotion across other users). Tests Global→Local replication semantics.
  - **V7.b:** Specialty user (e.g., medical professional) — bootstrap layer is general English; their domain is biomedical. Cold-start performance is poor; rapid improvement as their tasks accumulate.
  - **V7.c:** Adversarial — user submits all wrong inputs (intentional miscorrections via HITL). User's Local empirical layer drifts in wrong direction. Global gold-set V1 catches degradation; Local-to-Global promotion blocks the drift from polluting other users.
  - **V7.d:** Domain shift mid-deployment — user changes industry. Old empirical-layer evidence is stale. Class-generalization weights (per WSD architecture §5.5 Mechanism 5) adapt over time, lowering legacy-domain weight.

### Success criteria

  - Calibration ECE on warm system ≤ cold-start ECE - 0.01 (measurable improvement).
  - Admin audit summary report under 1 page per dream cycle for typical-load user.
  - V7.b: domain-specific accuracy improves significantly (>10pp) within 100 user tasks.
  - V7.c: gold-set V1 catches 100% of degradations larger than threshold.

### Failure modes this catches

  - Dream miner not running → empirical layer doesn't grow → cold-start performance forever.
  - Auto-apply policy applies bad updates without sanity validation → silent degradation.
  - V7.c: gold-set anchor missing → adversarial HITL corrupts Local; if Local→Global promotion fires without separate validation, Global gets corrupted too.
  - V7.d: class-generalization weights don't adapt → user stuck on legacy-domain priors.

---

## UC-WSD-8 — User opts out of training a specific subsystem

### Quick facts

- **Subsystems exercised:** L0 user_settings; ALS subsystem registration filtering; user-as-Local-admin audit policy override.
- **Lifecycle:** continuous — affects every dream cycle.
- **Architectural commitments tested:** L0 settings infrastructure; ALS gating per user; audit-policy-override (more-conservative-only).

### Setup

User Alice configures:

  - `als.training_enabled = true`.
  - `als.parameter_set.wsd_scorer.enabled = true`.
  - `als.parameter_set.wsd_scorer.priority = high`.
  - `als.parameter_set.fol_rules.enabled = false`. (Alice doesn't want FOL rule learning.)
  - `als.parameter_set.task_shape_recognition.audit_policy_override = "individual-review"`. (Subsystem default is `batched-summary`; Alice wants individual review.)

### Input

Same task inputs as UC-WSD-1 through UC-WSD-5; observed across multiple dream cycles.

### Expected behavior

  - WSD-scorer parameter updates: enabled, high priority. Larger evidence batches, more frequent training.
  - FOL rule confidence updates: **skipped entirely** for Alice. No staging rows written; no audit queue entries; no parameter updates.
  - Task-shape recognition updates: applied with individual-review audit policy (more conservative than declared `batched-summary`). Each proposed update reviewed separately by Alice.

### Walk-through

**At login:**

  - Server constructs Session including Alice's settings (lazy-loaded via `Session.get_settings("als.")`).

**During task execution:**

  - Phase 5 emits signals to ALS as normal — all signal-source capacities run regardless of settings.
  - But: signals targeting `fol_rules` parameter set are **filtered** before being staged. L4 reads Alice's `als.parameter_set.fol_rules.enabled = false`; staging-write is skipped for those rows.
  - Signals targeting `wsd_scorer` parameters are written to `parameter-staging` with priority annotation.
  - Signals targeting `task_shape_recognition` are written normally; audit policy override is applied at audit phase, not staging phase.

**At dream cycle:**

  - Maintenance dream pulls Alice's `parameter-staging` rows.
  - Aggregation runs only for enabled parameter sets.
  - For `task_shape_recognition`, dream produces proposed update; written to `pending-promotions` with `audit_policy: individual-review` (override applied).

**At audit:**

  - Alice's audit queue shows:
    - `wsd_scorer` proposed update — batched-summary (subsystem default) applied; one batch entry shown.
    - `task_shape_recognition` proposed updates — individual-review applied; one entry per proposal.
    - `fol_rules` — nothing (training disabled).

  - Alice reviews and approves WSD batch; reviews each task-shape proposal individually.

### Architectural pressures

  - **L0 settings read at correct lifecycle point** (start of dream cycle, or per-task signal-emission).
  - **ALS filters at staging phase** — disabled subsystems don't pollute staging with rows that will never be processed.
  - **Audit-policy override semantics** — user can move toward more conservative (`individual-review` over `batched-summary`); cannot move toward less conservative (`auto-apply` if subsystem says `individual-review`). L4 enforces at audit phase.
  - **Per-user state isolation.** Alice's settings affect only her Local; don't leak to other users or to Global.

### Coordinated-change implications

  - **L0 settings read latency** — must not be on hot path. Caching at session level appropriate.
  - **Settings change mid-session** — what happens? Settings updated by user during a session: do new settings apply immediately, or only on next session? L0 chat decides.
  - **Settings UI** — user must be able to view/edit. L0 surfaces JSON-shaped values; UI work needed for friendly editing.
  - **Default behavior on new ALS subsystem registration** — when a new subsystem registers, existing users implicitly opt in (per L0 handoff §6.4 open question). This means new training behaviors apply unless user opts out. Confirm acceptable.

### Variants and edge cases

  - **V8.a:** Alice tries to set `audit_policy_override = "auto-apply"` for a subsystem registered as `individual-review`. **Override rejected at L4 read time** with audit-log entry. Tests more-conservative-only enforcement.
  - **V8.b:** Alice has `als.training_enabled = false` (master switch). All training disabled regardless of per-subsystem settings. Tests master switch.
  - **V8.c:** Alice deletes her account. Settings cascade-deleted (per L0 handoff schema). Local parameter-staging and pending-promotions also cleared. Tests cleanup.
  - **V8.d:** Alice enables training mid-session. Mid-session enable: new staged rows from this point forward; previous task signals are lost (already filtered out at emission time). Documents the limitation.

### Success criteria

  - Disabled subsystems produce zero staging rows for that user.
  - Audit-policy override correctly applied (more-conservative) and correctly rejected (less-conservative).
  - Settings reads under 1ms (cached at session level).
  - V8.b master switch correctly disables all subsystems.

### Failure modes this catches

  - Disabled subsystem writes staging rows anyway → wasted storage; potentially confusing audit queue.
  - Override allows less-conservative change → user accidentally enables auto-apply on dangerous parameters.
  - Settings read on hot path → latency issues.
  - V8.c cascade incomplete → stale data after account deletion.

---

## UC-WSD-9 — Goal misidentification (silent failure)

### Quick facts

- **Subsystems exercised:** Phases 1-5 (initial, "successful"); external feedback; Phase 6 with goal-misidentification flagged.
- **Lifecycle:** initial run "succeeds" → external signal contradicts → Phase 6 attributes blame upstream → ALS demotes Phase 1 priors.
- **Architectural commitments tested:** Phase 4 verification limits; external-signal-only detection; Phase 6 backward propagation to Phase 1.

### Input

Task: *"Summarize this article."* (Article is provided as input — a 500-word piece on machine learning.)

External feedback (HITL): "I asked for a summary but you wrote a critique. The summary itself is fine, but it's the wrong task — I wanted a neutral summary, not your critical analysis."

### Task

Summarization. The task-shape recognition layer mistook the input for a critique-needed task because the article had some hedging language that triggered a `critique-evaluation-needed` recognizer.

### Expected output (initial run)

```
{
  "outcome": "success",
  "result": "<critical analysis of the article>",
  "task_shape": ["critique-evaluation-needed"],   // wrong recognition
  "verification_confidence": 0.91
}
```

### Walk-through

**Initial run:**

  - Phase 1: `recognize_task_shape` matches `critique-evaluation-needed` (incorrect) at confidence 0.79. The user's instruction "summarize" was overshadowed by the article's hedging language.
  - Phase 2: derives task goal accordingly. Pipeline includes critique-generation capacities.
  - Phase 3-4: pipeline runs successfully, produces critique. Goal verification: high confidence (0.91) — the critique is structurally complete.
  - Phase 5: consolidate as success. S6 positive signals to ALS.

**External signal arrives:**

  - User: "Wrong task. I wanted a summary, not a critique."

**Phase 6 — Failure diagnosis with goal-misidentification flagged:**

  - L4 invokes `analyze_failure_provenance` — but with a special flag: external signal contradicts the *task identification*, not just the output quality.
  - Provenance walk:
    - Phase 1 task-shape recognition: confidence 0.79 (lowest in the chain — flagged as primary suspect).
    - Phase 2 pipeline selection: confidence 0.90 (correct given the wrong task-shape).
    - Phase 3-4: confidence 0.91 (correct given the wrong pipeline).
  - Goal-misidentification heuristic: external signal targets task-identification → primary blame to Phase 1.
  - Output: `[(task_shape_recognition_priors, 0.70), (task_goal_derivation_priors, 0.20), (pipeline_selection_priors, 0.05), (other, 0.05)]`.

**Cross-validation:**

  - L4 invokes `cross_validate_failure` — but the alternative isn't another pipeline; it's another task-shape interpretation. L4 re-runs Phase 1 with a hint ("user said 'summarize'" — explicit lemma anchor). Now `summarize-needed` recognizer matches at higher confidence. Pipeline 2 with summarize-pipeline succeeds (the system can also produce summaries).
  - Cross-validation evidence: with explicit lemma anchor, system correctly identifies summarize task. Confirms blame on task-shape recognition layer's underweighting of explicit instruction-words.

**Route to ALS:**

  - S5 (HITL feedback) negative signal weighted by blame → mostly to `task_shape_recognition_priors`.
  - Specifically, the prior weighting that "explicit instruction lemma" should be heavily weighted.

**Dream-time + audit + apply** as in UC-WSD-6.

**Re-run:**

  - Same input, post-training. Phase 1 now correctly weights "summarize" as the primary instruction. Task-shape: `summarize-needed` at 0.92.
  - Pipeline runs; produces summary. Verification confidence 0.93.
  - User: correct.

### Architectural pressures

  - **Goal-misidentification is undetectable from internal signals alone.** Phase 4 verification confidence was 0.91 — the system thought it succeeded. Only S5 HITL caught it.
  - **Phase 6 backward attribution to Phase 1.** Most failure-attribution use cases hit Phase 2 or 3. UC-WSD-9 specifically tests attribution upstream — to interpretation, not execution.
  - **Cross-validation in Phase 6** can be re-running with a hint or an alternative interpretation, not just an alternative pipeline. Tests flexibility of cross-validation mechanism.
  - **External signal as the only oracle.** Without HITL or post-task gold validation, this failure stays silent. **The architecture is honest about this limitation.**

### Coordinated-change implications

  - **HITL UX must support task-shape feedback**, not just output-quality feedback. User can say "wrong task," not just "wrong answer." UX design implication.
  - **Phase 6 cross-validation strategies** — beyond alternative pipeline: alternative interpretation (re-run Phase 1 with hint), alternative parameters (counterfactual run with different priors), explicit user query ("Did you want X or Y?"). Each is a different `cross_validate_failure` strategy. v1 ships with what?
  - **Goal-misidentification gold set** — separate held-out gold for task-shape recognition (not just sense-disambiguation). Need to maintain.
  - **Documenting the limitation** — users should know that without external feedback, goal-misidentification is silent. Honest about the architectural blind spot.

### Variants and edge cases

  - **V9.a:** User provides feedback before consolidation (during Phase 4): "wait, this is wrong." L4 catches before Phase 5; doesn't write to memory; Phase 6 runs immediately.
  - **V9.b:** External feedback never arrives. System believes it succeeded; trains in wrong direction (S6 positive to wrong parameters). Insidious — Phase 6 only triggers on contradiction. **Documents the limitation: silent goal-misidentification compounds without external feedback.**
  - **V9.c:** Adversarial — user provides false negative feedback (claims wrong task when actually correct). System demotes correct Phase 1 priors. Gold set V1 catches; update rejected.
  - **V9.d:** Multi-step task where intermediate goal is misidentified. Phase 6 must trace blame back to *which* phase's interpretation diverged. More complex provenance walk.

### Success criteria

  - Phase 6 attributes >60% of blame to Phase 1 task-shape recognition (correct primary suspect).
  - Cross-validation with hint succeeds and confirms blame allocation.
  - Re-run after training correctly identifies task.
  - V9.b: documented limitation visible to admin in audit logs.

### Failure modes this catches

  - Phase 6 attributes blame to Phase 3 or 4 (where the actual execution was correct given the wrong task) — wastes training data.
  - Cross-validation only tries alternative pipelines, not alternative interpretations → can't detect goal-misidentification.
  - System trains positively on goal-misidentified successful runs → reinforces the wrong recognition.
  - V9.b: silent compounding without admin visibility.

---

## UC-WSD-10 — Domain shift and calibration drift

### Quick facts

- **Subsystems exercised:** ALS validators V1/V2/V3 (especially V3 distribution-drift alarm); cross-domain class-generalization weighting; admin audit decisions on drifting parameters.
- **Lifecycle:** longitudinal — system trained on news domain, deployed against biomedical text.
- **Architectural commitments tested:** drift detection; admin queue for V3 alarms; class-generalization per-hierarchy weight adaptation.

### Setup

System has been operating on general-English newswire for months. WSD scorer parameters in `learned-parameters` have converged. Lexicon empirical layer has rich `news`-domain edges.

User starts inputting biomedical text: *"The patient was prepped for the lumbar puncture procedure."*

### Input

Sequence of biomedical-domain inputs over weeks of usage.

### Expected behavior over time

**Initial biomedical input (week 1):**

  - WSD-init reads empirical layer; biomedical-domain `domain_tag` edges are sparse; falls back to general-English priors.
  - "patient" → `patient.n.01` (biomedical sense) at 0.65; `patient.adj.01` (calm/enduring) at 0.30. Distribution is wider than ideal because biomedical priors are weak.
  - "prepped" → `prep.v.01` (prepare) at 0.85; biomedical sense overlap.
  - "lumbar" → fine; specific term.
  - "puncture" → general sense; biomedical sense exists in lexicon but with low evidence.
  - Output: distributions calibrated but moderately wide.

**After 50 biomedical tasks (week 2-3):**

  - Empirical layer has accumulated biomedical-domain evidence (Track A auto-apply running). Edges with `domain_tag = "biomedical"` are strengthened.
  - V3 distribution-drift alarm fires: WSD-init's output distributions on biomedical text differ markedly from output on news text. Drift threshold exceeded.
  - V3 alarm sent to user's audit queue: "Significant distribution drift detected on biomedical-domain inputs. Possible causes: legitimate domain shift (parameters need updating); or systematic error (parameters need reverting)."
  - User sees options: "accept drift (continue updating)" or "revert to general parameters" or "keep both — use domain-conditional routing."

**User chooses domain-conditional (the smart choice):**

  - L4 trains class-generalization weights (per WSD architecture §5.5 Mechanism 5) to upweight biomedical-domain hierarchies (BFO if available; biomedical class systems) when input domain is `biomedical`.
  - WSD-init's queries become domain-aware: empirical layer query filtered by `domain_tag = current_domain_or_general`.

**After 200 biomedical tasks (week 4+):**

  - Domain-conditional routing fully active.
  - Calibration on biomedical text matches calibration on news text (both ~ECE 0.04).

### Walk-through (drift detection step)

V3 validator runs as part of ALS dream cycle. For each registered subsystem with parameters that affect output distributions:

  1. Generate probe inputs (held-out gold subset + recent task subset).
  2. Compute output distributions with current parameters and with previous-version parameters.
  3. Compute KL divergence between distributions.
  4. Aggregate by domain (using `domain_tag` on inputs).
  5. If any domain's KL > V3 threshold (admin-tunable, default e.g., 0.15), fire V3 alarm.

V3 alarm:

  - Written to `pending-promotions` with `validation_results: {V3_alarm: true, KL: 0.21, domain: biomedical}`.
  - Audit policy: even if subsystem is `auto-apply`, V3 alarm escalates to `individual-review` automatically.
  - User sees the alarm with diagnostic info.

### Architectural pressures

  - **V3 distribution-drift alarm catches legitimate domain shift before it corrupts general-domain calibration.**
  - **Per-domain edge tagging** (in lexicon empirical layer) is critical — without it, biomedical evidence dilutes news-domain priors and vice versa.
  - **Per-hierarchy weight learning** adapts to user's domain mix over time. UC-WSD-10 is the longitudinal validation of WSD architecture §5.5 Mechanism 5.
  - **Admin escalation on V3 alarm** — auto-apply doesn't override drift alarms. V3 forces admin review.
  - **Domain-conditional querying** — readers (WSD scorer) filter empirical layer by domain when context provides domain signal.

### Coordinated-change implications

  - **Domain detection** — how does system know input is biomedical? Implicit via task-shape patterns? Explicit via session metadata? L2 task-patterns may need a `domain` declaration. Open design item.
  - **V3 alarm threshold** — admin-tunable; default value needs careful initial calibration.
  - **Domain-conditional routing UI** — user/admin sees the option; needs to understand it. UX work.
  - **Multi-hierarchy fusion across domains** — when biomedical text needs BFO (per FOL #11) but only DOLCE is available, class-generalization weights give partial smoothing but with limits. Documents the gap.

### Variants and edge cases

  - **V10.a:** User has mixed-domain input (some biomedical, some news, some legal). System learns per-domain weights independently. Tests multi-domain coexistence.
  - **V10.b:** Adversarial — user inputs garbage characterized as biomedical. V3 alarm fires; user reviews and rejects (treats as garbage); biomedical empirical layer remains unaffected.
  - **V10.c:** Slow drift over months (no sudden change). Each individual update passes V3 (small KL); cumulatively the system has shifted significantly. Tests whether V3 catches gradual drift via cumulative metric or only sudden changes. Recommendation: V3 should track baseline-relative drift over a window, not just turn-over-turn.
  - **V10.d:** Domain shift mid-task. User starts biomedical; switches to news mid-conversation. Per-domain caching needs to handle this.

### Success criteria

  - V3 alarm fires within 50 biomedical tasks of system's first exposure.
  - Domain-conditional routing reduces calibration drift on news domain post-shift.
  - Per-hierarchy weights show measurable adaptation over 200 tasks.
  - V10.b: gold set V1 catches the rejection; biomedical layer stays clean.

### Failure modes this catches

  - V3 not implemented → silent calibration drift → news-domain calibration degrades as biomedical edges pollute.
  - Per-domain tagging missing → all evidence pooled; can't separate; no domain conditioning possible.
  - Per-hierarchy weights frozen → no adaptation; user gets one-size-fits-all priors regardless of domain.
  - V10.c: V3 only catches sudden changes → gradual drift accumulates undetected.

---

## UC-WSD-11 — Three-capacity NLU composition (WSD + FOL + Frame)

### Quick facts

- **Subsystems exercised:** WSD, FOL, Frame-understanding running together as a composed NLU path; SCMS BSP turns; intergraph-edge traversal across lexicon → concepts → frames.
- **Lifecycle phases:** 1 → 2 → 3 (full path execution with three coupled capacities) → 4 → 5.
- **Architectural commitments tested:** Frame as v1 capacity (currently invisible in UC-1–10); DataState handoff between capacities; path-engine-handled inter-graph traversal (decision B from goal-finalization, 2026-04-30); paths-of-paths composition at the NLU level.

### Input

Sentence: *"The defendant pleaded guilty to the judge."*

### Task

Produce a calibrated NLU annotation comprising:
  - sense distributions for content words (WSD output),
  - logical entailments (FOL output),
  - extracted frame instance(s) (Frame output, with role fillers).

### Expected output

```
WSD:
  defendant:  [{defendant.n.01: 0.95}, ...]
  pleaded:    [{plead.v.02 (legal speech act): 0.85}, {plead.v.01 (general beg): 0.10}, ...]
  guilty:     [{guilty.s.01 (admitting fault): 0.90}, ...]
  judge:      [{judge.n.01 (court official): 0.92}, {judge.n.02 (assessor): 0.05}, ...]

Frame:
  Plea_event:
    Defendant   = "defendant"     (filler-confidence 0.94)
    Plea_value  = "guilty"        (filler-confidence 0.93)
    Authority   = "judge"         (filler-confidence 0.91)

FOL:
  ∃e Plea(e) ∧ Speaker(e, defendant) ∧ Audience(e, judge) ∧ Content(e, guilty)
  Asserts(defendant, guilty)
  Court_setting(e)   [derived from Frame + concepts.court]
```

### Walk-through

**Phase 1 — Task interpretation.**

  - `recognize_task_shape` matches `nlu-full-annotation-needed` (frame extraction + sense distributions + entailments). Confidence 0.93.

**Phase 2 — Pipeline determination.**

  - `lookup_known_pipeline` returns the canonical NLU path: `tokenize → dep_parse → wsd-init → frame-init → fol-init → SCMS-monitors → calibrate-output`. Each `*-init` step is itself a promoted sub-path (paths-of-paths).
  - The path crosses graphs via path-engine-handled inter-graph hops:
    - WSD sub-path reads from `lexicon` (theoretical + empirical layers).
    - Frame sub-path reads from `concepts` (FrameNet structure) via metaedge `lexicon→concepts`.
    - FOL sub-path reads from `ontology` (DOLCE) and `learned-parameters` via metaedges.

**Phase 3 — Pipeline execution with SCMS.**

  - `wsd-init` runs first; produces initial sense distributions. `pleaded` is moderate-confidence (legal-vs-general).
  - `frame-init` runs concurrently on the parsed input + initial sense distributions. Frame matcher proposes `Plea_event` because of high evocation from `pleaded` + presence of court-context words. Frame fillers tentatively assigned.
  - `fol-init` runs; derives `Plea(e) ∧ Speaker(e, defendant)` as initial atoms.
  - **SCMS BSP turn 1.** Monitors emit:
    - `frame-match` monitor: Frame's confident `Plea_event` evocation increases evidence for `plead.v.02` (legal sense). Sends partial signal to `wsd-update`.
    - `fol-update` monitor: FOL's `Court_setting(e)` derived predicate increases evidence for `judge.n.01` over `judge.n.02`.
    - `cross-word` monitor: legal-domain coherence across all four content words reinforces the legal-sense cluster.
  - MSUR resolves signals (none contradictory; all reinforce). `wsd-update` integrates: `pleaded` lifts from 0.85 → 0.92, `judge` lifts from 0.85 → 0.92.
  - **SCMS BSP turn 2.** State changes from turn 1 trigger: `fol-update` re-derives with sharpened sense distributions; no new atoms produced. `frame-match` re-checks; fillers stable. **Pair-wise quiescence reached.**

**Phase 4 — Goal verification.** Three-capacity output present and calibration-shaped. Confidence 0.91.

**Phase 5 — Outcome processing.** S6 task-outcome positive. ALS receives signals attributed to each sub-path (WSD-path, Frame-path, FOL-path independently).

### Architectural pressures

  - **Three coupled capacities running as composed path.** Validates that v1's stated NLU stack (WSD + FOL + Frame) actually executes coherently end-to-end — UC-1 through UC-10 don't exercise Frame.
  - **DataState handoff schema between capacities.** Frame-init consumes WSD's sense distribution + parsed input + lexicon edges. FOL consumes Frame's role-fillers + sense distributions. Each handoff requires DataState type-compatibility (per L3 capacity layer's `strict_compatible`).
  - **Path-engine-handled inter-graph traversal.** Path crosses lexicon → concepts → frames → ontology graphs through metaedges, with the path executor (not capacities) managing graph context.
  - **Paths-of-paths at the NLU level.** The composed NLU path references sub-paths (`wsd-init-path`, `frame-init-path`, `fol-init-path`); reference-graph tracks dependencies for cascade flagging.
  - **SCMS as L3 orchestration capacity invoked by L4.** The capacity is dormant until invoked; once invoked, manages BSP turns until pair-wise quiescence.

### Coordinated-change implications

  - **Frame-init capacity** must exist as a v1 promoted-path with its own DataState signature. Currently undesigned at the path level; needs a dedicated handoff entry.
  - **Frame-match monitor** must exist with state-change-driven emission semantics matching the other SCMS monitors.
  - **DataState taxonomy** for NLU stack: `DS_PARSED_TEXT → DS_SENSE_DISTRIBUTIONS → DS_FRAME_INSTANCES → DS_FOL_ATOMS → DS_NLU_FULL_ANNOTATION`. Each shape needs explicit definition to support `strict_compatible` checks at path registration time.
  - **Inter-graph hop primitives** in the path executor (decision B): the path executor needs `hop_to_graph(metaedge_id, datastate)` semantics. Not in current L1 docs; ADR needed.

### Variants and edge cases

  - **V11.a:** WSD's `pleaded` distribution comes out incorrect (general sense over legal). Frame-match monitor's signal corrects via SCMS BSP iteration. Tests mutual-refinement among three capacities.
  - **V11.b:** Frame-match cannot find a frame for the input (concept gap). Falls back to WSD + FOL only; calibration must reflect the frame absence honestly.
  - **V11.c:** FOL derives a contradiction (e.g. inferred sense conflicts with frame-derived predicate). MSUR opens an assumption thread; resolves by per-monitor evaluator.
  - **V11.d:** Path-executor cannot find the metaedge for an inter-graph hop. Path execution fails with a structural error before any capacity runs; tests path-validity gating at execution start.

### Success criteria

  - All three capacities produce output. Top-1 sense for content words ≥0.85 confidence after SCMS quiescence.
  - Frame `Plea_event` extracted with all role fillers present.
  - FOL atoms derived without contradiction.
  - Total SCMS turns ≤4 for this input.
  - Path execution validates DataState compatibility at every hop.

### Failure modes this catches

  - Frame capacity missing or non-callable as a path → v1 NLU stack is incomplete.
  - DataState handoff between WSD and Frame fails type-check → silent path-misregistration.
  - Path-executor doesn't support inter-graph hops → entire NLU path can't run.
  - SCMS quiescence not reached because Frame and WSD send contradictory signals MSUR can't resolve → infinite turns or arbitrary cutoff.
  - Reference-graph dependency on Frame-path missing → updates to Frame-path don't flag the NLU-path stale.

---

## UC-WSD-12 — Multi-metric dream recomposition and admin selection

### Quick facts

- **Subsystems exercised:** Dream system fan-out; multi-metric outcome evaluation; minimal user UI metric panel; admin-selection logging.
- **Lifecycle phases:** dream-time (out-of-task) → variant generation → multi-metric validation → admin selection via UI → versioned apply.
- **Architectural commitments tested:** Multiple recomposed variants per dream cycle, each maximizing a different outcome metric; user-facing tradeoff panel; admin-decision rationale logging; promotion-rule-capacity auto-selection by L4 with admin override available.

### Setup

A WSD scoring sub-path `P_score` has been used 200+ times over the past 30 days. Outcome history shows it's stable but not optimal. A scheduled dream cycle decides to explore recompositions.

### Input

Existing `P_score` and a held-out task set of 500 sentences spanning legal, medical, general-English, and technical domains.

### Expected behavior

Dream generates ≥2 variants (selected examples: `P_score_cal` calibration-prioritized, `P_score_acc` accuracy-prioritized, `P_score_cov` coverage-prioritized). Each is validated against the held-out set on the full metric set. The minimal UI panel shows the tradeoff surface to the user (as Local admin); user picks one (or none) with logged rationale.

### Walk-through

**Dream-time variant generation.**

  - Dream system reads the user's `dream-priorities` (per UC-15+ design — user can specify dream priorities of any of four meanings: goals, metrics, paths to vary, weight on cycles). Suppose priorities specify "honest confidence + decent accuracy."
  - Dream generates three candidate recompositions of `P_score` by substituting sub-segments:
    - `P_score_cal`: replaces the scoring sub-segment with a calibration-aware-training-trained variant.
    - `P_score_acc`: replaces with a sharper top-1-confidence-pushing variant.
    - `P_score_cov`: keeps the original scoring sub-segment but adjusts the prior to favor higher-confidence commitments above τ.

**Multi-metric validation.**

  - Each variant runs against the 500-sentence held-out set. Metrics computed:

| Variant | ECE | Brier | Top-1 | Top-3 | Coverage@0.7 | Per-domain top-1 (legal/med/gen/tech) |
| --- | --- | --- | --- | --- | --- | --- |
| Incumbent | 0.05 | 0.12 | 88% | 96% | 70% | 73 / 84 / 92 / 85 |
| `P_score_cal` | 0.03 | 0.10 | 86% | 96% | 65% | 80 / 86 / 91 / 84 |
| `P_score_acc` | 0.08 | 0.13 | 91% | 97% | 78% | 87 / 88 / 92 / 87 |
| `P_score_cov` | 0.05 | 0.12 | 88% | 96% | 73% | 75 / 84 / 92 / 85 |

  - Anti-regression gates (V1 gold drift, V2 calibration anti-regression) check each variant. `P_score_acc` fails calibration anti-regression (ECE worsens beyond ε=0.02 threshold) — flagged as conditional candidate, not auto-rejected because the user might still want it.
  - Pareto-frontier promotion-rule capacity surfaces non-dominated candidates: `P_score_cal` (best ECE, Brier, calibration metrics) and `P_score_acc` (best Top-1, Coverage). Incumbent and `P_score_cov` are dominated.

**Admin-panel UI.**

  - User opens minimal UI's audit/promotion panel.
  - Panel shows the table above plus:
    - Per-variant "examples this would have changed" with diffs (5–10 representative cases).
    - Anti-regression flag on `P_score_acc` highlighted.
    - L4's auto-recommended action: "Pareto-frontier rule selected; two non-dominated candidates surfaced."
  - User picks `P_score_cal` because honest confidence aligns with their priorities. Rationale field captures: "calibration is primary; willing to trade 2pts of top-1 for ECE 0.03."
  - Decision logged to audit trail. `P_score_acc` and `P_score_cov` archived (retained for future reference but not promoted).

**Apply.**

  - L4 versioned-writes `P_score_cal` to Local `promoted-pipelines`. Reference graph updated; dependents flagged stale.

### Architectural pressures

  - **Dream fan-out.** Single dream cycle produces multiple variants targeting different metrics — central to the goal-finalization decision (2026-04-30) that all promotion-rule and metric options live as capacities.
  - **Multi-metric outcome computation.** All metrics measured every cycle; promotion uses a subset.
  - **Pareto-frontier promotion-rule capacity.** Surfaces non-dominated candidates only.
  - **Anti-regression gates.** Catch variants that improve one metric at the cost of degrading a foundational commitment (calibration).
  - **Admin-selection rationale logging.** Future dream cycles may learn from this admin's preferences (out-of-v1 capability but the data trail is captured now).

### Coordinated-change implications

  - **Variant-generation strategy** in the dream system needs explicit design: how does dream pick which sub-segments to substitute and which metrics to maximize? v1 needs a defaults list.
  - **"Dream priorities"** as a user-editable concept in the minimal UI needs a schema covering all four meanings (goal, metric, path-to-vary, cycle-weight).
  - **Per-variant per-domain reporting** in the panel — domain tags must propagate through metric computation. Adjacent to UC-7/UC-10 implications.
  - **Anti-regression gate parameters** (ε for calibration, gold-drift threshold) — need v1 defaults plus admin-tunable overrides.

### Variants and edge cases

  - **V12.a:** All variants are dominated by incumbent. Dream reports "no candidate to promote"; no panel shown; staged signals retained for next cycle.
  - **V12.b:** Two variants Pareto-tie (e.g. each is best on a disjoint metric set). Panel surfaces both equally. UC-WSD-13 explores this further.
  - **V12.c:** User picks "split-promote" — promote `P_score_cal` for a calibration-prioritized pipeline class and `P_score_acc` for accuracy-prioritized. Tests the multi-pipeline-class promotion model (out-of-v1, but logging captures the admin's intent).
  - **V12.d:** Dream cycle interrupted (system load); partial variants validated. Panel shows only the validated subset; remaining variants queued for next cycle.

### Success criteria

  - Dream produces ≥2 variants per cycle when ≥1 metric tradeoff exists.
  - Pareto-frontier rule correctly identifies non-dominated candidates.
  - Anti-regression gates catch genuine regressions without false positives on tail-domain cases.
  - Panel displays full metric matrix + per-variant changed-example diffs.
  - User selection logged with rationale; non-selected variants archived.

### Failure modes this catches

  - Dream produces only one variant → admin can't see tradeoffs.
  - Metrics not all measured → tradeoff invisible.
  - Anti-regression gate too strict → all useful variants rejected.
  - Anti-regression gate too lax → variants that destroy a foundational metric get promoted.
  - Panel shows just deltas, no examples → admin makes uninformed selection.

---

## UC-WSD-13 — Promotion under genuine metric conflict (Pareto non-dominance)

### Quick facts

- **Subsystems exercised:** Pareto-frontier promotion-rule capacity; admin UI tradeoff panel; decision-precedent logging.
- **Lifecycle phases:** dream-time variant generation → multi-metric validation → genuine non-domination detected → admin sees explicit tradeoff with concrete examples → admin chooses with rationale → decision logged for future precedent reference.
- **Architectural commitments tested:** the system handles cases where no variant is strictly better; admin gets a tradeoff surface, not a number; rationale becomes a precedent that can inform future similar decisions.

### Setup

Two recomposed variants of a WSD scoring sub-path emerge from a dream cycle. Neither dominates the other on the full metric set.

### Input

Variants `P_A` and `P_B`, each validated against the same held-out set.

### Expected behavior

| Variant | ECE | Top-1 | Coverage@0.7 | Tail-domain (technical) Top-1 | Latency |
| --- | --- | --- | --- | --- | --- |
| Incumbent | 0.05 | 88% | 70% | 78% | 80ms |
| `P_A` | 0.03 | 87% | 65% | 82% | 90ms |
| `P_B` | 0.06 | 91% | 78% | 76% | 70ms |

`P_A` wins on calibration (ECE), tail-domain accuracy. `P_B` wins on accuracy (Top-1), coverage, latency. Neither dominates.

### Walk-through

  - Pareto-frontier rule capacity surfaces both as non-dominated candidates.
  - Panel UI shows:
    - Side-by-side metric comparison.
    - "Examples where `P_A` is better" — a list of ~10 concrete inputs with predictions from both variants and gold.
    - "Examples where `P_B` is better" — same.
    - "Examples where they agree with incumbent" — count.
  - L4's auto-recommendation: "Genuine tradeoff; admin decision required." No automated tiebreak.
  - Admin examines the example diffs and decides:
    - Picks `P_A` because tail-domain calibration is critical for the user's typical task profile (legal + technical).
    - Rationale field: "tail-domain matters here; willing to trade 4pts coverage for 4pts tail-domain accuracy + better calibration."
  - Decision logged. Audit trail records: (a) the metric snapshot, (b) the example diffs viewed, (c) admin's rationale, (d) selected variant ID.
  - **Decision precedent:** future dream cycles produce a similar tradeoff. The system surfaces the previous decision rationale ("you previously prioritized tail-domain over coverage") as advisory context — but does not auto-apply.

### Architectural pressures

  - **Pareto-frontier rule** must correctly identify non-domination over arbitrary metric sets.
  - **Tradeoff-surface UX** requires the panel to surface concrete examples, not just numbers — without examples, admin can't reason about which tradeoff matters for their workload.
  - **Decision-precedent retrieval.** When similar tradeoffs arise later, prior rationale is fetched and shown — but never auto-applied (admin always re-decides).
  - **Rationale capture as schema'd field.** Free-text rationale must be searchable/structured enough to surface as precedent.

### Coordinated-change implications

  - **Concrete-example diff generator** in the panel UI needs a v1 design: how does it pick which examples to surface? Random subset? Most-changed? Per-domain stratified?
  - **Decision-precedent retrieval** in the audit subsystem — needs a similarity function over admin decisions (metric-snapshot similarity + variant-change similarity).
  - **Rationale schema** — free-text + tags? Structured fields (priority, willing-to-trade, etc.)?

### Variants and edge cases

  - **V13.a:** Three or more non-dominated variants. Panel must scale to N candidates; visual layout for >2 needs design.
  - **V13.b:** Admin rejects all non-dominated candidates (none worth promoting). Logged; staged for next cycle.
  - **V13.c:** Tradeoff is so close that the metric differences are within noise. System flags "tradeoff may be noise; consider re-running validation with larger held-out set" before admin decides.
  - **V13.d:** Admin's rationale is internally inconsistent across multiple decisions (earlier picked calibration; this time picks accuracy under similar tradeoff). System notes the inconsistency in audit but does not block.

### Success criteria

  - Pareto rule correctly identifies non-domination on real cases.
  - Panel displays tradeoff with concrete examples per axis.
  - Admin selection logs structured rationale.
  - Future similar decisions surface prior rationale as advisory.

### Failure modes this catches

  - Pareto-rule implementation incorrect → wrongly drops a non-dominated candidate.
  - Panel shows only metrics, no examples → admin selection is uninformed.
  - Rationale captured as raw text only, never retrievable → no precedent reuse.
  - Decision precedent auto-applied without admin re-decision → audit guarantee weakened.

---

## UC-WSD-14 — Capacity-limitation discovery (data-gap vs. capacity-gap)

### Quick facts

- **Subsystems exercised:** Phase 6 attribution distinguishing data sparsity from capacity absence; capacity-gap admin queue; minimal UI surface for "missing capacity" reports.
- **Lifecycle phases:** 1 → 2 → 3 (failure or low-confidence output) → 4 → 6 → capacity-gap classifier → admin queue.
- **Architectural commitments tested:** The reactive "discover capacities as needed" claim from goal-finalization (2026-04-30); distinction between *data gap* (insufficient examples) and *capacity gap* (no operation exists for this concept type); admin sees missing-capacity proposals and decides whether to design new capacity or accept limitation.

### Input

Sentence: *"Mary said John might come to the meeting."*

### Task

Sense annotation + entailment derivation.

### Expected behavior

WSD produces sense distributions for content words. FOL begins entailment derivation but cannot represent the modal *might* — its modal-reasoning capacity does not exist in v1. SCMS BSP turns reach quiescence with FOL output flagged "modal scope unhandled." Phase 4 verifies what was achievable. Phase 6 (triggered by partial-success flag) classifies the residual as capacity gap, not data gap.

### Walk-through

**Phases 1–4.** Path executes. WSD output normal. Frame matches `Statement` and `Possible_event`. FOL derives `Said(Mary, ?content)` but cannot resolve `?content` because *might come* requires modal logic that the FOL capacity does not support. FOL emits a partial-output marker tagged `modal-scope-unhandled`.

**Phase 6 — Failure (or partial-success) diagnosis.**

  - Attribution walks the path. WSD, Frame: high confidence, no blame. FOL: low confidence on the residual; marker `modal-scope-unhandled`.
  - **Data-gap vs capacity-gap classifier.** L4 invokes a classifier that distinguishes:
    - *Data gap* — capacity exists but lacks training examples (signal: similar inputs in past have produced confident output; this case is an outlier).
    - *Capacity gap* — capacity to handle this concept type does not exist at all (signal: marker emitted by capacity itself; or signal: similar inputs have all produced the same partial-output marker over many runs).
  - For this case: marker is the dominant signal. Classifier outputs `capacity-gap: modal-reasoning-missing`.

**Capacity-gap admin queue.**

  - Failure routed to a separate admin queue (distinct from ALS staging).
  - Admin sees in minimal UI:
    - Capacity-gap report: "modal-reasoning-missing — fired on 47 inputs over last 30 days."
    - Suggested capacity sketch: "modal operator handling for FOL — DataState changes: add `modal-tag` to FOL atoms; capacity transforms `Said(X, P) → Said(X, ◇P)` for *might/may/could*."
    - Example inputs that triggered the marker.
  - Admin decides:
    - Design and implement the missing capacity (out-of-v1; feature request logged).
    - Accept the limitation (mark v1 as not handling modal reasoning; calibration-honest output continues; capacity-gap marker visible to end users in their output).
    - Defer (re-evaluate next quarter when input volume justifies).

### Architectural pressures

  - **Data-gap vs capacity-gap distinction at Phase 6.** The classifier needs explicit design — which signals indicate which type of gap.
  - **Capacity-gap marker propagation.** Capacities themselves emit markers when they encounter inputs they cannot handle. This is a contract on every L3 capacity: must emit `unhandled-input-class` markers rather than silently producing junk.
  - **Capacity-gap admin queue** distinct from ALS staging.
  - **Admin UI surface for capacity proposals.** Sketch fields, example inputs, frequency, suggested DataState changes.

### Coordinated-change implications

  - **Capacity contract: emit unhandled-input markers.** Every L3 capacity (atomic and composed) must expose `unhandled_inputs` semantics. Needs ADR.
  - **Data-gap-vs-capacity-gap classifier** as itself an L3 capacity.
  - **Capacity-gap admin UI** in minimal UI scope. Adjacent to the user-add capacity surface; same UI but admin-only routing for system-wide capacity addition.
  - **Frequency thresholds** for surfacing capacity-gap reports (suppress noise from one-off cases).

### Variants and edge cases

  - **V14.a:** Capacity-gap marker fires once. System suppresses (single occurrence below threshold). Tests noise filtering.
  - **V14.b:** Marker fires from many distinct inputs but the underlying issue is data-gap (capacity exists but lacks training). Classifier must correctly diagnose and route to ALS, not capacity-gap queue.
  - **V14.c:** Multiple capacity gaps fire from the same input (modal scope + temporal scope + quantifier scope). Classifier surfaces a clustered report, not three separate ones.
  - **V14.d:** Admin designs the missing capacity. Once added, prior capacity-gap report queue items are re-evaluated against the new capacity to confirm they resolve.

### Success criteria

  - Phase 6 correctly distinguishes data-gap from capacity-gap on canonical examples.
  - Capacity-gap reports surface to admin within ≤1 dream cycle of threshold being crossed.
  - Reports include frequency, examples, and suggested capacity sketch.
  - Admin can accept/defer/escalate from minimal UI.

### Failure modes this catches

  - Capacity emits silent junk on unhandled inputs (no marker) → classifier sees data gap (false negative) → wastes training data on a problem training cannot fix.
  - Classifier biased toward data-gap → real capacity gaps invisible.
  - Capacity-gap report routes into ALS by mistake → noise in staging signals.
  - Threshold too low → admin queue flooded with one-off noise.

---

## UC-WSD-15 — Cross-consumer blame attribution (WSD vs FOL vs Frame)

### Quick facts

- **Subsystems exercised:** Phase 6 path-segment blame attribution under composed NLU paths; cross-validation by sub-path substitution; signal routing to the correctly-blamed sub-path's ALS lane.
- **Lifecycle phases:** Composed NLU run → downstream failure → Phase 6 walks the multi-capacity path → cross-validation by single-capacity substitution → blame correctly localized → signals routed to one ALS lane only.
- **Architectural commitments tested:** Path-segment-level blame attribution; cross-validation as substitution along the path; consumer-coupled outcome metrics (R3 phased adoption — internal v1.0, consumer-coupled gating later).

### Input

Sentence: *"The patient pleaded with the doctor."*

### Task

Full NLU annotation; downstream task is "extract the patient's emotional state."

### Expected behavior (failure case)

The composed NLU path runs. WSD assigns `pleaded` correctly to general-emotional-plead sense. Frame matches `Plea_event` correctly. But FOL derives the wrong emotional state (`Anger(patient)` instead of `Distress(patient)`) due to a bug in its sentiment-mapping capacity. The downstream task fails. Phase 6 must localize blame to FOL, not WSD or Frame.

### Walk-through

**Phase 6 — Path-segment attribution.**

  - Walks the path: tokenize → dep-parse → wsd-init → frame-init → fol-init → emotion-extract.
  - Per-segment confidence: tokenize 0.99, dep-parse 0.95, wsd-init 0.92, frame-init 0.90, fol-init 0.65 (low — FOL output flagged inconsistent), emotion-extract 0.70.
  - Initial heuristic blame share: fol-init (0.55), emotion-extract (0.30), others ≤0.05.

**Cross-validation by sub-path substitution.**

  - L4 substitutes wsd-init with an alternative WSD sub-path → result still wrong → WSD not the cause.
  - L4 substitutes frame-init with an alternative → result still wrong → Frame not the cause.
  - L4 substitutes fol-init with an alternative → result corrects to `Distress(patient)` → FOL was the cause.
  - Blame localized: fol-init (0.85), emotion-extract (0.10), others ≤0.05.

**Signal routing.**

  - S5 (HITL) signal weighted by blame.
  - Routed only to FOL's ALS lane. WSD and Frame staging untouched.
  - Reference-graph: any composed NLU path referencing fol-init flagged stale.

### Architectural pressures

  - **Path-segment blame requires per-segment provenance** — confidence, replan-divergence, output marker — captured during execution.
  - **Cross-validation by substitution** assumes alternative sub-paths exist or can be cheaply synthesized. v1 needs a default alternative-sub-path registry per capacity type.
  - **Signal routing to a single ALS lane** prevents misattribution across capacities.
  - **Reference-graph staleness propagation** at sub-path granularity.

### Coordinated-change implications

  - **Per-segment provenance schema** must capture confidence, divergence, output markers. Extends current Phase-6 design.
  - **Alternative-sub-path registry** per capacity type for cross-validation. v1: at minimum 2 alternatives per capacity in the v1 NLU stack.
  - **ALS lane separation** by capacity — staging signals partition by which capacity is implicated.
  - **Cross-validation budget** — substitution doubles compute. Budget management needed.

### Variants and edge cases

  - **V15.a:** Multiple capacities partially wrong. Substitution shows each contributes; blame distributed proportionally.
  - **V15.b:** Substitution doesn't find an alternative that fixes the failure (FOL alternatives all fail too → real capacity gap, not implementation bug). Blame routes to capacity-gap queue (UC-14 link).
  - **V15.c:** Substitution introduces a new failure (alternative WSD sub-path produces a different downstream failure). Cross-validation evidence becomes ambiguous; diagnostic confidence drops; admin sees both signals.
  - **V15.d:** Failure is upstream of NLU (e.g. dep-parse). Substitution along NLU sub-paths doesn't fix it; blame correctly localizes to dep-parse despite downstream NLU sub-paths having lower per-segment confidence.

### Success criteria

  - Phase 6 + cross-validation correctly localize blame to the offending capacity in ≥80% of canonical multi-capacity failure cases.
  - Signals route to one ALS lane only (no cross-contamination of WSD, Frame, FOL staging).
  - Reference-graph staleness flags propagate correctly at sub-path granularity.

### Failure modes this catches

  - Phase 6 only attributes blame at flat parameter-set granularity → cannot localize across composed paths → wrong capacity gets the training signal.
  - Cross-validation alternative registry missing → blame can never be empirically confirmed by substitution.
  - Signals route to all capacities' ALS lanes → all three get noisy training data from the same failure.

---

## UC-WSD-16 — Value-typed paths-of-paths and registry expression metadata

### Quick facts

- **Subsystems exercised:** Path registration with sub-path composition shorthand; expression-metadata recomputation on sub-path updates; per-level independent dream improvement; admin UI display of equivalent expressions.
- **Lifecycle phases:** user composes P_new from existing P1 + C via UI → system inlines P1's current atomic sequence at registration → P_new stored as A–B–C (value-typed, not reference-typed) → P1 later updates → P_new content unchanged but its expression metadata is recomputed.
- **Architectural commitments tested:** Paths-of-paths-always **as registration shorthand** (decision 2026-04-30, clarified later in same session); paths are **value-typed**, frozen-at-registration, no cascade re-evaluation; dream improvements run **independently at each level**; expression metadata for display can be recomputed without affecting path content.

### Input

Three paths exist after registration:
  - P1 = A–B (a WSD scoring sub-path).
  - P2 = A–B–C, registered via shorthand "P1–C" (system inlined P1 to A–B at registration).
  - P3 = A–B–C–D, registered via shorthand "P2–D" or "P1–C–D" (system inlined to A–B–C–D either way).

A dream cycle then promotes P1 → P1' = A–B' (B replaced with a calibration-aware variant; admin selected via UC-12 panel).

### Expected behavior

  - P1 now contains A–B'. Old A–B retained per audit policy (immutable-with-versions or mutable-with-history — v1 design decision).
  - P2 is **still A–B–C**. Unchanged. Outcome history valid. Calibration unchanged.
  - P3 is **still A–B–C–D**. Unchanged. Outcome history valid.
  - The **expression metadata** for P2 and P3 is recomputed: P2 was previously displayable as "P1–C" (because P1 = A–B); after the update, P1 = A–B' no longer matches the prefix of P2's atomic sequence, so the "P1–C" abbreviation is removed from P2's display forms. P2 may now match against other paths or be displayed only in atomic form.
  - To benefit from the calibration-aware B', P2 and P3 must be **independently dreamed/recomposed** — there is no auto-propagation. The flywheel runs separately at every level.
  - Admin UI shows P1' (new), P2 unchanged, P3 unchanged. No staleness flags. Display abbreviations are recomputed lazily on read or eagerly on update (v1 design decision).

### Walk-through

**Registration of P2 via shorthand.**

  - User in minimal UI composes P2 = "P1–C". P1's atomic sequence at this moment is A–B.
  - System inlines: P2's stored atomic sequence is A–B–C.
  - Expression-metadata table records: P2 was registered via expression "P1–C" at the time when P1 = A–B.
  - P2 is value-typed; its content does not depend on future changes to P1.

**Registration of P3 via shorthand.**

  - User composes P3 = "P2–D". At registration, P2 = A–B–C. P3 stored as A–B–C–D.
  - Expression-metadata records the registration form.

**P1 update via dream cycle.**

  - Dream produces variant P1' = A–B' targeting calibration. Admin selects via UC-12 panel. P1' applied.
  - Whether this is "P1 mutated to A–B'" or "new path P1' registered as successor with old P1 retained" depends on the path-mutability decision (v1 TBD; both are supported by the value-typed model).

**Expression-metadata recomputation.**

  - System recomputes which abbreviations remain valid for displaying P2 and P3.
  - For P2 (atomic A–B–C):
    - "P1–C" no longer matches (P1 = A–B' now, prefix mismatch).
    - If any *other* registered path matches a prefix of A–B–C, P2's display form may use that. Otherwise P2 displays as the atomic sequence.
  - For P3 (atomic A–B–C–D):
    - "P2–D" still matches (P2 = A–B–C unchanged).
    - "P1–C–D" no longer matches.
    - P3 displays as "P2–D" preferentially.

**No staleness, no re-evaluation.**

  - P2's outcome history remains valid (its content is unchanged).
  - P3's outcome history remains valid.
  - No promotion gates triggered.

**Independent improvement (separate dream cycle).**

  - To bring P2 into the calibration-aware regime, a separate dream cycle on P2 must run. It might generate P2' = A–B'–C by recomposing P2 with the new scoring sub-path B'. This P2' is registered as a new path; admin compares P2' vs P2 via UC-12 panel.

### Architectural pressures

  - **Inlining at registration.** Composition shorthand resolves to atomic sequence at registration time; this is the authoritative content.
  - **Expression-metadata recomputation.** When any path is updated, the registry walks paths whose expressions referenced it and recomputes their preferred display form. Cheap (no behavioral re-eval).
  - **Per-level independent flywheel.** Dream improvements at level N do not propagate to N+1. Admin/system must schedule dreams across levels.
  - **Path mutability decision.** Paths are either mutable-with-version-history (P1 → P1' in place) or immutable-with-successor-IDs (P1' is a new entity). Either fits the value-typed model. Decision pending.
  - **Atomic-capacity update propagation** is a separate question — when an L3 atomic capacity B is updated, do all paths containing B execute with new B (reference-by-name) or frozen B (versioned)? Same dichotomy at a different level.

### Coordinated-change implications

  - **Path storage schema** in L2 promoted-pipelines: each path's authoritative form is the inlined atomic sequence. Expression metadata (registration form, current abbreviations) is a separate field.
  - **Expression-metadata recomputation protocol** — on path updates, walk paths whose expression metadata references the updated path and recompute display forms. Cheap, no behavioral implications.
  - **Path-mutability decision** for v1 — mutable-with-version-history vs. immutable-with-successor-IDs. Both are value-typed; pick for audit/storage clarity.
  - **Atomic-capacity-update semantics** — at the L3 atomic level, paths reference atomics by name/ID. If atomics are mutable, paths' behavior changes silently. If atomics are versioned with explicit binding, paths reference a specific version. v1 decision pending.
  - **Equivalence detection at registration.** When user adds P_new = "P1–C–D" via UI and the inlined sequence A–B–C–D matches an existing path, the registry should detect equivalence — either reject as duplicate or link to existing.
  - **Cycle prevention** at registration — composition shorthand cannot reference the path being registered (would create infinite expansion). Trivially handled because inlining is one-shot.

### Variants and edge cases

  - **V16.a:** User composes P_new via shorthand referencing a path that has just been updated mid-session. Inlining uses the *current* version at registration time; if the user's UI was showing the old version, surfacing the change before commit is good UX.
  - **V16.b:** Two paths happen to have identical atomic sequences (e.g. one composed via "P1–C", another typed atomically as A–B–C). Equivalence detector fires; registry either rejects the second or links them.
  - **V16.c:** Dream cycle improves P1; admin wants the improvement to propagate to P2 and P3. Admin manually triggers "rebuild P2 from P1' + C" — a registry operation that registers P2' as the inlined A–B'–C. P2 and P2' coexist; admin compares via panel.
  - **V16.d:** Path stored as A–B–C; later, a new path Q = A–B is registered. Expression-metadata recomputation now recognizes A–B–C can also be displayed as "Q–C". Adds to display options.
  - **V16.e:** Atomic capacity B is updated to a new implementation with same DataState signature. Decision required: does P1 = A–B now execute with new B (silent improvement, possibly silent regression) or frozen old B (paths immune to atomic changes)? v1 TBD.

### Success criteria

  - Path content is immutable post-registration except by explicit dream-recomposition or admin action.
  - Expression-metadata recomputation completes within the same audit cycle as the triggering update.
  - Equivalent atomic sequences are detected at registration and linked or rejected.
  - Admin UI clearly distinguishes path content (frozen) from display abbreviations (recomputable).
  - Per-level dream cycles run independently; no auto-propagation surprises.

### Failure modes this catches

  - Implementation accidentally makes paths reference-typed → updates to P1 silently change P2's behavior → outcome history invalidated without anyone noticing.
  - Expression-metadata recomputation skipped → registry shows stale abbreviations → admin confusion.
  - Equivalence not detected → registry accumulates duplicate paths under different IDs.
  - Atomic-capacity update silently changes path behavior with no audit trail → versioned-binding decision was needed but not made.
  - Admin assumes auto-propagation across levels → improvements at lower levels never reach higher levels because no one schedules per-level dreams.

---

## Summary — what these stress tests collectively validate

The sixteen use cases exercise the architecture at depth across:

  - **Calibration target enforcement** (UC-1, UC-3, UC-7, UC-12): both single-sense commitment when warranted and multi-candidate output when ambiguity is genuine; calibration-aware-training as a v1 capacity.
  - **SCMS BSP turn execution** (UC-2, UC-3, UC-5, UC-11): MSUR signal partitioning, contradictory branching, state-change-driven emission, pair-wise quiescence; multi-capacity (WSD+FOL+Frame) coupling.
  - **WSD ↔ FOL coupling** (UC-2, UC-5, UC-11): mutual feedback through assumption-resolution events; extended to three-capacity coupling under UC-11.
  - **Six-phase task lifecycle** (UC-4, UC-9, UC-14): including capacity-gap surfacing, short-circuit termination, and data-gap-vs-capacity-gap classification.
  - **Phase 6 failure diagnosis** (UC-6, UC-9, UC-14, UC-15): blame attribution at path-segment granularity, cross-validation by sub-path substitution, signal routing to single ALS lane.
  - **ALS audit pipeline with dream fan-out** (UC-6, UC-7, UC-8, UC-10, UC-12, UC-13): staging, multi-variant dream-aggregation, validation gates, multi-metric admin panels, audit policies, application.
  - **Promotion-rule capacities** (UC-6, UC-12, UC-13): A–F as L3 capacities; L4 auto-selection with admin override; Pareto-frontier handling of genuine metric conflict.
  - **Paths-of-paths registry, value-typed** (UC-11, UC-15, UC-16): paths-of-paths as registration shorthand only; paths are value-typed (inlined to atomic sequences at registration); expression-metadata recomputation on updates; per-level independent dream improvement.
  - **L0 user settings** (UC-8): per-user training preferences, audit policy override.
  - **Empirical layer growth and class generalization** (UC-7, UC-10): bootstrap quality, dream-mining, per-domain tagging, hierarchy weight adaptation.
  - **External-signal oracles** (UC-6, UC-9, UC-10, UC-12): HITL via minimal UI, gold-set validation, V3 drift alarms, anti-regression gates.
  - **Capacity-gap discovery and admin queue** (UC-14): reactive capacity discovery; minimal UI for capacity-gap reports.

Combined coordinated-change implications discovered:

  - **Minimal user UI is v1 critical-path** — covers local-knowledge add (L2), local-capacity add atomic+composed (L3), pipeline add (L4), dream-priority editing, admin-panel decision/audit, capacity-gap reports. Originally cut from v1; now in scope.
  - **Path-engine-handled inter-graph traversal** (decision B, 2026-04-30) needs an L1 ADR — path executor's `hop_to_graph(metaedge_id, datastate)` semantics; not currently in L1 docs.
  - **Path storage schema** in L2 promoted-pipelines — paths stored as inlined atomic sequences (value-typed); separate expression-metadata field tracks current display abbreviations. No reference-graph or cascade re-evaluation needed under value-typed model.
  - **Path mutability decision** — mutable-with-version-history vs immutable-with-successor-IDs. Both fit the value-typed model; pick for audit/storage clarity.
  - **Atomic-capacity-update propagation** — when an L3 atomic is updated, do paths execute with new implementation (reference-by-name) or frozen version? Same dichotomy at the L3 atomic level. v1 decision pending.
  - **Per-level independent dreaming** — the flywheel runs separately at each composition level; admin/system schedules dreams across levels.
  - **Capacity contract: `unhandled_inputs` markers** — every L3 capacity (atomic and composed) must emit markers for inputs it cannot handle. Needs ADR.
  - **Per-segment provenance schema** (Phase 6) — confidence, replan-divergence, output markers per path-segment.
  - **Alternative-sub-path registry** for cross-validation — minimum 2 alternatives per v1 NLU capacity.
  - **DataState taxonomy for v1 NLU stack** — `DS_PARSED_TEXT → DS_SENSE_DISTRIBUTIONS → DS_FRAME_INSTANCES → DS_FOL_ATOMS → DS_NLU_FULL_ANNOTATION` with explicit `ShapeDescriptor`s.
  - **Calibration-aware training as a v1 L3 capacity.**
  - **Promotion-rule capacities A–F** all live in L3; L4 auto-selection logic + admin override flow is v1.
  - **Multi-metric outcome computation** always-on; promotion uses a subset chosen by the active promotion rule.
  - **Decision-precedent retrieval** (UC-13) — rationale schema for admin selections; surfacing prior rationale on similar future tradeoffs.
  - **Document-scope handling for SCMS** (multi-sentence input). UC-2 and UC-5 still expose this.
  - **Domain detection mechanism**. UC-10 still requires this.
  - **Sufficient-predicate flexibility** (ambiguity-preserved outcome). UC-3 still requires this.
  - **Per-domain `domain_tag`** propagation. UC-7 + UC-10 + UC-12 require this.
  - **V3 drift alarm thresholds and gradual-drift detection.** UC-10 + V10.c.

These are the v1-blocking design refinements the use cases reveal. Less critical refinements (admin-UI panel polish, cross-validation budget tuning, decision-precedent UX details) can iterate post-v1.

---

**End of use cases.**

Update with new UCs as architectural pressures surface. Each UC should remain a specific, testable scenario tied to identifiable architectural commitments.
