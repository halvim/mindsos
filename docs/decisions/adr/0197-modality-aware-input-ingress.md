---
title: Modality-aware input ingress for the Phase-1 interpretation seam
status: Accepted
date: 2026-07-04
layer: L4
aliases: [intelligence-ADR-modality-ingress]
supersedes: []
amends: [0195]
---

# ADR-0197: Modality-aware input ingress for the Phase-1 interpretation seam

**Status:** Accepted (shipped on `feat/modality-ingress`, slices 1+2; Linux
fresh-clone gate 4139 passed / 0 failed, modality_ingress=5 + test_cli=256
collected)

**Date:** 2026-07-04

## Context

`phase_1.interpret` (ADR-0195) has no modality or source concept. Every task
input enters as one opaque `DS_RAW_INPUT` handed to the profile-selected
`process` slot, and the inter-step DataState spine is **hardcoded**:

```
structured = dispatch(process, {DS_RAW_INPUT: task_input}).outputs[DS_STRUCTURED_INPUT]
hints      = dispatch(hint,    {DS_STRUCTURED_INPUT: structured}).outputs[DS_HINT_SET]
goal       = dispatch(derive_goal, {DS_STRUCTURED_INPUT, DS_HINT_SET}).outputs[DS_GOAL]
mapping    = dispatch(map,   {DS_STRUCTURED_INPUT, DS_HINT_SET, DS_GOAL}).outputs[DS_MAPPING]
```

Two consequences:

1. A picture or a button-action cannot be read by a text passthrough, and the
   interpretation *shape* (which body tokenizes, what "structured" means) is
   text-specific — yet nothing types the input by what it *is*.
2. The shipped, real text family (`text.space_split`: `text.raw` → `text.tokens`,
   ADR-0063 perception) is **installed but dormant** — its `text.tokens` output
   is consumed by nothing, because the spine reads the fixed `DS_STRUCTURED_INPUT`.

`Phase1Profile` (ADR-0195) is a *construction-bound, per-consumer* selection of
capacity IRIs held on `L4Dispatcher.phase1_profile`. It swaps *which body* runs
per slot, but the DataState spine those bodies flow through is fixed. It has no
notion of "this input is text vs an image" and no per-input selection.

Motivating consumer: **arc-solver** — text today (its intake tokenizes inline),
a UI with buttons/images later. arc does not block on this; this is a core
platform feature arc will *consume*, and per RULES §8 it must not live in arc.

## Decision

Add a **modality-aware ingress layer** over the ADR-0195 seam. Five sub-decisions.

### 1. Two axes, never collapsed: MODALITY selects, SOURCE is provenance

**Modality** (the data *type*: text / image / action) drives capacity
selection. **Source** (which button, API, channel) is provenance metadata,
carried on the input envelope and **never** consulted for selection. The
boundary/adapter that admits an input **stamps** the modality — *declared by the
source* (RULES §7; the UI knows it fired an action), never sniffed from bytes.

### 2. Modality IS the identity of the ingress DataState — no parallel taxonomy

We do **not** introduce a first-class modality enum. A modality *is* the type of
the DataState the raw value is wrapped in at ingress: text → `text.raw`, image →
`image.raw` (future), action → `action.event` (future). "Stamp the modality" =
"choose which ingress DataState wraps the raw value." This keeps selection on the
same axis ADR-0195 §Decision.4 already uses (`reference_kind` = a DataState IRI
naming a type = the `find_pipeline` start), and satisfies "do not pre-bake the
taxonomy" — modalities are added by registering DataStates + a profile, not by
editing an enum.

### 3. Runtime `{modality → Phase1Profile}` selection, extending the construction-bound profile

ADR-0195 binds **one** `Phase1Profile` at dispatcher construction. This ADR adds
a **modality table** — `Mapping[ingress_datastate_iri, Phase1Profile]` — held on
the dispatcher alongside `phase1_profile`. `interpret` reads the stamped ingress
modality off the input envelope and selects `table[modality]` **per input**,
falling back to the construction-bound `phase1_profile` (then all-v0) when the
table has no entry. This is still a dispatch-time IRI selection — **no
scope-mix** (ADR-0195 hard constraint a preserved): bodies register into their
own scope; the table only names IRIs.

Eventual: the modality DataState becomes a `find_pipeline` *start* (modality →
intent), so selection is finder-composed rather than table-looked-up. That is
**gated on the sound multi-step/DAG finder** (composition-lifecycle Part 5) and
is **not** a v1 dependency. The modality DataStates are declared as real
`find_pipeline` start nodes now so the later swap re-types nothing.

### 4. De-hardcode the interpret spine — read inter-step DataStates from the selected caps

`interpret` stops hardcoding `DS_RAW_INPUT` / `DS_STRUCTURED_INPUT` /
`DS_HINT_SET` / `DS_GOAL` / `DS_MAPPING`. Each step keys its input/output off the
**declared I/O of the selected capacity** (`Capacity.inputs` / `.outputs`):

