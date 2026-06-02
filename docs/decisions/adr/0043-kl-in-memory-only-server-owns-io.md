---
title: KL stays in-memory only; server owns all FalkorDB I/O
status: Accepted
date: 2026-04-22
layer: L2
aliases: [kl-ADR-006]
---

# ADR-0043: KL stays in-memory only; server owns all FalkorDB I/O

**Status:** Accepted

**Date:** 2026-04-22

## Context

An earlier draft had KL reach into FalkorDB via a persistence adapter so tests could "just work" with a real graph. That coupled the layer to a specific backend, made unit tests slow, and fought the 5-layer architecture's separation-of-concerns.

## Decision

`mindsos_knowledge/` has zero imports of any FalkorDB client, any persistence module, or any file-I/O primitive. Everything KL does is on in-memory `Metagraph` objects. The server reads from FalkorDB on login, installs the Metagraph via ADR-0042, lets KL do its writes, extracts on logout, and writes back.

## Consequences

**Good:**
- Unit tests instantiate a `KnowledgeLayer()` with no I/O, no fixtures, no containers.
- Alternate backends remain plausible.

**Bad:**
- Any feature that needs persistence awareness has to live in the server layer.

## Alternatives considered

None recorded; this was the consensus choice during the 2026-04-22 design session.
