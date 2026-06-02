---
title: DataStates carry only a structural ShapeDescriptor
status: Accepted
date: 2026-04-21
layer: L3
aliases: [capacity-ADR-004]
---

# ADR-0063: DataStates carry only a structural ShapeDescriptor

**Status:** Accepted

**Date:** 2026-04-21

## Context

Auto-discovery needs to decide "can capacity X feed capacity Y" mechanically. The more that decision depends on subjective typing, the worse auto-discovery behaves.

## Decision

`ShapeDescriptor` carries `kind`, `elem`, `fields`, and `opaque_tag` — nothing else. Two stages consuming structurally identical data are TYPE_COMPAT even if their semantics differ; `opaque_tag` is the escape hatch.

## Consequences

**Good:**
- Auto-discovery is deterministic and cheap.

**Bad:**
- Callers who want a semantic distinction must express it as a distinct shape.

## Alternatives considered

1. **Bolt on a `semantic_class` field** — rejected; re-introduces subjective typing.
2. **Let callers register compatibility edges by hand** — rejected; belongs on CONSTRAINT edges.
