---
title: Decision Records — what the demo does, and what it cannot do
status: Current
date: 2026-08-17
basis: demo/decision-records `cfe1bd8` (tag `dr-beat-confirmed`), read off the tree
lane: the answer to "what will we have at the end of the plan" — kept current on every demo ship
---

# What this demo does, and what it does not

The demonstration plan has phases and gates. It has never stated what the
demo **is able to do**, so every answer to that question has been reassembled
from prose by whoever was asked. This file is that statement, derived by
recorded commands rather than recalled, and it is **updated in the same ship
as any change to either list**.

**Read the "cannot" list first.** RULES §11: a list of only successes is a
pitch.

## How this file was derived

Not from memory, and not from the plan:

```
git tag --list '*-confirmed' | while read t; do git diff --quiet "$t" HEAD -- 'mindsos_*' && echo "$t"; done
git ls-tree --name-only origin/demo/decision-records:decision_records_demo/
grep -c '^def test_' decision_records_demo/test_*.py
```

Pinned core at the time of writing: **`dr-partial-record-confirmed`**, verified
by the first command against the tree, matching `STATE.demos` and the demo
README. Guard total **56** — render 29, screen 9, run 5, routing 4, no-model 3,
beat 3, dump 3 — from the third.

---

## 1. What it does today

Every line below is a thing the code performs, not a thing the design permits.

- **Routes the exposures of one claim to two desks.** One document, several
  decisions: one Record per exposure plus a claim-level assignment line, on the
  Guidewire-sourced model (plan §2.5). Rendered from a real FalkorDB round
  trip, never from live objects.
- **Refuses one exposure in-band, beside siblings that routed.** The missing
  item is named in the reader's own stored words, on the same page as three
  answers. The refusal renders **at its position** among the exposures, not in
  a footnote.
- **Refuses a claim on a missing document, and names which one.**
- **Answers a dated policy question against two editions**, naming the edition
  and the window it was in force. Two cases differing only in the as-of date
  select different limits (G5).
- **Rebuilds any of those Records from the store alone**, given only a
  `capacity_root_ref`, after the application is killed — no live knowledge
  layer in the code path at all.
- **Proves no model is in the decision path**, checked live rather than
  asserted: the pinned core carries no model seam, no demo module imports one,
  and no case produces a value a model read.
- **Runs cold three times with no operator intervention**, each run in its own
  container and its own subprocess, store asserted empty before any case
  executes, exit code = the gate's verdict.
- **Stops honestly on five shapes the room never sees** — no-route, outage,
  boundary, refusal, partial. These are gate evidence: they prove the renderer
  raises rather than fills.

## 2. What it cannot do today

- **It cannot read prose.** Intake is a structured record (open decision 9); a
  human did the reading. The honest sentence in the room is *"intake here is
  structured; reading prose is the next variant, and its seam shipped
  2026-08-16."*
- **It cannot adjudicate anything.** No clean approval, no clean denial, no
  policy exception. §2.5 specifies all three and none exists. Beat 4 is a page
  titled *Decision Record* containing two lookups and no decision.
- **It cannot say WHY on a decision it answered.** §2.3's form — question →
  answer → therefore — is achieved **only when the system refuses**. Successful
  decisions render item → verdict. The refusals are better documented than the
  answers.
- **It cannot take a case or a policy chosen at the table.** Every input is a
  Python constant in a demo module. Nothing in the demo can be varied without
  editing source.
- **It cannot state a decided date from stored evidence.** The date lives on the
  Episode, which is not store-resident (ADR-0042). The page states that absence
  rather than omitting the line — that is the design, and it is the honest half
  of this entry.
- **It cannot say what is missing on a stop-and-ask.** `NeedsInput.missing` is a
  DataState IRI; the renderer suppresses IRI-valued stop details (G6, correctly);
  and no manifest field maps an arbitrary IRI to its registered description. This
  is why the shipped beat 3 is the **in-band** refusal — the same mechanism as
  beat 2 — and says so in its own docstring. Filed as
  `dr-needs-input-missing-item-translation`.
- **It cannot plan.** All thirteen L4 catalog capacities are placeholders
  (`DECISION_RECORDS_V0_PLAN.md` §6), so `run_lifecycle` yields one milestone and
  one pipeline. **Nothing said in a room about composition, planning or "working
  out what to do" is supported by what runs.** This is the entry most likely to
  be over-claimed.
- **It cannot produce a single number that is not ours.** No dataset in scope
  supplies routing ground truth — plan §1 records this as verified, not assumed —
  so routing is **shown, not measured**. Every case is one we wrote. That is what
  Phases 1–3 are for, and until they run, *"confidently wrong: zero"* is
  unfalsifiable outside our own cases.
- **It has never been compared against a live model.** Screen B has not been run
  at any beat; the script's prereqs 3 and 4 (paste-identical inputs, ≥5
  rehearsals per beat) are untouched, and they are a third of what the room
  experiences.

## 3. What is being built, and what was refused

v1 scope, frozen 2026-08-17 (`DECISION_RECORDS_DEMO_PLAN.md` §0.3):

| Ship | Closes | Entry above it removes |
|---|---|---|
| A | walk gap 1 | *cannot say WHY on a decision it answered* — replaced by: the page names **the fact that DECIDED**, from a stored field the deciding capacity writes |
| B | walk gaps 2, 3, 5 | *cannot adjudicate anything* |
| C | owner finding, 2026-08-17 | *cannot take a case or a policy chosen at the table* |

**Refused:** walk gap 6, the room-facing text pass — past the gate, with ONE
promotion into ship B on a §11 ground (*"1 cannot be assigned yet — see the
exposure above"* is ambiguous over four exposures, so the routing reducer names
the pending one). Currency formatting stays refused: an invented `$` is a
fact-channel violation, and the number's unit becomes stored content in v2 rather
than chrome. Two other strings ride along only where a ship already edits that line.

**Owner-owned and not code, and they are the critical path:** the RULES §12.5
full-matrix re-run before the demo is shown outside, and five rehearsals per beat on
both screens. Neither is closed by building anything.

**Not addressed by any ship, and staying on the "cannot" list:** prose intake,
the decided date, the stop-and-ask translation, planning, and any number that is
not ours.

## 4. The rule this file exists to enforce

**A capability is what the code performs on a command someone else can run**
(RULES §11). Anything on the first list that stops being true is a red gate, not
a documentation update — and anything moved from the second list to the first in
the same breath as the ship that moved it is the only way this file stays worth
reading.
