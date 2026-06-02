---
title: L2 role-graph schemas ship at strict=False with a 2-week tightening rule
status: Accepted
date: 2026-05-18
layer: L2
---

# ADR-0149: L2 role-graph schemas ship at strict=False with a 2-week tightening rule

**Status:** Accepted

**Date:** 2026-05-18

## Context

Phase 13 closes the L2 schema dispatch table: 8 named-role schema
builders + a parametric `alignment` builder + a `schema_for_role`
dispatch function. Four are seed-role ports from v3; five are NET-NEW
upper-layer schemas (`promoted_pipelines`, `task_patterns`,
`memories`, `problem_trace`, `capacity_state`) constructed from the
payload sketches in `_source_backup/docs_legacy_full/DESIGN_UPPER_LAYER_ROLES.md`
§2.1.

The five upper-layer roles are in active design flux — L4 and L5 will
refine payloads as they implement. Shipping strict schemas now would
cause write rejections every time an upper layer adds a property.
Shipping lenient schemas now accepts churn at the cost of losing
typo protection during the design period.

The seed roles (ontology, lexicon, concepts, alignment) were already
`strict=False` in v3. The decision applies uniformly across all 9
role-graphs.

## Decision

All 9 L2 role-graph schemas ship at `strict=False` by default. The
`build_<role>_schema(strict: bool = False)` signature plumbs the flag
through; callers (Phase 14 KL bootstrap, tests) may override.

**Per-role tightening to `strict=True` requires three preconditions:**

1. The inventory helper (legacy `strict_support.py` sketch from
   `DESIGN_UPPER_LAYER_ROLES.md` §4.5; deferred to first-consumer
   phase) is run against the role-graph in question. Output: per-type
   property key sets observed in actual writes, cross-referenced
   against the current schema's declared properties.
2. A **2-week-no-edit observation period** during which the role's
   schema receives no NodeType / EdgeType / HyperEdgeType amendments
   (purely additive property declarations don't count). This window
   gives downstream phases (Phase 14-17 for seed roles; Phase 24-30
   for upper-layer) time to surface real edge cases.
3. An explicit per-role ADR amendment to this ADR's §Revisions,
   naming the role being flipped, citing the inventory output, and
   listing the PropertyType declarations being added to the
   NodeTypes.

The Phase 13 sentinel test
`tests/phase_13/test_strict_false_sentinel.py` enforces precondition
(3) — any flip that bypasses the ADR amendment trips the test.

ADR-0017 §amendment-1 cross-links this ADR.

## Consequences

**Good:**
- Upper layers iterate freely during the design period.
- Inventory-helper output is the explicit anchor for tightening
  decisions — no guessing at PropertyType enum values.
- Sentinel test catches accidental flips at PR review time.

**Bad:**
- Typo protection is deferred to Phase 36 (hybrid validators).
- `strict_support.py` inventory helper is a real deliverable owed to
  the first-tightening phase — not free.

## Alternatives considered

1. **Ship some schemas strict, some lenient** — rejected. Uniform
   policy is simpler to communicate; per-role decisions create N
   bikeshed conversations.
2. **Ship all strict; flip lenient on demand** — rejected because
   strict-tighten requires PropertyType declarations that nobody
   has data to populate yet.
3. **Defer the L2 schema dispatch entirely until Phase 14** — rejected
   because Phase 14's KL bootstrap (`ensure_role_graph(mg, role)`)
   needs `schema_for_role(role)` to exist.

## Revisions

(None yet. Per-role tightening will append rows here.)

## Source

Phase 13 design log §1 PB-7. Locked 2026-05-18.
