---
title: Decision Records — the first walk of the demo
status: Current
date: 2026-08-17
basis: demo/decision-records `cfe1bd8` (tag `dr-beat-confirmed`), run on the Linux box
lane: input to v1 scoping and to the critic round — NOT a defect list
---

# The first walk, 2026-08-17

The owner ran `dr_demo_beat.py` beats 1–6 live and read each page cold. **This
is the first time anyone performed the demo.** Everything here was found by
LOOKING at pages. **56 guards were green throughout**, Gate 7's mechanical
clause had already passed, and none of it caught any of this — which is the
point of the document.

Read with `DR_DEMO_SCRIPT.md` (the beats) and
`decision_records_demo/README.md` on `demo/decision-records` (which case drives
which beat).

## 1. The one finding

**The pages show WHAT, not WHY, and the form the plan specifies appears only
when the system fails.**

Demo plan §2.3 states the form is *question → answer → therefore*. Every
refusal renders exactly that. Every successful decision renders
`item → verdict` — no question, no reason. So **the refusals are better
documented than the answers**, which is backwards for a product whose claim 1
is *the reasoning IS the record*.

Beat 2's page is the proof: three routed exposures carry no question, and the
one that refused carries *"Q. What injury severity was assessed for this
exposure? — Nothing. the intake record for this exposure does not state an
injury severity assessment."*

**The reasoning is already in the graph.** The routing readers store their
questions (*"Which coverage was this exposure filed under?"*, *"What injury
severity was assessed?"*) and their answers with origins. `dr_render` consults
origin records only when refusing — and, since the beat-4 ship, for the policy
source line. Rendering the reads above each verdict **invents nothing** and is
inside the existing Q-form source rule: a Q line is *earned* by a stored
question, and these are stored.

Cost to weigh when scoping: a four-exposure page grows by roughly eight lines,
and long pages carry their own room risk.

## 2. The gaps, ranked by what they cost in a room

1. **No reasoning on answered decisions** — beats 1, 2 and 4. One renderer
   change closes three beats. Highest value.
2. **No adjudication content exists.** §2.5's clean approval, clean denial and
   policy-exception cases were never built. The demo is routing + policy
   lookups + refusals. It shows worst at **beat 4**, where a page titled
   *Decision Record* contains no decision: the room sees two lookups, because a
   versioned limit only matters when something is decided against it. The
   labels also read *"dwelling limit as of"* where the script says *submission*
   vs *assessment*, so even the framing is absent from the page.
3. **Beat 3 has no consequence.** It names the missing document — genuinely
   good — but never says the claim cannot be settled. `dr_settlement` has no
   reducer, so nothing states the claim-level result, and the beat lands as a
   shorter, weaker repeat of beat 2. *(This risk was named before beat 3 was
   built; the walk confirmed it.)* Either give it a claim-level *therefore*, or
   fold it into beat 2.
4. **Beat 5 puts test output on the buyer's screen.** `PASS
   test_no_demo_module_imports_the_model_seam` uses the exact vocabulary G6
   bans from the page, and it substitutes evidence for an action. Fix is in the
   script, not the code: the action lives on Screen B (see `DR_DEMO_SCRIPT.md`
   beat 5, re-cut).
5. **Beat 6 rebuilds the WEAKEST page.** `closer_ref` prefers `settlement`
   (three lines, no decision) over `routing` (four exposures, three verdicts, a
   refusal, a therefore). *"Every line traces"* needs lines. One-line
   preference change plus its guard assertion.
6. **Room-facing text defects**, all small, all real:
   - `2 exposure(s)` — the `(s)` reads as software (`dr_routing._assign`).
   - `350000` where a claims manager expects `$350,000`. Note the policy's own
     stored text already reads *"The dwelling coverage limit is 350,000."* —
     the page shows the machine's number, not the policy's words.
   - `one exposure, as filed` repeated once per exposure — noise at four.
   - DataState descriptions used as labels: *"the date the coverage question is
     asked about"*.
   - *"1 cannot be assigned yet - see the exposure above"* — with four
     exposures above, name D. Laurent.
   - A fixture parenthetical inside a claim label: *"claim CLM-3007 (one more
     exposure filed)"*. No real claim carries that.
   - The source line repeats the phrase already on the line above it.

**Gaps 1–3 stand between this and a v1. Gaps 4–6 are an afternoon.**

## 3. Observed, and not a defect

Beat 6's first line is *"Decided date: not available from stored evidence"* —
the honest stated absence the script narrates as the product (*it won't claim a
date it can't prove*). Note the trade rather than fixing it: an auditor's first
question is often *when*, and the answer is an absence. It is store-resident
truth; the date lives on the Episode, which is not persisted (ADR-0042).

## 4. What the walk did NOT cover

- **Screen B.** No comparison against a live frontier LLM was run at any beat.
  The script's prereqs 3 and 4 (paste-identical inputs, ≥5 rehearsals per beat)
  remain untouched, and they are a third of what the room experiences.
- **Beats 0 and 7.** Spoken, never rehearsed.
- **Mauricio's two questions**, which sit inside Gate 7's acceptance and are
  asked before the demo is shown outside. The second can still falsify the
  BEAT rather than the intake (demo plan open decision 9), which would make
  parts of §2 moot.
