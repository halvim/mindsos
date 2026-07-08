---
title: Same-type operand arity on the capacity registration + invoke input contract (Form B)
status: Proposed
date: 2026-07-07
layer: L3
amends: [ADR-0156, ADR-0159, ADR-0072]
aliases: [Part-5, 5a, C1, operand-arity]
---

# ADR-0198: Same-type operand arity (Form B)

**Status:** Proposed (build scoped to 5a + C4; ships with ADR-0199)

**Date:** 2026-07-07 (CORE build chat — ARC comparator family)

## Context

The invoke inputs map is `Mapping[DS-IRI → value]` and `register_capacity`
emits one binary `CONSUMES` per **distinct** input DataState (ADR-0156). A
capability consuming **two operands of the same DataState type** cannot express
both — they collide on one key/edge and the operand axis is invisible. Part 6
(ADR-0072 §am-2, shipped `2676b9d`) validates inputs by **key** only
(`_validate_inputs`, `mindsos_capacity/capacity.py`), so it keys the same way.

The motivating consumer is the ARC comparator/profiler family — 14 bodies
(`same_object`/`same_shape`/`moved`/`touching`/`inset`/…), validated in
`arc_solver/PART5_OPERAND_SPEC.md`. bongard-m3 hits the identical binary shape
and co-signs. Both today would have to fake the shape as a single-input
declaration, or invent a wrapper DataState per operand type.

**Grounding verified this chat:**

- `_CapacityBase.inputs` is `Tuple[str, ...]` of IRIs; `_validate_inputs`
  computes `present = {k for k in inputs}` — a **set of keys**. Two same-type
  operands genuinely cannot be declared distinctly.
- `_validate_inputs` checks **keys only**, never value types. Core has no
  value-type-checking of operands anywhere on the invoke path.
- **Positional suffices for 14/14.** No cap needs core to know the operand
  *role* (from/to, container/contained, in/out); the role is read off slot index
  **inside the ARC body** and lives in ARC-local metadata. It never enters core.

**Justification is expressiveness + recurrence, not "execution is impossible."**
A comparator *can* execute today via a monolith-over-pair (ARC's own
`touching_delta` proves it) — but there is no shared `object_pair`/`shape_pair`
type (the existing `pairs*`/`pair` is task train-example pairs), so that path
forces every comparator-using brain to invent wrapper DataStates and re-invent
them per consumer. That recurring expressiveness gap — not a correctness defect —
is what this ADR closes.

**Consumer-discipline note.** ARC is a **committed** executing consumer, not a
live one (it cannot route comparators through `invoke` until this ships). This
build clears the "no scaffolding without a consumer" gate (design-log §0)
because it is **additive and default-inert**: `operand_arity` defaults to
today's behavior and changes nothing for any existing capacity. A non-additive
change would *not* clear the gate on a committed-not-live consumer on this basis
— which is why C3 (a context-surface narrowing) is tracked as a separate ADR
(ADR-0200) with its own, Part-6-precedent gate-clearance rationale, though it
ships in the same build.

## Decision

**Adopt Form B — a list-valued key under an additive `operand_arity`
declaration. Positional in core; roles ARC-local. Length-check only.**

1. **Registration.** Add one additive field to `_CapacityBase`
   (`mindsos_capacity/capacity.py`):

   ```python
   operand_arity: Mapping[str, int] = field(default_factory=dict)   # DS-IRI → N; absent/1 = today
   ```

   No role/label field. Default empty preserves every existing capacity without
   migration (ADR-0159 default-valued discipline). `register_capacity`
   (`validate_for_registration`) additionally rejects `operand_arity` keys that
   are not declared inputs, so a typo fails loud at registration rather than
   silently skipping the invoke-time arity check.

2. **Invoke validation.** One added branch in `_validate_inputs`: for each key
   `k` with `operand_arity[k] = N > 1`, require `inputs[k]` to be a **length-`N`
   list**. **No per-operand value-type check** — consistent with core's
   key-only discipline; core never inspects operand values. The `**inputs` body
   signature and the DS-IRI-keyed invoke path are otherwise unchanged. A body
   reads `a, b = inputs[DS_OBJECT]`.

