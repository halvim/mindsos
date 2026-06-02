# MindsOS Demo Examples — Synthetic Domain Test Suite

**Date:** 2026-04-30
**Origin:** WSD goal-finalization chat (forked from WSD design chat).
**Purpose:** Concrete test scenarios for demonstrating the MindsOS learning loop against current LLMs. Each example pairs (a) an LLM test prompt that targets a structural LLM weakness, (b) a step-by-step MindsOS teaching plan, and (c) the narrative arc(s) the example exercises.

---

## Framing (read first)

### Why synthetic domains

LLMs are good at facts. Context-injection lets them answer almost any factual question in-conversation. The MindsOS differentiator is not *knowing things LLMs don't know* — it's *operations on knowledge that LLMs structurally need retraining to perform*: persistent updates across sessions, counter-training-prior overrides, calibration changes, behavioral rule adoption, knowledge versioning with rollback, federated/cross-user learning, auditable provenance, and contradiction detection at add-time.

These differentiators surface only when both systems start equally ignorant of the domain. Real-world domains contaminate the test — LLMs already know parts of them. **Every example here uses a fully synthetic domain so neither system has prior knowledge.**

### How to read these as commercial value

Each synthetic domain is a stand-in for *proprietary enterprise knowledge*: your firm's internal compliance rules, your hospital's protocols, your jurisdiction's specific regulations, your product's pricing logic. The value proposition demonstrated is "live teach + audited reasoning + persistent learning over private knowledge." The toy domain is the demo medium; the buyer's takeaway is the loop.

### Structural LLM-resistance test types

When testing an LLM on these examples, target *structural* weaknesses, not factual ones:

- **Multi-rule consistency.** Provide N rules in context. Ask M sequential questions where each requires applying a different subset. Track whether the LLM correctly applies *all* relevant rules consistently across all questions. LLMs typically drift after 6-8 turns.
- **Counter-prior persistence.** Provide a rule that contradicts the LLM's likely training prior. Test that it applies the rule persistently across questions, not just immediately after being told. LLMs frequently revert.
- **Faithful chain reporting.** Ask the LLM to show its work after answering. Verify whether the steps it claims correspond to actual computation (compare to ground-truth derivation). Chains-of-thought are often post-hoc rationalization.
- **Persistence across sessions.** Test the LLM in a fresh session without re-providing the context. It will not have learned anything.

### Narrative arc reference

- **A** — Persistence across sessions (close + reopen).
- **B** — Compounding teaching (layer dependent knowledge).
- **C** — Counter-intuitive rule override (resists training prior).
- **D** — Rollback / supersedes (correction with audit).
- **E** — Contradiction detection at add-time.
- **F** — Cross-user promotion (Local→Global).
- **G** — Calibration shift via teaching.
- **H** — TC3-style proof chain (entailment with auditable derivation).

### Combined demo arc (recommended for primary investor demo)

The strongest single demo combines multiple arcs into one continuous flow: **B → C → H → A → D → E**. Pick one example below and execute the combined arc against it. This stress-tests the whole learning loop in 8-12 minutes.

---

## D-Synth-1 — Micro-jurisdiction rule system

Setting: the fictional Kingdom of Atlantis has its own ruleset. None of it matches any real jurisdiction.

### Example 1.1 — Citizenship eligibility

**Task.** Given a person's properties (place of birth, parents' citizenship status, residency duration, criminal record), determine if they qualify for Atlantean citizenship.

**LLM test prompt.**
> *"The Kingdom of Atlantis has these citizenship rules: (R1) Anyone born within Atlantis territory is an automatic citizen. (R2) Children of at least one Atlantean citizen parent are eligible by descent. (R3) Foreign nationals with 7+ years continuous residency and a clean criminal record can naturalize. (R4) Exception to R1: children of foreign diplomats born in Atlantis are NOT citizens. (R5) Exception to R2: if the citizen parent's citizenship was revoked before the child's birth, descent claim is invalid. (R6) Exception to R3: any criminal conviction in the past 10 years bars naturalization. (R7) Exception to R3: refugees with valid asylum status only need 4 years residency. (R8) Diplomatic-immunity-revocation triggers reapplication of R4 retroactively to children.*
>
> *Now answer these 8 cases sequentially:*
> *Case A: Person born in Atlantis to two diplomat parents who later defected and renounced diplomatic status. Citizenship?*
> *Case B: Person whose mother was Atlantean but renounced citizenship before the child's birth. Citizenship?*
> *Case C: Refugee, 5 years residency, clean record. Citizenship?*
> *Case D: 8 years residency, theft conviction 6 years ago. Citizenship?*
> *Case E: Born to Atlantean father (citizen at birth), foreign mother. Citizenship?*
> *Case F: 10 years residency, refugee status, no record. Citizenship?*
> *Case G: Diplomat's child, parents' immunity was revoked when child was 5, child now 12 lived in Atlantis whole life. Citizenship?*
> *Case H: Born in Atlantis but parents were both refugees, not diplomats. Citizenship?*

