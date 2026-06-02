# MindsOS Business Problem Catalog — Commercial Use Cases

**Date:** 2026-04-30
**Origin:** WSD goal-finalization chat.
**Purpose:** Catalog of business problems where MindsOS structurally outperforms LLMs after admin teaches the rules and processes. For pilot-vertical selection and commercial roadmap planning.

---

## Pattern across all problems

Every problem in this catalog shares seven characteristics:

1. **Rules are proprietary or highly local** — not in LLM training data.
2. **Multi-rule consistency** is required across high query volume.
3. **Audit trail is mandatory** (regulatory or liability driven).
4. **Updates happen frequently** — supersedes-with-audit beats retraining.
5. **Counter-intuitive exceptions** abound — LLMs revert to general priors.
6. **Calibration matters** — borderline cases need honest uncertainty.
7. **The cost of being wrong is high** — fines, lawsuits, patient harm, denied benefits.

---

## 1. Internal compliance / regulatory determination

**Problem.** "Does this transaction / activity / disclosure comply with our firm's interpretation of [regulation X]?"

**Why LLMs struggle.** Internal interpretations of regulations are firm-proprietary. RAG can fetch policy documents but cannot reliably synthesize multi-rule decisions with consistent override semantics across thousands of queries. Compliance audit requires a *traceable chain of why this decision was made*. LLMs produce post-hoc justifications, not faithful chains. Wrong answers cost millions in fines.

**MindsOS after teaching.** Compliance officer encodes the firm's interpretation of each rule + override + exception as axioms. New transactions get audit-traced decisions. Interpretation updates are versioned. Cross-team knowledge sharing via Local→Global promotion. Every decision is reproducible.

**Teaching effort.** ~50-200 axioms per regulatory regime. Substantial up-front; each axiom encoded once.

**Examples:** banking AML/KYC, broker-dealer suitability, healthcare HIPAA decisions, GDPR data-handling judgments, FDA labeling adherence.

---

## 2. Insurance claim adjudication

**Problem.** "Is this claim covered? At what amount? With what reasoning the policyholder can dispute?"

**Why LLMs struggle.** Each insurer has unique policy clauses with intricate exception interactions. Adjudicators handle thousands of claims; consistency across adjudicators is mandatory. Disputes require auditable reasoning. LLMs produce fluent reasoning that doesn't survive legal scrutiny.

**MindsOS after teaching.** Policy clauses + exclusions + exceptions encoded as axioms. New claims get coverage decisions with full audit trail. Policy version updates propagate via supersedes. Dispute resolution shows the policyholder which clauses applied.

**Teaching effort.** ~30-80 axioms per insurance product line.

---

## 3. Tax determination for niche jurisdictions / edge cases

**Problem.** "What's the correct tax treatment for this transaction under [jurisdiction Y / specific edge case]?"

**Why LLMs struggle.** Tax law has counter-intuitive interactions between credits, deductions, and timing rules. LLMs trained on general tax content miss jurisdictional specifics and post-cutoff rule changes. CPAs/tax attorneys need to *justify* treatment in audit defense — fluency without traceability is worthless.

**MindsOS after teaching.** Each tax rule as axiom; calculation procedures as capacities. Yearly updates via supersedes. Audit trail per return shows every rule applied.

**Teaching effort.** ~100-300 axioms for a major jurisdiction; smaller for narrow specialties.

---

## 4. Loan underwriting / credit decisions

**Problem.** "Approve / reject / conditional-approve this loan application, with regulator-defensible reasoning."

**Why LLMs struggle.** Fair Lending laws (ECOA, FCRA in US) require *adverse action reasons* be specific, accurate, and discrimination-free. Banks must prove decisions don't reflect protected-class proxies. LLM-generated reasons are unverifiable; regulators reject them.

**MindsOS after teaching.** Bank's underwriting criteria encoded as axioms. Each decision produces explicit adverse-action codes traceable to specific axioms. Audit for fair-lending review is direct: which rules fired, on which inputs.

**Teaching effort.** ~50-150 axioms per loan product; reusable across products with shared criteria.

---

## 5. Healthcare protocol adherence / clinical decision support

**Problem.** "Does this treatment plan adhere to our hospital's protocol for [condition X]? Why or why not?"

**Why LLMs struggle.** Hospital protocols are institution-specific and update frequently as guidelines evolve. Patient safety mandates calibrated confidence — LLM overconfidence on medical decisions is a known liability. Joint Commission audits require traceable adherence to specific protocols.

**MindsOS after teaching.** Hospital protocols as axioms; treatment-plan evaluation as capacity. Calibrated confidence on borderline cases. Audit shows protocol-by-protocol adherence. Supersedes for protocol updates.

