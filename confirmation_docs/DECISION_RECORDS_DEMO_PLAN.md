---
title: Decision Records — Demonstration Plan
status: Proposed
basis: origin/main 5c6c5db (audited), confirmation_docs/marketing/, BRAIN_ARCHITECTURE_AUDIT.md
date: 2026-08-08
amended: 2026-08-11 — the routing beat, and SARA narrowed. See §0.1.
---

# Decision Records — Demonstration Plan

## 0.1 Amendments, 2026-08-11

Four decisions, owner-agreed. Each is recorded in the section it changes; this is
the index. Occasioned by two field conversations (Mauricio, claims, by phone;
Elisandro Porto, S4A, 2026-08-11) and by one verification against the SARA
dataset that killed the version of the beat everyone preferred.

1. **The routing beat is taken, and it is Phase 7 content — claims, synthetic,
   demonstration-only.** Two people in unrelated industries described the same
   intake-triage problem unprompted, which nothing else in the field notes has
   done. §1, §2.5, Phase 7.
   ⚠ **Its SUBJECT changed later the same day — route EXPOSURES, not the claim.**
   Classifying an arriving claim to a line of business dramatises a decision the
   policy number already made. §2.5.
2. **Routing cannot be evidenced by any dataset in scope, and the deck must say
   so.** Verified, not assumed — §2.1. It buys credibility in the room, not in
   the pack.
3. **SARA narrows to §152 and §7703 for Phases 1–2.** Nine sections was the
   largest uncosted line item; those two are the ones this plan itself calls
   "the product's shape". The numeric half follows if it earns its place. §2.1,
   Phases 1–2.
4. **Route-as-decomposition is rejected** — the attractive version, where the
   system works out which statutes a question depends on. §2.1.

**Sequencing is deliberately NOT changed.** The 2026-08-11 assessment argued for
pulling Phase 7 ahead of Phases 1–6, and the argument is a fair one: those phases
serve a deck and Phase 7 serves the two people actually waiting. It is moot until
Decision Records v0 exists — nothing in Phase 7 can start before runs 1 and 2
render — so the question is left open and revisited when v0 lands, rather than
re-planned now against a build that does not exist. §6, open decision 6.

## 0.2 Amendments, 2026-08-16 -> 2026-08-17 — PHASE 7 IS BUILT

**Read `STATE.json` `demos.decision_records` before this plan**, then
`projects/decision_records_demo/DR_DEMO_WALK_2026-08-17.md`. Four changes:

1. **Phase 7's freeze is the demo script's SEVEN BEATS** — owner ruling
   2026-08-16 — **not** §5 Phase 7's *"five synthetic claims cases; batch
   pass; refusal list on page one"*. Three documents defined Phase 7
   differently (§5, open decision 6's close condition, and
   `DR_DEMO_SCRIPT.md`), which made *"the scope is FROZEN as written"*
   unevaluable — the Gate-4 failure mode, on Gate 7. §5 Phase 7 below is
   amended to match; the script is the operative text.
2. **Gate 7's MECHANICAL clause is GREEN** (2026-08-16, Linux box, three cold
   runs, no operator intervention, exit 0). What is still owed is in §5
   Phase 7. **The tag is not a green gate.**
3. **A per-beat runner** (`dr_demo_beat.py`) was added to the frozen scope by
   owner ruling 2026-08-17: the batch driver measures the machine and cannot
   *perform* the script.
4. **The demo was walked end to end for the first time on 2026-08-17 and it is
   NOT a v1.** Six ranked gaps, found by looking at pages while 56 guards were
   green. The one finding: **the pages show WHAT, not WHY** — §2.3's form
   (question -> answer -> therefore) is achieved only when the system
   *refuses*. Do not scope v1 without reading the walk document.

## 0.3 Amendments, 2026-08-17 — THE v1 FREEZE

**Read `projects/decision_records_demo/DR_DEMO_CAPABILITIES.md` beside this
section.** It states what the demo does and cannot do, off the tree, and it is
the answer this plan has never carried.

Phase 7 is built and was walked end to end for the first time on 2026-08-17
(§0.2 amendment 4). This section freezes what v1 is. **Reasoning, the refused
alternatives and the critic lane's conditions are in
`DR_CRITIC_COORDINATION.md` §90–§93** (untracked, shared checkout — RULES §5);
what is operative is here.

**1. Gate 7 (b) is AMENDED — Mauricio leaves the acceptance.** Owner ruling:
his two questions are no longer asked before the demo is shown, because the
call is unscheduled and the demo must be shown to other people. They become
**post-hoc validation**. ⚠ **The showing-risk does not disappear with the
clause** — §2.5's open question, *is routing PERCEIVED as the hard call*, is now
unmeasured at showing time, so §2.5's own constraint hardens: **the demo shows
THAT routing happens and MUST NOT assert what any carrier does.** See §5
Phase 7 (b).

**2. The v1 acceptance criterion, and it is TWO THINGS because one sentence was
not evaluable.** The first draft read *"the room knows the answer in advance,
an input is changed in front of them, and the Record reacts"* — half gate, half
wish. Split, on the critic lane's condition (§91 Q1), the same move that
rescued Gate 4:

- **THE GATE — mechanical, and it can go red. AMENDED 2026-08-17 (owner),
  after the critic lane RAN the edits instead of reading the sentence.** *An
  input edit made in front of the room changes the rendered Record, and the
  changed page NAMES the changed value and its source.* Checked by re-running
  with the edited input and diffing the pages: **the diff must be non-empty
  and must contain the new value; the changed page must name that value's
  source WHERE THE STORE HOLDS ONE.** The guard's rehearsed edit is chosen so
  the **determining fact does not move**; the **equality edit** — where the
  limit stops binding, the page re-credits the claimed amount and stops citing
  the edition — is pinned as its own guard, **behavior shown, not gated**.
  Ship C carries both; a mutation that makes the edit inert reddens the first.

  ⚠ **Why the original wording could not be met.** It required the diff to
  contain the new value *and its named edition or source*. On an amounts-only
  edit the Source line does not move, so it is context and never enters the
  diff — and on the equality edit it leaves the page altogether. Read
  literally, the gate was unsatisfiable on the surface §0.3 item 4 rules
  editable, which would have made ship C depend on
  `decision-records-as-of-date-validity`. **That dependency does not exist
  under this wording.**

- **THE FIXTURE-DESIGN RULE — enforced at rehearsal, not by a test. RE-WORDED
  2026-08-17 (owner).** *Every case whose OUTCOME the room is asked to
  anticipate must be derivable from values visible on screen; a case shown for
  refusal or rule-following must instead make the deciding or missing item
  visible on screen before the page renders.* This is a property of the CASES,
  so no test can assert it; it is checked in the rehearsal walkthrough
  (prereq 4).

  ⚠ **The one-clause original — *"every live case's expected outcome must be
  derivable by mental arithmetic"* — condemned beats 1, 2 and 3**, which
  contain no arithmetic and never will. Half of an acceptance criterion that
  cannot be met is the drift the Gate-4 split exists to remove. The second
  clause is not a softening: it is what ships A and B already built, so it
  costs nothing to satisfy and it would have caught the walk's own gaps.

**3. SARA on the live screen is REJECTED** — open decision 10 records the four
reasons. The need underneath it is real and unchanged: Phases 1–3 supply the
number that is not ours, offline, in the evidence pack.

**4. The live inputs console is ADDED to Phase 7's frozen scope**, owner ruling
— the same class of addition as the per-beat runner. Cases and the policy store
move out of Python constants into an editable file, so an input can be changed
in front of the room and the beat re-run.

⚠ **THE EDITABLE SURFACE IS RULED — AMOUNTS ONLY at v1. Owner ruling
2026-08-17**, taken on both lanes' recommendation (coordination §99.4, §100,
§101.4) after ship B mapped what this system can and cannot refuse.

- **EDITABLE: the edition's stated limit, and the claimed amount.** Both are
  integers read by `structured_ingest_v0`, whose `value_not_coercible` refusal
  is shipped and honest — so a wrong value in the room lands on a refusal this
  demo was built to show.
