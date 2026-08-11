# Decision Records — demo lane

The **Decision Records demo** lane. Zero-revenue; sales evidence, not product. **Not core.** Nothing here
owns an architectural mechanism (RULES.md §8); nothing here is imported by `mindsos_*`.

Governing plan: `confirmation_docs/DECISION_RECORDS_DEMO_PLAN.md` (the record of record).
Build slice: `confirmation_docs/DECISION_RECORDS_V0_SLICE_PLAN.md`.
Cross-lane agreements: `confirmation_docs/DECISION_RECORDS_AGREED_CHANGES.md`.

This folder holds **demo and evidence research** — domain material, sourced taxonomies,
scenario notes. Design decisions do not live here; they go in the confirmation docs.

---

## ⚠ Scope boundaries

- **`Projects/Sanmyaku-GTM/` is not this folder.** That one is meeting operations with real
  humans (`meeting-prep` skill + Granola). Demo and research artifacts do not go there.
- **The plan has no intake-routing beat.** `DECISION_RECORDS_DEMO_PLAN.md` §2.5 is five seeded
  synthetic cases — clean approval, clean denial, needs a policy exception, missing a required
  document, policy changed between submission and assessment. There is no claim-classification
  stage and no lines-of-business taxonomy in the plan. A 2026-08-11 task prompt quoted one;
  the quote is not in the file (md5 `83fe6c6b93f7a09ff4853f0aff43ec70`, both copies).
- **§2.5 and Phase 7 are both held** until the claims-practitioner conversation. Domain-specific
  demo work should not run ahead of it.

---

## Contents

| File | What it is |
|---|---|
| `INSURANCE_LINES_TAXONOMY.md` | Sourced Canadian P&C line-of-business taxonomy, plus the verified finding that claims **departments** are not lines of business. Researched against a premise that turned out not to be in the plan — read its status block first. |
