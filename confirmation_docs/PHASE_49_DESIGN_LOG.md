# Phase 49 — Integration C: design log

**Status:** R0 design pass (analysis-only; no branch cut, no impl). Authored
by the Phase 49 Cowork chat under the operating-mode instruction *"reanalyze
the plan, list pushbacks with options, show your pick; pause before impl."*

**Scope (locked by `POST_PHASE_38_PHASE_MAP.md §4 Phase 49 row`):** the LAST
numbered phase of the post-Phase-38 plan. **Net-new code? No** — composes
shipped L0–L5 pieces into one end-to-end exercise, ships the
`usage/cookbook/end-to-end.md` cookbook page, and closes PB-HHH (Falkor index
strategy). Trivial-task substrate verification, NOT a feature-complete
cognition demo (that is WSD-gated).

> This log is unusually long because the operator will not be giving
> mid-stream feedback this round ("analyze, choose the best, list picks for
> end approval"). Every fork is therefore resolved here with a pick + reason,
> and the picks are collected in §7 for a single approval gate.

---

## 0. Prereq check (run 2026-06-09)

| Check | Result |
|---|---|
| Tags `phase-4[0-8]-confirmed` present | ✅ 40–48 all present |
| `main` tip | `1952260` (Phase 48 confirm commit), tag `phase-48-confirmed` at it |
| Branch point for `phase-49` | `phase-48-confirmed` (= `main` tip) |
| Working tree | clean of phase work; long-standing untracked Robot-Demo corpus + `demo_ui/ prototype_zero/ sim/ web/` + modified `docs/future_work/L3_FUTURE_WORK.md` + 4 tracked modified docs (CLAUDE.md, HANDOFF.md, PHASE_MAP, L3_FUTURE_WORK) — **leave alone; stage selectively; never `git add -A`** |
| `tests/phase_49/` | does not exist yet (new dir) |
| ADR high-water | `docs/decisions/adr/0180-*`; next free = **0181** |

No blocker. `phase-49` can branch off `phase-48-confirmed` once R0 picks are
authorized.

**Required-reading ack:** HANDOFF §1/§2.5/§3.1.19–21/§4/§9/§10; PHASE_MAP
§0/§1/§3/Phase-49 row/§6/§7; PHASE_48_CONFIRMED + PHASE_48_DESIGN_LOG;
PHASE_47/46_CONFIRMED; `text-realm.md`; `_workbench/cookbook_routing.md`;
`future_work/L5_FUTURE_WORK.md` (PB-HHH/L5-NEW-13 framing). All read in full.

---

## 1. Integration surfaces (S-format)

The Phase 49 row decomposes into these surfaces. Each is tagged with its
ship reality after the grounding probe.

- **S1 — End-to-end scenario harness** (`tests/phase_49/integration_c.py` +
  `test_integration_c_scenario.py`). Drives L0 login → KL bootstrap → L3
  invoke → L4 enqueue/lifecycle → L5 consolidation → Episode write → Falkor
  persister flush + reload round-trip → dream driver. **Composition only.**
- **S2 — Cookbook page** (`docs/usage/cookbook/end-to-end.md`) + nav entry +
  `test_cookbook_page_renders.py`. Mirrors `text-realm.md` format.
- **S3 — PB-HHH Falkor index decision** + (per pick) one ADR + index-decision
  test anchor. **No `indexes.py`** (see PB-HHH).
- **S4 — ADR-amendment sentinel test** (`test_adr_amendment_sentinels.py`) —
  chain-link from Phase 48; anchors the new index ADR.
- **S5 — Version bump 48→49** (10 surfaces; slot 49 > high-water 48 → full
  bump). Mechanical; enumerated in §6.
- **S6 — Outstanding Phase 38 §4 doc closures.** #13 (society-of-mind) shipped
  Phase 48; #14 (per-page ADR cleanup) absorbed Phase 42; #15 dropped. **Net
  work: zero** — verify-and-note only.

---

## 2. Grounding probe — what actually shipped (the reality the scenario must
respect)

Probed the live tree at `phase-48-confirmed`. Five findings change how the
scenario must be written; all are routed into the pushbacks below.

1. **`text.tokenize` does not exist.** Shipped text builtins are
   `text.space_split` (`capacity:perception:text.space_split`) and
   `text.sentence_split` (`mindsos_capacity/builtins/text.py`). The PHASE_MAP
   row's "`text.tokenize`" is naming drift. → PB-1.

