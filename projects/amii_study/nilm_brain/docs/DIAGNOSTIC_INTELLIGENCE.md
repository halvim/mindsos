# Diagnostic Intelligence — a hand-run trace of the L4 acquisition/diagnosis loop

**Status / scope.** This records the *diagnostic* reasoning used to bring appliance
recognition up on real PLAID data. It is deliberately separated from the brain: the
brain (mindsos capacities) does the **recognition**; the **diagnosis** — deciding *why*
recognition was wrong and *what to change* — was performed by the operator (an LLM) in a
working chat, standing in for the L4 acquisition/joint-inference control loop that the
doctrine names but core has **not built** (`LEAF_LEARNING_PROCESS.md` §4: "L4 deliberates
… designed-not-built core"; §3B the acquisition procedure).

**Why record it.** The study's claim is *"mindsos architecture can do the diagnoses from
real data."* Today that is **not yet true**: mindsos does the recognition, the operator did
the diagnosis. This file is the worked example of what that diagnostic loop must do, so it
can later be built as L4 capacities rather than run by a human/LLM.

**Numbers here are session observations** (a trace of what drove each decision), not
persisted brain truth. The capacities remain the source of truth (contamination rule).

---

## 1. The two layers (the honest line)

- **Recognition** — raw data → typed atoms → verdict. This *is* mindsos: a finder-composed
  pipeline of capacities executed by `execute_pipeline`.
- **Diagnosis** — recognition is failing → hypothesize the cause → probe → localize → fix →
  re-test. This was the **operator/L4**, not the architecture.
- **Transfer target.** Turn the diagnosis loop into L4 control capacities. Each move below is
  tagged with its doctrine home to show it is buildable, not foreign.

---

## 2. The diagnostic method (the recurring loop)

Every fix this session came from the same loop:

> **hypothesize a cause → build a *falsifiable, labeled* probe → measure → localize the
> fault → make the smallest fix → re-test on held-out data.**

The load-bearing principles (the "diagnose intelligence"):

1. **Measure before fixing.** A fault's location is in the numbers, not intuition. The one
   time the operator guessed instead of instrumenting (the current-amplitude hypothesis), the
   guess was wrong. Instrument, then decide.
2. **Labeled ground truth, not a single assertion.** You cannot judge a decision boundary
   without examples spanning the classes with known answers. Build a confusion matrix; a lone
   pass/fail can't tell you *which* component is wrong.
3. **A good test diagnoses, it doesn't just fail.** Design the probe so the result points at
   the fault: *threshold vs feature* (does any cutoff separate the classes → calibration; does
   none → the feature is inadequate); *memorization vs generalization* (does a held-out
   instance match, or only the taught one).
4. **Classification must match production.** A value documented as *learned* but sourced as a
   *given constant* is a bug even when nothing crashes (open item #1).
5. **A learned threshold inherits the honesty of its reference.** Calibrating a "structure vs
   noise" gate on a baseline that is itself structured poisons it. Check the baseline.
6. **Physically impossible values are signposts.** A concentration gate of `1.57` (max ~1.0),
   a leftover of `0.9` on every non-taught window — these locate the fault (bad seed; wrong
   representation) faster than any theory.
7. **Test against memorization and against negatives.** Teach-A / recognize-B, plus explicit
   negatives (a different structure, noise, other appliances). A match count is meaningless
   until self-match is excluded and rejection of negatives is confirmed.
8. **When calibration and alignment are exhausted, change the representation.** Repeated
   failure at the margin means the feature is wrong — match a different, invariant quantity.

---

## 3. Per-step trace (what failed → how it was localized → the fix → doctrine home)

| # | Symptom | How localized | Fix | Doctrine home |
|---|---|---|---|---|
| 1 | `held_ambiguity` unreachable; `request_reference` degenerate | Reanalysis: thresholds hardcoded in `build_given`, spectral gate saturated (~0.995 always) | Re-home thresholds to an L2 slot (#1a); seed-fit them (#1b) | §7 learned-L2; verify/calibration §3B.4 |
| 2 | Battery baseline RED: noise → `request_reference` | Printed per-class feature ranges → temporal gate ~0.0004 because clean residual is a smooth harmonic | Gate = `max(clean-floor, noise-floor)`; noise floor from a white-noise surrogate | Redundant-grounding / descent §4; calibration audit P14 |
| 3 | `teach` on current: "no request_reference window" (×2) | Printed the full feature landscape → current gate `1.57` (>1) | Seed the current gate on a **synthetic pure-sinusoid** current (honest zero-distortion baseline) | Reference-quality check; synthetic-for-ground-truth (app §1) |
| 4 | Appliance `matched=1` — memorization? | `match_leftovers`: taught window leftover 0.000, all others ~0.9 | Diagnosed as memorization → representation is wrong | Held-out verify §3B.4; anti-memorization guard §3B(a) |
| 5 | Shift-invariance inert (notch + appliance unchanged) | A single lag can't align a mixed periodic+localized residual (verified the math on a toy first) | Kept (harmless); not the fix | — |
| 6 | Time-domain template can't be the signature | Leftover-0.9-everywhere ⇒ phase-sensitive, varies window-to-window | New capacity `harmonic_profile`; match the phase-invariant harmonic magnitudes | Operator-level irreducibility → **logged request for a new operator** §3A closure |
| 7 | Does the spectral signature discriminate? | `profile_similarities`: Laptop 0.994–0.998 (generalizes), others ≤0.957 | Kept spectral signature; margin ≈0.04 | Acquisition verify §3B.4 |

---

## 4. Recognition as pipelines (DataState transitions) — and what is still operator/L4

**The recognition measurement pipeline (fully mindsos):**

```
raw_data
  -(parse_raw)->      current, voltage, time
  -(bind_current)->   signal            (or bind for voltage)
  -(normalize)->      signal            (current only: amplitude-independent)
  -(window)->         signal_window
  -(fit_reference)->  cycle_model       (sinusoid fundamental)
  -(synthesize)->     reconstructed_window
  -(subtract)->       residual
  -(fft)->            residual_spectrum
  -(harmonic_profile)-> harmonic_amplitudes     # the appliance signature
      # parallel: rms, spectral_flatness, temporal_flatness, band_energy,
      #           compare_across_windows -> calibrate -> cycle_confidence
  -(verdict)->        cycle_verdict     (cycle | request_reference | held_ambiguity)
```

**Still operator/L4 Python, NOT capacities (the gap to close for recognition to be mindsos
end-to-end):**

- **Match** — comparing a window's `harmonic_amplitudes` to a reference profile (cosine) lives
  in `profile_similarities` / `_match_references`, not a capacity.
- **The recognition decision** — "similar enough → `recognized[name]`" lives in `_match_verdict`,
  not the decision family.
- **The match cutoff** — no learned-cutoff DataState exists.
- **Teach** — `teach` / `teach_spectral` (extract residual/profile, store a reference) is L4
  acquisition. The human-initiated case is legitimately L4; the *autonomous* request→teach is the
  unbuilt loop.

**Concretely, to make appliance recognition fully expressible as mindsos capabilities:**

1. a **comparison capacity** (predicate family): `harmonic_amplitudes` + reference profile → a
   `comparison`/similarity (replaces inline cosine);
2. a **learned match-cutoff DataState** (L2), fit from the taught appliance's own window-sim
   spread (not a literal);
3. the **verdict** extended to emit `recognized` from (similarity, cutoff).

These are small and well-scoped, and — unlike the diagnostic loop — they are *recognition*, so
they belong in the architecture. **Caveat:** even built, "solves the dataset" is unproven — one
appliance vs five at a 0.04 margin on one instance each; dataset-scale separation is untested.

---

## 5. Transfer spec — each diagnostic act → its mindsos home

To build the diagnosis into L4, each operator move maps to a doctrine-defined act:

- **Build a labeled battery, read the confusion matrix** → the acquisition **verify** step
  (§3B.4: faithfulness + calibration on held-out) + the **calibration audit** (P14).
- **Instrument features; decide threshold-vs-feature** → **descent / redundant-grounding** (§4):
  on a confidence deficit, descend for a more discriminating reading; decide recalibrate vs add-a-
  reading.
- **Teach-A / recognize-B, reject negatives** → the **anti-hallucination / anti-memorization**
  invariant (§4) + generator guard §3B(a) (never fit on the tested instance).
- **"The library can't express this" → new capacity** → **operator-level irreducibility**, a
  logged **request for a new operator** (§3A closure) — `harmonic_profile` was exactly this,
  performed by hand.
- **"The clean seed isn't clean" → synthetic baseline** → a **reference-quality check** and the
  sanctioned use of synthetic data for a ground truth real data can't supply (app §1).

The recognition capacities do not drift from the architecture. The risk of drift is that the
**decision** and the **diagnosis** keep accreting in L4 Python — where the brain "works" but the
intelligence is in the operator's code, not the architecture. The discipline: every L4 addition
is either legitimate orchestration (iteration/dispatch) **or** must become a capacity. The match
decision (§4 above) is the current, closest instance of that line.
