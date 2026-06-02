---
title: Single mindsos_core package with submodules
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-005]
---

# ADR-0018: Single mindsos_core package with submodules

**Status:** Accepted

**Date:** 2026-04-22

## Context

A "data", "schema", "persistence", and "reconstruction" split across sibling packages would force every consumer to learn four import prefixes for what is really one concept: "Core".

## Decision

One package, `mindsos_core`, with submodules (`models/`, `schema/`, `persistence/`, `reconstruction/`, `cypher/`). Public API is re-exported from `mindsos_core/__init__.py`. Consumers type `from mindsos_core import Metagraph`, not `from mindsos_core.models.metagraph import Metagraph`.

## Consequences

**Good:**
- One import path per concept.
- Cohesion at the package boundary.
- Free to reshuffle internal submodules without breaking callers.

**Bad:**
- The package grows over time; current size is manageable.

## Alternatives considered

1. **Four packages** — rejected because it externalises an internal organisation that callers never want to think about.
