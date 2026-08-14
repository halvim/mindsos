# Decision Records — demo code home

This directory exists **only on `demo/decision-records`**, never on `main`
(RULES §1). It is a consumer of MindsOS: it registers its own DataStates and
capacities into a Local realm and drives them through core's own orchestration.
**It never edits `mindsos_*`** (RULES §3); a core change lands on `main` first
and this branch merges the tag.

- **Pinned core:** `dr-fold-grounding-confirmed` (squash `9024c51`). Bump
  deliberately: `git merge <core-tag>` → re-run the commands below → update
  `pinned_core` in `STATE.json` on `main`.
- **Research + docs home** (taxonomies, scenario notes) stays at
  `projects/decision_records_demo/` on `main`. This directory is code.
- Governing plans: `confirmation_docs/DECISION_RECORDS_DEMO_PLAN.md` (record
  of record), `confirmation_docs/DECISION_RECORDS_V0_PLAN.md` (build order).

## What is here

| File | What it is |
|---|---|
| `dr_dump.py` | The RULES §12 command: dumps every grounding graph a run leaves, raw. **Zero third-party deps** (bare Python 3.12 venv + repo packages; in-memory MM, no FalkorDB). |
| `dr_persist_smoke.py` | The persistence smoke: runs real cases, closes them the production way (`consolidate_request` → FalkorDB), loads everything BACK and asserts live==persisted per node — plus the Episode's `consolidated_at`, `outcome_classification` and `state`. Needs `falkordb`. |
| `dr_render.py` | Item 7's renderer: the Decision Record page from persisted graphs and nothing else. G1-pure (stdlib + `mindsos_core` only); every gap raises (`RendererGapError`); render-time G6 scans its own page. |
| `dr_render_pages.py` | The §12 command for the renderer: five cases → a real store → each page rendered FROM the store. `--from-root <capacity_root_ref>` renders from the store ALONE (no live KL) — the reconstructibility proof, a **Gate-7 predecessor** (coordination §54). |
| `test_dr_render_guards.py` | 16 guard tests (G1/G2/G6, the §30 rulings, the correlation bijection, the stated-absence rule). Plain python or pytest; no FalkorDB. |
| `test_dr_dump_printer_guard.py` | 3 tests pinning the dump instrument itself: printed counts equal object counts; the retry delta is reported, not hidden. |
| `requirements-demo.in` | The demo's own dependency set (RULES §1). `falkordb` for the smoke and pages; `dr_dump.py` stays zero-dep. |

## Run commands (Linux box)

`dr_dump.py` — all eleven shapes (`leaf`, `claim`, `noroute`, `replan`,
`retry`, `memberabort`, `needsinput`, `refusal`, `outage`, `boundary`,
`codec`), or one by name:

```
PYTHONPATH=. python3 decision_records_demo/dr_dump.py all
```

The guard tests, plain python (also collectable by pytest):

```
PYTHONPATH=. python3 decision_records_demo/test_dr_render_guards.py
PYTHONPATH=. python3 decision_records_demo/test_dr_dump_printer_guard.py
```

Smoke and pages need a real FalkorDB. **Host port 6382** — on the reference
Linux box 6379 is held by a stray container and 6380/6381 by the arc demos:

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
limit (coordination §51.1): the "Decided <date>" line comes from the Episode,
which is not store-resident — KL persistence is the server's job (ADR-0042) —
so the from-root page states that absence rather than omitting the line.
