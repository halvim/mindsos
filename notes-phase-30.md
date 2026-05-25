# Phase 30 — L3 Pipeline finder + invoke runtime + ProblemTraceRecord

## phase_title

L3 Invocation + BFS Finder + ProblemTrace

## §1 Scope (PHASE_MAP §30)

**Fourth L3 ship.** Adds 2 NEW source files to existing
`mindsos_capacity/` package (`runtime.py` + `pipeline.py`) + edits 3
(`exceptions.py` +2 raisers, `capacity_layer.py` +invoke method
+problem_trace attribute, `__init__.py` +11 exports + version bump).
Adds 1 NEW CLI command file (`mindsos_cli/commands/capacity.py`) + 1
wire-up edit (`mindsos_cli/app.py`). No new top-level package (9-site
checklist N/A).

**Features shipped:**

* `mindsos_capacity.runtime` (NEW) — `invoke` free function +
  `ProblemTraceRecord` + `ProblemTraceSink` + `emit_problem_trace`.
* `mindsos_capacity.pipeline` (NEW) — `Pipeline` + `PipelineStep` +
  `find_pipeline` (datastate-keyed BFS over auto-discovered
  TYPE_COMPAT graph per ADR-0071).
* `CapacityLayer.invoke(capacity_iri, inputs, *, session=None,
  context=None, task_id=None, step_id=None) -> InvocationResult`
  method on the L3 facade — wraps `_runtime_invoke` after
  `_resolve_declaration` lookup; injects `session_user_id` +
  `session_id` into context for provenance-stamping capacities.
* `CapacityLayer.problem_trace: ProblemTraceSink` — single in-memory
  sink per layer instance (multi-tenant scoping is L4's concern via
  payload field).
* Lifted exports: `InvocationResult` + `call_capacity` (existed in
  `capacity.py` since Phase 27; public re-export new at Phase 30).
* `PipelineNotFoundError` + `ProblemTraceError` — new raisers in
  `mindsos_capacity/exceptions.py` (5→7 classes).
* `mindsos capacity find` + `mindsos capacity problem-trace tail` CLI
  verbs. No `invoke` verb at Phase 30 (R3 PB-36 lock — deferred to
  Phase 31 alongside text builtins).
* 2 Phase 28 sentinels FLIPPED — file rename
  `test_invocation_not_exported.py` → `test_invocation_exported_phase_30.py`;
  function rename `test_problem_trace_attribute_not_present_at_phase_28` →
  `test_problem_trace_attribute_present_at_phase_30`.

**Source files NEW (2):** `runtime.py`, `pipeline.py`.
**Source files EDITED (3):** `exceptions.py` (+2 classes; 5→7),
`capacity_layer.py` (+invoke method +problem_trace attribute
+ProblemTraceSink import +InvocationResult import +_runtime_invoke
import), `__init__.py` (+11 exports + docstring rewrite + version bump).
**CLI files NEW (1):** `mindsos_cli/commands/capacity.py`.
**CLI files EDITED (1):** `mindsos_cli/app.py` (register_capacity_app).

**Test files NEW (~21 in `tests/phase_30/`):** `__init__.py`,
`_fixtures.py`, `test_invoke_success_path.py`,
`test_invoke_exception_emits_trace.py`,
`test_invoke_unknown_iri_raises.py`,
`test_invoke_local_wins_resolution.py`,
`test_invoke_session_user_id_in_context.py`,
`test_find_pipeline_shortest.py`,
`test_find_pipeline_start_equals_target.py`,
`test_find_pipeline_no_path_raises.py`,
`test_find_pipeline_max_depth_exhausted.py`,
`test_find_pipeline_with_session.py`,
`test_find_pipeline_shortest_by_capacity_count.py`,
`test_problem_trace_sink_api.py`,
`test_problem_trace_record_shape.py`,
`test_emit_problem_trace_validates.py`,
`test_pipeline_dataclasses.py`, `test_cli_capacity_find.py`,
`test_cli_capacity_problem_trace_tail.py`,
`test_phase_30_export_slate.py`, `test_adr_amendment_sentinels.py`.
Plus 2 Phase 28 sentinel flips (one file rename + one function rename).

