# MindsOS — Working Rules (point every chat/project here)

Read this + `STATE.json` before doing anything. They are the source of truth.

## 0. How to talk to me
- Say what is needed concisely, in a way I have enough context to
  understand and make decisions — but not so long it's a chore to read.
  If I need more, I'll ask.

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
- Shipped core changes are **tags**, not branches: phases → `phase-NN-confirmed`;
  non-phase feats/fixes → `<name>-confirmed`. **Every** core ship is tagged (§7).

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

## 7. Grounding discipline — only the solver's knowledge
- **Never assume a fact the solver cannot itself derive.** Capacities and
  profiling may use ONLY knowledge the system actually has at that point — not
  the author's outside understanding of the task or domain.
- Concretely: do **not** hardcode or infer the background colour, object roles,
  task intent, palette meaning, or any "obvious to a human" fact. If a step
  needs such a fact, it must come from an explicit capability that *derives or
  verifies* it from the grids (e.g. `verify_background`), with its assumptions
  visible and challengeable — never a buried default (most-frequent ≠ background).
- When a needed fact cannot yet be derived, the honest output is "don't know"
  (abstain / flag), not a guess. Smuggling author-knowledge in as if the solver
  produced it makes the demo lie about what the architecture can do.

## 8. Subsystems vs core (architectural ownership)
- **Subsystems own nothing architectural.** WSD is a MindsOS *subsystem* (a Skill)
  for text — one piece of the larger **NLU** system. It is *installed on top of*
  the MindsOS platform and *uses* core components; it does **not** own any L0–L5
  architectural component. Same for FOL and any future skill. (Stop deferring core
  mechanics "to WSD" — that framing is wrong and has misled multiple chats.)
- **Any component that belongs to MindsOS is core, even if a subsystem needs it
  first.** If core mechanics are currently sketched inside a subsystem
  (`projects/wsd/source/`, etc.), they are to be **extracted, individualized, and
  implemented at the core layer** whenever any MindsOS component needs them — not
  left as subsystem-private code. Example: real **pipeline execution** (run a
  `Pipeline`'s capacity steps for real; the Phase-47 `execution.run` notional-step
  stub) is a **core** component, not WSD's; build it at core when first needed.

## 9. Core-ship checklist (MANDATORY for every change to `mindsos_*`)
- **Tag the ship.** After the change merges to `main` and the Linux gate is green,
  cut an annotated `<name>-confirmed` tag at the squash commit and push it
  (`git tag -a <name>-confirmed <sha> -m "..."` → `git push origin <name>-confirmed`).
  Demos pin tags, never bare shas (§3). Applies to non-phase feats/fixes too — not
  only numbered phases. (Slice 1, F9, the rename, Part 6 all landed untagged — the gap
  this rule closes.)
- **Gate must exercise the CLI.** A ship is not "green" unless the cumulative gate
  collected the `mindsos_cli.app`-importing suites (with `--build`, §4). Verify before
  declaring green:
  `docker compose -p mindsos-core --profile test run --rm --build mindsos-test pytest --collect-only -q | grep -c test_cli`
  must be `> 0`. A broken CLI import must surface as gate errors, never hide silently
  (it did on Slice 1 — see §4 + `STATE.recent`).
