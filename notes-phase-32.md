# Phase 32 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

Integration B: L0+L1+L2+L3 read-side end-to-end scripted scenario

## tester_notes

### Background

Second cross-layer integration ship (after Phase 26a/26b's Integration A) per PHASE_MAP §32. Scaffolding for the Phase 38 vertical slice. **Net-new features: No. Net-new test code: yes** (scenario harness only — `tests/phase_32/` + 2 sentinel-flips in `tests/phase_30/` + `tests/phase_31/`).

Zero source changes; zero ADR amendments. Phase 32 exercises the Phases 02–31 stack co-resident through a single `test_integration_b` scenario (11 step helpers + ScenarioState thread).

**Integration B is co-resident execution, not co-resident persistence** (R0-PB-7 lock). L1/L2 substrate lives in FalkorDB (via `bootstrap_global_pair_from_falkordb`). L3 substrate is in-memory Python — every `mindsos capacity invoke` rebuilds Global + auto-installs text builtins via the CLI's `_construct_invoke_layer`. Phase 30 carry-forward #3 (Falkor-backed L3 bootstrap) stays open.

### Design saturation

Five design rounds (pre-R0 + R0–R3) + R4 pre-impl probe execution. R4 ran 16 probes against the shipped halvim surface; surfaced 7 §am-impl reconciliations (concrete IRI literals; CLI flag names; CapacityLayer constructor-bootstrap vs classmethod-bootstrap; InvocationResult envelope field name `outputs` plural; `find_pipeline` single Pipeline return) + 1 reverse pivot (R1-PB-1 CLI find smoke → negative-path-only per R4 §am-impl-5; CLI find builds empty layer → exit 1 by construction).

Locked picks before impl: single admin user (α5); CLI + in-process mix per substep; smoke-assert pattern (no golden snapshot); fixture text = `"the cat sat"`; substep 7 invoke uses `--input-file` form; substep 8 problem-trace tail asserts empty-by-fresh-construction; substep 11 query-audit asserts `{EVT_BOOTSTRAP:1, EVT_LOGIN:2, EVT_LOGOUT:1}` (EVT_AUDIT_QUERY filtered).

### Ship surface

**No source changes.** No ADR amendments. No mkdocs touches.

Tests NEW (5 files):

- `tests/phase_32/__init__.py`
- `tests/phase_32/conftest.py` (~85 LOC; copied verbatim from `tests/phase_26b/conftest.py`)
- `tests/phase_32/fixtures/__init__.py`
- `tests/phase_32/fixtures/_text_importer.py` (~55 LOC; TextFixtureImporter — 1-Frame-node into `concepts` role)
- `tests/phase_32/test_integration_b.py` (~270 LOC; 11 step helpers + ScenarioState + `test_integration_b`)

Tests EDITED (2 files):

- `tests/phase_30/test_phase_30_export_slate.py` — `test_version_bumped_to_phase_31` → `_to_phase_32` (literal `0.0.0+phase31` → `+phase32`)
- `tests/phase_31/test_phase_31_export_slate.py` — same flip; `test_phase_31_export_count_is_97` UNCHANGED (count stays 97 — Phase 32 ships zero new exports)

Version bump (12 sites in 10 files): 7 package `__init__.py` `__version__` literals; `pyproject.toml`; `mindsos_cli/manifest.toml` (phase + version); `docker-compose.yml` (2 image tags).

### ADR amendments

**None.** Phase 32 is integration; no policy decisions. R4 probes confirmed zero §amendment surface required.

### Hotfix ledger

_TBD — filled after `confirm-phase` runs on Linux. Budget = 5 per α7. Pre-emptive sentinel-flips at impl-start (2 version sentinels) are NOT counted (R1-PB-7)._

### Test counts

_TBD — fill after Linux Docker run. Expected baseline: **3235 passed / 49 skipped** (Phase 31 baseline 3234/49 + 1 new `test_integration_b`). No new skip count delta — zero new ADR-amendment sentinels._

### Smoke tests on prod image

_TBD — fill after Linux smoke. Expected:_

1. `doctor --self-test --json` confirms all 7 packages at `0.0.0+phase32`; `expected_compose_image_phase: "32"`; clean.
2. Integration scenario itself = the smoke test (test_integration_b covers L0+L1+L2+L3 read-side flow end-to-end).

### Carry-forwards to Phase 33+

Phase 30 carry-forwards still open:

- `--session-token` CLI flag (Phase 30 #2).
- Falkor-backed L3 bootstrap (Phase 30 #3).
- L3 state-file serialization (Phase 30 #4).
- Per-user (Local-scoped) ProblemTraceSink (Phase 30 #5).

Phase 31 carry-forwards still open:

1. `--install-builtins=<family,...>` CLI flag on `mindsos capacity invoke` — Phase 33+ when a 2nd builtins family ships.
2. Additional text-family capacities (`text.lowercase` / `text.normalize_nfc` / etc.) — Phase 33+.
3. Pathfinding registered-builtin form — Phase 33+ if vertical-slice surfaces a real consumer.
4. L4 resident scheduler / state-snapshot lifecycle per ADR-0099 — L4 ship.

Phase 32 new carry-forwards (1 item):

1. **CLI `mindsos capacity find` positive-path coverage** — the CLI verb builds an empty layer (no auto-install, unlike `invoke`'s `_construct_invoke_layer`); substep 6 settled for negative-path smoke (exit 1 PipelineNotFoundError) per R4 §am-impl-5. Positive-path CLI find requires either (a) a `--install-builtins=` flag on `find` (symmetric with Phase 31 carry-forward #1), or (b) Phase 30 carry-forward #3 (Falkor-backed L3 bootstrap making `find`'s layer non-empty by construction).

### Observed quirks / process notes

_TBD — fill after smoke + ship._
