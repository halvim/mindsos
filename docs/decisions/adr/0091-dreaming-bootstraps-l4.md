---
title: Bootstrapping L4's pipeline-finder via dreaming - idle-compute exploration
status: Accepted
date: 2026-04-21
layer: L3
aliases: [L3-Q8]
---

# ADR-0091: Bootstrapping L4's pipeline-finder via dreaming

**Status:** Accepted

**Date:** 2026-04-21

## Context

When the system starts, it has capacities and empty knowledge about which pipelines work. The question is how L4's pipeline-finder acquires initial confidence priors and explores the space of possible pipelines.

## Decision

The system **dreams** when no task is pending and compute is available. L4 runs maintenance, exploration, and retry loops using L3 capacities. These are not special hardwired modes but rather normal tasks enqueu ed with dream-task intents. Dreaming is the mechanism by which the system bootstraps itself and grows its effective repertoire.

Details of exploration policy, bootstrapping priors, and budget caps live in the L4 design notes, not L3.

## Consequences

**Good:**
- Dreaming is self-explanatory as a concept — idle cycles are invested in learning.
- Same machinery applies to learning and task-solving (no special path).
- High-confidence discoveries from dreaming can be promoted to Global.

**Cost:**
- Requires L4's orchestrator and learning loop to be fully specified before the system can dream effectively.

## Alternatives considered

1. **Hard-coded bootstrap in L4** — rejected (not learnable; policy frozen at system design time).
2. **External exploration tools** — rejected (divorces bootstrap from the main architecture).
