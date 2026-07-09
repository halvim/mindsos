---
title: All decision-point policies composed from L3 capacities as meta-pipelines
status: Deferred
date: 2026-04-22
layer: L4
aliases: [L4-policy]
---

# ADR-0102: Policy authorship - all L4 decisions via meta-pipelines

**Status:** Deferred — acknowledged with a known path forward but not implemented in v1; revisit post-v1. Reconciled in the 2026-07 doc-vs-code audit.

**Date:** 2026-04-22

## Context

L4's orchestrator needs to make decisions at many points: which planner to use, whether to replan, how to triage signals, how to compose attention scores. The question is whether these policies are hard-coded in L4 or composed from L3 capacities.

## Decision

**All decision-point policies are composed from L3 capacities, run by L4 runtime.** Each meta-pipeline ships as a default, carries its own `promoted-pipelines` record (so it's improvable via the same learning loop that improves object-level pipelines), and is swappable — L4 reads the best-confidence meta-pipeline for the current task shape at each decision point.

Meta-pipelines compose capacities from `capacity:path_finding`, `capacity:decomposition`, `capacity:scoring`, `capacity:signalling`.

## Consequences

**Good:**
- All decision-making is learnable; meta-layer policies improve over time.
- Hard-coded L4 Python doesn't freeze the meta-layer.
- Policies are inspectable and auditable.

**Cost:**
- Requires designing six core meta-pipelines (planning, signal-triage, replan-check, confidence-composition, promotion-proposer, attention-score).
- Adds bootstrapping complexity; system must ship sensible defaults.

## Alternatives considered

1. **Hard-coded L4 policies** — rejected (freezes meta-layer at system design time).
2. **Config files** — rejected (not learnable; can't improve from observation).

## Related decisions

Locked decision #3 in the L4 handoff.