2. **The v0 lifecycle never dispatches a real L3 capacity.**
   `mindsos_intelligence/execution.py::run` emits one **notional**
   `StepExecutionRecord` per leaf Milestone and sets the PipelineRun to
   `completed` — it does *not* call `dispatcher.dispatch(...)` on any
   capacity. `planning_v0._derive_initial_plan` produces a single leaf
   Milestone with no real Pipeline body; `phase1_v0`/`orchestration_v0` are
   placeholder verdict-emitters. So the chain "task_input → text.space_split →
   Plan → … → consolidation" described in the PHASE_MAP row is **not** a
   single linear data-flow in the shipped substrate. → PB-1 (core fork).

3. **Consolidation is real and KL-gated.** `orchestrator._consolidate` →
   `consolidation.consolidate_task` fires on all three terminal paths unless
   `simplified`. `consolidation_enabled(dispatcher)` requires BOTH the
   `consolidate:mm` capacity registered AND a KL bound to the dispatcher
   (`dispatcher._kl is not None`). `consolidate:mm` writes the 6-field D-B47
   Episode + materialises the Memory composite + the `MEMORY_CONTAINS_EPISODE`
   edge into the user's **Local** metagraph (`KnowledgeLayer` →
   `local_metagraph(user)`), via the ADR-0180 pre-authorized `writeable`
   capability (no global cap needed for a Local write — PB-10 fix).

4. **The persister is whole-metagraph save/load, not query-by-index.**
   `FalkorDBLocalPersister.save(user_id, metagraph)` / `load(user_id)` /
   `delete(user_id)` round-trip the entire Local metagraph natively
   (`mindsos_server/persistence/local_persister.py`). There is **no indexed
   query path** anywhere in the v1 read flow — `MetagraphView.get_edges`
   walks in-memory. → PB-HHH (no index consumer exists yet).

5. **The dream driver is synchronous-callable and re-runs from `task_input`.**
   `dream_cycle.py` ships `invoke_dream_capacities`, `run_dream_cycle`, and a
   `DreamDriver` callable. v1 collects `DreamDirective`s from the 3 `dream.*`
   capacities over episode descriptors; re-execution goes through a provided
   `re_executor` hook. Faithful episode→MM reconstruction,
   `replay_recorded`-vs-`re_execute_capacities` differentiation, and real ALS
   firing are **WSD-gated** (PHASE_48_CONFIRMED). The Phase-46
   `DreamCycleTimer` runs the driver on a background thread (timing-
   nondeterministic). → PB-3.

**Integration-test infra precedent confirmed:** `@pytest.mark.integration`
is registered in `tests/conftest.py`; Integration B (`tests/phase_32/`) uses
a `scenario_falkordb_clean` conftest fixture that `pytest.skip`s when no live
FalkorDB sidecar is reachable. The canonical gate
(`docker compose run --rm mindsos-test pytest tests/`) brings up `falkordb`
(`mindsos-test depends_on: falkordb: service_healthy`), so integration tests
**run live** at the gate and **skip gracefully** elsewhere / under
`-m 'not integration'`.

---

## 3. Pushbacks (forks) — options + pick

### PB-1 — The scenario conflates a read-side L3 invoke with a write-side
L4→L5 lifecycle that never invokes L3. *(core fork)*

The PHASE_MAP step-list reads as one linear chain through `text.tokenize`.
Reality (probe findings 1+2): (a) the capacity is `text.space_split`, and (b)
the v0 lifecycle's leaf-pipeline execution emits a notional record and
dispatches nothing. A faithful single-chain "tokenize feeds the plan feeds
consolidation" does not exist in shipped code.

**Options:**
- **PB-1a — Two stitched slices sharing one live session + KL + persister.**
  The harness runs, against the *same* Falkor-backed `KnowledgeLayer` and L0
  session: (i) the **read-side** L3 slice — `install_text_capacities` +
  `find_pipeline(DS_RAW_TEXT→DS_TOKENS)` + invoke `text.space_split` on
  `"the cat sat"` → `["the","cat","sat"]` (the text-realm slice); and (ii) the
  **write-side** L4→L5 slice — `run_lifecycle({"text": ...})` over the v0
  catalogs → consolidation writes a real Episode/Memory/edge into the Local
  metagraph → `FalkorDBLocalPersister.save` + `load` round-trip asserts the
  Episode persisted → dream driver run synchronously. The cookbook documents
  the seam honestly (the L4 lifecycle executes v0 *placeholders*, not the
  tokenize output).
  - *Pros:* zero product-code change (honors "Net-new code? No"); honest;
    exercises every named layer L0–L5 + the persister round-trip; respects the
    "WSD replaces v0 atomically" decision (no v0 surgery); matches the
    text-realm precedent of documenting "does not" boundaries.
  - *Cons:* the two slices are co-resident, not a single data-flow; a reader
    expecting "my text gets tokenized then becomes the Episode" must read the
    seam note. Mitigated by explicit cookbook framing.
