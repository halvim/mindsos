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
- Gate `tests/test_gate.py` — **8 passed** on Linux (F1/F2, seeded-clean→`cycle`,
  disturbance<clean, C7, placeholder, `test_terminal_battery`, `test_teach_then_recognize`).
  The battery separates all three base terminals on labeled synthetic data (clean→`cycle`,
  notch→`request_reference`, noise→`held_ambiguity`); the teach→recognize test closes the
  leaf-learning loop (teach notch → held-out notch `recognized`, sag/noise not matched, clean
  untouched) — with recognition position-specific for now (see #2).
- Demo on **real PLAID `Water_kettle_1805`** (data at `/home/sanmyaku/_sample`): finder
  composed the recognition segment; 18/19 steady windows → `cycle` (conf 1.000); the one
  anomalous window (start=5000, residual 3.35 vs ~2.1 baseline, `temp` 0.064 vs clean ~0.012)
  → **`request_reference [temporal]`** (conf 0.001). **Post-1b the attribution is now
  `[temporal]`, not `[spectral]`** — `spec` saturates ~0.995 on every window so the learned
  spectral gate (~0.997) correctly stays silent; discrimination is carried by the temporal
  axis, and the request is now **structure-driven** (temp ≫ learned threshold), not fired by
  a degenerate always-on gate. **`held_ambiguity` is now reachable and correctly bounded** — the
  temporal gate is `max(clean floor, white-noise floor)` (0.021), so noise (temp ≤0.018) →
  `held_ambiguity` and only genuine localized structure (temp 0.065) → `request_reference`.
- Re-run: gate `PYTHONPATH=.:projects/amii_study python -m pytest
  projects/amii_study/nilm_brain/tests -q`; demo `… scripts/cycle_demo.py --data
  /home/sanmyaku/_sample --record Water_kettle`.

## Open items / next phase (pick one)
1. **✔ DONE (this chat) — Axis degeneracy fixed (1a + 1b).**
   - **1a** — `structuredness_thresholds` re-homed out of `build_given` into the Solver learned
     slot (`self.thresholds` ← `decision.default_thresholds()`); fixes the §7 doc-divergence.
   - **1b** — `fit_calibrate` now seed-fits the gates (`decision.fit_thresholds`, `k`=3.0 an L4
     fit arg, **not** a DataState). Result on real PLAID: request_reference is now
     **structure-driven and correctly `[temporal]`** (was a degenerate `[spectral]`).
   - **1c — noise-surrogate gate (DONE, battery green).** The acceptance battery
     (`test_terminal_battery`, held-out labeled synthetic) exposed that a clean-only gate is
     `~0` on the temporal axis (a steady cycle is temporally flat) so noise tripped it → 12/12
     `request_reference`. Fix: each gate = `max(clean floor, noise floor)`, where the noise floor
     is the concentration a **white-noise surrogate** produces, measured by running the real
     `fft`/`spectral_flatness`/`temporal_flatness` caps on it (`Solver._noise_floor`, no
     duplicated numpy). Temporal gate 0.0004→0.021; noise→`held_ambiguity`, structure→`request`,
     clean→no false alarm. The battery *diagnosed* this as a threshold (not feature) problem:
     noise temp ≤0.018 vs structure 0.065 separated cleanly.
   - **Follow-up (NOT done) — `calibrate` over-sensitivity.** 4/12 clean windows fall to
     `held_ambiguity` (conf min 0.144) because `seed_std` is tiny → `energy_score=exp(-½z²)` is
     razor-sharp, so normal residual jitter reads as low confidence. Harmless on real PLAID (conf
     1.000) but under-confident on synthetic clean. Fix later (floor on `seed_std`, or a gentler
     curve). Also still open: `required_confidence` literal in `build_given` (§7 = L5 input).
   - **Watch item:** `required_confidence` still literal in `build_given` (§7 = L5 task input) —
     re-home next, same species as the 1a fix.
2. **✔ DONE (this chat) — Matcher + teach (the leaf-learning loop closes).** The verdict was
   refactored (structured→`request_reference`; the fake name-check dropped — PB3); `recognized` is
   a 4th terminal emitted by an **L4 matcher** (`Solver._match_verdict`/`_match_references`).
   `fit_reference`/`synthesize` gained `form:"template"` (guarded; sinusoid path untouched).
   `Solver.teach(name, record)` stores the most-structured flagged residual as one additive
   template reference. Matcher: on a `request_reference` window, fit each taught template to the
   residual, subtract, and if the leftover drops below **both** gates → `recognized[name]`.
   `test_teach_then_recognize` green: teach notch_A → a **held-out** notch_B window is
   `recognized[notch]`, sag+noise are **not** matched (0 false matches), clean untouched
   (no-forgetting). Gate **8 passed**.
   - **KNOWN LIMITATION — recognition is position-specific.** The template is NOT shift-invariant:
     only the notch_B window whose notch aligns with the taught offset is recognized (1/≈3);
     others fall back to `request`/`held`. The brain recognizes "notch-at-this-offset," not
     "notch." Test-exposed template rigidity → next matcher improvement = cross-correlate for best
     lag before the scale-fit (or a parametric shape). Not required for the mechanism claim.
3. **Teach a reference on real data (transfer check).** Inspect what the `Water_kettle` start=5000
   structure actually is; teach it and confirm request→recognize on real PLAID (the synthetic loop
   is proven; the real-data transfer is not yet run). That *adding*
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
