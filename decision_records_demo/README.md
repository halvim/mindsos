# Decision Records — demo code home

This directory exists **only on `demo/decision-records`**, never on `main`
(RULES §1). It is a consumer of MindsOS: it registers its own DataStates and
capacities into a Local realm and drives them through core's own orchestration.
**It never edits `mindsos_*`** (RULES §3); a core change lands on `main` first
and this branch merges the tag.

- **Pinned core:** `dr-fold-grounding-confirmed` (squash `9024c51`). Bump
  deliberately: `git merge <core-tag>` → re-run `dr_dump.py all` → update
  `pinned_core` in `STATE.json` on `main`.
- **Research + docs home** (taxonomies, scenario notes) stays at
  `projects/decision_records_demo/` on `main`. This directory is code.
- Governing plans: `confirmation_docs/DECISION_RECORDS_DEMO_PLAN.md` (record
  of record), `confirmation_docs/DECISION_RECORDS_V0_PLAN.md` (build order).

## `dr_dump.py` — the RULES §12 command

Dumps every grounding graph a run leaves in `capacity_mm`, raw (`repr()`,
nothing translated — the §11 seam is stated at the top of the script). Shapes:
`leaf`, `claim` (map over three exposures + the fold that concludes the
claim), `noroute`, `all`.

```
PYTHONPATH=. python3 decision_records_demo/dr_dump.py all
```

Run from this worktree's root. **No third-party dependencies** — verified
against a bare Python 3.12 venv; the in-memory `MentalModel` path needs no
FalkorDB. (`requirements-demo.in` is therefore empty today; future demo
increments — persistence smoke, the renderer — add theirs there, never to
core's requirements.)

## What the dump is for

Every §12 check in this lane answers its questions against this dump — run by
the owner, not by the lane (RULES §12). The claim shape is the demo's headline:
one Record per exposure PLUS the claim-level conclusion, which grounded
nowhere until PR #158.