LLMs frequently apply R1-R3 correctly but miss R4 on case A (the rule says diplomats *born* under diplomatic status, but interaction with later defection is ambiguous), miss R8's retroactive interaction on case G, and conflate R6 and R7 across cases.

**MindsOS teaching steps.**
1. Add `Person` schema to local L2 lexicon: properties (birthplace, parents[], residency_years, criminal_record, asylum_status, parents_diplomatic_status_history).
2. Add `Atlantean_citizenship` concept node and `citizenship_status` enum (citizen / eligible / ineligible) to local concepts graph.
3. Add 8 axioms (R1-R8) to local `world-axioms` graph, each linked to its evaluation conditions and outcome.
4. Add a `derive_citizenship_status` capacity (composed path) that traverses input person properties → applies axioms in priority order → produces calibrated status with derivation trace.
5. Test cases A-H. Audit trail shows for each case which axioms fired in which order.
6. Re-test in a fresh session (Arc A demonstration).
7. Add a corrected R8 ("retroactivity does not apply if the child has already received another citizenship") via supersedes; show case G now resolves differently with the audit trail showing the rule change (Arc D).
8. Attempt to teach a contradictory R9 ("diplomat children are always citizens regardless of R4") — system detects conflict with R4, surfaces to admin (Arc E).

**Arcs exercised.** B (compounding axioms), H (entailment proof per case), A (persistence test), D (rollback/supersedes on R8), E (contradiction detection on R9).

---

### Example 1.2 — Tax bracket with profession exceptions and counter-intuitive rules

**Task.** Compute Atlantean income tax for a given person.

**LLM test prompt.**
> *"Atlantean income tax rules: (B1) 0-25k income: 0% tax. (B2) 25k-75k: 15%. (B3) 75k-200k: 28%. (B4) 200k+: 40%. (E1) Teachers receive a 50% discount on their first 50k of income, regardless of bracket. (E2) Farmers receive a flat 8% on all income up to 150k, then standard brackets above. (E3) Newly-naturalized citizens (citizenship < 5 years) get a one-bracket-down treatment for first 3 years. (E4) Exception to E3: this benefit is forfeited if income exceeds 250k. (E5) Children of military veterans receive a 10% credit on total tax owed, capped at 5k.*
>
> *Compute final tax for these cases sequentially (show all steps):*
> *Case A: Teacher, 80k income, 10-year citizen.*
> *Case B: Farmer, 180k income, citizenship 2 years.*
> *Case C: Engineer, 280k income, citizenship 4 years (naturalized), military-veteran father.*
> *Case D: Teacher who is also a farmer (dual occupation), 60k from teaching + 90k from farming.*
> *Case E: Newly-naturalized (year 2) doctor, 260k income, mother is a military veteran.*
> *Case F: Teacher, 30k income, mother and father both military veterans (both qualify for E5)."*

LLMs typically apply E1 correctly on case A but mishandle the dual-occupation in case D, miss the E4 exception on case E (forfeiture), and double-apply E5 on case F.

**MindsOS teaching steps.**
1. Add `Income`, `Tax`, `Profession`, `Citizenship_age` types to local lexicon.
2. Add brackets B1-B4 as axioms in `world-axioms` with explicit threshold conditions.
3. Add exceptions E1-E5 as axioms with their own conditions and override priority. E1 (teacher 50% discount on first 50k) is the counter-intuitive one — most tax codes don't structure incentives this way (Arc C target).
4. Add `compute_tax` capacity (composed path): identify applicable bracket → apply profession exception → apply citizenship-age exception → apply credits → produce tax + audit trail showing every rule fired.
5. Test cases A-F. Each output includes the calibrated tax and the rule-firing chain.
6. Test the LLM with the same prompts; demonstrate drift on cases D, E, F.
7. Counter-intuitive demonstration: show that LLM-in-context on case A may apply E1 correctly, but in case F (where the discount + the credit interact), LLM may mis-apply or revert toward standard tax logic. MindsOS applies consistently.

