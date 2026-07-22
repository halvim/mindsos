# Leaf-Learning applied to NILM (Energy Disaggregation) — amii study (WORKING DRAFT)

**Status.** Working draft, 2026-07-20. The **NILM instantiation** of the domain-neutral contract
in `LEAF_LEARNING_PROCESS.md`. It *applies* that doctrine; it does not redefine it. Lives in the
amii worktree: `projects/amii_study/LEAF_LEARNING_NILM_APPLICATION.md` (branch `chore/amii-study`).
Grows as the study settles; nothing frozen until the prereg is. (Replaces the retired PQ
application file — PQ is not the domain.)

**Goal.** Prepare a study that **proves the leaf-learning process** (`LEAF_LEARNING_PROCESS.md`
§0–§6) on a real Energy-&-Utilities problem, with the **architecture-is-cause** claim fail-proof.
Not "beat NILM SOTA on accuracy" (SOTA is ~0.99 in-distribution).

---

## 1. Locked decisions

- **Sector:** Energy & Utilities. Beneficiary = utility / grid / energy operators (load
  disaggregation, demand response, grid-edge monitoring). Default use-case: residential NILM.
- **Domain:** NILM — disaggregate a household's aggregate electrical measurement into appliances.
  Aggregation is **addition by construction** (aggregate = Σ appliance signatures) → compositional
  grounding handed to us by physics.
- **NILM is the real flagship; synthetic bench allowed where needed.** We do not run a parallel
  synthetic study, but a synthetic generator is a permitted *tool* wherever it's genuinely needed
  to achieve a goal — e.g. exact atom-level ground truth for a specific validation, or dialed
  difficulty for an honest-limit sweep. Default is real data: signal atoms are self-grounding
  (their truth is a deterministic transform of the waveform) and faithfulness is tested by
  **ablation**, not labels — so the bench is reached for only when a real-data check can't stand
  in.
- **Substrate: high-frequency current + voltage waveform** (30 kHz), not low-frequency power.
  Gives genuine waveform atoms (harmonics, phase, shape) for grounded composition.
- **Dataset: PLAID 2018** — 1876 submetered records, 16 appliance types, 30 kHz current+voltage,
  ~2 s; plus `aggregated.zip` for the concurrent case. Local at `datasets/PLAID_2018/` (to be moved
  under the gitignored `data/datasets/`). WHITED later, only for generalisation hardening.
- **Primary claim / flagship (regime B analog):** a **novel appliance** (never taught) →
  no composition of held atoms explains its current signature → **request-reference** (names the
  residual structure) → **teach one appliance atom additively** (new L2, existing untouched),
  few-shot, on-device, inspectable. This is NILM's acknowledged-unsolved "unknown appliance"
  problem.
- **Axes we contest (a calibrated CNN cannot match):** **H5** named gap (actionable) vs opaque
  OOD scalar · **H4** one-atom additive expansion, matched-units zero-forgetting, on-device,
  inspectable · the **stance**. **H3 (refuse-vs-bluff) conceded as a tie** (calibrated abstain
  also flags novelty).