**Teaching effort.** ~20-100 axioms per protocol; modular per condition.

---

## 6. Procurement / vendor approval workflows

**Problem.** "Who must approve this purchase? Has policy been followed?"

**Why LLMs struggle.** Approval chains depend on amount, vendor risk, contract type, regional law, employee tenure, emergency status. Each company's chain is unique and updates with org changes. SOX compliance audits require demonstrable adherence.

**MindsOS after teaching.** Approval rules as axioms; routing as capacity. Audit shows approval chain per transaction. Updates via supersedes when org changes.

**Teaching effort.** ~20-50 axioms for typical mid-size company.

---

## 7. Investment suitability / portfolio compliance

**Problem.** "Is this trade suitable for this client given their stated risk tolerance, regulatory designation, and investment objectives?"

**Why LLMs struggle.** Suitability rules are highly specific and intersect with multiple regulatory regimes (FINRA Rule 2111, SEC Reg BI, state-level fiduciary rules). Audit-required. LLMs cannot reliably maintain consistency across thousands of trades.

**MindsOS after teaching.** Suitability rules + client-specific constraints as axioms. Per-trade evaluation with audit chain. Updates per regulatory change.

**Teaching effort.** ~50-150 axioms; multi-regime compliance is the value driver.

---

## 8. Government benefits eligibility (multi-program)

**Problem.** "Which benefits is this household eligible for, and how does receipt of one affect eligibility for others?"

**Why LLMs struggle.** Means-testing rules interact across programs (SNAP, TANF, Medicaid, housing assistance, etc.). Counter-intuitive interactions are common ("benefits cliff" effects). LLM hallucinations on income thresholds disenfranchise applicants. Caseworker decisions are auditable and appealable.

**MindsOS after teaching.** Each program's eligibility rules as axioms; cross-program interactions as derived axioms. Per-applicant evaluation with audit chain showing every program considered.

**Teaching effort.** ~100-300 axioms; high reuse across caseworkers.

---

## 9. Construction permit / zoning compliance

**Problem.** "Does this proposed construction comply with local zoning, building code, and permit requirements?"

**Why LLMs struggle.** Zoning is hyper-local and updates frequently. Multi-rule interactions (setbacks, height limits, use restrictions, historical districts, environmental overlays). LLMs lack jurisdiction-specific data; permit denials require legally-defensible reasoning.

**MindsOS after teaching.** Local zoning axioms; per-site evaluation. Audit trail for permit decisions. Easy to update when ordinances change.

**Teaching effort.** Per-jurisdiction. Could be templated by jurisdiction-type.

---

## 10. Contract review against firm risk policy

**Problem.** "Does this contract clause violate our firm's standard risk preferences? If so, what's the redline?"

**Why LLMs struggle.** Firm risk policies are proprietary and idiosyncratic. Counter-intuitive clauses (a firm may accept some risks others reject). Malpractice exposure on missed flags. LLMs produce inconsistent reviews across documents.

**MindsOS after teaching.** Firm risk policies as axioms; clause-by-clause evaluation as capacity. Audit trail per contract. Update as policy evolves.

**Teaching effort.** ~30-100 axioms per practice area.

---

## Pilot recommendation

For first commercial pilot, lead with #1 (regulatory compliance) or #6 (procurement). Both have:

- High volume (justifies teaching investment).
- Existing audit infrastructure (buyer already values audit).
- Concrete LLM weakness (LLMs have already failed in compliance contexts at major institutions).
- Reasonable teaching scope (50-200 axioms achievable for a pilot).
- Clear ROI (compliance officer hours saved + reduced audit findings).

**Avoid as first pilots despite high value:**
- Healthcare (#5): FDA software-as-a-medical-device exposure if outputs influence treatment.
- Government benefits (#8): affects vulnerable populations; political risk.

Both are great v3+ targets but risky for v1.

---

## Caveats

1. **v1 won't fully solve any of these.** v1 demonstrates the capability on a subset of rules in a controlled scope. Production-grade deployment requires deep capacity stacks built over years of flywheel iteration.

2. **Teaching cost is non-trivial.** SME time (lawyers, CPAs, doctors, compliance officers) is expensive. MindsOS value prop must beat hiring more humans or LLMs+manual-review. Pilot where volume is high and human review is the current bottleneck.

3. **Robust NLU is a prerequisite.** Most problems start with natural-language input. MindsOS's WSD + FOL + Frame must reliably extract structured properties for axioms to operate on. The v1 NLU stack must mature before production deployment.

---

**End of catalog.**

Add new business problems as they surface from prospect conversations. Each entry should retain the same structure: problem statement, structural LLM weakness, MindsOS-after-teaching advantage, teaching effort estimate.
