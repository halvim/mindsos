---
title: Server owns promotion orchestration; KL owns graph writes
status: Accepted
date: 2026-04-22
layer: L2
aliases: [kl-ADR-013]
---

# ADR-0050: Server owns promotion orchestration; KL owns graph writes

**Status:** Accepted

**Date:** 2026-04-22

## Context

Promotion involves: capability enforcement, multi-user lock acquisition, transient-install of offline authors, FalkorDB transaction, in-memory graph mutation, persistence, audit events, and rollback on failure. Every one of those could live in KL or the server.

## Decision

The split is deliberate. Server: `_GLOBAL_PROMOTE_LOCK`, per-user mutexes, transient installs, `MetagraphSnapshot.of(...)` before / `.restore_into(...)` on failure, FalkorDB transaction, audit events, freshness check. KL: `similarity_report` (read-only), `promote` (capability assertions, graph writes, attribution stamping, Local-draft rewrite, undo-stack for atomicity). Server calls KL inside its orchestration.

## Consequences

**Good:**
- KL testable without spinning up a server.
- Server testable with KL as a pure dependency.

**Bad:**
- Server and KL must agree on what `promote` does.

## Alternatives considered

None recorded; this was the consensus choice during the 2026-04-22 design session.
