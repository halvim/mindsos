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

---

## 7. Risks

- **The benchmark becomes the product.** Phases 1–6 are more interesting than Phase 7 and pay nothing. Highest risk in this plan.
- **A guard authored after the renderer.** It will pass and it will mean nothing.
- **Encoding cost underestimated.** Nine IRC sections is the largest uncosted line item; the ontology cannot be shortcut because the finder is type-directed and a generic comparator would wire itself everywhere.
- **Reporting accuracy.** Every time it appears without the refusal rate beside it, we compete on the axis we lose.
- **Domain fork.** Running tax and claims in parallel doubles the ontology. One is evidence, one is demo — neither is a product line. **Sharpened 2026-08-11:** the routing beat is claims and the evidence pack is tax, and they share the *ops* and nothing else. **The moment they share a DataState type, this risk has landed.**
- **[2026-08-11] Routing presented as evidence.** It has no dataset support and cannot acquire any (§2.1). It is shown, not measured. A routing accuracy number in the deck is this plan's §0 failure — a green benchmark standing in for a green guard — wearing a different hat.
- ~~**[2026-08-11] The demo depending on a component that does not exist.** No transport, and Gate 7 needs one.~~ **CLOSED 2026-08-16 (PR #169).** Kept as a record of the risk's shape: it was named because the routing beat's own assessment costed the beat and not this. ⚠ **The successor risk is the inverse and is live now** — the plan documents cited a transport that did not exist; they now risk citing a `main` that has moved again. This ship caused five such drifts and fixed them in the same commit; the sixth will not announce itself.
