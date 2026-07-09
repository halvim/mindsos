---
title: Recursive scale-relative recognizers + reuse-driven promotion
status: Proposed
date: 2026-06-27
layer: L3/L2
amends: []
related: [0150, 0156, 0159, 0184, 0191, 0192]
---

# ADR-0194: Recursive scale-relative recognizers + reuse-driven promotion

**Status:** Proposed — design for B6 of the perception hand-off, grounded in
`docs/concepts/perception-principles.md` (P3, P5, P7, P16) and the validated reuse findings
(PREREG AM-7; P16). No `mindsos_*` code ships yet.

**Date:** 2026-06-27

## Context

- **B6 — concepts as recursive, scale-relative relational templates (P7).** A concept
  recognizer is **substrate-agnostic** (`parallel ∧ perpendicular ∧ closed` over *any*
  elements), applied **recursively** up the metagraph (a structure recognized at level N is an
  element at level N+1), with **scale-coupled tolerances**. This is the missing "arrangement
  perception" the Bongard-LOGO diagnostic exposed.
- **P3 promotion** asks *when* a derived composite earns element status at the next level.
- Validated (P16, AM-7, audited): **reuse pressure** is what surfaces a shared intermediate in
  a bottleneck (reconstruction does not); decomposition is justified by reuse (MDL), not purity.
  *(Genuine unsupervised discovery remains open — `PERCEPTION_DISCOVERY_TEST_SPEC.md`.)*

Existing surfaces: capacity families + `register_capacity` bipartite topology (ADR-0156/0159);
the promotion seam ADR-0184 (two-half target-applier; design-only, no writer yet); the
`promoted-pipelines` / `learned-parameters` role-graphs (ADR-0150); confidence + per-capacity
calibration (ADR-0191).

## Decision

1. **Recognizers are a substrate-agnostic capacity family over the bipartite graph.** A
   recognizer is a capacity whose inputs are *element* DataStates (of any realm/level) and whose
   output is a *structure* DataState, defined by a **relational template** (the relation among
   inputs), **not** by what the inputs are. The same recognizer capacity applies at any level —
   recursion is just the metagraph: a structure DataState at level N is an element input at
   level N+1 (P7, P3). No special "level" machinery; levels are emergent from the
   PRODUCES/CONSUMES wiring.

2. **Tolerances are scale-coupled parameters of the recognizer, read from context (P7).** A
   recognizer evaluates its template *within tolerance*, and the tolerance widens with coarser
   resolution. Scale is an explicit input (the DataState realm/level + a resolution field), not
   a hidden constant — so "a rectangle from far enough" is a first-class, inspectable judgement,
   and it ties into the grounding/decision confidence (ADR-0191) and the borderline/descent zone
   (ADR-0193).

3. **Promotion (P3) = the introduce-atom primitive (ADR-0192 §4), endogenously triggered and
   loop-gated.** When a recognized composite is **reused** (consumed by ≥2 downstream
   capacities — the MDL/reuse criterion, validated P16), it becomes a candidate to be promoted
   to an element DataState at the next level. Promotion **reuses the existing path** — do NOT
   invent a parallel mechanism:
   - proposal: a `PromotionProposal` on `learned-parameters` (Local) when the reuse criterion
     is met;
   - apply: the ADR-0184 two-half target-applier seam → `promoted-pipelines` (Global), through
     the promotion loop (admin/loop-gated, never L3 runtime state);
   - result: a new structure DataState + its recognizer registered as a producer (= the
     introduce-atom primitive), so the promoted composite is thereafter a level-N+1 element.

4. **Two gates for a *public* promoted atom (validated P16 + nameability).** reuse (≥2
   consumers) **and** nameability (a bounded probe / human can identify it) → public derived
   atom. reuse-only → a private cached subroutine (not an atom). The genuine *unsupervised*
   variant (lossy-consumer discovery) is **not yet validated** and must not auto-promote until
   the discovery test passes (spec deferred to a torch environment).

## Consequences

- Arrangement perception is expressible without new primitives: recognizers are capacities,
  recursion is the metagraph, scale is an input. This is what the Bongard-LOGO gap needed.
- Promotion is unified with atom-addition (ADR-0192) and with the existing promotion
  infrastructure (ADR-0150/0184) — one mechanism, two trigger sources.
- Reuse is both the *decomposition* criterion and the *promotion* trigger — a single principle.

## Alternatives considered

- **A bespoke promotion mechanism for perception.** Rejected — duplicates ADR-0184/0150; the
  introduce-atom primitive (ADR-0192) already covers it.
- **Promote on confidence/frequency threshold (auto).** Rejected for v1 — risks ungrounded
  auto-promotion; reuse + nameability + loop-gating is the validated, conservative path.
- **Level as explicit machinery.** Rejected — levels are emergent from PRODUCES/CONSUMES; an
  explicit level field would duplicate the topology and break recursion's substrate-agnosticism.

## Open / tested
Genuine unsupervised discovery (vs the reuse-driven *propagation* shown) was **tested NEGATIVE
within a synthetic** (torch β-VAE, 2026-06-27; PREREG §12): a reuse-pressured bottleneck encodes
the task-sufficient statistic (≈ what the consumer labels determine) and **no more** — it
propagates required atoms but does not spontaneously discover novel ones. Consequence for §3:
the endogenous promotion trigger fires for **reused** (task-required) composites only; do **not**
expect reuse pressure to surface atoms the tasks don't require. Discovery of genuinely novel
atoms, if pursued, needs a *non-task* mechanism (unsupervised structure-learning / curiosity),
out of scope here. Recognizer *content* (specific named templates like rectangle) is subsystem,
not core (ADR-0192 §1).