**Cumulative target:** Phase 29 baseline 3115 (memory; --skip-tests
prevented exact CONFIRMED.md capture) + ~50-60 new Phase 30 cases - 5
ADR-amendment sentinels skipping under Model C = **~3160-3170 passed,
~45 skipped** (40 inherited + 5 new Phase 30 ADR sentinels). Reconcile
from docker output at impl Step-0 per `[[feedback-phase-baseline-literal-audit]]`.

**Docs:** mkdocs.yml Capacity nav `(Phase 27, 28, 29)` →
`(Phase 27, 28, 29, 30)` + `building.md` + `retrieval.md` (both NEW).

## §2 Design rounds summary

Six rounds (R0–R5, with R4 = pre-impl probe execution). See
`confirmation_docs/PHASE_30_DESIGN_LOG.md` for full pick ledger
(~56 picks across R0-R5; zero design-pick obsolescence from R4 probes;
4 R4 sub-cases refined R3 picks).

**Key locked picks shaping ship:**

* R0 PB-1(a) — Ship existing `success:bool` + `error` `InvocationResult`
  shape; ADR-0072 §amendment-1 + §Impl footer locks the field rename
  vs §Decision text (R3 PB-35(b) strengthened to amendment).
* R0 PB-3(a) — Residents (start_resident/stop_resident/Subscription/
  ResidentError) DEFER to Phase 31 per PHASE_MAP §31 + halvim
  `exceptions.py:9-11` docstring inventory.
* R0 PB-4(a) — NEW `pipeline.py` module (not `builtins/pathfinding.py`
  which is Phase 31 territory).
* R0 PB-5(a) — `find_pipeline` takes `session: SessionArg = None`;
  halvim Phase 28 R1 PB-14 convention.
* R0 PB-6(a) → R3 PB-36(b) — DROP `mindsos capacity invoke` CLI verb
  at Phase 30; ship `find` + `problem-trace tail` only.
* R0 PB-7(c) — Ship BOTH `building.md` + `retrieval.md` at Phase 30.
* R0 PB-9(a) → R3 PB-37(a) → R4 PB-45(a) — Sentinel flip is in-place
  with file rename (whole-file sentinel) and function rename only
  (mixed-content file).
* R0 PB-13(a) — `find_pipeline` raises `PipelineNotFoundError` (not
  enveloped) per ADR-0072 §Decision carve-out.
* R1 PB-14(a) — `find_pipeline(capacity_layer, ...)` first arg —
  parent-mirror.
* R1 PB-16(a) — `task_id=None` foot-gun documented; envelope returned
  but no trace emitted.
* R1 PB-21(a) — Full 21-file `tests/phase_30/` layout (close to ~22
  estimate).
* R2 PB-26(b) → R5 PB-61 — Exit code 3 (envelope failure) MOOTED
  by R3 PB-36(b) invoke-verb drop; deferred to Phase 31.
* R2 PB-27(a) — CLI uses fresh in-memory layer per invocation; no
  Falkor L3 bootstrap at Phase 30.
* R2 PB-28(a) — `pipeline.py` uses `TYPE_CHECKING` guard for
  `CapacityLayer` type hint (circular-import insurance).
* R2 PB-29(a) — Single ProblemTraceSink per CapacityLayer per ADR-0074
  literal; multi-tenant scoping deferred to L4.
* R2 PB-30(a) — CLI Global-only at Phase 30; no `--session-token`.
* R3 PB-35(b) — ADR-0072 §amendment-1 + §Impl (not just §Impl footer).
* R3 PB-40(a) — `_fixtures.py` ships 7 helpers (DS const IRIs + 5
  capacity builders + session helper) + 3 layer builders.
* R4 PB-46(a) — `runtime.py` imports trimmed (no Capacity/Monitor/
  ResidentError; Phase 31 re-adds when residents ship).
* R4 PB-47(a) — `pipeline.py` DROPS parent's `build_bfs_capacity_declaration`
  scaffolding factory; Phase 31 ships registered builtin form directly.
