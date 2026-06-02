---
title: Schema strictness is opt-in per Schema(strict=...)
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-004]
---

# ADR-0017: Schema strictness is opt-in per Schema(strict=...)

> *See `confirmation_docs/PHASE_MAP.md` §5 for footnoted clarifications through Phase 05d (the strictness model also gates property-type validation on the four `MetagraphSchema` vocabularies — `IntergraphEdgeType` (Phase 05b), `IntergraphHyperEdgeType` (Phase 05c), `MetaEdgeType` + `MetaHyperEdgeType` (Phase 05d)). Inline footnoting deferred to Phase 38 per shipped precedent.*

**Status:** Accepted

**Date:** 2026-04-22

## Context

Different datasets live at different points on the strictness spectrum. DOLCE wants every property validated; exploratory user-authored graphs want to stash arbitrary keys while they're being figured out. One-size-fits-all strictness would force either all datasets into loose mode or block every prototype.

## Decision

`Schema(strict=True/False)` is a per-schema flag. `strict=True` validates property types on every write; `strict=False` accepts any property value and trusts the caller.

## Consequences

**Good:**
- Stable types get enforcement; exploratory types stay fluid.
- Tests can flip strictness without rewriting schemas.

**Bad:**
- Mixed strict/loose at the *property* level is not expressible — strictness is per-schema, not per-property.

## Alternatives considered

1. **Always strict** — rejected because it kills prototyping.
2. **Always loose** — rejected because it defers all type bugs to runtime.
3. **Per-property strictness** — deferred; worth revisiting when user-facing config surfaces appear.

## Revisions

### amendment-1 — L2 role-graph schemas at `strict=False` with 2-week tightening rule (Phase 13, 2026-05-18)

Phase 13 ships nine L2 role-graph schemas under
`mindsos_knowledge/schemas/`:

* 4 seed: `ontology`, `lexicon`, `concepts`, `alignment` (parametric).
* 5 upper-layer (NET-NEW): `promoted_pipelines`, `task_patterns`,
  `memories`, `problem_trace`, `capacity_state`.

**All 9 default to `strict=False`** per Phase 13 PB-3. Per-role
tightening to `strict=True` requires THREE preconditions:

1. The inventory helper (legacy `strict_support.py` sketch from
   `DESIGN_UPPER_LAYER_ROLES.md` §4.5; deferred to first-consumer
   phase) is run and reports which property keys L4 has actually been
   writing under `strict=False`.
2. A **2-week-no-edit observation period** during which the role's
   schema receives no NodeType / EdgeType / HyperEdgeType amendments.
3. An explicit ADR amendment naming the per-role flip and citing
   the inventory output.

The Phase 13 regression test
`tests/phase_13/test_strict_false_sentinel.py` parametrises over all
9 builders and asserts `schema.strict is False`. Any future
strict-tighten PR must (a) update the sentinel test, (b) amend this
ADR with a new revision row naming the per-role flip, (c) cite the
inventory output. ADR-0149 owns the full strictness-policy
documentation; this revision only names the cross-link.

See also: Phase 13 `confirmation_docs/PHASE_13_DESIGN_LOG.md` PB-3.
