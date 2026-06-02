---
title: Coherence dream intent - GAN-like generator vs critic for training pipeline stability
status: Proposed
date: 2026-04-22
layer: L4
aliases: [L4-coherence]
---

# ADR-0110: Coherence dream intent - GAN-analogous training

**Status:** Proposed

**Date:** 2026-04-22

## Context

Dreaming (idle-compute exploration) has three intents: maintenance, exploration, and retry (settled). The question is whether there's a fourth intent that specifically targets learning pipeline stability.

## Decision

Yes. **Coherence dream intent** (fourth alongside maintenance, exploration, retry). GAN-analogous: generator (planner meta-pipeline) vs critic (replan-check meta-pipeline); divergence measured on replayed memories is training signal. Variants of the generator are proposed and ranked by divergence; winners get `promoted-pipelines` records.

This converts replan stability from a retrospective metric to a forward-training signal: the system learns to produce plans that remain valid under mid-run information updates.

Companion: critic-honesty loop. Periodically validate the critic against known-good memories so false disagreement doesn't drift training (generator chases ghosts if critic is noisy).

## Consequences

**Good:**
- Stability is earned, not just observed.
- System improves plan quality over time via self-play.
- Coherence dreams surface novel pipelines that might otherwise be missed.

**Cost:**
- Requires maintaining two separate meta-pipelines (generator/critic) with aligned semantics.
- Adds computational overhead during dream phases.

## Alternatives considered

1. **No dedicated stability training** — rejected (stability is too important to learn passively).
2. **Hard-coded stability metric** — rejected (not learnable; frozen at design time).

## Related decisions

Locked decision #23, #24 in the L4 handoff.
