# MindsOS — Working Rules (point every chat/project here)

Read this + `STATE.json` before doing anything. They are the source of truth.

## 1. Where you work
- One chat = one worktree = one branch. Never check out another chat's branch in
  your folder. Need their work? `git merge` it.
- Every project lives under `projects/<name>/` with its own docs.
- **Core** → `MindsOS/` on `main` (or a short branch off it): the 8 `mindsos_*`
  packages + tests + docs.
- **Core-contributor projects** (edit core, merge phases to `main`) →
  `projects/{wsd,fol,dwf_mapping,skill_acquisition,maintenance}/`, own worktree
  + own test instance, branches `wsd-NN`/`fol-NN`/`dwf-NN`/`feat/*`.
- **Demo projects** (built on top, never edit core) →
  `projects/{robot_demo,arc_demo,bongard_demo}/` on `demo/*` branches, own
  worktree (`MindsOS-robot`, `MindsOS-arc`, `MindsOS-bongard`) + own instance.

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
  `docker compose -p mindsos-<project> --profile test run --rm --build mindsos-test pytest <paths>`
- **Always pass `--build`.** The test image bakes the source via `COPY`
  at build time (no volume mount), so without `--build` the gate silently
  reuses a stale image and tests OLD code. (This masked the
  `mindsos_cli` breakage on the Slice-1 gate — a no-`--build` run reported
  3991 green while the real branch was 4019; see STATE.recent
  `pipeline rename` 2026-06-22.)
- core-dev (main/phase/wsd) tests the modified core in place.
- consumer (demo/*) tests demo code on top of the pinned, unmodified core.

## 5. Execution discipline
- Cowork builds; Mac commits + pushes; Linux runs/gates. Never run tests on the Mac.
- Never mutate git from the Cowork sandbox (stale `index.lock` blocks the Mac).
- Update `STATE.json` on every ship. Keep `HANDOFF.md` for narrative only.
- **Never commit chat/next-chat prompts.** `*NEXT_CHAT_PROMPT*.md` and any
  copy-paste handoff prompt are transient and local-only — they are gitignored
  and must stay out of git. Hand them off by pasting into the next chat, not by
  pushing. Same for scratch/planning dirs (`_reorg/`).
- **Never `git add -A`/`git add .`.** Stage explicit paths only — the shared
  tree accumulates untracked floaters that a blanket add will sweep onto the
  wrong branch. Verify with `git diff --cached --name-only` before committing.

## 6. State lookup
- Current version, last shipped phase, what each demo pins → `STATE.json`.
- Your lane + who owns what → `BRANCHES.md`.
