---
title: SubMind endowment lifecycle + `subminds` L2 role-graph
status: Accepted
date: 2026-06-23
layer: L2
amends: [ADR-0150]
related: [0180, 0183, 0188, 0189]
---

# ADR-0190: SubMind endowment lifecycle + `subminds` L2 role-graph

**Status:** Accepted — Slice 1 shipped on `feat/subminds` (Linux gate green; tag `feat-subminds-slice1-confirmed`). The `subminds` L2 role-graph (Global form) + ADR-0150 §amendment-7 (closed role-set 13→14) are live; the Local form + taught path + de-endowment land in Slice 4. See `confirmation_docs/SUBMIND_DESIGN_LOG.md` §19.

**Date:** 2026-06-23

## Context

ADR-0188/0189 define the SubMind construct and its runtime arbitration. This ADR fixes *where the definition lives* and *how a SubMind is added to a system*. A SubMind is inherently cross-layer (check-capacity → L3, threshold → L2, resolver → skill/capacity, loop + scheduler + arbitration → L4), so its persisted definition needs a durable, auditable, Global/Local home — and its install path needs to be conceptually distinct from skill-acquisition (Phase 50 / ADR-0183) without re-inventing the plumbing.

A skill is the *use* of the system to achieve a goal (acquired). A SubMind is an *extension* of the system — a standing faculty that conditions it (endowed). These are different acts and should have different lifecycles, even though both ultimately register content into the running system.

## Decision

1. **New L2 role-graph `subminds`** holds SubMind definition records (Global + Local). The closed role-set grows **13 → 14** (amends ADR-0150). A record carries: check-capacity ref, threshold/criterion ref(s), severity-normalization range, severity→tier mapping, importance weight, resolver ref + its declared exclusive-resource needs, cadence-law parameters, activation class, declared Reflex conditions + pre-wired actions, and refractory/reset parameters.

2. **Runtime home is L4** — the SubMind runtime class, the single scheduler thread, and the `SubMindRegistry` (ADR-0189) live in `mindsos_intelligence`. L2 holds the persisted *definition*; L4 holds *execution*.

3. **Endowment is a distinct lifecycle from skill-acquisition.** It has its own concept, vocabulary, registry, lifecycle verbs, and audit events — but it **reuses low-level primitives**: `register_capacity` (for the check-capacity), role-graph write, the ADR-0180 pre-authorized scope-aware write gate, and audit. It does **not** clone the entire skill installer (preflight/digest/records/driver/activation) merely to rename it.

4. **Authored and taught paths converge on the role-graph.** An authored endowment (admin-gated, Global) and a taught/exemplified endowment both write a definition record into `subminds`; the L4 `SubMindRegistry` loads active records at session start.

## Consequences

- "Improve a mind by adding a small mind to it" becomes a concrete, durable, auditable operation — endowment — that is clearly separate from acquiring a skill.
- Global + Local scoping lets some SubMinds be system-wide and others user/agent-specific (e.g. a particular robot's battery profile as a Local threshold).
- **Cost:** a new role-graph (schema + bootstrap), an ADR-0150 amendment, and a parallel-but-lean endowment lifecycle distinct from the skill lifecycle.

**Open:** de-endowment semantics (marker-only deprecation vs removal) follow the Phase-50 installed-skills precedent and are deferred to implementation.

## Amendment trail

- **Amends ADR-0150** — closed role-set 13 → 14 with the addition of `subminds` (Global + Local).
- Reuses the ADR-0180 write gate and the ADR-0183 install-lifecycle primitives without adopting the skill installer wholesale.
- Composes with ADR-0188 (construct) and ADR-0189 (runtime/arbitration).
