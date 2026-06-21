# Neural-Leaf — Discussion Handoff

> **Purpose:** seed a focused design *discussion* (not a build) about the **neural-leaf** — the learned proposer inside the autonomous composition mechanism of the ARC intelligence demo. This file is the complete description + the open tensions to work through with the owner.
> **Mode:** discussion/design only. No code unless the owner asks.
> **Date:** 2026-06-15.

## Role / posture

Critical design reviewer (MindsOS posture: skeptical by default, terse, no validation-to-be-polite, alternatives as a scannable menu, push back on vague choices, lead with the strongest concern).

## Where this sits (context)

The `intelligence_demo` is an AI-community proof-of-path for the MindsOS learning paradigm. Locked direction (full contract: `intelligence_demo/DEMO_BUILD_NEXT_CHAT_PROMPT.md`):
- **Domain = ARC-AGI** (ARC-1 = curriculum/dev corpus; ARC-2 = headline goal).
- **Claim = option c**: headline *reasoning where blind ML fails* + moat *auditability + honest abstention*.
- **Learning split**: frozen seed primitives (fixed in code) + **autonomous composition/minting** of named composites (the priority, the unbuilt 80%).
- **Autonomous mechanism**: compositional search over the seeds (the `coherence_loop` strategy), scored by fit on the few-shot examples, **MDL-penalized**, with a **structural verify/abstain gate**.
- ARC ontology/lexicon foundation is already built in `intelligence_demo/arc1/` (see `arc1/README.md`, `arc1/ONTOLOGY.md`); the task-solving pipeline is the active build thread (`arc1/PIPELINE_NEXT_CHAT_PROMPT.md`). **The neural-leaf is the proposer that makes that pipeline's search tractable** — this discussion feeds it.

## The neural-leaf — complete description

### What it is
Uninformed search over ARC's primitive space explodes combinatorially — which is why strong ARC entries use neural/LLM guidance. The **neural-leaf is a learned *proposer*: given the task (few-shot input/output pairs + the current partial search state), it outputs a prior/ranking over which primitive to try next.** It steers the search toward promising compositions first. **It guides; it does not decide.**

### Why it exists
Two forces in tension: search must be tractable, and the result must be auditable. A net that emits the answer makes search trivial but destroys the moat. The neural-leaf confines the black box to *guidance over ordering*, not *the decision*. This is handoff §4.1 made literal — "the black boxes don't disappear, they become small, contained, named, replaceable." The neural-leaf **is** one of those contained leaves.

### What it is NOT (hard lines)
- Never emits the answer grid.
- Never emits a complete program (that would make it the synthesizer, not a proposer).
- Not load-bearing for *correctness*. The **verify gate** (does the composed program reproduce the example outputs?) is the sole arbiter of acceptance. The neural-leaf changes only the *order/speed* of search.
- Falsifiable test of "only a proposer": **ablating it degrades efficiency, not correctness.** If removing it changes *which* answers are accepted, it was secretly deciding — and the moat is gone.

### How it fits the invariants
Fixed-not-learned governs the *capacity* (the search strategy + primitives — both fixed in code). The neural-leaf is a learned *heuristic/parameter* feeding that fixed strategy → no invariant violation. It lives as learned state (naturally `learned-parameters`, or a small named leaf capacity), and it's a *small contained leaf* per §4.1.

### The auditability relationship (the key property)
The audit trail is over the **symbolic program** — the named primitive composition the verify gate accepted. The neural-leaf's only footprint is "it suggested trying primitive X early." So: **a black-box guide producing a white-box result.** The proposer's internals can be opaque; the inspected output (the program) is fully legible. That is the whole trick.

### The honesty caveat
The proposer being opaque is safe *only as long as the verify gate is sound*. A weak gate (accepts a program that fits the few visible examples but is wrong) lets a biased proposer systematically steer toward plausible-but-wrong programs — the §4.2 calibration risk, confined to the leaf. **The neural-leaf's safety is entirely parasitic on the verify gate's strength.**

### Concrete ARC instantiation (a spectrum)
Same role, very different sizes:
- a learned frequency/co-occurrence prior over primitive usage (barely "neural"),
- a small trained net scoring primitives from grid/object features,
- an LLM proposing candidate steps.

All are "the proposer." Simplest honest spike version = the frequency prior. The point is it's **replaceable** — swap the proposer without touching the rest.

## Open tensions to discuss (ordered by how much they bite)

1. **A capable proposer eats the headline.** The central tension. The more powerful the leaf (especially an LLM), the more a skeptic says *"the LLM is doing the reasoning — you just wrapped it."* Tractability and the "we reason where blind ML fails" claim pull in opposite directions. Where on the spectrum do we sit, and how do we prove the *composition*, not the proposer, carries the result?
2. **Do we even need it for the spike?** For simple ARC-1 tasks with a small seed set, uninformed or cheaply-heuristic search may suffice. Prior: **start without a neural-leaf; add it only when search demonstrably explodes** — keeps the black box minimal and the early proof clean.
3. **"Small contained leaf" vs capability.** An LLM proposer isn't *small*. Which honesty sentence (§4.1 "small leaves") do we get to keep at each point on the spectrum?
4. **Training signal + bootstrapping.** It learns from `signal.self_distillation` (own solved tasks) + `signal.gold_anchor` (authored composites). Cold start: early on there are no solved tasks — how does the proposer get off the ground without leaking the gold anchor into the load-bearing beat?

## Reviewer's prior (to argue against)

The proposer should be the **last** thing added and the **smallest** thing that makes search tractable — every increment of its capability is an increment of headline given away. Ablation (efficiency drops, correctness holds) is the standing proof that it's a guide, not the decider.

## Required reading (in order)

1. **This file.**
2. `intelligence_demo/INTELLIGENCE_PARADIGM_HANDOFF.md` — §4 honest boundaries (esp. §4.1 small leaves, §4.2 leaf calibration), §7 criteria.
3. `intelligence_demo/DEMO_BUILD_NEXT_CHAT_PROMPT.md` — the locked contract (autonomous mechanism, verify/abstain gate, baselines, firewall).
4. `intelligence_demo/arc1/ONTOLOGY.md` + `arc1/README.md` — the ARC primitive/family grounding the proposer ranks over.
5. (background) `ROBOTICS_PITCH_HANDOFF.md §3` — zero-proof audit; the learning engine is unbuilt.

## Outcome of the discussion (what to produce)
A settled position on: (a) where on the proposer spectrum the demo commits, (b) whether the spike runs with no proposer first, (c) the ablation protocol that proves "guide not decider", (d) the cold-start/training-signal plan. Capture it back into `DEMO_BUILD_NEXT_CHAT_PROMPT.md` (autonomous-mechanism section) when settled.
