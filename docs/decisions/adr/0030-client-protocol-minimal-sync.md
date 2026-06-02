---
title: Client Protocol is minimal and synchronous
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-017]
---

# ADR-0030: Client Protocol is minimal and synchronous

**Status:** Accepted

**Date:** 2026-04-22

## Context

Core's persistence abstraction is consumed by every layer above it. Every additional method on the protocol is a constraint on every future driver. Async, transactions, and cancellation each add surface area.

## Decision

The `Client` Protocol exposes exactly three methods: `run_query(query, params) -> QueryResult`, `run_batch(statements) -> List[QueryResult]`, `close()`. No async. No transactions (FalkorDB doesn't expose them). No cancellation. No per-call timeout. `run_batch` is sequential; a failure mid-batch leaves partial writes.

## Consequences

**Good:**
- New client implementations are cheap (InMemoryClient is ~35 lines).
- Higher layers that need async / timeout / cancellation wrap the protocol.

**Bad:**
- Every layer would pay for hooks it doesn't use if baked in.

## Alternatives considered

1. **Rich protocol with observer hooks baked in** — rejected as premature.
2. **Async-first** — rejected because FalkorDB driver is sync.
