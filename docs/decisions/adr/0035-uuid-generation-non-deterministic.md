---
title: UUID generation is non-deterministic
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-022]
---

# ADR-0035: UUID generation is non-deterministic

**Status:** Accepted

**Date:** 2026-04-22

## Context

`generate_uuid()` mints a fresh UUID4 on every call. Re-running an importer produces a new set of ids. Test goldens need to stub `generate_uuid`; cloning a metagraph can't preserve stable mapping; Layer 3 idempotent-derivation pipelines can't diff runs by id.

## Decision

Core keeps UUID4. Determinism is delegated to higher layers that own the content (the Knowledge Layer mints stable IRIs from source content where possible).

## Consequences

**Good:**
- Core stays simple; no opinion on what "stable" means for a given element.

**Bad:**
- Testing Layer 3+ derivations requires id-stubbing or content-based stable ids upstream.

## Alternatives considered

Pluggable id-strategy on `Metagraph` (e.g. seeded UUID5 from content hash) — deferred; worth revisiting when Layer 3 idempotency becomes a blocker.
