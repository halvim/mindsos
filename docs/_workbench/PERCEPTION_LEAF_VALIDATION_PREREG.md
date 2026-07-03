# Compositional Atom-Learning vs Learned Perception — Validation Pre-Registration (Study 2)

**Status: PRE-REGISTRATION — frozen before any experiment code is written.** Paper-grade. Supersedes
the Study-1 leaf-novelty contest (`PERCEPTION_LEAF_NOVELTY_PREREG.md`), whose honest result was that
its substrate + metrics were aimed at axes where opaque ML is already strong, and whose MindsOS side
used a hand-coded corner-counter rather than genuine atom learning. This study fixes both: it learns
the atoms, validates shapes *through* their atoms, and measures the axes where a compositional system
is claimed to differ — auditability, honest "don't-know", named-atom expansion, and data-efficiency —
against the baselines specialists actually respect.

**Anti-tuning.** Every threshold, metric, baseline, and pre-committed reading below is frozen. Change
only by a dated amendment in §11 recorded *before* the affected run. If a claim fails, fix the claim,
not the test. Every empirical claim is independently audited by an adversarial "ML-advocate" subagent
(it tries to make the baselines win) **before** any verdict is reported.

**Reproducibility.** Fixed seeds; ≥5 seeds; per-run JSON + seed; one frozen per-sample test set shared
byte-identically by every system. Per-sample records retained (not only aggregates).

---

## 0. The claim under test (frozen)

**Architecture (frozen).** MindsOS perceives by **bidirectional joint inference over a named-atom
part-whole hierarchy**, NOT a one-way pipeline. `leaf-learning` is a capacity (a DataState transition)
that learns the **atoms**; atoms compose into **derived components**; and the two levels **mutually
validate**: a derived-component hypothesis raises/confirms its expected atoms (top-down) while the
atoms raise/confirm the component (bottom-up). **Confidence = the degree of cross-level agreement**, so
an individual low-confidence detection at one level can be carried by consistency at another — "as a
group they complement each other." When **no** mutually-consistent interpretation exists over the
*current* atom vocabulary, the system emits a **named request for a specific new atom** (not merely
"low confidence").

> **H (compositional-architecture hypothesis).** A named-atom joint-inference perceiver has properties
> a strong learned system — *including an interpretable neuro-symbolic one AND an iterative
> feedback/part-whole one* — does not match at equal atom-supervision:
> (**H1**) generalizes to unseen shapes / unseen polygon-orders for ~zero additional labeled
> shape-examples; (**H2**) identifications are **faithfully auditable** (the stated sub-atoms actually
> determine the output); (**H3**) **refuses rather than bluffs** when no consistent interpretation
> exists; (**H4**) **expands by adding one named atom** that then participates in validation, near-zero
> cost, zero old-skill change; (**H5**) its "don't-know" **names the missing primitive** (actionable
> where a saliency map is not); (**H6 — HEADLINE**) its mutual validation achieves **high rescue AND
> low hallucination** — it recovers correct answers on degraded input that neither level alone gets
> right, *without* completing genuinely-absent structure — **because it is anchored at verifiable named
> atoms**, where an un-anchored feedback model must trade one for the other.

> **Null / failure reading (pre-committed).** For each Hi, if a fairly-tuned baseline (best abstain,
> best attribution, concept-bottleneck, the **feedback/part-whole** model, or enough labeled examples)
> matches MindsOS on the frozen metric, that Hi is **NOT established** — report it plainly. H is not a
> single win; each Hi stands or falls on its own measured number. **H6 can genuinely fail** (if
> atom-anchoring does not suppress top-down hallucination) — a negative result there is a real finding,
> reported as such.

**Novelty positioning (honest).** Bidirectional part↔whole mutual validation with confidence-from-
agreement is **prior art in form** (probabilistic grammars / And-Or graphs, part-whole MRFs, predictive
coding, capsule routing-by-agreement, analysis-by-synthesis). "We do mutual validation" is **not** the
contribution and is not claimed. The contested contribution is the **bundle**: exogenous **named**
atoms auditable at every level (H2), **request-a-named-new-atom** when consistency is unreachable
(H5), single-**named**-atom expansion (H4), and — the headline — **rescue-without-hallucination via
atom-anchoring** (H6), each measured against a feedback baseline that shares the mechanism but lacks
the anchoring.

