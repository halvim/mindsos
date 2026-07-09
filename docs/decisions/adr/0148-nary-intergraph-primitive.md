---
title: N-ary IntergraphEdge / IntergraphHyperEdge primitive
status: Accepted
date: 2026-05-16
layer: L1
reconstructed: true
---

# ADR-0148: N-ary IntergraphEdge / IntergraphHyperEdge primitive

**Status:** Accepted (reconstructed 2026-07 — see note)

**Date:** 2026-05-16 (Phase 05b)

!!! warning "Reconstructed record"
    The original ADR-0148 file was **never committed** to the docs tree,
    though several shipped docs and CHANGELOG entries cite it (as a "first
    draft" that was later amended for the n-ary primitive). This file
    reconstructs the decision from those citations and from the shipped
    code so the references resolve. It is **not** the original text; the
    prose here is a faithful summary, not the as-authored ADR.

## Context

MindsOS needs typed relationships that cross graph boundaries *within one
metagraph* (e.g. an L3 capacity referencing an L2 DataState, or a
composition binding several element graphs into one identity-bearing
whole). A binary cross-graph edge is insufficient for compositions, which
are inherently n-ary. The earlier `CompositionalMetaEdge` idea was dropped
in the L1 slim port (N3-D); its role is taken over by an explicit flag on
the intergraph primitives.

## Decision

Introduce two cross-graph primitives in `mindsos_core`:

- **`IntergraphEdge`** — a binary typed edge between elements in two graphs
  of the same metagraph (`mindsos_core/models/intergraph_edge.py`).
- **`IntergraphHyperEdge`** — the **n-ary** generalisation, binding an
  arbitrary set of cross-graph elements
  (`mindsos_core/models/intergraph_hyperedge.py`).

Both carry a top-level **`compositional: bool`** dataclass field (default
`False`; Pushback 2-A). When `compositional=True`, the edge is
**identity-bearing** — the composition *is* the bound whole, and the edge
is immutable: mutation attempts raise **`CompositionalImmutableError`**
(`mindsos_core/exceptions.py`). Compositional intergraph hyperedges are
`compositional=True, ordered=False` by default (per the amendment cited in
the glossary). `Metagraph` gains `add_intergraph_edge` /
`update_intergraph_hyperedge` and enforces the compositional-immutability
invariant on write (`metagraph.py`).

## Consequences

- The primitive is live: `IntergraphEdge`, `IntergraphHyperEdge`,
  `compositional`, and `CompositionalImmutableError` all ship in
  `mindsos_core` (exported from `mindsos_core/__init__.py`).
- ADR-0156 (Phase 42) builds the L3 bipartite `PRODUCES`/`CONSUMES`
  topology on top of these intergraph primitives.
- Soft-delete (ADR-0133) excludes the intergraph variants at Phase 10 (P83);
  the `CompositionalImmutableError` class is retained as an
  `IntergraphEdge.compositional` consumer, not a soft-delete refusal.

## Citations that reference this ADR

`docs/api/core/intergraph-edge.md`, `docs/concepts/glossary.md`,
`docs/getting-started/whats-new-v4.md`, `docs/decisions/adr/0133-*.md`,
and several `CHANGELOG.md` entries.