**Arcs exercised.** B, C (E1 counter-intuitive structure), H (proof chain for compute_tax), G (calibration when income falls near a bracket threshold).

---

### Example 1.3 — Voting rights with policy update

**Task.** Determine if a person can vote in Atlantis.

**LLM test prompt.**
> *"Atlantean voting rules: (V1) Citizens 18+ may vote. (V2) Citizens with felony convictions in the past 10 years cannot vote. (V3) Foreign residents with 15+ years cannot vote but may participate in advisory referendums. (V4) Citizens with active military duty obligations may vote remotely. (V5) Homeowners pay an additional vote-tax of 50 atlantean credits per election."*
>
> *Apply these to: 17-year-old citizen, 19-year-old citizen with theft conviction 8 years ago, 16-year-old citizen of Atlantean parents living abroad, 60-year-old foreign resident of 20 years."*

(LLMs handle these with varying consistency.)

**MindsOS teaching steps.**
1. Add voting rules V1-V5 to local `world-axioms`.
2. Add `voting_eligibility` capacity. Test the four cases.
3. **Arc D demonstration:** "Atlantis just lowered the voting age to 16. Update V1." Add V1' as the supersede; old V1 marked superseded. Re-query the 17-year-old and 16-year-old cases — different outputs, audit trail shows the rule transition with timestamps.
4. **Arc E demonstration:** Try to add a new rule: "Voting age is 21." System detects contradiction with V1' and surfaces both to admin for resolution.
5. **Arc F demonstration (if multi-user setup is available):** Promote V1' to Global; another user instance immediately sees the new voting age applied in their queries.

**Arcs exercised.** D, E, F, H.

---

## D-Synth-2 — Fictional company compliance policy

Setting: TerraSynth Inc., a fictional company with internal expense and approval rules.

### Example 2.1 — Transaction approval routing

**Task.** Given a transaction (amount, type, region, requester role), determine which approval(s) are required.

**LLM test prompt.**
> *"TerraSynth approval policy: (A1) Transactions under $500: requester self-approves. (A2) $500-$5000: direct manager approves. (A3) $5000-$50000: department head approves. (A4) $50000+: VP approves. (A5) Cross-border transactions add Compliance Officer approval regardless of amount. (A6) Capital expenditures require CFO sign-off above $10000. (A7) Exception: marketing-team transactions under $2000 self-approve regardless of A1-A4. (A8) Exception: emergency procurement (declared) skips A2 and A3, escalating directly to A4. (A9) Foreign-currency transactions add CFO above $5000 in addition to A6's CapEx rule. (A10) New-employee transactions (employee tenure < 90 days) require an additional skip-level approver above their direct manager.*
>
> *For each transaction, list ALL required approvals in order: T1: $4500 marketing supplies, US, regular tier-1 employee. T2: $7500 office equipment, EU subsidiary (cross-border), department-head requester, capital expenditure. T3: $850 lunch event, marketing, US, employee tenure 30 days. T4: $80000 emergency server purchase, US, IT director, declared emergency. T5: $12000 software license, multi-region (US + EU), 2-year-old engineer requester, foreign-currency. T6: $400 stationery, marketing, new employee (45 days), US."*

LLMs frequently miss A10 on T6 (new-employee skip-level), miss A9's interaction with A6 on T5, and mis-apply A8's emergency override on T4.

**MindsOS teaching steps.**
1. Add `Transaction` schema (amount, type, region, requester, requester_tenure, currency, capex_flag, emergency_flag).
2. Add 10 approval axioms with priority order and override semantics.
3. Add `route_approval` capacity that walks transaction properties through the rule chain and produces an ordered list of required approvers + audit trail.
4. Test T1-T6. Each output names the approvers, the rules that fired, and the order.
5. Test the same against an LLM in-context; show drift on T5 and T6.
6. **Arc A:** close session, reopen, re-query T6. Persistent.
7. **Arc B compounding:** add a new rule A11 ("Sustainability initiatives under $100k can self-approve at department-head level regardless of A4") and an T7 case requiring it. The system uses the new rule and existing rules together.

**Arcs exercised.** A, B, H. Strong narrative for an enterprise audience: this is exactly how internal company policies work.

---

### Example 2.2 — Expense reimbursement with edge cases

**Task.** Given an expense receipt, determine reimbursable amount and category.