**Explicitly NOT claimed:** "structured beats opaque on accuracy" (known); "interpretable/feedback
perception exists" (known — that is why the concept-bottleneck AND feedback baselines are mandatory);
that MindsOS invents atoms unsupervised (it does not — atoms are exogenous, P2); that the advantage
survives arbitrary real-world degradation (the tolerance/occlusion sweeps, §7, report exactly where
it breaks — including regimes where a baseline is *more* robust).

---

## 1. Locked design decisions (approved 2026-06-29)

**D-A — MindsOS learned/given line: ATOMS LEARNED, COMPOSITION GIVEN AS DEFINITIONS.**
The point / segment / vertex / curvature **detectors are learned** from labeled atom examples (held-out
atom accuracy reported, §5). Shape **concepts are given as one-line declarative definitions**
(`triangle = 3 segments, 3 vertices, closed`; `pentagon = 5 segments…`). The fair contrast is therefore
**definition-driven (1 declaration) vs example-driven (N labels)** — a data-efficiency axis, not
"MindsOS learns everything." **Anti-"rule-engine" control (D-A′):** a side-experiment shows a shape's
composition rule can be **induced from ≤3 labeled shape-examples** (so the rule is not load-bearing
hand-tuning); the main protocol stays definition-driven.

**D-B — Baselines (four):** (1) **CNN, two variants** — *incremental* (new shapes appended to prior
weights) and *from-scratch* (retrained on all data so far; the no-forgetting upper bound at full cost);
(2) **concept-bottleneck** — a learned-but-interpretable feedforward system predicting named parts →
shape (load-bearing for H1/H2); (3) **calibrated-abstain + best attribution** — every CNN gets a proper
reject-option and its strongest saliency/anomaly map, so H3/H5 are contested fairly; (4) **feedback /
part-whole model** — an *iterative* part↔whole model (routing-by-agreement / small energy-grammar)
that **shares the mutual-validation mechanism but lacks named-atom anchoring** — the fair contest for
H2/H6 (approved 2026-06-29). Without it, H6 would be feedback-vs-feedforward and inadmissible.

---

## 2. Systems under test

| System | Learned | Given | Inference | Expansion mechanism |
|---|---|---|---|---|
| **MindsOS** (numpy) | point/segment/vertex/curvature detectors (+ tolerances, calibrated) | shape definitions (declarative); atom *vocabulary* (P2) | **bidirectional joint** (atom↔component mutual validation; conf = cross-level agreement) | add one **named atom** + one definition; old atoms/shapes untouched |
| **CNN-incremental** (torch) | everything (pixels→shape) | nothing | feedforward | fine-tune on new-shape examples (forgets) |
| **CNN-scratch** (torch) | everything | nothing | feedforward | retrain from scratch on all data (no forgetting, full cost) |
| **Concept-bottleneck** (torch) | part-detectors + part→shape head | the *set* of named parts | feedforward (parts→whole) | add part(s) + retrain the small head |
| **CNN + abstain/heatmap** (torch) | as CNN | reject-option calibration; attribution | feedforward | as CNN |
| **Feedback / part-whole** (torch) | parts + agreement weights | the part set | **iterative** part↔whole (routing/energy), **no named-atom anchor** | add part(s) + re-fit |

All consume the **same frozen per-sample test set**. The learned/given ledger is published per stage.
The feedback model is the mechanism-matched control for H2/H6 (shares mutual validation, lacks anchoring).

---

## 3. Substrate (frozen generator)

64×64 grid, outline-rendered. **Atoms:** point → segment (aligned points) → vertex (two segments
meeting at an angle) → **curvature** (a run of points with no within-tolerance straight-segment fit).
**Shapes (built in stages):** triangle (3), rectangle (4), **square (4, equal sides + right angles)**,
**pentagon (5)**, circle (curved). Ground truth emitted at **every atom level** (point set, segment
list, vertex list + angles, per-pixel curvature flag) — required for training the learned atom
detectors *and* for faithfulness ablations (§5).

- Noise σ ∈ {0, .05, .1, .2}; scale s ∈ [0.6, 1.6]; random rotation.
- **Near-miss / degradation set:** bowed-edge polygons swept fine→coarse (the irreducible blind-spot
  regime) for §7.
