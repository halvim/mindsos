---
title: Five admin-authored CONSTRAINT kinds; intra-category only in the slice
status: Accepted
date: 2026-04-21
layer: L3
aliases: [capacity-ADR-011]
---

# ADR-0070: Five admin-authored CONSTRAINT kinds

**Status:** Accepted

**Date:** 2026-04-21

## Context

L4 pipeline assembly has to respect operational rules (mutual exclusion, ordering, rate limits, approval requirements, version gates) that aren't derivable from shape. These rules live somewhere — either baked into L4 policy code, or declared as edges that L4 reads.

## Decision

Edge-native. Five kinds: `MUTUALLY_EXCLUSIVE`, `MANDATORY_BEFORE`, `RATE_LIMIT`, `REQUIRES_APPROVAL`, `REQUIRES_L2_VERSION`. `add_constraint(source, target, kind, ...)` writes a `:CONSTRAINT` edge with `constraint_kind` set. In the vertical slice endpoints must share a category graph; cross-category constraints are a phase-2 `MetaEdge` extension.

## Consequences

**Good:**
- Declarative, inspectable, traceable.
- Admin changes show up as data, not code deploys.

**Cost:**
- Intra-category restriction is pragmatic (vertical slice stays small); open-concerns C2 tracks the follow-up.

## Alternatives considered

1. **L4-side policy tables** — rejected (admins and L4 would drift out of sync).
2. **A sixth "custom code" constraint** — rejected (arbitrary code in constraint payload defeats inspectability).

## §Implementation (Phase 28 — 2026-05-25, closure footer at Phase 29 — 2026-05-25)

Phase 28 shipped `CapacityLayer.add_constraint(source, target, kind, *, session, note, rate_limit)` writing a `:CONSTRAINT` edge with `constraint_kind` set + intra-category endpoint validation + 5-kind `CONSTRAINT_KINDS` whitelist + `iter_constraints` reader. ADR-0068 (`constraint_kind` property key) covered in Phase 28 via the `EDGE_CONSTRAINT` EdgeType property-whitelist in `schemas.py`.

**Phase 29 closure.** Phase 28 R0 PB-11 locked "API at 28; enforcement at 29" — the "enforcement at 29" half was reframed and **superseded** by Phase 29 R0 PB-1 pick (a): runtime constraint enforcement is L4's concern per ADR-0092 (constraints are admin-authored signals L4 reads when assembling pipelines), not an L3 invocation-time check. ADR-0092's `Decision` explicitly delegates runtime semantics to L4. The Phase 29 ship therefore introduces NO new constraint-related code; the only Phase 29 test against the constraint surface is a sentinel re-asserting `constraint_kind` round-trips through `add_constraint` + `iter_constraints` (no new behaviour). Cross-category constraints (currently rejected with `ConstraintViolationError` "Cross-category constraints are not supported in the Phase 28 vertical slice") remain a phase-2 MetaEdge extension when a real L4 caller needs them.

## §Amendment (Phase 42 — ADR-0156)

Capacity flow topology underlying constraint endpoints is now the explicit bipartite `PRODUCES`/`CONSUMES` IntergraphEdge set (TYPE_COMPAT retired). The 5 CONSTRAINT kinds + their admin-authored semantics are unchanged.
