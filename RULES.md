# MindsOS — Working Rules (point every chat/project here)

Read this + `STATE.json` before doing anything. They are the source of truth.

## 1. Where you work
- One chat = one worktree = one branch. Never check out another chat's branch in
  your folder. Need their work? `git merge` it.
- Core work → `MindsOS/` on `main` (or a short branch off it).
- Demos → their own worktree: `MindsOS-robot` (`demo/robot`), `MindsOS-arc` (`demo/arc`).

## 2. Branches
- Off `main`, squash-merge back, then delete: `phase-NN`, `wsd-NN`, `dwf-NN`,
  `fol-NN`, `feat/*`, `fix/*`, `chore/*`.
- Long-lived: `main` (the product), `demo/*` (installs on top of main).
- Shipped phases are `phase-NN-confirmed` **tags**, not branches.

## 3. The two hard rules
- **Demos never edit `mindsos_*`.** Need a core change? Land it on `main` first,
  then `git merge <core-tag>` into the demo. CI enforces this.
- **Demos pin a core version.** Bump deliberately: merge a core tag → re-test →
  update `pinned_core` in `STATE.json`. No auto-following `main`.

## 4. Testing (Linux, parallel)
- Each project runs its own isolated stack, in its own terminal, concurrently:
  `docker compose -p mindsos-<project> --profile test run --rm mindsos-test pytest <paths>`
- core-dev (main/phase/wsd) tests the modified core in place.
- consumer (demo/*) tests demo code on top of the pinned, unmodified core.

## 5. Execution discipline
- Cowork builds; Mac commits + pushes; Linux runs/gates. Never run tests on the Mac.
- Never mutate git from the Cowork sandbox (stale `index.lock` blocks the Mac).
- Update `STATE.json` on every ship. Keep `HANDOFF.md` for narrative only.

## 6. State lookup
- Current version, last shipped phase, what each demo pins → `STATE.json`.
- Your lane + who owns what → `BRANCHES.md`.