3. **Finder untouched.** `find_pipeline` / `ConjunctionFinder` stay type-level /
   role-blind. **L4 supplies which operands** at dispatch (the correspondence /
   pairing is an L4 decision; the group→pair unpack is C4 / ADR-0199). The finder
   composes on DataState type only and never threads operand order. So the operand
   axis touches the **registration + invoke** contracts only.

4. **No graph edge for the operand axis (v1).** Like `input_group` (ADR-0159
   §am-1, Decision 8), `operand_arity` is read off the declaration and **not**
   emitted as N `CONSUMES` edges. ADR-0156's binary-edge model is unchanged; the
   operand count rides the registration field, not the topology.

**Out of scope (fenced):**

- **No fold (5b).** No same-type-operand cap folds N-of-one-type under a single
  logical role. `fold` stays unenforced (ADR-0072 §am-2). bongard-m5's fold is
  the 5b axis, separate.
- **`touching` cross-kind operands** (Object×Object / Object×Point / Point×Point,
  all typed `region`) are resolved **ARC-side**: L4 wraps operands as a `region`
  view at bind (both carry `cells`). Because 5a checks **length only**, core sees
  no value-type conflict; no flat-type/subtype machinery is added.
- **C3** (truthful MM read channel) is a **separate ADR (ADR-0200)** — it is
  subtractive (gates the `mm_handle` injection on the shipped `reads_mm` flag)
  and clears the consumer gate on the Part-6 precedent, not on additive-inertness
  like 5a/C4. It ships **in the same build/branch** as this ADR and ADR-0199 (one
  ARC comparator-family enablement, one re-pin), but is tracked separately because
  its gate-clearance rationale and blast-radius class differ.

## Consequences

- Comparator/profiler families register honestly on the true operand type
  (`object × object`) instead of a fabricated wrapper. ARC reopens D3, decomposes
  the #8 monolith, and routes through `invoke` after this + ADR-0199 ship.
- Zero behavior change for existing capacities (default-inert). No shipped-body
  audit required (unlike C3).
- `fold` enforcement remains open; the first executing `fold` consumer is the
  next trigger to revisit operand multiplicity under a single role (5b).
- **Zero task-solving payoff expected** — this is honest grounding
  (skill-acquisition done-test), not new solves.

## Alternatives considered

- **Form A — parallel positional invoke API + `(operands, context)` body
  signature.** Rejected: a second invoke path and a second body signature
  everywhere, for no expressiveness Form B lacks.
- **Wrapper DataState per operand type** (`object_pair`, `shape_pair`, …), body
  unpacks internally. Rejected: proliferates types across operand-type × consumer
  (ARC + bongard-m3 independently), types comparators on an invented bundle
  instead of the perceptual atom, and hides the operand type from the finder.
- **Per-operand value-type check in `_validate_inputs`.** Rejected: net-new
  value-type-checking core deliberately avoids, and the sole thing that would make
  `touching`'s cross-kind operands a core problem.
- **Role/label field in core** (from/to, source/target). Rejected: 14/14 bodies
  read the role off slot index; the role never needs to be a core concept.

## Supersession / amendment trail

- Amends **ADR-0159** (adds `operand_arity` to `_CapacityBase`), **ADR-0072**
  (extends the Part-6 invoke input contract with the length branch), and relates
  to **ADR-0156** (binary-edge model unchanged — operand axis is a field, not
  edges). Un-defers the `composition-lifecycle-s2-part5` park
  (COMPOSITION_LIFECYCLE_DESIGN_LOG §9/§14). Ships with **ADR-0199** (C4).
- ADR-0184's "open contract risk" (a promoted composite with same-type-operand
  inputs must carry the operand axis) resolves against this: the descriptor
  carries `operand_arity` when the eventual m5 writer lands.