- **PB-1b — Make `text.space_split` the real leaf-Pipeline body.** Change
  `execution.py` to dispatch the leaf Pipeline's capacity steps and wire a
  catalog that routes the v0 leaf to `text.space_split`.
  - *Pros:* a true single chain.
  - *Cons:* net-new product code in the convergence-complete substrate;
    contradicts "Net-new code? No"; mutates the v0 execution loop that WSD is
    chartered to replace atomically; risks regressing 46/47/48 lifecycle
    tests. **Reject.**
- **PB-1c — Drop the L3-invoke step.** Scenario = L4→L5 only.
  - *Cons:* loses L0→L3 coverage; the cookbook's whole lineage is the
    text-realm read-side slice; PHASE_MAP explicitly lists the L3 invoke.
    **Reject.**

**PICK: PB-1a.** Also **rename `text.tokenize`→`text.space_split`** everywhere
in the scenario + cookbook (finding 1). The harness is a `ScenarioState`
thread of step helpers mirroring Integration B's 11-step shape.

---

### PB-HHH — Falkor index strategy for cross-sub-MM hyperedge queries.
*(the routed Phase 49 R0 decision; PHASE_MAP §7 q2 / L5-NEW-13)*

The question (Chat B PB-HHH): which cross-sub-MM hyperedge queries —
Pipeline→member CapacityInstances/DataStateInstances via IntergraphHyperEdge;
`MEMORY_CONTAINS_EPISODE`; episode lookup by task-pattern — need Falkor
indexes at scale? Probe finding 4: **there is no indexed query consumer in
v1.** The persister is whole-metagraph save/load; reads walk `MetagraphView`
in-memory. The future indexed-query consumers (WSD retrieval, memory-cluster
secondary index L5-NEW-11, dream candidate scans) are all deferred.

**Options:**
- **PB-HHH-A — Decide-and-document; ship zero index code.** Ratify the index
  *strategy* in a lightweight ADR (0181) + the cookbook "scaling" section:
  name the queries that *will* need indexes and the index each wants — node-
  label+property indexes on `Episode.task_pattern_iri`, `Memory.memory_id`,
  and the IntergraphHyperEdge membership relation — and **defer physical
  creation to the first real query consumer (WSD retrieval chat)**. No
  `mindsos_server/persistence/indexes.py`, no migration scripts.
  - *Pros:* honors the project's load-bearing consumer-discipline rule (defer
    absent-consumer surfaces — every Phase 39–48 chat applied it); closes q2
    with a real decision + an ADR ("index definitions land in the cookbook
    page + an ADR if substantial"); zero speculative code to maintain or
    regress; FalkorDB `CREATE INDEX` semantics are recorded for the consumer
    chat to apply verbatim.
  - *Cons:* `test_falkor_index_present.py` (PHASE_MAP-named) has nothing to
    assert → folded into S4 (see PB-5). A future reader might expect physical
    indexes "shipped at 49"; the ADR states explicitly they are routed.
- **PB-HHH-B — Ship `indexes.py` + index DDL now.**
  - *Pros:* indexes exist when the consumer lands.
  - *Cons:* speculative; no query exercises them at v1 (whole-graph
    save/load); the index set is best decided *with* the WSD retrieval query
    shapes, which don't exist yet — premature commitment risks indexing the
    wrong properties. **Reject** (violates consumer discipline).
- **PB-HHH-C — Punt (no decision).**
  - *Cons:* PB-HHH is an explicit Phase 49 R0 obligation; q2 must close.
    **Reject.**

**PICK: PB-HHH-A.** Ship **ADR-0181 "Falkor index strategy for cross-sub-MM
queries"** (status Accepted; decision = strategy ratified, physical creation
routed to WSD retrieval as first consumer) + a cookbook "Scaling / indexes"
section. No index code. Update `L5_FUTURE_WORK.md` L5-NEW-13 owner to
"WSD retrieval (physical creation); strategy ratified ADR-0181 @ Phase 49."

---

### PB-2 — Live Falkor vs in-memory KL for the scenario test.

The scenario explicitly includes "Falkor-backed persister flushes (Phase 44)"
— only meaningful against live Falkor.

