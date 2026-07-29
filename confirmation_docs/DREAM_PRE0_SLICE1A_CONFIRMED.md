# DREAM PRE-0 Slice 1a — L2 node-edit path (CONFIRMED)

**Status:** gate-green on branch `feat/dream-build` @ `9900487`. Linux gate
**4348 passed / 12 skipped / 1 xpassed / 0 failed** (containerized full, live
FalkorDB, 2026-07-27) — baseline 4343 + 5 new; 0 regressions. **HEAD confirmed
`9900487` on the gate box before the run** (first attempt reported a stale 4343 —
the box's local `feat/dream-build` was 4 commits behind origin; fixed with
`git reset --hard origin/feat/dream-build`, then re-gated). NOT yet on main.

## What
First shipped **edit path at L2** — the reusable primitive the whole streaming
Episode lifecycle (and the dream's later write-backs) sits on.

- `mindsos_knowledge/write_handle.py` — new `KLWriteHandle.update_and_validate(*,
  iri, field_updates, content_fields=frozenset(), via_lazy_inline=False,
  is_settled=False, is_admin=False)`. Resolves the existing node by `iri`, runs
  `validate_mutation_discipline` per field against the caller-supplied
  content/metadata partition, then applies the in-memory merge via
  `Graph.update_node_properties` when permitted. First real caller of the
  previously-dormant `validate_mutation_discipline` (ADR-0153 §3, deferred at
  Phase 43 "until the first capacity that edits an existing node").
- Persistence stays the server's job (KL never touches Falkor) — same posture as
  creates via `write_and_validate`.

## Why this shape
- The L2 layer was **write-once** (only `write_and_validate` / `add_node`); node
  editing was declared but unbuilt. This wires the existing pieces
  (`validate_mutation_discipline` + `Graph.update_node_properties`) into the L2
  boundary so discipline is enforced per-field.
- `episodic_memories` is `APPEND_ONLY_WITH_LAZY_INLINE`: metadata fields freely
  mutable; content fields frozen except `via_lazy_inline=True`. That maps exactly
  to the Episode lifecycle (Slice 1b): progress/`state` = metadata (free), frozen
  memory = content (written at close via lazy-inline).

## Tests
`tests/phase_43/test_l2_edit_path.py` (5): content-field edit blocked without
lazy-inline (+ node left unchanged); allowed with `via_lazy_inline`; metadata
field (`state`) freely mutable; empty-partition treats all fields as metadata
(partition-wiring proof); missing node → `IdentityError`. The discipline RULES
are separately covered by `test_validate_mutation_discipline.py`.

## Inert / additive
No callers yet (Slice 1b is the first). Purely additive — a new method + a new
test file; `write_and_validate` untouched. 0 regression surface.

## Next
Slice 1b — add a `state` **metadata** field to the Episode schema; open the
Episode at Request start; close on any terminal decision (flip `state=closed` +
lazy-inline the content via this primitive); rework crash-recovery to scan
`state=open` (subsuming the in-memory marker); mark needs-input `suspended`;
realign the failure vocab (decision ≠ "failed"; failed = crash/open only).
