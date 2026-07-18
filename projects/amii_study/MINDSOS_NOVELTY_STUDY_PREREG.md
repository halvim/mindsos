# Pre-Registration — Compositional Skill-Acquisition: a four-axis novelty study

**Domain:** power-quality (PQ) disturbance recognition (parametric generator).
**Status:** DRAFT to be frozen before the MindsOS arm is built. Numbers marked *(calibrate)* are set from the pilot (Phase 2) and frozen before any test-set read.
**Discipline:** test split read once; baselines tuned to convergence with an equal engineering budget; no metric chosen or changed after results are seen.

---

## 1. The claim being tested

> A capability **learned as a composition of typed primitives** achieves, *jointly and from the same system*: (A1) target competence from **fewer labels**, (A2) at **lower compute**, with (A3) **no degradation of prior capabilities**, and (A4) **positive transfer** to new ones — and the advantage is **caused by the compositional structure** (remove it and the advantage disappears).

The contribution is not any single axis — each has prior art. It is landing **off the trade-off frontier on all four axes at once**, attributable to the architecture. That combination is what existing methods do not achieve jointly.

**Falsifiable.** Section 7 gives a numeric success **and kill** condition per axis. If the kill condition fires, the claim is reported as failed and narrowed — not rescued.

---

## 2. Why this domain (efficiency + rigor in one)

PQ disturbances are generated from **parametric equations** you own, so: unlimited fair examples, exact ground truth, zero labeling cost, controllable difficulty, and — decisively — you can **design the concept stream** (shared primitives, held-out compositions) that axes A3/A4 require. Signals are **1-D**, so every arm runs on **CPU in minutes**: many seeds are affordable, the compute comparison is matched-hardware and clean, and the "runs on a laptop" accessibility story is honest. And it is a real **energy** task, relevant to Amii and Alberta funders.

---

## 3. The generator (controlled, parametric)

Base: 60 Hz fundamental (Alberta grid). Sampling and window: *(calibrate — proposed 256 samples/cycle, 10-cycle window)*. Additive white Gaussian noise swept over **SNR 20–50 dB** as a controlled robustness variable.

**Primitive vocabulary — the single disturbances (the "typed primitives"):**

| Primitive | Parametric form (sketch) | Free parameters |
|---|---|---|
| sag | `[1 − α(u(t−t₁)−u(t−t₂))]·sin(ωt)` | depth α∈[0.1,0.9], start, duration |
| swell | `[1 + α(u(t−t₁)−u(t−t₂))]·sin(ωt)` | α∈[0.1,0.8], start, duration |
| interruption | sag with α→~1 | start, duration |
| harmonic | `sin(ωt)+Σ aₖ sin(kωt)`, k∈{3,5,7} | aₖ amplitudes |
| flicker | `[1 + α·sin(2πβt)]·sin(ωt)` | α∈[0.1,0.2], β∈[5,20] Hz |
| oscillatory transient | `sin(ωt)+β e^{−(t−t₁)/τ} sin(ω_n t)` | β, τ, ω_n, start |
| notch | periodic notch subtracted at firing angle | depth, position |
| (held-out primitive) | one class **never taught** — for the honesty axis (§7 A5) | — |

**Composition = the combined disturbances**, which are *literally the single-primitive operations applied together* (e.g. `sag+harmonic`, `swell+harmonic`, `sag+transient`, `flicker+harmonic`). A combined event **reuses** its constituent primitives — this is exactly what makes backward/forward transfer non-trivial and what a compositional system should exploit.

---

## 4. The concept stream (what makes A3/A4 measurable)

Concepts are taught **incrementally**, in a fixed pre-registered order, and every combined concept **shares primitives** with earlier ones (so forgetting is *possible in principle* — otherwise "no forgetting" is a trivial property of frozen modules):

1. Increments 1–7: the single primitives, one at a time.
2. Increments 8–N: combined concepts, each composed of already-taught primitives.

**Held-out compositional split:** a pre-specified subset of *combinations* is **never trained** and appears only at test (e.g., train `sag+harmonic`, `swell+harmonic`; hold out `sag+transient`). Success on held-out combinations = genuine composition, not memorization.

**Test set:** frozen, generated once, drawn from parameter ranges and SNRs disjoint from training seeds. Read **once**, in Phase 5.

---

## 5. Arms (all evaluated identically)

- **MindsOS** — primitive-detection Capacities (learned leaves with calibrated confidence per your grounding→leaf→composition ladder), composition assembles the multi-label verdict.
- **MindsOS − structure (ablation)** — same learned components, compositional typing removed / replaced by a flat learned map. **This arm is the causal test:** if the A1/A2 gains survive here, the structure was not the cause.
- **Per-increment deep net** — standard 1-D CNN and CNN-LSTM (the PQ-classification standard), retrained/fine-tuned per increment.
- **Continual-learning baselines** — EWC, LwF, iCaRL, Experience Replay (via the Avalanche library) — the real competition on **forgetting**, run at a matched memory/compute budget.
- **Few-shot baseline** — Prototypical Network / MAML — the real competition on **data efficiency**.
- *(optional)* **Selective-prediction baseline** — softmax-threshold / an LLM-style classifier — for the honesty axis.