- **NOT EDITABLE at v1: dates.** Not the as-of date, not an edition's in-force
  window. **The reason is a defect, not a preference:** `policy_lookup_v0`
  reports a malformed `as_of` as `source_unreachable`, so a typo renders *"the
  policy store cannot be read"* — the demo blaming our own system for the
  room's keystroke, in front of a buyer. Filed as
  `decision-records-as-of-date-validity`, unowned since 2026-08-12 and **now
  owner-taken**. Editable windows additionally reach the *boundary* shape this
  plan classifies as gate evidence the room never sees.
- ⟹ **Dates join the editable surface when that item closes, not before.**
  **Console validation is NOT the fix** and may only ever be a stopgap: no
  validation makes a misclassification true, it only hides it from the one
  path that happens to be validated.
- **What this costs, stated rather than glossed:** the room cannot re-drive
  *"the policy changed mid-claim"* by hand at v1 — beat 4's pair stay
  prepared, and only the amounts move. The gate is unaffected: an edition-limit
  edit changes the rendered Record and the changed page names the new value
  and its edition, which is the gate in full.

⚠ **THE BOUNDARY IS THE WHOLE OF IT, and narration does not carry it.** Policy
DATA and the CLAIM are editable live; routing and decision LOGIC are not
(`DR_DEMO_SCRIPT.md` beat 7 stands unamended — *"no live rule-authoring,
ever"*). Three layers, two mandatory:

- **(a) MANDATORY — the editable file must LOOK like a record.** `key: value`
  lines, a claim form, an edition with dates. Never `if/then`, never a
  threshold paired with an action. **This is ship C's acceptance condition, and
  its failure branch is named in advance:** if the file cannot be made
  record-shaped, ship C drops to the HYBRID — prepared cases, room-chosen
  values only. A lane that discovers this mid-build takes the hybrid; it does
  not make the file logic-shaped and narrate around it.
- **(b) MANDATORY — one narration line at the edit**, verbatim in the script:
  *"you are changing what arrived and what the policy says — not how it
  decides; that is expert work, and it is beat 7's ask."*
- **(c) REHEARSED — the planned parry.** When the room proposes a rule change
  (*"send severe injuries to the routine desk"*), **the demo DECLINES, live.**
  Performing the product's own refusal at the meta-level is what makes the
  data/logic line legible by demonstration rather than by assertion.

**5. THE DETERMINING FACT — what a Record shows on a decision it ANSWERED.**
Owner ruling 2026-08-17, and it supersedes the two-step form this lane
proposed earlier (*"every admitted read now, narrow later"*). **The page shows
the fact that DECIDED, not every fact that was read.**

- A four-exposure page listing every read is a data dump the room stops
  following; *"the specialty injury unit, because the assessed severity is
  severe"* is a decision, and it is what §2.3's *question → answer →
  therefore* was always describing.
- ⟹ **The deciding capacity must RECORD which of its inputs determined the
  outcome**, as a stored structural field on the verdict value, exactly as
  ADR-0209's `refusal_reason` marker already is: **branch-only, never
  printed** (it names a DataState, and G6 bans IRIs from the page). The
  renderer uses it to SELECT which stored question and answer to show.
- **Gate 1's own words are the reason** — *"every Record names the determining
  condition"*. This makes the live demo satisfy in claims what Phase 1 was
  going to have to satisfy in SARA, and it does so on the beat the room can
  check.
- ⚠ **A capacity that records no determining input renders `item → verdict` as
  it does today, and is NOT punished for it** — the policy criterion writes no
  origin record by design (ADR-0208 (c)). What raises is a capacity that
  DECLARES a determining input whose stored question or answer cannot be
  found: that is a gap, and G2 says raise, never fill.

**6. THE COMPARISON — what Screen B actually tests.** Owner ruling: **not
accuracy.** On a case a claims manager can check, a frontier model will also be
right, and a correct-answer contest is one this plan says on its own terms is
lost (§2.1, §3). What is compared is **reaction to a change**: alter the policy
edition or the claimed amount in front of the room and re-run BOTH. The Record
names the edition and the in-force window it decided under; the model changes
its answer and cannot say which policy it used or that anything changed. **This
comparison holds even when the model's answer is right**, which is the property
every other framing lacks. Written into `DR_DEMO_SCRIPT.md`.

**7. The room does NOT bring its own claim at v1.** Owner ruling. An
unrehearsed claim can land on a refusal or a no-route path, and the meeting is
then spent explaining rather than demonstrating. The room chooses **a value
inside a case we control** — the claimed amount — which buys the same
credibility with none of the risk. A claim of their own stays beat 7's ask,
where it is already the close.

**8. v1 is THREE SHIPS, and the fourth is refused.**

| Ship | Closes | Why it is in |
|---|---|---|
| **A** — the determining fact on the page | walk gap 1 | without it the refusals are documented better than the answers, and claim 1 is asserted rather than shown |
| **B** — claimed amount vs the dated limit, the settlement reducer, and the routing reducer naming its pending exposure | walk gaps 2, 3, 5, and one promotion out of 6 | the only beat whose answer the room computes before the page renders |
| **C** — the live inputs console | the *"looks pre-made"* finding | a value the ROOM chooses is the only evidence the demo is not a lookup table; prepared variants are pre-made by definition |

**REFUSED: walk gap 6, the room-facing text pass**, with ONE promotion out of
it on a stated §11 ground (critic §91 Q5): *"1 cannot be assigned yet — see the
exposure above"* over a four-exposure list is AMBIGUOUS to a cold reader, which
is a page defect rather than formatting, so the routing reducer NAMES the
pending exposure and that line joins ship B. **Currency formatting stays
refused:** a `$` the layout invents is a fact-channel violation in miniature —
if the room needs it, the number's UNIT becomes stored content in v2, not
chrome. Two strings ride along only where a ship already edits that line.
Walk gap 4 is a SCRIPT fix, already amended in `DR_DEMO_SCRIPT.md` beat 5.

**⟹ THE REFUSAL RULE, and it is the point of this section: anything not on
that table is past the gate and is refused like any other work past its gate.**
Adding to it is an owner ruling, not a lane choice.

⚠ **SHIPPED 2026-08-17: A (`dr-deciding-fact-confirmed`) and B
(`dr-ship-b-confirmed`, squash `df57033`, PR #180).** Ship B in five slices —
the claim-level line NAMES the exposure it cannot assign; beat 6 rebuilds the
richest Record; a refusing LEAF names the decision it could not make, in the
capacity's own words; beat 4 decides the claimed amount against the dated
limit and carries the edition behind it; the two beat-4 pages say **submitted**
and **assessed**. 68 → 92 guards, 13 → 41 mutations. **C is not started**, and
its editable surface is the open owner ruling (see §0.3 item 4 and
`DR_DEMO_CAPABILITIES.md`'s refusal boundary). ⚠ **The item numbering of this
section ran 1–9, 11, 10 for a ship** while being the text refusals are made by
citing; corrected here.

**9. Two things are owed that are NOT code, and they are the demo's critical
path.** Escalated by the critic lane (§91) and owner-accepted 2026-08-17:

- the **RULES §12.5 full-matrix re-run** is a Gate-7 predecessor with **no
  owner**, and is in none of v1's three ships. **Owner-owned; run before the
  demo is shown outside.**
- **Screen B has never been run at any beat** and beats 0 and 7 have never been
  rehearsed. **Owner-owned; five rehearsals per beat, both screens**, including
  §0.3 amendment 4(c)'s parry.

Neither is engineering, and no amount of building closes them. Gate 7 is green
with the hole it was worded to close until both are done.

**10. SHIP D — THE LIVE PROSE BEAT. Owner ruling 2026-08-17, and it does NOT
gate v1.** The pitch is *the model reads, MindsOS decides*; the demo shows
MindsOS deciding with no model present anywhere. Those are different claims and
Gate 7 (a) exists to stop the first being said over the second. Ship D closes
that: `comprehension_v0` reads a claim EMAIL live, and the rest of the pipeline
is untouched.

- **Reuse beat 2, swap ONE reader** — structured ingest → comprehension, over a
  prose email stating the injury. Same routing, same desks, same page. **The two
  pages differ in ORIGIN and in nothing else**, which is claim 5's artifact
  (§3, the adapter delta) performed live instead of tabulated. A new case would
  prove less, by having nothing to be identical to.
- ⚠ **IT REQUIRES A PIN BUMP, and that kills all three no-model guards.**
  `mindsos_capacity/llm/` and `builtins/comprehension_v0.py` are on `main` and
  **absent from `dr-partial-record-confirmed`** (checked with `git ls-tree`).
  After the bump, *the pinned core carries no model seam* is false, *no demo
  module imports the seam* is false, and *no case produces a value a model
  read* is false. **Deleting them to make the beat build would destroy the
  proof of the strongest claim in order to demonstrate the second-strongest.**
- **They are REPLACED by four structural guards, and the claim gets stronger.**
  The old set proves *no model is present* — a fact about a configuration that
  stops being true the moment the product does what it is sold as doing. The
  replacement proves *the model cannot decide*: (i) no capacity in
  `origin_v0.DECISION_SHAPED_CATEGORIES` declares `consults_llm`; (ii) no
  verdict carries `read_by_model`; (iii) every model reading is quote-verified
  against the source or refused — `comprehension_v0` locates the quote in the
  source text, so a fabricated value becomes a refusal by construction; and
  (iv) **the CENSUS** — the set of capacities declaring `consults_llm` is
  pinned to exactly the enumerated readers and reddens when anything joins it.
  ⚠ **(iv) exists because (i) has a hole the critic lane found: a REDUCER sits
  in family `derivation`, outside the decision set, while shaping the
  claim-level conclusion** — `dr_routing._assign` is one keyword away from
  being it. Verified on the tree: `consults_llm=True` appears on **exactly one
  capacity in the repo** (`comprehension_v0`), so the census's correct value
  today is 1. Beat 5's line becomes *"the model read this line, and here is why
  it could not have decided it."*
- **TWO GATES, each stating what it covers.** Gate 7 keeps its scope and says
  so — it covers the structured cases, which stay the demo's spine. Ship D gets
  its own weaker, honestly-named gate: *it ran N times against a live provider
  in rehearsal, with the refusal branch observed at least once.* **The weaker
  gate's name rides IN the script on the beat card** — *"live-provider,
  rehearsal-gated; everything else you saw runs cold"* — so the room's
  description of the demo is the script's own words rather than an inference
  from the stronger gate.
- **Fallback.** `recording.py` / `replay.py` exist. Open decision 9's D9 rule
  governs: a demo running from saved answers is a scripted demo **and deserves
  to be called one**, out loud, in the room.
- **PRECONDITION, not advice: first provider contact happens at the owner's
  desk before any rehearsal.** The transport has never met a provider; the
  build gate has neither network nor key.
- **D DOES NOT GATE v1.** It is the only item in this plan with an external,
  non-deterministic dependency, and putting the finish line behind it is open
  decision 6's drift warning in a new costume. **Claim discipline in the
  interval, and it is a rule: until D is green, nobody says "the model reads"
  in a room.**
- ⚠ **RULED 2026-08-17 (owner): the quote-verification refusal IS COURTED,
  and it is DISCLOSED BEFORE THE RUN.** Choosing a source that genuinely lacks
  the fact, so the model overreaches and is caught live, is the strongest
  moment available in this demo — and it is honest **if and only if** the room
  is told first: *"this email never states the severity; watch what each
  does."* The line between rigged and designed is concealment, so the
  disclosure is not a courtesy, it is the condition. **Undisclosed, the lane
  will not build it and the beat is not run.** The disclosure line rides in
  the script on the beat card beside the weaker gate's name.
- Second rehearsal case, never the room's first prose contact: a source with
  MULTIPLE candidate values (a prior injury in the history), where
  disambiguation is the work.

Reasoning and the critic round: `DR_CRITIC_COORDINATION.md` §95–§97.

**11. THE RENDERER'S VOICE — where it ends. Owner-ratified 2026-08-17
(coordination §100 Q2, §109.3), and it is general rather than a fix.**

> The renderer may describe **the Record's LIMITS** — meta, case-invariant,
> true of every Record rendered from a store, which is what makes *"Decided
> date: not available from stored evidence"* chrome. It may **never describe
> the case's OUTCOME**. Outcome words belong to the capacity that decided, or
> failed to; a refusal-capable producer owes registered words for what it
> could not do, and a refusing leaf without them RAISES.

The one-sentence form is in `RULES.md` §11 so it binds every lane, not this
one. ⚠ **It has a live consequence in ship C:** the comparison words the
beat-4 verdict adopts (item 12, step 5) are minted in the deciding capacity
and never in the renderer — a comparison word arriving from layout chrome is
exactly what this rule reddens.

**12. THE ROAD TO v1 — the ordered steps, owner-approved 2026-08-17.** Recorded
here because a plan of record that states gates and never states the sequence
is how the two owner-owned items sat unowned for a week.

| # | Step | Owner | Done when |
|---|---|---|---|
| 1 | **This ship** — the acceptance re-wordings, the gate amendment, ship D's ruling, the renderer's voice, this table | lane | merged to `main` |
| 2 | **Ship D's courted refusal** — nothing built; rides in the script on the beat card | lane (text), owner (delivery) | in the script |
| 3 | **The §12.5 full-matrix re-run** — a SEPARATE lane costs it and produces the exact commands and nothing else; **the OWNER runs them** and reads the output (§11: the dump is the owner's); findings get dispositioned in STATE in the same ship | owner, scoped by a lane | commands run, findings dispositioned |
| 4 | **Screen B and the rehearsals** — prereq 3 ruled (below), the paste files built with ship C, then ONE full dry run both screens beats 0–7 with nothing fixed mid-run, then per-beat reps aimed at what it exposed, with the parry drilled separately | owner | dry run done, reps logged |
| 5 | **Ship C** — amounts only, dates SHOWN LOCKED, the gate guard in the shape item 2 now specifies, the comparison-led verdict, and the paste files step 4 needs | lane | merged + tagged |

**Step 4's prereq 3 is RULED (owner 2026-08-17):** with intake structured,
*paste-identical* means **pasting the structured record to the model
verbatim** — satisfiable for claims, unlike SARA where open decision 10
correctly calls it impossible. It sharpens beat 5 for free: the model reads
the same intake the system reads and still cannot say which edition governed.

**Step 5's verdict change, and the pushback that caused it.** Owner, 2026-08-17:
*arithmetic can be done by anything and may not read as intelligence — it will
be confused with an algorithm; a comparison could show some intelligence.*
Correct, and it names a real failure mode: `400000 − 350000 = 50000` is the
CHECK, not the claim, and it is the one operation a room can dismiss as a
spreadsheet. **The verdict leads with the comparison and keeps the operands as
evidence** — *"exceeds the limit in force — 350000 payable of 400000 claimed"*,
and *"within the limit in force — 300000 payable in full"*. The room does the
arithmetic; the system does the judgment. Four conditions (critic §111.1): the
comparison words are minted in the deciding capacity; three guard re-cuts land
in the same ship, including the §103 collision fixture whose assert keys on the
removed token; the equality guard is drafted against the NEW phrasing from the
start; and beat 4's magnitude movement survives in the two editions' operands
(350,000 vs 375,000) without the difference token.

⚠ **What is NOT the intelligence, stated so nobody defends the wrong thing in
a room:** the subtraction. **What IS, and it is already built:** which limit
applied — two editions, selected by a date, the in-force window named; which
input DECIDED, and the page re-crediting itself when the limit stops binding;
and, a year later, which edition it decided under. A spreadsheet compares. It
does not tell you which policy edition governed February.

**13. THE TRANSFER LINE — RULED 2026-08-17 (owner). TWO SENTENCES, AND THE
FORM IS PART OF THE RULING.**

A room that does not do claims watches twelve minutes of someone else's
industry unless something names what a beat is an INSTANCE of. Occasioned by a
dated owner statement: *for an audience that deals with claims and routing this
is easy; for one that does not, the presentation has to inspire them to see
their own problems fixed.*

**What was ruled IN, and it is deliberately smaller than the bound the critic
lane offered (one line per beat, §111.2):**

- **Beat 0 frames it once**, after the pain and before any product: *"That's a
  claims example — the shape is the same wherever work arrives and a person
  decides where it goes."* ⚠ **This is a claim about the PROBLEM's generality,
  which is field-evidenced** (§2.5: two people in unrelated industries
  described the same intake-triage problem unprompted, and nothing else in the
  field notes has done that). It is **not** a claim about this system's
  generality.
- **Beat 4 carries ONE interrogative line**, because versioned rules are the
  most universal thing the demo shows: *"Your rules changed in March — could
  your system tell you which version it applied in February?"*

**TWO CONSTRAINTS, and the first is why this is rulable at all:**

1. **INTERROGATIVE FORM ONLY.** A transfer line asks a question about the
   ROOM's system; it never asserts that ours generalises. ⚠ **The reason is
   `DR_DEMO_CAPABILITIES.md`:** all thirteen L4 catalog capacities are
   placeholders, so nothing said about composition or planning is supported by
   what runs, and *"anywhere work gets split and assigned"* would be a
   generality claim the demo cannot demonstrate — §11's over-claim, in one
   sentence, on the beat card. A question about their system asserts nothing
   about ours and the beat they just watched answers it by demonstration.
   **If a candidate line cannot be phrased as a question about them, it does
   not go in.**
2. **WHICH BEATS IS DECIDED BY THE DRY RUN, NOT NOW.** Two lines to start.
   Beats 2 and 3 — the refusal beside an answer, and telling your team what to
   fetch — are arguably the most transferable moments in the demo and get
   nothing; if they visibly fail to land on a non-claims audience that is
   EVIDENCE, and a third line is a second ruling with a dated cause. It is not
   drift.

**What this does NOT reopen.** Walk gap 6 — re-wording existing narration for
quality — **stays refused**, and the distinction is the reusable half (critic
§111.2): *wording-without-a-dated-cause is the refused pass whatever argument
it wears; changing what a beat CLAIMS TO BE, for an audience named in a dated
statement, is new content and enters by owner ruling* — the same door the live
inputs console walked through. **Never in code. Never a paragraph.**

**14. What this section does NOT change.** Phase 7's intake stays STRUCTURED
(open decision 9). The beats stay the operative scope text. Phases 1–3 remain
the committed following block at a green Gate 7 (open decision 6) — v1 does not
reorder them, and any proposal that makes v1 depend on SARA does.

---

## 0. What this plan is, and what it is not

It produces **two separate artifacts**. Merging them is the main way this goes wrong.

| | **The evidence pack** | **The live demo** |
|---|---|---|
| Audience | Read before the meeting; cited in the deck | Watched in the room, on a laptop |
| Domain | US federal tax law (SARA), federal civil procedure (LegalBench) | Synthetic claims |
| Purpose | Prove the claims hold on cases we did not write | Show what a Record looks like |
| Runs | Offline, batch, reproducible | Live, five cases, reliably |

The evidence pack is **not** the demo. Tax law in front of a claims manager is a distraction. The demo is **not** evidence — we wrote the cases.

**This whole track is zero-revenue.** It is sales evidence, not product. Time-box it; it must not displace the four build pieces.

### What no dataset can test

The acceptance gate — *the Record is rendered from the grounding graph, not from anything computed beside it* — is a property of the code. It is verified by the mechanical guards in §4 and by nothing else. **A green benchmark must never stand in for a green guard.** That substitution is how arc1 happened.

---

## 1. The claim-to-evidence matrix

Every external claim, and the one thing that tests it.

| # | Claim | Tested by | Artifact |
|---|---|---|---|
| 1 | The reasoning **is** the record | Mechanical guards G1–G3 | Code, not data |
| 2 | Every value keeps its origin | ContractNLI evidence spans (which sentence a value was read from) | Evidence pack |
| 3 | It refuses | SARA-ablation (fact missing) + unroutable target (no route exists) | Evidence pack |
| 4 | It composes rather than scripts | `diversity_1..6` staged difficulty; SARA case heterogeneity | Evidence pack |
| 5 | The model reads, it does not decide | SARA run **twice** — structured input, then adapter — same answers, different origins | Evidence pack |
| — | Policy identity and version | SARA in-force windows + dated cases | Evidence pack |
| — | Policy *replaced* between submission and assessment | Synthetic only | Live demo |
| — | **Exposure routing** — this exposure goes to that desk, and here is why | **Nothing. No dataset in scope supplies routing ground truth** (§2.1) | **Live demo only** |

Claim 1 has no dataset row on purpose. **The routing row has none for a different
reason, and the difference matters:** claim 1 is tested by a mechanical guard
instead of data; routing is tested by *nothing*, and is shown rather than
measured. It is checkable on the spot by one person watching one case, which is
real and is why the beat is worth taking. If routing ever appears in the evidence
pack, or a routing number appears in the deck, that is the arc1 substitution in a
new costume.

---

## 2. Datasets and their roles

### 2.1 SARA — primary
Johns Hopkins StAtutory Reasoning Assessment. Nine IRC sections (§1, §2, §63, §68, §151, §152, §3301, §3306, §7703), lightly edited to be self-contained. **376 hand-crafted cases: 276 entailment, 100 numeric.** Cases are prose fact patterns carrying calendar dates. Statutes carry effective-date clauses and year-dependent dollar amounts.

- **Entailment (276) is the primary half.** §152 dependency and §7703 marital status are multi-condition eligibility tests producing a yes/no with a determining condition — the product's shape. Use these for the Record.
- **Numeric (100) is the arithmetic proof.** A dollar amount is not a Decision Record; it demonstrates threshold, lookup and precedence composing correctly.
- **In-force windows are the versioning test.** A case dated inside one window and a case dated inside another must select different limits, and each Record must name which.
- Prose fact patterns mean SARA exercises the **reading stage** as well as the decision stage. Errors are attributable to a stage — which is itself a demonstration of claim 2.

**Known and to be stated up front:** a hand-built Prolog system already scores well on SARA, and SARA is in LegalBench so any LLM baseline is contamination-inflated. **Accuracy is not the claim.** Do not publish a head-to-head table.

#### Amended 2026-08-11 — scope, and what SARA cannot do

**Phases 1–2 encode §152 and §7703 only, not nine sections.** They are the two
this plan already names as the product's shape — multi-condition eligibility
producing a yes/no with a determining condition. Nine sections is named in §7 as
the largest uncosted line item, and most of that cost buys the numeric half,
which is the lesser one. The remaining sections are added when a specific gate
needs them, not up front.

**SARA cannot carry the routing beat, and this was verified rather than
reasoned.** The proposal was appealing: route *within* SARA — which section
governs this case — where the labels are already in the data and the shape is the
same "which specialist handles this". It fails, because the governing section is
stated three times over in every case:

- the `id` encodes it — `s151_a_neg`;
- the `text` names it — *"She gets one exemption of $2000 for the year 2015 under
  section 151(c)"*;
- the `question` names it — *"Alice's total exemption for 2015 under section
  151(a) is equal to $6000"*.

A router reading the question already has the answer; regex scores ~100%. SARA's
task is *apply the named statute*, not *find it*. Routing between two datasets
(SARA versus LegalBench) fails for a different reason — the label is free but the
task is a corpus classifier over prose by different authors, and nobody has an
intake queue mixing IRC §152 with federal diversity jurisdiction.

**Two salvage paths, both recorded and neither taken for the demo:**

- **Ablate the section reference** — strip it from question and text, route on
  facts alone. Legitimate, and it is the same mechanically-derived, publish-the-
  rule method §2.2 already accepts for refusal. But it is a set we built, so it is
  weaker than third-party. Available if a routing number is ever genuinely needed.
- **Route as decomposition** — *which sections must be consulted*, where §63 pulls
  in §151. Genuinely non-trivial, and SARA's `facts` / `test` Prolog fields encode
  which predicates fire, so the true dependency set is **derivable per case**: a
  real third-party label. **Rejected for the demo, kept as a future test for
  CORE-C4R3.** The wiring exists — `plan_construction._decompose_recursive`
  dispatches and recurses to `MAX_DEPTH` — and only two bodies are stubs
  (`decompose` returns `[]`, `predicate.is_leaf` is always True). But they are
  **Global placeholders**, so giving them real bodies changes `run_lifecycle` for
  nilm, arc1 and arc3, all of which assume one milestone and one pipeline; that is
  CORE-C4R7's, not a demo's. The additive alternative — Local shadows of the
  placeholders, the arc1 precedent — is the mechanism ADR-0205 §amendment-4.9
  retires. There is no small path, and it answers *which statutes* when the field
  evidence asked *which human*.

### 2.2 SARA-ablation — refusal
Derived, not sourced. For each case with a known answer, delete one input field and re-run; the correct answer becomes *"cannot be decided; missing X"*, labelled by construction with the missing item named.

**Ablate mechanically — every field, one at a time, exhaustively — and publish the count.** Any curation and a skeptic is right to say we wrote our own test.

This is closer to the product than any sourced refusal set, because it tests *a decision being underdetermined* rather than *a document being silent*.

### 2.3 LegalBench `diversity_1..6` — transfer and composition
Federal diversity jurisdiction: party citizenship plus an amount-in-controversy threshold over $75,000, yes/no ground truth, six staged difficulties. Same op shapes as SARA, different area of law, small.

Its job is answering *"you hand-built this for one benchmark."* The staging gives a curve rather than a point.

### 2.4 ContractNLI — extraction provenance
The only set in scope with **labelled evidence spans**. It is the sole dataset-level check that the origin a Record asserts points at the right sentence. Requires the LLM adapter, therefore sequences last, after the adapter's ADR.

Its "not mentioned" class is a *second* refusal flavour — keep it, but ablation is the primary.

### 2.5 Synthetic claims — the live demo
Five seeded cases per the GTM prompt: clean approval, clean denial, needs a policy exception, missing a required document, policy changed between submission and assessment. The fourth is the punchline. The fifth is the only thing no sourced dataset provides.

~~**Held until the claims-practitioner conversation.** Domain-independent work does not wait on it.~~

**Amended 2026-08-11 — the hold is satisfied, and a routing stage opens the
flow.** The claims-practitioner conversation happened (Mauricio, by phone,
unrecorded). The demo stays claims, which answers open decision 3.

**A sixth element, and it comes first: routing.** A case arrives and is routed
before anything is adjudicated, giving one continuous story — intake → route →
validate → decide or escalate — rather than two demos. Grounds, and they are
field evidence rather than invention: Mauricio described a human deciding which
department handles a claim, and Elisandro Porto (S4A, SAP integrator) described a
ticket arriving by email and a person paid to analyse it. Nothing else
volunteered twice, from two industries, unprompted. By contrast the adjudication
scenario in the market documents was written for illustration and has never been
checked by anyone who does the work.

#### ⚠ Amended again 2026-08-11 — the beat's SUBJECT was wrong

The version written earlier the same day said *"a case arrives and is **classified
to a department**"*, and argued the beat on *"this system knew it was liability,
not property, and can show why."* **That is falsified**, by
`projects/decision_records_demo/INSURANCE_LINES_TAXONOMY.md` §3 — the demo lane's
sourced research, commissioned to support the beat and returning against it.

**Why it is wrong.** In Guidewire ClaimCenter, which Intact runs, **FNOL requires
a policy before the claim opens, so the line of business is inherited from the
policy — not decided at intake.** Nor are claims units the statutory classes:
*Auto Physical Damage*, *Bodily Injury* and *Accident Benefits* are coverages
*inside* one line, *Casualty* collapses several, **severity tier dominates**
(Wawanesa's numbered levels, Travelers' "Mid-Loss"), and SIU / subrogation /
catastrophe / total-loss cut across everything. Ontario auto splits Accident
Benefits from Bodily Injury *within the single statutory line "Automobile"*.
⟹ **A demo classifying an arriving claim into a line of business dramatises a
decision the policy number already made.** In front of a claims manager that is
worse than showing nothing.

**The replacement, and it is a better beat: route EXPOSURES, not the claim.** An
exposure is *one claimant × one coverage*, and it is the assignable atom.
Guidewire's own documentation gives the case: one auto loss, the vehicle
exposures to a routine group and the injury exposure to a group *"that specialize
in fatalities"* — **one claim, one line of business, two departments.** Three
gains over the classification version:

- The decision is genuinely **post-FNOL and genuinely unautomated** — the two
  properties the classification version lacked.
- **One document yields several routing decisions with different answers.** More
  striking in a room than a single classification, and it is the product's actual
  shape rather than a shape borrowed for the demo.
- The refusal lands where it is strongest: *"I cannot tell whether this exposure
  needs the specialty unit, and here is what is missing"* — a per-exposure refusal
  standing **beside** a per-exposure answer, on the same claim.

**Caveat on the evidence, recorded rather than glossed.** No carrier publishes a
claims org chart. §3's finding is reconstructed from job titles (strong that a
unit exists, weak on hierarchy) plus Guidewire's routing documentation (strong,
but one vendor — Duck Creek, Sapiens and Origami were not checked). It is enough
to abandon the classification framing; it is not enough to assert what every
carrier does. One question to Mauricio settles it.

**The taxonomy survives the subject change.** OSFI/CCIR Section III — nineteen
classes, mirrored on Alberta's licensing side by the Classes of Insurance
Regulation — is the right vocabulary for naming the **coverages** exposures are
made of, and its ambiguous pair transfers unchanged: **Automobile vs Liability**,
where the CGL auto exclusion, *mobile equipment* and the *loading and unloading*
doctrine make the boundary *"necessarily a fact-intensive inquiry"* decided case
by case. NAIC's lines were rejected for Canada — workers' compensation is a
provincial WCB monopoly, so putting it on the board says the deck was written for
someone else.

**Two costs, restated. The second one I have now had wrong twice.**

1. ~~**The no-route refusal has no machinery behind it.**~~ **CLOSED** —
   `core-terminal-node-on-non-success` (L-2) shipped as `c9754ac`, tag
   `terminal-node-confirmed`. A stopped run now leaves a `RunStopped` node wired
   to the values that led to it.
2. **Per-exposure routing is a MAP over a collection, not N flat capacities.**
   The earlier text called it *"N registrations of a shape already exercised"* and
   then corrected itself to add a reducer. Both undercounted. Fanning over the
   exposures of one claim is the collection-iteration path — shipped, and already
   carrying a known defect (`execution.py` composes a pipeline **per map member**,
   whose caller moves at C4R3) — plus the reducer that collapses per-exposure
   verdicts where *ambiguous* and *unroutable* live. **Check any new op against
   Gate 4 first**: if routing needs one adjudication did not, *"no new decision op
   was needed"* fails inside the demo, in front of the room.

**A third undercount, and a broken gate — found 2026-08-14 by reading the
tree, after a first draft of this paragraph got it wrong.** Routing is a
**selection**; the only `decision`-family capacity v0 ever built is ADR-0208's
**comparison** criterion. So routing needs a decision capacity of a kind never
built — the third undercount of this beat, after *"N registrations of a shape
already exercised"* and *"plus a reducer"*.

⚠ **And the check this plan tells you to run cannot be run.** §5 Phase 0 item 5
says *"all six ops in `decision`"*, and both v0 documents list *"the other five
decision ops"* as out of scope — but **the six are enumerated nowhere**. In
code: `origin_v0.DECISION_SHAPED_CATEGORIES` is a frozenset of **three
categories** (`decision`, `comparator`, `predicate`), and `FAMILY_RULES` holds a
single `decision: VERDICT` entry. In docs: no ADR names a set of six. The phrase
exists only in planning prose, repeated across three documents.

⟹ **Gate 4 is currently UNEVALUABLE.** Its pass condition is *"no new decision
op was needed"*, and you cannot decide whether an op is *new* against a set that
was never defined — so Gate 4 would pass or fail on whoever is reading it. Owed
before routing is registered: either **enumerate the six in an ADR** (making
Gate 4 checkable as written), or **restate Gate 4** against something that
exists — e.g. *no new capacity **category** beyond `DECISION_SHAPED_CATEGORIES`,
and no new `FAMILY_RULES` entry*. The first draft of this very paragraph
asserted "one of the family's six" and inherited the same phantom set; it was
caught by grepping instead of quoting. **Fourth instance in this lane, and the
second in one day.**

⚠ **Do not invent a department taxonomy or an exposure taxonomy.** Both are
sourced above. An invented one re-creates exactly what makes the adjudication
scenario weak — a scenario we wrote ourselves.

**Open, and it is what kills the beat if anything does:** is routing perceived as
valuable, or as something a junior does? Ask Mauricio on the demo call, before any
capacity is written: *"when a claim gets routed to the wrong desk, how long until
anyone notices, and what does it cost?"* — and, now, *"when a claim has several
exposures, who decides which desk each one goes to?"*

---

## 3. Metrics

One pair on the front page. Everything else is supporting.

**Headline**
1. **Correct when it answers** — accuracy conditional on not refusing.
2. **Confidently wrong** — answered, and wrong. **Target: zero.**

**Supporting**
- Answer rate (1 − refusal rate) — the honest cost of (2).
- Refusal precision on ablation — refused **and** named the correct missing item.
- Refusal recall on ablation — did not answer an underdetermined case.
- Transfer curve across `diversity_1..6`.
- As-of correctness — cases differing only in date select different limits.
- Extraction span agreement (ContractNLI).
- **Adapter delta (claim 5)** — SARA answers with structured input vs. with the adapter reading prose. Identical answers, different origins. Keep the pair; it is stronger than any score.

Never report a raw accuracy number without the refusal rate beside it.

---

## 4. The mechanical guards

Authored **before** the renderer. A guard written afterwards is shaped to pass.

- **G1 — Renderer isolation.** The renderer module may not import the blackboard, the capacity context, the L2 snapshot, the `Pipeline` object, or `chain_artifacts`. Enforced as an import test.
- **G2 — Renderer completeness.** Given a run graph with one capacity instance removed, the renderer **raises** rather than filling the gap from anywhere else.
- **G3 — No Record without execution.** A Record cannot be produced for a run whose capacities did not execute and write to the graph.
- **G4 — Refusal is in the graph.** Both shapes: fact-missing and no-route. Asserted structurally, not by string match on rendered prose.
- **G5 — As-of correctness.** Two cases differing only in date produce Records naming different limits and different in-force windows.
- **G6 — No vocabulary leak.** Rendered output contains none of: capacity, pipeline, DataState, metagraph, layer, verdict, IRI, or any `xxx:` IRI form.

Each must be demonstrably failable. A guard that cannot go red is worse than none.

---

## 5. Phases

Gates are pass/fail. Do not start the next phase on a red gate.

### Phase 0 — Domain-independent core *(no claims content, no SARA content)*
Everything here is mechanism and is not blocked on any conversation.

1. Refusal written into the run graph, both shapes; mint the grounding root before the finder runs so a no-route case still has a graph.
2. The origin taxonomy — read-from-source / asserted-by-a-party / inferred-by-a-model — derived from the producing capacity's registered metadata, never hand-attached per value.
3. The **extracted-not-seeded** rule: no value a Record must attribute may enter as a start input. Verified in code: `seed()` mints an instance with no incoming edge, so a seeded value's origin is structurally unrecoverable.
4. Policy store: append-only, `in_force_from` / `in_force_to`, read **through a lookup capacity** so the limit and its version enter the derivation as produced DataStates. Verified: `record()` writes only `(capacity_iri, input IRIs, outputs)`, so anything read from the context snapshot never reaches the graph.
5. Decision family: all six ops in `decision` (VERDICT shape). `FAMILY_RULES` already declares `decision: VERDICT`; it has shipped and never been used.
6. Phrase convention: `DataState.description` is the noun phrase, capacity family supplies the verb. Both are already registered and persisted.
7. Guards G1–G4, G6, written and shown to fail.

**Gate 0:** guards red on a deliberately broken build, green on a correct one. Nothing rendered yet.

### Phase 1 — SARA entailment, structured input
Encode §152 and §7703 — **and, amended 2026-08-11, only those two** (§2.1). Values supplied structured; no adapter.

**Gate 1:** entailment cases answered; confidently-wrong = 0; every Record names the determining condition; G1–G4 green.

### Phase 2 — SARA numeric and in-force windows
Encode §1, §63, §68, §151. Dated cases select limits through the policy store.

**Amended 2026-08-11.** This is the half the nine-section cost mostly buys, and it is the lesser half. Encode the **minimum** that makes Gate 2 fire — one section with a year-dependent dollar amount and two in-force windows — and add the rest only when a named gate needs them.

**Gate 2:** G5 green — two cases differing only in date name different limits and windows. This is the money sentence, on third-party data.

### Phase 3 — Ablation
Exhaustive single-field ablation across Phase 1 and 2 cases.

**Gate 3:** refusal precision and recall reported; every refusal names the missing item in plain language. `NeedsInput.missing` is a DataState IRI today — G6 covers the translation.

### Phase 4 — `diversity_1..6`
Second area of law. Reuse the ops; register new types only.

**Gate 4 — RESTATED 2026-08-14 (critic §48 condition 4; decided in this PR, not filed as an IOU):** transfer curve produced; **no new capacity CATEGORY beyond `origin_v0.DECISION_SHAPED_CATEGORIES` and no new `FAMILY_RULES` entry was needed.** ⚠ **The previous wording — *"no new decision op was needed"* — was UNEVALUABLE**: the set of decision ops it measured against is enumerated nowhere (§2.5). **Restated rather than enumerated, deliberately:** an ADR inventing six ops to rescue the sentence would promote the phantom instead of killing it. The new form names two things that exist in the tree and can be checked by grep, so the composition claim has a gate that can actually fail.

### Phase 5 — LLM adapter
ADR first, code second. The adapter is fixed; the model is an external oracle it consults; its output is a typed DataState carrying provenance to the raw input and a recorded extraction uncertainty; it can decline.

Re-run Phases 1–2 with the adapter reading prose.

**Gate 5:** answers identical to the structured run; origins now show read-vs-inferred. That delta is the claim-5 artifact.

### Phase 6 — ContractNLI
Span agreement on extraction provenance.

**Gate 6:** the origin a Record asserts points at the labelled sentence.

### Phase 7 — Live demo *(~~blocked on the practitioner conversation~~ — the hold is satisfied, 2026-08-11)*

⚠ **STATUS 2026-08-17 — BUILT, AND THE SCOPE SENTENCE BELOW IS AMENDED.**
**The freeze is `DR_DEMO_SCRIPT.md`'s seven beats** (§0.2 amendment 1), so the
paragraph below — *"five synthetic claims cases; batch pass; one Record per
case plus the refusal list on page one"* — is **superseded on the scope
question**: there is no batch pass and no page-one refusal list, and the cases
that exist are the beats' cases plus five mechanism shapes the room never
sees. Shipped: `310bfe3` (tag `dr-phase7-confirmed`) and `cfe1bd8` (tag
`dr-beat-confirmed`) on `demo/decision-records`; 56 demo guards.

⚠ **AMENDED 2026-08-17 (§0.3 amendment 1): what is still owed is the BEATS ALONE.** Mauricio's two questions have left this acceptance. The three ships that close the walk's gaps are named in §0.3 amendment 5, and the list is closed.

**Gate 7's mechanical clause is GREEN, and Gate 7 is NOT.** Verified
2026-08-16 on the Linux box at `310bfe3`: `dr_demo_run.py` -> *cold runs: 3,
failed: 0*, exit 0. Still owed: **(b) below — Mauricio's two questions** — and
the beats themselves, which the 2026-08-17 walk found are not yet a v1
(`projects/decision_records_demo/DR_DEMO_WALK_2026-08-17.md`). A green exit
proves no gap reached a page; it says nothing about whether the beats land.
**Exposure routing opens the flow** (§2.5) — one claim, several exposures, each routed on severity and specialty — then five synthetic claims cases; batch pass; one Record per case plus the refusal list on page one.

~~**Depends on `core-terminal-node-on-non-success` (L-2)**~~ — **closed 2026-08-11**, shipped as `c9754ac`, tag `terminal-node-confirmed`. A stopped run now leaves a `RunStopped` node, so the unroutable case renders.

**Gate 7 — AMENDED 2026-08-14 (critic §48 conditions 1 + 2):** run cold on a laptop three times with no operator intervention. The refusal case fires on cue.

**(a) NAME THE VARIANT IN THE ROOM.** The cold run is the **structured-intake** variant — **no model, no transport**. This is written into the gate so nobody presents inbox-reading that does not exist: §11's seam rule applied to the demo itself. A prose-intake run is a DIFFERENT gate and needs the transport (open decision 7). ⚠ **AMENDED 2026-08-16 — this is no longer *a* variant, it is THE demo:** open decision 9 rules the intake STRUCTURED. Naming it in the room stays mandatory — say that intake is structured and that prose reading is the next variant, because the gap between what is shown and what is claimed is the only thing that cannot be repaired afterwards.

⚠ **AMENDED 2026-08-17 - Mauricio leaves this clause.** OWNER RULING: the call is unscheduled and the demo must be shown to other people, so his two questions are **no longer asked before the demo is shown** and no longer sit inside Gate 7's acceptance. They become POST-HOC VALIDATION - asked when the call happens, and capable of falsifying the BEAT afterwards rather than gating it beforehand. **The showing-risk did not evaporate with the clause, and this is the part that must survive the amendment:** §2.5's open question - is exposure-level routing PERCEIVED as the hard call - is now UNMEASURED at showing time, so §2.5's own constraint hardens rather than relaxes. The demo may show THAT routing happens and **must not assert what any carrier does**, and the room is told the cases are ours. The paragraph below is kept because its reasoning is why the questions exist at all.

**(b) VALIDATION IS SCHEDULED, NOT EVAPORATED.** Open decision 8 removed Mauricio as a BUILD gate; his two questions move here, into Gate 7's acceptance, and are **asked before the demo is shown to anyone outside**: *"when a claim has several exposures, who decides which desk each one goes to?"* and *"is that a judgement call or a rule?"* A no on the second means the beat dramatises a rule, and the demo changes before it is shown — not after. Showing-risk stays owned; only the build was unblocked.

⚠ **AMENDED 2026-08-14 — the transport is CONDITIONAL, not a flat Gate-7 blocker.** This paragraph's own last sentence always said so and was read past for three days: **routing from a STRUCTURED intake record needs no model at all**; it is routing from Elisandro's actual inbox that puts the seam on the critical path. So the transport gates Gate 7 **only if** the demo's intake is prose. Decide the intake shape first, and cost the transport from that — do not carry it as an unconditional blocker. S-2 is ruled either way (open decision 7), because settling it costs nothing now and becomes a rewrite later. ⚠ **CITATION CORRECTED:** this paragraph cited `LLM_SEAM_MANUAL.md` and `CORE_CR_EXTERNAL_MODEL_SEAM.md`, **neither of which was on `main`** — both live only on `archive/decision-records-llm-seam`. The manual is restored to `main` by this commit; the CR is not, and any citation of it must name the tag. Fifth instance in this lane of an argument resting on a document not in the tree.

⚠ ~~**Gate 7 has a dependency nobody has costed: there is no transport.**~~ **CLOSED 2026-08-16 (PR #169) — THE TRANSPORT EXISTS.** The paragraph below is kept because its *conditional* still governs: the transport gates Gate 7 **only if the demo's intake is prose**, and that shape is now **RULED: STRUCTURED** (2026-08-16, open decision 9). ⟹ **The conditional resolves to NO — the transport does NOT gate Gate 7.** Both the uncosted-dependency risk and the conditional itself are dead, the first by PR #169 and the second by the ruling. ⚠ **The remainder of this paragraph is SUPERSEDED on the blocker question** — it argues the transport is *"a Phase-7 blocker, not a nicety"*, which held only while the intake shape was open. It is kept because its D9 replay ruling still governs any future prose variant. `LLM_SEAM_MANUAL.md` S-3 — the one piece that touches the network does not exist. So a cold laptop run is replay-only today, and `CORE_CR_EXTERNAL_MODEL_SEAM.md` D9 rules that a demo running from saved answers is a scripted demo and deserves to be called one. Two consequences: **the transport is a Phase-7 blocker, not a nicety**, and **S-2 — whether the transport or `mindsos_llm` parses the model's output — must be settled before anyone writes one**, because afterwards it is a rewrite rather than a decision. Note also that routing from a *structured* intake record would need no model at all; it is routing from Elisandro's actual inbox that puts the seam on the critical path.

---

## 6. Open decisions

1. ~~**Which half of SARA leads.**~~ **CLOSED 2026-08-11 — entailment, and only §152 + §7703** (§2.1). Numeric narrows to the minimum that fires Gate 2.
2. **Whether the evidence pack ships publicly.** A published SARA result invites the accuracy comparison we do not want. Recommend: cited in the deck, method reproducible on request, no leaderboard entry.
3. ~~**Domain of the live demo.**~~ **CLOSED 2026-08-11 — the demo stays claims, the evidence pack stays tax**, and the practitioner conversation that gated it has happened (§2.5).
4. **Time-box — RESOLVED 2026-08-14 as a GATE, not a date.** Phases 0–4 are the defensible minimum. The original instruction (*set the box before starting*) was guarding against indefinite drift; the owner ruled that **the timeline is not the constraint, a proper demo is**, so the box became **gate-bound**: Phase 7 closes at a green Gate 7, its scope frozen, and Phases 1–3 begin there (decision 6). A concrete finish line does the guarding a date was meant to do — **and it only works because the scope is frozen**; unfreeze the scope and the gate recedes, which is the same drift by another route.
5. **Prior art review before any novelty claim.** A Prolog system solves SARA; "Explainable OpenFisca" exists. Neither has the grounding graph, but both need to be read before the deck asserts novelty.
6. **[OPENED 2026-08-11 · RULED 2026-08-14] Does Phase 7 move ahead of Phases 1–6? YES — Phase 7 first, GATE-BOUND, with Phases 1–3 as the committed following block.** The condition the old text deferred on (*"revisit when v0 lands"*) is met: v0 landed (items 1–7 + the correlation bijection; five case shapes render from a real FalkorDB round-trip). **Three facts that were not true when this was written and that decided it.** (i) **Phases 5 and 6 are blocked regardless** — both need the transport, and Phase 6 also needs `comprehension_v0`, which is on `archive/decision-records-llm-seam`; deferring them costs nothing because they cannot run. (ii) **Gate 4 is UNEVALUABLE** as written (§2.5), so the against-argument — *"skipping 1–6 leaves Gate 4 with nothing behind it"* — is currently protecting nothing. (iii) Phase 7 is the only block with people waiting and **no blockers**. **Why not the alternatives:** deferring the evidence pack indefinitely leaves every number in the room coming from cases we wrote, which makes *"confidently wrong: zero"* unfalsifiable; running Phases 1–3 first delays the only thing anyone waits for by this plan's largest uncosted line item (SARA encoding) and is the ordering §7 names as the highest risk. **The demo must be believed in a room, and that needs the beat working AND at least one number that is not ours** — Phase 7 delivers the first, Phases 1–3 the second, in that order. **THE BOX IS GATE-BOUND, not calendar-bound — owner ruling 2026-08-14: the timeline is not the constraint, a proper demo is; quality beats development speed.** The box **closes at a green Gate 7** — five pages rendered from the PERSISTED graph on a cold laptop, three times, refusal on cue, G1/G2/G6 green, and the page surviving the §11 room test unedited. **Phase 7's scope is FROZEN as written; any addition to it is an owner ruling, not a lane choice** — that freeze is what stops a gate-bound box from drifting the way an unset calendar box would. **Past a green Gate 7, further polish is refused like any other work past its gate: quality is gates passed, not time spent.** Phases 1–3 begin at that green gate. *(Supersedes the blank box this line first carried; the critic ruled — correctly — that a ruling whose operative term is blank is not a ruling.)* 
7. **[OPENED 2026-08-11 · S-2 RULED 2026-08-14 · S-2 BUILT 2026-08-16, PR #169 · OWNERSHIP STILL OPEN] Who owns the transport, and who parses the model's output?** **OWNER RULING on S-2: ratify the fix already proposed in `LLM_SEAM_MANUAL.md` §11** — the transport may return EITHER raw text OR a mapping; if text, decoding happens inside `mindsos_llm`, and a decode failure becomes the `malformed_response` refusal rather than an exception from unowned code. Accepting a mapping keeps provider-native structured output usable. ~~Compatible with shipped `main`: `malformed_response` is already classified in `origin_v0.REASONS_RESERVED` (#156).~~ ⚠ **STALE AS OF 2026-08-16 (PR #169): `REASONS_RESERVED` is now EMPTY (`{}`).** The four reasons it held *awaiting the LLM seam* are emitted (6/0/2) — the seam arrived, so `malformed_response` is a reason the shipped system EMITS, not one it reserves. **S-2 is now BUILT, not merely ruled**; the transport's OWNERSHIP is the half that stays open. ⚠ **S-2 was never an open question — it carried a written proposed fix nobody had ruled on**, and the row was read as undecided for three days because the manual it lives in **was not on `main`** (see the correction below). Ratified BEFORE a transport exists, which is the whole point of the deadline. **The transport's ownership is still open**, and it is reclassified below.
8. **[OPENED 2026-08-11 · RULED 2026-08-14] Is exposure-level routing what a claims manager actually recognises as the hard call?** §2.5's subject change rests on Guidewire's routing model — strong, but one vendor, and no carrier publishes an org chart. **OWNER RULING 2026-08-14: this does NOT gate the build.** Mauricio is an EXTERNAL RESOURCE WHO VALIDATES WHAT WE BUILD — not a decision-maker we wait on. The previous text (*"ask before any capacity is written"*) over-gated: §2.5 already forbids inventing a taxonomy **because both are sourced** — OSFI/CCIR Section III for the coverages exposures are made of, Guidewire's routing documentation for the exposure→desk model. The build needs neither answer. What his answer affects is whether routing is PERCEIVED as the hard call, which is a question about the pitch, not an input to the code. **The constraint that survives, and it is §2.5's own:** the org-chart evidence is reconstructed from job titles (strong that a unit exists, weak on hierarchy) plus one vendor, so the demo may show THAT routing happens and MUST NOT assert what every carrier does. Ask the two questions when convenient; do not schedule work around them.
9. **[OPENED + RULED 2026-08-16] Is Phase 7's intake PROSE or STRUCTURED? — STRUCTURED.** **OWNER RULING 2026-08-16**, taken on the transport lane's recommendation at the close of PR #169, and recorded here so Phase 7 begins with no undecided input. **The demo's intake is a structured record; the demo runs with NO MODEL AND NO TRANSPORT.** **Why, and the first reason is the only one that would settle it alone:** Gate 7 amendment (a) ALREADY specified this — *"the cold run is the structured-intake variant"* — so the ruling is compliance with a gate written 2026-08-14, not a fresh choice, and the box is gate-bound with Phase 7's scope FROZEN, which is exactly what stops the question reopening. Beyond that: three cold runs with no operator intervention is Gate 7's hardest clause and a live provider call fights it directly — the build gate has no network and no API key (`LLM_SEAM_MANUAL.md` §6.4), so a contract-tested transport has still never met a provider and first contact would be in the room; replay does not rescue it, because D9 rules a demo running from saved answers is a scripted demo and deserves to be called one. **And the largest gain is a claim rather than a cost:** with no model present at all, *"the model reads, it does not decide"* (claim 5) stops being asserted and becomes structurally unarguable. **What it costs, stated rather than glossed.** The field evidence was PROSE — Elisandro's ticket arriving by email is the thing two industries volunteered unprompted — so a structured record means a human already did the reading, and *"you automated the easy half"* is a fair question in the room. Answer it honestly and without defence: *intake here is structured; reading prose is the next variant, and its seam shipped 2026-08-16.* It also leaves claim 2 thin in the live demo — origins show `asserted_by_party` and `read_from_source`, never `read_by_model`, so the origin taxonomy shows smaller than it is. That is what the evidence pack is for. **What reverses this — and it is not cost or appetite:** Mauricio's already-scheduled Gate-7 question. If *"is that a judgement call or a rule?"* returns *the hard part is reading the email, not routing the exposures*, then the BEAT is wrong rather than the intake — a larger change than prose-versus-structured, and §2.5's open question rather than this one. ⟹ **The transport is therefore NOT a Phase-7 blocker.** It is a Phase-5/6 prerequisite that arrived early.

10. **[OPENED + RULED 2026-08-17] Does v1 succeed by running a case from a third-party dataset against a live LLM in the room? — NO, and SARA in particular is rejected for the live screen.** The proposal: *"I will consider v1 successful when I can choose a SARA case, give it to an LLM and to MindsOS, and check both results."* **Four reasons, in descending order of force.** (i) **Contamination inverts the beat.** SARA is inside LegalBench, and §2.1 already records the consequence — *"any LLM baseline is contamination-inflated… Accuracy is not the claim. Do not publish a head-to-head table."* On a memorised case the model answers correctly and confidently and MindsOS produces the same answer with more ceremony; every beat in the script is built to win on PROVENANCE and REFUSAL, so this criterion moves the contest onto the one axis this plan says is lost. (ii) **Open decision 9 makes paste-identical input impossible.** SARA cases are prose fact patterns; the demo's intake is ruled STRUCTURED, no model, no transport. The model would read the prose while a human hand-structured the same pattern for MindsOS — which is not `DR_DEMO_SCRIPT.md` prereq 3, and it puts *"you automated the easy half"* on screen as evidence. (iii) **It reverses open decision 6.** Encoding §152 + §7703 is this plan's largest uncosted line item (§7); making v1 depend on it re-plans the ordering ruled 2026-08-14, and does so by unfreezing Phase 7 — the drift mechanism that ruling names in its own text. (iv) **Domain.** §0's table is explicit — evidence pack: US federal tax law; live demo: synthetic claims — and open decision 3 closed on it. SARA has cases, not claims. **What is RIGHT about the proposal, and is kept unchanged:** open decision 6's own sentence — *"the demo must be believed in a room, and that needs the beat working AND at least one number that is not ours."* The disagreement was never whether, only **when** and **on which screen**. The number that is not ours stays Phases 1–3, offline, in the evidence pack. **The live replacement, adopted:** choose the case so **the ROOM holds the ground truth** — arithmetic against a stated policy limit is computed in every head before the page renders. No dataset, no contamination, in domain. That is §0.3's ship B.

---

## 7. Risks

- **The benchmark becomes the product.** Phases 1–6 are more interesting than Phase 7 and pay nothing. Highest risk in this plan.
- **A guard authored after the renderer.** It will pass and it will mean nothing.
- **Encoding cost underestimated.** Nine IRC sections is the largest uncosted line item; the ontology cannot be shortcut because the finder is type-directed and a generic comparator would wire itself everywhere.
- **Reporting accuracy.** Every time it appears without the refusal rate beside it, we compete on the axis we lose.
- **Domain fork.** Running tax and claims in parallel doubles the ontology. One is evidence, one is demo — neither is a product line. **Sharpened 2026-08-11:** the routing beat is claims and the evidence pack is tax, and they share the *ops* and nothing else. **The moment they share a DataState type, this risk has landed.**
- **[2026-08-11] Routing presented as evidence.** It has no dataset support and cannot acquire any (§2.1). It is shown, not measured. A routing accuracy number in the deck is this plan's §0 failure — a green benchmark standing in for a green guard — wearing a different hat.
- ~~**[2026-08-11] The demo depending on a component that does not exist.** No transport, and Gate 7 needs one.~~ **CLOSED 2026-08-16 (PR #169).** Kept as a record of the risk's shape: it was named because the routing beat's own assessment costed the beat and not this. ⚠ **The successor risk is the inverse and is live now** — the plan documents cited a transport that did not exist; they now risk citing a `main` that has moved again. This ship caused five such drifts and fixed them in the same commit; the sixth will not announce itself.
