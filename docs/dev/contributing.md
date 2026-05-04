---
last_confirmed_phase: 01
---

# Contributing

MindsOS is built incrementally via the phased rollout in
`confirmation_docs/PHASE_MAP.md`. Every change lives on a `phase-NN` branch
that maps to one row in §3 / §4 / §5 of that file.

## Branching policy

```
main                ─── always reflects the most-recent confirmed phase
└── phase-00        ─── implementation branch for Phase 00 (merged + tagged)
└── phase-01        ─── implementation branch for Phase 01 (current)
└── phase-NN        ─── one branch per phase
```

- A phase chat opens `phase-NN` off `main` (or the most-recent confirmed
  phase if `main` is mid-merge).
- When implementation is complete and tests pass, the tester opens a PR
  against `main` and squash-merges.
- The tester then tags the merge commit `phase-NN-confirmed` and pushes the
  tag, which triggers `.github/workflows/release.yml`.

## Per-phase workflow

For full detail see `confirmation_docs/PHASE_MAP.md` §1, "Per-phase workflow".
Summary:

1. **Implement** on `phase-NN`.
2. **Tests pass in-container.** `docker compose run --rm mindsos-test pytest tests/`
   is canonical (see `testing.md`). Host-side runs allowed for dev iteration
   but do not count.
3. **Manual CLI exploration.** Tester pokes the new commands and confirms
   they behave as described in the phase row's "Pass criterion".
4. **Confirm.** Phase 01+: `mindsos confirm-phase --init-notes phase-NN` →
   edit notes file → `mindsos confirm-phase --phase NN --notes-file …`.
   Phase 00 only: hand-fill `confirmation_docs/_template.md`.
5. **Review** the produced `PHASE_NN_CONFIRMED.md`; hand-edit if needed.
6. **Update the next phase row** in PHASE_MAP if implementation revealed
   refinements (the phase chat does this).
7. **Push branch, open PR, merge, tag, push tag.**

## Phase rollback

If Phase N+k reveals a regression in already-confirmed Phase N: tag
`phase-NN-superseded`, open `phase-NN-v2`, rewrite the PHASE_MAP row, ship
v2, tag `phase-NN-v2-confirmed`. Original `phase-NN-confirmed` remains in
history but is no longer the install target. See PHASE_MAP §1 row "Phase
rollback / supersession" for the full policy.

## Code style

- Python 3.12+. Type hints throughout. `from __future__ import annotations`
  in every file.
- Errors go to stderr; structured success goes to stdout. Every CLI command
  supports `--json` for test-friendly output.
- No emojis in source files unless the user explicitly asks.
- Pre-existing tests must continue to pass on every phase.

## Out of scope (for the L0–L3 plan)

L4 (Intelligence), L5 (Mental Model), and FOL are deliberately deferred. See
PHASE_MAP §1 "Out of scope" for the full list.
