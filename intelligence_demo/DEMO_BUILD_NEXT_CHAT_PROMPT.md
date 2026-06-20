# Next-Chat Prompt — Intelligence Demo BUILD (ARC, autonomous-composition proof)

> Paste as the opening message of the next chat. The **design phase is closed**; this chat moves to **build/execution**. The decisions below are a locked contract — relitigate only with the owner.

> **Progress (2026-06-15):** the ARC **Ontology Definition** foundation (Skill-Acquisition step 1) is COMPLETE in `intelligence_demo/arc1/` — dataset + viewer, lexicon (`LEXICON.md` + map), the class+relationship **ontology** with locked decisions in `arc1/ONTOLOGY.md §4`, the capacity→family map (§3), and L2/L3/L5 graphs (`arc_graphs.html`). **The next chat is the task-solving pipeline** — use `intelligence_demo/arc1/PIPELINE_NEXT_CHAT_PROMPT.md` (start there, not at step 1 below). Build-order **step 1 (persistence probe) remains an open prerequisite** for any cross-session claim. Index: `arc1/README.md`.

## Role

Critical design reviewer (MindsOS posture: skeptical by default, terse, no validation-to-be-polite, alternatives as a scannable menu, push back on vague choices, lead with the strongest concern). You are building a demo, not cheerleading it.

## Required reading (in order)