- **Hallucination-adversarial set (H6, frozen):** inputs engineered to tempt top-down completion —
  (a) **occluded** shapes (erase one edge/corner: a true rectangle missing a side; a triangle missing a
  vertex); (b) **partial** figures that are genuinely *not* a closed shape (2–3 disconnected segments)
  but resemble the start of one; (c) **rescue-positive** inputs where a single edge/corner is
  noise-buried but the rest is intact (the joint interpretation *should* recover it); (d) **pure-noise**
  and **ambiguous** (square≡rectangle) foils. Ground truth marks each as *completable-correctly*
  (rescue target) vs *not-a-shape* (hallucination trap), so rescue and hallucination are scored on
  disjoint, pre-labeled subsets.
- Determinism: seed → identical arrays on any machine; the test split is serialized once and shared by
  all systems (no per-system regeneration). Train/cal/test splits are document-disjoint by seed.

---

## 4. Protocol — the 8 stages (your structure, reframed as data-efficiency curves)

Each stage reports, **per system, per sample**: prediction, correctness, confidence, and (where
applicable) refuse/abstain and the explanation artifact. New-shape stages are run as **learning curves**
over #labeled-examples for the learned baselines (so a baseline is never scored on a class it had zero
chance to learn — the contribution is *where each system sits on the curve*).

