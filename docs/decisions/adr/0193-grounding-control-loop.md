---
title: Grounding control loop — irreducibility/request-atom signal + top-down descent trigger
status: Proposed
date: 2026-06-27
layer: L3/L4
amends: []
related: [0155, 0157, 0171, 0191, 0192]
---

# ADR-0193: Grounding control loop — irreducibility/request-atom signal + descent trigger

**Status:** Proposed — design for B4/B5 of the perception hand-off, grounded in
`docs/concepts/perception-principles.md` (P4, P8, P15, P17) and the validated grounding/
confidence findings (ADR-0191; PREREG AM-3…AM-8). No `mindsos_*` code ships yet.

**Date:** 2026-06-27

## Context

Two control behaviours the doctrine requires, both L4 control-flow over L3 grounding signals:

- **B4 — irreducibility → request-atom (P4).** When no composition of current atoms can
  separate/explain a phenomenon, the system must **signal that a new fundamental atom is
  needed** — not fabricate one (the ~50-gon failure). This is the perceptual twin of "extend
  the vocabulary only on solve-failure."
- **B5 — top-down descent (P8).** Cognition starts at the **highest meaningful layer** and
  **descends to lower-atom capacities only when the current layer is insufficient** — lazy,
  demand-driven, bounded (not an all-scales search).

The empirical work sharpened *when* these fire (ADR-0191; P15/P17):
- grounding confidence is **novelty-distance-relative** — it cleanly flags **far** novelty but
  is **blind to near-vocabulary novelty**;
- near-miss detection is **not** a statistical add-on — it needs a deviation-specific (finer)
  atom AND the deviation above the noise floor, i.e. **descent to finer resolution** (P17).

Existing surfaces: ADR-0157 family-specific dont-know contracts + `DS_UNHANDLED_INPUT`; the
in-flight `pipelinenotfound-to-dontknow` path-finding verdict (STATE pending_designs); the L4
six-phase orchestrator (ADR-0171); the signal-triage worker + signal-source skeletons (Phase
47); Monitor lifecycle at L4 (ADR-0155).

## Decision

1. **Three-zone grounding verdict (not a binary).** A perception step's grounding outcome is
   one of:
   - **grounded** — reconstruction within tolerance (high grounding_conf, ADR-0191) → accept;
   - **borderline** — grounding_conf elevated-but-not-clearly-OOD (the regime where residual
     magnitude under-separates, P15/P17) → **B5 descent trigger**;
   - **ungroundable (far)** — reconstruction fails outright → **B4 candidate**.
   The borderline zone is the formal "current layer insufficient" condition B5 needed.

2. **B5 descent = re-dispatch at the next-lower atom layer, on the borderline trigger.** L4
   control flow (orchestrator) responds to a borderline verdict by descending: invoke
   finer-resolution / finer-atom capacities and re-test with deviation-specific recognizers
   (P17). Descent is **bounded** — one level at a time, on demand (P8) — not an all-scales
   search. Descent terminates at the finest available atom layer.

3. **B4 request-atom signal = a distinct dont-know variant, emitted only after descent
   bottoms out.** Reuse the ADR-0157 family-dont-know machinery + the `pipelinenotfound-to-
   dontknow` verdict: when (a) the top layer is ungroundable OR (b) a borderline case is still
   unresolved at the **finest** available resolution, emit a `REQUEST_ATOM` signal (a typed
   dont-know carrying the unexplained residual + the layer reached). It routes to the L4
   signal-triage worker → human/admin (P2: only a human supplies a fundamental atom). The
   system **never fabricates** an atom (P4).

4. **Honest blind-spot contract.** Because grounding is novelty-distance-relative (P15), B4
   reliably fires only for **far** novelty; **near-vocabulary** novelty that survives descent
   (deviation below the noise floor even at finest resolution) is a **known, documented blind
   spot** — the system absorbs it into the nearest atom and may be confidently wrong. Consumers
   must not assume B4 catches every novelty.

## Consequences

- Perception control becomes: try-high → on borderline, descend (B5) → on bottom-out, request
  (B4) or abstain. This is the lazy, bounded top-down loop P8 specifies, with the descent
  trigger made formal (the borderline zone).
- B4 is additive over existing dont-know infrastructure (ADR-0157) — no new paradigm.
- The blind-spot contract makes the irreducible near-miss limit explicit rather than hidden.

## Alternatives considered

- **Confidence-threshold descent (single scalar).** Rejected — grounding is not an absolute
  scalar (P15); a single threshold mis-fires across novelty distances.
- **Eager all-scales perception.** Rejected — violates P8 laziness/bounding; expensive.
- **Fabricate-then-validate a new atom on failure.** Rejected — violates P2/P4 (only humans add
  fundamental atoms); produces the 50-gon pathology.

## Depends on
`pipelinenotfound-to-dontknow` (STATE pending_designs) for the verdict substrate; ADR-0192 for
the finer-atom layers descent targets; ADR-0191 for the grounding_conf the zones read.
