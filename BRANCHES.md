# BRANCHES.md — branch & worktree registry (anti-collision contract)

> This is the going-forward source of truth for "who works where." Once the
> reorg lands, move this file to the repo root on `main` and keep it current.
> A chat must claim its lane here before pushing.

Every project lives under `projects/<name>/`. Core-contributors merge to `main`;
demos live on `demo/*` branches and never edit `mindsos_*`.

## Worktrees

⚠ **Rebuilt 2026-08-13 from `git worktree list`, because it had drifted.** It listed
`MindsOS-arc` on `demo/arc` when git says `arc-solver`, and omitted four live worktrees
entirely. Homes are marked **unverified** where no such directory exists on `main` —
`projects/{robot_demo,arc_demo,bongard_demo}/` are all in that category, which is the same
drift RULES §1 was corrected for. Do not restore a home column entry without `ls`-ing it.

| Directory                 | Branch             | Kind             | Project home                     |
|---------------------------|--------------------|------------------|----------------------------------|
| `MindsOS/`                | `main`             | core             | `mindsos_*` + `tests/` + `docs/` |
| `MindsOS-wsd/`            | `wsd-51`           | core-contributor | `projects/wsd/` ✅               |
| `mindsos-amii-study/`     | `chore/amii-study` | study            | `projects/amii_study/` ✅        |
| `MindsOS-robot/`          | `demo/robot`       | demo             | `robot_demo/` at root ✅ (NOT `projects/robot_demo/`) |
| `MindsOS-arc/`            | `arc-solver`       | demo             | unverified                       |
| `MindsOS-arc-viz/`        | `arc-solver-viz`   | demo             | unverified                       |
| `MindsOS-bongard/`        | `demo/bongard`     | demo             | unverified                       |
| `nilm_brain/`             | `nilm_brain`       | long-lived       | unverified                       |
| `_MindsOS-dr-critic/`     | `feat/dr-critic`   | critic lane      | `scripts/critic/` — **transient; owes §10.1**, its probe scripts exist nowhere else |
| `MindsOS-dr/`             | `demo/decision-records` | demo        | `decision_records_demo/` at root ✅ (demo branch only, created 2026-08-13 @ `d94ca4f`) |

**Decision Records** code home is `decision_records_demo/` at the repo root, **only on
`demo/decision-records`** (worktree `MindsOS-dr`, pins `dr-fold-grounding-confirmed`). Its
research + docs home stays `projects/decision_records_demo/` on `main`. Build order:
`confirmation_docs/DECISION_RECORDS_V0_PLAN.md`.

On demand (create when the work starts):
`git worktree add ../MindsOS-fol -b fol-1 main` (also dwf, skill_acquisition, maintenance).
Then point that Cowork chat's project at the new folder.

## Long-lived branches

| Branch        | Purpose                                  | May modify                                                        | Rule                                  |
|---------------|------------------------------------------|------------------------------------------------------------------|---------------------------------------|
| `main`        | Operational system (the product)         | `mindsos_*`, `docs/`, `confirmation_docs/`, `projects/`, `tests/` | Always green on the Linux gate        |
| `demo/robot`  | Robot demo, installed on top of main     | `robot_demo/ demo_ui/ sim/ web/ metagraph_visualizer/` + robot docs | NEVER edits `mindsos_*`; merges main in |
| `demo/arc`    | ARC demo, installed on top of main       | `intelligence_demo/ run_spike`                                    | NEVER edits `mindsos_*`; merges main in |
| `demo/decision-records` | Decision Records demo, installed on top of main | `decision_records_demo/`                          | NEVER edits `mindsos_*`; merges main in |

## Short-lived branches (off `main`, squash-merge back, then delete)

| Prefix       | For                                   | On ship                          |
|--------------|---------------------------------------|----------------------------------|
| `phase-NN`   | numbered core phase                   | tag `phase-NN-confirmed`, delete branch |
| `wsd-NN`     | WSD install phase                     | merge to main, delete            |
| `dwf-NN`     | DWF install phase                     | merge to main, delete            |
| `fol-NN`     | FOL install phase                     | merge to main, delete            |
| `feat/<slug>`| feature / spike                       | merge to main, delete            |
| `fix/<slug>` | bug fix                               | merge to main, delete            |
| `chore/<slug>`| docs / housekeeping                  | merge to main, delete            |

## Testing & version pinning per lane

| Lane          | Test mode | How to run on Linux (own terminal, parallel)                          | Core version |
|---------------|-----------|----------------------------------------------------------------------|--------------|
| `main`/core   | core-dev  | `docker compose -p mindsos-core --profile test run --rm mindsos-test pytest tests/` | self (latest) |
| `demo/robot`  | consumer  | `docker compose -p mindsos-robot --profile test run --rm mindsos-test pytest ...`   | `pinned_core` in `STATE.json` |
| `demo/arc`    | consumer  | `docker compose -p mindsos-arc --profile test run --rm mindsos-test pytest ...`     | `pinned_core` in `STATE.json` |

Each `-p` namespace is an independent FalkorDB → runs concurrently, no waiting.
Demos upgrade core deliberately: `git merge <core-tag>` → re-test → bump
`pinned_core`. See `TESTING_AND_VERSIONING.md`. Current state of everything is in
root `STATE.json`, not `HANDOFF.md`.

## The two rules that prevent the mess from returning

1. **One chat = one worktree = one branch lane.** Do not check out another
   chat's branch in your directory. If you need their work, `git merge` it.
2. **Demos are installs, not forks.** A demo never edits `mindsos_*`. If a demo
   needs a core change, it lands on `main` first via `feat/*` or `phase-NN`,
   then the demo merges `main` to receive it.

## Current ownership snapshot (fill in / keep current)

| Branch        | Active chat / handoff doc                          | Last touched |
|---------------|----------------------------------------------------|--------------|
| `main`        | core phase chats                                   | —            |
| `wsd-51`      | WSD Phase 51 chat — see `WSD_PHASE_51_NEXT_CHAT_PROMPT.md` | —     |
| `demo/robot`  | robot demo chat                                    | —            |
| `demo/arc`    | ARC demo chat — `arc1/SOLVER_NEXT_CHAT_PROMPT.md`  | —            |