**LLM test prompt.**
> *"TerraSynth expense rules: (X1) Meals: max $50 per person, only with valid attendee list, alcohol not reimbursable. (X2) Hotels: standard room rate only; upgrades require pre-approval. (X3) Flights: economy class only for trips under 6 hours; business class allowed for 6+ hour flights with prior approval. (X4) Client gifts: max $50 per recipient, max $200 per quarter per requester. (X5) Sunday work-related expenses are reimbursed at 1.5x rate (the company's 'commitment bonus' rule). (X6) Foreign-currency expenses: convert at the date-of-purchase exchange rate, not the date-of-submission rate. (X7) Round-trip ground transport above $200 in a single day requires receipts and justification. (X8) Conference fees fully reimbursed if the requester presents at the conference; 75% otherwise. (X9) Exception: alcohol IS reimbursable at client dinners with stated business purpose, max $30 per attendee.*
>
> *For each expense, compute reimbursable amount:*
> *E1: Sunday business dinner, 4 attendees, $280 total food, $90 wine, attendee list provided, business purpose noted.*
> *E2: 8-hour flight, business class, $3500, no prior approval logged.*
> *E3: Q3 client gift to Vendor X: $35; previous gifts to Vendor X this quarter total $180.*
> *E4: 5-day hotel in EUR, €750 total, exchange rate at purchase 1.10, at submission 1.05.*
> *E5: Client lunch Sunday + alcohol, 3 attendees, $100 food, $80 cocktails, business purpose noted."*

LLMs miss the X5+X9 interaction on E1 (Sunday rate × alcohol-permitted-at-client-dinner), misapply X3 to E2 (ambiguous: business class on long flight without prior approval — not reimbursable per X3), and may apply submission-rate on E4 instead of purchase-rate.

**MindsOS teaching steps.**
1. Add `Expense` schema and category taxonomy.
2. Add 9 reimbursement axioms.
3. Add `evaluate_expense` capacity producing (reimbursable_amount, breakdown, rules_fired).
4. Test E1-E5. Each produces a calibrated reimbursement with full breakdown.
5. **Arc C:** X5 (Sunday 1.5x rate) is counter to most real-world expense policies — a likely LLM-prior-resistance target. Verify LLM either ignores X5 or fails to combine it with X9.
6. **Arc G:** for E2 (ambiguous because the flight is long enough but no approval logged), MindsOS produces a calibrated "0.6 confidence reimbursable / 0.4 confidence requires retroactive approval review" output rather than committing.

**Arcs exercised.** B, C, G, H.

---

## D-Synth-3 — Custom academic eligibility ruleset

Setting: Avalon University, a fictional institution with custom scholarship and admission rules.

### Example 3.1 — Scholarship eligibility multi-criteria

**Task.** Given a student profile, list all scholarships they're eligible for.

**LLM test prompt.**
> *"Avalon University scholarships: (S1) Excellence Award: GPA ≥ 3.8, no other criteria. (S2) STEM Innovators: GPA ≥ 3.6 + STEM major. (S3) First-Generation Pathway: first-gen college student (no parent has bachelor's) + GPA ≥ 3.4 + financial need (family income ≤ $80k). (S4) Athletic Honors: varsity athlete + GPA ≥ 3.0. (S5) Global Citizens: international student + GPA ≥ 3.5 + bilingual. (S6) Service Award: 200+ documented community service hours + any GPA. (S7) Combined Awards exclusion: cannot hold S1 + S2 simultaneously (student must choose). (S8) Exception: S3 stacks with all others. (S9) Renewal: any scholarship requires GPA maintenance ≥ 3.5 (regardless of original threshold) for renewal in subsequent years. (S10) Late-application override: applications received after Sept 15 are evaluated against next-year cohort instead, and S5 becomes ineligible.*
>
> *For each student, list all eligible scholarships:*
> *St1: GPA 3.85, biology major, varsity track, 50 service hours, parents both high-school grads, family income $40k, applying September 2.*
> *St2: International student, GPA 3.7, English+Mandarin+Korean, applying September 30.*
> *St3: First-gen, GPA 3.5, history major, family income $75k, 220 service hours.*
> *St4: GPA 3.9, math major, applying for renewal year 2 (current GPA 3.4)."*

LLMs typically catch the obvious eligibilities but miss S7's exclusion on St1, miss S10's late-application effect on St2, mis-apply S8 stacking on St3, and miss S9's renewal threshold on St4.

