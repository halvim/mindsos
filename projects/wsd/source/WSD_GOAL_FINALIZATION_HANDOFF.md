# WSD Goal Finalization — Handoff for Goals Discussion

**Date:** 2026-04-29
**Origin:** WSD subsystem design conversation (Word Sense Disambiguation project, Henrique Alvim).
**Purpose:** Continue the goals discussion that paused in the WSD design chat. The user wants to finalize the system's goal and resolve a list of twelve pushbacks before resuming architectural design. Once finalized in this chat, conclusions paste back into the design chat.

---

## 1. The user's goal (verbatim)

> *"Create a system that eventually will do what LLMs do (understanding world knowledge, compositional patterns, and reasoning traces) through self-improving, and add what LLMs lack (calibration, audit trails, symbolic grounding, on-the-fly updates without retraining), so we can mimic the human understanding functions by operationalize (a) updates beliefs given new evidence, (b) knows what it doesn't know, (c) explicit auditable representations, (d) handles novel inputs by class-grounded generalization."*

This goal is for the WSD subsystem of MindsOS, intended as the text-understanding base of the broader system.

---

## 2. The twelve pushbacks (to discuss)

### Original architectural gaps

**1. New-lexical-item ingestion pipeline.** When unknown lemma appears: recognize new, hypothesize sense via class context, place in hierarchy, validate via observed correlations. UC-NLU-2 in cookbook; no concrete L3 capacity family in v1.

**2. Compositional semantics layer.** WSD assigns senses; understanding composes them. FOL handles logical entailment. Doesn't handle: modality, tense/aspect, quantifier scope, conditional reasoning, negation interaction, prepositional scope. Each is its own compositional concern.

**3. World knowledge beyond senses.** Plausibility priors, defaults with exceptions, common-sense reasoning. Our `concepts` graph (FrameNet) is partial.

**4. Discourse-level processing.** Coreference across sentences, topic continuity, narrative structure. `cross-word` Monitor is a v1 stub.

**5. Active learning / question generation.** When confused, ask. Phase 6 is reactive; no proactive curiosity-driven exploration.

**6. Pragmatics / intent inference.** Why did the user say this? Beyond literal meaning. Not in current scope.

**7. Grounding to non-text.** Eventually need perceptual / actional grounding. Out of v1 scope; acknowledged limitation of any text-only system.

### Pushback-derived gaps for the reformulated goal

**8. Knowledge-scale strategy.** How does the system reach useful coverage given orders-of-magnitude slower accumulation than LLM training? Options: (a) targeted domain-deep deployment, (b) ingest LLM-derived knowledge as a corpus (problematic — inherits LLM biases), (c) accept narrower coverage and rely on graceful "I don't know." No clear v1 answer.

**9. Self-improvement ceiling and oracle quality.** Without high-quality external oracle, self-training plateaus. Our gold-set + HITL + FOL-disagreement anchors help but don't scale infinitely. Need: explicit ceiling measurement (when does additional training stop helping?) and oracle-improvement strategy.

**10. Deep reasoning chain machinery.** LLMs do chain-of-thought, multi-step abductive inference, counterfactual reasoning, analogical mapping. Our architecture has: step-level provenance, FOL inference traces, Phase-6 blame attribution. Doesn't have: arbitrary-depth reasoning trees, hypothesis exploration, analogical reasoning capacity family.

**11. Belief-update latency.** ALS is audit-gated — staging → dream-aggregate → admin approval → apply. Latency: hours to days. Faster than LLM retraining (impossible without full retrain) but slower than within-conversation belief revision. Open question: do we need a faster "provisional belief" tier that updates intra-task without admin gate?

**12. LLM complementarity vs replacement.** Pure-replacement framing loses; complementarity wins. Specific complementarity strategies not designed: LLM as one of our scorer strategies (ensemble member); LLM as a fast bootstrap for new lexical items (with audit before persistent commit); LLM as a HITL surrogate for low-volume diagnostic. Each has design implications.

---

## 3. Current state of the WSD system (context)

This section gives just enough context for the goals discussion to be meaningful. The full architecture is in `WSD_ARCHITECTURE.md` (available on demand).

### 3.1 What the system is

A Word Sense Disambiguation subsystem of MindsOS. Assigns calibrated multi-candidate sense distributions to content words in text input. Coupled with a First-Order Logic (FOL) subsystem; together they iteratively refine sense distributions and FOL state via a continuous monitoring subsystem.

