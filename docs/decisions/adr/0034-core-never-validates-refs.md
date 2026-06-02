---
title: Core never validates cross-graph ref targets
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-021]
---

# ADR-0034: Core never validates cross-graph ref targets

**Status:** Accepted

**Date:** 2026-04-22

## Context

ADR-0016 introduced `ref:*` properties. Core emits and iterates them but performs no validation that the target id exists. Every higher layer re-implements the check or accepts dangling refs. The Knowledge Layer shipped `_check_global_target_exists` for its narrow Local → Global need.

## Decision

Core does not validate reference targets. Validation is delegated to higher layers. A diagnostic helper `Metagraph.verify_refs()` (scan-only, returns dangling refs) is a proposed addition that would give upper layers a ready tool without baking integrity into the write path.

## Consequences

**Good:**
- Core's write path stays cheap and role-resolution-agnostic.

**Bad:**
- Dangling refs are a silent data-integrity risk until caught by a layer that looks.

## Alternatives considered

1. **Opt-in `enforce_ref_integrity=True` on Metagraph** — rejected for now because of role-resolution ambiguity.
2. **Eager walker on every write** — rejected because of N+1 read cost.
