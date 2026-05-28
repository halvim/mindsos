# PHASE 38 → L4 + L5 FOLLOW-UP PLAN — NEXT CHAT PROMPT

> Phase 38 SHIPPED + TAGGED 2026-05-28 (squash `edb25df`, PR #47,
> release.yml run 26585482750 SUCCESS, GitHub Release "Phase 38 —
> confirmed Latest"). Closes the L0-L3 numbered-phase rollout
> (Phase 37 retired 2026-05-19; Phase 38 is the terminus).
>
> **The next chat is NOT a Phase 39.** Per PHASE_MAP.md §1 + §5,
> L4 (Intelligence) and L5 (Mental Model) plus FOL are explicitly
> out of scope for the L0-L3 plan; a separate follow-up plan will
> cover them. This file seeds that follow-up plan's design chat.

══════════════════════════════════════════════════════════════════════
NEW CHAT — L4 + L5 follow-up plan design (post-Phase-38)
══════════════════════════════════════════════════════════════════════

You are running the L4/L5 follow-up plan design chat. Your goal is
to produce a phased rollout plan analogous to PHASE_MAP.md (L0-L3
plan) but covering: L4 (Intelligence) + L5 (Mental Model) + FOL +
the 19-item carry-forward backlog inherited from Phase 38 ship.

Project rules + memory system live in your normal context. Project
rules (skeptical reviewer, picks-per-pushback, alternatives format,
re-litigation cue, saturate before impl, no filler, alternatives
without recommended pick by default, deep-analysis-only-on-request)
apply.

══════════════════════════════════════════════════════════════════════
REQUIRED READING — read in this order, BEFORE drafting R0
══════════════════════════════════════════════════════════════════════

**Canonical closing state of L0-L3:**

1. `halvim_mindsos/confirmation_docs/PHASE_MAP.md` §1 (settled
   cross-cutting decisions; design-only-phase + docs-only-phase
   sub-shape extensions) + §5 "Phase 38 — End-to-end vertical
   slice" row (full Status + 4-clause §inline-amendment) + §6
   "Doc-to-phase map" (out-of-scope rows) + §7 "Open questions"
   (q5/q9/q10 RESOLVED annotations).
2. `halvim_mindsos/confirmation_docs/PHASE_38_DESIGN_LOG.md` — full;
   §2 picks per round (R0-R5 design-time + R6 post-design;
   5 reversals enumerated) + **§4 19-item L4/L5 follow-up plan
   carry-forward list (LOAD-BEARING — this is your starting backlog)**
   + §5 process notes.
3. `halvim_mindsos/confirmation_docs/PHASE_38_PAGE_INVENTORY.md` —
   drift discussion; 1 non-benign drift (`usage/knowledge/memories.md`)
   + 1 amendment-not-applied (`concepts/promotion-bridge.md`) +
   ~17 amendment-history-lost benign rows.
4. `halvim_mindsos/confirmation_docs/PHASE_38_CONFIRMED.md` — ship
   metadata + tester_notes; for ship-mechanics context.

**L4/L5 design context (parent tree per Model C):**

5. `Layered Intelligence/layer4_intelligence_design_notes.md` —
   L4 conceptual design baseline.
6. `Layered Intelligence/layer5_mental_model_design_notes.md` —
   L5 conceptual design baseline.
7. `Layered Intelligence/mindsos_l4_session_handoff_2026-04-25.md`
   — L4 session-orchestrator handoff doc.

**Memory entries (load via `[[name]]` from MEMORY.md):**

- `[[project-mindsos-phase-38]]` — closing-phase ship details + R6
  reversal pattern + B-38-T1 hotfix.
- `[[project-mindsos-l4-design]]` — L4 architecture sketch from a
  prior chat.
- `[[project-mindsos-architecture]]` — 5-layer overview.
- `[[reference-mindsos-layer-handoffs]]` — current paths to L0/L1/L2/L3/L4 handoff docs.
- `[[feedback-wrapper-parity-vs-docs-only-ship]]` — Phase 38 R6 lesson.

══════════════════════════════════════════════════════════════════════
LOAD-BEARING OPEN QUESTIONS (R0 PB-1 candidates)
══════════════════════════════════════════════════════════════════════

The L4/L5 plan has no single load-bearing PB-1 — multiple
foundational questions need user adjudication:

- **Scope boundary** — does the L4/L5 plan also absorb the
  19-item L0-L3 carry-forward backlog (per PHASE_38_DESIGN_LOG §4),
  or do the carry-forwards become their own bug-fix-style PRs
  against `main` independent of any new phase?
- **L4 vs L5 ordering** — L5 (Mental Model) depends on L4
  (Intelligence). Plan L4 fully before L5, interleave, or define
  L4-then-L5 as a hard sequential boundary?
- **FOL placement** — PHASE_MAP §7 q8 left FOL with "default = clean
  defer." Does the L4/L5 plan absorb FOL, ship it as a separate L6
  follow-up plan, or formally abandon?
- **Phase numbering** — continue from Phase 39 (numeric continuation),
  reset to Phase L4-00 (layer-prefixed), or use a different
  numbering scheme entirely?
- **Sentinel chain extension** — `14a → 15a → 15b → 35 → 36 → 38`
  is the L0-L3 closing chain. Extend into L4/L5 phases or start
  a new chain?
- **Cookbook gaps** — `nlu-slice.md` + `code-slice.md` were OOS'd at
  Phase 38 R0-PB-2 because nlu + code builtins weren't shipped at
  L3. Does L4 land them as part of the orchestrator demo, or do
  they wait for L3-write-flow consumers shipped under L4?
- **Model C remediation** — strict-lift was deferred to L4/L5 per
  R4-PB-A. Does L4/L5 ship the link-strip / `mkdocs-redirects` /
  ADR-shim choice as a discrete phase, or fold it into the first
  L4 ship?

══════════════════════════════════════════════════════════════════════
DESIGN PASS
══════════════════════════════════════════════════════════════════════

R0 surfaces design PBs above (and any new ones from
required-reading consumption); saturate per project rules; do NOT
begin plan-authoring (drafting L4/L5_PLAN_MAP.md or equivalent)
until user says "proceed."

Reversal lesson from Phase 38 R0-R6: probe shipped reality
explicitly at R0. Specifically:

- Probe persistence-layer state for every type the plan depends on
  (the `local_persister.py:57-58` finding that cascaded 3 reversals
  at Phase 38).
- Probe current CLI verb roster before proposing new verbs.
- Probe `mkdocs build` WARNING count before locking strict-lift criteria.
- Probe the actual shape of design-time vs execution-time picks for
  ship-shape decisions (Phase 38 R6-PB-A: tester preference can
  override design-time picks).

══════════════════════════════════════════════════════════════════════
FIRST RESPONSE EXPECTATIONS
══════════════════════════════════════════════════════════════════════

1. Confirm required-reading files consumed (terse paths list; no
   content paraphrase).
2. Open Round 0 with design PBs covering the load-bearing open
   questions above + any new ones surfaced during required-reading.
3. Stop. Wait for user re-litigation cue ("I agree with all your
   suggestions… reanalyze...") before R1.

DO NOT begin plan-authoring (no L4/L5_PLAN_MAP.md drafting) until
user says "proceed" after design saturation (typically R3-R5).

══════════════════════════════════════════════════════════════════════
before proceeding with these tasks, reanalyze the plan and list your
push backs with options.... show me your choice…. Make sure to read
all required-reading files. The load-bearing question stack is
larger than any single PB-1; surface all R0 candidates and let the
user pick which to drill on first.
══════════════════════════════════════════════════════════════════════
