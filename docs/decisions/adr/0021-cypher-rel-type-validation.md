---
title: Cypher rel-type identifier validation via regex
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-008]
---

# ADR-0021: Cypher rel-type identifier validation via regex

**Status:** Accepted

**Date:** 2026-04-22

## Context

FalkorDB rel-type names are spliced into Cypher as literal tokens (they cannot be parameterised). Without validation, a malicious or buggy rel-type name could inject Cypher. An allowlist of known rel types would constrain extensibility.

## Decision

Every rel-type name must match `^[A-Z][A-Z0-9_]{0,63}$`. Validation fires at schema-build time (via `validate_edge_type_identifier`) and again at persist time before splicing.

## Consequences

**Good:**
- Safe splicing without an allowlist.
- Names stay human-readable (`WORKS_AT`, `REFINES`).
- The regex is strict enough to prevent injection, loose enough that any layer can invent new types without a Core PR.

**Bad:**
- None observed.

## Alternatives considered

1. **Explicit allowlist of known types** — rejected because it blocks layer autonomy.
2. **Unvalidated splicing** — rejected because of injection hazard.
3. **Runtime escaping** — rejected because FalkorDB does not accept escaped rel-type literals.
