# Skill Intake Probe — v0.4

**What this is:** a self-contained instrument an LLM runs on existing skill material to produce a
MindsOS-aligned component map. **The LLM needs no prior MindsOS knowledge** — this doc carries the
target model (Phase 2 + glossary). First sub-process of skill acquisition; output feeds Stage A/B of
`AUTHORING_TAXONOMY.md`.

**Input** = whatever exists: a codebase, design docs, or (greenfield) just a domain description +
example tasks. Fewer inputs → fewer components found and more gaps; that is a valid result, not a failure.

**Core principle — the probe observes, the user decides the roles.** Docs and code are two sources.
The probe records what **each says** and reports the **delta** between them. It does **not** decide
which source is authoritative — it must not treat code as truth *or* docs as truth. Whether a doc is
an intended target, a description of current behavior, or a stale note — and therefore whether a
doc/code gap is planned work, a bug, or noise — is the **user's** determination, not the probe's.

**Source-of-truth policy (user input, applied by the probe).** So the report is usable and not a raw
dump, the user supplies a policy the probe *applies* (never invents):

- global: `docs-are-target` | `code-is-target` | `ask-per-delta`; and/or
- per-source overrides (e.g. "this ONTOLOGY.md = target; this README = descriptive; these SVGs = stale").

With no policy, the probe defaults to `ask-per-delta` and presents deltas unresolved. The probe may
attach a **non-binding suggestion** to a delta (clearly marked `suggestion:`) but never resolves it.

Run the three phases in order. Emit one report per §Output.

**v0.4 changelog:** roles are no longer fixed by the probe — added the user source-of-truth policy;
the probe presents deltas + non-binding suggestions, the user assigns authority. **v0.3:** two-
authorities framing + doc intent-classification + maturity status + delta report. **v0.2:** input
broadened; Phase 1 execution reality; fit rule R7; evidence-backed stage read. (ARC run — `ARC_INTAKE.md`.)

---

## Phase 0 — Triage (separate skill from exhaust)

Classify every file into one bucket. Only `skill-content` and `code` proceed.

- **code** — runs / computes (the skill's real behavior).
- **skill-content** — the domain model: vocabulary, class/type definitions, rules, use-cases.
- **exhaust** — process scaffolding: chat prompts, TODO/next-step notes, changelogs, meeting logs.
- **artifact** — generated/derived: viewers, images, exported data, caches.

Flag: (a) multiple docs covering the same topic (redundancy), (b) multiple code lineages (>1
independent implementation of the same behavior).

## Phase 1 — Extract (MindsOS-agnostic — describe in the code's OWN terms)

Inventory, no MindsOS vocabulary:

1. **Ground** — what is the single raw input the skill starts from?
2. **Data types** — every named thing the code represents (types/classes/structs/dataclasses).
   For each: is it *given* (parsed from input) or *derived* (computed)?
3. **Operations** — every function that transforms data. For each: inputs → output; is it pure?
4. **Vocabulary** — domain terms with definitions (from docs/comments/names).
5. **Control flow** — what runs always vs conditionally vs on-demand; how the next step is chosen.
6. **Use-cases / tests** — the concrete examples the skill is checked against.
7. **Execution reality** — for each operation (Q3): is it *actually called* when the skill runs, or
   only *declared/registered* and never invoked? Trace from the real entry point. Flag any operation
   that is declared but dead, or whose real compute lives somewhere other than where it's declared.

## Phase 2 — Align (map the Phase-1 inventory onto the K-table)

Fill one row per component. The K-table (target model — the LLM reads it here, no outside knowledge):

| K | Component | Fill from Phase 1 |
|---|---|---|
| K0 | Ground | the single raw input (Q1) |
| K1 | Domain scope + corpus | what's in/out; where examples come from |
| K2 | Lexicon | vocabulary terms + definitions (Q4) |
| K3 | Ontology | data types as classes + how they relate (Q2) |
| K4 | DataStates | one per **derived** data type (Q2) |
| K5a | Capability contract | each operation's inputs→output signature (Q3) |
| K5b | Capability body | each operation's actual compute (Q3) |
| K6 | Pipeline / control | always-run vs on-demand; how next step is picked (Q5) |
| K7 | Reasoning convention | how candidate solutions are induced/searched/verified (Q5) |
| K8 | Grounding checker | is there a check that every derived thing traces to the ground? |
| K9 | Use-case validation | the tests/examples (Q6) |
| K10 | Change unit | N/A at intake (only relevant when modifying) |

**Two independent statuses per component:**
- **housing** — `suggested` (intake output is always suggested; not yet in MindsOS form).
- **maturity** — `planned` (in a doc the **user** designated a target, no code) → `transcribed`
  (coded/registered, not run — R7) → `executed` (coded and actually invoked). `transcribed`/`executed`
  are read from code (Q7); `planned` is only assigned after the user resolves a delta as target-ahead-
  of-code. The probe never sets `planned` on its own.

### Phase-2 fit rubric (flag violations — these block later grounding)

- **R1** No operation may *select or call another operation* by name at runtime (no dispatcher). Flag any.
- **R2** Every relationship between data types is one of: part-of (compositional), relation-peer
  (relational), producer/consumer I/O (functional), or borne-value (attribute). Flag relationships
  that fit none.
- **R3** Part-whole must be expressible as one whole↔{parts} grouping, not scattered pair-links.
- **R4** Every operation returns a defined "don't-know" (None / abstain / marker), not a silent default.
- **R5** Multi-input or fold operations need a *sound* composer — flag any that a naive one-input-at-a-
  time chainer would mis-run (drops inputs / collapses folds).
- **R6** Every derived data type must trace back to the ground through producer operations only
  (provenance). Flag orphans (derived, but no producing operation named).
- **R7** For each operation, mark grounding level: **executed** (actually invoked at runtime, real
  compute reachable from the entry point — Q7) vs **transcribed** (declared/registered only, or real
  compute lives off to the side). A skill that is all-transcribed is a *prototype*, not a committed
  skill — this is the single check that most distinguishes stage (see stage read).

## Output (one report)

1. **Triage table** — files bucketed + redundancy/lineage flags.
2. **K-table** — filled rows, each citing the source file/symbol.
3. **Fit report** — R1–R6 violations, each with the offending component.
4. **Gaps** — K-rows with neither intended-doc nor code behind them (the skill hasn't conceived this).
5. **Doc/code delta report** — every discrepancy, stated neutrally as *doc-says X · code-does Y*, with
   an optional `suggestion:`. The user's source-of-truth policy then resolves each into an outcome
   (not a probe verdict): **planned** (user calls the doc the target → the **LLM-generation work
   queue**, doc = spec), **bug/drift** (user calls code the target), or **stale** (user marks it dead).
   Unresolved deltas remain listed under `ask-per-delta` until the user decides.
6. **Stage read** — which acquisition stage the skill is actually at (logical / prototype / commit),
   **with evidence**: cite the R7 executed-vs-transcribed split, whether the runtime is wired to the
   declared components, and how many use-cases actually pass. No bare verdict.