**Options:**
- **PB-2a — Live-Falkor `@pytest.mark.integration` headline scenario + a thin
  in-memory lifecycle companion.** The headline `test_integration_c_scenario`
  is `@pytest.mark.integration`, uses a `scenario_falkordb_clean`-style skip
  fixture (copy phase_32 pattern), and runs in the canonical docker gate where
  `falkordb` is healthy — exercising the real persister round-trip. A second,
  non-integration in-memory test (`KnowledgeLayer.bootstrap()`) asserts the
  L4→L5 chain + consolidation deterministically so `pytest -m 'not
  integration'` and sidecar-less CI still cover the chain. (Mirrors the
  existing split: phase_47 in-memory smokes + phase_32 live-Falkor scenario.)
  - *Pros:* exercises the headline Phase-44 surface; degrades gracefully;
    matches Integration A/B precedent exactly; deterministic chain coverage
    survives sidecar-less runs.
  - *Cons:* two test entry points instead of one. Acceptable — they assert
    different things (round-trip persistence vs chain determinism).
- **PB-2b — In-memory only.** Skips the persister flush — the headline Phase-44
  step. Defeats the integration purpose. **Reject as primary.**
- **PB-2c — Live-Falkor only.** No deterministic coverage when the sidecar is
  absent (local dev, `-m 'not integration'`). **Reject as sole.**

**PICK: PB-2a.**

---

### PB-3 — How much of the dream/ALS background step is exercisable.

Probe finding 5: real re-execution / ALS / reconstruction are WSD-gated; the
`DreamCycleTimer` background thread is timing-nondeterministic.

**Options:**
- **PB-3a — Drive the dream driver synchronously; assert directives.** Call
  `run_dream_cycle` / `DreamDriver.__call__` directly (not via the live timer)
  over the consolidated Episode(s); assert the 3 `dream.*` capacities emit
  `DreamDirective`s (and that `dream.retry` carries a `ReplanInjectionDirective`
  on a failed episode). Use an identity/no-op `re_executor` (live re-execution
  WSD-gated). Cookbook notes the `DreamCycleTimer` exists (Phase 46) but the
  scenario drives the driver synchronously for determinism.
  - *Pros:* deterministic; exercises the real Phase-45 capacities + Phase-48
    driver wiring; CI-stable; honest about the WSD gate.
  - *Cons:* doesn't prove the background *timer* fires — but that's a Phase-46
    unit concern already covered (`test_intelligence_layer_lifecycle`), not an
    integration concern.
- **PB-3b — Start the timer and assert it fired.** Nondeterministic; flaky.
  **Reject.**
- **PB-3c — Omit dream.** Loses Phase 45/48 coverage the row lists. **Reject.**

**PICK: PB-3a.**

---

### PB-4 — Cookbook scope + driving style vs the text-realm precedent.

`text-realm.md` is read-side L0→L3, mixes CLI (login, capacity invoke) +
Python-API (KL bootstrap), has a "Does / Does not" section, golden outputs,
and a "the test is load-bearing; if prose drifts, the test wins" pointer. The
L4→L5 substrate has **no CLI verb** (enqueue/lifecycle/consolidation are
Python-API internal).

**Options:**
- **PB-4a — Mirror text-realm's mixed style + honest boundaries.** CLI for L0
  login + L3 `capacity invoke capacity:perception:text.space_split`;
  Python-API for KL-from-Falkor bootstrap, `run_lifecycle`, consolidation
  inspection, `FalkorDBLocalPersister` round-trip, and the dream driver. A
  "What this does / does not do" section states plainly: does NOT demonstrate
  real cognition (v0 placeholders); the L4 lifecycle does not consume the
  tokenize output (the seam, PB-1a); live re-execution / ALS WSD-gated; **no
  physical Falkor indexes ship — strategy only (ADR-0181)**. Front-matter
  `last_confirmed_phase: 49`. Points at `tests/phase_49/test_integration_c_
  scenario.py` as load-bearing.
  - *Pros:* consistent with the only existing cookbook; honest; the test is
    the regression anchor.
  - *Cons:* none material.
- **PB-4b — Pure-CLI cookbook.** Impossible — no L4/L5 CLI verbs. **Reject.**

**PICK: PB-4a.**

---

### PB-5 — Test-module layout + the 4 PHASE_MAP-named test files.

