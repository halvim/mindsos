# Phase 34 — Notes

## Scope shipped

L3 symmetric write contract (ADR-0146 §amendment-1 clauses 4 + 5 closed)
+ `KLWriteHandle` body wiring + ADR-0143 status flip Proposed →
Accepted. Phase 33 carry-forwards #1, #3, #5, #6, #7 closed; #2 (Phase
36) + #4 (capacity:promote:pipeline phase) remain.

- `KLWriteHandle.graph()` / `mint_iri()` / `write_and_validate()`
  bodies wired (Phase 33 stubs replaced).
- Minimal 2-entry `_IRI_BUILDERS` registry in
  `mindsos_knowledge/identifiers.py` (per-flow build per ADR-0147).
- `KnowledgeLayer.writeable(..., *, version="v1")` keyword.
- `KLWriteHandle._version` field (required, end of frozen dataclass).
- `InvocationResult.write_outcome: Optional[Any] = None` field
  (additive; default `None`).
- `runtime.invoke` bypass branch for `outputs=()` write capacities;
  raises `CapacityRegistrationError` on wrong return shape (R5 PB-G);
  stashes `WriteResult` | `ProblemTraceRecord` in `write_outcome`.
- `CapacityLayer(*, kl=None)` constructor + conditional
  `ctx.setdefault("kl", self._kl)` injection at invoke +
  start_resident (R5 PB-B — only when self._kl is not None).
- `consolidate:mm` + `trace:problem` capacity bodies rewritten:
  extract kl from context; call `handle.write_and_validate`; return
  `WriteResult`.
- CLI `_construct_invoke_layer` bootstraps fresh KL + installs writes;
  `_invocation_result_to_dict` + `_to_human` render `write_outcome`.
- DataState shapes for both capacities flipped opaque → record
  (`{"memory_id": "str", "value": "Any"}` / `{"trace_id": "str",
  "value": "Any"}`) with `opaque_tag` preserved.
- `docs/dev/review-checklist.md` NEW (3 items per R1 PB-D).

## Design saturation

5 design rounds + R4 (16 probes) + R5 (impl-start gate). ~52 picks
across rounds + ~13 §am-impl reconciliations at R4 + R5. 1 reverse
pivot (R3 PB-A reversed at R4 — `ShapeDescriptor.record` exists).

Key revisions across rounds:

- R0 PB-1: minimum-viable close (clauses 4 + 5 only); 1, 2, 3 stay
  open per §amendment-1 (no §amendment-2 needed for them — clause 1's
  text already covers deferral).
- R1 PB-A: bypass in `runtime.invoke` (not `call_capacity`); zero
  blast radius on Phase 27-shipped primitive.
- R1 PB-G: §amendment-2 narrowed to OCC defer + clause-3 partial
  close only.
- R2 PB-A: input-shape tighten REQUIRED at Phase 34 (collision with
  mint_iri kwarg surface); minimum-required record-shape.
- R2 PB-B: `write_and_validate` does NOT catch L1 raises; clause 1
  stays fully open.
- R3 PB-A reversed at R4 §am-impl-2: `ShapeDescriptor.record` exists
  in datastate.py:69; use it directly.
- R4 §am-impl-1: `Graph.add_node(value, type_name, ...)` — NOT
  `type_=`; handle's `type_` kwarg translates at L1 boundary.
