# WSD Goal Discussion — Guidance

**Date:** 2026-04-30
**Purpose:** Frame this chat. My pushbacks on the reformulated goal and on the 12-item gap list, plus a working order.
**Companion:** `WSD_GOAL_FINALIZATION_HANDOFF.md`.

---

## 1. Working agreement

- One item at a time. ~10-message cap per item; defer if exceeded.
- Per-item deliverable: **v1 / v2 / post-v1 / out-of-scope** + one-line rationale.
- No architecture redesign here. Capture follow-up design questions; resolve them in the WSD design chat.
- I will not validate to be polite. If a framing is weak, I'll say so.

---

## 2. Additional pushbacks on the reformulated goal

The handoff lists three (A "eventually", B oracle ceiling, C symbolic grounding). Three more I want resolved before scoping items:

### D — Functions (a)–(d) are not orthogonal; treating them as four goals hides one

(a) belief update + (b) calibrated unknowns are the same Bayesian apparatus viewed from two sides. (c) audit + (d) class-grounded generalization are both consequences of having an explicit symbolic representation. The reformulation reads as four pillars; it's really two: **calibrated belief revision** and **symbolic explicitness**. Worth deciding whether to merge (clearer scoping) or keep four (more checkable).

### E — "Eventually do what LLMs do" is the wrong benchmark even after narrowing

LLM-coverage parity, even in a deployed domain, is the wrong success metric. The system's value proposition is *different*: less hallucination at known-knowns, honest unknowns, auditable derivations. If the goal frames itself against LLM coverage, every scoping decision tilts toward "match LLM" instead of "be the thing LLMs aren't." Suggest reframe: "for tasks where calibration/audit/traceability matter, outperform an LLM baseline; elsewhere, route to LLM via complementarity."

### F — Function (a) "updates beliefs given new evidence" is already in tension with ALS audit-gating

Belief-update latency (Item 11) is hours-to-days by design. Item 11 sits in tier 2. But function (a) is a *first-order* goal element. You can't simultaneously make (a) a defining function and treat its latency as a tier-2 design concern. Either (a) needs a fast provisional-belief tier baked into the goal, or function (a) needs to be re-stated as "**audited** belief update" with explicit acknowledgment that latency is the price of audit.

---

## 3. Pushbacks on the 12-item gap list

### 3.1 Tier 1 ordering is wrong

Handoff Tier 1 = {1 new-lexical-item, 2 composition, 10 deep reasoning}. My objections:

- **Item 10 (deep reasoning) should not be Tier 1.** Multi-step reasoning chains over composed propositions. Without Item 2 settled, Item 10 has nothing to chain. Doing both v1 is overscope and Item 10 cannot meaningfully precede Item 2.
- **Item 12 (LLM complementarity) belongs in Tier 1.** "Complement, not substitute" was already accepted. Every v1/v2 decision on Items 1, 3, 6, 8 implicitly answers "does an LLM fill this gap?" If complementarity strategy is tier 2, the others are decided on guesswork.
- **Item 1 and Item 8 are coupled.** New-lexical-item ingestion policy depends on knowledge-scale strategy (LLM-as-hypothesis-generator? auto-tagged corpora? curated only?). Scoping Item 1 without Item 8 is design-by-default.

**Proposed revised Tier 1:** {12 LLM complementarity, 8 knowledge-scale, 2 composition}. Item 1 follows once 8 + 12 are settled. Item 10 demoted to Tier 2 or 3.

### 3.2 Item 7 (non-text grounding) — confirm out, but reserve a hook

Hand-wavy "out of v1" is fine, but the architectural-hook question (reserved L2 role-graph slot for `modalities`) is a 5-minute decision that materially affects later cost. Treat it as a yes/no design hook decision in this chat, not deferred.

### 3.3 Item 9 (oracle ceiling) is upstream of half the others

You can't decide v1 scope for Items 1, 5, 8, 10 without an answer to "what oracle do we have, how does it grow, and where does self-training plateau?" Ceiling measurement is a goal-level commitment, not a tier-3 implementation detail. Promote.

---

## 4. Missing gaps to add to the list

### Item 13 — In-deployment validation strategy

Architecture commits to "ECE/Brier/NLL on held-out gold." That's training-time calibration, not deployment-time validation. The goal explicitly says "self-improving" — there is no defined mechanism for deciding whether self-improvement is helping or harming once held-out gold runs out. Need: in-deployment proxy metrics (e.g., FOL-disagreement rate, ensemble disagreement rate, replan divergence trend) and a stop-rule when self-improvement degrades.

### Item 14 — SCMS non-convergence / failure-mode policy

What happens when monitor-driven mutual refinement doesn't quiesce? Mentioned in use cases, not a goal-level commitment. Without it, the goal's promise of "deliberate, transparent reasoning" has no defined behavior on its hardest case. Need: timeout policy, abort policy, what gets persisted on abort, what the consumer sees.

### Item 15 — Subsystem contract to the rest of MindsOS

WSD outputs "calibrated multi-candidate sense distributions." That's a data shape. Consumers (FOL, retrieval, comprehension capacities) need a *behavioral* contract: latency bound, when WSD is allowed to refuse, what "no answer" looks like to a caller, ordering guarantees within a session. The goal cannot be finalized without this — every consumer's design depends on it.

---

## 5. Suggested working order for this chat

1. **Resolve pushbacks D, E, F.** They reshape what "the goal" even is.
2. **Confirm or refine A, B, C** with the new framing in mind.
3. **Walk revised Tier 1** in order: Item 12 → Item 8 → Item 2.
4. **Walk Item 9 + Items 13–15** (the upstream/missing items).
5. **Walk Item 1**, now that 8 + 12 are settled.
6. **Walk Tier 2** (3, 4, 11) → quick decisions.
7. **Survey Tier 3** (5, 6, 10) → most likely defer.
8. **Tier 4** (7) → confirm out + decide architectural hook.

Time-box: if a single item exceeds 10 messages, mark "needs-detailed-design" and move on.

---

## 6. Output for paste-back to design chat

Per handoff §7:

- Updated goal statement (incorporating accepted D/E/F refinements if any).
- Per-item v1 / v2 / post-v1 / out-of-scope + rationale (12 original + Items 13–15 if accepted).
- New gaps surfaced during discussion.
- Architectural commitments retained or pressured.
- Open questions for further design (with owner: design chat).

---

**End of guidance.**
