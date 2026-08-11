# Skill Acquisition — Guide

**Status:** DRAFT v0.1 · 2026-08-11. The entry point for acquiring a MindsOS skill. This is a
**sequencer** — it orders the steps and points to the instrument/spec for each; it does not restate
them. Canonical design lives in the referenced docs.

**What "acquisition" means here:** turning a domain into grounded, evolving MindsOS skill components
(construction **+** modification). Distinct from *installation* (Phase-50 bundle/install; the last step).

## The three references this guide sequences

- **What a skill is** — `AUTHORING_TAXONOMY.md` (components K0–K10).
- **How you change one** — `AUTHORING_TAXONOMY.md` §7 (one transactional modification surface: add / modify / retire).
- **When** — `AUTHORING_TAXONOMY.md` §8 (stage model: logical → prototype → commit → package).

## Acquisition is task-pulled, not layer-pushed

The motivator is always **solve a task** (often vaguely formulated) that intelligence will later
automate. Nobody knows the MindsOS architecture, so the process must guide the user *from the task*,
not from the layer stack. Components (K2–K5) are acquired **on demand, pulled by task-solving** — the
world-model grows under task pressure, it is not authored top-down. **Prototyping is the main
sub-process**; construction/commit/package are the comparatively mechanical tail.

### The prototyping loop (the heart of SAP)

0. **Pin** one concrete task **+ a checkable pass test** (e.g. ARC's withheld answer). Not the vague
   goal — a solvable instance you can measure. *(Fixes "the task isn't formulated.")*
1. **Seed** a generalizable pipeline skeleton (K6/K7) + whatever capacities exist.
2. **Run** the current pipeline on the task.
3. **Gap** — if it fails, find the **smallest missing datastate/capacity**.
4. **Extend** via the modification surface; the SAP backend rule-checks the add (C1/DS5/…).
   **Reuse-first:** extend a shared primitive; a bespoke capacity is the last resort. *(anti-overfit #1)*
5. **Regression-gate** — re-verify **all previously-solved tasks**. *(anti-overfit #2)*
6. Repeat with the next task.

**Exit:** new tasks solve with **no** new capacities (generalization reached) → commit/ground (Step 4).
Without steps 4–5 the loop degrades into a task→answer lookup table, not an intelligence.

## Two front doors

- **Intake** (existing material — code, docs, or a prototype like ARC): start at Step 1.
- **Greenfield** (nothing but a domain + examples): Step 1 still applies — the probe's extraction runs
  on whatever exists (a problem description + example tasks); it just finds fewer components and more gaps.

## Steps

Each step names its instrument and its exit bar. Every change within a step goes through the
modification surface (§7); the **validation reference** (the re-grounding walk) runs at each step,
**stage-aware** (logical bar in Steps 1–3; executed bar at Step 4).

| # | Step | Instrument | Produces | Exit bar |
|---|---|---|---|---|
| **1** | **Intake probe** | `SKILL_INTAKE_PROBE.md` | initial K-table (housing = *suggested*) + fit report (R1–R6) + gaps + stage read | triage done; every extracted component placed or flagged |
| 2 | Logical design | K-table (§2) + fit rubric (§8.1) | filled K-table; fit violations resolved | K0–K10 have an owner + no open R1–R6 violation |
| 3 | Prototype + test | spike; use-case task(s) | a solving prototype (inline bodies OK) | logical grounding passes + use-case solves + fit-checklist clean (§8.2) |
| 4 | Commit / ground | modification surface `commit` op | MindsOS registrations; layer wired | executed grounding passes (provenance walks + layer actually invoked) |
| 5 | Package / install | Phase-50 bundle (*installation*) | installable bundle | install / de-install / provenance / idempotency (Phase-50 criteria) |

## Notes

- **Step 1 is the only MindsOS-agnostic step** — the probe carries the target model as data, so an LLM
  that doesn't know MindsOS can run it. Steps 2–4 assume the taxonomy/stage model.
- **Modification re-enters at any step.** Revising a committed skill = a change-set on the surface (§7)
  with blast-radius re-grounding (K10); it does not restart at Step 1.
- **Validated so far:** Step 1 on ARC (`ARC_INTAKE.md`) — alignment half only; foreign extraction untested.