PHASE_MAP names: `integration_c.py` (harness), `test_integration_c_scenario.py`,
`test_cookbook_page_renders.py`, `test_falkor_index_present.py`,
`test_adr_amendment_sentinels.py`. Under PB-HHH-A no physical index ships, so
`test_falkor_index_present.py` has nothing to assert; and the Phase-48
docs-nav test found `mkdocs.yml` is not copied into the test image (skips when
absent — nav validated by `mkdocs build` on the docs host).

**Options / pick (bundled):**
- **PB-5a (PICK):**
  - `tests/phase_49/integration_c.py` — `ScenarioState` + step helpers
    (shared harness).
  - `test_integration_c_scenario.py` — headline `@pytest.mark.integration`
    live-Falkor scenario **+** the in-memory chain companion (PB-2a).
  - `test_cookbook_page_renders.py` — assert `end-to-end.md` exists + is in
    `mkdocs.yml` nav; mirror Phase-48's skip-if-`mkdocs.yml`-absent-in-image
    guard (the real `--strict` build runs on the docs host, not the test
    image). **Do not** gate on repo-wide `--strict` (Phase 41/42: 17
    pre-existing broken-link warnings make repo-wide `--strict` unsatisfiable).
  - **Drop `test_falkor_index_present.py`** (nothing to assert under HHH-A);
    fold the index-decision anchor into `test_adr_amendment_sentinels.py`
    (assert ADR-0181 exists with `status: Accepted` + the routed-to-WSD
    clause). Note the drop explicitly in PHASE_49_CONFIRMED so the deviation
    from the PHASE_MAP-named file set is on record.

---

### PB-6 — Does the scenario need any new capability/DataState? *(scope guard)*

Probe: **No.** The harness composes `CapacityLayer(kl=kl)` +
`install_planning_v0` + `install_phase1_v0` + `install_orchestration_v0` +
`install_consolidate_capacities` + `install_text_capacities` + `L4Dispatcher`
+ `Orchestrator` + `FalkorDBLocalPersister` + `DreamDriver`. All shipped.
Net-new = test scaffolding + cookbook + ADR-0181 only. **Confirms "Net-new
code? No."** PICK: hold the line — any temptation to add a capacity/DataState
mid-impl is a PB-1b regression and must be re-surfaced, not absorbed.

---

### PB-7 — Gate shape for the live-Falkor scenario. *(process)*

The canonical gate runs `docker compose run --rm mindsos-test pytest tests/`
with `falkordb` healthy → the integration scenario runs live; sidecar-less
runs skip it. PICK: scenario test reuses the phase_32 skip-fixture idiom so
the cumulative gate stays green in both modes; the in-memory companion
(PB-2a) carries deterministic coverage when the integration test skips. Per
HANDOFF §9: rebuild `mindsos-test` after each push; `python3` for any host
smoke; squash-before-confirm; hand-write `PHASE_49_CONFIRMED.md` (no `mindsos`
CLI / no `gh` on the gate host); tag `phase-49-confirmed` at the confirm-
artifacts commit (release.yml requires the confirmation doc present at the tag).

---

## 4. Net effect on the Phase 49 row (deltas from the PHASE_MAP as written)

| PHASE_MAP says | Reality / pick | Delta |
|---|---|---|
| invoke `text.tokenize` | `text.space_split` (shipped) | rename |
| single chain tokenize→…→consolidate | two stitched slices share session+KL+persister (PB-1a) | re-framed; honest seam in cookbook |
| `indexes.py` or migration scripts (PB-HHH) | ADR-0181 strategy only; **no index code** (PB-HHH-A) | scope reduced; consumer-deferred |
| `test_falkor_index_present.py` | dropped; folded into ADR sentinel test (PB-5) | file-set deviation (recorded) |
| `mkdocs build --strict` in test | exists+nav guard; `--strict` on docs host only | matches Phase-41/42/48 reality |
| Net-new code? No | confirmed (PB-6) | none |

---

## 5. Version bump (S5) — exact 10-surface set (slot 49 > high-water 48)

1–8. Package `__version__` `0.0.0+phase48`→`+phase49`: **mindsos_admin,
mindsos_capacity, mindsos_cli, mindsos_core, mindsos_instances,
mindsos_intelligence, mindsos_knowledge, mindsos_server** (8).
9. `pyproject.toml` `version`.
10a. `mindsos_cli/manifest.toml` `version` **and** 10b. `phase = "48"`→`"49"`
(the manifest counts as the version+phase pair).
11. `docker-compose.yml` `image: mindsos:phase48-prod`→`phase49-prod`.
12. `docker-compose.yml` `image: mindsos:phase48-test`→`phase49-test`.
13. Export-slate assertions embedding the version string in
`tests/phase_30/test_phase_30_export_slate.py`,
`tests/phase_31/test_phase_31_export_slate.py`,
`tests/phase_34/test_phase_34_export_slate.py`.

