---
title: KL version-pinned read + retire-version lazy-inline hook
status: Accepted
date: 2026-06-04
accepted_date: 2026-06-04
layer: L2
amends: [0153]
related: [0153, 0150, 0160, 0044]
---

# ADR-0161: KL version-pinned read + retire-version lazy-inline hook

**Status:** Accepted

**Date:** 2026-06-04

**Related:** ADR-0153 (mutation discipline — `append_only_with_lazy_inline`), ADR-0150 (knowledge lifecycle), ADR-0160 (dump carries the version pin this surface reads), ADR-0044 (episodic_memories).

## Context

The D'1 retention model (Chat B §4.4) stores episode references as `(iri, version_int)` pairs, pins them at instantiation, and resolves historical content from Phase 11 side-by-side version graphs. Two KL operations were deferred to the L0 substrate phase (L2-41 / L0-21 / L0-22): a version-pinned read and a retire hook that releases KL-held content lazily. Phase 44 ships both.

The `append_only_with_lazy_inline` mutation discipline and its `via_lazy_inline` validator gate already shipped at Phase 43 (`mindsos_knowledge/validators.py`). What remains is the *trigger* (`retire_version`) and the *marker* it writes; the *read-time consumer* that consults the marker on episode read is owned by Phase 48 (L5), not this phase.

## Decision

### 1. `kl.read_at_version(metagraph, role, version)`

Returns the version-pinned view of a role graph from the Phase 11 side-by-side version graphs. Distinct from a HEAD read: it resolves the content as of `version` regardless of subsequent versions. Required by D'1 fallback reads and episode resolution.

### 2. `kl.retire_version(metagraph, role, version)`

Flips a lazy-inline marker on the retired version node and releases the KL-held content so it can be inlined on next episode read. Distinct from `kl.deprecate_version()`: deprecated content stays readable side-by-side; only **retire** actually releases held content.

### 3. The retire marker — forward-contract for Phase 48

The marker is a node property named **`_retired_inline_pending`** (boolean) on the retired version node, co-located with the versioned content. The name and storage location are frozen here so the Phase 48 episode-read consumer can consult it. Because single-underscore Cypher-property keys are reserved at user-property scope but are NOT auto-reserved by the `ov__` prefix machinery, `_retired_inline_pending` is registered in `RESERVED_PROPERTY_KEYS` (`mindsos_core/schema/validation.py`) so schema validation does not reject the marker write.

**Consumer split (CR-4):** Phase 44 ships the hook + marker-write + marker-state unit test only. The episode-read consultation that inlines the marked content lands at Phase 48 under D'1.

## Rationale

- **Marker as a node property, not a side graph or version_db row.** Co-locating the marker with the versioned content keeps retire a single-node write and makes the Phase 48 read a property check rather than a cross-store join.
- **Freeze the name now.** Phase 48 is a separate chat; a frozen property name is the contract that lets it ship without re-opening Phase 44.
- **Retire ≠ deprecate.** Releasing content is irreversible-ish; flagging is not. Keeping them separate prevents an accidental release on a mere deprecation flag.

## Consequences

- `RESERVED_PROPERTY_KEYS` gains one entry (`_retired_inline_pending`).
- A retire with no Phase 48 consumer is intentionally inert at v1 — the marker is written and asserted by unit test, but nothing reads it until Phase 48. This is a deliberate forward-contract, not dead code.

## Alternatives considered

1. **Separate marker graph in the Metagraph.** Rejected — adds a graph and a cross-graph read for a one-bit flag.
2. **Marker row in `version_db`.** Rejected — splits the marker from the content it describes across the graph/SQLite boundary.
3. **Ship the read-time consumer here too.** Rejected — episode read under D'1 is Phase 48 (L5) scope; pulling it forward couples Rail C to L5.
