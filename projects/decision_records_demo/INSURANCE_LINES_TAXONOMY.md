# Insurance Lines of Business — Taxonomy for the Intake Routing Beat

Research note, 2026-08-11. Decision Records demo lane. Taxonomy only — no demo design.

> [!WARNING]
> **Status: sourced and reusable, but researched against a premise the plan does not contain.**
> This was commissioned to support an "intake routing" demo beat said to be in
> `DECISION_RECORDS_DEMO_PLAN.md` §2.5. It is not there — §2.5 is five seeded synthetic cases,
> with no classification stage and no lines-of-business taxonomy (verified 2026-08-11; both
> copies md5 `83fe6c6b93f7a09ff4853f0aff43ec70`). §2.5 and Phase 7 are held until the
> claims-practitioner conversation. The taxonomy in §1 and the department finding in §3 stand
> on their sources and are worth keeping; the framing "which lines go in the demo" does not.

---

## 1. Recommendation

**Use the classes of insurance from the Canadian P&C Insurance Return (OSFI / CCIR), Section III.**

Nineteen classes, maintained jointly by OSFI and the Canadian Council of Insurance Regulators, filed annually by every federally regulated P&C insurer in Canada:

> Property – Personal · Home Warranty · Product Warranty · Property – Commercial · Aircraft · Automobile · Boiler and Machinery · Credit Insurance · Credit Protection · Fidelity · Hail · Legal Expenses · Liability · Mortgage · Other Approved Products · Surety · Title · Marine · Accident and Sickness

`Liability` carries named sub-classes: CGL with products, CGL without products, Cyber, D&O, Excess, Professional, Umbrella, Pollution, Other. `Automobile` splits into Liability / Personal Accident / Other.

**Why this set and not the others:**

- It is the set a Canadian claims manager's own company files in. Every other candidate is either foreign or internal.
- It is mirrored on the licensing side in Alberta by the **Classes of Insurance Regulation, Alta Reg 144/2011**, under the provincial *Insurance Act* — so the names are legally operative in Sanmyaku's own province, not just in a federal return. (I could not open the CanLII or open.alberta copies during this pass — robots.txt and a 520 — so the *alignment* with OSFI is asserted from the OSFI list plus the regulation's title and citation, not from a side-by-side read. Worth ten minutes to confirm before it goes on a slide.)
- Insurance Bureau of Canada's annual *Facts* book reports industry premium along the same broad splits (personal property, commercial property, auto, liability), so the vocabulary matches the trade press a Canadian manager reads.

**Rejected:**

- **NAIC annual statement lines (US).** ~34 numbered lines (1 Fire, 2.1 Allied lines, 2.2 Multiple peril crop, 2.3 Federal flood, …). Authoritative and public, but visibly American: "Homeowners multiple peril", "Federal flood", "Workers' compensation" as a P&C line. Workers' comp is a public monopoly (WCB) in every Canadian province — putting it on the board tells an Alberta manager the deck was written for someone else. *Note: I confirmed the blank's structure and opening lines directly; I did not page through the full Appendix enumeration.*
- **ISO/Verisk.** Not a line-of-business taxonomy. It is a *class code* system inside commercial lines (CGL class codes, BOP classifications) for rating the insured's business — the wrong axis entirely, and the manuals are licensed, not public.
- **ACORD.** `LOBCd` is a real enumerated code list, but it is a data-interchange codelist for forms and messages, not a regulatory taxonomy; the model viewer is 403 to anonymous fetch and the specs are member-gated. Cite it as "the interchange standard exists", nothing more.

---

## 2. Demo subset — five classes

All names taken verbatim from the OSFI/CCIR list. No invented categories.

1. **Property – Personal**
2. **Property – Commercial**
3. **Automobile**
4. **Liability** (CGL)
5. **Boiler and Machinery**

### The ambiguous pair: Automobile vs Liability

This is the strongest choice because the ambiguity is not a demo artifact — it is a **litigated coverage boundary with decades of case law**. The CGL auto exclusion removes anything "arising out of the ownership, maintenance, use or entrustment" of an auto, pushing it to the auto policy; the boundary is set by the *mobile equipment* definition and the *loading and unloading* doctrine, and IRMI describes resolving it as "necessarily a fact-intensive inquiry" decided case by case.

Concrete intake facts that genuinely sit on the line:

- A worker injured while goods are moved off a delivery truck — "loading and unloading" runs the whole movement of goods, but courts split on how close to the vehicle the injury must be.
- A forklift or skid-steer that injures someone — mobile equipment (CGL) or auto, depending on registration and where it was operating.
- A person injured *near* a vehicle where the vehicle was transport, not cause (the exploding-rifle case; the fall outside hospital doors).

Two cheaper backup ambiguities, if one pair is not enough:

- **Property – Commercial vs Boiler and Machinery.** An electrical arc or a burst boiler damages a building. Fire/water damage is property; the failed machine itself is equipment breakdown. Real, routine, and the reason equipment breakdown is sold as a separate form.
- **Property – Personal vs Property – Commercial.** Home-based business, short-term rental, detached workshop. A first-notice document rarely says which.

