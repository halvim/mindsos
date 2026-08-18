---
title: Decision Records — Phase 7 handoff
status: Current
date: 2026-08-16
basis: main 8eca4a3; PRs #169, #170, #171
lane: demo/decision-records (worktree MindsOS-dr) — NOT a core lane
---

# Phase 7 handoff — what was decided 2026-08-16, and where to read the rest

⚠ **SUPERSEDED IN PART, 2026-08-17 — PHASE 7 IS BUILT.** §2 below (*"what
Phase 7 still has to build"*) is **stale**: items 1 and 2 had already shipped
when this was written (`a4d4b0b`, `dr_routing.py`), and item 3 shipped as beats
3–5. Its §3 (the gates) and §4 (the traps) still stand. **Current state:**
`STATE.json` `demos.decision_records`, then
`docs/DR_DEMO_WALK_2026-08-17.md` in `github.com/halvim/mindsos-decision-records`. **Gate 7's
mechanical clause is GREEN; Gate 7 is not** — see demo plan §5 Phase 7.

**This document does not restate the plan.** It records what changed on
2026-08-16, names the files that hold everything else, and lists the traps this
lane has actually fallen into. Read `DECISION_RECORDS_DEMO_PLAN.md` for the plan
itself; read `STATE.json` before anything else.

## 1. The three rulings of 2026-08-16

| # | Ruling | Recorded in |
|---|---|---|
| 1 | **Phase 7's intake is STRUCTURED** — the demo runs with **no model and no transport** | demo plan §6 open decision **9**, and Gate 7 amendment (a) |
| 2 | **The transport is NOT a Phase-7 blocker** — it is a Phase-5/6 prerequisite that arrived early | demo plan §5 Phase 7, the struck "uncosted dependency" paragraph |
| 3 | **S-3 is closed; S-2 is built** — the seam ships as `mindsos_capacity/llm` | `LLM_SEAM_MANUAL.md` §6.5, §6.7, and its header |

Ruling 1 is the one that unblocks the lane: **Phase 7 now has no undecided
input.** It is not a new choice — Gate 7 amendment (a) already specified the
structured-intake variant on 2026-08-14 — and the box is gate-bound with Phase
7's scope **frozen**, so reopening it is an owner ruling, not a lane choice.

## 2. What Phase 7 still has to build

Read demo plan **§2.5** in full before writing anything. In short, and each of
these is costed there rather than here:

1. **The exposure-routing selection criterion.** §2.5's *third undercount*:
   routing is a **selection**, and the only decision-family capacity ever built
   is ADR-0208's **comparison** criterion.
   ⚠ **Verified 2026-08-16: no decision-category capacity exists in `mindsos_*`
   at all** — `grep -rn 'category.*"decision"' mindsos_capacity/` returns
   nothing. ADR-0208's criterion is **demo code**. ⟹ **The routing criterion is
   demo code too, and belongs in `decision_records_demo/`, not in core.**
2. **The per-exposure fan-out and its reducer.** A MAP over the exposures of one
   claim, plus the reducer where *ambiguous* and *unroutable* live. §2.5 cost 2.
3. **The five synthetic claims cases**, after routing opens the flow. §2.5.

**Check any new op against Gate 4 first.** Gate 4 was restated 2026-08-14 to
something checkable: *no new capacity CATEGORY beyond
`origin_v0.DECISION_SHAPED_CATEGORIES`, and no new `FAMILY_RULES` entry.*
Verified 2026-08-16: `DECISION_SHAPED_CATEGORIES = {decision, comparator,
predicate}` (`mindsos_capacity/builtins/origin_v0.py:528`) and `FAMILY_RULES`
already carries `"decision": VERDICT` (`mindsos_capacity/family_rules.py:38`).
⟹ **A routing criterion registered under category `decision` needs neither.**
Gate 4 is satisfiable without core changes; if you find yourself wanting a new
category, stop and re-read §2.5.

## 3. The gates, and where they are written

Do not paraphrase Gate 7 from memory — it has been amended twice and both
amendments carry conditions. `DECISION_RECORDS_DEMO_PLAN.md` §5 Phase 7 is
authoritative. The parts most often misread:

- **Three cold runs on a laptop, no operator intervention, refusal on cue.**
- **Name the variant in the room** — say intake is structured and prose reading
  is the next variant. The gap between what is shown and what is claimed is the
  only thing that cannot be repaired afterwards.
- **Mauricio's two questions are inside Gate 7's acceptance**, asked *before* the
  demo is shown outside. The second — *"is that a judgement call or a rule?"* —
  is the only thing that reverses ruling 1, and it would do so by falsifying the
  **beat**, not the intake.
- **Past a green Gate 7, further polish is refused like any other work past its
  gate.** Quality is gates passed, not time spent.

## 4. Traps this lane has actually fallen into

Not hypotheticals — each has a recorded instance.

- **Citing a document that is not in the tree.** Five instances before
  2026-08-16, and PR #169 caused a sixth by making five live citations false;
  #170 fixed them. **Grep before you quote.**
- **A phantom set.** *"All six ops in `decision`"* was repeated across three
  documents and enumerated nowhere, which made Gate 4 unevaluable. It was
  restated rather than enumerated, deliberately.
- **A guard that cannot go red.** PR #169's isolation guard passed *vacuously*
  in its first version — it walked its own list, so emptying the list made it
  iterate nothing. Ask the filesystem, not your own constant.
- **A green that means nothing.** A mutation run without `--build` re-runs the
  previous image, because the compose service bakes source in. Every mutation
  run needs `--build`.
- **Inventing a taxonomy.** §2.5 forbids it for both departments and exposures;
  both are sourced (OSFI/CCIR Section III; Guidewire routing documentation). An
  invented one recreates exactly what makes the adjudication scenario weak.
- **Replay presented as live.** D9: a demo running from saved answers is a
  scripted demo and deserves to be called one.

## 5. Lane rules for this work

`BRANCHES.md` governs. The two that bite here:

- **One chat = one worktree = one branch lane.** This work is `MindsOS-dr` on
  `demo/decision-records`. Do not do it in a core worktree.
- **A demo never edits `mindsos_*`.** If Phase 7 genuinely needs a core change,
  it lands on `main` first via `feat/*`, then the demo merges `main` to receive
  it. §2 above establishes that the routing criterion does **not** need one.

## 6. Still open, and owed by the owner rather than the lane

- **The transport has no owner.** `llm-seam-s2-parse-ownership` in `STATE.json`
  stays filed for exactly this; the parsing half is closed, ownership is not.
- **Open decisions 2 and 5** in the demo plan — whether the evidence pack ships
  publicly, and the prior-art read before any novelty claim.
