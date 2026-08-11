# SAP toolkit — how to use each module

Practical usage. For *why* / the process concepts, see `SKILL_ACQUISITION_GUIDE.md`.

## Start here (for the main SAP chat — you own this now)

This folder is the **Skill Acquisition Process (SAP)** — the *authoring* front-half: turn any project
into grounded, installable MindsOS skill components. As of 2026-08-11 the main SAP chat owns it.

**Entry points:** this README (how to run) → `SKILL_ACQUISITION_GUIDE.md` (the process + prototyping
loop) → `AUTHORING_TAXONOMY.md` (design spine, components K0–K10) → `SAP_RULES.md` (rules, sourced
from MindsOS code).

**⚠ Naming:** `SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md` + `_PHASE_MAP.md` here are the **older
*install* lifecycle** (Phase 50), pending rename to *installation*. They are **not** this work.
SAP = authoring; those = installation.

**Built + validated:** the intake prompt (`SAP_INTAKE_PROMPT.md`) is reproducible across 3 LLMs
including a foreign, non-MindsOS codebase; the validator (`sap_backend.py`) + YAML I/O
(`sap_io.py`) + install-adapter (`sap_install.py`) + regression gate (`sap_gate.py`) are working
prototypes — all standalone (no `mindsos` import).

**Not done:** live install (`sap_install --execute` is a stub; needs a MindsOS instance + admin
session); a rule refinement the foreign run surfaced (scalar constructors that read no datastate);
Guide Steps 2–5; re-derive `SAP_RULES.md` if it graduates (≈190 core commits since it was drafted,
anchors verified present).

## The flow

```
project (code+docs)
   │  SAP_INTAKE_PROMPT.md  →  external LLM
   ▼
skill.yaml  ──sap_backend.py──▶  skill_report.md (+ .json)
   ▲                                     │ read gaps
   └───────── fix gaps ◀─────────────────┘
   │  when report is PASS: set "approved": true in the .json
   ▼
sap_install.py  →  register-plan  →  MindsOS
```

## Quick start

```bash
# 1. produce the input (paste SAP_INTAKE_PROMPT.md + your project into an LLM) → save as skill.yaml
# 2. validate
python3 sap_backend.py skill.yaml --report-prefix skill_report
# 3. read skill_report.md, fix gaps in skill.yaml, re-run step 2 until it says PASS
# 4. approve: edit skill_report.json → "approved": true
# 5. see the install plan (dry-run)
python3 sap_install.py skill.yaml skill_report.json
```

## Modules

| File | What it is | Run / use | In → Out |
|---|---|---|---|
| **SAP_INTAKE_PROMPT.md** | Paste-into-an-LLM prompt that turns a project into the input YAML. MindsOS-agnostic. | paste it + project files into any LLM | project → `skill.yaml` |
| **SAP_CHATGPT_PASTE.md** | The prompt **plus** ARC's two key files inlined, for one-shot pasting into ChatGPT. | paste whole into ChatGPT | (ARC demo) → yaml |
| **sap_io.py** | Translator: friendly YAML ⇄ backend JSON. Used by the others; not run directly. | imported | `.yaml`/`.json` → internal dict |
| **sap_backend.py** | The validator. Checks the rules, writes the gap report + valid build order. | `python3 sap_backend.py <skill.yaml> [--report-prefix out]` | yaml → `out.md` + `out.json` |
| **sap_install.py** | Turns an **approved, passing** report into the ordered MindsOS `register_*` plan. Refuses if not approved/not passing. | `python3 sap_install.py <skill.yaml> <report.json> [--execute]` | yaml + report → register plan |
| **sap_gate.py** | Regression gate + overfit signal for the prototyping loop (solved→not-solved; caps-per-task). | imported; inject the skill's `solve`/`oracle` | task results → regressions + signal |
| **SAP_RULES.md** | Reference: the rules the backend enforces, sourced from MindsOS code. | read | — |

## Authoring format (`skill.yaml`)

```yaml
skill: myskill
ground: realm.raw_input          # the one starting datastate
datastates:
  - realm.thing                  # a plain id …
  - {id: realm.other, note: "…"} # … or with a note
capabilities:
  - name: do_something
    family: derivation           # perception|derivation|comparator|generator|predicate|…
    reads:  [realm.raw_input]    # ≥1 input datastate (required)
    writes: [realm.thing]        # ≥1 output datastate (required)
tasks:
  - {id: task-1, status: solved}
```

## What the report tells you

- **Must fix (blocks install)** — e.g. a capability that doesn't read+write a datastate, an undeclared
  datastate, no family, no/many ground, a dependency cycle, a duplicate id.
- **Notes (accepted)** — e.g. orphan datastates (declared but nothing produces them yet — a *planned*
  concept). Reported, never blocking.

Install proceeds only when there are **no blocking gaps** and you've set `"approved": true`.

## Source vs generated

Commit: the `sap_*.py`, the `*.md` docs, and your `skill.yaml`.
Regenerable (don't commit): `*_report.md/json`, `arc_input.json`, `arc_*.yaml` demo outputs.
