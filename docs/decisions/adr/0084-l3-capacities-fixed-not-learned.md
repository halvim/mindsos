---
title: L3 - Functional-category as primary axis for graphs
status: Accepted
date: 2026-04-21
layer: L3
aliases: [L3-Q1]
---

# ADR-0084: L3 - Functional-category as primary axis for graphs

**Status:** Accepted

**Date:** 2026-04-21

## Context

L3 design question Q1: Functional-category as the primary axis for graphs. The system has to organize capacities into graphs somehow. Partitioning by function (perception, comprehension, etc.) gives each capacity a natural neighborhood, keeps discovery fast, and aligns with task decomposition patterns.

## Decision

Yes. Twelve functional categories as the partition axis. Multi-graph membership (a capacity in multiple category graphs) handles cross-category cases via explicit registration.

## Consequences

**Good:**
- Fast, readable partition.
- Aligns with L4's task decomposition strategy.

**Bad:**
- Requires explicit opt-in for cross-category membership.

## Alternatives considered

None recorded; this was locked as Q1 Settled.
