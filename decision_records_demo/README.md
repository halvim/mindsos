# Decision Records — demo code home

This directory exists **only on `demo/decision-records`**, never on `main`
(RULES §1). It is a consumer of MindsOS: it registers its own DataStates and
capacities into a Local realm and drives them through core's own orchestration.
**It never edits `mindsos_*`** (RULES §3); a core change lands on `main` first
and this branch merges the tag.

- **Pinned core:** `dr-partial-record-confirmed` (squash `b276c63`), merged
  into this branch at `7a88404`. Bump deliberately: `git merge <core-tag>` →
  re-run the commands below → update `pinned_core` **here and in `STATE.json`
  on `main`, in the same ship**.
- ⚠ **Read the pin off the tree, never off a document.** This lane's gate
  condition is `git diff --stat <pin>..HEAD -- 'mindsos_*'` printing nothing,
  so a stale pin makes a green lane report red. On 2026-08-16 both this file
  and `STATE.demos.decision_records.pinned_core` still said
  `dr-fold-grounding-confirmed` — three ships out of date — and the check ran
  against it reported 8 core files and 842 insertions on a branch that had
  edited none of them. The tree's answer:
  `for t in $(git tag --list '*-confirmed'); do git diff --quiet "$t" HEAD -- 'mindsos_*' && echo "$t"; done`.
- **Research + docs home** (taxonomies, scenario notes, the demo script) stays
  at `projects/decision_records_demo/` on `main`. This directory is code.
- Governing plans: `confirmation_docs/DECISION_RECORDS_DEMO_PLAN.md` (record
  of record), `confirmation_docs/DECISION_RECORDS_V0_PLAN.md` (build order).

## What is here

| File | What it is |
|---|---|
| `dr_dump.py` | The RULES §12 command: dumps every grounding graph a run leaves, raw. **Zero third-party deps** (bare Python 3.12 venv + repo packages; in-memory MM, no FalkorDB). |
| `dr_persist_smoke.py` | The persistence smoke: runs real cases, closes them the production way (`consolidate_request` → FalkorDB), loads everything BACK and asserts live==persisted per node — plus the Episode's `consolidated_at`, `outcome_classification` and `state`. Needs `falkordb`. |
| `dr_render.py` | Item 7's renderer: the Decision Record page from persisted graphs and nothing else. G1-pure (stdlib + `mindsos_core` only); every gap raises (`RendererGapError`); render-time G6 scans its own page. |
| `dr_render_pages.py` | The §12 command for the renderer: nine cases → a real store → each page rendered FROM the store, then an end-state re-verify of every page from the store alone. `--from-root <capacity_root_ref>` renders from the store ALONE (no live KL) — the reconstructibility proof, a **Gate-7 predecessor**. `--screens <dir>` writes the Screen-A HTML per case. |
| `dr_routing.py` | The routing content (plan §2.5): exposures → desks on the Guidewire-sourced model. Beat 1 (one claim, two desks) and beat 2 (a refusal beside an answer) — a MAP over the exposures of one claim plus the reducer that assigns the claim. |
| `dr_screen.py` | Screen A: the document layout over the renderer's composed text page, plus the "what arrived" panel. Typography only — it never reads a graph; the fact guard is text EQUALITY against the renderer page, and the stylesheet is linted for hiding declarations on every compose. Stdlib only. |
| `dr_demo_run.py` | **The Gate-7 driver: three cold runs, no operator intervention.** One command; each run gets its own container AND its own subprocess, the store is asserted empty before any case executes, teardown is unconditional, and the exit code is the gate's verdict. |
| `test_dr_render_guards.py` | 27 guard tests (G1/G2/G5/G6, the §30 rulings, the correlation bijection, the stated-absence rule, the policy source line and its contract pin). Plain python or pytest; no FalkorDB. |
| `test_dr_routing_guards.py` | 3 guard tests on the routing content, including the static fold-reducer decode check firing before any member runs. |
| `test_dr_screen_guards.py` | 9 guard tests on Screen A: chrome closure, the fact-equality channel, the stylesheet lint, the classification pins. |
| `test_dr_run_guards.py` | 5 guard tests on the cold-run driver — the five ways it could report a green gate that means nothing. Fake backend; no docker, no FalkorDB. |
| `test_dr_dump_printer_guard.py` | 3 tests pinning the dump instrument itself: printed counts equal object counts; the retry delta is reported, not hidden. |
| `requirements-demo.in` | The demo's own dependency set (RULES §1). `falkordb` for the smoke, the pages and the driver; `dr_dump.py` stays zero-dep. |

**Guard total: 47** (render 27, screen 9, run 5, routing 3, dump 3). These are
the demo's own guards and are **not** part of the core gate — a demo's tests are
not in the core test image (RULES §1).

## Run commands (Linux box)

**The Gate-7 command — this is the one the gate is read from.** It starts and
tears down its own FalkorDB, three times, and needs nothing else from an
operator:

```
PYTHONPATH=. /tmp/drdemo-venv/bin/python decision_records_demo/dr_demo_run.py
```

Exit 0 means three cold runs green. Exit 1 means a run failed (the reason is
printed). Exit 3 means the store could not be started — an environment fault,
not a demo verdict. `--cold-runs N`, `--port P` and `--screens DIR` are
available; the defaults are the gate's.

`dr_dump.py` — all eleven shapes (`leaf`, `claim`, `noroute`, `replan`,
`retry`, `memberpartial`, `needsinput`, `refusal`, `outage`, `boundary`,
`codec`), or one by name:

```
PYTHONPATH=. python3 decision_records_demo/dr_dump.py all
```

The guard tests, plain python (also collectable by pytest):

```
PYTHONPATH=. python3 decision_records_demo/test_dr_render_guards.py
PYTHONPATH=. python3 decision_records_demo/test_dr_routing_guards.py
PYTHONPATH=. python3 decision_records_demo/test_dr_screen_guards.py
PYTHONPATH=. python3 decision_records_demo/test_dr_run_guards.py
PYTHONPATH=. python3 decision_records_demo/test_dr_dump_printer_guard.py
```

Smoke and pages can also be driven by hand. **Host port 6382** — on the
reference Linux box 6379 is held by a stray container and 6380/6381 by the arc
demos:

```
docker run --rm -d --name drdemo-falkor -p 6382:6379 falkordb/falkordb
PYTHONPATH=. FALKORDB_PORT=6382 /tmp/drdemo-venv/bin/python decision_records_demo/dr_persist_smoke.py
PYTHONPATH=. FALKORDB_PORT=6382 /tmp/drdemo-venv/bin/python decision_records_demo/dr_render_pages.py
PYTHONPATH=. FALKORDB_PORT=6382 /tmp/drdemo-venv/bin/python decision_records_demo/dr_render_pages.py --from-root <capacity_root_ref>
docker rm -f drdemo-falkor
```

(The default pages run prints each case's `capacity_root_ref` in its
narration — feed one to `--from-root`.)

## What these are for

Every §12 check in this lane answers its questions against output the OWNER
ran, not the lane (RULES §12). The claim shape is the demo's headline: one
Record per exposure PLUS the claim-level conclusion. The page's one stated
limit: the "Decided <date>" line comes from the Episode, which is not
store-resident — KL persistence is the server's job (ADR-0042) — so the
from-root page states that absence rather than omitting the line.