### 3.2 Foundational design commitments

- **Calibrated coverage, not single-sense F1 maximization.** Multi-candidate output preserved when ambiguity is genuine. Calibration metrics (ECE, Brier, NLL) are the validation target.
- **Self-improvement over time, not static evaluation.** Parameters update via dream-time aggregation, gated by admin audit.
- **Honest "I don't know"** at sense level (multi-candidate), task level (capacity-gap when no path exists), blame level (Phase 6 cross-validation can be inconclusive).
- **MindsOS layer separation** — fixed L3 capacities, learning lives in L4 via parameters in L2, L0 owns identity/sessions/audit.
- **L3 capacities never self-modify** — parameter learning happens via L4 reading/writing L2's `learned-parameters`.

### 3.3 Architecture in one paragraph

The system runs a six-phase task lifecycle (interpretation → pipeline determination → execution → goal verification → outcome consolidation → failure diagnosis on contradicted outcomes). During text-handling phases, the **Sense Confidence Monitoring Subsystem (SCMS)** runs continuously: WSD-init produces initial sense candidates, FOL-init derives logical implications, then mutual refinement via state-change-driven monitors (wsd-update, fol-update, frame-match, retrieval, cross-word) iterates in BSP turn-based execution until pair-wise quiescence. Multi-source signals are resolved by the Multi-Source Update Resolver (MSUR), which branches contradictory signals into assumption threads, scores them via a per-monitor evaluator method, and selects the winning thread. Self-improvement runs through the **Audited Learning Subsystem (ALS)**: live evidence accumulates in Local `parameter-staging`, dream-time aggregates into proposed updates, validation gates check calibration and drift, admin approves through one of three audit policies (auto-apply / batched-summary / individual-review), and approved updates write versioned snapshots to `learned-parameters`. Local-to-Global promotion is admin-triggered with separate validation. Failures trigger Phase 6 blame attribution via inverse-confidence × replan-divergence × hard-failure-isolation heuristic; blame-weighted signals route back into ALS.

### 3.4 What's in v1 (relevant to the goal discussion)

- SCMS with WSD ↔ FOL coupling.
- ALS with six signal sources (S1 self-distillation, S2 gold anchor, S3 FOL disagreement, S4 ensemble agreement, S6 task outcome, S8 replan divergence).
- Lexicon as single graph with schema layers — `theoretical` (OEWN edges) + `empirical` (corpus-mined edges from SemCor + OntoNotes + FrameNet + VerbNet + SemLink + GlossTag).
- Multi-metric per edge (Resnik selectional association + PMI + conditional probability).
- Hybrid class generalization — DOLCE mandatory + WordNet hypernym lazy + learnable per-hierarchy weights.
- Multi-candidate output mandatory.
- User training preferences in L0 server settings (per-user opt-in/opt-out, audit-policy override more-conservative-only).

### 3.5 What's explicitly cut from v1 (relevant to the goal discussion)

- Neural scorer (gradient descent / M1 mechanism) — deferred until blob storage (FOL #8) lands.
- Multi-domain ontology support (medical, legal, technical) — deferred to v3+.
- HITL UX — deferred to post-v1 (use cases UC-6 and UC-9 push back on this).
- Capacity synthesis — out of scope.
- Cross-user federated training — out of v1.

### 3.6 Pushbacks already accepted in the design chat

The user accepted three pushbacks before the reformulated goal landed:

- "Substitute for LLMs" is overreach — refined to "complement, not substitute."
- "Mimicking humans" is the wrong goal — refined to "deliberate, transparent, self-correcting reasoning over symbolic representations."
- "Real understanding" needs operational definition — operationalized via the four functions (a)-(d) in the goal statement above.

These are folded into the verbatim goal in §1.

---

## 4. Files available on demand

If the goal discussion needs deeper context:

- `WSD_ARCHITECTURE.md` — full architecture spec.
- `WSD_USE_CASES.md` — ten in-depth use cases stress-testing the architecture.
- `coordinated_change_L0_user_settings.md` through `coordinated_change_L4_intelligence_and_als.md` — layer-specific implementation handoffs.

User can upload any of these on request.

---

**End of handoff.**

Once the goal discussion finalizes, paste conclusions back into the WSD design chat to drive next architectural steps.
