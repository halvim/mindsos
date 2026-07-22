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
  placeholder check). A terminal-state acceptance battery replaced the weak reachability
  test — currently RED at the baseline (see #1); driving the gate redesign, not yet green.
- Demo on **real PLAID `Water_kettle_1805`** (data at `/home/sanmyaku/_sample`): finder
  composed the recognition segment; 18/19 steady windows → `cycle` (conf 1.000); the one
  anomalous window (start=5000, residual 3.35 vs ~2.1 baseline, `temp` 0.064 vs clean ~0.012)
  → **`request_reference [temporal]`** (conf 0.001). **Post-1b the attribution is now
  `[temporal]`, not `[spectral]`** — `spec` saturates ~0.995 on every window so the learned
  spectral gate (~0.997) correctly stays silent; discrimination is carried by the temporal
  axis, and the request is now **structure-driven** (temp ≫ learned threshold), not fired by
  a degenerate always-on gate. **`held_ambiguity` is currently UNREACHABLE** (the reachability
  test falsified my earlier "reachable-in-principle" claim): the temporal gate is fit to a clean
  residual that is a *smooth harmonic* (near-zero dispersion), so its `mean + 3σ` bar sits below
  even broadband noise → noise trips `[temporal]` → `request_reference`. This is a real gate
  MIScalibration (per §4A/P1 noise is the canonical `held_ambiguity` case). Being driven by the
  acceptance battery (#1).
- Re-run: gate `PYTHONPATH=.:projects/amii_study python -m pytest
  projects/amii_study/nilm_brain/tests -q`; demo `… scripts/cycle_demo.py --data
  /home/sanmyaku/_sample --record Water_kettle`.

## Open items / next phase (pick one)
1. **✔ DONE (this chat) — Axis degeneracy fixed (1a + 1b).**
   - **1a** — `structuredness_thresholds` re-homed out of `build_given` into the Solver learned
     slot (`self.thresholds` ← `decision.default_thresholds()`); fixes the §7 doc-divergence.
   - **1b** — `fit_calibrate` now seed-fits the gates (`decision.fit_thresholds`, mean + `k`·σ,
     `k`=3.0 an L4 fit arg, **not** a DataState). Result on real PLAID: request_reference is now
     **structure-driven and correctly `[temporal]`** (was a degenerate `[spectral]`). The axis
     fix is done; the separate `held_ambiguity` gate problem it exposed is tracked below.
   - **1b-test → acceptance battery (IN PROGRESS, RED).** The weak `test_held_ambiguity_reachable`
     was replaced by `test_terminal_battery`: labeled synthetic classes (clean→`cycle`,
     notch→`request_reference`, noise@SNR→`held_ambiguity`) with a confusion-matrix criterion —
     the two forbidden confusions are a MISS (structured→not-request) and a FALSE ALARM
     (clean/noise→request). Gate fit on the clean seed only (held-out battery). Expected to fail
     at baseline (noise→request, per the miscalibration above); it prints the matrix. **Design
     rule:** if a threshold placement can pass → calibration fix (noise-floor gate); if no
     placement separates noise from structure → the *feature* is inadequate → redesign the
     structuredness metric. `held_ambiguity` is not load-bearing for the H4/H5 claims, so minimal
     bar first.
   - **Watch item:** `required_confidence` still literal in `build_given` (§7 = L5 task input) —
     re-home next, same species as the 1a fix.
2. **Matcher (NEXT — the #2 prerequisite).** Recognition currently fits only the *given*
   `cycle_reference`; the verdict consults `known_references` by *name*, never fitting them. So
   doctrine §5 ("recognition is matching against known references") is half-built and #2's
   "teach → recognition" cannot close. Add a step that fits each known reference to the residual
   and routes by best-explanation. Design pending approval.
3. **Teach a reference (the leaf-learning).** Inspect what the `Water_kettle` start=5000
   structure actually is; add it to `known_references` (and persist to L2). That *adding*
   is the leaf-learning; request_reference for that pattern then becomes a confident
   recognition.
4. **Wire the secondary pipelines / rungs** — `power` needs a current-signal bind; each
   rung needs its own reference + §4A template instance.
5. **Durable L2 (v1)** — persist learned `calibrate` params + taught references as
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
