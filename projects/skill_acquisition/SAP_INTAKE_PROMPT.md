# SAP Intake Prompt (paste into an external LLM)

You are given a software project (code + design docs) that solves some task. Your job is to
describe its **skill components** as a YAML file, following the format below. You do **not** need
any knowledge of the target platform — everything you need is in this prompt. Output **only** the
YAML and a short `# deltas` block; do not judge, install, or add prose.

---

## What you're describing

A skill has four kinds of piece:

- **ground** — the single raw input the skill starts from (e.g. the task/file it's given).
- **datastates** — every named *data type* the code represents. Mark whether each is *given*
  (parsed from input) or *derived* (computed).
- **capabilities** — every *operation* that transforms data. For each, list what it **reads**
  (input data types) and **writes** (output data types), and a **family** (see list below).
- **relations** (optional) — a named tie between two capabilities.

## Procedure

1. **Triage** — ignore process exhaust (chat notes, TODOs, changelogs); keep code + design docs.
2. **Data types** — inventory every type/class/struct the code represents → `datastates`.
3. **Operations** — every function that transforms data → `capabilities`, with `reads`/`writes`
   named in terms of the datastates above.
4. **Classify + family** — assign each capability a `family` from:
   `perception, comprehension, derivation, decomposition, combination, comparator, predicate,
   generator, detector, metric, reasoning, scoring`. If none fits, use your best guess and note it.
5. **Deltas** — where a **doc** and the **code** disagree (a type named in docs but not built; a
   behavior described but not coded), **list it** under `# deltas`. Do **not** resolve it — that's
   the user's call. (If given a source-of-truth policy, apply it; otherwise just flag.)

## Rules to satisfy (self-check before output)

- Exactly **one** `ground`.
- Every capability's `reads`/`writes` names a **declared datastate** (add it if missing).
- Every **derived** datastate is **written by at least one capability** (no orphans).
- Every capability has a `family`.
- Read the code as the source of *behavior*; read docs as *intent* — when they differ, flag, don't pick.

## Output format (emit exactly this shape)

```yaml
skill: <name>
ground: <realm>.<raw_input>
datastates:
  - <realm>.<name>              # a simple id …
  - {id: <realm>.<name>, note: "<why/what>"}   # … or with a note
capabilities:
  - name: <operation>
    family: <family>
    reads:  [<realm>.<name>, ...]
    writes: [<realm>.<name>]
tasks:
  - {id: <task-id>, status: solved|unsolved}
# deltas
#  - <doc says X · code does Y — flagged, unresolved>
```

### Example (abbreviated)

```yaml
skill: arc
ground: arc.raw_task
datastates:
  - arc.grid
  - {id: arc.object, note: "monochrome connected component"}
capabilities:
  - name: build_grid
    family: perception
    reads:  [arc.raw_grid]
    writes: [arc.grid]
  - name: extract_objects
    family: decomposition
    reads:  [arc.grid]
    writes: [arc.object]
tasks:
  - {id: 05f2a901, status: solved}
# deltas
#  - ONTOLOGY names class "Pattern" · no code produces it — flagged
```

---

**Note:** your YAML is a *draft*. A deterministic backend re-validates it and produces the gap
report; the user fixes gaps and re-runs. You are not the authority — accuracy + valid format matter
more than completeness. When unsure, include it and add a note rather than guessing silently.
