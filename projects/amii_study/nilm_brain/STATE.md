# nilm_brain — STATE (handoff for future chats)

**Read this first.** It records what the brain *is*, what was **decided**, what was
**validated**, and what's **open**. It does not repeat the design — that's in
`README.md` (layout + discipline), `docs/LEAF_LEARNING_NILM_APPLICATION.md` (the
DataState/capacity/pipeline registry the brain implements), and
`docs/LEAF_LEARNING_PROCESS.md` (the domain-neutral leaf-learning doctrine).

**Locked framing (this chat): recognition is mindsos; diagnosis was the operator (an LLM)
standing in for the unbuilt L4 loop.** The brain's *recognition* (raw→verdict) is capacities/
pipelines; the *diagnosis* (why recognition fails, what to change) was NOT in the architecture.
The recorded reasoning + the recognition/diagnosis line + the transfer spec live in
`docs/DIAGNOSTIC_INTELLIGENCE.md` — read it to understand what this project is actually proving.

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
8. **Appliance recognition built as mindsos (#3 done).** Its own path **parallel to the cycle
   segment**: binds BOTH channels **un-normalized** (keeps power factor + absolute current, which
   the normalized cycle path drops). Signature = **union + turn-on onset** (`[pf, crest, log_irms,
   THD, harmonic ratios]` (+) `[inrush_ratio, onset_frac]`), the cross-instance-validated feature.
   Layering: **score = `signature_distance` capacity**; **match = L4 k-NN** over the taught library
   (variable-size fan-out = iteration, honest — `find(window→appliance_verdict)` correctly NOT
   FOUND); **decision = `recognize` capacity** emitting `appliance_verdict` (`recognized[name]` |
   `request_reference`). Cutoff learned **negative-aware + instance-aware** (`within` = nearest
   same-class *different-instance*, `between` = nearest different-class; never from positives blind).
   Teach = **per-window exemplars, additive** (no forgetting). Signature extraction is a real
   **finder-composed segment** (`power_features`→`current_harmonics`→`steady_signature`; F1/F2);
   `onset_features`/`assemble_signature` are record-level L4. Library + norm + cutoff are **in-memory
   on the Solver** (durable L2 = next slice, STATE #5 species).

## Validated (green)
- **Current channel operational (#3, `scripts/appliance_demo.py`).** The recognition pipeline
  runs channel-agnostically on current (`recognize(..., channel="current")`, amplitude-normalized;
  gates seeded on a **synthetic pure-sinusoid current** — the honest zero-distortion baseline, as
  no real appliance is distortion-free; a real resistive seed pushed the spectral gate to 1.57 >
  1.0, dead). All six appliances → `request_reference`; teaching an appliance rejects the other
  five with **zero false matches**.
  The **time-domain residual template MEMORIZES** (`match_leftovers`: taught window leftover 0.000,
  every other Laptop window ~0.8–0.99 → template explains nothing; shift-invariance inert — a single
  lag can't align a mixed periodic+localized residual). Wrong signature.
  **SPECTRAL signature WORKS (tested, kept) — the fix.** `harmonic_profile` cap (per-order harmonic
  magnitudes, phase-invariant) + `teach_spectral` (mean profile over the appliance's windows) +
  `profile_similarities` (cosine sim). Result on real PLAID: teach `Laptop` → **all 16 Laptop
  windows cos-sim 0.994–0.998 to the profile (generalizes)**, and every other appliance's best
  window ≤ 0.957 (CFL 0.922 / fridge 0.887 / hairdryer 0.930 / microwave 0.957 / kettle 0.942) →
  **separable at a cutoff ~0.98**, margin ≈0.04. Caveats: modest margin, switching loads somewhat
  confusable, cutoff must be **learned** (not hardcoded). NEXT SESSION: wire the spectral matcher
  into a `recognized` verdict with a learned cutoff (replace/augment `form:"template"` for
  appliances); the time-domain template stays for localized voltage disturbances.
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
- **Appliance recognition (#3) — gate + real-PLAID brain demo green.** Gate **9 passed** incl.
  `test_appliance_teach_recognize`: the finder composes the signature segment (F1), it executes to
  real values (F2), teach→fit→recognize round-trips, and a **novel appliance is rejected**
  (`request_reference`, not mis-recognized). Real-PLAID demo (`scripts/appliance_recognize_demo.py`,
  the BRAIN's `recognize_appliance` over `_sample_expanded`, leave-out split) recognizes held-out
  real records in the cross-instance ballpark; Fridge/Microwave/kettle strongest, Laptop↔Fridge the
  weakest pair, kettle optimistic (PLAID has only 10 kettle captures, one house). The *feature set*
  was chosen by a bake-off (`scripts/signature_bakeoff.py`) and confirmed cross-instance by
  `scripts/classify_eval.py` (leave-one-instance-out k-NN over `_plaid_full/_sample_expanded`, built
  by `scripts/pull_instances.py`) — those two are **operator/L4 diagnostics (standalone numpy, NOT
  the brain)**; the demo is the brain.

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
3. **✔ DONE (this chat) — Appliance recognition is mindsos end-to-end.** See decision #8 for the
   design. Path: parse → bind current+voltage (raw) → per window run the **composed signature
   segment** (`power_features`+`current_harmonics`→`steady_signature`) + record-level `onset_features`
   → `assemble_signature` → L4 k-NN over the taught library (`signature_distance` cap) → `recognize`
   cap → `appliance_verdict`. `Solver.teach_appliance`/`fit_appliance`/`recognize_appliance`. Gate
   `test_appliance_teach_recognize` green (9 passed); real-PLAID brain demo in ballpark (Validated).
   - **How the signature was chosen (the long way, honestly):** the residual-harmonic profile from
     the earlier plan only separated **Laptop** (n=1 6×6 matrix — a tight-class-biased centroid test
     that MISLED; e.g. predicted a kettle↔hairdryer confusion that real data did not show). Fixed by
     (a) **more data** — `pull_instances.py` builds `_sample_expanded` from `_plaid_full`; (b) a
     **feature bake-off** (`signature_bakeoff.py`, candidates A–I) whose n=1 "winners" (transient,
     shape+power) were **one-sample artifacts** that collapsed per-window; (c) a **cross-instance
     classifier** (`classify_eval.py`, leave-one-instance-out k-NN) → **union+onset ~88%**. Lesson
     (the DIAGNOSTIC method, §2): **do not tune a signature on n=1**; a centroid/argmax test
     is biased toward tight classes; only leave-one-instance-out is trustworthy.
   - **Weakest pair = Laptop↔Fridge** (both can look motor-ish across the split); onset is what
     separates the motor/resistive loads. **Kettle** is single-house in PLAID (10 captures) — its
     score is optimistic; a genuine second kettle instance does not exist in the dataset.
   - **Superseded:** the current-channel spectral profile / `teach_spectral` / `profile_similarities`
     / 6×6 matrix (`appliance_demo.py`) were the *exploration*, now replaced by the union+onset
     signature. `harmonic_profile` cap stays registered (harmless). Resistive-vs-resistive is now
     handled by keeping power/RMS in the signature (the old normalization follow-up — resolved).
4. **Wire the secondary pipelines / rungs** — each rung needs its own reference + §4A template
   instance. (`power`/`multiply` now references the generic `signal`; rewire for P=V·I in v1.)
5. **Durable L2 (v1) — PARTLY DONE.** ✔ **Pipelines persisted.** `repl.py` boots nilm as a
   resident mindsos brain (core `boot_brain` + `BrainREPL`/`loop`), installs L3, and persists the
   two composed segments as **learned pipelines** (ADR-0203: `learn_pipeline`, `immutable_successor`,
   value = full `Pipeline.to_dict()` incl. `edges`; persist-once guard so re-boot doesn't churn
   `taught_seq`). `mindsos brain` → `pl` lists `cycle_recognition` + `appliance_signature`;
   `--durable` (`stack.save()` → FalkorDBLocalPersister) boots knowing them. Verified: both listed,
   no round-trip rejection.
   **✔ BUILT + VALIDATED end-to-end (this chat).** The taught appliance library +
     `signature_norm` + `match_cutoff` now persist as **learned-parameters** (one bundled
     `LearnedParameter` node in the Local `learned-parameters` role, **append-only / latest-wins**),
     NOT as learned pipelines. New `nilm_brain/persistence.py`
     (`persist_appliance_state` / `load_appliance_state` / `apply_appliance_state`); `repl.py`
     reloads it at boot. Core ships **no `learn_parameter` writer**, so nilm writes/reads the role
     itself (consumer-side, mirrors `learn_pipeline`) — **CR out** for a core helper. A non-finite
     (accept-all) cutoff is **refused**; boot's reactivation walk **skips** nilm's nodes (no
     `reactivation_key`). Teach+persist flow = `scripts/teach_appliances.py` (there is no interactive
     `teach` verb). **Flag convention fixed:** `repl.py` is now **durable by default / `--ephemeral`
     opt-out**, matching core's `mindsos brain` (was an inverted `--durable`). Tests:
     `tests/test_durable_appliances.py` (4, gate-level, no Falkor) +
     `tests/test_durable_appliances_falkor.py` (@integration, skips w/o Falkor).
     **R2 reconcile (post main-merge 0021058):** the merge pulled R2 core (`execute_pipeline`/`invoke` `task_id`->`request_id`) but R2's rename ran on main and skipped `projects/amii_study/nilm_brain/` — `control.py` (2) + `dispatch.py` (3) call-sites were re-homed to `request_id` (the ONLY nilm consumer breakage; grep-clean). viz_spec survived the merge, so `repl.py` still boots.
   **VALIDATED (Linux):** gate **13 passed / 1 skipped** (Falkor test skips w/o sidecar);
     live round-trip PROVEN — `teach_appliances.py` taught 6 PLAID classes (288 exemplars,
     finite neg-aware cutoff), persisted seq=1 to Falkor; a fresh `--durable` boot reported
     **"288 appliance exemplar(s) loaded"**. Host note: compose does NOT publish Falkor's port —
     run a standalone `-p 6379:6379` FalkorDB for host-run teach/repl. Superseded next step:
     `teach_appliances.py --data /home/sanmyaku/_plaid_full/_sample_expanded` →
     `python -m nilm_brain.repl` should report the loaded exemplars.
6. **`fit_appliance` is O(n²)** in library exemplars (pairwise `signature_distance` for the
   negative-aware cutoff). Fine for demo-scale; an efficiency (not correctness) item before a large
   library — e.g. sample pairs, or a spatial index. Flagged, not faked.

## Cross-chat context (this session)
- **L4 doctrine (corrected, locked).** L4 = **dispatch only** (`L4Dispatcher` / `run_lifecycle`);
  NO capacities live in L4. ALL computation — incl. orchestration/eval — is L3 capabilities:
  fan-out = planning `decompose`+`aggregate_outputs`, teach = consolidate, eval = phase_6 verify.
  nilm's L4 Python loops (window fan-out, k-NN vote, teach) are an **interim scaffold**, to move
  onto those caps as they ship. The generic fan-out/aggregate are **Global builtins**
  (`install_brain_builtins` → planning_v0/orchestration_v0), being made real by the
  `collection-iteration` work on `main`. Still MISSING globally: a `select`/argmax cap (k-NN needs
  it) — CR out.
- **Resident brain.** `repl.py` = thin per-brain shim over core `boot_brain` + `BrainREPL`/`loop`
  (arc1 pattern). Engine is core; only nilm-specific lines = the Solver install + `learn_pipeline`.
  Brain-agnostic goal = **skill-package** nilm (`mindsos skill install`) so even the shim goes; the
  bundle format already carries l3 caps/datastates/`allow_new_realm`/l2_content/l4_slots. Blockers:
  L3 install is Global-only (user-Local skills = CR out) + a Global re-home of nilm's caps.
- **CRs out (other chats):** (1) user-scoped Local skill install; (2) Global `select`/argmax cap;
  (3) learned-pipeline persistence — **DONE, merged, ADR-0203**.
- **Viewer (separate chat).** A `mindsos brain view` verb + `mindsos_cli/brain_graph.py` + template
  are **STASHED** on the Mac (`git stash` "viewer WIP: brain view verb"); that chat reconciles onto
  main's `brain.py`. Its source generator is this chat's `brain_graph.py` (nilm graph).

## Working protocol (unchanged, enforced)
Explain in plain English → user approves → then run. Be **concise and skeptical** (a
critical design reviewer, not a validator). **Never edit `mindsos_*`.** **No git from the
Cowork sandbox** — the Mac commits/pushes with explicit paths (never `git add -A`), Linux
pulls/validates; read-only git from the sandbox is fine. **No hardcoded values** — every
constant is a DataState input. **Do not document numpy probe/test *results*** in any
persisted file (contamination rule): the brain's capacities are the source of truth, not
throwaway numpy.