**MindsOS teaching steps.**
1. Add `Student`, `Scholarship`, eligibility-condition schemas.
2. Add S1-S10 as axioms with their constraints and exclusions.
3. Add `find_eligible_scholarships` capacity producing the list + per-scholarship eligibility chain.
4. Test St1-St4.
5. **Arc F** (if cross-user setup): a different evaluator-user queries the same student → same answer with same audit; demonstrates that scholarship knowledge promoted to Global benefits all evaluators consistently.
6. **Arc B:** add a new scholarship S11 mid-demo for a hypothetical student St5 — system uses it without retraining.

**Arcs exercised.** B, F, H.

---

### Example 3.2 — Admission decision with mid-process rule update

**Task.** Determine admission decision for a candidate.

**LLM test prompt.**
> *"Avalon admission rules: (M1) Auto-admit: GPA 3.9+ + standardized test top 5%. (M2) Standard track: GPA 3.5+ + test top 30% + essay quality 'good'+. (M3) Holistic review: GPA 3.0-3.5 + extenuating circumstances documented. (M4) Auto-reject: GPA below 3.0 unless M3 applies. (M5) Major-specific override: STEM majors require additional math test ≥ 80th percentile, regardless of M1-M3. (M6) Legacy candidates (parent attended Avalon): one tier of relaxation on test percentile (e.g., 5% becomes 10%, 30% becomes 40%). (M7) Override: athletes with verified D1 scholarship offers from competing schools can use M3 path even with GPA 2.7+."*
>
> *For each candidate, determine: ADMIT / WAITLIST / REJECT.*
> *C1: GPA 3.95, test 4th percentile, biology major (STEM), math test 75th percentile.*
> *C2: GPA 3.6, test 25th percentile, English major, essay 'good'.*
> *C3: GPA 2.8, athlete with D1 offer from rival, basketball, no extenuating documents.*

