# mindsos_arc — placement + Linux-gate runbook

Built in Cowork (sandbox, Python 3.10). Place on the **arc-solver** branch and run
the gate on the **Linux** host (Python 3.11+). Never gate on the Mac.

## 1. Placement (Mac; on the arc-solver worktree)
The bundle is a self-contained distribution directory `arc_dist/` at the
arc-solver repo root (sibling to `arc_solver/`). It has its OWN `pyproject`
(`packages.find = mindsos_arc*`) and is NEVER added to the core root `pyproject`
`packages.find`. Do not flatten it into the repo root — that collides with the
root `pyproject`. Layout (already in place, untracked):

    arc_dist/mindsos_arc/{__init__,capacities,grids,solver}.py
    arc_dist/mindsos_arc/bundle/manifest.toml
    arc_dist/pyproject.toml     # the mindsos-arc distribution (depends on mindsos-runtime)
    arc_dist/gen_manifest.py    # regenerate the manifest roster from the live catalog
    arc_dist/tests/test_manifest_parity.py
    arc_dist/tests/test_install_path_e2e.py

Track it explicitly (`git add arc_dist/` — never `git add -A`) and commit on
arc-solver (do NOT touch main / core files). No core version bump.

PREREQ: arc-solver must first carry the base rename (merge main >=
`cli-redundancy-base-confirmed`) so `mindsos-runtime` is the real dist name and
the doctor `>1 provider` detector + `SKILL_REPO_CONTRACT.md` are present. Watch
the root `pyproject.toml` merge (name flips mindsos-cli -> mindsos-runtime).

### Install discipline (the CLI-redundancy rule)
Install ONLY the `mindsos_arc` distribution on top of base — never
`pip install -e .` at the arc-solver root. arc-solver is main+ARC, so its root
tree is a full (brain-less) `mindsos_*` copy; editable-installing it shadows
base and causes the `No such command 'brain'` collision. Correct flow:

    pip install -e <base-mindsos>              # base first
    pip install -e <arc-solver>/arc_dist --no-deps   # skill only

`mindsos doctor --self-test` fails if >1 dist provides `mindsos_cli` (catches a
slip). See `confirmation_docs/SKILL_REPO_CONTRACT.md` in base.

## 2. Linux gate (3.11+)
From the arc-solver repo root, with `arc_dist/` in place. The e2e imports both
the in-tree base packages (`mindsos_capacity`/`mindsos_server`/`mindsos_knowledge`,
from repo root) and `mindsos_arc` (from `arc_dist/`), so both must be on the path:

    # repo root on PYTHONPATH for base; arc_dist for the mindsos_arc package
    export PYTHONPATH="$PWD:$PWD/arc_dist"   # or: pip install -e arc_dist --no-deps
    python -m pytest arc_dist/tests/test_manifest_parity.py \
                     arc_dist/tests/test_install_path_e2e.py -v

Expected: parity (3) + e2e (3) green. The e2e drives the real
`install_skill` → record → `apply_installed_skills` replay. Needs 3.11+
(`mindsos_server` uses `datetime.UTC`); the dist's own `requires-python>=3.10`
is looser than the e2e — harmless (e2e is test-only, not shipped).

Optional CLI smoke (session-less admin path):
    mindsos skill install -m arc_dist/mindsos_arc/bundle/manifest.toml --json
    mindsos skill list --json
    mindsos skill activate --json

## 3. Confirmation
Tag `arc-packaging-confirmed`; write the confirm doc. Pair-execution: Cowork built,
Mac commits+pushes, Linux gated.

## Sandbox pre-checks already green (Python 3.10, against main's mindsos)
- module imports (capacities/grids/solver)
- manifest parity (roster == live catalog: 32 caps / 39 datastates)
- warm-layer idempotency (install_arc twice = no-op)
- real `parse_manifest` accepts the manifest (schema-valid; all datastates realm `arc`)
Not runnable in-sandbox (needs 3.11): the `mindsos_server` install driver → gate step 2.