* R4 PB-48(a) — `pipeline.py` imports trimmed (no SuccessorHop / View
  / CATEGORY_PATH_FINDING / capacity_iri).
* R5 PB-55(a) — ADR-0071 §Impl footer clarifies datastate-keyed BFS
  vs capacity-keyed `successors_of` (not amendment; §Decision wording
  is loose but semantically correct).
* R5 PB-62(a) — ADR-0072 §amendment-1 (above) + §Impl (below) as
  separate ADR blocks.

## §3 ADR amendments at ship (parent — no .git per Model C)

5 touches across 4 ADRs in parent `/Layered Intelligence/docs/decisions/adr/`:

* **ADR-0066 §Implementation (Phase 30)** — InvocationResult +
  call_capacity export-lift closure; capacity-IRI-form staging
  cross-cite resolved.
* **ADR-0071 §Implementation (Phase 30)** — BFS pipeline finder
  shipped; datastate-keyed (not capacity-keyed) clarification; halvim
  divergences (`session` not `user_id`, dropped `build_bfs_capacity_declaration`).
* **ADR-0072 §amendment-1 (Phase 30)** — InvocationResult field rename
  (failed→success polarity-inverted; exception→error). Semantic
  envelope-vs-raise contract preserved.
* **ADR-0072 §Implementation (Phase 30)** — invoke shipped in
  runtime.py + CapacityLayer.invoke method; task_id=None foot-gun
  documented; Phase 28 sentinels flipped.
* **ADR-0074 §Implementation (Phase 30)** — ProblemTraceSink in-memory
  per-layer; per-Local sink scoping deferred to L4; CLI tail peek-only.

## §4 Sentinel-paths additions (+2)

`mindsos_capacity/runtime.py`, `mindsos_capacity/pipeline.py`.

## §5 12-site version bump `+phase29 → +phase30`

| # | Site | Status |
|---|------|--------|
| 1 | `pyproject.toml` `[project] version` | ✅ |
| 2 | `mindsos_cli/manifest.toml` `[mindsos] phase` | ✅ |
| 3 | `mindsos_cli/manifest.toml` `[mindsos] version` | ✅ |
| 4 | `docker-compose.yml` `mindsos:phase30-prod` | ✅ |
| 5 | `docker-compose.yml` `mindsos:phase30-test` | ✅ |
| 6 | `mindsos_cli/__init__.py` `__version__` | ✅ |
| 7 | `mindsos_core/__init__.py` `__version__` | ✅ |
| 8 | `mindsos_instances/__init__.py` `__version__` | ✅ |
| 9 | `mindsos_knowledge/__init__.py` `__version__` | ✅ |
| 10 | `mindsos_admin/__init__.py` `__version__` | ✅ |
| 11 | `mindsos_server/__init__.py` `__version__` | ✅ |
| 12 | `mindsos_capacity/__init__.py` `__version__` | ✅ |

## §6 Memory edits at ship

1. NEW `project_mindsos_phase_30.md` — phase summary + halvim
   divergences + carry-forwards.
2. UPDATE `project_mindsos_phase_29.md` — close carry-forwards items
   1 (`building.md`), 2 (`mindsos capacity` CLI Typer group; partial —
   `find` + `problem-trace tail` only), 4 (Pipeline finder +
   invocation + InvocationResult/call_capacity + ProblemTraceRecord +
   sentinel flips).
3. UPDATE `MEMORY.md` index with the new Phase 30 entry.

## §7 Ship checklist (13-step ordering per Phase 28 R2 PB-28 + R0 PB-9 2-gate)

* [x] **[Sandbox]** Edit 4 parent ADRs (0066+0071+0072+0074; no git; Model C).
* [ ] **[Mac]** Verify parent ADR diffs visually.
* [ ] **[Mac]** `git checkout -b phase-30 origin/main` — **GATED ON
      Phase 29 squash-merge to main** (R0 PB-9 gate 1).
