# Decision Records — demo script (v1 design)

Input for the DR lane. Owner-approved design decisions from the GTM thread,
2026-08-15. Prerequisites and beat structure below; the lane owns the build.

**Audience:** small operators (claims/ops/owner). No architecture vocabulary,
ever (G6 discipline extends to the spoken track). Buyer's words: claims,
desks, hallucinations, "who decided this and why."

**Setup:** one laptop, two screens visible to the room.
- **Screen A (MindsOS):** two panels — left, *what arrived* (the claim,
  human-readable); right, *the Decision Record page* as it is produced
  (document layout — header, case label, printable; a layout OVER
  `dr_render` output, never a second source of facts).
- **Screen B (LLM):** a frontier LLM chat, **live**, given the same data
  verbatim at each beat. No screenshots, no canned replies — a rigged
  comparison hands back "AI can do that."
- Cold start, no operator intervention (Gate 7 discipline).

⚠ **COMMITTED + AMENDED 2026-08-17.** This file was UNTRACKED until now, while
being the operative text for Phase 7's frozen scope (demo plan §0.2 amendment
1) — the shape RULES §5 exists to refuse. **The beats are BUILT** and were
performed end to end for the first time on 2026-08-17. **Read
`DR_DEMO_WALK_2026-08-17.md` beside this file**: it records what each beat put
on screen and the six gaps between that and what is written here. Which case
drives which beat is in `decision_records_demo/README.md` on
`demo/decision-records`; run one with `dr_demo_beat.py <n>`.

