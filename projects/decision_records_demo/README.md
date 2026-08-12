# Decision Records — demo lane

The **Decision Records demo** lane. Zero-revenue; sales evidence, not product. **Not core.** Nothing here
owns an architectural mechanism (RULES.md §8); nothing here is imported by `mindsos_*`.

Governing plan: `confirmation_docs/DECISION_RECORDS_DEMO_PLAN.md` (the record of record).
Build order: `confirmation_docs/DECISION_RECORDS_V0_PLAN.md`, which **replaces `DECISION_RECORDS_V0_SLICE_PLAN.md` outright** — the older file is still on disk and must not be built from.
Cross-lane agreements: `confirmation_docs/DECISION_RECORDS_AGREED_CHANGES.md`.

This folder holds **demo and evidence research** — domain material, sourced taxonomies,
scenario notes. Design decisions do not live here; they go in the confirmation docs.

---

## ⚠ Scope boundaries

- **`Projects/Sanmyaku-GTM/` is not this folder.** That one is meeting operations with real
  humans (`meeting-prep` skill + Granola). Demo and research artifacts do not go there.
- ~~**The plan has no intake-routing beat.**~~ **SUPERSEDED — it does now.** That was true of the
  file as it stood when the taxonomy was commissioned; §2.5 was amended twice on 2026-08-11
  (`b325607`, then `cfc1795`) and the beat is **routing EXPOSURES, not classifying the claim** —
  an exposure being one claimant × one coverage. The original fabricated quote is still a
  cautionary tale and the rule it earned stands: **grep the cited file before building on a
  §-reference.**
- ~~**§2.5 and Phase 7 are both held** until the claims-practitioner conversation.~~
  **The hold is satisfied** — the Mauricio call happened (phone, unrecorded, 2026-08-11). What
  is still open is whether routing is *valued*, which `Sanmyaku-GTM/planned/mauricio-claims/
  CALL_2_QUESTIONS.md` is built to settle. Phase 7 remains blocked on Decision Records v0
  rendering runs 1 and 2, and on there being a transport.

---

## Contents

| File | What it is |
|---|---|
| `INSURANCE_LINES_TAXONOMY.md` | Sourced Canadian P&C line-of-business taxonomy, plus the verified finding that claims **departments** are not lines of business. Researched against a premise that turned out not to be in the plan — read its status block first. |