- **Baselines:** the existing incremental CNN + CL zoo as the monolithic "− structure" ablation
  arm (forgets on incremental add, can't name the gap); a strong **open-set NILM** baseline
  (ViT + detection head) for the unknown-appliance contest; **LLM-NILM** as the honesty contrast.
- **MindsOS arm on the real core** (needs the two CRs: learned-leaf L2 apparatus + L4
  joint-inference control loop). Guardrail: do not shape core to win the study.

## 2. What MindsOS receives

Two channels — **current and voltage at 30 kHz** (~60 k samples / 2 s). Nothing else. The
appliance fingerprint lives in the **current waveform shape** (same 60 Hz voltage; resistive loads
sinusoidal, switching loads harmonic-rich). Appliances are *concepts*; the shape structure is
*compositions*; the samples are the *floor*.

## 3. The NILM ladder (preview — to be defined one atom at a time, §1 doctrine)

Floor `current`, `voltage`, `time` → compositions `fundamental fit` · `harmonic content`
(project onto k·60 Hz) · `phase / power-factor` · `active/reactive power` · `waveform shape` /
`turn-on transient` → concept = appliance type. None frozen; each argued and tested in turn.

## 4. Test 1 (re-pointed to NILM) — teach & recognize an appliance

The first empirical test of the process on real data.

- **Teach a clean resistive appliance first** (Water kettle / Hairdryer — near-sinusoidal current):
  build/reuse the ladder bottom-up, add one thin appliance rung, learn only its L2 parameters to
  the required confidence (enough-shots, not fixed-k). Negatives must be **confusable** (other
  appliances), not silence.
- **Then a held-out novel appliance** (candidates: Blender = 2 records, Coffee maker / Hair Iron =
  10) to exercise **request-reference → teach-one → no-forget**.
- **Recognize:** P8 top-down; ambiguity + confidence-deficit → redundant-grounding descent;
  terminal states confident / held-ambiguity / request-reference.
- Pass/revise → recorded against `LEAF_LEARNING_PROCESS.md`; **#3 (request-reference mechanics) is
  finalised here.**

## 5. OPEN for NILM (deferred — argue one at a time)

- The **atom list** (floor → compositions → appliance), argued/tested one at a time.
- **Taught vs held-out appliance split** (the small-count classes are natural novels).
- **#3 request-reference mechanical criterion** — finalise against Test 1.
- Baseline configs (open-set NILM, LLM-NILM) and the matched-units retention metric on real data.
- Real-data logistics: placement (`data/datasets/`), loader, and how it reaches the Linux gate.

## 6. Capacity / pipeline registry (running list)

Two kinds, per the layer model (`docs/concepts/layers.md`): **L3 capacities** are *single-step*;
**L4 pipelines** *compose* L3 steps (the pipeline-finder assembles them) plus the control loop.
**D** = deterministic · **L** = learned (L2). *This registry doubles as the Test-1 build spec.*

### L3 — single-step capacities (by family)
- **perception** — `parse_raw`: raw_data → {voltage, current, time} (D; the §2 interpretation
  boundary; uses given channel metadata: col0=current, col1=voltage, row ÷ `fs` = time).
- **derivation** (all D) — `bind` (value+time→signal) · `multiply` · `subtract` · `rms` · `fft` ·
  `band_energy` · `spectral_flatness` (→ spectral_concentration) · `temporal_flatness`
  (→ temporal_concentration) · `normalize` · `angle` · `window` (signal → sub-window) ·
  `segment` · `count` ·
  `fit_reference` (observation + **reference** → model) · `synthesize` (model → signal) ·
  `compare_across_windows` (→ stability) · `induce_structure` (examples → DAG).
- **scoring** — `calibrate`: features → confidence (**L** — the only learned capacity).
- **predicate** (D) — `compare` · `compare_structures` (declared vs induced agreement).
- **comprehension** — `bind_declaration`: declared_structure → bound | request (D).
- **decision** — `verdict`: (atom, confidence) → confident | held-ambiguity | request-reference (D;
  the family VERDICT dont-know channel).

### L4 — pipelines (compose L3 steps) + control
- `power` = `parse_raw → multiply` (declared `P=V·I`).
- `harmonic_amplitudes` = `segment → fft → band_energy(k·f0)`.
- **Recognitions** (each a §4A template pipeline: `fit_reference → synthesize → subtract →`
  `features{rms, spectral_flatness, temporal_flatness, band_energy→harmonic_fraction, compare_across_windows}`
  `→ calibrate → verdict`): `cycle` · `onset` · `harmonics_present` · `load_type` · `appliance`.
- **Control loop** (L4 control flow, not a pipeline): top-down engagement (P8) · descent on
  confidence-deficit · joint-inference / whole-part validation · redundant-grounding · the
  acquisition sequence (reach-check → declare/induce → fit → verify) · terminal-state routing.

### Given (exogenous)
- `declared_structure` — a human-authored DAG (input, understood via `bind_declaration`).

## 6.1 The `cycle` recognition pipeline (raw_data → verdict) — detailed

An L4 pipeline of single-step L3 capacities. Each row: `capacity` (family, D/L) : **in_ds → out_ds**.

| # | capacity (family, D/L) | in_ds (constants are DataStates, never literals) | out_ds |
|---|---|---|---|
| 1 | `parse_raw` (perception, D) | `raw_data`, `fs`, `channel_map` | `voltage`, `current`, `time` |
| 2 | `bind` (derivation, D) | `voltage`, `time` | `voltage_signal` |
| **3–4** | **period-refinement loop (L4): repeat 3→4 until \|Δperiod\| < `period_tol`** | `voltage_signal`, `f0`, `window_cycles`, `fs`, `period_tol` | converged `cycle_model` |
| 3 | `window` (derivation, D) | `voltage_signal`, `freq_estimate`, `window_cycles`, `fs` | `voltage_window` |
| 4 | `fit_reference` (derivation, D) | `voltage_window`, `cycle_reference` (L2), `freq_estimate`, `fs` | `cycle_model` (→ next `freq_estimate`) |
| 5 | `synthesize` (derivation, D) | `cycle_model`, `voltage_window`, `fs` | `reconstructed_window` |
| 6 | `subtract` (derivation, D) | `voltage_window`, `reconstructed_window` | `residual` |
| 7 | `rms` (derivation, D) | `residual` | `residual_energy` |
| 8 | `fft` (derivation, D) | `residual`, `fs` | `residual_spectrum` |
| 9a | `spectral_flatness` (derivation, D) | `residual_spectrum` | `spectral_concentration` |
| 9b | `temporal_flatness` (derivation, D) | `residual`, `n_time_bins` | `temporal_concentration` |
| 10 | `band_energy` (derivation, D) | `residual_spectrum`, `f0`, `harmonic_orders` | `harmonic_fraction` |
| 11 | `compare_across_windows` (derivation, D) | `cycle_model`, `cycle_model_history` | `period_stability` |
| 12 | `calibrate` (scoring, **L**) | `residual_energy`, `harmonic_fraction`, `spectral_concentration`, `temporal_concentration`, `period_stability` (+ L2 params) | `cycle_confidence` |
| 13 | `verdict` (decision, D) | `cycle_model`, `cycle_confidence`, `spectral_concentration`, `temporal_concentration`, `known_references` (L2), `required_confidence`, `structuredness_thresholds` | `cycle_verdict` |

`cycle_verdict` → **`cycle`** (confidence ≥ `required_confidence`) · **`held_ambiguity`** (low conf,
residual flat on all axes) · **`request_reference`** (`spectral_concentration` *or*
`temporal_concentration` ≥ its threshold, **and no `known_references` match** — names the structure +
the axis).

**No hardcoded values.** Every constant is a DataState input (provenance in §7): `fs` `f0` `channel_map`
`window_cycles` `harmonic_orders` `harmonic_bandwidth` `window_step` `n_time_bins` `period_tol` are
given; `required_confidence` is from L5; `structuredness_thresholds` + `calibrate` params are learned
in L2; `cycle_reference` / `known_references` are **L2 references** (§8). `freq_estimate` initialises to
`f0`, updated each loop pass by `fit_reference`. The **3–4 refinement loop is L4** — explicit,
auditable, no single pass. `period_stability` needs ≥2 windows (a multi-window pipeline).

## 7. DataState registry (running list)

Realm `nilm` (`datastate:nilm.<name>`; registered `allow_new_realm`). **given** = input/const; **floor** =
irreducible atom; **derived** = composition output; **verdict** = terminal.

- **given — domain constants:** `raw_data` (input) · `fs` · `f0` · `V_nom` · `channel_map` ·
  `window_cycles` · `window_step` · `harmonic_orders` · `harmonic_bandwidth` · `n_time_bins` · `period_tol`
- **given — task (L5):** `required_confidence`
- **given — references (L2):** `cycle_reference`, and the growing `known_references` library (§8)
- **given — learned (L2):** `structuredness_thresholds` (per-axis) · (`calibrate` parameter sets, per rung)
- **given — state:** `cycle_model_history` · `freq_estimate` (loop) · `declared_structure`
- **floor:** `voltage` · `current` · `time`
- **derived:** `voltage_signal` · `current_signal` · `voltage_window` · `cycle_model` ·
  `reconstructed_window` · `residual` · `residual_energy` · `residual_spectrum` ·
  `spectral_concentration` · `temporal_concentration` · `harmonic_fraction` · `period_stability` ·
  `power` · `harmonic_amplitudes` · `shape` · `phase`
- **learned output:** `cycle_confidence` (and, per rung: `<rung>_confidence`)
- **verdict / terminal:** `cycle_verdict` → `cycle` | `held_ambiguity` | `request_reference`

## 8. L2 reference registry (running list)

**References = L2 knowledge** — the known patterns the system matches observations against
(`concepts` role-graph + their `learned-parameters`). This library is what grows additively; L3
capacities and L4 pipelines stay fixed. A **request-reference** asks to add a new entry here.

- **given (domain knowledge):** `cycle_reference` — *"a grid cycle is a sinusoid at ~`f0`"*, the model
  `fit_reference` matches the voltage window against. Previously baked into `fit_sinusoid`; now explicit.
- **learned (taught, few-shot):** *none yet.* Each taught disturbance/appliance (`sag`, `notch`,
  appliance signatures, …) is added here as one new reference — that adding **is** the leaf-learning.
- The **request-reference loop** only becomes meaningful once this library holds enough references that
  a novel observation is genuinely "none of these."

(Grows as we define the `onset` / `harmonics_present` / `load_type` / `appliance` rungs.)
