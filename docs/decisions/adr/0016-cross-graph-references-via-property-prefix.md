---
title: Cross-graph references via ref:* property prefix
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-003]
---

# ADR-0016: Cross-graph references via ref:* property prefix

**Status:** Accepted

**Date:** 2026-04-22

## Context

Knowledge-Layer-style graphs (ontology, lexicon, concepts, …) need to reference each other. Cypher relationships can't cross Core's "edges live inside one graph" invariant, and inventing a new primitive ("XRef") would add a persistence path and a loader step for every new reference shape.

## Decision

Cross-graph references are properties whose key starts with `ref:` and whose role follows: `ref:anchor = <node_id>`, `ref:global_lexicon = <node_id>`. `iter_ref_properties(props)` enumerates them. Core emits and reads the convention; it does **not** validate targets (see ADR-0021).

## Consequences

**Good:**
- No new primitive; iterable via a prefix scan.
- Graph-pair agnostic; easy to extend to new roles without schema changes.

**Bad:**
- Refs are strings — Core cannot detect dangling or cross-metagraph references.

## Alternatives considered

1. **A first-class `XRef` primitive** — rejected because it ballooned the persistence surface for marginal gain.
2. **Sentinel edge types with a `metagraph_id` property** — rejected because it conflates with Core's "edges live in one graph" invariant.
