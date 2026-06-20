# Next-Chat Prompt — Bongard Solver (design continues)

> Paste as the opening message of the next chat. This continues a **design discussion** (not a build) for the Bongard-LOGO solver — a standalone MindsOS instance. No code unless asked.

## Role / posture

Critical design reviewer (MindsOS project posture: skeptical by default, terse, no validation-to-be-polite, alternatives as a scannable menu, push back on vague choices, lead with the strongest concern). On settled trade-offs, **pick a side and move forward** — pushbacks are for blind spots and unanalyzed points, not indefinite relitigation.

## Required reading (in order)

1. `intelligence_demo/BONGARD_PLAN.md` — **the canonical record.** Scope boundary, locked decisions, perception subsystem, the mint-Skill 5-step, layer mapping, sequence, open decisions (§10), risks (§11). Start here.
2. `intelligence_demo/INTELLIGENCE_PARADIGM_HANDOFF.md` — §4 honest boundaries (esp. §4.1 small leaves, §4.2 leaf calibration), §7 criteria.
3. `intelligence_demo/NEURAL_LEAF_DISCUSSION_HANDOFF.md` — the proposer (neural-leaf): guide-not-decide; relevant to decision E.
4. `CLAUDE.md` + `HANDOFF.md` — MindsOS shipped state + layer model (L1–L5 + Server). The mint-Skill design must respect: L3-layer extensible / each capacity-function fixed; composite = new L3 node + L2 footprint, never a new primitive.

## Where we are

The plan is folded and agreed. Perception subsystem, ontology atoms (segment+vertex+closure), verifier strategy (held-out + reconstruction), and the mint-Skill shape (identify→validate→provisional/Local→human-name at Local→Global→promote/Global) are settled. Mint is a **Skill** owned in coordination with the **Skill-Acquisition chat** (not concluded) — design here is the Bongard-grounded worked example that feeds it; coordinate to avoid divergence.

## First task (do this first)

**Design decision F — the top-down half of the perception↔concept integration contract:** what the concept layer hands *down* to perception (expected atoms / priors) to re-rank and disambiguate the parse (sequence step 6). This is the nested-loop seam and **must exist before perception is sealed**, or step 6 forces a teardown. The bottom-up half is already defined (perception hands up `Shape{type,vertices,pose,confidence}` or abstain).

## Then (in plan order)

- E — perception proposer (brute/deterministic first slice; learned prior later).
- D — reconstruction mechanics + match-tolerance calibration → `learned-parameters`.
- H — backtrack/hypothesis budget → abstain thresholds.
- Persistence open-detail (in-memory CapacityLayer; "minted shape survives restart" = test, not assume).
- Curve atom family (deferred).
- Skill-Acquisition coordination contract (consume/produce interface).

## Build sequence (for reference; build is later)

1. Perception chain on a single polygon (with abstain) → 2. Shape-mint = mint milestone 1 (worked example for Skill-Acquisition) → 3. Multi-object scene parse → 4. Concept search + held-out verify → 5. Concept-mint = milestone 2 (the research-hard 20%) → 6. Top-down feedback.

## First action for the new chat

Confirm the plan is loaded, then open with the strongest concern on **decision F (top-down seam)** and propose a concrete design.
