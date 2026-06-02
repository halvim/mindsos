---
title: PromotionValidationError as KL-specific promotion failure type
status: Accepted
date: 2026-04-22
layer: L2
aliases: [kl-ADR-017]
---

# ADR-0054: PromotionValidationError as KL-specific promotion failure type

**Status:** Accepted

**Date:** 2026-04-22

## Context

Promotion can fail for four categorically different reasons: (1) permission, (2) argument, (3) lookup, (4) validation. Python's standard exceptions cover the first three. Validation doesn't map onto a stdlib class that carries enough meaning.

## Decision

Add `PromotionValidationError(KnowledgeLayerError)` to `mindsos_knowledge/exceptions.py`. `promote` raises it when Core's `add_node` rejects a draft's schema / type / property bag, or when there is no active Global role-graph. Original exception is chained via `raise … from e`.

## Consequences

**Good:**
- The server can catch validation failures distinctly from argument errors — they audit differently.
- The exception hierarchy stays small — one new class, not one per failure mode.

**Bad:**
- None observed.

## Alternatives considered

None recorded; this was the consensus choice during the 2026-04-22 design session.
