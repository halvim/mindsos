# mindsos_arc — placement + Linux-gate runbook

Built in Cowork (sandbox, Python 3.10). Place on the **arc-solver** branch and run
the gate on the **Linux** host (Python 3.11+). Never gate on the Mac.

## 1. Placement (Mac; on the arc-solver worktree)
Copy this tree to the arc-solver repo root (top-level `mindsos_arc/` sibling to
`arc_solver/`; NOT added to core `pyproject` `packages.find`):

    mindsos_arc/{__init__,capacities,grids,solver}.py
    mindsos_arc/bundle/manifest.toml
    pyproject.toml          # the mindsos-arc distribution (install_requires = mindsos)
    gen_manifest.py         # regenerate the manifest roster from the live catalog
    tests/test_manifest_parity.py
    tests/test_install_path_e2e.py

Commit on arc-solver (do NOT touch main / core files). No core version bump.

## 2. Linux gate (3.11+)
From the arc-solver repo root, with the tree in place:

    # deps: mindsos importable (repo root on PYTHONPATH) + this package
    export PYTHONPATH="$PWD:$PWD/mindsos_arc_root"   # or `pip install -e .` in the pkg dir
    python -m pytest tests/test_manifest_parity.py tests/test_install_path_e2e.py -v

Expected: parity (3) + e2e (3) green. The e2e drives the real
`install_skill` → record → `apply_installed_skills` replay.

Optional CLI smoke (session-less admin path):
    mindsos skill install -m mindsos_arc/bundle/manifest.toml --json
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
