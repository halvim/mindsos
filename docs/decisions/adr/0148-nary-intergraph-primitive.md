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
(`mindsos_core/exceptions.py`). At Phase 05c the factory **refuses**
`compositional=True` together with `ordered=False` (P8-A); see
§amendment-1 — an earlier line here asserted the opposite and was a
reconstruction error. `Metagraph` gains `add_intergraph_edge` /
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
`docs/decisions/adr/0205-abstraction-levels.md` (§amendment-1),
and several `CHANGELOG.md` entries.

---

## Amendments

### amendment-1 (2026-07-31, CORE-C2 pre-build read-through) — a reconstruction error is corrected

**What was wrong.** §Decision previously read: *"Compositional intergraph hyperedges are
`compositional=True, ordered=False` by default (per the amendment cited in the glossary)."*

That sentence and `docs/concepts/glossary.md` form a **citation cycle asserting opposite
outcomes**. The glossary says the primitive *"Refuses `compositional=True, ordered=False` per
ADR-0148 amendment"*; this ADR said such links are that combination by default, citing the
glossary. Neither reproduces the amendment. No such amendment text exists anywhere in the
repo.

**Resolution — the refusal was the real decision.** Four independent sources agree:

- the code — `Metagraph.add_intergraph_hyperedge` validation step 10 raises
  `SchemaError("compositional hyperedges require ordered=True types")`;
- `docs/concepts/glossary.md`;
- `confirmation_docs/PHASE_MAP.md`, the Phase 05c **P8-A** row, which carries the rationale
  (*compositional implies identity-bearing composition — `cat = c + a + t`, order and
  duplicates matter; set semantics is incompatible*);
- `confirmation_docs/INTERGRAPH_EDGES_DESIGN.md`, the canonical design document for both
  primitives, and `confirmation_docs/PHASE_05c_CONFIRMED.md`.

One reconstructed line said otherwise. **This ADR is a reconstructed record** (see the warning
above) and the line is corrected to match, rather than treated as authority.

**Consequence for anyone citing this ADR.** ADR-0205 §2's amendment permitting
`compositional=True` with `ordered=False` is a **deliberate override of P8-A's argument**, not
a restoration of an ADR-0148 contract. Do not cite this ADR as the ground for it; cite
ADR-0205 §amendment-1 (which independently located the same rationale in
`INTERGRAPH_EDGES_DESIGN.md`) together with §amendment-2.3.