- R4 §am-impl-3: NodeType locks "Memory" + "ProblemTraceEntry"
  (Phase 13 schema names; NOT ADR §Skeleton's "ConsolidatedMemory").

## Ship surface

Source NEW (0): no new source files.

Source EDITED (10):

- `mindsos_capacity/capacity.py` — `+InvocationResult.write_outcome`
  field.
- `mindsos_capacity/runtime.py` — invoke() bypass branch + lazy
  `WriteResult` import (avoid runtime ↔ write_outcome cycle).
- `mindsos_capacity/capacity_layer.py` — TYPE_CHECKING guard for
  KnowledgeLayer + `kl=None` __init__ kwarg + conditional ctx
  injection at invoke + start_resident.
- `mindsos_capacity/builtins/consolidate.py` — body rewrite + record
  DataState shape.
- `mindsos_capacity/builtins/trace.py` — body rewrite + record
  DataState shape.
- `mindsos_cli/commands/capacity.py` — `_construct_invoke_layer` KL
  + install writes; `_write_outcome_to_dict` helper; render in
  `_to_dict` + `_to_human`.
- `mindsos_knowledge/identifiers.py` — `_IRI_BUILDERS` 2-entry
  registry + `_mint_memory` + `_mint_problem_trace` wrappers.
- `mindsos_knowledge/knowledge_layer.py` — `writeable(..., version=)`
  keyword kwarg + `_version=` pass-through.
- `mindsos_knowledge/write_handle.py` — `_version: str` field +
  wired bodies for `graph()` / `mint_iri()` / `write_and_validate()`.

Tests NEW (`tests/phase_34/`, 12 files / 42 cases):

- `_fixtures.py` + `__init__.py`
- `test_write_handle_graph_body.py` (4 cases)
- `test_write_handle_mint_iri.py` (7 cases)
- `test_write_and_validate.py` (5 cases)
- `test_writeable_version_kwarg.py` (3 cases)
- `test_capacitylayer_kl_injection.py` (4 cases)
- `test_runtime_invoke_bypass.py` (5 cases)
- `test_invocation_result_write_outcome_field.py` (4 cases)
- `test_cli_invoke_write_capacities.py` (3 cases)
- `test_review_checklist_file.py` (3 cases)
- `test_phase_34_export_slate.py` (4 cases)

Phase 33 tests REPURPOSED (R4 §am-impl-5; 5 tests + 2 shape sentinels):

- `tests/phase_33/test_consolidate_mm_capacity.py`:
  - `test_mm_composite_datastates_single_member_opaque` → `_record`:
    shape.kind opaque → record + fields assertion added.
  - `test_consolidate_mm_with_session_yields_writehandle_not_wired` →
    `_succeeds_with_write_outcome`.
  - `test_consolidate_mm_emits_problem_trace_on_failure` →
    `_success_emits_no_problem_trace`.
- `tests/phase_33/test_trace_problem_capacity.py`:
  - `test_problem_trace_datastates_single_member_opaque` → `_record`.
  - `test_trace_problem_session_with_cap_reaches_handle...` →
    `_succeeds`.
  - `test_trace_problem_session_none_skips_gate_per_adr_0080` →
    `_and_succeeds`.
  - `test_trace_problem_emits_problem_trace_on_failure` →
    `_success_emits_no_problem_trace`.
- `tests/phase_33/test_kl_writeable.py`:
  - `test_handle_graph_raises_writehandle_not_wired` →
    `_returns_real_graph_at_phase_34`.
  - `test_handle_mint_iri_raises_writehandle_not_wired` →
    `_returns_iri_at_phase_34`.

STAYS: cap-denial test (R0 PB-6), scope=local+session=None ValueError
test, validate_node + validate_xref raise tests (Phase 36 wires).

Pre-emptive sentinel-flips at impl-start (4 files):

- 3 export-slate count files: function rename
  `test_phase_33_export_count_is_110` → `test_phase_34_export_count_
  is_110` (count literal 110 unchanged; Phase 34 adds zero new exports).
- 1 version literal: `tests/phase_30/test_phase_30_export_slate.py` +
  `tests/phase_31/test_phase_31_export_slate.py` —
  `"0.0.0+phase33"` → `"0.0.0+phase34"` + function rename
  `_to_phase_33` → `_to_phase_34`.

Version bump: 12 sites in 10 files (7 init.py + pyproject.toml +
manifest.toml [phase + version, 2 fields] + docker-compose.yml [2
image tags]).

## ADR amendments (parent tree per Model C)

3 ADR touches in `/Layered Intelligence/docs/decisions/adr/`:

- **ADR-0146 §amendment-2** (R1 PB-G) — narrow 2-clause Phase 34
  amendment: clause 1 OCC retry deferred (no L1 contract yet);
  clause 2 §amendment-1 clause 3 partial close (mint-key surfacing
  only). Plus §Implementation Phase 34 footer documenting clauses
  4 + 5 closure mechanism (bypass + handle bodies). Status STAYS
  Accepted (no change at Phase 34).
- **ADR-0143 Status FLIPPED Proposed → Accepted** + §Implementation
  (Phase 34 — Accepted) footer. All 3 §Accept criteria satisfied:
  (a) handle ships with wired bodies; (b) ≥2 capacities use
  `write_and_validate`; (c) review-checklist file shipped with
  "never mutates" rule.
- **ADR-0147 §Implementation (Phase 34 — partial)** footer documents
  the 2-entry registry per-flow discipline. Status STAYS Proposed
  per R0 PB-9 (Phase 35 is the canonical flip target per PHASE_MAP).

## Docs

- Halvim `docs/dev/review-checklist.md` NEW — 3 items (KLWriteHandle
  never mutates, write capacities have outputs=(), capacity bodies
  use context.get for session+kl).
- Halvim `docs/dev/internals/capacity.md` AMEND — Phase 34 section
  added (bypass + KL injection + CLI rendering + NodeType lock).
  `last_confirmed_phase: 33` → `34`.
- Halvim `docs/dev/coordinated-changes/L3-capacity-write-flows.md`
  AMEND — consolidate + trace status `stub-shipped` → `wired`;
  `last_confirmed_phase: 33` → `34`.
- Halvim `mkdocs.yml` — +1 nav entry (Review checklist — Phase 34).
- Halvim `confirmation_docs/PHASE_MAP.md` §34 — inline amendment per
  R1 PB-H (symmetric is success-path-only; failure-mode return-PTR
  deferred).

## Hotfix ledger

1 hotfix fired (well within budget of 5 per R5):

- **B-34-T1** (impl-time circular import): `runtime.py` initially
  imported `WriteResult` at module top from `write_outcome.py`, but
  `write_outcome.py` imports `ProblemTraceRecord` from `runtime.py` —
  circular. Fix: move `WriteResult` import inside the bypass branch
  body in `runtime.invoke`. Documentation note added at the runtime
  import site.

## Test counts (TBD on Docker)

Sandbox runs only the slice not transitively importing
`mindsos_server.admin` (which uses `datetime.UTC`, Python 3.11+).
Linux Docker (Python 3.12) runs the full cumulative.

- **Sandbox slice (Python 3.10):** **149 passed in 0.24s**
  (`tests/phase_27/` + `tests/phase_29-31/test_*_export_slate.py` +
  `tests/phase_33/` + `tests/phase_34/`).
- **Phase 34 isolated:** 42 passed in 0.16s.
- **Estimated cumulative on Docker:** Phase 33 baseline 3298 + ~42
  new from `tests/phase_34/` = **~3340 / 49 skip** target.

## Carry-forwards to Phase 35+

Phase 30/31/33 carry-forwards still open (unchanged):
`--session-token` CLI flag, Falkor-backed L3 bootstrap, L3 state-file
serialization, per-user ProblemTraceSink, `--install-builtins` CLI
flag, additional text-family capacities, pathfinding registered-builtin
form, L4 resident scheduler, PROMOTED breadcrumb reader (phase that
ships `capacity:promote:pipeline`).

Phase 34 new carry-forwards:

1. **`validate_node()` + `validate_xref()` body wiring** — Phase 36
   (ADR-0139); still raise `WriteHandleNotWiredError`.
2. **ADR-0146 §amendment-1 clauses 1, 2, 3** stay open. Clause 1
   (failure modes return PTR vs raise) is the load-bearing one —
   L4 consumer drives the shape.
3. **ADR-0146 §amendment-2 clause 1** OCC retry — defer until L1
   grows OCC contract.
4. **`WriteResult.extras["retry_count"]`** key reserved by convention
   (Phase 34 doesn't enforce; future retry impl populates).
5. **`--session-token` for CLI Local writes** — Phase 30
   carry-forward; without it, CLI `capacity:consolidate:mm` fails
   (scope='local' + session=None raises ValueError). Phase 34 ships
   negative-path test.
6. **`_IRI_BUILDERS` registry entries** for the 4 deferred write
   capacities — added per-flow when each capacity's L4 flow closes
   design.

## Observed quirks / process notes

- **B-34-T1 hotfix class:** new for Phase 34. L2-imports-L3 dependency
  (the `WriteResult` import in `write_handle.py` + `runtime.py`) needs
  careful import placement — Phase 33 shipped the L2 → L3 import of
  `WriteHandleNotWiredError` cleanly because that exception type
  doesn't itself import back. `WriteResult` lives in `write_outcome.py`
  which imports `ProblemTraceRecord` from `runtime.py` → cycle.
  Resolution: lazy-import inside the function body (one site).
- **Sandbox limitation reaffirmed:** `mindsos_server.admin`'s
  `from datetime import UTC` (3.11+) blocks any test transitively
  importing the server package in the Python 3.10 sandbox. The
  Phase 34-touched test slice (phase_27/29/30/31/33/34) is entirely
  sandbox-runnable because none of those phases import server.
- **R4 §am-impl-2 reverse:** R3 PB-A wrongly assumed
  `ShapeDescriptor.record` didn't exist. Probe found it at
  `datastate.py:69`. The R3 pick "stay opaque + docstring tighten"
  was reversed at R4 to "use record({...})" — cleaner, no substrate
  invention needed.
- **Phase 33 forward-anchor tests:** 5 of them needed REPURPOSE (not
  literal flip). Test bodies + names changed to reflect Phase 34's
  wired behavior. STAYS: cap-denial + scope-local-no-session
  ValueError tests; validate_node/xref still raise (Phase 36).

## Phase 34 design log

Full ledger lives in chat transcript (rounds R0 + 5 re-litigations
through R5 + impl). PR description summarises picks; this notes file
captures the impl-side observations.

## Memory edit at ship

After ship, write `[[project-mindsos-phase-34]]` memory entry per
Phase 33 precedent. Highlights:
- Cumulative N / skip M green (TBD Docker run).
- Squash sha, tag `phase-34-confirmed` placement.
- ADR-0146 §am-2 + §Impl Phase 34 footer; ADR-0143 flipped.
- Hotfix B-34-T1 (L2-imports-L3 circular import class — new).
- R3 PB-A reverse pivot at R4 §am-impl-2.
- §am-impl 13 reconciliations across R4 + R5.
- Bypass-in-runtime-invoke design pattern (R1 PB-A) — future write
  capacities that need typed return shapes follow this template.