---

## 3. Q4 — Do claims departments actually follow lines of business?

**Not reliably. The premise is partly false, and the part that is false is the part the beat depends on.**

Line of business is *an* axis, but it is neither the primary one nor the one that determines who gets the file.

**What the evidence shows:**

- **LOB appears in the org, coarsely.** Wawanesa Canada posts "Claims Adjuster – Auto Physical Damage", "Claims Adjusters – Farm/Commercial"; Travelers posts "Property Mid-Loss Claims Adjuster", "General Liability Claim Representative". So a top-level auto/property/casualty split is real.
- **But the units are not the statutory classes.** "Auto Physical Damage", "Bodily Injury", "Accident Benefits", "Total Loss" are *coverages inside one statutory line*. "Casualty" *collapses several statutory lines into one unit*. The org's buckets are neither a subset nor a superset of the OSFI classes.
- **Severity/complexity dominates.** Wawanesa runs numbered levels (Level 2, Level 3) and an "Inside Large Loss Level 3" unit; Travelers bands property as "Mid-Loss". The tier decides who touches the file.
- **Orthogonal specialty units cut across everything:** SIU, subrogation/recovery, catastrophe, total loss, litigation management.
- **Ontario auto is the sharpest counterexample:** Accident Benefits (SABS, first-party) and Bodily Injury/tort (third-party) are separate adjusting disciplines in separate units — *inside the single statutory line "Automobile"*.

**And the intake question itself is different from what the beat assumes.** In Guidewire ClaimCenter — which Intact runs — FNOL requires a policy before the claim opens, so **the line of business is inherited from the policy, not decided at intake**. The claim is then decomposed into *exposures* (one claimant × one coverage) and each exposure is assigned separately on severity and specialty. Guidewire's own documentation gives the case: one auto loss, vehicle exposures to a routine group, the injury exposure to a group "that specialize in fatalities." One claim, one LOB, two departments. ClaimCenter also treats Loss Type and Claim Segment as independently searchable facets — vendor-level confirmation that LOB and complexity are orthogonal dimensions, not a hierarchy.

**Plainly:** a demo that shows a claim arriving and being classified *to a line of business* is showing a decision that, in a real carrier, was already made by the policy number on the document. The classification a claims manager would recognise as hard — and unautomated — is the one *below* the line: which coverage/exposure, which severity tier, litigated or not, specialty unit or not. Routing to a "department" named after a statutory class will read as regulatory vocabulary borrowed for a demo. This is a finding about the beat's premise, not a proposal; someone owns the decision about what to do with it.

**Caveat on strength of evidence:** no carrier publishes a claims org chart. The above is reconstructed from job titles (strong evidence a unit exists, weak evidence of hierarchy) plus Guidewire's official routing documentation (strong, but one vendor — Duck Creek, Sapiens, Origami not separately checked). The Ontario AB/BI split is strongly supported inference, not a quoted org chart.

---

## 4. Sources

**Canadian taxonomy (recommended set)**

