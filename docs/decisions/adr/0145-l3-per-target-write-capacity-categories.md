---
title: L3 per-target write capacity categories
status: Proposed
date: 2026-04-27
layer: L3
---

# ADR-0145: L3 per-target write capacity categories

**Status:** Proposed

**Date:** 2026-04-27

**Related:** ADR-0060 (L3 fixed-not-learned), ADR-0138 (KL drops write API), ADR-0143 (`KLWriteHandle`), ADR-0146 (write invocation contract), ADR-0147 (per-flow build pattern).

## Context

Today L3 ships 12 functional categories — perception, comprehension, derivation, decomposition, combination, trace, retrieval, signal-emission, relevance-scoring, path-finding, etc. — all read or transform. ADR-0138 relocates KL's write methods into L3 as named capacities. This raises the categorisation question: do write capacities form a new category, distribute across existing categories by mechanism, or get organised by *target* (which role-graph they write)?

## Decision

**Per-target categories.** Write capacities are organised by what they write, not by the fact that they write:

| Category | Writes to (role) | Example capacities |
|----------|-------------------|---------------------|
| `capacity:consolidate` | `memories` (Local) | `consolidate-mm` |
| `capacity:trace` | `problem-trace` (Global) | `record-problem` |
| `capacity:promote` | promotion path (`pending_global` via server) | `propose-pipeline`, `propose-pattern` |
| `capacity:author` | `concepts`, `lexicon`, `alignments` (Local drafts) | `author-concept`, `author-lexicon-entry`, `author-alignment` |
| `capacity:state` | `capacity-state` (Local) | `capture-resident-state` |

Existing L3 categories (perception, comprehension, derivation, decomposition, combination, trace, retrieval, signal-emission, relevance-scoring, path-finding) remain unchanged in semantics; some grow capacities that happen to write (e.g. `capacity:trace` already exists as a problem-trace concept and now contains `record-problem` write capacity).

There is no umbrella `capacity:write` category. Writing is a mechanism, not a function. Categories on the L3 axis are functions.

## Rationale

L3's organising principle is *what cognitive function does this capacity perform*. The 12 existing categories follow that axis. A new `capacity:write` umbrella breaks the axis (mixes "what" with "how").

Per-target categories preserve the axis. Each category has coherent semantics:

- "consolidate" = take an MM and produce a stable memory record.
- "trace" = record what failed and why.
- "promote" = propose a Local artefact for cross-user sharing via release.
- "author" = create a user-authored Local draft.
- "state" = capture resident-capacity state.

These are functions, not mechanisms. They happen to write because writing is what they do — but each category names the function, not the act.

## Consequences

**Good:**

- L3's category axis stays coherent (function-organised).
- Each category is small and reasonable to enumerate; auditors can ask "what's in `capacity:consolidate`?" and get a short answer.
- The 6 minimum capacities for L4 v1 (consolidate-mm, record-problem, propose-pipeline, propose-pattern, capture-resident-state, author-concept) map 1-to-1 to a category-and-name slot.
- Adding new write capacities adds new category members; existing categories don't bloat.

**Tradeoffs:**

- 5 new category names; some start with one capacity. (`capacity:state` may stay singular long-term.)
- "How do I find all write capacities?" requires scanning multiple categories. Mitigation: write capacities tag themselves as such in their schema; build a derived `where_writes` view.
- The line between `capacity:trace` (write-side here) and existing trace-related read capacities is named the same; disambiguate with capacity IRIs (`capacity:trace:record-problem` vs `capacity:trace:retrieve-by-error-type`).

## Alternatives considered

1. **Single `capacity:write` umbrella category.** Rejected — heterogeneous content; "write" is mechanism, not function.
2. **Distribute writes across existing categories without new categories.** Rejected — write capacities mixed with read; "find all writers" requires scanning all categories; no coherent grouping.
3. **Hybrid: umbrella `capacity:write` + per-target subcategories.** Rejected — two ways to slice; introduces accidental hierarchy.

## Implementation references

- 6 minimum write capacities (per ADR-0147 per-flow build pattern):
  - `capacity:consolidate:mm` — Local write to `memories`.
  - `capacity:trace:problem` — Global write to `problem-trace`.
  - `capacity:promote:pipeline` — wraps `mindsos_server.propose_for_promotion()` for `promoted-pipelines`.
  - `capacity:promote:pattern` — wraps `mindsos_server.propose_for_promotion()` for `task-patterns`.
  - `capacity:author:concept` — Local write to `concepts`.
  - `capacity:state:capture` — Local write to `capacity-state`.
- Each capacity uses `KLWriteHandle` (ADR-0143) and follows the symmetric invocation contract (ADR-0146).
- ADR moves to Accepted when (a) at least one capacity in each new category ships, (b) `docs/usage/capacity/categories.md` lists the new categories, (c) the `mindsos_capacity` discovery layer surfaces them.

## §Implementation (Phase 33 — partial-flip; halvim, 2026-05-26)

Phase 33 lights up ONE of the 5 new categories per ADR-0147 per-flow
build discipline (Phase 33 design Round 0 PB-1):

- `capacity:consolidate` — NEW category; `CATEGORY_CONSOLIDATE`
  constant added to `mindsos_capacity/identifiers.py`;
  `FUNCTIONAL_CATEGORIES` extended 12 → 13. Bootstrap default
  (`create_global()`) now produces 14 contained graphs (13 categories
  + `capacity:datastates`). First occupant: `capacity:consolidate:mm`
  (Local write to `memories` role-graph via
  `KLWriteHandle(scope='local')`).
- `capacity:trace` — EXISTING category (Phase 27 vocabulary); first
  *write* occupant added at Phase 33: `capacity:trace:problem` (Global
  write to `problem-trace` role-graph via
  `KLWriteHandle(scope='global')`). The category was previously
  read-only.

Deferred to per-flow phases (ADR-0147):

- `capacity:promote` — promote:pipeline + promote:pattern; wraps
  `mindsos_admin.promotion.propose_for_promotion`. Ships at the
  phase that closes the L4 pipeline-finder flow.
- `capacity:author` — author:concept + lexicon-entry + alignment;
  ships at the L4 author flow.
- `capacity:state` — state:capture; ships at the L4 capacity-state
  snapshot lifecycle.

§Accept criteria satisfied PARTIALLY at Phase 33: (a) one category
(`consolidate`) lit; (b) `docs/usage/capacity/categories.md` amends
with the write-side note + link to this ADR; (c) the new categories
surface through `FUNCTIONAL_CATEGORIES` + `mm_composite_datastates`
+ `build_consolidate_mm` etc. exported via `mindsos_capacity.__all__`.
**Status stays Proposed** until promote / author / state ship
alongside their L4 flows. ADR-0145 flips Accepted at the latest of
those category-ship phases.

**Write-capacity terminator semantic (Phase 33 amendment).** Write
capacities have `outputs=()` per ADR-0146 §amendment-1 clause 4 —
they consume DataStates but emit none. Phase 30's BFS pipeline-finder
treats them as dead-ends (correct; L4 invokes writes directly).
Auto-discovery (ADR-0069 + ADR-0086) emits zero outbound TYPE_COMPAT
edges from write capacities; inbound edges fire only when other
capacities produce the placeholder input DataStates (none do at
Phase 33).
