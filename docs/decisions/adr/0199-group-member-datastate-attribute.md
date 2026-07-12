---
title: Group / member DataState registration attribute (typed L3→L4 iteration seam)
status: Accepted
date: 2026-07-07
layer: L3
amends: [ADR-0159, ADR-0156]
aliases: [C4, group-member, datastate-group]
---

# ADR-0199: Group / member DataState attribute

**Status:** Accepted (shipped 2026-07-07, main 54b00c0, tag operand-arity-groups-readsmm-confirmed; built with ADR-0198 + ADR-0200)

**Date:** 2026-07-07 (CORE build chat — ARC comparator family)

## Context

A DataState whose value is a **group** (a list/set of individually-addressable
members — `objects*`, `points*`, `pairs*`) has no typed distinction from its
**member** (`object`, `point`, `pair`). L4 must iterate the group to feed
member-consuming capacities (the comparator picks a pair out of `objects*`,
per ADR-0198), but nothing in the registration types that seam.

Grounding: `DataState` (`mindsos_capacity/datastate.py`) is a frozen dataclass
with `name`, `shape`, `description`, `provenance_category`, `l2_roles`. The
finder already treats `objects*` and `object` as **distinct IRIs** and never
bridges them — so this is a *typing/metadata* gap, not a finder-behavior gap.
ARC's atom table (`arc_solver/ATOM_TABLE.md`) records the group registry
(`objects*→object`, `points*→point`, `pairs*→pair`); `CORE_REQUESTS.md` C4 is
the ask. This replaces the dropped C2 ("runtime fan-out as a finder feature") —
fan-out is an L4 concern by design; C4 only types where L4 iterates.

## Decision

**Add two additive, default-absent attributes to `DataState`:**

```python
group: bool = False
member_ds: Optional[str] = None    # DS-IRI of the member type; required iff group
```

- **Group and member stay distinct DataState types.** The finder never bridges
  them (it already doesn't — distinct IRIs). `member_ds` is a pointer L4 reads to
  know what the unpack loop yields; core adds no fan-out or cardinality behavior.
- **L4 owns the unpack loop.** Registration types the L3→L4 iteration seam;
  runtime fan-out is expressible **without** finder cardinality.
- **Emitted to node props** (`to_properties`) for inspectability, alongside the
  existing shape/role keys.
- **Validation** (`validate_datastate`): if `group is True`, `member_ds` must be
  non-empty; if `group is False`, `member_ds` must be absent. Member-IRI
  **existence is not validated at v1** — no consumer requires it and the pointer
  is advisory metadata L4 reads. DataStates register in any order, so an
  existence check would need a seal-time pass; deferred until a consumer needs
  it (consumer discipline, §0).
- **Naming follows semantics** (documentation convention, not enforced): group →
  plural + `*` rendering; member → singular. A single entity that internally
  holds a set (e.g. `palette`) is **not** a group — it is one opaque value.

**Additive / default-inert.** Absent `group`/`member_ds` = today's behavior; no
existing DataState changes. Clears the design-log §0 gate on the same
additive-inertness basis as ADR-0198.

## Consequences

- The comparator dispatch reads honestly: L4 unpacks `objects*` (group), picks a
  pair, invokes the comparator with two positional operands (ADR-0198). C4 types
  the group; 5a expresses the arity. They are complementary and ship together.
- No finder change, no cardinality in the finder, no new edges.
- ARC group-naming cleanup (`arc.object` → `arc.objects*` / `arc.object`) becomes
  expressible; that rename is ARC-side (deferred demo chat), not core.

## Alternatives considered

- **Runtime fan-out as a finder feature (the dropped C2).** Rejected: fan-out is
  L4 by design; putting cardinality in the finder conflates composition with
  iteration.
- **Infer group-ness from `ShapeDescriptor.kind == "list"`.** Rejected: a list
  shape is a value shape, not a semantic "group of individually-addressable
  members with a distinct member type." `palette` (a list-backed single entity)
  would be miscategorized. The distinction must be declared, not inferred.
- **A single `member_ds` with `group` inferred from its presence.** Rejected in
  favor of the explicit `group` flag for a self-documenting, independently
  validatable declaration.

## Supersession / amendment trail

- Amends **ADR-0159** (DataState registration gains `group`/`member_ds`) and
  relates to **ADR-0156** (bipartite topology unchanged — the seam is metadata L4
  reads, not new edges). Replaces the dropped C2. Ships with **ADR-0198**.

## Amendment 1 (2026-07-11) — attribute renamed `group` → `collection`

The typing attribute `group` (field, emitted node prop, and `validate_datastate`
messages) is renamed to `collection`; `member_ds` is unchanged. **Pure rename,
zero behaviour change.**

Reason: "group" is an overloaded domain word — the ARC brains use `group` /
`Group` for a composite of ≥2 objects that functions as one. A `group=True`
DataState is really a *collection* (an ordered list, dups allowed), distinct from
that domain entity. Renaming the typing attribute frees "group" for its domain
meaning and disambiguates DataState names inside brains.

Scope: `mindsos_capacity/datastate.py` + `tests/composition_lifecycle/`
(`test_group_member_datastate.py` → `test_collection_member_datastate.py`). The
prop is write-only (inspectability only; never round-tripped — reactivation
rebuilds from code factories, not props), so no data migration is required in
core; existing persisted nodes keep an inert `group:true` breadcrumb, and no
read path exists to dual-read.

**Deprecated constructor alias (transition window).** `DataState` accepts a
deprecated `group=` keyword (an `InitVar`, so `ds.group` is *not* stored — reads
must use `ds.collection`). Passing `group=True` folds into `collection` and emits
a `DeprecationWarning`. This lets not-yet-migrated consumers (arc3) keep
constructing without breaking mid-transition. Drop the alias once consumers move
to `collection=`.

The `C4` / `group-member` / `datastate-group` aliases and this file's number are
retained for history; the original decision text above is left intact as the
record of what shipped 2026-07-07.