- [P&C Insurance Return – Section III – Definitions (OSFI)](https://www.osfi-bsif.gc.ca/en/data-forms/reporting-returns/filing-financial-returns/financial-reporting-instructions/pc-insurance-return-section-iii-definitions) — the 19 classes and the Liability/Automobile sub-classes. **Primary source.**
- [P&C Insurance Return – Section IV – Detailed Instructions (OSFI)](https://www.osfi-bsif.gc.ca/en/data-forms/reporting-returns/filing-financial-returns/financial-reporting-instructions/pc-insurance-return-section-iv-detailed-instructions)
- [P&C Insurance Return Instructions – Section I (CCIR, via CAS)](https://www.casact.org/sites/default/files/2021-03/6C_CCIR_Instructions.pdf) — class list confirmed against this copy; "classes are defined in the order they appear on the forms listed in the return."
- [Classes of Insurance Regulation, Alta Reg 144/2011 (CanLII)](https://www.canlii.org/en/ab/laws/regu/alta-reg-144-2011/latest/alta-reg-144-2011.html) — **not opened** (robots.txt). Alberta licensing-side classes. Verify before use.
- [Classes of Insurance Regulation (Alberta Open Government)](https://open.alberta.ca/publications/2011_144) — **not opened** (520 error).
- [IBC Facts of the P&C Insurance Industry in Canada, 2023](https://a-us.storyblok.com/f/1003207/x/487fb75d80/2023-ibc-fact-book.pdf) · [IBC Facts book landing page](https://www.ibc.ca/industry-resources/resources-data/facts-book) — industry premium reported on the same broad splits.
- [GISA – Automobile Statistical Plan](https://www.gisa.ca/AutomobileStatisticalPlan\(ASP\)) · [Commercial Liability Statistical Plan Manual](https://www.gisa.ca/Documents/View/2164) — the Canadian statistical plans sitting under auto and commercial liability. Not needed for the demo; noted for completeness.

**US taxonomy (rejected)**

- [NAIC 2025 Annual Statement Blank – Property/Casualty](https://content.naic.org/sites/default/files/publication-asb-prop.pdf) — numbered lines; structure and opening lines confirmed, full appendix not paged through.
- [NAIC 2025 P&C Annual Statement Instructions](https://content.naic.org/sites/default/files/publication-asi-pua-25.pdf) — states the "Property and Casualty Lines of Business" list is in the Appendix; the appendix text did not render in fetch.

**ISO/Verisk and ACORD (out of scope, documented)**

- [ISO Risk Classification: Commercial Lines Manual guide (Federato)](https://www.federato.ai/library/post/iso-risk-classification-navigating-the-commercial-lines-manual) — secondary; ISO CLM is a *class code* system, not an LOB taxonomy. Manuals are licensed.
- [ISO joins ACORD to develop data exchange standards (Verisk)](https://www.verisk.com/company/newsroom/iso-joins-acord-to-help-develop-standards-for-data-exchange/)
- [ACORD `LOBCd` model viewer (Pilotfish)](https://modelviewers.pilotfishtechnology.com/modelviewers/ACORD-PCS/model/LOBCd.html) — **403 to anonymous fetch.** Code list exists; contents unverified.

**The confusable pair**

- [The Auto Exclusion in the CGL Policy (IRMI)](https://www.irmi.com/articles/expert-commentary/the-auto-exclusion-in-the-cgl-policy) — auto exclusion, mobile equipment, loading/unloading; "necessarily a fact-intensive inquiry", case-by-case.
- [Some Common Coverage Misconceptions of the CGL Policy (IRMI)](https://www.irmi.com/articles/expert-commentary/some-common-coverage-misconceptions-of-the-cgl-policy)
- [Equipment Breakdown — More Than Just Boiler and Machinery (IRMI)](https://www.irmi.com/articles/expert-commentary/equipment-breakdown-more-than-just-boiler-and-machinery) · [Equipment Breakdown Insurance (Adjusters International)](https://www.adjustersinternational.com/pubs/adjusting-today/equipment-breakdown-insurance/) — the property / B&M overlap.

**Claims org structure (Q4)**

- [Guidewire ClaimCenter — Assigning exposures](https://docs.guidewire.com/cloud/cc/202507/cloudapibf/cloudAPI/topics/111-CCFNOL/05-exposures/c_assigning-exposures.html) — the fatalities-specialist example; one claim routed to two groups.
- [Guidewire ClaimCenter — Overview of exposures](https://docs.guidewire.com/cloud/cc/202507/cloudapibf/cloudAPI/topics/111-CCFNOL/05-exposures/c_overview-of-exposures-in-ClaimCenter.html) — exposure = one claimant × one coverage; the assignable atom is below LOB.
- [Guidewire ClaimCenter — The FNOL process](https://docs.guidewire.com/cloud/cc/202507/cloudapibf/cloudAPI/topics/111-CCFNOL/01-executing-FNOL/c_the-FNOL-process-in-ClaimCenter.html) — policy required before claim opens; LOB inherited.
- [Guidewire release highlights — Claim Segment](https://docs.guidewire.com/cloud/olos/whatsnew/topics/cc-release_highlights.html) — segment as a first-class complexity attribute, searchable alongside Loss Type.
- [Intact selects Guidewire for claims management (Canadian Underwriter)](https://www.canadianunderwriter.ca/inspress/intact-financial-corporation-selects-guidewire-solution-for-claims-management/) — a major Canadian carrier runs the model above.
- [Wawanesa Canada claims careers](https://jobs.wawanesa.com/go/Claims/2567017/) — LOB × numbered level matrix; Large Loss and Recovery/Subrogation units.
- [TD Insurance — Claims Specialist, Ontario Bodily Injury](https://www.themuse.com/jobs/tdbank/claims-specialist-claims-ontario-bodily-injury) — "Casualty Claims Services / 3rd Party Liability, Bodily Injury Operations"; litigated-claims protocol.
- [TD Insurance — SIU Auto Claims Investigator](https://www.themuse.com/jobs/tdbank/td-insurance-siu-auto-claims-investigator) · [TD Insurance — Residential Field Claims Advisor](https://www.themuse.com/jobs/tdbank/td-insurance-bilingual-engfre-residential-field-claims-advisor) — specialty and field/inside axes.
- [Progressive — Claims teams](https://careers.progressive.com/en/pages/our-teams-claims/) — auto/property/commercial/medical/PIP/BI/ARBI/catastrophe/subrogation.
- [Travelers — Total Loss Claim Trainee](https://www.insurancejournal.com/jobs/844692-total-loss-claim-trainee) · [Travelers — General Liability Claim Representative](https://www.insurancejournal.com/jobs/840213-general-liability-claim-representative)
- [Claims in the digital age (McKinsey)](https://www.mckinsey.com/industries/financial-services/our-insights/claims-in-the-digital-age) — commentary; "segment claims cases by complexity."
