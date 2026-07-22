# nilm_brain — STATE (handoff for future chats)

**Read this first.** It records what the brain *is*, what was **decided**, what was
**validated**, and what's **open**. It does not repeat the design — that's in
`README.md` (layout + discipline), `docs/LEAF_LEARNING_NILM_APPLICATION.md` (the
DataState/capacity/pipeline registry the brain implements), and
`docs/LEAF_LEARNING_PROCESS.md` (the domain-neutral leaf-learning doctrine).

## Where it lives
- Branch **`nilm_brain`** (off `chore/amii-study`, verified API-compatible).
- Worktrees: Mac `…/Projects/nilm_brain`, Linux `/home/sanmyaku/nilm_brain`.
- Package: `projects/amii_study/nilm_brain/` (package imports as `nilm_brain`; the
  DataState **realm stays `nilm`**, so all IRIs are `datastate:nilm.*`).

## What it is
A cycle-recognition brain built as a **consumer of MindsOS** (never edits `mindsos_*`).
Template = `MindsOS-bongard/projects/bongard_demo`. Anti-pattern guide = the arc
audits: `arc1-brain/docs/BRAIN_MINDSOS_CONFLICTS.md` (Part D catalogue) and
`Arc3/ARC3_STATE_AND_MINDSOS_CONFLICTS.md`. The whole point is to **not** be a
"44 caps registered, 3 live, echoing Python" brain.

## Decisions locked this chat (do not re-litigate without cause)
1. **Shipped-level v0.** Recognition is a finder-composed **segment** run by core's
   `execute_pipeline`; the window fan-out + repeat-until-converged refinement are **L4
   Python** (arc A4/C4). `find(raw_data → cycle_verdict)` end-to-end is *correctly* NOT
   FOUND across the fan-out. **Rung 5** (mindsos's own orchestrator driving the brain) is
   **blocked by core WSD/phase-1 placeholders** — same as arc1/arc3 — and is **not faked**.
2. **One `cycle_verdict` DataState; its value carries the terminal**
   (`cycle` / `held_ambiguity` / `request_reference`). Distinct terminal DataStates were
   **rejected**: a capacity has a fixed output signature, so a branching terminal type
   isn't expressible (arc3 C8). L4 routes on `cycle_verdict["state"]`.
3. **`calibrate` is learned** — a `Params` dict fit off a **clean-cycle seed** (bongard's
   definitional-seed pattern). This is what resolves the single-pass "everything is
   request_reference" collapse. Durable L2 persistence of the params is **v1**.
4. **Bodies own their numpy** (no `probe.py` oracle they echo — arc D4). Honest
   PRODUCES/CONSUMES edges. Every `invoke` checks `success` (arc C7). Thresholds /
   references / required_confidence are **DataState/L2 inputs, never literals** (arc D2 =
   the "no hardcoded values" rule).
5. **4 hyperparameters promoted to DataStates** beyond doc §7 so nothing is a literal in a
   body: `freq_search_frac`, `n_grid`, `max_loop_iters`, `window_start`.
6. Two secondary pipelines (`power`, `harmonic_amplitudes`) and the rungs (`onset`,
   `harmonics_present`, `load_type`, `appliance`) are **registered but not composed** — the
   rungs need their own L2 references (§8), which don't exist yet. Flagged, not faked.
7. **`structuredness_thresholds` is L2-learned, not a domain given.** It travels the
   `calibrate_params` channel — a Solver-held slot (`self.thresholds`, default
   `{spectral:0.5, temporal:0.5}` from `decision.default_thresholds()`), **not** `build_given`.
   v0 code wrongly minted it in `build_given` (a doc §7 divergence); re-homing it is **step 1a**
   of open item #1. Seed-fitting the value is **step 1b**.

## Validated (green)
- Gate `tests/test_gate.py` — **6 passed** on Linux (F1 finder-composes, F2
  executes-to-real-values, seeded-clean-cycle→`cycle`, disturbance<clean, C7 envelope,
  placeholder check).
- Demo on **real PLAID `Water_kettle`**: finder composed a **10-step** pipeline; 18/19
  steady windows → `cycle` (conf 1.000); the one anomalous window (start=5000, residual
  3.35 vs ~2.1 baseline) → **`request_reference [spectral]`** (conf 0.001). The thesis
  end-to-end: steady cycles recognized, genuine outlier honestly flagged as "no reference
  for this."
- Re-run: gate `PYTHONPATH=.:projects/amii_study python -m pytest
  projects/amii_study/nilm_brain/tests -q`; demo `… scripts/cycle_demo.py --data <PLAID
  dir> --record Water_kettle`.

## Open items / next phase (pick one)
1. **Axis degeneracy (highest-value fix) — split 1a/1b.**
   - **1a — re-home the threshold source (implemented this chat; awaiting Linux gate).**
     `structuredness_thresholds` moved out of `build_given` into a Solver learned slot
     (`self.thresholds` ← `decision.default_thresholds()`), threaded into the segment like
     `calibrate_params`. **Behavioral no-op** — fixes the §7 doc-divergence, not behavior yet.
   - **1b — fit the thresholds off the clean-cycle seed (implemented this chat; awaiting Linux
     gate + demo).** `fit_calibrate` now also fits `structuredness_thresholds` = seed mean +
     `k`·σ per axis (`decision.fit_thresholds`), so 'structured' means *more concentrated than a
     healthy cycle*, not 'above 0.5'. `k` is an **L4 fit hyperparameter** on `fit_calibrate`
     (default 3.0), **not** a DataState — no capacity consumes it, so a DataState would be an
     orphan node. **Gate stays 6/6** (1b is gate-neutral: clean cycles still score ≥ req →
     `cycle` before any threshold check); its effect shows only in the **demo**. Caveat:
     `spectral_concentration` saturates ~0.995 on voltage (harmonics everywhere), so the spectral
     gate may still never fire — discrimination is expected to fall on the **temporal** axis.
     Whether `held_ambiguity` actually becomes reachable is the empirical result the demo reports.
   - **1b-test — `held_ambiguity` reachability gate test: DEFERRED.** A robust fixture depends on
     the real seed-fit concentration numbers (guessing them risks a red gate + breaks the
     contamination rule). Author it against the demo output, next.
2. **Teach a reference (the leaf-learning).** Inspect what the `Water_kettle` start=5000
   structure actually is; add it to `known_references` (and persist to L2). That *adding*
   is the leaf-learning; request_reference for that pattern then becomes a confident
   recognition.
3. **Wire the secondary pipelines / rungs** — `power` needs a current-signal bind; each
   rung needs its own reference + §4A template instance.
4. **Durable L2 (v1)** — persist learned `calibrate` params + taught references as
   `learned-parameters` nodes (arc3 B6: L2 is the layer that works); `boot_brain` +
   FalkorDBLocalPersister.

## Working protocol (unchanged, enforced)
Explain in plain English → user approves → then run. Be **concise and skeptical** (a
critical design reviewer, not a validator). **Never edit `mindsos_*`.** **No git from the
Cowork sandbox** — the Mac commits/pushes with explicit paths (never `git add -A`), Linux
pulls/validates; read-only git from the sandbox is fine. **No hardcoded values** — every
constant is a DataState input. **Do not document numpy probe/test *results*** in any
persisted file (contamination rule): the brain's capacities are the source of truth, not
throwaway numpy.
