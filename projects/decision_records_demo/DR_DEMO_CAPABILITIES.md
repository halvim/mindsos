---
title: Decision Records — what the demo does, and what it cannot do
status: Current
date: 2026-08-17
basis: demo/decision-records `df57033` (tag `dr-ship-b-confirmed`), read off the tree
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
README — **unchanged by ships A and B**. Guard total **92** — render 37,
routing 16, assessment 13, screen 10, run 5, no-model 3, beat 5, dump 3 —
from the third.

⚠ **This block said `cfe1bd8` / 56 for the length of a ship while §1 below
already described ship A**, which is this file failing its own §4 rule. The
derivation commands are the fix; running them is what this line now is.

---

## 1. What it does today

Every line below is a thing the code performs, not a thing the design permits.

- **Routes the exposures of one claim to two desks.** One document, several
  decisions: one Record per exposure plus a claim-level assignment line, on the
  Guidewire-sourced model (plan §2.5). Rendered from a real FalkorDB round
  trip, never from live objects.
- **Names the fact that DECIDED each verdict** — the deciding capacity records
  which of its inputs determined the outcome, and the page prints that stored
  question with that stored answer. Not every fact read: the one that moved the
  answer. *(Ship A, `dr-deciding-fact-confirmed`, 2026-08-17. Beats 1 and 2
  only — beat 4 has no decision yet.)*
- **Refuses one exposure in-band, beside siblings that routed.** The missing
  item is named in the reader's own stored words, on the same page as three
  answers. The refusal renders **at its position** among the exposures, not in
  a footnote, and the claim-level line **NAMES the exposure it cannot assign**
  rather than counting it. *(Ship B, `dr-ship-b-confirmed`.)*
- **Decides a claimed amount against the limit in force on a date**, and names
  the edition and window that limit came from. The same claim assessed as of
  two dates pays two different amounts. **The room does the arithmetic before
  the page renders** — 400,000 claimed, 350,000 payable under the 2023 edition
  and 375,000 under the 2024 one. *(Ship B — beat 4, which until then was a
  page titled Decision Record containing two lookups and no decision.)*
- **Names the decision it could NOT make.** A refusing leaf carries the
  capacity's own words for what could not be done — *"settling the claim on
  what was filed → cannot be settled"* — never the renderer's. *(Ship B.)*
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
- ⚠ **When it does read prose, it cannot establish that a read VALUE follows
  from its quote.** Added 2026-08-17 from RUNS, not from reading:
  `comprehension_v0.locate_quote` binds **quote → source** only. Nothing binds
  **value → quote**, nothing binds the quote to the field or the question, and
  `expected_basis` is recorded (`:345`) and compared nowhere. Critic probe
  `probe_reader_weak_model.py`: value `2` under the true quote *"off work for
  at least six weeks"* is **admitted with `quote_verified: True`**; value `6`
  under the quote *"Dear team,"* is **admitted**. ⟹ the mechanism catches
  **fabrication**, not **misreading**. **The sentence that must never be said
  again** — and it was in the plan until this ship — is *"a cheap extractor
  degrades to a refusal rather than a wrong answer"*. Filed as
  `dr-value-span-binding`; the ruling is plan §0.5 item 2.
- ⚠ **It cannot extract a COLLECTION from a document with per-member
  verification.** `build_reader` is one reader per DataState IRI with one quote
  per value, and `coerce_to_shape` returns `opaque`, `list` and `record` shapes
  untouched (`:257`) — a `record` shape's declared fields are never compared to
  the members, and `extraction_schema` reaches the transport (`:411`) unchecked
  against the reply. Critic probe `probe_collection_reader.py`: a reply carrying
  an invented claimant *"K. Invented"* and an invented peril *"flood damage"*,
  under the true quote *"Two of our people"*, is **admitted with
  `quote_verified: True`**. ⟹ **the step that decides which exposures exist has
  no check, and every checked step is downstream of it.** Filed as
  `dr-collection-extraction-per-member`; the ruling is plan §0.5 item 3.
- **It adjudicates ONE thing: an amount against a dated limit.** Narrowed
  from *"it cannot adjudicate anything"* by ship B rather than removed, because
  §2.5 specifies **clean approval, clean denial and policy exception** and only
  the amount comparison exists. What the demo can say is *"this claim exceeds
  the limit in force, by this much, under this edition"*; it cannot approve, it
  cannot deny, and it has no exception path. Do not describe it as adjudication
  in general.
- **It can only REFUSE for a reason a reader recorded.** A refusal carries no
  prose of its own (ADR-0209 D1) and the renderer raises on a refusing value
  with no stored words, so *"the field is absent"* and *"the value is not a
  number"* refuse honestly — while a well-formed NONSENSE value (a negative
  claim, a date in 1850) has no refusal available to it and is decided on.
  **This is the boundary any live-editing console inherits**, and it is ship
  C's constraint before it is anyone else's.
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
| A ✅ `dr-deciding-fact-confirmed` | walk gap 1 | *cannot say WHY on a decision it answered* — replaced by: the page names **the fact that DECIDED**, from a stored field the deciding capacity writes |
| B ✅ `dr-ship-b-confirmed` | walk gaps 2, 3, 5 + the §11 promotion out of 6 | *cannot adjudicate anything* — **narrowed, not removed**: one comparison against a dated limit exists; §2.5's three cases do not |
| C — not started | owner finding, 2026-08-17 | *cannot take a case or a policy chosen at the table* — **AMOUNTS ONLY** when it lands (owner ruling 2026-08-17): the edition's stated limit and the claimed amount. **Dates stay off the editable surface** until `decision-records-as-of-date-validity` closes, because a malformed date is reported as our outage rather than as their input |

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

⚠ **Two entries were ADDED to the cannot list on 2026-08-17 without any ship
touching the code** (plan §0.5 items 2 and 3): the value↔quote binding and
per-member collection verification. **That is this file working as designed and
it is worth naming.** Both were believed closed — the plan asserted a cheap
extractor was *"safe structurally"* — and both were opened by the critic lane
RUNNING the mechanism the build lane had only read. A capability list derived
from prose would still say the opposite. Reasoning of record:
`DR_CRITIC_COORDINATION.md` §118, §120, §121 (untracked, shared checkout).

## 3a. Instruments — not demo, never shown

These exist to make a RULES obligation mechanical. They render nothing, register
nothing, and the room never sees them.

| Instrument | The rule it makes mechanical |
|---|---|
| `dr_dump.py` | RULES §12's *"answer against a dump the owner ran"* — every grounding graph a run leaves, raw, zero third-party deps. |
| `dr_mutations.py` | RULES §12.2's *"one mutation per new guard; a mutation that reddens nothing is a finding"*. Applies each mutation, runs every guard file in a fresh subprocess, reverts in a `finally`, hashes the sources before and after, re-runs to prove the tree came back. A **dead** mutation — one whose anchor no longer exists — exits non-zero, because a guard whose only proof of failure has silently stopped existing reads as a shorter run. Three went dead on the first refactor after it was written. |

If a second consumer appears core-side, `dr_mutations.py` generalizes then, not
now.

## 4. The rule this file exists to enforce

**A capability is what the code performs on a command someone else can run**
(RULES §11). Anything on the first list that stops being true is a red gate, not
a documentation update — and anything moved from the second list to the first in
the same breath as the ship that moved it is the only way this file stays worth
reading.
