# MindsOS — Working Rules (point every chat/project here)

Read this + `STATE.json` before doing anything. They are the source of truth.

## 0. How to talk to me
- Say what is needed concisely, in a way I have enough context to
  understand and make decisions — but not so long it's a chore to read.
  If I need more, I'll ask.
- **Never put comments in a command block.** Any block I am meant to run
  (`bash`, `git`, `docker`, SQL, a REPL) contains commands only — no `#`
  comments, no inline annotations, no explanatory trailing text. I copy
  those blocks straight into a terminal; comments are noise there and are
  a paste hazard. If a command needs explaining, explain it in prose
  outside the block.

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
  `fol-NN`, `feat/*`, `fix/*`, `chore/*`. **Deleting is §10, and it is not optional** —
  this line has existed since the beginning and the sweep of 2026-08-10 still had to
  remove 31 branches and 6 orphaned worktrees.
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

## 7. Core-ship checklist (MANDATORY for every change to `mindsos_*`)
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
- **Close the lane.** A ship is not done when the PR merges. It is done when the branch
  and the worktree are gone — **§10**. A chat that ends without doing this has left work
  for someone else.

---

## 9. ADRs and their guards

- **Adding an ADR file REQUIRES adding its row to `docs/decisions/adr/README.md`.** The gate
  fails otherwise (`tests/test_adr_status_consistency.py`). The README is the full index and is
  held to that; the per-layer `docs/decisions/summary/*.md` pages are deliberately partial and
  are checked for agreement, not coverage.
- **An ADR-level status change is FOUR edits** — front-matter `status:`, the prose
  `**Status:**` line, the README row, and any summary-table cell.
- **An in-file amendment needs no README row**, but must label its status
  `**Amendment status:**` — never `**Status:**`. The checker reads the *first* `**Status:**`
  line as the ADR's own, so an amendment using that label shadows it.
- **A contradicted ADR flips to `Proposed`** (new form decided, not built) **or `Superseded`**
  (decision wholly replaced). There is no other status word. Where an ADR is shipped and only
  partly wrong, leave it `Accepted` and let the amendment carry `Proposed`, naming the CR that
  flips it.
- **Never name a subsystem as the owner of core work in a `mindsos_*` docstring** (§8). Gate
  -enforced by `tests/architecture/test_no_subsystem_ownership.py`, which also refuses an
  ALLOWLIST entry that exempts nothing.

**Why this section exists.** Both guards were written in the 2026-07 doc-vs-code audit to stop
exactly the drift they were then unable to see: the ADR guard silently checked zero rows for
~69 ADRs, and the ownership guard could not match the phrasings RULES §8 itself uses. Repaired
2026-08-01 (PRs #106, #108).

> **A green guard that cannot fail is worse than no guard.** When you add or change one, write
> a test that makes it go RED — assert the failure behaviour, not only the passing state.
---

## 10. Closing a lane (MANDATORY — run it before the chat ends)

**Order matters.** `gh pr merge --delete-branch` refuses while a worktree holds the branch,
and a `git worktree remove` after the branch is gone leaves a registered stale worktree. So:
**merge → remove the worktree → delete the branch, local and remote → prune.**

```
cd ~/Documents/Claude/Projects/MindsOS && gh pr merge <N> --squash --delete-branch && git worktree remove ../_MindsOS-<slice> && git branch -D <branch> && git pull --ff-only && git worktree prune && git worktree list && git branch --list
```

`git worktree list` and `git branch --list` at the end are the point: **look at them.** If your
lane is still there, you are not done.

### 10.1 Work that will never merge — `archive/<name>`, never an orphan branch

A branch whose code exists nowhere else must not be left behind "in case". **Tag it, then
delete it:**

```
git tag -a archive/<name> <branch> -m "Archived <date>. <what it holds>. <why it died>." && git push origin archive/<name> && git branch -D <branch> && git push origin --delete <branch>
```

The commits survive and are fully recoverable; the branch list stays readable. **Plain deletion
is only for work provably already on `main`.**

**How to prove that**, because `git branch --merged` is useless here — everything is
squash-merged, so no branch is ever an ancestor of `main`:

```
mb=$(git merge-base main "$b"); for f in $(git diff-tree -r --name-only "$mb" "$b"); do git cat-file -e main:"$f" 2>/dev/null || echo "MISSING $f"; done
```

Nothing missing, plus a known ship record ⟹ delete. Anything missing ⟹ `archive/` tag.

⚠ **Do not** intersect "files the branch touched" with "files that differ from `main`". It
over-reports wildly on old branches — a file differs because *`main`* changed it later, not
because the branch is unmerged. That method reported 200 files for a branch that touched one.

⚠ **Verify against the tree, never from a note.** Project memory recorded two branches as
"gate-green, NOT merged" on 2026-08-10; both were on `main`.

### 10.2 Worktrees created from the Cowork sandbox

`git worktree add` run from the sandbox bakes the sandbox path (`/sessions/…`) into **both**
pointer files and registers the worktree under it. On the Mac, `git worktree remove ../<name>`
then fails with *"not a working tree"* even though the folder is right there. Recovery:

```
cd ~/Documents/Claude/Projects/MindsOS && rm -rf .git/worktrees/<name> && git worktree prune && git branch -D <branch> && rm -rf ../<name>
```

**Create worktrees on the Mac, not from the sandbox.** File edits from the sandbox are fine;
git operations are not (§5).

### 10.3 Enforcement

`.github/workflows/stale-branches.yml` runs weekly and **fails** when a branch's tip is older
than **14 days** with no open PR, excluding `main` and the long-lived set (`demo/*`,
`arc-solver*`, `wsd-*`, `nilm_brain`, `chore/amii-study`). The allowlist lives in the workflow.

**When it goes red, close the lane or archive the branch.** Do not raise the threshold and do
not add an exclusion to make it green — that is how §2 decayed into a 43-branch cleanup.

> **A rule with no enforcement is a rule that has already decayed.** §2 said "then delete"
> from the start. It was never checked, so it was never followed.