**MindsOS teaching steps.**
1. Add admission rules M1-M7 to `world-axioms`.
2. Add `admission_decision` capacity with audit-traced decision per candidate.
3. Test C1-C3. C1 should reject (M5 fails despite M1's auto-admit prelude); C2 should standard-admit; C3 should holistic-review (M7 override).
4. **Arc D:** mid-demo, "Avalon's board just relaxed M5: math test required at 70th percentile instead of 80th." Add M5' supersede. Re-query C1 — now admitted. Audit shows the rule change.
5. **Arc E:** try to teach a contradictory M5'' (STEM majors require 90th percentile math); system detects conflict with M5' and surfaces both.

**Arcs exercised.** B, D, E, H.

---

## D-Synth-4 — Custom game state evaluator

Setting: a small fictional card/board game called "Threnody" with simple but distinctive rules.

### Example 4.1 — Threnody legal moves

**Task.** Given a Threnody board state, list all legal moves.

**LLM test prompt.**
> *"Threnody is a 2-player game on a 5×5 grid. Pieces: King (K), Mage (M), Pawns (P), 4 of each per player. Rules: (G1) Kings move 1 square in any direction. (G2) Mages move any number of squares in straight lines (orthogonal or diagonal) but cannot pass over other pieces. (G3) Pawns move forward 1 square; capture diagonally forward. (G4) Special: a pawn that reaches the opponent's back row promotes to a Mage. (G5) Special-counter: any pawn promotion can be 'denied' if the opposing King is adjacent to the promotion square (the pawn instead disappears from the board). (G6) Mages have a 'banishment' ability: once per game, a Mage can remove an opponent's piece adjacent to it without moving (uses the Mage's turn). (G7) Kings cannot move into check (a square attacked by an opposing piece). (G8) Exception: if the only legal move is into check, the player must take it (game continues; winning conditions resolve). (G9) The Mage's banishment cannot target the opposing King.*
>
> *Given board: White King at e1, White Mage at c3 (banishment unused), White Pawns at b2, c2, d2, e2. Black King at e5, Black Mage at c4 (banishment used), Black Pawns at a4, b4, d4. White to move. List all legal moves."*

LLMs frequently miss G5's promotion-denial, mis-apply G6 (banishment is once-per-game; LLMs may suggest an already-used banishment), and miss the G7-G8 interaction in tight states.

**MindsOS teaching steps.**
1. Add `Threnody_board` schema, piece types, position grid.
2. Add movement and capture rules G1-G3 to `world-axioms`.
3. Add special rules G4-G9.
4. Add `legal_moves` capacity that, given a board state, returns the full move list.
5. Test on the example state. Output enumerates moves with the rules supporting each.
6. **Arc B:** add a new rule G10 mid-demo (e.g., "Pawns adjacent to a friendly Mage move 2 squares"); system applies without retraining.
7. **Arc H:** for a complex state, the audit shows the proof-chain: this move is legal because G3 + (no G5 trigger) + (G7 doesn't block).

**Arcs exercised.** B, H.

---

### Example 4.2 — Threnody win-condition evaluator

**Task.** Given a board state, determine if the position is win/loss/draw/ongoing.

**LLM test prompt (continuing Threnody):**
> *"Win conditions: (W1) Capture opposing King = win. (W2) Stalemate (current player has no legal moves and is not in check) = draw. (W3) Insufficient material (only Kings + at most one Mage between both players) = draw. (W4) Three-fold repetition = draw. (W5) Counter-intuitive special: if a player has lost both Mages but still has 4+ Pawns, they earn a 'desperate strike' bonus turn each round (extra move), to reflect Threnody's lore of a trampled army's last stand. (W6) Counter-intuitive special: a King reaching the opponent's back row triggers immediate win regardless of remaining pieces ('royal advance' victory).*
>
> *Evaluate the following position: White King at e8 (Black's back row), White Mage at c3, White Pawns at b2, c2, e2, d2, f2. Black King at d5, Black Pawns at a4, b4, c4, d4. Black to move. State: ?"*

The W6 (King-on-back-row = win) is counter-intuitive (real chess has no such rule); LLMs typically miss it and continue evaluating piece counts.

**MindsOS teaching steps.**
1. Add win-condition axioms W1-W6.
2. Add `evaluate_position` capacity.
3. Test the example. MindsOS returns "WHITE WINS via W6 (royal advance)"; audit shows W6 fired and other conditions were not evaluated.
4. **Arc C demonstration:** test LLM with the same prompt; LLM typically continues conventional evaluation, missing the royal-advance rule despite it being in context.
5. **Arc G:** for an ambiguous state (e.g., insufficient material plus desperate strike active), MindsOS produces calibrated probabilities rather than a single answer.

**Arcs exercised.** C (royal advance counter-intuitive), G, H.

---

## D-Synth-5 — Made-up insurance / claim policy

Setting: Aegis Insurance Co., a fictional insurance product with custom coverage and exclusions.

### Example 5.1 — Claim coverage determination

**Task.** Given a submitted claim, determine: covered / partially covered / denied, with reason.

**LLM test prompt.**
> *"Aegis Standard policy: (P1) Property damage from natural causes covered up to $50k. (P2) Theft covered up to $10k with police report. (P3) Liability up to $100k for accidents on insured premises. (P4) Personal injury up to $25k for accidents involving the insured directly. (P5) Exclusion: damage from neglect (lack of maintenance) not covered. (P6) Exclusion: claims filed > 30 days after incident not covered, except (P7) emergency situations (fire, flood) which extend to 90 days. (P8) Counter-intuitive: 'good neighbor' clause — damages caused to or by adjacent properties under shared maintenance agreements covered at 75% rate even if normally excluded by P5. (P9) Multi-claim discount: third claim in a 12-month period reduces coverage to 50% of stated limits. (P10) Exception to P9: weather-event claims do not count toward the multi-claim threshold. (P11) Calibration clause: claims with incomplete documentation are processed at 60% confidence pending review (Aegis specific term).*
>
> *Evaluate each claim:*
> *Cl1: Roof damage $35k from a hurricane (declared natural disaster), filed 45 days post-incident, second weather claim this year, full documentation.*
> *Cl2: Theft $8k, police report attached, third claim this year (previous two: water damage from burst pipe, and a fire), filed 5 days post-incident.*
> *Cl3: Garage damage $12k, owner admits 5 years of unmaintained roof leaks contributed, but the immediate cause was a tree falling during a storm.*
> *Cl4: Adjacent property damage $20k from a shared fence collapse, both owners had a maintenance agreement, owner had partially neglected their portion.*

LLMs miss P10's exception on Cl2 (weather doesn't count, so this is only the second non-weather claim — full coverage, not 50%), misapply P9 vs P10, miss the P5/P8 interaction on Cl4 (the "good neighbor" 75% override), and may miss P7's hurricane extension on Cl1.

**MindsOS teaching steps.**
1. Add `Claim`, `Policy`, `Incident_type` schemas.
2. Add coverage axioms P1-P11 with priorities and override semantics.
3. Add `evaluate_claim` capacity producing (decision, reimbursement_amount, fired_rules, calibration).
4. Test Cl1-Cl4 with full audit.
5. **Arc C:** P8 (good-neighbor 75% override) is counter to common insurance norms — verify LLMs miss or misapply.
6. **Arc G:** P11 (incomplete documentation = 60% confidence) is the calibration arc — Cl4's partial neglect creates a 0.6 confidence "75% via P8" / 0.4 confidence "denied via P5". MindsOS surfaces both with weights; LLM commits to one.

**Arcs exercised.** B, C, G, H.

---

### Example 5.2 — Premium adjustment after life event with retroactive correction

**Task.** Given a policyholder's life event, recompute their premium.

**LLM test prompt.**
> *"Aegis premium adjustment rules: (Q1) Marriage: -10% on combined household policy. (Q2) New child: +5% per child up to 3 children, then +2% per additional. (Q3) Major accident claim: +15% for 3 years following the claim. (Q4) Career change to a high-risk profession (firefighter, race car driver, etc.): +25%. (Q5) Move to a low-risk zip code (Aegis-classified): -8%. (Q6) Exception: military deployments (active service) freeze any pending premium increases for the deployment duration. (Q7) Counter-intuitive: birthday year ending in 7 (lucky-year clause): -3% one-time. (Q8) Stacking: discounts and surcharges are multiplicative, not additive (e.g., -10% then +5% gives 0.9 × 1.05 = 0.945 of base, not 0.95).*
>
> *Compute final premium multiplier for: John, base premium $1200/yr. He: married last year (-10%), had 4 children since (+5+5+5+2 = +17%), had a major accident claim 2 years ago (+15%), moved to low-risk zip code 6 months ago (-8%), turned 47 this year (lucky year)."*

LLMs frequently apply the discounts and surcharges *additively* despite Q8's explicit multiplicative rule, miss Q7's lucky-year clause, and may double-count Q2.

**MindsOS teaching steps.**
1. Add premium adjustment axioms Q1-Q8.
2. Add `compute_premium_adjustment` capacity producing the final multiplier with audit chain.
3. Test John's case. Correct answer: 0.9 × 1.17 × 1.15 × 0.92 × 0.97 = 0.978 multiplier.
4. **Arc D:** mid-demo, Aegis updates Q3: "Major accident surcharge is reduced from +15% to +10% effective 30 days ago." Add Q3' supersede; re-query John; new multiplier 0.945.
5. **Arc E:** try to add Q9 ("major accident surcharge is +20%"); system detects conflict with Q3' and surfaces both for admin resolution.
6. **Arc A:** close session, reopen, re-query John — same answer with same audit trail.

**Arcs exercised.** A, B, D, E, H.

---

## D-Synth-6 — Constructed family-tree with custom relations

Setting: a fictional dynasty with custom kinship rules different from any real-world tradition. (Note: family-tree examples are weaker for the demo because LLMs are reasonable at standard kinship — this domain only shines if the kinship rules are non-standard.)

### Example 6.1 — Inheritance under custom dynastic rules

**Task.** Given a death and surviving relatives, compute inheritance shares under custom rules (deliberately non-Western, non-standard).

**LLM test prompt.**
> *"The Velmara dynasty's inheritance rules: (I1) Eldest surviving sibling of the deceased inherits the title regardless of age, marital status, or descendants. (I2) Estate (movable wealth) is split: 50% to deceased's surviving spouse(s), 30% to children equally, 20% to siblings equally. (I3) Children adopted via the Velmara 'shared lineage' rite inherit double share. (I4) Counter-intuitive: spouses who married the deceased after the deceased was already widowed once receive only 25% of the spouse share (not 50%); the remaining 25% adds to the children's pool. (I5) Stepchildren who undertook the 'sworn devotion' ceremony at age 12+ inherit equal share with biological children. (I6) Counter-intuitive: any sibling who outlives the deceased by less than 30 days is treated as predeceased for inheritance purposes (their share redistributes per the rules). (I7) Counter-intuitive: posthumous children (born after deceased's death within 10 months) inherit a 'spectral share' equal to 1.5x normal child share. (I8) Exception: I7 voids if the posthumous child's parentage is contested through a Velmara legal challenge in the year following birth."*
>
> *Velmar Sevethi has died. He had: spouse Lyra (married after Velmar's first wife died — second marriage), 3 biological children (Kaelin, Sora, Rin), 1 shared-lineage adopted son (Ven), 1 stepson Mara who completed sworn devotion at 14, 2 living siblings (Tarn, who outlived Velmar by 50 days; Nia, who died 12 days after Velmar), and 1 posthumous child (Dren, born 6 months after Velmar's death, parentage uncontested). Estate: 100,000 atlantean credits.*
>
> *Calculate each person's share."*

LLMs typically apply I2 standardly and miss I4's 25%-remainder-to-children rule, miss I6's 30-day-rule on Nia, miss I7's spectral share, and may struggle with I3+I5 stacking.

**MindsOS teaching steps.**
1. Add `Person`, `Relation`, `Inheritance_event` schemas.
2. Add custom inheritance axioms I1-I8.
3. Add `compute_inheritance` capacity producing share-per-person with rule chain.
4. Test the Velmar example.
5. **Arc C:** I4, I6, I7 are all counter-intuitive (none match Western inheritance norms). LLMs in-context will likely miss at least two. MindsOS applies all consistently.
6. **Arc H:** the audit produces a formal derivation showing every rule fired, every share computed.

**Arcs exercised.** B, C, H.

---

### Example 6.2 — Multi-generation kinship derivation in a custom system

**Task.** Given a custom family tree, determine specific kinship relations under non-Western rules.

**LLM test prompt.**
> *"The Velmara dynasty uses these kinship rules (different from English): (K1) 'Tev' = parent's elder sibling of same gender. (K2) 'Lor' = parent's younger sibling of same gender. (K3) 'Mev' = parent's elder sibling of opposite gender. (K4) 'Nor' = parent's younger sibling of opposite gender. (K5) Cousins of the 'Tev' branch are 'Tev-cousins' (they have higher status). (K6) 'Sworn-cousins' = children of two 'Tev-cousins' who completed the sworn-devotion ceremony together. (K7) Counter-intuitive: in Velmara, your aunt's husband (uncle by marriage) is called 'Pen' (not Mev/Nor) regardless of age, and Pens have specific ceremonial roles distinct from blood-relation Mev/Nor.*
>
> *Given this family tree: Old Velmar had children A (eldest, female), B (younger, male), C (younger, female). A's children: A1 (female), A2 (male). B's children: B1 (female). B1 married Q (an outsider). What is B1 to A1? What is Q to A2? What is A1 to B1's hypothetical future child (assume biological)?*"

**MindsOS teaching steps.**
1. Add Person nodes + parent/sibling/spouse relations to local lexicon.
2. Add custom kinship axioms K1-K7.
3. Add `derive_kinship` capacity producing the specific term (Tev/Lor/Mev/Nor/Pen) with derivation chain.
4. Test queries.
5. **Arc C:** K7 (Pen vs Mev/Nor) is counter to English uncle terminology; verify LLM-in-context drift.

**Arcs exercised.** B, C, H.

---

## How to use these examples

1. **Test against current LLMs first.** Pick 2-3 examples from different domains. Run the test prompts against Claude, GPT, Gemini. Document where they drift, miss exceptions, or revert to priors. Save outputs.
2. **Pick a primary demo example.** Recommended primary: **Example 2.1** (TerraSynth approval routing) for enterprise audiences, or **Example 5.1** (Aegis claims) for insurance-vertical audiences. Both showcase the highest density of LLM weaknesses while being legibly enterprise-relevant.
3. **Optionally pick a secondary example** that exercises arcs the primary doesn't (e.g., if primary is 2.1, pair with 1.3 or 5.2 for arcs D/E demonstration).
4. **Build the combined arc demo** (B → C → H → A → D → E) on the chosen example. The combined arc takes 8-12 minutes.
5. **For internal validation**, also implement a fully synthetic-only example (D-Synth-1 / Atlantis or D-Synth-7-style made-up) so your testing isn't contaminated by any real-world knowledge LLMs might bring.

---

## Recommended pairing matrix

| Primary | Secondary | Total arc coverage |
|---|---|---|
| 2.1 (approval routing) | 1.3 (voting + supersedes) | A, B, D, E, F, H |
| 5.1 (claims) | 1.1 (citizenship) | B, C, D, E, G, H |
| 3.2 (admission) | 5.2 (premium) | A, B, D, E, H |
| 1.2 (tax) | 4.2 (game win-cond) | B, C, G, H |

Pick a row that aligns with the audience.

---

**End of demo examples.**

Update with new examples as architectural/UX testing surfaces additional weaknesses to demonstrate. Each example should remain (a) synthetic, (b) tied to a specific structural LLM weakness, (c) executable as a step-by-step MindsOS teaching plan, and (d) mapped to one or more narrative arcs.