1. `intelligence_demo/INTELLIGENCE_PARADIGM_HANDOFF.md` — the thesis + **honest boundaries (§4)** + criteria (§7). Binding contract for what the demo may assert.
2. **This file** — the locked direction (supersedes the design debate and the stale spec).
3. `ROBOTICS_PITCH_HANDOFF.md §3` — zero-proof audit (learning engine unbuilt; build a minimal kernel, don't wire existing parts).
4. `MINDSOS_VS_ROS_EVALUATION.md §4` — architectural ceilings.
5. `CLAUDE.md` + `HANDOFF.md` — shipped state (Phase 50; ALS = empty skeletons; CapacityLayer in-memory-first; L0-26 episode-flush gap).
6. `confirmation_docs/ROBOT_DEMO_UI.md` + `demo_ui/maps/orchestrator_card_map.py` — the brain-card UI pattern to reuse.

**Stale, do NOT follow:** `intelligence_demo/DEMO_DESIGN_SPEC.md` — written for an abandoned dynamical-system domain (pre-ARC pivot). Superseded by this file. Rewrite it for ARC at step 4.

## The locked contract

**Audience:** AI/ML research community. Paradigm contrast is the star, not embodiment.

**Domain:** ARC-AGI. **ARC-1 = curriculum / dev corpus** (well-understood, public; capacities evolve simple→complex here). **ARC-2 = the headline goal** (where base LLMs ≈ 3% and "blind ML fails" is the accepted result; ARC-1 is saturated at the frontier so it cannot carry the headline against frontier models).

**Claim (option c, ranked):** headline (a) *reasoning where blind ML fails* + moat (b) *auditability + honest abstention*. Must prove all five criteria (handoff §7): instructed learning · verify/repair + known-unknown · structure discovery (≥ front 1) · held-out generalization (mandatory) · auditability + honest don't-know.

**The learning split (invariant-safe):**
- **Frozen seed primitives** — fixed in code, honor fixed-not-learned.
- **Autonomous composition/minting** of named composites from seeds — **the priority; the proof; the unbuilt 80%.** Composites are *specializations of seeds, never new primitives* (§4.4, local discovery only).

**Authored line = gold anchor + bring-up scaffold ONLY. Never in the load-bearing beat.** Authored composites are the *yardstick the autonomous line must rediscover without seeing them*. Autonomous success = independently mint a composite that matches/beats the authored one, on held-out tasks, with the authored version NOT in the solver's inputs. (Maps to planned ALS: gold = `signal.gold_anchor` S2; rediscovery = `signal.self_distillation` S1.)

**Autonomous mechanism (the thing to build + study):** compositional search over the frozen seeds (the `coherence_loop` strategy), scored by fit on the few-shot examples, **MDL-penalized** (the compose/split must pay for added complexity — the not-hardcoded proof), with a **structural verify/abstain gate** ("no consistent composition within budget" — NOT a confidence threshold). Option-c **neural leaf = a proposer/prior over which primitive to try next**: small, named, replaceable, **never emits the answer grid**.

**Generalization + baselines:** held-out = the ARC test grid (native) + ARC-2 as the OOD goal. Baselines = from-scratch small net + nearest-neighbor memorizer, **explicitly NOT frontier LLMs** (the ARC-1 contrast is vs from-scratch baselines; the ARC-2 contrast is the published blind-ML-fails result). Pre-register the holdout; the win is reasoning/OOD + honest refusal, never in-distribution accuracy.

**Firewall — INVERTED vs the robot demo.** Reveal the program / primitives / composition (auditability *is* the product). Keep MindsOS 5-layer / metagraph / FalkorDB / full-ALS internals black-boxed, described in paper terms. Do NOT reuse the robot demo's IP-sanitization map.

**Circularity defenses (non-negotiable):** freeze the seed primitive set + the mint mechanism *before* touching ARC-2; freeze the task-family selection rule *before* measuring solve rate; report abstention rate over the whole family (abstaining honestly on the hard ones is the moat working).

## Build order (with the gate)

0. Authored-as-gold-anchor discipline locked (above).
1. **Fresh MindsOS instance on Linux.** First probe = **persistence**: do a minted capacity + its `learned-parameters` survive a restart? (CapacityLayer is in-memory-first per Phase-42 PB-7; episodes can't flush to Falkor per L0-26 — so the "evolve across sessions" story may need a build item here.) Document the add-capacity surface (Python + `register_capacity` + Phase-50 TOML bundle) as the **Skill-Acquisition byproduct** — keep it a byproduct, not a co-equal deliverable.
2. **Download ARC-1, analyze real grids** → freeze seed primitives + the mint mechanism + the task family + structural abstention → **thin autonomous spike on a handful of real tasks. GATED:** if autonomous minting can't beat the memorizer on held-out, **scale the headline back to "auditable composition"** (weaker but honest). Learn this cheaply, before building UI/spec.
3. **Demo UI** (only if the spike clears the gate). Reuse the brain-card *layout* + the mock↔live data-source seam. Section map: **Task** (few-shot + held-out grids) · **Plan** (hypothesized program) · **Pipeline** (composed primitive sequence) · **Capabilities** (seeds + minted composites, flagged minted/reused/abstained) · **audit modal** (why this program; honest "no consistent program" on out-of-scope). Firewall inverted; **deduction/mint/generalization beats render LIVE solver state, not a baked mock** (§8).
4. **Full solver → ARC-2 generalization → baselines → rewrite `DEMO_DESIGN_SPEC.md` for ARC.**

## Known risks / open items

- **Autonomous induction is a research bet** (handoff §3, the hard 80%) — may not clear the step-2 gate. The gate exists precisely to catch that early.
- **Persistence** (in-memory CapacityLayer + L0-26) may block cross-session capacity evolution — test first (step 1).
- **Scope-coupling** with Skill Acquisition — keep the five demo criteria primary.
- **Reuse planned vocabulary, don't invent parallels:** seed/compose via `register_capacity` (PRODUCES/CONSUMES, ADR-0156); strategy = `capacity:coherence_loop:<strategy>` (L3-16, pick the simplest local search); learned leaf params → `learned-parameters` role-graph; verify/abstain via the `validate` family + structural budget; audit trace via the chain artifacts (`HintSet→MappingResult→Plan→Pipeline→PipelineRun→TaskRun`) + `phase6:attribute_blame` BlameVerdict; signals `gold_anchor`/`self_distillation`/`task_outcome`; mechanism `ema`/`bayesian_update`.

## First action for the new chat

Confirm the contract is loaded, then **start step 1**: stand up the fresh Linux instance and run the persistence probe (minted capacity + learned-parameters survive restart?). Report the result before touching ARC.
