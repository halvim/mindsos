# SubMind Slice 3 (Reflex path) — design handoff

**Status:** Design settled + verified against `main` (`af329eb`); **not built**. Two owner
decisions still OPEN (§3). Supersedes the per-chat design discussion (that chat is archived).
**Owner from now on:** the main CORE lane.
**Read with:** `SUBMIND_DESIGN_LOG.md` §10 (Reflex WHAT — settled) + §18 (closed ledger) +
§19.1 (Slice-3 row) + §20 (Slice-2 resource model this builds on); ADR-0188 Decision 3;
ADR-0189 §2/§3. `STATE.json` → `pending_designs[subminds-slice-3]`.

The WHAT is settled in §10 / ADR-0188 D3. This doc is the **HOW**: the implementation
decisions + the surfaces + the two things only the owner can decide.

---

## §1 Scope (unchanged from STATE)

A declared non-reconcilable predicate at endowment fires a pre-wired **single fast capacity**
that **bypasses the queue + L4 deliberation** and notifies L4 after; **forcible resource
seizure = supersede, not negotiate** (arbiter override for actuators / drain for compute) on
the shared `ResourceHold` (add a `seize` hook beside `cancel`; reuse the Slice-2 ledger, do
not fork it); the Reflex stays **dumb** (pure reallocation — any solving is a downstream
CRITICAL deliberated task) + a cognitive-Reflex **hard floor** that never starves monitoring +
the same refractory/hysteresis as Signals. **Out of scope:** Slice 4 (Local scope / teaching /
de-endowment / tuning).

## §2 Settled HOW-decisions

1. **Reflex eval is a new sibling method `SubMind.evaluate_reflex(reading)`** — NOT folded into
   the frozen `tick()`. Parallel per-condition ARMED/FIRED state, independent of the Signal
   state machine; re-arm on `reflex_reset_margin`. Predicates must be cheap (run inline on the
   single scheduler thread).
2. **`ReflexCondition` (0..N) on `SubMindDefinition`** (mirrors the unconsumed-runtime-field
   pattern): `predicate`, `capacity`, `resources`, `watch_datastate`, `reset_margin`,
   `drain_compute`, optional `followup_goal`. New `ReflexFiring` output.
3. **Seize is callback-only; it does NOT mutate the ledger.** `ResourceHold.seize` (new,
   mirrors `cancel`) + `ResourceLedger.seize(resources)` collects conflicts under lock, invokes
   `seize()` outside the lock, and **leaves the holder map untouched** (the displaced task keeps
   its logical hold, per ADR-0188 §10). Consequence: no orphaned-entry / no `restore` hook
   needed (§3 is separate).
4. **Compute-drain is an executor concern, not the ledger.** The ledger is exclusive-resources-
   only ("not shared schedulable compute"). Add additive `executor.drain(exclude_request_id)`
   (cooperative-cancel running non-reflex tasks). Actuator supersede → `ledger.seize`; compute →
   `executor.drain`.
5. **Reflex runs on a dedicated reserved thread (the hard floor)** — a `ReflexRunner`, one
   reserved thread outside the worker pool AND outside the scheduler thread. Detection (predicate
   eval) + `seize`/`drain` run **inline** on the detecting thread (instant supersede); only the
   fast-capacity body offloads to the runner, so monitoring is never blocked. Pool size = Slice-4
   tuning.
