# Direction: main/projects CLI redundancy fix

**Status:** DIRECTION recorded 2026-07-05. **Base half IMPLEMENTED 2026-07-06**
(this chat) — see `SKILL_REPO_CONTRACT.md`. Open questions resolved: multi-repo
+ skill-only repos (not monorepo); git-dependency only (no private index);
`doctor` detector built; pin = git tag + `requires_mindsos_phase`; base dist
renamed `mindsos-cli`→`mindsos-runtime`; install stays two-step `--no-deps`
(PB4). **Arc half OWED:** purge the arc repo's vendored `mindsos_*` tree + set
its dep to `mindsos-runtime`, folded with landing `mindsos_arc`.

## Problem
Multiple full `mindsos_*` checkouts editable-installed into one interpreter
collide on the `mindsos_cli` (and other `mindsos_*`) top-level package names.
pip has **no** guard for editable module-name collisions — the last install
wins silently. Symptom that surfaced this: `mindsos brain` →
`No such command 'brain'`, because the `mindsos-arc` repo (which vendors a full,
brain-less `mindsos_cli`) was installed and shadowed base mindsos.

`arc_dist/` itself is clean (arc-only: `name="mindsos-arc"`,
`include=["mindsos_arc*"]`, `dependencies=["mindsos"]`). The collision is the
arc **repo's** vendored `mindsos_*` copy, not `arc_dist`.

## Decision (settled)
Exactly **one** `mindsos_cli` — the base mindsos. Projects (ARC, Bongard, …)
are on-top **skill bundles** that consume base mindsos and ship only their own
`mindsos_<skill>` package. No project vendors a second `mindsos_*` tree.
Rationale is the generic-runtime / skills-are-consumers principle already in
the codebase — do NOT restate it here; see RULES §8 and memory
[[wsd-subsystem-not-core]] / [[cli-redundancy-one-shared-cli]].

## Interim discipline (works today — the venv fix)
One venv → install base mindsos first → then only `arc_dist --no-deps` → always
run from that venv. Never `pip install` anything carrying a rival `mindsos_cli`.
(A venv is necessary but not sufficient: two full trees in one venv still
collide.)

## Options for the structural fix (the next chat decides + builds)
1. **Depend, don't copy.** Distribute base mindsos as a pin-able dependency —
   git+URL (`mindsos @ git+ssh://…/mindsos.git@<sha|tag>`) or a wheel on a
   private index — so a project's install pulls the ONE canonical mindsos and
   there is no second `mindsos_cli` to install. Pair with a version/phase pin
   and the existing manifest `requires_mindsos_phase` preflight
   (`mindsos_server/skills/preflight.py::current_mindsos_phase`).
2. **Repo shape.** Make project repos skill-only (`arc_dist`-style, consuming
   mindsos), OR adopt a monorepo: one mindsos tree + `mindsos_arc` /
   `mindsos_bongard` as sibling installable packages, so exactly one
   `mindsos_cli` exists in source.
3. **Detector (defense-in-depth).** A `doctor` check that fails loudly when >1
   installed distribution provides `mindsos_cli`, or when the active
   `mindsos_cli.__file__` is not the expected base path. Detect, do not auto-fix.

## Open questions for the next chat
- Monorepo vs multi-repo + git-pinned dependency? (affects every future skill)
- Publish mindsos to a private index, or git-dependency only?
- Add the `doctor` collision detector to base mindsos now, or defer?
- Version-pin policy for skills (exact sha, tag, or `requires_mindsos_phase`
  only?).

## Do NOT re-derive
The what-shipped + env lessons are already in files — reference, don't repeat:
resident-brain slices ([[resident-brain-repl-slices-shipped]]), the venv /
reinstall / falkordb-collision setup lessons in the usage guide
(`docs/usage/runtime/resident-brain.md` "Set up and run" + "Updating the code")
and [[ship-env-invariants]], and the version-lock in
[[mindsos-version-scheme-phase-locked]].
