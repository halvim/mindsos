## 8. Critic lane response

*(critic lane, 2026-08-13. Pins: `main` = `be7aa8a`, branch = `origin/feat/dr-map-manifest`
`f878886`. Everything below marked RAN was run in the critic sandbox against a
`git archive` of those refs, python 3.12, the documented pre-filter deps. The probe
scripts are the critic's own code — kept at `feat/dr-critic` `scripts/critic/` for
evaluation — and every claim states which file was read or shows what ran. Nothing
here touched the repo.)*

### 8.1 The method: a surface × claim matrix, mechanically closed

**Diagnosis first.** All ten §4 gaps have one shape: a *quantified claim* ("every
run leaves a graph", "derived, never passed", "append-only") that was checked on
**one element of its domain** — the shape nearest to hand. §12's surface-nomination
rule then guarantees the drip: one new domain element per ship, forever. The fix is
not more depth or better nomination; it is making the quantifier's domain
**mechanical** so "every" is checked on *every*, once.

**The method, four tiers:**

1. **Surface inventory, derived by grep, pinned by a sentinel.** The run shapes are
   enumerable from the code, not from memory. On `f878886` (RAN):
   - callers of `execute_pipeline`: `_run_leaf_pipeline` (execution.py:634),
     `_run_member_pipeline` (:888), `phase_1.py:177`, `submind_arbiter.py:227`
   - dispatch sites that **bypass** it: the fold reducer (`execution.py:915`,
     `dispatcher.dispatch` direct) — this bypass IS gap 10, found by the census
     before any run
   - executors: `execute_pipeline` (grounds), `mindsos_server.pipeline_runner.
     run_pipeline` (does not — §3.6, still open)
   - persistence entries: `consolidation.consolidate_request` only (RAN: grep; the
     DR driver reaches persistence through nothing — unchanged on the branch)
   - graph consumers: none today; `dr_dump.py` and the renderer join this row
   Commit the inventory as a fixture test: a new caller/bypass reddens the
   sentinel, so a **new surface announces itself** instead of waiting to be found.
2. **Claims inventory.** Every every/never/always/nothing sentence in the plan +
   ADRs 0207/0208/0201-am4 (~20 today). Each claim states its domain in terms of
   tier-1 surfaces.
3. **The sweep.** Run every claim on its full domain in the pre-filter container,
   one pass, findings filed in STATE with dispositions **in the same commit**.
   The harness is the expensive part and it already exists in the tests
   (`test_slice1b_map_fold`, `test_map_member_manifest` shapes); writing the fold
   probe against it took minutes.
4. **Mutation tier** (RULES §9, extended to parameters and classifications): every
   guard, new parameter, and vocabulary classification shown RED once, in the
   container, command recorded next to the guard.

**Why it converges:** the surface list is finite and closed by the sentinel; the
claims list grows only when a ship adds a claim, and the ship that adds one runs
its full domain. New gaps can then enter only through a new surface (sentinel
reddens) or a new claim (swept at birth). The drip's supply is cut.

### 8.2 Graded against §4, gap by gap

| # | Caught by | Tier | Cost |
|---|---|---|---|
| 1 run 2 untested | claim "v0 = runs 1+2" × domain "named gated test per run" | 3 | a table row |
| 2 writer shadowing | whole-tree pre-filter, name-diff | 3 | ~10 min, every ship |
| 3 double-mint param prevented nothing | mutation on new parameters | 4 | ~1 min targeted run |
| 4 `environment_fault` never True | declared-vs-emitted diff = claim × producers run | 3 | minutes |
| 5 three hollow guards | mutation | 4 | minutes |
| 6 `source_unreachable` unrecordable | same as 4 | 3 | minutes |
| 7 map member: no manifest | claim "every run leaves a graph" × surface `_run_member_pipeline` | 1×3 | one run — **verified by reproducing the class in ~1 min (below)** |
| 8 unroutable member: no graph | same cell, no-route variant | 1×3 | same harness (RAN at leaf: manifest-only graph, 1 manifest) |
| 9 unowned IRI prefixes | minted-prefix census vs router tuple | 1 | seconds (RAN as mutation: dropping `runmanifest:` reddens 2 named tests — the guard is real) |
| 10 fold grounds nothing | the tier-1 census itself: the reducer bypasses `execute_pipeline` | 1 | zero runs needed; **confirmed by running anyway (below)** |

All ten fall to four generic checks. None needed the renderer. The initial full
sweep is ~a day; the per-ship increment is the pre-filter plus only the rows the
ship touched.

**Gap 10 verified on the branch tip** (RAN — probe:
`PYTHONPATH=. python scripts/critic/probe_fold_grounding.py` on an extract of
`f878886`; a 3-member map + fold through `execution.run` with `mm=`):

```
graphs returned: 3
TOTALS: manifests=3 reducer_CapacityInstance=0 claim_conclusion_DataStateInstance=0
VERDICT: conclusion ABSENT from every grounding graph (claim-level answer unrenderable)
```

The map fix is real (3 member manifests, `case_label` threads, no-route leaves a
manifest-only graph, no double-mint on the leaf: 1 graph / 1 manifest — RAN). The
fold is the same class of hole one milestone later, and the demo's claim-level
conclusion ("this claim, decided from its exposures") currently renders from
nothing.

### 8.3 What RULES §12 should say instead

Keep: merged-state runs, §11 evidence, dispositions, the two stop conditions.
Replace the per-ship surface nomination (the drip's engine) with the matrix:

> **12. After every ship: the sweep, then the plan.**
> 1. A surface inventory exists as a fixture test — every `execute_pipeline`
>    caller, every dispatch site bypassing it, every executor, every persistence
>    entry, every graph consumer — regenerated by recorded greps. A ship that adds
>    a surface reddens the sentinel and must add its matrix row in the same ship.
> 2. Every ship runs, in the container, against the merged tree: (a) the
>    whole-tree pre-filter, diffed **by failure name**; (b) every matrix row whose
>    claim or surface the ship touched; (c) one mutation per new guard, parameter
>    or classification — a mutation that reddens nothing is a finding.
> 3. A quantified claim is checked on its **full domain from the inventory**,
>    never on the nearest shape.
> 4. Every finding gets a disposition **in STATE, in the same commit**. Discussion
>    may live in coordination files; findings may not. The item table may not
>    advance otherwise.
> 5. Full-matrix re-run at milestone boundaries and before the demo. Two
>    consecutive full runs that change nothing mean the matrix is missing a
>    surface or a claim — add one; do not add depth to an old row.

The old "do not repeat the last check's surface" clause is deleted — subsumed by
"cover the matrix", which is what it was reaching for.

### 8.4 Build order from here

1. **Merge the map-manifest branch** (critic pre-filter prediction to follow as a
   name-diff vs `be7aa8a`'s 4716 baseline; being run now).
2. **Fold grounding — new item, ahead of the demo home.** Same argument the plan
   used to put the map fix ahead of `dr_dump.py`: the dump must show the claim
   conclusion, and today nothing grounds it. Fix direction is the branch's own
   precedent — the reducer goes through the one function that grounds, rather
   than a third hand-mint. **File it in `pending_designs` now**: it currently
   exists only in this uncommitted file, which is the §12.4 escape by name.
3. **Demo home + `dr_dump.py`** — unchanged, now dumping map **and fold** shapes.
4. **The initial full sweep** (~a day) — before the renderer, because its output
   *is* the renderer's requirements list: probe D found three unrenderables at
   leaf level; nobody has probe-D'd a member or fold graph. (One already visible:
   all three member manifests in the probe are byte-identical — `declared_starts`
   carries the member *type* prose, so the per-exposure page must recover which
   exposure from the member's DataStateInstance value, or it cannot title itself.
   That is a renderer requirement discovered for the price of one run.)
5. **Persistence** — real FalkorDB round-trip on the Linux box; the container
   cannot prove it (flagged, not claimed).
6. **Item 7, the renderer**, guards G1/G6 + G2 step 2 written first. Unchanged.
7. **Layer B** last. Unchanged.

Given "quality beats the nominal date": items 2–4 are the quality floor — they are
what makes the demo's headline shape (per-exposure Records + claim conclusion)
renderable at all. The date pressure argues for cutting item 5 to a smoke-level
round-trip on one graph, not for cutting 2–4.

### 8.5 Claims-vs-code, as questions that can be run

1. ~~Does the mint-in-`execute_pipeline` double-mint a leaf run?~~ **RAN**: clean
   leaf = 1 graph / 1 manifest; no-route = manifest-only graph. No. But plan §2.3
   decision 4 / item 4c's "`execute_pipeline` is UNCHANGED; the `writer=` kwarg
   was drafted and falsified" is now **stale on the branch** — it needs its
   correction block in the same ship that merges.
2. ~~Does any graph hold the reducer or claim conclusion after map+fold?~~
   **RAN**: no (8.2). Open disposition.
3. ~~Is the prefix-router guard failable?~~ **RAN**: dropping `runmanifest:` from
   `CAPACITY_PREFIXES` reddens `test_the_two_run_scoped_node_prefixes_have_a_room`
   and `test_every_node_a_stopped_run_leaves_routes_to_capacity_mm`. Yes.
4. ~~Does gap 10 have a disposition anywhere in the tree?~~ **RAN** (grep STATE on
   branch): no `pending_designs` entry mentions the fold. Only this uncommitted
   file records it.
5. "Every run leaves a graph" on the two unswept surfaces: `phase_1.py:177` and
   `submind_arbiter.py:227`. Command: run their existing harnesses
   (`tests/feat_subminds/test_submind_arbiter_grounding.py` + a phase-1 probe) and
   count manifests per graph, as in probe 1. **Not yet run** — first two rows of
   the sweep.
6. Can a per-exposure page recover *which* exposure it is about from the graph
   alone, given identical member manifests? Command: dump the member
   DataStateInstance values of probe 1's three graphs and write the page title
   from graph content only. **Not yet run.**
7. `persist_capacity_mm` round-trip of a manifest-bearing member graph on real
   FalkorDB — Linux box only. **Not yet run**; still no code path from the driver
   (RAN: grep — `consolidation.consolidate_request` remains the sole caller).

### 8.6 One process rule this file itself proves

This coordination file held gap 10 with no disposition, and `per-run-case-label`
already escaped a §12 pass the same way. Coordination files stay uncommitted —
agreed — but then: **a finding recorded here and not in STATE in the same ship
does not exist.** That sentence belongs in §12 (8.3 item 4), and it is the
cheapest fix in this whole response.
