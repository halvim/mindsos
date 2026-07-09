# Resident-brain runtime v1 — CONFIRMED (2026-07-04)

Design: `RESIDENT_BRAIN_RUNTIME_DESIGN_NOTE.md`. Direction:
`RESIDENT_BRAIN_DIRECTION_2026-07-04.md`. Branch: `feat/resident-brain-runtime`.
Not a numbered phase; no version bump (no versioned domain surface changed).

## What shipped

- `mindsos_server/boot.py` — `boot_brain(client=None, *, user, install_builtins=True,
  session=None) -> Stack`. Durable path: `bootstrap_kl_from_falkordb` → install v0
  builtins → `apply_installed_skills` → `boot_local`. Ephemeral path (`client=None`):
  in-memory KL + `InMemoryLocalPersister`, builtins only. `Stack.save()` /
  `Stack.global_view()`.
- `mindsos_capacity/catalog_check.py` — `catalog_check(view) -> CatalogReport`
  (sources / sinks / orphans; `ok = no orphans`). Record-less structural x-ray from
  the bipartite view; the skill-verify engine adds manifest-aware defect detection later.
- `mindsos_cli/commands/brain.py` — `mindsos brain [--user U] [--ephemeral]`. One held
  `Stack`, pure `BrainREPL.dispatch(line)->str` + `loop`. Verbs: `ls` / `datastate` /
  `caps` / `verify` / `task` / `save` / `reset` / `help` / `quit`.
- `mindsos_cli/app.py` — registered the `brain` subapp.
- `tests/resident_brain/` — 19 tests: catalog_check (5), boot_brain ephemeral (4),
  REPL (9), durable Falkor round-trip (1, `@pytest.mark.integration`).

## Decisions (converged)

PB-1 synchronous Stack, no started IntelligenceLayer · PB-2 `boot_brain` promoted from
the test-only `build_stack` · PB-3=B Falkor-durable from v1 · PB-4 lightweight
`catalog_check` in `mindsos_capacity` · PB-5 Server/Capacity/CLI homes, no phase ·
PB-6=A episodes are durable memory (`reset` explicit-only).

Build-time correction: `catalog_check` v0 flagged consumed-but-unproduced DataStates as
defects; those are legitimate entry points (raw text) and false-positive the real
builtins catalog. Reworked to sources/sinks/orphans. Caught by the ephemeral
orphan-free test.

## Gate

Canonical containerized gate (`docker compose run --rm mindsos-test pytest tests/ -v`):
**4133 passed / 11 skipped / 1 xpassed / 0 failed** (2026-07-04). Durable round-trip
passed live — the FIRST end-to-end consumer of Episode save→load, exercising (and
de-risking) carry-forwards L0-25 / L0-26; the ADR-0182 dict-value codec round-trips a
full Local-with-episodes.

A raw host `pytest -q` shows 11 env-only failures (`phase_00` needs the `falkordb`
hostname; 10 `phase_13` check the `/app` image) — container-context tests, green in the
canonical gate.

## Deferred

Daemon + socket client (IntelligenceLayer re-enters here for background dream/submind) ·
retention policy for unbounded Local growth · crash-autosave · full engine-backed
`verify`. Next consumer chat: package ARC as an installable intelligence
(`ARC_PACKAGING_RUNTIME_COORDINATION.md` answered — Global caps, full v0 stack, install
via CLI + ledger reactivation).