6. **Net-new reflex feed on `SubMindRegistry`**, not a repurpose of `MonitorSubscriptionRegistry`
   (which maps DataState→L3 Monitor IRIs with an orchestrator-thread-only invariant — confirmed
   passive; §17's "repurpose" wording is aspirational per §19.2). A `Dict[ds_iri → [SubMind]]` +
   `notify_datastate_changed(ds_iri, value)`. Live detection in core = scheduler tick (bounded
   latency); the instant write-hook ships **real-but-unconsumed** (the robot demo wires it).
7. **Followup = optional declared `followup_goal`, default none**, dispatched as a **normal
   CRITICAL executor task** (find_pipeline + execute_pipeline) *after* the fast capacity, in the
   runner's completion callback — NOT the Slice-2 resolver goal, NOT routed through the Signal
   arbiter.
8. **`needs_input` (ADR-0196) on the reflex fast capacity → non-completion + notify** (flag a
   probable misdeclared reflex). A reflex has no human in the loop; only the deliberated followup
   may surface `needs_input` normally.
9. **Notify L4 after** = a registered `on_reflex_fired(firing)` callback + the optional followup
   dispatch.

## §3 OPEN — owner must decide before build (do NOT guess)

- **D1 — does the emergency fast capacity write an audit trail into `capacity_mm`?** Every
  deliberated run now grounds a per-run graph into the MM (L5 capacity_mm persist). The followup
  will ground like any task. The fast capacity is the question: **(A)** ground fully (full audit,
  MM-write latency in the emergency path); **(B)** run dark (fastest; only the "reflex fired"
  notify records it); **(C)** lightweight fired-event marker (fast + a trace, no full grounding).
  *Design lean: C.* Tradeoff is auditability-stance vs emergency latency.
- **D2 — inject the real `MentalModel` into the ReflexController, mandatorily?** The arbiter now
  refuses a `None` mm to prevent silent grounding-drop. If D1 ≠ B, the controller grounds the
  followup and needs the MM. *Lean: A — mandatory, mirror the arbiter.* (If D1 = B and no
  grounding at all, mm becomes unnecessary → this is moot.)

## §4 Drift verified vs `main` (af329eb)

- `ResourceHold` frozen, has `cancel`, docstring already reserves the `seize` hook — fits.
  **Rename:** `ResourceHold.task_id` → **`request_id`** (and executor `_Entry`); use the new name.
- `SubMindArbiter.__init__` **requires `mm`** (raises on None) — precedent for D2.
- `execute_pipeline(mm=, pipeline_run_ref=)` grounds a per-run DAG; `mm=None` = byte-identical
  old behavior; with `mm`, `pipeline_run_ref` is **mandatory** (fresh `pipelinerun:` IRI — mint
  one per reflex dispatch to avoid the replan collision the code guards).
- `L4Dispatcher.dispatch` gives MM read access only when the declaration sets `reads_mm`; it does
  **not** ground (grounding is `execute_pipeline`-only). New read handle = read-only `MMResolver`.
- `submind*.py`, `resources.py`, `executor.py`, `monitor_subscription.py` otherwise match the
  design; `needs_input` field is live on `execute_pipeline` / `InvocationResult`.

## §5 Task list (build)

1. `resources.py` — `seize` on `ResourceHold`; `ResourceLedger.seize(resources)` (callback-only,
   no map mutation).
2. `executor.py` — thread `seize` through `submit`/`_Entry`→`ledger.acquire`; add `drain(...)`.
3. `submind.py` — `ReflexCondition` + `ReflexFiring`; `reflex_conditions` field; per-condition
   reflex state machine + `evaluate_reflex(reading)`. `tick()` untouched.
4. `reflex_runner.py` (new) — reserved single-thread runner (the floor).
5. `reflex_controller.py` (new) — inline seize + drain → offload fast-capacity dispatch to the
   runner → `on_reflex_fired` notify + optional CRITICAL followup; MM-grounding per D1/D2.
6. `submind_registry.py` — `_on_due` also calls `evaluate_reflex`; ds→subminds feed +
   `notify_datastate_changed`; wire controller (optional, mirror the arbiter wiring).
7. `intelligence_layer.py` — build runner + controller (thread `self._mm` per D2); wire into
   registry; expose `notify_datastate_changed` + `on_reflex_fired` seams.
8. `__init__.py` — export the new public types.
9. `tests/feat_subminds/` (+~6) — reflex state/refractory, `ledger.seize`, `executor.drain`,
   controller seize+dispatch+notify, runner-floor, write-hook feed, `needs_input` guard.
10. Docs — ADR-0188 amendment trail (seize shipped; ledger/executor split; needs_input guard) +
    `SUBMIND_DESIGN_LOG.md` new §21 + §19.1 Slice-3 row; update STATE pending→recent.
11. Verify — **no role-graph change → parity sentinels untouched** (confirm against the current
    baseline, not 4090); layer-isolation green; sandbox Py3.10 dev-check, then Linux Py3.11
    authoritative gate `--build`, tag `feat-subminds-s3-confirmed`.

## §6 Landmines / ops

- **Own worktree off `main`.** Open `feat/subminds-s3` in its own worktree; do not build into an
  unrelated lane's tree.
- Pure L4 — **no role-set/closed-set change**, so the phase_12/13/14/34/39/50 +
  `mindsos_admin._GLOBAL_ROLE_ORDER` sentinels stay untouched (re-confirm).
- Pair-execution: Cowork builds; Mac commits/pushes/tags; Linux gates (`--build`, authoritative;
  sandbox is Py3.10 — server/CLI suites are Linux-only).
- No new ADR needed — ADR-0188 Decision 3 already covers the Reflex; amend its trail on ship.
