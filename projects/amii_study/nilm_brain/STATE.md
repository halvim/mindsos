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
1. **Axis degeneracy (highest-value fix).** `spectral_concentration` **saturates ~0.995**
   on every window (real voltage always has harmonics), so discrimination comes entirely
   from `calibrate` confidence, and **`held_ambiguity` is currently unreachable** (any
   low-confidence window trips the always-true spectral gate → `request_reference`). Fix:
   calibrate `structuredness_thresholds` to the saturated range, or normalize
   `spectral_concentration`. This is a threshold/normalization issue, not a plumbing bug.
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
