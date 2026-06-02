# Phase 32 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

Integration B: L0+L1+L2+L3 read-side end-to-end scripted scenario

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

### Background

Second cross-layer integration ship (after Phase 26a/26b's Integration A) per PHASE_MAP §32. Scaffolding for the Phase 38 vertical slice. **Net-new features: No. Net-new test code: yes** — scenario harness only (`tests/phase_32/`) plus 2 sentinel-flips in `tests/phase_30/` + `tests/phase_31/`. Zero source changes; zero ADR amendments; zero mkdocs touches.

Integration B exercises the Phases 02-31 stack co-resident through a single `test_integration_b` scenario (11 step helpers + ScenarioState thread). PHASE_MAP §32's 7 substeps unpacked to 11 helpers per R2-PB-1: server bootstrap → admin login → KL bootstrap + import → L3 Global + Local bootstrap → install_text_capacities → find pipeline → CLI invoke → problem-trace tail → logout → re-login for audit → query-audit.

**Integration B is co-resident execution, NOT co-resident persistence** (R0-PB-7 lock). L1/L2 substrate lives in FalkorDB (via `bootstrap_global_pair_from_falkordb`); L3 substrate is in-memory Python — every `mindsos capacity invoke` rebuilds Global + auto-installs text builtins via the CLI's `_construct_invoke_layer`. Phase 30 carry-forward #3 (Falkor-backed L3 bootstrap) stays open.

### Design saturation

Five design rounds (pre-R0 + R0-R3) + R4 pre-impl probe execution. R4 ran 16 probes against the shipped halvim surface; surfaced 7 §am-impl reconciliations (concrete IRI literals; CLI flag names `--start`/`--target`; `CapacityLayer` constructor-bootstrap vs classmethod-bootstrap; InvocationResult envelope field name `outputs` plural; `find_pipeline` single-Pipeline return; query-audit wire shape; conftest fixture re-use safety) + 1 reverse pivot (R1-PB-1 CLI find smoke → negative-path-only per R4 §am-impl-5; `mindsos capacity find` builds empty layer → exit 1 PipelineNotFoundError by construction).

Locked picks before impl: single admin user (α5); CLI + in-process mix per substep; smoke-assert pattern (no golden snapshot); fixture text = `"the cat sat"`; substep 7 invoke uses `--input-file` form; substep 8 problem-trace tail asserts empty-by-fresh-construction; substep 11 query-audit asserts `{EVT_BOOTSTRAP: 1, EVT_LOGIN: 2, EVT_LOGOUT: 1}` (EVT_AUDIT_QUERY filtered per Phase 21 B-21-T1).

### Ship surface

Source NEW: **none**. Source EDITED: **none**. ADR amendments: **none**. mkdocs touches: **none**.

Tests NEW (5 files):

- `tests/phase_32/__init__.py`
- `tests/phase_32/conftest.py` (~85 LOC; copied verbatim from `tests/phase_26b/conftest.py` per R1-PB-3; pytest conftest discovery is package-scoped — no collision with 26b)
- `tests/phase_32/fixtures/__init__.py`
- `tests/phase_32/fixtures/_text_importer.py` (~55 LOC; `TextFixtureImporter` — 1-Frame-node into `concepts` role)
- `tests/phase_32/test_integration_b.py` (~270 LOC; 11 step helpers + `ScenarioState` + `test_integration_b`)

Tests EDITED (2 files — pre-emptive sentinel flips at impl-start, NOT counted toward hotfix budget per R1-PB-7):

- `tests/phase_30/test_phase_30_export_slate.py` — `test_version_bumped_to_phase_31` → `_to_phase_32`; literal `0.0.0+phase31` → `+phase32`.
- `tests/phase_31/test_phase_31_export_slate.py` — same flip; `test_phase_31_export_count_is_97` UNCHANGED (count stays 97 — Phase 32 ships zero new exports).

Version bump: 12 sites in 10 files — 7 package `__init__.py` `__version__` literals + `pyproject.toml` + `mindsos_cli/manifest.toml` (phase + version) + `docker-compose.yml` (2 image tags).

### ADR amendments

**None.** Phase 32 is integration; no policy decisions. R4 probes confirmed zero §amendment surface required. The §am-impl reconciliations were wording corrections against shipped surface; no policy changes.

### Hotfix ledger

**0 hotfixes** fired during ship (well within budget of 5 per α7). R4's 16-probe pass caught every surface mismatch up front; the reverse pivot of R1-PB-1 (CLI find smoke → negative-path) was design-time, not impl-time.

### Test counts

- **Docker (Linux, prod image):** **3235 passed / 49 skipped / 109 warnings** in ~31 min. Phase 32 isolated: 1 passed (`test_integration_b`). Skip delta from Phase 31 baseline: **0** — zero new ADR-amendment sentinels per α9.
- **Sandbox (Python 3.10):** N/A — repo requires Python 3.12; sandbox couldn't install pytest. Static checks only (py_compile + import-symbol resolution against source tree) passed.

### Smoke tests on prod image

1. `doctor --self-test --json` confirms all 7 packages at `0.0.0+phase32`; `expected_compose_image_phase: "32"`; clean (`ok: true`, `failures: []`).
2. The integration scenario itself = the load-bearing smoke. `test_integration_b` covers the L0+L1+L2+L3 read-side flow end-to-end through 11 substeps; passing implies the seven verbs (`server bootstrap admin`, `server login`, `capacity find`, `capacity invoke`, `capacity problem-trace tail`, `server logout`, `server query-audit`) are wired correctly + the in-process L3 path composes with the FalkorDB-backed KL substrate.

### Carry-forwards to Phase 33+

Phase 30 carry-forwards still open (deferred per Phase 31 + Phase 32 narrow scope):

- `--session-token` CLI flag (Phase 30 #2).
- Falkor-backed L3 bootstrap (Phase 30 #3).
- L3 state-file serialization (Phase 30 #4).
- Per-user (Local-scoped) ProblemTraceSink (Phase 30 #5).

Phase 31 carry-forwards still open:

1. `--install-builtins=<family,...>` CLI flag on `mindsos capacity invoke` — Phase 33+ when a 2nd builtins family ships.
2. Additional text-family capacities (`text.lowercase` / `text.normalize_nfc` / etc.) — Phase 33+.
3. Pathfinding registered-builtin form — Phase 33+ if vertical slice surfaces a real consumer; else permanent retirement.
4. L4 resident scheduler / state-snapshot lifecycle per ADR-0099 — L4 ship.

Phase 32 new carry-forward (1 item):

1. **CLI `mindsos capacity find` positive-path coverage** — the CLI verb builds an empty layer (no auto-install, unlike `invoke`'s `_construct_invoke_layer`); substep 6 settled for negative-path smoke (exit 1 + `PipelineNotFoundError`) per R4 §am-impl-5. Positive-path CLI find requires either (a) a `--install-builtins=` flag on `find` symmetric with Phase 31 carry-forward #1, or (b) Phase 30 carry-forward #3 (Falkor-backed L3 bootstrap rendering `find`'s layer non-empty by construction).

### Observed quirks / process notes

- **R4 saturation paid off** — 16 probes surfaced 7 §am-impl reconciliations + 1 reverse pivot, all design-time. Zero impl-time hotfixes. The `[[feedback-export-slate-sentinel-audit]]` N-2..N-1 scope extension (Phase 31 B-31-T2 lesson) caught both version sentinels (`phase_30/` + `phase_31/`) at pre-emptive flip; the count sentinel `test_phase_31_export_count_is_97` correctly stayed unflipped (Phase 32 ships zero new exports).
- **CapacityLayer "bootstrap" is a constructor**, not a classmethod. Memory entry `[[project-mindsos-phase-28]]`'s "bootstrap" terminology was loose; actual API is `CapacityLayer()` for Global + `layer.local_metagraph(user_id)` for lazy Local creation. Documented at R4 §am-impl-4 for future-phase readers.
- **Sandbox Python 3.10 vs repo Python 3.12** blocked pytest install on the Mac sandbox; runtime smoke deferred to Linux Docker per `[[feedback-two-machine-setup]]`. Pre-ship static checks (py_compile + import-symbol resolution) caught one unused import (`CapacityRegistrationError`) before commit.
- **`mindsos capacity find` is empty-by-construction in Phase 32** — the CLI's `_construct_global_layer` doesn't auto-install builtins (only `invoke`'s `_construct_invoke_layer` does). Substep 6's CLI smoke asserts exit 1 + `PipelineNotFoundError` rather than positive-path discovery. Honest about the carry-forward; integration test still covers positive-path via in-process `find_pipeline(state.layer, ...)`.
- **Hotfix-free ship** — first integration phase to ship with 0 hotfixes (Phase 26b fired 8; Phase 31 fired 3 mostly sentinel-flips). The R4 probe extension to 16 (vs Phase 31's 10) was load-bearing — Probes 12+13 (CLI flag shapes + IRI string literals) caught what would otherwise have been at least 3 mid-impl reconciliations.
