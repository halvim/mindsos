# Phase 31 — Notes

## phase_title

L3 Residents + Text Builtins + Invoke CLI

## §1 Scope (PHASE_MAP §31 + inline amendment 2026-05-25)

**Per PHASE_MAP §31** (post-inline-amendment):

- Resident start / stop / list (descriptive only, no thread spawn — ADR-0073).
- Install text builtins (raw text / tokens / sentences + space/sentence split).
- Pathfinding remains the function-form `find_pipeline` shipped Phase 30 (no registered-builtin form).
- `mindsos capacity invoke` CLI verb (closes Phase 30 carry-forward #1+#6).

**Inline amendment recorded in PHASE_MAP §31** (2026-05-25):

Prior wording: "install pathfinding" (third bullet). Narrowed to "expose for use" per ADR-0071 §Implementation (Phase 31) footer. Rationale: the registered-builtin form (parent's `build_bfs_capacity_declaration`) requires synthetic DataStates for `start` / `target` / `pipeline` that leak the IRI-as-reference shape into the DataState vocabulary, and has no Phase-31 consumer. Function-form `find_pipeline` (Phase 30) is canonical. Phase 32+ Integration B may surface a real consumer; the registered form ships then if so.

**Carry-forwards from Phase 30 closed at Phase 31:**

- `mindsos capacity invoke` CLI verb (Phase 30 carry-forward #1).
- Exit code 3 (envelope failure) (Phase 30 carry-forward #6).

**Phase 30 carry-forwards still open** (deferred per pre-R0 PB-α):

- `--session-token` CLI flag (Phase 30 #2).
- Falkor-backed L3 bootstrap (Phase 30 #3).
- L3 state-file serialization (Phase 30 #4).
- Per-user (Local-scoped) ProblemTraceSink (Phase 30 #5).

## §2 Design rounds summary

Six design rounds (pre-R0 + R0-R5). ~38 picks. Reverse-pivots: 0.

| Round | Picks | Key locks |
|-------|-------|-----------|
| pre-R0 | 7 | Scope narrowed; pathfinding-registered retires; per-layer registry; opt-in install; hybrid exit codes; stale arithmetic corrected |
| R0 | 8 | Method-only residents; declaration source of truth; eq=False handle; `text.X` naming; nested builtins; --input-json XOR --input-file; exit code map; sentinel-paths +2 |
| R1 | 8 | `_subscriptions` in `__init__`; strict stop; idempotent install w/ partial-state; sessionless invoke; full envelope --json; ResidentError(CapacityLayerError) |
| R2 | 8 | ResidentSubscription stays in runtime.py; shared _fixtures; no test-file cap; no Phase-32 forbidden sentinel; ADR-0073 §am-1 single 4-clause batch; per-phase ADR footers; inline PHASE_MAP edit; 10-probe R4 |
| R3 | 8 | Source-first; ResidentError on wrong-type; CapacityRegistrationError pass-through on unknown IRI; custom JSON encoder for Exception; always-install builtins; cumulative 49 skips; docstring structure locked R3; default --human |
| R4 | 1 (+confirmations) | All 10 probes clean; zero reverse-pivots; `context=` kwarg retained |
| R5 | 3 | B-31-T0 sentinel-flip in-place; hotfix budget 3; baseline gate ship-checklist step 0 |

Full pick ledger: see chat transcript at design lock (no separate design-log file shipped at Phase 31 — pick-table embedded above).

## §3 ADR amendments at ship (parent — no .git per Model C)

4 touches across 3 ADRs in parent `/Layered Intelligence/docs/decisions/adr/`:

1. **ADR-0073 §amendment-1** — 4-clause batch (per Phase 22 ADR-0012 §am3 precedent): per-layer registry (clause 1); drop `subscribes_to` kwarg (clause 2); `ResidentSubscription` eq=False (clause 3); wrong-type raises `ResidentError` (clause 4).
2. **ADR-0073 §Implementation (Phase 31)** — names the 3 halvim source files touched + locks the `start_resident` signature.
3. **ADR-0088 §Implementation (Phase 31)** — granularity validated via `Monitor.subscribes_to` source-of-truth + builtins/text.py precedent.
4. **ADR-0071 §Implementation (Phase 31)** — separate footer from Phase 30's; obsoletes `build_bfs_capacity_declaration`; locks function-form `find_pipeline` as canonical.

ADRs 0099 + 0100 are reference-only at Phase 31 (no §Implementation footers; the contract is for L4 to consume — Phase 31 ships only the descriptive substrate per ADR-0073).

## §4 Sentinel-paths additions (+2)

Verify before commit: `tests/_shared/sentinel_paths.py` should add 2 entries for the new files:

- `mindsos_capacity/builtins/__init__.py`
- `mindsos_capacity/builtins/text.py`

If the precedent is "subpackages tracked by package-name only," reduces to +1 (`builtins/` only). R4 Probe 5 confirmed no circular-import risk in the parent shape; Phase 31 mirrors.

## §5 12-site version bump `+phase30 → +phase31`

Confirmed bumped (verified in §7 ship checklist):

| Site | File |
|------|------|
| 1 | `pyproject.toml` |
| 2 | `mindsos_capacity/__init__.py` |
| 3 | `mindsos_core/__init__.py` |
| 4 | `mindsos_knowledge/__init__.py` |
| 5 | `mindsos_admin/__init__.py` |
| 6 | `mindsos_instances/__init__.py` |
| 7 | `mindsos_server/__init__.py` |
| 8 | `mindsos_cli/__init__.py` |
| 9 | `mindsos_cli/manifest.toml` |
| 10 | `docker-compose.yml` (mindsos prod image tag) |
| 11 | `docker-compose.yml` (mindsos-test image tag) |
| 12 | `mindsos_cli/manifest.toml` `[mindsos] phase = "31"` (separate literal from `version`) |

## §6 Memory edits at ship

Memories to add / update:

- `[[project-mindsos-phase-31]]` — NEW; phase-31-confirmed tag + SHA + cumulative test counts.
- `[[feedback-export-slate-sentinel-audit]]` — UPDATE if Phase 31 surfaces a new lesson (none expected; B-30-T1 class already documented).

## §7 Ship checklist (13 steps; mirror Phase 30)

0. **[Linux user]** Verify Phase 30 baseline gate BEFORE branch creation:
   ```
   docker compose --profile cli build mindsos
   docker compose run --rm mindsos doctor --self-test --json
   # Verify: expected_compose_image_phase: "30"; all 7 pkgs at 0.0.0+phase30
   docker compose --profile test build mindsos-test
   docker compose run --rm mindsos-test pytest tests/ -q
   # Verify: 3173 passed, 45 skipped baseline
   ```
   HALT if mismatch.
1. **[Mac/git]** Confirm `phase-30-confirmed` tag's release.yml green at origin/main; branch `phase-31` off `origin/main` (DONE).
2. **[Linux user]** Re-run R4 probes on the branch (probe execution is source-grep; same result expected as design-pass).
3. **[Mac impl]** Source files in PB-25 order (1→7) (DONE).
4. **[Mac impl]** ADR §amendments per §3 above (DONE).
5. **[Mac impl]** PHASE_MAP §31 inline edit per §1 above (DONE).
6. **[Mac impl]** B-31-T0 sentinel-flip in `tests/phase_30/test_phase_30_export_slate.py` (DONE).
7. **[Mac impl]** `tests/phase_31/` per §test-inventory (DONE — 25 test files + `__init__.py` + `_fixtures.py`).
8. **[Linux user]** `pytest tests/phase_31/` green BEFORE cumulative sweep per `[[feedback-test-order-current-then-cumulative]]`.
9. **[Linux user]** Cumulative `pytest tests/` — verify ~3228 passed / 49 skipped (±3).
10. **[Linux user]** `mindsos confirm-phase --phase 31 --notes-file notes-phase-31.md` on the SAME Linux machine that will commit + push `PHASE_31_CONFIRMED.md` per `[[feedback-confirm-phase-machine-locality]]`.
11. **[Mac/git]** Pre-push cleanup: `rm *.bak **/*.bak` (sandbox FS left sed backup artifacts; .gitignore covers them but on-disk should be cleaned). PR squash-merge → main; verify `confirmation_docs/PHASE_31_CONFIRMED.md` at main HEAD.
12. **[Mac/git]** Tag `phase-31-confirmed` at main confirmation-doc-bearing SHA per `[[feedback-release-tag-after-squash-merge-only]]`; push tag; verify release.yml green.

## §8 Hotfix ledger preamble

Hotfix budget per R5 PB-35: up to 3 slots.

Likely axes (informed by Phase 28-30 precedents):

- **B-31-T1**: subpackage import resolution. First `builtins/` subdir under `mindsos_capacity/`; sentinel-paths config or import-order surprise.
- **B-31-T2**: cumulative literal-decay. Version bump `+phase30 → +phase31` trips a test literal somewhere unexpected (e.g. doctor self-test, manifest parity).
- **B-31-T3**: CLI exit-code mismatch. Typer's `--json` flag ordering quirk per Phase 21 precedent, or CliRunner-vs-shell exit-code semantics.

Hotfix discipline: each in own branch, squash-merge, tag at confirmation-doc SHA. Document in tester_notes if any fire.

## tester_notes

### Background

Fifth L3 ship per PHASE_MAP §31. Adds 2 EDITED + 2 NEW `mindsos_capacity/` modules + 1 EDITED CLI command + 25 test files. No new top-level package; no new admin/server surface. First subpackage under `mindsos_capacity/` (`builtins/`). 4 ADR amendments across 3 ADRs in parent tree (Model C).

Residents are descriptive (ADR-0073) — no event loop, no thread spawn. The per-layer registry (`self._subscriptions: Dict[str, ResidentSubscription]`) closes ADR-0073 §Cost row's "module-level dict's sharing across layer instances" hazard. Halvim divergences from parent across 4 clauses in ADR-0073 §amendment-1.

Text builtins ship the vertical-slice family (3 DataStates + 2 capacities) plus an idempotent installer with partial-state detection (R1 PB-12 lock). NOT auto-installed on `create_global()` (R0 PB-ε opt-in); CLI's fresh-layer init calls `install_text_capacities()` explicitly.

`mindsos capacity invoke` CLI verb closes 2 Phase 30 carry-forwards. Hybrid exit codes (R0 PB-7 lock): `--human` exits 0/1/3 by envelope state; `--json` always exits 0 with `success` in payload. Inputs: `--input-json '<json>'` XOR `--input-file <path>` (R1 PB-14 mutex lock).

Pathfinding-as-registered-builtin formally retires at Phase 31 (PHASE_MAP §31 inline amendment + ADR-0071 §Implementation Phase-31 footer). Parent's `build_bfs_capacity_declaration` stub never ports.

### Design saturation

Six design rounds. R4 ran the locked 10 probes (PB-24) with zero reverse-pivots; 1 doc-defect surfaced (Phase 30 `__init__.py` "Excluded (defer)" had a stale "auto-register on layer construction" claim — resolved by Phase 31's docstring rewrite, no separate fix). R5 surfaced one mechanical sentinel-flip (B-31-T0 pre-emptive) + hotfix budget + baseline gate.

### Ship surface

**Source NEW (2):** `mindsos_capacity/builtins/__init__.py` + `mindsos_capacity/builtins/text.py`.

**Source EDITED (4):** `mindsos_capacity/exceptions.py` (+ResidentError = 8 classes); `mindsos_capacity/runtime.py` (+ResidentSubscription dataclass + module docstring rewrite for Phase 31 section); `mindsos_capacity/capacity_layer.py` (+`_subscriptions` field init + 3 resident methods + docstring section); `mindsos_capacity/__init__.py` (+2 exports = 97 total + docstring rewrite + version bump).

**CLI EDITED (1):** `mindsos_cli/commands/capacity.py` (+invoke verb + helpers; mutex flags + hybrid exit codes).

**Tests NEW (25):** `tests/phase_31/{__init__.py,_fixtures.py}` + 23 test files / ~58 cases across resident lifecycle (8 files), text builtins (7 files), CLI invoke (7 files), and sentinels (3 files).

**ADR amendments (parent tree per Model C; no .git at parent root):** 4 touches across 3 ADRs.

**Test sentinel-flip pre-emptive (B-31-T0):** `tests/phase_30/test_phase_30_export_slate.py::test_version_bumped_to_phase_30` renamed in place to `test_version_bumped_to_phase_31`; literal bumped `0.0.0+phase30` → `0.0.0+phase31`. Same-file convention because the test asserts ongoing export-slate stability across phases.

### Test counts (estimates pending Linux verification at ship)

- **Docker (Linux, prod image):** Phase 30 baseline 3173 passed / 45 skipped. Phase 31 isolated estimate: ~58 passed + 4 ADR-amendment-sentinel skips. Cumulative target: **~3228 passed / 49 skipped** (±3 for hotfix elasticity).
- **Sandbox (Python 3.10):** sandbox tests will skip CLI tests if Typer not available + skip ADR-sentinels (parent ADR dir accessible on host sandbox; in-docker skip). Verify at ship.

### Carry-forwards to Phase 32+

Phase 30 carry-forwards #2 / #3 / #4 / #5 STILL OPEN (deferred per pre-R0 PB-α scope-narrow lock).

**Phase 31 new carry-forwards (4 items):**

1. **`--install-builtins=<family,...>` CLI flag** on `mindsos capacity invoke` — Phase 32+ when a second builtins family ships (R3 PB-29 lock).
2. **`text.lowercase` / `text.normalize_nfc` / other text-family additions** — Phase 32+ when a use case surfaces (R0 PB-4 naming convention is `text.X` precisely to scale here).
3. **Pathfinding registered-builtin form** — Phase 32+ if Integration B surfaces a real consumer; otherwise permanent (per ADR-0071 §Implementation Phase 31).
4. **L4 resident scheduler / state-snapshot lifecycle** per ADR-0099 — L4 ship; L3 holds the descriptive contract only.

### Observed quirks / process notes

- **Probe 4 surfaced a stale claim** in Phase 30 `__init__.py` "Excluded (defer)" inventory: "text builtins that auto-register on layer construction" — R0 PB-ε flipped to opt-in. The docstring rewrite at Step 3.6 self-resolves the claim (no separate fix).
- **Sandbox FS left `.bak` artifacts** from sed-based 12-site version bump (sandbox `rm` denied). `.gitignore` extended to cover `*.bak`; physical cleanup deferred to Mac shell at Ship Checklist Step 11.
- **`build_bfs_capacity_declaration` never lands at halvim** — parent's NotImplementedError stub stays unported. ADR-0071 §Implementation (Phase 31) records the retirement; future phases must not reintroduce without a concrete L4 consumer.
