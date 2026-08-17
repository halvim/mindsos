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
| `dr_render_pages.py` | The §12 command for the renderer: twelve cases → a real store → each page rendered FROM the store, then an end-state re-verify of every page from the store alone. `--from-root <capacity_root_ref>` renders from the store ALONE (no live KL) — the reconstructibility proof, a **Gate-7 predecessor**. `--screens <dir>` writes the Screen-A HTML per case. |
| `dr_routing.py` | The routing content (plan §2.5): exposures → desks on the Guidewire-sourced model. Beat 1 (one claim, two desks) and beat 2 (a refusal beside an answer) — a MAP over the exposures of one claim plus the reducer that assigns the claim. |
| `dr_assessment.py` | Beat 4: one claim of 400,000 assessed as of two dates — the claimed amount decided against the limit in force, paying 350,000 under the 2023 edition and 375,000 under the 2024 one. The only decision in this demo whose answer the room finishes before the page renders. ⚠ It can refuse only for a reason a READER recorded (ADR-0209 D1), so a well-formed nonsense value is decided on rather than refused — the boundary any live-editing console inherits. |
| `dr_settlement.py` | Beat 3: the claim cannot be settled until a named document arrives. Same in-band refusal mechanism as beat 2, stated as such — the scope and the consequence differ (the claim, not one desk), the substrate does not. |
| `dr_screen.py` | Screen A: the document layout over the renderer's composed text page, plus the "what arrived" panel. Typography only — it never reads a graph; the fact guard is text EQUALITY against the renderer page, and the stylesheet is linted for hiding declarations on every compose. Stdlib only. |
| `dr_demo_beat.py` | **The demo, performed: one beat, live, on cue** (`up`, `1`-`6`, `down`, `list`). Prints the page raw and writes the screen; beat 6 rebuilds an earlier beat's Record from the store alone. Carries the ONLY map from the script's beats to the demo's cases. |
| `dr_demo_run.py` | **The Gate-7 driver: three cold runs, no operator intervention.** One command; each run gets its own container AND its own subprocess, the store is asserted empty before any case executes, teardown is unconditional, and the exit code is the gate's verdict. |
| `test_dr_render_guards.py` | 37 guard tests (G1/G2/G5/G6, the §30 rulings, the correlation bijection, the stated-absence rule, the policy source line and its contract pin, beat 3's refusal, the deciding fact on the leaf road, and ship B's refusing-leaf verdict line — a refusing leaf NAMES the decision it could not make, the member road does NOT gain that line because its fold already states the consequence, and two unconsumed refusal carriers raise). Plain python or pytest; no FalkorDB. |
| `test_dr_routing_guards.py` | 16 guard tests on the routing content: beats 1-2; the static fold-reducer decode check firing before any member runs; the member road's refusal-with-no-stored-words raise; and the deciding-fact set — only the read that DECIDED reaches the page, the marker never does, an unfindable question or a cross-capacity pairing raises, a verdict standing on a refusing record raises, the field is spelled the same in all three places, and the intake line does not echo the fact the deciding line is about to state; and ship B slice 1 — the claim-level line NAMES the exposure it cannot assign, every verdict carries that name on both doors, the pluraliser is checked at one and at two, the field name never reaches the page, and a refusal the record cannot name RAISES. |
| `test_dr_screen_guards.py` | 10 guard tests on Screen A: chrome closure, the fact-equality channel, the stylesheet lint, the classification pins. |
| `test_dr_run_guards.py` | 5 guard tests on the cold-run driver — the five ways it could report a green gate that means nothing. Fake backend; no docker, no FalkorDB. |
| `test_dr_no_model_guards.py` | 3 guard tests on beat 5's claim: the pinned core carries no model seam, no demo module imports it, and no case produces a value a model read. Neither check may pass vacuously. |
| `test_dr_assessment_guards.py` | 13 guard tests on beat 4: the page carries a DECISION and not two lookups, the two dates pay different amounts and name their editions, the limit decides when the claim is over it and the AMOUNT decides when it is under (both doors), a claim with no amount refuses in the reader's own words, what is payable is arithmetic on stored values, the as-of date is a read fact with its own stored question, the deciding fact carries the authority behind it, and no invented currency reaches the page. |
| `test_dr_beat_guards.py` | 5 guard tests on the per-beat runner: every scripted beat resolves to a case that exists, the memo holds refs never pages (D9), the closer refuses when no beat has run, the closer rebuilds the RICHEST Record the room watched (every position in `CLOSER_PREFERENCE`, not just the walk's pair), and every preferred case is one a beat actually runs. |
| `test_dr_dump_printer_guard.py` | 3 tests pinning the dump instrument itself: printed counts equal object counts; the retry delta is reported, not hidden. |
| `dr_mutations.py` | **The mutation harness: every new guard shown RED by a named mutation, then reverted.** One command instead of eleven hand-cycles. Applies an exact string replacement, runs every guard file in a fresh subprocess, restores in a `finally`, hashes all three sources before and after, and re-runs the guards to prove the tree came back. A mutation that reddens NOTHING prints FINDING; so does one whose red set differs from the prediction recorded beside it. Ship discipline, not demo content — the room never sees it. |
| `dr_transport.py` | **Step 1: the piece that touches the network** (plan §0.4 item 7 step 1). `LiveLLM` takes a deployment-supplied callable and it was never written; this is that callable. Stdlib `urllib`, no new dependency, registers nothing. ⚠ **This branch cannot import `mindsos_capacity.llm`** — it is on `main` and ABSENT from the pinned core — so `contract.verify_transport` is run by the OWNER from the `main` checkout, never as a guard here. ⚠ **The answer is FORCED into a shape, not repaired into one:** the extraction schema is sent as a tool with `tool_choice` forced, because a live provider returned JSON fenced in a markdown block despite two instructions not to, and repairing that in the transport would edit the model's output before anything checks it. Returns the tool input as a `Mapping`, unaltered. No free-text fallback. No words live in it — the prompt and the tool description are both injected. |
| `dr_transport_smoke.py` | **The step-1 gate: one real call, and the owner watches the answer come back.** Prints what this lane composed above what the model produced (RULES §11). Its prompt is a step-1 throwaway; the demo's stored, printable prompt lands with step 3. The owner's fixture (email B) is deliberately NOT here — that is step 3. |
| `test_dr_transport_guards.py` | 9 guard tests on the transport: all five of `LiveLLM`'s keyword args are required (bind fails with any one removed), a forced tool reply is returned UNALTERED with the model's commentary never mistaken for the answer, a non-2xx raises as an OUTAGE rather than handing back an error body, the credential appears nowhere in a return value or anywhere in the exception chain, the model id and endpoint appear nowhere in the exception THIS module raises, the per-call timeout reaches the opener, the prompt on the wire came from the injected resolver, the request FORCES the tool and sends the injected schema, and a call with no schema RAISES instead of falling back to free text. Fake opener throughout — no network, no key. |
| `requirements-demo.in` | The demo's own dependency set (RULES §1). `falkordb` for the smoke, the pages and the driver; `dr_dump.py` stays zero-dep. |

**Guard total: 101** (render 37, routing 16, assessment 13, screen 10, transport 9, run 5, beat 5, no-model 3, dump 3) — 92 before step 1, 68 before ship B, 56 before the deciding-fact ship.
⚠ **Counted with `grep -c '^def test_'`, never recalled.** This line said 67 for
the length of one ship because the last guard landed after it was written — the
eighth instance in this lane of a document disagreeing with the tree it
describes. The count and `dr_mutations.MUTATIONS` both move in the ship that
changes them. These are
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

**Performing the demo — one beat at a time.** The Gate-7 command above runs
everything in a batch and writes files; it measures the machine and cannot
perform the script. In a room, use the beat runner:

```
PYTHONPATH=. /tmp/drdemo-venv/bin/python decision_records_demo/dr_demo_beat.py up
PYTHONPATH=. /tmp/drdemo-venv/bin/python decision_records_demo/dr_demo_beat.py 1
PYTHONPATH=. /tmp/drdemo-venv/bin/python decision_records_demo/dr_demo_beat.py down
```

**Which case is which beat** (`DR_DEMO_SCRIPT.md`, `projects/decision_records_demo/`
on `main`). ⚠ **Seven of the twelve cases are NOT beats** — they are mechanism
shapes that prove the renderer stops honestly, and the room never sees them:

| Beat | Case(s) | What the room sees |
|---|---|---|
| 0 · the pain | — | spoken |
| 1 · one claim, two desks | `routing` | CLM-3007: two vehicle exposures to the routine desk, one severe injury to the specialty unit |
| 2 · the refusal beside an answer | `routingrefusal` | the same claim plus an injury exposure with no severity assessed |
| 3 · the missing document | `settlement` | CLM-5093: no proof of loss, and the Record names it |
| 4 · the policy changed | `assessprior` + `assesscurrent` | CLM-4188, 400,000 claimed, as SUBMITTED and as ASSESSED: 350,000 payable under v2023.1, 375,000 under v2024.1 — the room does both subtractions before the page appears |
| 5 · unplug the model | — | no case: there is no model. The runner checks the absence live |
| 6 · a year later | — | rebuilds an earlier beat's Record from the store alone |
| 7 · the ask | — | spoken |
| — | `claim` `refusal` `outage` `boundary` `noroute` `policyprior` `policycurrent` | **never shown** — gate evidence. ⚠ The policy pair was beat 4 until ship B gave the beat a decision; it stays because G5's guard is written on it |

`dr_dump.py` — all eleven shapes (`leaf`, `claim`, `noroute`, `replan`,
`retry`, `memberpartial`, `needsinput`, `refusal`, `outage`, `boundary`,
`codec`), or one by name:

```
PYTHONPATH=. python3 decision_records_demo/dr_dump.py all
```

The guard tests, plain python (also collectable by pytest). ⚠ **Run mutations
with `PYTHONDONTWRITEBYTECODE=1`** — a same-length mutation reverted inside one
second leaves the mutated `.pyc` cached (mtime+size unchanged), so "reverted,
green again" silently re-runs the mutation. Same defect as a `docker compose`
run without `--build`:

The mutation harness — the §12.2 obligation, mechanically. It writes to
`dr_render.py`, `dr_screen.py`, `dr_settlement.py`, `dr_routing.py`, `dr_demo_beat.py`,
`dr_assessment.py` and `dr_transport.py` and restores them in a
`finally`; if it ever reports NOT RESTORED, recover with
`git checkout -- decision_records_demo/`:

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 decision_records_demo/dr_mutations.py
```

```
PYTHONPATH=. python3 decision_records_demo/test_dr_assessment_guards.py
PYTHONPATH=. python3 decision_records_demo/test_dr_render_guards.py
PYTHONPATH=. python3 decision_records_demo/test_dr_routing_guards.py
PYTHONPATH=. python3 decision_records_demo/test_dr_screen_guards.py
PYTHONPATH=. python3 decision_records_demo/test_dr_run_guards.py
PYTHONPATH=. python3 decision_records_demo/test_dr_no_model_guards.py
PYTHONPATH=. python3 decision_records_demo/test_dr_beat_guards.py
PYTHONPATH=. python3 decision_records_demo/test_dr_dump_printer_guard.py
PYTHONPATH=. python3 decision_records_demo/test_dr_transport_guards.py
```

**Step 1's gate — the one real call.** Not a test: the callable is bound at
boot and is outside any tree check by design, so the gate is the owner seeing an
answer return. Needs a credential in the environment and reaches the network;
the build gate has neither:

```
ANTHROPIC_API_KEY=... PYTHONPATH=. python3 decision_records_demo/dr_transport_smoke.py
```

Exit 0 = an answer came back. Exit 2 = no credential. Exit 1 = the call failed,
with the reason printed.

⚠ **THE CONFORMANCE HARNESS RUNS FROM `main`, AND NOTHING ON THIS BRANCH MAY
IMPORT IT.** `contract.verify_transport` is product code written so a deployment
can prove its own transport (S-3), and `mindsos_capacity/llm/` is ABSENT from
this branch's pinned core. The first draft of `dr_transport_smoke.py` imported
it inside a `try/ImportError` for convenience and **reddened
`test_no_demo_module_imports_the_model_seam`** — an AST scan, so a
function-level import trips it exactly like a module-level one. That guard is
one of the three that survive until step 3's pin bump, and it is right. The
procedure copies the transport out of git and runs the harness against it from
`main`, leaving no seam import in the tree:

```
cd /home/sanmyaku/mindsos && git show demo/dr-transport:decision_records_demo/dr_transport.py > /tmp/dr_transport.py && git checkout main
```

⚠ **COMING BACK IS NOT JUST `git checkout`, and this procedure is what makes it
matter.** Checking out `main` creates `mindsos_capacity/llm/`; checking the demo
branch back out removes the tracked `.py` files and **leaves the untracked
`__pycache__`**, so the directory survives. Python 3 treats a directory with no
code in it as a **namespace package**, `importlib.util.find_spec` returns a spec
with `loader=None`, and
`test_the_pinned_core_carries_no_model_seam` reads that as the seam being
present and goes RED on a tree that contains no seam at all. Observed
2026-08-17, on the first use of this procedure. Return with:

```
cd /home/sanmyaku/mindsos && git checkout demo/dr-transport && rm -rf mindsos_capacity/llm && python3 -c "import importlib.util;print(importlib.util.find_spec('mindsos_capacity.llm'))"
```

That must print `None`. ⚠ **The guard's predicate is also weaker than its
name** — it claims something about the PINNED CORE and measures what this
checkout can import, counting a codeless directory as code. Not fixed here:
it is not step 1's slice, and plan §0.5 item 7 replaces all three no-model
guards with the four structural ones at step 3's pin bump. Filed as a finding
against that ship.

```
cd /home/sanmyaku/mindsos && PYTHONPATH=.:/tmp python3 /tmp/conformance.py
```

where `/tmp/conformance.py` builds the transport with the smoke's prompt, tool
and schema and calls `verify_transport` with `failing_transport=`,
`garbage_transport=` and `wrong_type_transport=` supplied — **without them three
of the contract's checks report SKIPPED and the report reads greener than it
is.** None of those three touch the network.

⚠ **Read the report's `unverifiable` lines, not only its passes.** `contract.py`
names four §6.3 properties no external observer can establish — no silent retry,
no substituted default, timeout honoured, document not logged elsewhere — and
reports them by name rather than omitting them. Only one of the four is
checkable from inside the transport, and that one has a guard here
(`test_the_timeout_reaches_the_opener`).

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
