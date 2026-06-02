---
title: Admin enforcement is capability-based, not role-string-based
status: Accepted
date: 2026-04-22
layer: L2
aliases: [kl-ADR-009]
---

# ADR-0046: Admin enforcement is capability-based, not role-string-based

**Status:** Accepted

**Date:** 2026-04-22

## Context

The first draft used `session.is_admin: bool` checks. That conflates "is this a super-user" with "may this principal do this specific thing." It also breaks down the moment a second admin role appears.

## Decision

Admin powers decompose into a capability set: `can_read_other_locals`, `can_write_global`, `can_promote`, `can_hard_delete_archived`. KL methods check the specific capability they need. `actor_role` on the Session is informational; enforcement is always `session.has(cap)`.

## Consequences

**Good:**
- Fine-grained enforcement at the KL boundary.
- New admin roles are zero-cost.

**Bad:**
- Every admin method must name the right capability.

## Alternatives considered

None recorded; this was the consensus choice during the 2026-04-22 design session.

## Revisions

### amendment-1 (Phase 18 ship — 2026-05-21) — documentary: UPPER casing alignment

**Trigger:** This ADR's §Decision spells the four KL-relevant
capability constants in lower-case (matching ADR-0041 §Decision).
ADR-0002 §Decision uses UPPER. Phase 18 PB-4 picked UPPER as
canonical; ADR-0041 §amendment-1 records the alignment. This
amendment mirrors that decision for ADR-0046 so the codebase has a
single casing convention.

**Amended behavior:** the four capability strings named in this ADR's
§Decision (`can_read_other_locals`, `can_write_global`, `can_promote`,
`can_hard_delete_archived`) are re-cited as `CAN_READ_OTHER_LOCALS`,
`CAN_WRITE_GLOBAL`, `CAN_PROMOTE`, `CAN_HARD_DELETE_ARCHIVED`. The
runtime behavior described by the ADR is unchanged — capability-based
enforcement still uses `session.has(CAP)` against the named constants.

See `halvim_mindsos/confirmation_docs/PHASE_18_DESIGN_LOG.md` §1
rounds 1-2 PB-4 for the casing decision rationale.