- ingress key = the selected `process` cap's declared input (the modality
  ingress DS);
- `structured` = `dispatch(process, …).outputs[<process cap's sole output>]`;
- downstream steps key `structured` off each selected cap's declared input.

**Invariant — the all-v0 path is byte-for-byte unchanged.** The v0 caps declare
exactly `DS_RAW_INPUT → DS_STRUCTURED_INPUT → …`, so a `None`-table / `None`-
profile dispatcher produces the identical Phase-47/48 flow. This is the load-
bearing change: it is what lets the text modality's `process` step *be*
`text.space_split` (output `text.tokens`) and have downstream consume `tokens`,
closing the phase1↔text disconnect **without** a bespoke bridge capacity.

### 5. v1 ships exactly one real modality — text — plus contract-only extension points

- **Text (real, has a consumer):** register a text modality profile whose
  `process` slot is the shipped `text.space_split`; the text modality's
  "structured" DataState is `text.tokens`. The downstream `hint`/`derive_goal`/
  `map` slots stay the input-agnostic v0 bodies, re-keyed via §4 to the text
  structured DS (they ignore their inputs, so the trivial mapping still returns).
  This proves an input is tokenized **by a capacity** inside the seam.
- **Image / action (extension points only):** define the ingress DataState +
  selection contract so adding one is "register a catalog." **Ship no image/
  action capacities** — no consumer today (RULES §8).

Migrating arc's local `_hint_impl(.split())` onto this seam is a **follow-up in
the arc chat**, not here. Home is `mindsos_intelligence/phase_1` + the phase-1
catalog.

### Ownership vs the adapter family (ADR-0062 / ADAPTER_FAMILY_CHAT)

Modality **stamping** and **selection** are ingress concerns owned here. They are
**not** `Adapter` nodes (ADR-0062, shape-bridging) and do **not** front-run
ADAPTER_FAMILY_CHAT (cross-*realm* `adapter.*` capacities). Because §4 lets the
spine flow the selected caps' own DataStates, v1 needs **no** cross-realm bridge
capacity, so no `adapter.*` ships and there is no ownership conflict. The word
"adapter" is avoided for the boundary role.

## Consequences

**Good:**
- Adding a modality = register an ingress DataState + a `Phase1Profile` + a table
  entry. No enum, no `interpret` edit.
- The dormant text family becomes live; the phase1↔text disconnect closes with
  the real capacity, not a copy.
- Strict extension of ADR-0195 — the construction-bound single-profile path and
  the all-v0 path are untouched; the finder-composed future re-types nothing.
- Source/provenance is structurally prevented from influencing selection.

**Bad:**
- `interpret` grows a per-step declared-I/O lookup, slightly more machinery than
  the fixed spine.
- v1 exercises the selection table with a single entry — the extension seam is
  real but only one modality proves it (mitigated: text is a genuine consumer and
  the contract, not the table size, is the deliverable).
