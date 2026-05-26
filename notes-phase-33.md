# Phase 33 — Notes

## Scope shipped

L3 write capacities — **stub-phase carve-out** per ADR-0146 §amendment-1.
Two capacities lit; rest of ADR-0145's 5 categories deferred to L4-flow
phases per ADR-0147 per-flow build discipline.

- `capacity:consolidate:mm` — NEW category `CATEGORY_CONSOLIDATE` lit;
  Local write to `memories` role-graph via `KLWriteHandle(scope='local')`.
- `capacity:trace:problem` — first WRITE occupant of existing
  `CATEGORY_TRACE`; Global write to `problem-trace` role-graph via
  `KLWriteHandle(scope='global')`.

Both capacities stub-bind to `KLWriteHandle` whose body methods
(`graph()` + `mint_iri()` + `validate_node()` + `validate_xref()`) raise
`WriteHandleNotWiredError`. `metagraph()` returns the real L1 Metagraph
(read-only state inspection — safe at stub phase per R3 PB-S Pick).

## Design saturation

4 design rounds + R4 (31 probes) + R5 (impl-start gate). 56 picks across
the 4 rounds + 7 §am-impl reconciliations at R4. R4 reconciliations
were all design-time tweaks (no reverse pivots).

Key revisions across rounds:

- R1 PB-A revised R0 PB-3: stub raises; capacity does NOT catch; invoke
  envelope surfaces as `success=False, error=<...>` (the `call_capacity`
  output-validation contract is incompatible with returning a bare
  `ProblemTraceRecord` from a write capacity).
- R3 PB-S revised R1 PB-D: `mint_iri()` joins the raise set due to
  version-handling ambiguity post-Phase-17 retirement (ADR-0150
  §amendment-3 lock — no active-version dispatch mechanism exists).
  Only `metagraph()` returns real; the other 4 handle methods raise.
- R2 PB-J + R2 PB-V: session routing via `context["session"]` injection
  (4-site amendment in `capacity_layer.py` — `invoke` + `start_resident`
  symmetric). Capacity bodies extract via `(context or {}).get("session")`.
- R2 PB-K: write capacities have `outputs=()` — pipeline terminators.
  Phase 30's BFS finder treats them as dead-ends; auto-discovery emits
  zero outbound TYPE_COMPAT edges from them.

## Ship surface

Source NEW (4):

- `mindsos_capacity/write_outcome.py` — `WriteResult` dataclass +
  `WriteOutcome` union alias.
- `mindsos_capacity/builtins/consolidate.py` — `capacity:consolidate:mm`
  family.
- `mindsos_capacity/builtins/trace.py` — `capacity:trace:problem` family.
- `mindsos_knowledge/write_handle.py` — `KLWriteHandle` frozen dataclass
  (5 methods; partial stub).

Source EDITED (6):

- `mindsos_capacity/identifiers.py` — `+CATEGORY_CONSOLIDATE`;
  `FUNCTIONAL_CATEGORIES` 12 → 13.
- `mindsos_capacity/exceptions.py` — `+WriteHandleNotWiredError`,
  `+CapabilityDeniedError` (2 new classes; 7 → 9 raisers).
- `mindsos_capacity/capacity_layer.py` — 4-site amendment for
  `ctx.setdefault("session", session)` (invoke lines 524-525 block;
  start_resident lines 599-600 block).
- `mindsos_capacity/__init__.py` — +13 exports (97 → 110); version
  bump.
- `mindsos_knowledge/knowledge_layer.py` — `+writeable(session, role, scope)`
  method; `TYPE_CHECKING` block added for `SessionProtocol` +
  `KLWriteHandle`.
- `mindsos_knowledge/__init__.py` — `+KLWriteHandle` export; version
  bump.