**Supervision ledger (mandatory).** For every arm, enumerate the human knowledge supplied — MindsOS: the typed primitive definitions and parametric priors; baselines: architecture, hyperparameters, any pretraining. This is published *with* the result so a reviewer can see the priors are not smuggling the answer. It is the primary defense against "your hand-authored structure did the learning."

---

## 6. Metrics (all read off the one incremental run)

- **A1 Data efficiency** — *labels-to-competence*: labels needed to reach the competence threshold (per-class F1 ≥ *(calibrate, proposed 0.95)*) on held-out test. Reported as a sample-efficiency curve (area under it) per arm.
- **A2 Compute efficiency** — *compute-to-competence*: **FLOPs** (via profiler) **and** wall-clock to reach the same threshold, on **matched CPU**, **params reported**, **training vs inference separated**. Plus the **amortization curve**: marginal compute to learn concept *N* as a function of *N*.
- **A3 Non-destructive learning** — **Backward Transfer (BWT)**: change in accuracy on every prior concept after each new one, vs. strong CL baselines at matched budget.
- **A4 Compositional transfer** — **Forward Transfer (FWT)**: does having the primitives reduce the labels/compute to learn a new *composition*, vs. learning it from scratch.
- **ATTR Attribution** — the A1/A2 gap between MindsOS and **MindsOS − structure**.
- **A5 (optional) Calibrated honesty** — on the never-taught held-out primitive: refusal precision / risk-coverage vs. the selective-prediction baseline (which should confidently misclassify it).

---

## 7. Pre-registered success **and kill** conditions

Set the *(calibrate)* numbers from the Phase-2 pilot on **dev only**, then freeze. Confirmation requires ≥5 seeds, mean ± 95% CI, paired significance.

| Axis | Confirms novelty | Kills the claim |
|---|---|---|
| A1 data | MindsOS hits threshold with ≤ *(calibrate, target ≤20%)* of the best baseline's labels, significant | A tuned baseline matches within the label budget |
| A2 compute | MindsOS FLOPs-to-competence ≥ *(calibrate)*× lower **and** amortization slope significantly **negative** | Baseline matches; or MindsOS slope not negative (no amortization) |
| A3 forgetting | MindsOS BWT ≥ −0.02 while a strong CL baseline shows BWT ≤ −0.10 at equal budget | MindsOS forgets (BWT < −0.02); **or** a CL baseline also achieves ~0 at equal cost (then not novel) |
| A4 transfer | MindsOS FWT > 0, significant, vs. ~0 for from-scratch | FWT ≤ 0 (primitives don't help) |
| ATTR | ablation loses ≥ half the A1/A2 gain | ablation keeps the gain (structure wasn't the cause) |

**The load-bearing kill conditions** are ATTR (if the ablation keeps the gain, you've built a good classifier, not a novel architecture) and A3's second clause (if a standard CL method also gets ~0 forgetting cheaply, non-destructiveness isn't novel). Do not soften these after seeing results.

---

## 8. Confounds designed out in advance

1. *"The priors did the learning"* → supervision ledger + structure-ablation.
2. *"Weak baseline"* → equal tuning budget; report each baseline's best; standard architectures.
3. *"Smaller model is just faster"* → compute-to-**competence** (same accuracy), params + hardware reported, training/inference separated.
4. *"No forgetting is trivial for modules"* → concepts **share** primitives; measured vs strong CL baselines, not naive fine-tuning.
5. *"Cherry-picked toy"* → held-out compositions + a second-domain replication (real vibration data, §10).
6. *"Metric gaming"* → standard CL metrics (BWT/FWT/avg-acc), pre-registered, no post-hoc metric.

---

## 9. Analysis & integrity

≥5 seeds per arm; mean ± 95% CI; paired significance (Wilcoxon) with effect sizes; sample-efficiency curves and the forgetting matrix reported in full. Build the rig and **all baselines before** the MindsOS arm. Sanity-check the harness on a known result before it judges anything. Test set read **once**. Headline numbers independently re-run before presenting.

---

## 10. Scope, replication, execution

**A positive result licenses exactly:** *compositional skill-acquisition yields joint data + compute efficiency and non-destructive transfer in PQ disturbance recognition, attributable to structure* — replicated once on a **real public vibration-fault dataset** (Paderborn/CWRU) for realism. Not general superiority, not AGI.

**Phases:** (0) freeze claim → (1) build generator + evaluation rig + all baselines → (2) pilot on dev, calibrate the *(calibrate)* thresholds → (3) freeze this pre-registration → (4) build MindsOS + ablation arms → (5) run all arms × seeds, read test once → (6) analyze vs §7, replicate on real data, write up (positive **or** the sharpened negative).

---

## 11. Prior-art check (run before Phase 4 — do not skip)

Confirm no existing method already reports this *joint* result in PQ or a comparable domain: search neuro-symbolic / compositional continual learning, few-shot class-incremental learning (FSCIL), and PQ-classification continual-learning papers. If someone already owns the four-axis joint claim, narrow to the axis that is still open. Findings recorded here before building.