- Downstream v0 bodies are input-agnostic, so the text path proves *flow*, not
  text-specific hint/goal/map (those are the arc consumer's Local bodies).

## Alternatives considered

- **First-class modality enum + a `modality` field on the envelope that selects.**
  Rejected — duplicates the DataState type system and pre-bakes the taxonomy
  (violates the brief). §2 uses the ingress DataState identity instead.

- **Keep the fixed spine; wrap text in a `process.text` cap that emits
  `DS_STRUCTURED_INPUT`.** Rejected — copies `space_split` logic into a wrapper,
  does not run *the shipped capacity*, and leaves `text.tokens` still consumed by
  nothing (disconnect not truly closed).

- **Compose the process step as a `find_pipeline` chain from the ingress DS to a
  fixed `DS_STRUCTURED_INPUT`.** Rejected for v1 — needs a `text.tokens →
  structured_input` bridge capacity, which is `adapter.*` territory (front-runs
  ADAPTER_FAMILY_CHAT) and is unsound until the multi-step finder lands. This is
  the natural *eventual* shape (§3) once that finder is sound.

- **Per-input `Phase1Profile` passed by the caller instead of a dispatcher
  table.** Rejected — the boundary, not the caller, knows the modality; a
  dispatcher-held table keeps `interpret`'s signature stable and mirrors
  ADR-0195's construction-bound binding.

## Build decisions (resolved against shipped code, 2026-07-04)

The three open questions are settled against `mindsos_capacity` as shipped:

1. **Input validation is strict, so §4 is mandatory, not optional.**
   `capacity._validate_inputs` enforces both *missing-required* (per
   `input_group`) **and** *no-unexpected* — any input key absent from a cap's
   declared `CONSUMES` raises `InputContractError`. Therefore a text `process`
   step (declaring `text.raw` → `text.tokens`) *cannot* be fed through a
   `DS_STRUCTURED_INPUT`-keyed spine; the de-hardcode is the only sound wiring,
   which also retires the "wrapper cap" alternative for good.

2. **The spine is environment-threaded, not positional.** `interpret` keeps a
   `{DataState IRI → value}` environment. It seeds `{<process cap's declared
   input> : value}`, and for each step passes `{ds: env[ds] for ds in
   selected_cap.inputs}`, then merges the step's `outputs` back into `env`. Each
   return artifact is read from its producing step's declared output
   (`structured` = process output, `hints` = hint output, etc.) rather than a
   fixed IRI. This handles `derive_goal`/`map` re-consuming
   `structured`+`hint_set`+`goal` with no positional guessing and is
   byte-identical on the all-v0 path. A selected cap declaring an input absent
   from `env` raises `InterpretationError` (mis-wired profile). All v1 phase-1
   step caps are `all_required`; `any_of`/`fold` phase-1 steps are out of scope.

3. **Ingress is a frozen `InputEnvelope(value, modality=None, source=None)`.**
   `interpret` accepts a raw value (legacy → construction-bound profile → v0,
   unchanged) *or* an envelope. `modality` is the ingress DataState IRI driving
   the §3 table lookup; `source` is provenance carried through and **never**
   read for selection — structurally enforcing §1. Lives in
   `mindsos_intelligence.ingress`.

## Shipped

- **Slice 1** — `InputEnvelope` + the environment-threaded spine (the
  load-bearing de-hardcode), with the all-v0 path proven byte-identical.
- **Slice 2** — the `L4Dispatcher` `{modality→Phase1Profile}` table + per-input
  selection, and the text phase-1 catalog
  (`mindsos_capacity.builtins.phase1_text`) wiring the shipped
  `text.space_split` as the text `process` step. The phase1↔text disconnect is
  closed: `text.tokens` is consumed inside `interpret` by a capacity.

Deferred: finder-composed modality selection (modality DataState as a
`find_pipeline` start), gated on the sound multi-step finder; and real
`image`/`action` catalogs, which have no consumer today.

## Supersession / amendment trail
- **Amends [[ADR-0195]]** — extends the construction-bound `Phase1Profile` with a
  runtime `{modality→Phase1Profile}` table, and de-hardcodes the fixed
  interpretation DataState spine that 0195 introduced into an
  environment-threaded one. Builds on **ADR-0156** (bipartite topology /
  `find_pipeline`) and **ADR-0063** (the shipped `text.*` family).
- Supersedes / superseded by: none.

## Amendment 1 (modality is authoritative — unroutable is dont-know, not v0)

**Status:** Accepted (self-amendment; scope = `mindsos_intelligence/phase_1.py`
selection path + `tests/modality_ingress`). Does not change this ADR's status.

§3 as shipped let a **stamped** modality with no table entry fall back to the
construction-bound `phase1_profile` and then to all-v0. Combined with the v0
`map` body's fixed `mapping_confidence = 1.0`, an unhandled input (unknown,
typo'd, or unsupported modality) returned `task-pattern:v0:trivial` at full
confidence — a confident answer to an input the brain cannot interpret.
`tests/modality_ingress/test_ingress_text.py::test_unknown_modality_falls_back_to_v0`
pinned that as intended, so this is a deliberate **policy reversal of the §3
fallback clause**, not a bug patch. The rest of the Decision (§1, §2, §4, §5) is
intact.

The modality is **authoritative** (§2: the modality *is* the ingress DataState):

1. **Unroutable (Mode A).** A stamped modality absent from the
   `{modality→Phase1Profile}` table raises `InterpretationError`. It does **not**
   fall back to the construction-bound profile — that binding is the legacy
   `modality=None` path only. `run_lifecycle` maps the raise to a terminal
   `TaskOutcome.status = dont_know` (ADR-0196; DontKnowReason class
   `UNHANDLED_INPUT`, ADR-0157).
2. **Mis-registered (Mode B).** A stamped modality whose selected profile's
   `process` declares an ingress ≠ the modality raises `InterpretationError`,
   enforcing §2 at the point of use.

**Unchanged:** the `modality=None` legacy path (raw value or
`InputEnvelope(modality=None)`) is byte-identical — neither guard fires. No new
verdict type: `interpret` already raises `InterpretationError` for its
dont-know-class conditions (unresolvable `map` target, below-threshold
confidence), and this is the same class. Both guards live in
`phase_1.interpret`'s selection path (no separate boot-time validator — that
would couple dispatcher construction to capacity-install order and be
forgettable).

**Not additive-inert** (unlike the base ADR's §4): this reverses a shipped,
tested behavior and inverts `test_unknown_modality_falls_back_to_v0`
(→ `test_unknown_modality_raises_not_v0`), plus adds
`test_modality_routes_to_wrong_ingress_raises`. It is carried by this amendment,
not routed through the design-log §0 additive-inertness gate.

**Deferred / out of scope:** killing the v0-trivial default and mandatory
stamping (every raw caller depends on `modality=None → v0`); threading
`DontKnowReason.UNHANDLED_INPUT` into the raise for richer L4 telemetry; and an
optional boot-time `validate_modality_table()` for fail-at-CI rather than
fail-at-first-use (the per-selection Mode-B guard already covers correctness).