* [x] **[Sandbox]** Halvim source + tests + sentinel-paths + version
      bump + mkdocs.yml + PHASE_MAP §30 + notes-phase-30.md +
      design log.
* [ ] **[Sandbox]** Local `python3 -m pytest tests/phase_30/` →
      sandbox-runnable pass (some tests may collect-skip on Python
      3.10 due to `datetime.UTC` 3.11+ requirement; will run green in
      docker on Python 3.12).
* [ ] **[Linux]** Host pip refresh NOT needed (no new top-level pkg).
* [ ] **[Linux]** `docker compose --profile test build mindsos-test`.
* [ ] **[Linux]** **Step-0 baseline anchor** — `docker compose run --rm
      mindsos-test pytest tests/` at `phase-29-confirmed` tag for an
      authoritative Phase 29 cumulative count BEFORE Phase 30 tests
      land. Memory says 3115/40; PHASE_29_CONFIRMED.md says count=0
      (--skip-tests); PHASE_28_CONFIRMED.md says 3073/37 (Phase 28
      baseline — brief's "3079" is incorrect). Record actual in §1
      above; reconcile any drift.
* [ ] **[Linux]** `docker compose run --rm mindsos-test pytest
      tests/phase_30/ tests/`. **Expected: ~3160-3170 passed, ~45
      skipped** (40 inherited from Phase 29 + 5 new Phase 30 ADR-
      amendment sentinels skipping per Model C).
* [ ] **[Mac]** Commit + push + open PR + CI green (release.yml).
* [ ] **[Mac]** Squash-merge.
* [ ] **[Linux]** `mindsos confirm-phase --phase 30 --notes-file
      notes-phase-30.md` — **GATED ON `phase-29-confirmed` tag pushed
      + tag-CI green** (R0 PB-9 gate 2). Per
      `[[feedback-confirm-phase-machine-locality]]` the same Linux
      machine that runs this command must commit + push the
      generated `PHASE_30_CONFIRMED.md`.
* [ ] **[Linux]** Commit + push `PHASE_30_CONFIRMED.md` (same machine
      as confirm-phase).
* [ ] **[Mac]** Pull; `git tag phase-30-confirmed <follow-up-sha>` +
      push.
* [ ] **[Mac]** CI re-runs against tag green.

## §8 Hotfix ledger (R2 PB-32(a) → R5 PB-56 confirm; 1 fired)

R4 probes obsoleted ZERO design picks (4 sub-cases tightened R3
picks); R0-R5 covered ~56 picks. 1 contingency slot fired:

* **B-30-T1** (FIRED, closed) — Phase 29 sentinel-flip class. Two
  tests in `tests/phase_29/test_phase_29_export_slate.py` (Phase 29's
  R1 PB-20 + R5 PB-41 sentinels) asserted Phase 30 surface NOT
  exported + count in 82-86 range. Flipped at Phase 30 per
  `[[feedback-parity-test-sentinel-flip-at-target-phase]]`:
  ``test_phase_29_does_not_export_phase_30_surface`` →
  ``test_phase_30_surface_exported_at_phase_30`` (11 expected
  exports); ``test_phase_29_export_count_around_84`` →
  ``test_phase_30_export_count_is_95``. Discovered at first docker
  cumulative pytest run; pass count was 3171/45 (test 3170 + 1 of
  these flipped sentinels). PB-29 picked the same sentinel pattern at
  Phase 29 — should have been audited pre-impl as a Phase 29 sibling
  to PB-9. Pre-impl probe class extension: future phases must
  step-0-grep `tests/phase_(N-1)/test_phase_*_export_slate.py` for
  forbidden-Phase-N sentinels.

## §9 Carry-forwards to Phase 31+

Phase 30 closes Phase 29 carry-forwards #1 (building.md), #2
(`mindsos capacity` CLI — partial; `find` + `problem-trace tail`
only), #4 (Pipeline finder + invocation + InvocationResult/
call_capacity + ProblemTraceRecord + sentinel flips). Phase 29
carry-forwards #3 (admin-deleted auto-edge), #5 (residents + text
builtins + pathfinding-as-builtin), #6 (write capacities), #7
(additional-graph membership), #8 (bulk rediscover), #9
(include_deprecated discipline) UNCHANGED.

