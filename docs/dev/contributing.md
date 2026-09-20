---
last_confirmed_phase: 02
verified_at: 5172b3c
---

# Contributing

MindsOS was built through the numbered rollout in
`confirmation_docs/PHASE_MAP.md`, which ran to Phase 50. **Core work no longer
uses phase numbers**: it lands on `feat/*` branches and ships under a
`<name>-confirmed` tag (RULES §2 and §7).

## Branching policy

Per RULES §2:

- Cut the branch off **`origin/main`**, never off another lane's branch.
  Short-lived branch names are `feat/*`, `fix/*`, `chore/*` — plus the
  historical `phase-NN`, `wsd-NN`, `dwf-NN`, `fol-NN`.
- Open a PR against `main` and squash-merge. `phase-ci.yml` gates both `main`
  and pull requests into it, so **a PR gates itself**.
- Delete the branch and its worktree afterwards — RULES §10, not optional.
- A shipped core change is recorded as a **tag**, not a branch: a phase as
  `phase-NN-confirmed`, anything else as `<name>-confirmed`. A
  `phase-*-confirmed` tag additionally triggers
  `.github/workflows/release.yml`.

## Per-phase workflow (Mac + Linux split) — the PHASE ritual

The steps below are the ritual for a numbered phase. They still describe how
a phase was shipped, and `mindsos confirm-phase` still works; a non-phase core
ship skips the confirmation doc and the tag is `<name>-confirmed`.

MindsOS development happens on two machines synchronised via git:

- **Mac:** code editing (Claude sessions live here). File authoring,
  `git commit`, `git push`.
- **Linux:** Docker + Compose v2 + Python ≥ 3.12 + git. In-container test
  runs (canonical pass criterion). Manual CLI exploration. `mindsos
  confirm-phase`. Tag-and-push.

The Mac never sees the Linux filesystem and vice-versa — every recipe in
this repo tags steps `[Mac]` or `[Linux]` explicitly.

For full detail see `confirmation_docs/PHASE_MAP.md` §1 ("Per-phase
workflow" + "Two-machine workflow"). Summary:

1. **[Mac] Implement** on `phase-NN`. Branch off `origin/main`, never off
   the prior phase's branch.
2. **[Linux] Tests pass in-container.** `docker compose run --rm
   mindsos-test pytest tests/` is canonical (see `testing.md`). Host-side
   runs allowed for dev iteration but do not count.
3. **[Linux] Manual CLI exploration.** Tester pokes the new commands and
   confirms they behave as described in the phase row's "Pass criterion".
4. **[Linux] Confirm.** Phase 02+: `mindsos confirm-phase --init-notes NN`
   → edit notes file → `mindsos confirm-phase --phase NN --notes-file …`.
   The wrapper preflights `doctor --self-test --static-only` and aborts on
   drift unless `--skip-tests`. Phase 01 used `--init-notes phase-NN` (still
   accepted as a legacy alias). Phase 00 only: hand-fill
   `confirmation_docs/_template.md`.
5. **[Linux] Review** the produced `PHASE_NN_CONFIRMED.md`; hand-edit if
   needed.
6. **[Mac] Update the next phase row** in PHASE_MAP if implementation
   revealed refinements (the phase chat does this).
7. **[Mac] Verify the working tree is clean** before opening the PR. In
   particular, `notes-phase-NN.md` and `confirmation_docs/PHASE_NN_CONFIRMED.md`
   must be **tracked + committed** — Phase 01 hit a `release.yml` "Verify
   confirmation doc exists" failure because the doc was untracked at the
   squash-merge boundary.
8. **[Mac] Push branch, open PR, merge.**
9. **[Mac, on `main`] Tag the squash-merge commit** `phase-NN-confirmed`
   and push the tag.

## Host setup (Linux box, Phase 02+)

`mindsos confirm-phase` runs from a Python ≥ 3.12 venv on the Linux host —
**not** via `docker compose run`. The prod container has no `git`, no
`docker` CLI, and no docker socket; the wrapper shells out to all three.

```sh
# [Linux] one-time setup
cd <the repo checkout>
python3 --version           # must report 3.12+
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
mindsos doctor --self-test --static-only --json | jq .
```

After the setup, every subsequent `mindsos confirm-phase ...` invocation
is run from the venv.

## Phase rollback

If Phase N+k reveals a regression in already-confirmed Phase N: tag
`phase-NN-superseded`, open `phase-NN-v2`, rewrite the PHASE_MAP row, ship
v2, tag `phase-NN-v2-confirmed`. The v2 confirmation doc lives at
`confirmation_docs/PHASE_NN_v2_CONFIRMED.md` (sibling file; original kept
on disk). Original `phase-NN-confirmed` tag remains in history but is no
longer the install target. See PHASE_MAP §1 row "Phase rollback /
supersession" for the full policy.

## Code style

- Python 3.12+. Type hints throughout. `from __future__ import annotations`
  in every file.
- Errors go to stderr; structured success goes to stdout. Every CLI command
  that reports state supports `--json` for test-friendly output; the
  exceptions are the `brain` REPL and the `instances` / `persistence` write
  verbs (see `conventions.md`).
- No emojis in source files unless the user explicitly asks.
- Pre-existing tests must continue to pass on every phase.

## Out of scope (for the L0–L3 plan)

L4 (Intelligence), L5 (Mental Model), and FOL are deliberately deferred. See
PHASE_MAP §1 "Out of scope" for the full list.
