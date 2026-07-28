---
title: Reduction capability family (L4-support) — argmin / argmax / top_k / majority_vote
status: Accepted
date: 2026-07-27
layer: L4-support
amends: []
aliases: [reduction-family, argmax, top_k, majority-vote, CR-reduction]
---

# ADR-0204: Reduction capability family (L4-support)

**Status:** Accepted (gate green 2026-07-27 — Linux full suite 4361 passed / 0 failed; PR #86, main `c5c5d4d`; built on ADR-0199)

**Date:** 2026-07-27 (CORE build chat — generic reduction family)

## Context

Picking a winner from a variable-size collection under a per-member score is a
recurring **intelligence decision**: given N scored candidates, select the
argmin/argmax, the k best, or the modal label. Today consumer brains make this
decision in hand-written L4 Python (nilm's k-NN appliance vote, ARC's select
step) because core exposes no reusable capability for it — it is the last
"pick the best" step still off real MindsOS capabilities.

**Grounding verified this chat (origin/main `9e47654`):**

- **No existing reduction cap.** grep across `mindsos_capacity` for
  `argmin/argmax/top_k/majority/vote/reduce` finds nothing but an unrelated
  docstring — the family is genuinely absent.
- **These are L4 decisions, not aggregation plumbing.** `orchestration_v0.py`
  ships the L4-support decision family: "the L4 orchestrator dispatches L3
  decision/scoring points" — e.g. `decision.should_replan`,
  `decision.signal_to_tier`. Each is a capacity L4 **invokes** with the inputs
  the decision needs. A reduction ("select a winner from scored candidates") is
  exactly that shape.
- **The map fan-out already produces the collection.** Collection-iteration
  (ADR-0199, Slice 1b) writes an ordered collection of member outputs to the
  attempt-scoped blackboard. A reduction is the L4 decision step that reads that
  collection and selects — the map writes, then L4 invokes the reduction on it.
- **Capacity input mechanism.** A body is called `implementation(**inputs)`
  (`runtime.py`) and reads its declared DataState inputs by key; L4 supplies
  those inputs at dispatch (as it does for `should_replan`). So a reduction that
  needs `k` simply **declares `k` as an input** and reads it — `k` is produced
  upstream (an L4 decision) and handed in, never a literal baked into the cap.
- **Category layering.** `FUNCTIONAL_CATEGORIES` (13, gate-locked) are the L3
  cognition families pre-loaded by `create_global`. The L4-support families
  (`planning`, `decision`, `scoring`, `predicate`, …) and `dream`/`text` are
  **not** members: their category graphs are created lazily by
  `ensure_category_graph` at first register and installed opt-in, so the 13-count
  invariant is untouched and the bare-system bootstrap is unchanged.

## Decision

Introduce a new **L4-support** capability family, `reduction`, holding four
pure selection capabilities that L4 invokes as intelligence decisions.

### Family / install

- New category constant **`CATEGORY_REDUCTION = "reduction"`** — **not** a member
  of `FUNCTIONAL_CATEGORIES` (count stays 13); its category graph is created
  lazily via `ensure_category_graph` at first register, **not** pre-bootstrapped
  by `create_global`.
- New builtins module `mindsos_capacity/builtins/reduction_v0.py` exposing an
  opt-in **`install_reduction_v0(capacity_layer)`** that registers the four caps.
  Bodies are **real** (`placeholder=False`) — this is a permanent utility family,
  not a WSD placeholder catalog. A consumer opts in at boot (one call, exactly as
  it already installs `planning_v0` / `orchestration_v0`).

### The four capabilities

Each consumes a **scored collection**: an ordered collection DataState (ADR-0199
member shape) whose members are records carrying a numeric score under a fixed
convention key (and, for the vote, a label). Outputs are **non-lossy** — they
carry the winner's position and score so the caller need not re-derive them.

- **`reduction.argmin` / `reduction.argmax`** — the member with the min / max
  score. Direction is fixed by the two named variants (not a parameter).
  - Inputs: `(scored_collection)`
  - Output: `{index, member, score}`
- **`reduction.top_k`** — the `k` best members by score, ranked best-first.
  - Inputs: `(scored_collection, k)` — **`k` is a declared input** supplied by
    L4, never a literal.
  - Output: ordered `[{index, member, score}, …]`; `k > n` clamps to `n`.
- **`reduction.majority_vote`** — the modal label among the members.
  - Inputs: `(scored_collection)`
  - Output: `{label, won, total}` (caller derives confidence = `won / total`).
  - **Ties:** first-in-list wins (input order is authoritative; the caller
    controls order — e.g. feeding score-sorted members makes ties resolve to the
    best-scored). Exposed as the default of a tie-rule the caller may override.

### Invariants

- **L4 invokes; no fold channel.** Reductions are dispatched by L4 with their
  declared inputs, like any decision cap. They are **not** wired as
  `execution.py` fold reducers, so the shipped map/fold dispatch path is
  untouched. This is why `k` needs no special channel and no payload-bundling.
- **Empty collection is a value, not an error.** `argmin/argmax/top_k` →
  empty/`None` selection; `majority_vote` → `{label: None, won: 0, total: 0}`.
  A reduction never raises on empty (mirrors the "reducer concludes nothing"
  → legitimate `dont_know` value, not an abort, `execution.py`).
- **Pure.** Each is a pure function of its declared inputs; no hidden state, no
  MM read (`reads_mm=False`).

## Consequences

- **Additive / byte-identical bare gate.** `create_global` is unchanged (opt-in
  family), so a bare system holds none of these and existing snapshots that do
  not install the family are byte-identical. `FUNCTIONAL_CATEGORIES` stays 13.
- **Package export slate unchanged.** The reduction surface lives entirely in
  the non-re-exported layer: `mindsos_capacity/builtins/__init__.py` (its
  `install_reduction_v0`) and `identifiers.__all__` (the non-functional
  `CATEGORY_REDUCTION`, like its `decision`/`planning` siblings). The package
  `mindsos_capacity.__all__` is untouched, so the gate-locked `139` export-slate
  count and `FUNCTIONAL_CATEGORIES == 13` both hold.
- **No behavior change to shipped paths.** `planning_v0` / `orchestration_v0` /
  `execution.py` fold / find_pipeline are untouched.
- **Consumers adopt in their own chats.** A consumer emits a map that writes the
  scored collection, then an L4 step that invokes a reduction decision on it,
  replacing hand-written L4 selection. (nilm's k-NN vote = `top_k` by nearest
  distance → `majority_vote`; ARC's select = `argmax`. Not built here.)

## Alternatives considered

- **Fold-reducer bodies dispatched by `execution.py`'s map/fold** (the original
  framing). Rejected: reductions are L4 decisions L4 invokes, not aggregation
  plumbing. The fold dispatch passes only `{in_ds: collection}` with no channel
  for `k` / tie-rule, which would force either editing the shipped fold path or
  bundling knobs into the data payload — both avoided by L4 invocation.
- **Reuse the existing `decision` family.** Rejected: `decision.*` is the WSD
  placeholder catalog slated to be atomically replaced at WSD installation;
  seating permanent real caps there risks collision. A dedicated `reduction`
  family is clean and independently owned.
- **Functional category / always-on bootstrap.** Rejected: bumps the gate-locked
  13-count, declares reduction a core L3 cognition family (it is an L4 decision
  support family), and breaks the byte-identical bare gate.
- **Per-`k` cap variants (`top_3`, `top_5`, …).** Rejected: literal `k` violates
  "`k` is an input"; `k` is an L4 decision handed in at dispatch.
- **Lossy outputs (bare value / label only).** Rejected: `arg*` without the
  index throws away the winner's identity ("arg" = the position that optimizes),
  and a vote without its tally is half a decision; callers would re-derive both
  in L4 — the code this family exists to remove.

## Test plan (gate on Linux `/home/sanmyaku/mindsos`)

- **Per cap:** `argmin`/`argmax` basic + tie; `top_k` ranking + `k>n` clamp;
  `majority_vote` modal + first-in-list tie; **empty-collection** nothing-found
  for all four.
- **Install:** `install_reduction_v0` registers the four IRIs; idempotent
  (mirrors `test_text_install_idempotent.py`).
- **Additivity:** `create_global` roster unchanged; `FUNCTIONAL_CATEGORIES`
  still 13; package export-slate (139) unchanged.
- **Composition smoke (generic, no consumer import):** `top_k` → `majority_vote`
  over canned scored records reproduces a nearest-then-vote selection.

## Status flip

Proposed → **Accepted** on 2026-07-27: the full Linux suite passed green
(4361 passed / 0 failed) with the 10 new `tests/reduction/` tests.
