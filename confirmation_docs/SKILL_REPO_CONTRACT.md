# Skill-repo contract — one shared `mindsos_cli`

**Status:** IMPLEMENTED 2026-07-06 (base half). Companion to
`CLI_REDUNDANCY_FIX_DIRECTION.md` (the problem + settled decision).

The rule that makes "exactly one `mindsos_cli`" structural, not a convention a
project can forget. Applies to ARC, Bongard, and every future skill repo.

## The contract

1. **Ship only `mindsos_<skill>`.** A project repo contains its own
   `mindsos_arc` / `mindsos_bongard` package and nothing named `mindsos_cli`,
   `mindsos_core`, or any other base `mindsos_*` import package. Never vendor a
   second base tree — pip has no guard for editable module-name collisions, so a
   vendored `mindsos_cli` silently shadows base (the Phase-50
   `No such command 'brain'` bug).

2. **Depend on base, don't copy it.** Declare the base dependency as
   `mindsos-runtime` (the base distribution — renamed from `mindsos-cli`
   2026-07-06; it ships all 8 `mindsos_*` packages, the CLI is 1 of 8). Git-URL
   form: `mindsos-runtime @ git+ssh://…/mindsos.git@<tag>` — the name before `@`
   must equal the dist name even though the repo is `mindsos`.

3. **Install flow = two-step (decided PB4, 2026-07-06).** Base editable first,
   then the skill `--no-deps`:
   ```
   pip install -e <base-mindsos>
   pip install -e <skill> --no-deps
   ```
   pip-git resolution is NOT wired (would need a deploy key in the gate/CI image;
   the gate pins base by worktree, not pip). The dep line is a correctness
   declaration; installs run `--no-deps`. Revisit only if base is published.

## Pin policy

- **Source pin:** a git tag (reuse the `pinned_core` convention, e.g.
  `phase-50-confirmed`); sha only when no tag exists.
- **Compat floor:** the skill manifest's `requires_mindsos_phase`
  (`mindsos_server/skills/preflight.py::current_mindsos_phase`).
- **Do NOT** pin via pip version — the `+phaseN` local-version scheme is
  second-class in pip resolution.

## Enforcement (defense-in-depth)

`mindsos doctor` reports `mindsos_cli` providers; `mindsos doctor --self-test`
FAILS when >1 installed distribution provides the `mindsos_cli` import package
(name-agnostic; catches the class, not just the known instance).

**Honest scope — the detector is a CLEAN-ENV / CI regression guard, not a
live-broken-env autocatch.** In the *already-collided* state the rival
(brain-less) cli can win, so `mindsos doctor` runs *its* copy, which lacks the
check — chicken-and-egg. The gate installs base only, so `--self-test` there is
a true regression guard (fails if CI ever double-installs). For a suspected-bad
local env, run this resolution-independent snippet (plain Python, doesn't go
through the shadowed `mindsos` command):

    python -c "import importlib.metadata as m; \
    p=sorted(set(m.packages_distributions().get('mindsos_cli',[]))); \
    print('COLLISION' if len(p)>1 else 'ok', p)"

**Rename cleanup gotcha.** After `mindsos-cli`→`mindsos-runtime`, any venv that
previously did an editable install under the old name still carries a stale
`mindsos-cli` dist-info in site-packages (pip does not remove it on a rename) —
and the in-tree `mindsos_cli.egg-info/` regenerates under the old name too. Both
make `packages_distributions()` report two providers of `mindsos_cli` and the
detector false-positives. Cleanup in each such venv:

    pip uninstall -y mindsos-cli        # drop the old-named dist-info
    rm -rf mindsos_cli.egg-info         # drop the in-tree stale metadata
    pip install -e . --no-deps          # reinstall base as mindsos-runtime
