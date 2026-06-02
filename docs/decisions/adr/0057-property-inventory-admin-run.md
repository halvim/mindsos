---
title: Property-inventory helper is admin-run, not on the hot path
status: Accepted
date: 2026-04-22
layer: L2
aliases: [kl-ADR-020]
---

# ADR-0057: Property-inventory helper is admin-run, not on the hot path

**Status:** Accepted

**Date:** 2026-04-22

## Context

Strict-schema mode rejects any property not declared on the node/edge type. Moving a role from permissive to strict requires knowing every property that has ever appeared in the wild. Automated discovery could be hot-path (validate on every write, warn on undeclared) or admin-run (scan a metagraph on demand).

## Decision

`mindsos_knowledge/schemas/strict_support.py::inventory_properties(mg, role)` scans the active role-graph and emits a report: declared properties, undeclared properties (with example nodes), and counts. It is admin-run. Write-time validation stays permissive by default.

## Consequences

**Good:**
- Strict-mode migration has a clear checklist.
- The write path stays fast.

**Bad:**
- Admins must remember to run the inventory before enabling strict mode.

## Alternatives considered

Hot-path validation with warnings — rejected because it adds latency to every write for a rare operation.
