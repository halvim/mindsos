---
title: Metagraph-wide shared IdentityRegistry
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-007]
---

# ADR-0020: Metagraph-wide shared IdentityRegistry

**Status:** Accepted

**Date:** 2026-04-22

## Context

Cross-graph references (ADR-0016) need safe id resolution. If each `Graph` scoped its ids independently, `ref:lexicon = "abc-123"` would be ambiguous when two graphs happened to pick the same UUID (vanishingly unlikely but possible, and a correctness hazard either way).

## Decision

A `Metagraph` owns one `IdentityRegistry`; every contained `Graph` shares it. `add_graph` unifies the graph's registry into the metagraph's. Standalone Graphs (no metagraph) keep per-graph scope. Elements anywhere inside a metagraph are guaranteed globally unique within that metagraph.

## Consequences

**Good:**
- Cross-graph refs are trivially safe.
- No global registry needed.

**Bad:**
- Unification is a silent side-effect on `add_graph` — a caller holding `g.identity` before the call has a dangling handle.

## Alternatives considered

1. **Per-graph scope with explicit cross-graph namespacing** — rejected because it forces every ref to carry a graph prefix.
2. **Process-global registry** — rejected because it couples independent metagraphs, blocks test isolation.