**Phase 30 new carry-forwards (5 items):**

1. **`mindsos capacity invoke` CLI verb** (deferred from R3 PB-36(b))
   — alongside text builtins at Phase 31 (which auto-register on
   layer construction so invoke is usable for real users).
2. **CLI `--session-token` flag** (deferred from R2 PB-30(a)) —
   Phase 31+ when server/CLI session bootstrap matures.
3. **Falkor-backed L3 bootstrap** (deferred from R2 PB-27(a)) —
   `bootstrap_l3_from_falkordb` symmetric pair helper; Phase 31+
   when first concrete consumer arises.
4. **L3 state-file serialization** (rejected at R2 PB-27(c); flagged
   for future) — would enable stateful CLI workflows without Falkor.
5. **Per-user (Local-scoped) ProblemTraceSink** (deferred from R2
   PB-29(a)) — L4 lifecycle territory; current single-sink + payload
   `user_id` provenance is the v1 pattern.
6. **Exit code 3** (mooted at R5 PB-61 by R3 PB-36(b)) — ships with
   invoke CLI verb at Phase 31.

## tester_notes

Phase 30 ships `mindsos_capacity/runtime.py` + `pipeline.py` (both
NEW) + `CapacityLayer.invoke` method + `problem_trace` attribute +
`find_pipeline` BFS + `Pipeline`/`PipelineStep` dataclasses +
`ProblemTraceRecord`/`Sink`/`emit_problem_trace` + 2 new raisers
(`PipelineNotFoundError`, `ProblemTraceError`) + `InvocationResult`/
`call_capacity` export lift. No new top-level package, no new admin/
server surface. Residents (`start_resident`/`stop_resident`/
`ResidentSubscription`/`ResidentError`) deliberately deferred to
Phase 31 per PHASE_MAP §31 + halvim docstring inventory.

Two Phase 28 sentinels flipped per
`[[feedback-parity-test-sentinel-flip-at-target-phase]]`:

1. `tests/phase_28/test_invocation_not_exported.py` →
   `test_invocation_exported_phase_30.py` (file rename; whole-file
   sentinel).
2. `tests/phase_28/test_capacity_layer_init.py::test_problem_trace_attribute_not_present_at_phase_28`
   → `::test_problem_trace_attribute_present_at_phase_30` (function
   rename only; file contains other unrelated init tests).

`mindsos capacity` CLI ships TWO verbs at Phase 30: `find` + `problem-
trace tail`. The `invoke` verb is DROPPED (R3 PB-36(b)) because CLI
constructs a fresh in-memory layer per invocation (R2 PB-27(a)) and
Phase 28's registration API is not CLI-surfaced — invoke against an
empty layer fails 100%. Both `invoke` CLI + `--session-token` arrive
at Phase 31 when text builtins make a real end-to-end demo coherent.

Verify in-container with
`docker compose run --rm mindsos-test pytest tests/phase_30/ tests/`;
expect ~3160-3170 passed / ~45 skipped (Phase 29's 40 skips + 5 new
Phase 30 ADR-amendment sentinels skipping per Model C when parent ADR
tree at `/Layered Intelligence/docs/decisions/adr/` isn't COPYed into
the test image).

**Step-0 baseline reconciliation (R3 PB-39 + PB-11):** Docker pytest at
`phase-29-confirmed` tag before Phase 30 tests land. PHASE_28_CONFIRMED.md
authoritatively reports 3073/37 (NOT 3079 as the brief and one memory
entry claim); Phase 29 actual cumulative is captured only in the
project_mindsos_phase_29.md memory file (3115/40) because Phase 29
confirm-phase ran with --skip-tests.

No new ADRs created; 4 existing ADRs (0066, 0071, 0072, 0074) get
footers (0072 also gets §amendment-1). No `mindsos_server` /
`mindsos_admin` / `mindsos_knowledge` / `mindsos_core` surface
changes — Phase 30 is pure L3.
