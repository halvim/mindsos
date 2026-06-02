---
title: REF_TYPES is open vocabulary with explicit extension recipe
status: Accepted
date: 2026-04-22
layer: L2
aliases: [kl-ADR-010]
---

# ADR-0047: REF_TYPES is open vocabulary with explicit extension recipe

**Status:** Accepted

**Date:** 2026-04-22

## Context

The initial set was `{SPECIALISES, INSTANCE_OF, RENAMES, EXTENDS, CONTRADICTS, PROXY}`. Each upper-layer role brings pressure for new values.

## Decision

`REF_TYPES` is a `frozenset` in `identifiers.py` open to additions. Extensions follow a five-step recipe: (1) add to the frozenset, (2) add to the role docs, (3) add a test, (4) optionally update any classifier, (5) run the parity test. `"PROMOTED"` was added via exactly this recipe on 2026-04-22.

## Consequences

**Good:**
- Adding a ref_type is a one-PR operation.
- Drift between code and docs is caught by the parity test.

**Bad:**
- The vocabulary will grow — periodic consolidation may be needed.

## Alternatives considered

None recorded; this was the consensus choice during the 2026-04-22 design session.