**Hard prerequisites (dated, not optional):**
1. ~~**LLM transport built; S-2 settled BEFORE it is written**~~ — **DEAD
   2026-08-16.** Open decision 9 rules the intake **STRUCTURED**: the demo runs
   with **no model and no transport**, so this is satisfied by there being no
   model at all rather than by building one. The transport shipped anyway
   (PR #169), is a Phase-5/6 prerequisite rather than a demo one, and is **not
   on the core this demo pins**. D9 still governs any future prose variant.
2. Record page document layout (consumes the text renderer's facts).
3. Comparison harness: paste-identical data to the LLM at each beat.
   ⚠ **RULED 2026-08-17 (owner): "identical" means PASTING THE STRUCTURED
   RECORD TO THE MODEL VERBATIM.** With intake structured (decision 9) there is
   no prose to hand it, and this is satisfiable for claims — unlike SARA, where
   open decision 10 correctly calls paste-identical input impossible, because
   those are prose fact patterns. **It sharpens beat 5 for free:** the model
   reads the same intake the system reads, and still cannot say which edition
   governed. The paste files are BUILT WITH SHIP C, one per beat, generated
   from the same fixture the case runs so the two screens cannot drift.
4. Rehearse Screen B ≥5 runs per beat; beats are designed so EITHER LLM
   branch proves the point, but narration must be ready for both.

---

## Beats (~12 min)

**0 · The pain (30s, no product).** "A claim arrives. Someone you pay reads
it and decides which desk gets it. When it lands on the wrong desk, nobody
notices for days — and a year later, nobody can say why it went there."

⚠ **TRANSFER, one sentence, ruled 2026-08-17** (plan §0.3 item 13) — say it
here and nowhere else: *"That's a claims example — the shape is the same
wherever work arrives and a person decides where it goes."* This is a claim
about the PROBLEM's generality, which two unrelated industries volunteered
unprompted (plan §2.5). **It is not a claim that this system generalises** —
that sentence does not exist and must not be improvised.

**1 · One claim, two desks.** Multi-exposure case: vehicle exposures →
routine desk; injury exposure → specialty unit. One document, several
decisions, one Record each — *question → answer → therefore*.
*Screen B:* same case to the LLM. It will likely route plausibly — say so:
"Both look right. Keep watching."

**2 · The refusal, beside an answer.** Same claim, one more exposure:
"Cannot tell whether this needs the specialty unit — missing: [named item,
plain words]." A routed sibling and a refusal on the same page.
*Screen B:* if the LLM answers → confidently wrong, on screen. If it
refuses → ask both "what exactly is missing?" — generic prose vs the named
item. Either branch wins.

**3 · The missing document.** The punchline case: refusal that names what to
go fetch, **and says what it could not do because of it** — *"settling the
claim on what was filed → cannot be settled"* (ship B). Framed as
work-routing: "it tells your team what to get, not just that it can't."

**4 · The policy changed mid-claim.** ⚠ **RE-CUT by ship B, and again by the
verdict change ship C carries.** One claim of 400,000, assessed as of two
dates: *exceeds the limit in force — 350,000 payable of 400,000 claimed* under
the 2023 edition, and 375,000 payable under the 2024 one, each Record naming
its edition and the window it was in force.

⚠ **TRANSFER, the second and last one, ruled 2026-08-17** — and it is a
QUESTION about their system, never a statement about ours: *"Your rules changed
in March — could your system tell you which version it applied in February?"*
Ask it, then run the beat and let the Record answer it. Versioned rules are the
most universal thing this demo shows.

⚠ **Do NOT sell the arithmetic.** The room checking 400,000 against 350,000 is
how they VERIFY the answer; it is not the claim, and a room that hears you
praise the subtraction has been told a spreadsheet could do this. **The claim
is which limit applied** — two editions, selected by a date, the window named —
**which input decided**, and, a year later, which edition it decided under.
Quiet beat; the compliance buyer retells this one.

**5 · Unplug the model.** ⚠ **RE-CUT 2026-08-16/17 — there is nothing on OUR
side to unplug** (decision 9). The visible action lives on **Screen B**: close
the frontier LLM, then re-run beat 1 on Screen A — same claim, same Record,
identical to what the room watched a minute earlier. *The model was never in
this path; here is the same answer with it gone.* ⚠ **Do not show the guard
output.** The three checks that prove the absence
(`test_dr_no_model_guards.py`) use the exact vocabulary G6 bans from the page:
they are the evidence you offer if asked, never the show. ~~Feed the same case
as structured intake. MindsOS routes and records identically.~~
One line, only if asked "isn't this RAG?": *"RAG helps a model answer
better. Here the model never answers — it reads. The decision, and the
record of it, is ours either way."* Then stop talking.

**6 · The closer — a year later.** Kill the app, visibly. "It's next year.
The auditor asks why." Rerun `--from-root`: the same Record from the store
alone — including "Decided date: not available from stored evidence,"
narrated as the product: "it won't even claim a date it can't prove."
*Screen B:* open a **new chat**, ask it to retrace its earlier decision.
Branch 1: "I don't have access to previous conversations" → *the reasoning
is gone.* Branch 2: it confabulates a rationale → show it cites nothing
verifiable, line by line, against the Record where every line traces.
Either branch is the thesis. This is the lawyer-a-year-later story, run
live.

**7 · The ask (two-meeting close — no live rule-authoring, ever).**
"Send us your routing rules and one anonymized claim this week. Next
meeting, we route YOUR claim under YOUR rules, in front of you."
Rules encoding is offline expert work today — framed as the pilot's first
deliverable, priced into onboarding, never faked live.

---

## Live edits, and what the comparison actually is

⚠ **ADDED 2026-08-17 by owner ruling** (demo plan §0.3 amendments 4, 5, 6, 7).
This section governs every beat above; where it and a beat's *Screen B* line
disagree, this section wins.

**What the room may change, and what it may not.** The claim and the policy are
DATA and are edited live, in front of them, in a file that reads like a record
(`key: value`, a claim form, an edition with dates). Routing and decision LOGIC
are not editable and never will be live — beat 7's rule is unamended.

**Say this at the edit, once:** *"You are changing what arrived and what the
policy says — not how it decides. That is expert work, and it is what we ask
for at the end."*

**The parry — rehearse it, it is the strongest moment available.** When someone
asks for a rule change (*"make severe injuries go to the routine desk"*),
**decline, live**: that is not an input, it is rule-authoring, and it is done by
your people offline and delivered as the pilot's first work. A system that
refuses on stage is the whole product argument, performed instead of claimed.

**The comparison is NOT accuracy.** On a claim this room can check, the model
will also be right, and a correct-answer contest is one we lose on our own
terms (plan §2.1, §3 — no accuracy number without the refusal rate beside it;
no routing numbers at all). **Compare reaction to a change:**

1. Run the beat. Both screens answer.
2. **Change an AMOUNT** — the edition's stated limit, or let them pick the
   claimed amount. ⚠ **RE-CUT 2026-08-17: dates are NOT editable** (plan §0.3
   item 4), so this is not "change the policy edition" and must not be said
   that way; you are changing what an edition SAYS, not which edition applies.
3. Re-run BOTH.
4. **What actually changes on our side, and say only this:** the limit on the
   Q line, the payable line, and — if they set the limit at or above the claim
   — **which fact the page says decided it**, because the limit stops binding
   and the Record starts crediting the claimed amount instead. **The edition
   line does not move on an amount edit**, and on that equality edit it leaves
   the page: the Record only cites a source where the store holds one, and
   nothing sourced decided. The model gives a different answer and cannot tell
   you which policy it used, or that anything changed at all.

This holds **even when the model is right**, which is the property every other
framing lacks. Do not reach for a case the model gets wrong; that is luck, and
the room can smell it.

**The room does not supply its own claim in this meeting.** They choose a VALUE
inside a case we control. Their own claim is beat 7's ask, run next meeting,
rehearsed against their rules.

**What every answered Record shows.** The fact that DECIDED — *"the specialty
injury unit, because the assessed severity is severe"* — not every fact read. A
page that lists every read is a page the room stops following.

---

## Ship D — the live prose beat. NOT BUILT; do not speak it

Reuses beat 2 with ONE reader swapped, so the two pages differ in origin and
nothing else. **Until it is green, nobody says "the model reads" in a room**
(plan §0.3 item 10).

- **Beat card, verbatim when it runs:** *"live-provider, rehearsal-gated;
  everything else you saw runs cold."*
- **The disclosure, spoken BEFORE the run and never after** (owner ruling
  2026-08-17, the courted refusal): *"this email never states the severity;
  watch what each does."* Undisclosed, the beat is not run.

## Do not (from field evidence + plan)
- **No third transfer line without a ruling.** Exactly two exist (beats 0 and
  4), both are the owner's, and both are QUESTIONS or claims about the
  PROBLEM — never claims that this system generalises. All thirteen L4 catalog
  capacities are placeholders, so *"it could do this anywhere"* is an
  over-claim the demo cannot show. If beats 2 or 3 visibly fail to land on a
  non-claims room, that is evidence for a second ruling, not licence to
  improvise one live.
- No architecture, no edge/on-device, no "patch"/"layer" language.
- No accuracy number without the refusal rate beside it; no routing
  accuracy numbers at all (routing is shown, not measured — plan §1).
- No invented taxonomies: exposure routing stays on the Guidewire-sourced
  model (owner decision 2026-08-15 — external answers are validation or
  reversal when they arrive, never gates).
- The demo ends at the ask. Questions about how it works route to the
  technical annex meeting, where the IT inquisition is welcome.
