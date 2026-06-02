---
title: Instance overrides persisted under ov__* prefix
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-012]
---

# ADR-0025: Instance overrides persisted under ov__* prefix

**Status:** Accepted

**Date:** 2026-04-22

## Context

`ElementInstance.overrides` is a free-form dict. Persisting overrides as top-level properties on `:ElementInstance` rows would collide with Core's own metadata (`id`, `metagraph_id`, `kind`, `source_id`, …). Namespacing was required.

## Decision

Overrides serialise to properties whose key is `ov__<original_key>`. The loader strips the `ov__` prefix and rebuilds the overrides dict.

## Consequences

**Good:**
- No collision with Core metadata.
- Loader logic is a one-line strip.

**Bad:**
- A user property whose key happens to start with `ov__` gets mis-routed as an override on load.

## Alternatives considered

1. **Nested property with a single `overrides` JSON string** — rejected because FalkorDB cannot filter inside JSON strings.
2. **Separate `:Override` nodes edged to the instance** — rejected because it adds a persistence round-trip per override.
