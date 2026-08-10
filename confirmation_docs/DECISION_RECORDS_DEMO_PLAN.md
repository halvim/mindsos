---
title: Decision Records — Demonstration Plan
status: Proposed
basis: origin/main 5c6c5db (audited), confirmation_docs/marketing/, BRAIN_ARCHITECTURE_AUDIT.md
date: 2026-08-08
---

# Decision Records — Demonstration Plan

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

Claim 1 has no dataset row on purpose.

---

## 2. Datasets and their roles

### 2.1 SARA — primary
Johns Hopkins StAtutory Reasoning Assessment. Nine IRC sections (§1, §2, §63, §68, §151, §152, §3301, §3306, §7703), lightly edited to be self-contained. **376 hand-crafted cases: 276 entailment, 100 numeric.** Cases are prose fact patterns carrying calendar dates. Statutes carry effective-date clauses and year-dependent dollar amounts.

- **Entailment (276) is the primary half.** §152 dependency and §7703 marital status are multi-condition eligibility tests producing a yes/no with a determining condition — the product's shape. Use these for the Record.
- **Numeric (100) is the arithmetic proof.** A dollar amount is not a Decision Record; it demonstrates threshold, lookup and precedence composing correctly.
- **In-force windows are the versioning test.** A case dated inside one window and a case dated inside another must select different limits, and each Record must name which.
- Prose fact patterns mean SARA exercises the **reading stage** as well as the decision stage. Errors are attributable to a stage — which is itself a demonstration of claim 2.

**Known and to be stated up front:** a hand-built Prolog system already scores well on SARA, and SARA is in LegalBench so any LLM baseline is contamination-inflated. **Accuracy is not the claim.** Do not publish a head-to-head table.

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

**Held until the claims-practitioner conversation.** Domain-independent work does not wait on it.

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
Encode §152 and §7703. Values supplied structured; no adapter.

**Gate 1:** entailment cases answered; confidently-wrong = 0; every Record names the determining condition; G1–G4 green.

### Phase 2 — SARA numeric and in-force windows
Encode §1, §63, §68, §151. Dated cases select limits through the policy store.

**Gate 2:** G5 green — two cases differing only in date name different limits and windows. This is the money sentence, on third-party data.

### Phase 3 — Ablation
Exhaustive single-field ablation across Phase 1 and 2 cases.

**Gate 3:** refusal precision and recall reported; every refusal names the missing item in plain language. `NeedsInput.missing` is a DataState IRI today — G6 covers the translation.

### Phase 4 — `diversity_1..6`
Second area of law. Reuse the ops; register new types only.

**Gate 4:** transfer curve produced; **no new decision op was needed.** If one was, claim 4 is weaker than stated and the deck changes.

### Phase 5 — LLM adapter
ADR first, code second. The adapter is fixed; the model is an external oracle it consults; its output is a typed DataState carrying provenance to the raw input and a recorded extraction uncertainty; it can decline.

Re-run Phases 1–2 with the adapter reading prose.

**Gate 5:** answers identical to the structured run; origins now show read-vs-inferred. That delta is the claim-5 artifact.

### Phase 6 — ContractNLI
Span agreement on extraction provenance.

**Gate 6:** the origin a Record asserts points at the labelled sentence.

### Phase 7 — Live demo *(blocked on the practitioner conversation)*
Five synthetic claims cases; batch pass; one Record per case plus the refusal list on page one.

**Gate 7:** run cold on a laptop three times with no operator intervention. The refusal case fires on cue.

---

## 6. Open decisions

1. **Which half of SARA leads.** Recommend entailment. It is the product's shape; numeric is the arithmetic proof.
2. **Whether the evidence pack ships publicly.** A published SARA result invites the accuracy comparison we do not want. Recommend: cited in the deck, method reproducible on request, no leaderboard entry.
3. **Domain of the live demo.** SARA is tax; the scheduled practitioner is claims. Confirm the demo stays claims and the evidence pack stays tax — or move the practitioner.
4. **Time-box.** Phases 0–4 are the defensible minimum. Set the box before starting, not after Phase 2.
5. **Prior art review before any novelty claim.** A Prolog system solves SARA; "Explainable OpenFisca" exists. Neither has the grounding graph, but both need to be read before the deck asserts novelty.

---

## 7. Risks

- **The benchmark becomes the product.** Phases 1–6 are more interesting than Phase 7 and pay nothing. Highest risk in this plan.
- **A guard authored after the renderer.** It will pass and it will mean nothing.
- **Encoding cost underestimated.** Nine IRC sections is the largest uncosted line item; the ontology cannot be shortcut because the finder is type-directed and a generic comparator would wire itself everywhere.
- **Reporting accuracy.** Every time it appears without the refusal rate beside it, we compete on the axis we lose.
- **Domain fork.** Running tax and claims in parallel doubles the ontology. One is evidence, one is demo — neither is a product line.