1. **Atoms.** Teach all systems the atoms; test atom identification on held-out samples → atom accuracy
   + confidence. (Establishes that MindsOS's atoms are *learned*, not given.)
2. **Triangle/rectangle, zero new shape-examples.** MindsOS: from definitions only. Baselines: the
   learning curve starts at 0 labeled shape-examples (expected ~chance) and climbs as examples are
   added → record the #examples each baseline needs to reach MindsOS's definition-only accuracy.
3. **Teach triangle/rectangle.** All systems now competent; re-test atoms **and** shapes → accuracy +
   confidence + the old-skill (atom) retention check.
4. **Square + pentagon, zero new shape-examples.** MindsOS: square = a constrained rectangle, pentagon
   = a 5-segment closed loop — both should identify for free if atom-counting generalizes. Baselines:
   learning curve from 0. (H1: unseen-order generalization.)
5. **Teach square + pentagon.** Re-test atoms + all 4 polygons → accuracy + confidence + retention.
6. **Circle (the withheld curved atom).** All systems see circles. Question (a): honest "don't-know"
   vs bluff. (H3/H5.)
7. **Expansion.** MindsOS: add the **named atom `curvature`** + one definition. CNN: add circle
   (incremental + from-scratch). Concept-bottleneck: add a "curved" part. Re-test atoms + all 5 shapes
   → accuracy + confidence + retention + **expansion-cost ledger** (H4).
8. **Progressive comparison.** Across stages 1–7, plot each system's accuracy, retention, confidence,
   and expansion cost. The CNN-scratch vs CNN-incremental gap = the learned baseline's true expansion
   tax; MindsOS's curve is the compositional alternative.

---

## 5. Metrics — qualitative claims turned into frozen measurements

- **Accuracy + confidence (per sample).** Identity correctness and a calibrated confidence per system;
  reported per shape × σ × scale, **paired per sample** (same input id across systems).
- **Data-efficiency curve (H1).** Accuracy vs #labeled-shape-examples for each learned baseline;
  MindsOS plotted as a point at "0 shape-examples (definition) / +N for the induction side-exp". MP:
  MindsOS reaches ≥0.90 on an unseen order (pentagon) at **0** labeled pentagon-examples where the
  best baseline needs **>0** to match — report the exact crossover.
- **Old-skill retention (H4), MATCHED UNITS.** For *every* system report the **same** number: absolute
  accuracy on prior shapes **before** vs **after** expansion, and the **delta**. (Fixes the Study-1
  unit-mismatch: no comparing a "flip-rate" to an "absolute".) MP: MindsOS delta ≈ 0; baseline deltas
  reported as-is.
- **Faithfulness / auditability (H2).** Ablate a claimed sub-atom (remove one segment/vertex from the
  evidence) and check the decision **flips**; faithfulness = fraction of identifications whose stated
  sub-atoms are decision-determining. Computed identically for MindsOS (atom evidence) and for the
  CNN/concept-bottleneck **best heat-map** (treat top-k attributed pixels/parts as the "stated reason",
  ablate, check flip). MP: MindsOS faithfulness ≥ 0.95; report the baselines' on the same scale.
  Secondary: **human-simulatability** — can a person predict the output from the explanation (held-out
  rater protocol, ≥2 raters, report agreement).
- **Refuse-vs-bluff (H3).** On the withheld-circle stage and the degradation set, the **refuse-rate**
  (MindsOS: atoms don't verify; baselines: *calibrated* abstain at matched coverage) vs the
  **high-confidence error rate**. MP: MindsOS high-conf error on un-learnable inputs ≤ 0.05 at refuse;
  compare the calibrated-CNN's best achievable error-at-coverage on the same inputs.
- **Actionability of "don't-know" (H5).** Give an oracle the system's gap signal — MindsOS's **named**
  `REQUEST_ATOM("curvature")` vs the CNN's **anomaly heat-map** — and measure whether the oracle
  supplies the correct missing primitive. MP: named-gap → correct primitive ≥ 0.90; heat-map → correct
  primitive reported on the same task (this is the one genuinely-uncontested axis; it must be *measured*,
  not asserted — and the heat-map gets its best shot, per D-B).
- **Expansion cost ledger (H4).** Per system: #labeled examples to add the new shape, #parameters
  changed, retrain needed (y/n), wall-cost, old-skill delta, and **whether the added unit is
  named/inspectable**.
- **Rescue rate (H6).** On the *rescue-positive* subset, fraction the **joint** interpretation gets
  right that **atoms-alone AND component-alone (single-level)** both get wrong. This operationalizes
  "the group complements each other." Reported for MindsOS and the feedback baseline (both do joint
  inference); single-level ablations of MindsOS are the internal control. MP: MindsOS rescue > best
  single-level by a margin > 2× cross-seed std.
- **Hallucination rate (H6, the failure mode).** On the *not-a-shape* subset (occluded-past-recognition,
  partial non-closures, pure noise), fraction the system **confidently reports a full shape** that isn't
  there. MP: MindsOS hallucination ≤ 0.05 **at its rescue operating point** (the trap is that raising
  rescue raises hallucination — both are read at the SAME setting). The **feedback baseline is expected
  to trade these off**; the claim is MindsOS holds both because atoms must be re-verified, not just
  predicted. Report the full rescue-vs-hallucination curve for every joint-inference system.

---

## 6. Per-sample comparison (mandatory, not optional)

All claims are evaluated **paired per sample** on the shared frozen test set. Report: **McNemar's test**
for each MindsOS-vs-baseline accuracy contrast (paired, significance), a **disagreement map** (which
samples each system wins, stratified by shape/σ/scale/near-miss-f), and the **error-overlap** (are the
two systems' errors correlated or complementary?). Percentages alone are insufficient; the per-sample
records are retained and shipped with the results.

---

## 7. Robustness / tolerance — reported as a limit, not patched away

MindsOS's tolerances (intensity cut, straightness tolerance, angle tolerance) are **swept**; for each
setting report the trade-off curve: loosening "how bent before a line isn't a line" raises curved-catch
**and** raises false-curved on true polygons. Per the P15/P17 doctrine the near-vocabulary blind spot is
**irreducible at fixed resolution** — the sweep quantifies *where* MindsOS breaks (which near-miss f,
which occlusion fraction) **versus the per-sample CNN behavior on the identical inputs**. We report the
crossover honestly: the regime where the learned baseline is *more* robust than MindsOS. No knob is
tuned to hide it.

---

## 8. Controls (carried + paper-grade)

1. **Positive control.** Each baseline must be competent on the basic task (≥ MindsOS − 5 pts on stage-3
   accuracy) or that contrast is void (no beating a weak net).
2. **Anti-strawman.** Baselines get their *best* fair configuration: calibrated abstain, strongest
   attribution, concept-bottleneck, and enough examples (the learning curve). Audited.
3. **Learned/given ledger** published per stage for every system (Trap-A from the design review).
4. **Leakage.** Atom-train / shape-train / cal / test document-disjoint by seed; the frozen test set is
   never seen in any training/calibration of any system.
5. **Reproducibility.** ≥5 seeds, mean±std; per-run JSON+seed; per-sample records retained.
6. **Independent adversarial audit** of (a) the design for rigging *before* any run, and (b) every
   PASS/FAIL re-derived from the frozen thresholds *before* any verdict — the ML-advocate actively tries
   to make each baseline match MindsOS.
7. **Unit-consistency check** (Study-1 lesson): every cross-system number is in identical units before
   comparison; the auditor verifies this explicitly.

---

## 9. Pre-committed readings (frozen — outcome → conclusion)

- **H1 (data-efficiency / unseen-order generalization):** MindsOS ≥0.90 on pentagon at 0 labeled
  pentagon-examples AND a learned baseline needs >0 to match ⇒ H1 **established** (compositional
  generalization is real, quantified as the crossover). If a baseline matches at 0 ⇒ H1 fails (report).
- **H2 (faithful auditability):** MindsOS faithfulness ≥0.95 AND strictly > the best baseline heat-map's
  on the same ablation metric ⇒ H2 established. If the concept-bottleneck ties ⇒ H2 is **not** unique to
  MindsOS — report as "matched by interpretable ML."
- **H3 (refuse-not-bluff):** MindsOS high-conf error ≤0.05 on un-learnable inputs AND the *calibrated*
  baseline cannot reach the same error-at-coverage ⇒ H3 established; else tie.
- **H4 (named-atom expansion):** MindsOS old-skill delta ≈0 with 1 named unit added AND lower total cost
  than from-scratch retrain AND the added unit is named/inspectable (where the CNN's is not) ⇒ H4
  established as a *cost + inspectability* claim (NOT "CNN can't expand" — from-scratch can).
- **H5 (actionable named gap):** named-gap→correct-primitive ≥0.90 AND heat-map→correct-primitive lower
  on the same oracle task ⇒ H5 established; if the heat-map matches ⇒ gap-naming is not a differentiator.
- **H6 (rescue-without-hallucination — HEADLINE):** MindsOS rescue > best single-level (margin > 2×std)
  AND hallucination ≤0.05 at that same operating point AND the **feedback baseline cannot hold both**
  (its rescue-vs-hallucination curve is strictly worse — it must trade one for the other) ⇒ H6
  established: atom-anchoring buys rescue without hallucination. If the feedback baseline matches both
  ⇒ H6 fails — anchoring is not the source of the advantage; report plainly. If MindsOS itself cannot
  hold both ⇒ H6 fails — mutual validation hallucinates even when atom-anchored; report as the key
  negative result.
- **Overall:** the paper's contribution = exactly the subset of {H1..H6} that clears its bar against the
  *strongest* baseline, with the per-sample evidence and the honest robustness limit (§7). A clean
  sweep is not required and not expected; a precise, audited map of where the compositional architecture
  helps and where it does not **is** the contribution.

## 10. Build order (fail-fast; no run before the pre-reg audit)

1. Generator v2 (square/pentagon + atom-level GT + the H6 hallucination-adversarial set) → freeze test `.npz`.
2. MindsOS genuine chain — numpy, in-sandbox first: learned atom detectors + **bidirectional joint
   inference** (atom↔component mutual validation, confidence = cross-level agreement) + named-atom
   expansion + induction side-exp. **First internal gate:** does joint inference beat single-level on
   the rescue set *without* hallucinating on the not-a-shape set (H6 in isolation)? If not, stop and
   report — the headline claim is falsified before any baseline.
3. Baselines (torch, Linux): CNN×2, concept-bottleneck, abstain/heatmap, **and the feedback/part-whole
   model** (the H2/H6 mechanism control).
4. Per-sample metric harness: accuracy/conf, data-efficiency, faithfulness, refuse/error, actionability,
   expansion ledger, **rescue + hallucination curves**, McNemar, tolerance/occlusion sweep.
5. **Pre-reg design audit** (adversarial subagent) → fix rigging → only then run.
6. Run (Linux for torch; numpy in-sandbox), per-stage heartbeat, detached.
7. Per-claim adversarial audit → honest verdict.

## 11. Amendment log
*(none yet — entries dated, recorded before the affected run.)*