(Same set the Phase-48 confirm doc enumerated as "10 surfaces.") **No new
top-level package → no new-package manifest-list / doctor-parity checklist.**

---

## 6. Test plan (S1/S2/S4)

- `tests/phase_49/integration_c.py` — `ScenarioState` + ~10 step helpers
  (bootstrap admin → login → KL-from-Falkor bootstrap → install text+v0+
  consolidate catalogs → L3 `find_pipeline`+invoke `text.space_split` →
  `run_lifecycle` trivial task → assert Episode+Memory+edge in Local →
  `FalkorDBLocalPersister.save`+`load` round-trip assert → dream driver →
  logout). ~120–180 LOC.
- `test_integration_c_scenario.py` — `@pytest.mark.integration` headline
  (live Falkor, skip-fixture) + in-memory chain companion (`KnowledgeLayer.
  bootstrap()`, deterministic).
- `test_cookbook_page_renders.py` — page exists + in nav (skip-if-mkdocs.yml-
  absent guard).
- `test_adr_amendment_sentinels.py` — chain-link from Phase 48 + assert
  ADR-0181 present (`status: Accepted`, WSD-routing clause).
- Pass criteria (PHASE_MAP): scenario deterministic; cookbook renders;
  index decision ratified (ADR, no code); cumulative regression green;
  `mkdocs build --strict` clean on docs host.

---

## 7. DECISIONS CHOSEN — approval gate

Collected for a single sign-off (operator gave no mid-stream feedback this
round). Each is the analysis pick; any can be reversed at authorization.

1. **PB-1a — two stitched slices share one live session + KL + persister.**
   Read-side L3 `text.space_split` invoke + write-side L4→L5 lifecycle over v0
   + consolidation + persister round-trip, co-resident, honest seam in the
   cookbook. *No product-code change.* **Rename `text.tokenize`→
   `text.space_split` throughout.**
   *Why:* honors "Net-new code? No" + "WSD replaces v0 atomically"; the v0
   lifecycle provably dispatches no real L3 capacity, so a true single chain
   would require rejected product surgery (PB-1b).

2. **PB-HHH-A — ratify Falkor index strategy in ADR-0181 + cookbook; ship
   zero index code; route physical creation to the WSD retrieval chat (first
   real query consumer).** Update `L5_FUTURE_WORK.md` L5-NEW-13 owner.
   *Why:* no indexed-query consumer exists at v1 (persister is whole-graph
   save/load); consumer discipline (the rule every prior phase applied) says
   defer absent-consumer surfaces; the decision still closes q2 with an ADR.

3. **PB-2a — live-Falkor `@pytest.mark.integration` headline scenario
   (skip-fixture) + an in-memory deterministic chain companion.**
   *Why:* exercises the headline Phase-44 persister round-trip; keeps chain
   coverage under `-m 'not integration'`; exact Integration A/B precedent.