Tests NEW (10 files / 58 cases): `tests/phase_33/{_fixtures.py,
__init__.py, test_consolidate_mm_capacity.py,
test_exceptions_writehandle_capabilitydenied.py,
test_functional_categories_13.py,
test_invoke_session_context_injection.py, test_kl_writeable.py,
test_outputs_terminator_discovery.py, test_phase_33_export_slate.py,
test_trace_problem_capacity.py, test_write_outcome_dataclass.py}`.

Pre-emptive sentinel-flips (3 files / 5 sites):

- `tests/phase_30/test_phase_30_export_slate.py` —
  `test_version_bumped_to_phase_32` → `_to_phase_33`; literal flip.
- `tests/phase_31/test_phase_31_export_slate.py` —
  `test_version_bumped_to_phase_32` → `_to_phase_33`; literal flip.
- `tests/phase_31/test_phase_31_export_slate.py` —
  `test_phase_31_export_count_is_97` → `_is_110`; count flip.

Version bump: 12 sites in 10 files (7 init.py + pyproject.toml +
manifest.toml [phase + version] + docker-compose.yml [2 image tags]).

## ADR amendments (parent tree per Model C)

4 ADR touches:

- **ADR-0146 Status flipped Proposed → Accepted** + 5-clause
  §amendment-1 (stub-phase raise / context routing / placeholder
  DataStates / outputs=() / L2 stub home) + §Implementation footer.
- **ADR-0143 §Implementation footer** (stub-only Phase 33). Status
  STAYS Proposed (§Accept criterion (c) — review-checklist — waits
  for Phase 34).
- **ADR-0145 §Implementation footer** — `consolidate` category lit;
  partial-flip; 4 categories deferred to L4-flow phases. STAYS
  Proposed.
- **ADR-0147 §Implementation footer** — 2 capacities built per-flow
  (anticipatory; capacities exist before L4 flows that consume them);
  §Accept criterion (c) vacuously satisfied for halvim (KL never
  shipped the deprecated write API). STAYS Proposed.

## Docs

- Parent `docs/dev/internals/capacity.md` AMENDED — added L3 write
  capacities section (symmetric contract, failure-mode table,
  Phase 33 stub-phase carve-out, terminator semantic). Satisfies
  ADR-0146 §Accept criterion (c).
- Halvim `docs/dev/internals/capacity.md` NEW — package-internals
  doc with Phase 33 details + links to parent for canonical contract.
- Halvim `docs/dev/coordinated-changes/L3-capacity-write-flows.md`
  NEW — per-flow tracker (8 rows: 2 shipped + 6 deferred). Satisfies
  ADR-0147 §Accept criterion (b).
- Halvim `docs/usage/capacity/categories.md` AMENDED — 12 → 13
  categories + write-capacity note + link to ADR-0145.
- Halvim `mkdocs.yml` — 2 new nav entries (internals/capacity.md +
  coordinated-changes/L3-capacity-write-flows.md).

## R4 probe results

31 probes executed against branch base; 7 §am-impl reconciliations
surfaced:

1. `KL.bootstrap()` has NO `strict` kwarg — `(*, id_strategy=None)`.
2. `setdefault("session", session)` is a 4-site amendment (invoke +
   start_resident, 2 lines each).
3. `tests/phase_30/test_invoke_session_user_id_in_context.py:65-70`
   compatible with new `"session"` key (membership-only assertions).
4. `_LocalTestSession.has()` returns `True` unconditionally; Phase 33
   ships `_CapAwareTestSession` for cap-denial fixtures.
5. `tests/phase_32/test_phase_32_export_slate.py` does NOT exist
   (Phase 32 shipped zero new exports); forward sentinels live in
   `tests/phase_31/test_phase_31_export_slate.py` only.
6. `__all__` count baseline 97; Phase 33 ships +13 → 110 (not the
   estimated 109).
7. KL Global has 6 roles; Local has 2 (capacity-state + memories) —
   routing confirmed at runtime.

## Smoke tests (sandbox)

- `pytest tests/phase_33/` — **58 passed in 0.19s** (Python 3.10 sandbox).
- `pytest tests/phase_30/test_phase_30_export_slate.py
  tests/phase_31/test_phase_31_export_slate.py tests/phase_33/` —
  **67 passed in 0.18s** (sentinel flips verified).
