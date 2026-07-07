# ARC packaging — CONFIRMED 2026-07-06

ARC packaged as an on-top installable intelligence **skill bundle**. NOT part of
core: no `mindsos` wheel change, no phase number, no core version bump. Ships on
the **arc-solver** branch only. Completes the CLI-redundancy arc half.

## Prereq landed
arc-solver merged `main` >= `cli-redundancy-base-confirmed`: base distribution
renamed `mindsos-cli` -> `mindsos-runtime`; `mindsos doctor --self-test` now
fails on >1 provider of the `mindsos_cli` import package; the rule lives in
`confirmation_docs/SKILL_REPO_CONTRACT.md` + `docs/usage/runtime/resident-brain.md`.
The merge flipped the root `pyproject` name to `mindsos-runtime`; no `mindsos_arc`
packages are in the core root `packages.find` (arc_dist is a separate dist).

## Shipped (arc-solver, `arc_dist/`)
Self-contained distribution `mindsos-arc` (own `pyproject`; dependency
`mindsos-runtime`, a correctness declaration — installs are two-step `--no-deps`,
not pip-resolved):

- `mindsos_arc/{__init__,capacities,grids,solver}.py`
- `mindsos_arc/bundle/manifest.toml` — **L3-only**: 32 capacities / 39 datastates,
  realm `arc`, entry point `mindsos_arc.capacities:install_arc`; `[l2]`/`[l4]`
  empty; `requires_mindsos_phase = 50`.
- `gen_manifest.py` (regenerates the roster from the live catalog) + a parity test
  that guards manifest<->installer drift.

Installs through the Phase-50 skill path unchanged.

## Install discipline (the CLI-redundancy rule)
Install ONLY the `mindsos_arc` distribution on top of base — never
`pip install -e .` at the arc-solver root (its root tree is a full brain-less
`mindsos_*` copy and would shadow base -> `No such command 'brain'`). Two-step:

    pip install -e <base-mindsos>
    pip install -e <arc-solver>/arc_dist --no-deps

`mindsos doctor --self-test` catches a slip (>1 provider of `mindsos_cli`).

## Gate (Linux, py3.11+) — 6 passed
`arc_dist/tests` — parity (3) + e2e (3). Parity + warm-layer idempotency
re-verified in-sandbox (py3.10, 3/3, 2026-07-06); the e2e requires 3.11
(`mindsos_server` uses `datetime.UTC`) and ran on the Linux host. The e2e drives
the real `install_skill` -> record -> `apply_installed_skills` replay.

## Key
`install_arc` is warm-layer idempotent (builtins-triple); the manifest roster is
generated from the live catalog + a parity test guards drift; self-contained in
realm `arc` (no core datastate dependency).

## Deferred (not done; core-requests)
- Local-scope caps (driver is session-less -> Global-only).
- In-place upgrade (v2).
- Root non-installable hard guard (PB-5) — relying on the doctor detector +
  RUNBOOK install-discipline note for now.
- Live start -> install -> probe loop (resident-runtime REPL chat).

Pair-execution: Cowork built + docs; Mac merged/committed/tagged; Linux gated.
Tag: `arc-packaging-confirmed`.
