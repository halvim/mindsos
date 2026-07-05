---
title: Perception atom layer — geometry/signal realms + the introduce-atom primitive
status: Proposed
date: 2026-06-27
layer: L3
amends: []
related: [0156, 0158, 0159, 0184, 0191]
---

# ADR-0192: Perception atom layer — geometry/signal realms + the introduce-atom primitive

**Status:** Proposed — design for B2/B3 of the perception hand-off, grounded in the doctrine
`docs/concepts/perception-principles.md` (P2, P3, P5, P6, P10, P11). No `mindsos_*` code ships
on this ADR yet; build when a perception consumer exists (consumer discipline, RULES §8).

**Date:** 2026-06-27

## Context

The doctrine says perception = composition over atoms, where **atoms = DataStates** and
**perceptions = capacities** (P10). Two implementation questions follow:

- **B2 — what atoms, and where do they live?** The atom set must stay **minimal + orthogonal**
  (P6): one thing per atom, richness from *combination capacities*, not fat atoms. But the
  concrete atoms range from modality-general (point, intensity, edge) to sensor-specific
  (pixel, subpixel) to named concepts (rectangle). Putting all of it in core would violate the
  subsystem-ownership rule (RULES §8 — content belongs to subsystems, not core).
- **B3 — how is a new fundamental atom added?** P11 says the unit is never a bare DataState; it
  is a **DataState + a capacity that wires it into the existing graph**, and "fundamental" is a
  *movable* status (adding `subpixel→pixel` reclassifies pixel from fundamental to derived).

The realm machinery already exists (ADR-0158: `datastate:<realm>.<name>`, `RESERVED_REALMS`,
`register_datastate(..., allow_new_realm=)`); the bipartite topology already exists (ADR-0156:
`PRODUCES`/`CONSUMES` IntergraphEdges); `register_capacity` already emits those edges.

## Decision

1. **Core hosts modality-GENERAL atoms only; sensor-specific atoms + named recognizers are
   subsystem content (PB-2 = Option C).** Add two reserved realms to `mindsos_capacity`
   `identifiers.py`: **`geometry`** (point, line, angle, …) and **`signal`** (intensity, edge,
   gradient, …) — reusable across any spatial/temporal modality, mirroring how
   `builtins/text.py` ships minimal text capacities while WSD owns lexicon content. **Sensor
   atoms (`pixel`, `subpixel`) and named-concept recognizers (`rectangle`, `circle`) live in a
   future *perception/vision subsystem* (a Skill), not in core.** *(Reversible: if you prefer
   all vision atoms in core builtins, that is Option A — say so and this ADR changes.)*

2. **Minimal + orthogonal is a contract, not a guideline (P6).** Each atom DataState carries
   exactly one quantity; cross-atom richness is expressed by explicit **combination capacities**
   (`point + intensity → edge`), never by attributes packed onto an atom. Binding between atoms
   is by shared index (the grid), not by fields on the atom node.

3. **"Fundamental" is a COMPUTED status, not a stored flag.** A DataState is *fundamental* iff
   it has **no incoming `PRODUCES` edge** (no producer capacity) — i.e. it is supplied at the
   sensory boundary. This makes P11's "movable status" literally true in the graph: adding a
   `subpixel→pixel` capacity gives `pixel` a producer, so it *becomes* derived automatically,
   non-disruptively (every consumer of the `pixel` DataState still works; it just has an
   upstream producer now). No migration, no flag to flip.

4. **The introduce-atom primitive = (register_datastate + register_capacity), unified across
   exogenous and endogenous triggers (B3 + P3).** Adding a fundamental atom (human, P2) and
   promoting a derived atom (system, P3) are the **same operation**: introduce a DataState +
   the producer capacity that wires it in. They differ only in:
   - **trigger:** exogenous (human authoring) vs endogenous (promotion proposal, see ADR-0194);
   - **gate:** exogenous fundamental atoms are admin-authored (ADR-0158 `allow_new_realm`);
     endogenous promoted atoms go through the promotion loop (ADR-0184 seam).
   Do **not** build a separate "add fundamental atom" API — it is the existing registration
   pair plus a trigger (the trigger pathway is the signal route in ADR-0193).

## Consequences

- Core grows two realms + their atom DataStates + combination capacities (when first consumed);
  the vision subsystem supplies pixels/recognizers on top, pinning a core tag (RULES §3).
- `fundamental?` becomes a graph query (`no PRODUCES edge`), usable by the grounding/irreducibility
  machinery (ADR-0193) and the downward-extensible-floor story (P11).
- Atom additions are uniformly auditable (a DataState node + a capacity + its edges), whether
  human or promoted.

## Alternatives considered

- **Option A — all vision atoms in core builtins.** Rejected (default): violates RULES §8
  content/core split; pollutes core with sensor + named-concept specifics. (Re-openable on your
  call.)
- **Option B — all perception content (incl. point/intensity) in a subsystem.** Rejected:
  contradicts the `text.py` precedent (core does ship a minimal modality builtin); geometry/
  signal atoms are genuinely cross-modality substrate.
- **A stored `fundamental` boolean.** Rejected — duplicates information the `PRODUCES` topology
  already encodes and would need migration on every floor extension (P11).

## Open
The exact starter atom list for `geometry`/`signal` is left to the first consuming subsystem
(consumer discipline); this ADR fixes the realms, the minimal-orthogonal contract, the
computed-fundamental rule, and the unified introduce-atom primitive.
