---
title: Reserved property keys form a metagraph-wide union
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-019]
---

# ADR-0032: Reserved property keys form a metagraph-wide union

**Status:** Accepted

**Date:** 2026-04-22

## Context

Writing a property named `id` as user data would overwrite Core metadata. A per-type reserved list would mean the same key is allowed on one type and forbidden on another — confusing and unsafe.

## Decision

`RESERVED_PROPERTY_KEYS = {id, uuid, node_id, edge_id, graph_id, metagraph_id, instance_id, type, type_name, kind, label, role, value, source_id, target_id}`. Writing any of these as a user property raises `PropertyShapeError`. The set is a union: once reserved, always reserved.

## Consequences

**Good:**
- Clear, global contract for users.
- Adding a new reserved key is an additive change.

**Bad:**
- The set is conservative; if a user has legitimate reason to attach a "type" property they must rename it.

## Alternatives considered

1. **Per-type reserved keys** — rejected because of inconsistent UX.
2. **Namespace-prefix reservation** — rejected because it adds verbosity to every check.
