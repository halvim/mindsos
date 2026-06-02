---
title: Retrieval of memories via new capacity:retrieval category
status: Accepted
date: 2026-04-21
layer: L3
aliases: [L3-Q15]
---

# ADR-0097: Retrieval of memories via capacity:retrieval category

**Status:** Accepted

**Date:** 2026-04-21

## Context

L4 needs to search through past memories to find patterns, failures to retry, and examples to learn from. The question is whether retrieval is a set of fixed L3 capacities or a separate learned system in L4.

## Decision

A new `capacity:retrieval` functional category holds fixed search capacities over the `memories` role-graph in L2. Each is parameterised by a context: `by_capacity_used(c)`, `by_result(r)`, `by_input_shape(s)`, `by_pipeline_shape(p)`, `by_task_type(t)`, etc. L4 picks among them with learned confidence. Each retrieval capacity returns references (pointers) into the `memories` role-graph, never materialized values.

This makes **dreaming a well-formed task**: a dream pipeline always begins with a retrieval step, selecting which past memories to work with.

## Consequences

**Good:**
- Retrieval is inspectable and swappable like any other capacity.
- Dreaming decomposes naturally into: retrieve memories → propose alternatives → run → compare → decide.
- Multiple retrieval strategies can coexist; L4 learns which to use.

**Cost:**
- Each retrieval context is a separate capacity; the retrieval family can grow large.

## Alternatives considered

1. **Ad-hoc retrieval in L4** — rejected (not inspectable or learnable; hard-coded in L4 code).
2. **One generic retrieval capacity with parameter** — rejected (loses the benefit of having distinct, purpose-built search strategies).