4. **PB-3a — drive the dream driver synchronously; assert `DreamDirective`s
   (+ retry's `ReplanInjectionDirective`); identity `re_executor`.**
   *Why:* deterministic + CI-stable; real re-execution/ALS are WSD-gated; the
   background timer is a Phase-46 unit concern already covered.

5. **PB-4a — cookbook mirrors `text-realm.md`** (mixed CLI + Python-API; honest
   "does / does not"; `last_confirmed_phase: 49`; load-bearing test pointer;
   explicit notes on the v0 seam, the WSD gate, and the no-physical-index
   decision).

6. **PB-5a — test layout:** `integration_c.py` harness +
   `test_integration_c_scenario.py` (headline+companion) +
   `test_cookbook_page_renders.py` (exists+nav guard, not repo-wide
   `--strict`) + `test_adr_amendment_sentinels.py` (also anchors ADR-0181).
   **`test_falkor_index_present.py` dropped** (nothing to assert under HHH-A);
   deviation recorded in PHASE_49_CONFIRMED.

7. **PB-6 — composition only; no new capability/DataState.** Any mid-impl
   temptation to add one re-surfaces as a PB-1b regression.

8. **S5 — full 10-surface version bump 48→49** per §5 (slot 49 > high-water
   48). No new-package checklist.

9. **S6 — Phase 38 §4 doc closures: verify-and-note only** (#13 shipped P48,
   #14 absorbed P42, #15 dropped). Zero work.

10. **Process (PB-7 / HANDOFF §9):** branch `phase-49` off `phase-48-confirmed`;
    pair-execution (Cowork prepares content, Mac runs git, Linux gates via
    docker with `mindsos-test` rebuild + healthy `falkordb`); squash-merge to
    `main` before confirm; hand-write `PHASE_49_CONFIRMED.md` via heredoc; tag
    `phase-49-confirmed` at the confirm-artifacts commit. Leave the untracked
    Robot-Demo corpus + `demo_ui/ prototype_zero/ sim/ web/` alone; stage
    selectively.

**On approval:** open R1 (validate picks against any reversal), then cut
`phase-49` and begin impl in commit groups (harness → cookbook+ADR-0181 →
version bump → gate). Phase 49 is the LAST numbered phase; on confirm the
next chat is the downstream sequence (SKILL_ACQUISITION_PROCESS → WSD / FOL /
code-skill / adapter / L4-v2 / maintenance) per PHASE_MAP §6.

---

*R0 authored 2026-06-09.*

---

## 8. R1 + as-built record (authorized — impl prepared 2026-06-09)

Operator authorized ("proceed") with no mid-stream feedback. R1 found no
reversal of the §7 picks. Files prepared in the Cowork sandbox (git + the
docker gate run on Mac/Linux per pair-execution).

**As-built deviations from the PHASE_MAP row (all per §4 / §7):**

- `text.tokenize` → **`text.space_split`** applied throughout (the shipped
  capacity). The read-side invoke asserts
  `capacity:perception:text.space_split` + tokens `["the","cat","sat"]`.
- **`test_falkor_index_present.py` not authored** (PB-HHH-A ships zero index
  code; nothing to assert). The index decision is anchored by
  `test_adr_amendment_sentinels.py` against ADR-0181. Deviation recorded here
  + to be re-stated in PHASE_49_CONFIRMED.
- Scenario is **two stitched slices** sharing one session+KL (PB-1a); the
  cookbook's "Does NOT" section states the seam, the v0-placeholder lifecycle,
  the WSD gate, and the no-physical-index decision.

**Files (net-new unless noted):**

- `tests/phase_49/__init__.py`, `tests/phase_49/conftest.py` (skip + warm-up),
  `tests/phase_49/integration_c.py` (harness),
  `tests/phase_49/test_integration_c_scenario.py` (companion + integration),
  `tests/phase_49/test_cookbook_page_renders.py`,
  `tests/phase_49/test_adr_amendment_sentinels.py`.
- `docs/usage/cookbook/end-to-end.md` (new) + `mkdocs.yml` nav entry (edit).
- `docs/decisions/adr/0181-falkor-index-strategy-cross-sub-mm-queries.md`
  (new).
- `docs/future_work/L5_FUTURE_WORK.md` L5-NEW-13 owner update (edit).
- Version bump 48→49 (13 files: 8 package `__version__` + `pyproject.toml` +
  `mindsos_cli/manifest.toml` [`version` **and** `phase`] + the 3 export-slate
  tests) + `docker-compose.yml` (2 image tags).
- `confirmation_docs/PHASE_49_DESIGN_LOG.md` (this file).

**Sandbox self-verification (Python 3.10; `mindsos_server`/CLI paths excluded —
they need 3.11 `datetime.UTC` and run only in the docker gate):**

- `test_chain_inmemory` (read-side tokenize + lifecycle + Episode/Memory/edge +
  dream 2-of/3-of directives) — **passed**.
- `test_cookbook_page_renders` (2) + `test_adr_amendment_sentinels` (3) —
  **passed**.
- Export-slate `phase_30/31/34` (now assert `0.0.0+phase49`) — **passed**.
- `phase_49` full collection: 6 passed, 1 deselected (the integration test is
  marked + collected, skips without a sidecar).
- Regression: `phase_45` + `phase_46` (111) + `phase_47` + the `phase_48`
  consolidation/dream tests (33) — **passed**; no regression from the added
  files / version bump.
- `mkdocs build`: `end-to-end.md` + `text-realm.md` + ADR-0181 render; no
  errors. (`--strict` runs on the docs host per the ceremony; repo has 17
  pre-existing broken-link warnings unrelated to this phase.)

**NOT self-verifiable in sandbox (run at the Linux docker gate, 3.11 + live
Falkor):** `test_integration_c_scenario` (L0 CLI login + persister round-trip),
the CLI export-slate/doctor tests, and the full cumulative gate.

**Ship (pair-execution; operator runs):** branch `phase-49` off
`phase-48-confirmed`; commit the files above (stage selectively — never
`git add -A`; leave the untracked Robot-Demo corpus + `demo_ui/ prototype_zero/
sim/ web/` + the 4 pre-modified tracked docs alone); push WIP → Linux pull +
`docker compose build mindsos-test` + cumulative `pytest tests/` (Falkor
healthy) → if green, fast-forward `phase-49`, squash-merge to `main`,
hand-write `PHASE_49_CONFIRMED.md` via heredoc with the real gate numbers, tag
`phase-49-confirmed` at the confirm-artifacts commit. **Phase 49 is the LAST
numbered phase** — next chat is the downstream sequence (PHASE_MAP §6).

*R1 + as-built appended 2026-06-09.*

---

## 9. PB-RT — the episode-flush gap (R2 reanalysis finding; scope-changing)

**Surfaced during a post-impl skeptical reread of the persistence path — the
single material correction to §7.**

**Finding.** The Phase-49 scenario row lists "Falkor-backed persister flushes"
of the consolidated Episode. But the L0 node persister stores node `value` as a
**primitive**: `mindsos_core/cypher/builders.py::build_unwind_create_nodes`
emits `SET n.value = row.value` (docstring: *"value (any primitive)"*), and
ADR-0130's `_props_json` JSON-encodes only *metagraph* `.properties`, not node
values/props (`graph_repository.py` passes `n.value` + `_filter_user_props(...)`
raw). The L5 **Episode** node's `value` is a structured 6-field dict (Chat B
D-B47). FalkorDB stores properties as primitives/arrays only — so
`FalkorDBLocalPersister.save` of an episode-bearing Local **would error at the
gate**. Corroborated by the pre-existing **L0-25** (the Local persister
round-trip was never live-validated — Phase 44 used `InMemoryClient`).

**Why it would have failed the gate (not just locally).** The canonical CI
gate (`.github/workflows/phase-ci.yml` + `release.yml`) runs `docker compose
run --rm mindsos-test pytest tests/ -v` with the `falkordb` sidecar healthy
(`depends_on: service_healthy`) — **no `-m "not integration"`**. So
`@pytest.mark.integration` tests run live (Integration A/B do). My original
`test_integration_c_scenario` flushed the Episode to live Falkor → it would
have executed in CI and raised on `save()`. Caught pre-ship.

**Options.**
- **PB-RT-a (PICK) — descope the live Episode flush; document the gap; exercise
  the Phase-44 machinery via the proven path.** The integration test's live
  operations are restricted to ones Integration A/B already prove
  (`bootstrap_global_pair_from_falkordb` + `MetagraphRepository.persist` of the
  Global pair — the same native round-trip `FalkorDBLocalPersister` wraps). The
  Episode is asserted in the in-memory Local (the shipped reality). The gap is
  routed to **L0-26** + documented in the cookbook "Persisting episodes" note.
  *Why:* Integration C composes shipped pieces and **surfaces** cross-phase
  gaps — it must not silently smuggle in net-new L0 node-value serialization to
  paper over one. Keeps the gate green + honest.
- PB-RT-b — fix node-value persistence now (node-level `_props_json` encode/
  decode, extend ADR-0130 to nodes). *Reject:* net-new L0 code in an integration
  phase; the fix wants its own design (encode/decode symmetry, load-path
  reconstruction, migration) — a maintenance/v1.5 item, not Integration C.
- PB-RT-c — keep the flush, mark the test `xfail`. *Reject:* an `xfail` headline
  scenario misrepresents "the substrate works end-to-end"; the honest statement
  is "episodes are in-memory at v1," which PB-RT-a makes.

**As-built change (supersedes the §8 persister round-trip):** harness
`step_persist_round_trip` → **`step_live_persistence_machinery(client)`** (Global
bootstrap + persist; no episode flush). `test_integration_c_scenario` asserts
CLI login + live machinery + the in-memory chain. Cookbook Step 5 rewritten to
"Falkor persistence machinery (and the episode-flush gap)". New **L0-26** future
-work entry. The deterministic companion (`test_chain_inmemory`) is unchanged
and still self-verifies.

**Net:** Integration C's first-end-to-end exercise did its job — it surfaced a
real L0↔L5 seam (durable episode persistence) that no unit test caught. The
seam is **documented and routed, not fixed here**. This is the §7 pick-set's
only revision; all other picks stand.

*R2 reanalysis appended 2026-06-09. Awaiting the Mac/Linux ship ceremony.*
