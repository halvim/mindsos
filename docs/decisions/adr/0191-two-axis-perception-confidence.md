---
title: Two-axis perception confidence (grounding + decision) + per-capacity calibration
status: Proposed
date: 2026-06-27
layer: L3/L4
amends: []
related: [0155, 0157, 0159]
---

# ADR-0191: Two-axis perception confidence (grounding + decision) + per-capacity calibration

**Status:** Proposed — design validated on synthetic substrates only (see Evidence). Flip to
Accepted when a real probabilistic/learned capacity consumes the contract (consumer
discipline, RULES §8). No `mindsos_*` code ships on this ADR yet.

**Date:** 2026-06-27

## Context

The perception-learning work (`docs/_workbench/PERCEPTION_LEARNING_NOTES.md`, candidate
principles P12–P16; the parent doctrine is `docs/concepts/perception-principles.md` P1–P11)
introduces *probabilistic* capacities — leaves whose output is a learned/ambiguous estimate
of a known atom (P9, P12). Such a capacity must say *how much to trust* its output, and the
existing confidence machinery does not cover it cleanly:

- Settled constraint (HANDOFF §3.1): confidence is **pipeline-level** (on `promoted-pipelines`
  keyed by `(pipeline, task_type)`) and **per-run on `TaskRun`**; there is **no per-capacity
  confidence**, because confidence-as-capacity-*state* would violate L3 fixed-not-learned.
- But a probabilistic capacity genuinely produces uncertainty *per invocation*. That is
  output data, not capacity state — a distinction this ADR makes explicit.

A pre-registered, independently-audited synthetic study (PREREG.md §8–9, amendments AM-1…AM-6)
established two facts the contract must encode:

1. **Two independent uncertainty axes** (P14). Reconstruction fidelity measures *grounding*
   ("is this output explainable by known atoms"), **not** *decision* ("which atom"). Under
   irreducible ambiguity a round-trip reconstructs well while the answer is uncertain — so a
   single confidence number is dishonest in the well-grounded-but-ambiguous quadrant.
2. **The decision axis is not comparable across capacities without calibration.** Raw margins
   from capacities of different complexity carry different unit scales; a *pooled* raw ranking
   under-credited a real signal (AUROC 0.78), while **per-capacity Platt calibration** lifted
   it to 0.88 (1D) / 0.91 (2D), permutation-controlled to be genuine margin signal
   (+0.27–0.33 over base rate). Risk–coverage is the honest operationalization.

## Decision

1. **A probabilistic capacity emits two per-invocation confidence values with its output:**
   - **grounding_conf** — reconstruction fidelity to the fundamental floor (analysis-by-
     synthesis; P13/P15). "Is the output a valid composition of known atoms?"
   - **decision_conf** — peakedness/margin over the valid alternatives (requires a
     distributional or margin-producing proposer; P14). "Is it the right one?"
   These are **per-invocation OUTPUT**, carried on the run artifact (`TaskRun`/`PipelineRun`),
   **not** learned state on the capacity — preserving "no per-capacity confidence state" and
   L3 fixed-not-learned.

2. **Honest-dont-know defaults.** A capacity with no critic (a bare `->`, ADR-aligned with
   the `<->` grounding-pair notation in NOTES P13) reports `grounding_conf = unknown` (capped),
   never fabricated. A non-distributional proposer reports `decision_conf = unknown`, never a
   fabricated high value.

3. **The decision axis MUST be per-capacity calibrated before any cross-capacity use**
   (arbitration, selective prediction, tier ordering). Raw cross-capacity margin comparison is
   **prohibited** (falsified). The calibration mapping is **not** L3 runtime state; it is
   either (a) fit offline and **frozen at registration** (like the leaf model itself, P9 —
   training is bootstrap, runtime is inference), or (b) carried in the L2 `learned-parameters`
   role-graph and updated **only via the promotion loop**. Selective-prediction quality is
   reported via **risk–coverage**, not a single pooled AUROC.

4. **Grounding confidence is novelty-distance-relative, not absolute** (validated identically
   on two substrates). Reconstruction reliably flags *far* novelty and is **blind to
   near-vocabulary novelty** (a near-miss reconstructs almost as well as the true atom). Hence
   grounding_conf must be interpreted/characterized as a function of novelty distance, and the
   irreducibility/request-atom signal (B4) is contractually understood to fire only for far
   novelty; near-vocabulary mis-grounding is a **known blind spot** consumers must not assume
   away. (Formal re-specification of the P15 grounding *measurement* is tracked separately;
   this ADR only records the caveat the confidence contract depends on.)

## Consequences

- L4 arbitration / selective prediction consumes **calibrated** decision_conf only; abstain
  on low decision_conf ("refuse rather than guess").
- A new capacity that wants to participate in cross-capacity arbitration owes a calibration
  artifact (offline or promotion-loop), or it is treated as `decision_conf = unknown`.
- Grounding gates (B1/B4) must be specified against a novelty-distance characterization, not a
  single threshold — near-vocabulary novelty needs a different mechanism than reconstruction.

## Alternatives considered

- **Single confidence scalar.** Rejected — dishonest in the grounded-but-ambiguous quadrant
  (P14).
- **Raw (uncalibrated) cross-capacity margin comparison.** Rejected — empirically falsified
  (pooled AUROC 0.78; incommensurable margin units).
- **Confidence as learned per-capacity state.** Rejected — violates L3 fixed-not-learned and
  the settled no-per-capacity-confidence rule; calibration is offline/promotion-loop instead.

## Evidence

Synthetic, pre-registered, independently audited (4 audit rounds; 2 false passes caught):
1D piecewise signals + 2D filled shapes. P14 decision: PASS on both substrates
(calibrated AUROC 0.88/0.91, risk–coverage error 0.15→0.01, margin permutation-controlled).
P15 grounding: method real but novelty-distance-relative on both substrates (AUROC 0.99 far →
0.72 near). Full record: `docs/_workbench/PERCEPTION_LEARNING_PREREG.md` §8–9 + AM-1…AM-6;
`PERCEPTION_LEARNING_NOTES.md` P13/P14/P15 empirical notes.