- Full cumulative suite blocked on sandbox Python 3.10 (`datetime.UTC`
  is 3.11+); runs on Linux Docker per `[[user-two-machine-setup]]`.

## Test counts (TBD — Docker run)

Estimate vs Phase 32 baseline:

- Phase 32 cumulative docker: **3235 / 49 skip / 109 warnings**.
- Phase 33 isolated: **58 passed** (sandbox; expect same in Docker).
- Phase 33 cumulative estimate: **3293 / 49 skip** (no new ADR-amendment
  sentinels at Model C runtime parity — parent ADR dir not COPYed into
  runtime image, so the §am footers don't add new skip cases).

## Carry-forwards

- ADR-0143 §Accept criterion (c) — `docs/dev/review-checklist.md` with
  "KLWriteHandle never mutates" rule — DEFERRED to Phase 34 (when the
  working body lands; checklist meaningful at that point).
- `mindsos_capacity/templates/write_capacity.py` per ADR-0146 §Impl —
  NOT shipped at Phase 33 (2 reference capacities serve as templates;
  formal template file unnecessary until contract shape stabilises).
- CLI write-capacity tests — DEFERRED to Phase 34+ per R2 PB-L Pick
  (CLI `mindsos capacity invoke` works for writes by construction;
  Phase 33 doesn't add NEW CLI tests for them).
- `_construct_invoke_layer` auto-install for write capacities —
  DEFERRED to Phase 34+ per R2 PB-O Pick (in-process tests install
  manually).

## Memory edit at ship

`[[project-mindsos-phase-17-retired]]` line 29 — replace "at Phase 33"
with the phase-of-`capacity:promote:pipeline`-ship deferral. PROMOTED
breadcrumb reader is symmetric with the promote-write capacity, which
deferred OUT of Phase 33 scope per Round 0 PB-1 (narrow). Edit happens
post-ship on Mac side per `[[user-two-machine-setup]]`.

## Phase 33 design log

Full ledger lives in chat transcript (rounds R0-R3 + R4 probe execution
+ R5 readback). PR description summarises picks; this notes file
captures the impl-side observations.

## Observed quirks / process notes

- **R4 saturation paid off** — 31 probes surfaced 7 §am-impl
  reconciliations design-time; **0 hotfixes** during impl phase. Phase
  32's 16-probe + 7-reconciliation pattern carries forward; net-new
  Phase 33 adds 15 probes covering KL surface + session-routing impact.
- **Python 3.10 sandbox limitation** — `mindsos_server.admin` imports
  `from datetime import UTC` (Python 3.11+). Sandbox can't run the
  cumulative suite; phase-only suite runs cleanly. Linux Docker
  (Python 3.12) runs the full sweep.
- **`Capacity(outputs=())` registered uniformly** — `_CapacityBase.
  validate_for_registration` accepts empty tuple; `call_capacity` line
  220-224 only fires "expected mapping" raise if the impl RETURNS a
  single value. Phase 33 impls always raise before returning; Phase 34
  needs to navigate this (likely via separate `write_invoke` entry
  point that bypasses call_capacity).
- **CompositeInstance signature mismatch** — ADR-0146 §Skeleton's
  `mm.summary` / `mm.root_id` / `mm.task_pattern_iri` don't exist on
  halvim's `CompositeInstance` (it has `id` / `metagraph_id` / `members`
  / `bundle_overrides`). Resolved by Round 1 PB-B Pick: opaque
  placeholder DataStates; capacity body never touches the input value
  (handle raises before access).
- **Forward-anchor sentinel scope** — Phase 33's pre-emptive flip
  covered 3 files / 5 sites. Per Phase 31 B-31-T2 lesson, the audit
  walked `tests/phase_(N-2..N-1)/` (phase_30 + phase_31). Phase 32
  has no export-slate file; no flip needed there.
