---
title: MetagraphSnapshot is in-process only, not serialisable
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-015]
---

# ADR-0028: MetagraphSnapshot is in-process only, not serialisable

**Status:** Accepted

**Date:** 2026-04-22

## Context

A serialisable snapshot would be useful for cross-process rollback, debug capture, or time-travel. But giving it a disk format would couple Core to a rollback contract — every future Metagraph attribute change would be a snapshot-format migration.

## Decision

`MetagraphSnapshot` stores Python object references (deep-copied). It is not pickle-tested, has no `to_json()` / `from_json()`, and the docstring explicitly forbids disk use.

## Consequences

**Good:**
- Rollback stays narrowly scoped.
- Core schema can evolve without worrying about snapshot-format compatibility.

**Bad:**
- Cross-process rollback, if ever needed, is a separate concern with its own durable format.

## Alternatives considered

1. **JSON-serialisable snapshot** — rejected because of Core-to-rollback-format coupling.
2. **Pickle-based durability** — rejected because pickle is fragile and security-hazardous.
