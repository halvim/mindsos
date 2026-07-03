# BRANCHES.md — branch & worktree registry (anti-collision contract)

> This is the going-forward source of truth for "who works where." Once the
> reorg lands, move this file to the repo root on `main` and keep it current.
> A chat must claim its lane here before pushing.

Every project lives under `projects/<name>/`. Core-contributors merge to `main`;
demos live on `demo/*` branches and never edit `mindsos_*`.

## Worktrees

| Directory            | Branch        | Kind             | Project home             |
|----------------------|---------------|------------------|--------------------------|
| `MindsOS/`           | `main`        | core             | `mindsos_*` + `tests/` + `docs/` |
| `MindsOS-wsd/`       | `wsd-51`      | core-contributor | `projects/wsd/`          |
| `MindsOS-robot/`     | `demo/robot`  | demo             | `projects/robot_demo/`   |
| `MindsOS-arc/`       | `arc-solver`     | independent (consumer)  | `projects/arc_solver/` †  |
| `MindsOS-arc-viz/`   | `arc-solver-viz` | independent (consumer, parallel lane) | `projects/arc_solver/viz/` † |
| `MindsOS-bongard/`   | `demo/bongard`| demo (new)       | `projects/bongard_demo/` |

† arc-solver is an **independent project** (a MindsOS instance solving the ARC dataset), off the `demo/` prefix but still a **consumer**: it pins a core version and **never edits `mindsos_*`** (same rule as demos). Folder flatten `projects/arc_demo/intelligence_demo/arc1/ → projects/arc_solver/` is pending (Phase 2); `arc-solver-viz` is its parallel human-communication sub-project, code home `projects/arc_solver/viz/`.

On demand (create when the work starts):
`git worktree add ../MindsOS-fol -b fol-1 main` (also dwf, skill_acquisition, maintenance).
Then point that Cowork chat's project at the new folder.

## Long-lived branches

| Branch        | Purpose                                  | May modify                                                        | Rule                                  |
|---------------|------------------------------------------|------------------------------------------------------------------|---------------------------------------|
| `main`        | Operational system (the product)         | `mindsos_*`, `docs/`, `confirmation_docs/`, `projects/`, `tests/` | Always green on the Linux gate        |
| `demo/robot`  | Robot demo, installed on top of main     | `robot_demo/ demo_ui/ sim/ web/ metagraph_visualizer/` + robot docs | NEVER edits `mindsos_*`; merges main in |
| `arc-solver`  | ARC-solver (independent MindsOS instance), on top of main | `projects/arc_solver/` (currently `projects/arc_demo/…`) | NEVER edits `mindsos_*`; merges main in; pins core |
| `arc-solver-viz` | arc-solver's parallel human-communication sub-project | `projects/arc_solver/viz/`                                  | NEVER edits `mindsos_*`; merges `arc-solver` in |

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
| `arc-solver`  | consumer  | arc gate: `cd projects/arc_demo && ./run_spike` (→ 14 `[ok]`); docker `-p mindsos-arc-solver` | `pinned_core` in `STATE.json` |

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
| `arc-solver`  | ARC-solver chat — `projects/arc_demo/intelligence_demo/arc1/PIPELINE_DECISIONS.md` | 2026-07-03 (consolidated) |
| `arc-solver-viz` | arc-viz parallel lane — `projects/arc_solver/viz/ARC_VIZ_CONTRACT_SPEC.md` | 2026-07-03 (created) |
