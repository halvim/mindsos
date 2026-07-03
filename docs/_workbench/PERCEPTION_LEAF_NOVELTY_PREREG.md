# Leaf-Learning NOVELTY — Pre-Registration (v2)

**Status: PRE-REGISTRATION (frozen before experiment code). v2** — tightened after a skeptical
pass-to-saturation (see §8 AM-1). Supersedes v1. Tests the *actual differentiator* of MindsOS
leaf learning, designed to be **falsifiable against a STRONG, fair ML baseline**, not a strawman.

**The differentiator (frozen):** a **probabilistic leaf restricted to producing a *named,
human-specified atom* via an inspectable composition**, chained into a hierarchy, with the
**irreducibility → request-atom → one-shot repair** loop. The headline-novel piece is that loop
(Claim 4); inspectability/localization/reuse (1–3) are the *mechanism that enables it* and are
reported as byproducts, not contested against baselines in v1 (they overlap the published
neuro-symbolic value proposition — not where our novelty lives).

**NOT the claim:** "structured/symbolic beats opaque" (known), or "interpretable but brittle"
(known tradeoff). The leaves are **learned and probabilistic**; that is why P0 (robustness parity)
is the load-bearing precondition.

**Anti-tuning.** Thresholds frozen here; change only by a dated amendment recorded before the
affected run. If a claim fails, fix the claim, not the test.

**Roles.** Builder = next chat. Auditor = subagent playing **"ML advocate"**: it actively tries to
make the baseline *pass* each contrast (stronger OOD, few-shot fine-tune, probing, attribution). A
claim stands only if a genuinely-helped baseline still cannot meet it.

---

## 0. P0 — the gating precondition (earned parity, not baked)

> **P0 — Parity-or-better under noise, with LEARNED leaves.** The MindsOS leaf-chain's in-vocab
> accuracy across the noise sweep must be **within 5 points of (or above) the strong CNN baseline**.
> **Crucial fairness constraint:** each leaf is a detector **learned from labeled examples** of its
> named atom (the atom *type* is human-given — point, line, polygon — but the chain is **NOT**
> handed the generator's parameters/templates). Otherwise the chain is just the generator's
> inverse and parity is meaningless.

If MindsOS is materially less accurate, or parity is only achievable by baking in the generator,
the experiment is **NULL** (we merely re-traded accuracy for inspectability). Report honestly.

**Novelty = P0 (earned parity) AND Claim 4** — properties a strong baseline cannot match *at parity*.

## 0.5 Scope (v1, minimal)
v1 contests novelty for **Claim 4 only**, gated by **P0**, against **one** strong baseline
(CNN + OOD/abstain + few-shot-repair). Claims 1–3 are **reported as byproducts** of the chain
(inspectable by construction; localization is the gap-naming mechanism), with **no separate
baseline contest** in v1. B-ae / B-probe and the 1–3 contests are **deferred to v2-of-the-study**.

## 1. Substrate (known generator — the only kind that can grade this)
2D shapes on a 64×64 grid from a **known atom hierarchy**, ground truth at every level:
`pixel → point → line-segment → polygon{rectangle, triangle}` and `circle` (curved/withholdable).
- **Controllable vocabulary:** the curved `arc` atom can be **withheld** (the 50-gon setup).
- **Near-miss cases (mandatory, PB-5):** include *slightly-curved* shapes (near-polygon) — not
  only clean circles — so honest-failure is tested in the hard regime (the §10 continuous
  blind-spot), not just the trivial far-OOD one.
- Noise σ ∈ {0, .05, .1, .2}, scale s ∈ [0.6, 1.6]. Reuse the Domain-A generator from
  `PERCEPTION_LEARNING_PREREG.md` where possible.

## 2. Systems under test
- **MindsOS leaf-chain (numpy, in-sandbox):** named probabilistic capacities, each producing a
  *named atom* via an inspectable composition (analysis-by-synthesis fit with per-invocation
  grounding_conf + decision_conf), **parameters learned from labeled examples**:
  `pixel→point` · `point→segment` · `segment→polygon` · plus the **irreducibility detector**
  (no within-tolerance composition of current atoms → REQUEST_ATOM, never fabricate).
- **Strong baseline B-cls (torch, user's Linux):** small CNN (data→class) with a **fair
  abstain/OOD head** (deep-ensemble disagreement or MC-dropout + max-softmax/Mahalanobis) **and**
  a **few-shot repair path** (fine-tune on k circle examples) for the Claim-4 contrast. Must be
  competitive (positive control below) or the comparison is void.

## 3. Claim 4 — honest failure → request-atom → one-shot repair (CENTERPIECE)
Withhold the curved atom; present circles **and near-curved shapes**.

**MindsOS MPs:**
1. **No fabrication:** rate of high-confidence polygon fits on curved inputs ≈ **0** (≤ 0.05),
   including near-miss (the hard case).
2. **Repair cost (measured, not binary, PB-3):** adding the `arc` atom (a new named leaf + its fit)
   changes **only that one rung — zero re-fit of point/segment/polygon leaves** — and lifts curved
   accuracy to ≥ **0.85**; **old-task (polygon) accuracy is provably unchanged** (retention = 1.0).
3. *(reported, not MP, PB-4)* **Structured gap:** the REQUEST_ATOM names the *curvature* residual
   (actionable: an oracle given it supplies the right primitive), vs a generic "low confidence."

**Fair baseline contrast (anti-strawman):** B-cls's OOD head **is expected and allowed** to flag
curved inputs (high OOD AUROC is fine — NOT the differentiator). The discriminators, frozen:
- **Repair cost:** B-cls repair requires fine-tuning (≥ k labeled circles) that **modifies the
  shared model** and incurs **measurable forgetting** of polygons (retention < 1.0) — vs MindsOS
  one-leaf-added, retention = 1.0. Report both costs (params/rungs changed; labeled examples
  needed; old-task retention).
- **Structured gap (reported):** an oracle given the baseline's output (OOD score / residual
  heatmap) cannot name *which missing primitive* (curvature) reliably, where MindsOS's request can.

## 3b. Claims 1–3 — reported byproducts (no v1 contest)
- **C1 inspectability:** each rung's output matches the generator's true intermediate (point/segment/
  polygon recovery) ≥ 0.90, read directly, no training. (Reported; the v2-study adds the B-probe contest.)
- **C2 localization:** a corruption injected at one level drops that rung's grounding_conf most ≥ 0.85.
- **C3 reuse:** a new concept reusing existing leaves (`house = rectangle ∧ triangle`) needs only a
  new top-level rule, **zero leaf re-fit**, ≥ 0.85. (This is the same mechanism as Claim-4 repair.)

## 4. Controls / anti-strawman
1. **Baseline-strength positive control (mandatory):** B-cls in-vocab accuracy must be competitive
   (≥ MindsOS − 5 pts); a win against a weak net is a FAIL of the test, not a result.
2. **P0 parity gate first** — if it fails (or only passes via a baked generator), STOP → NULL.
3. **ML-advocate audit** — auditor must try to defeat the Claim-4 contrast (stronger OOD; smarter
   few-shot/continual-learning repair to reduce forgetting; residual-based gap naming) before the
   claim is accepted.
4. Pre-registered thresholds; fixed seeds; ≥3 seeds.
5. **Show the leaves are learned/probabilistic** (the fits + confidences) so nothing reduces to
   hand-coded rules.

## 5. Experiment order (fail-fast, cheap-first — PB-7)
1. **MindsOS Claim-4 behavior in-sandbox** (numpy): no-fabrication on circles + near-miss; the
   request-atom signal; one-leaf repair + polygon retention. Cheap, high-signal, no baseline needed.
2. **P0 parity** + **baseline Claim-4 contrast** on Linux (CNN+OOD+few-shot-repair).
3. (deferred to v2-study) Claims 1–3 baseline contests (B-probe, attribution, compositional split).
Stop-and-fix on P0 / baseline-strength failure.

## 6. Environment
MindsOS chain = numpy, in-sandbox. Strong baseline = torch → **user's Linux machine** (no torch /
no data egress in sandbox; same pattern as `discovery_test.py`). JSON + seed per run; auditor
re-derives from thresholds.

## 7. Pre-committed reading
- **P0 fail / baked-generator** ⇒ NULL (accuracy↔inspectability tradeoff only). Report, don't spin.
- **P0 pass (earned) + Claim 4 pass** ⇒ the MindsOS leaf is a genuine alternative to opaque ML:
  comparable robustness **and** honest, structured failure with one-leaf repair at full retention —
  a property a strong baseline cannot match at parity. **Novelty demonstrated.** Claims 1–3 reported
  as the supporting mechanism.
- **Partial** ⇒ record exactly which property holds vs collapses to the known tradeoff.

## 9. Results

### Step 1 — MindsOS leaf-chain (numpy, in-sandbox) — **TRUSTWORTHY (audited 2026-06-28)**
Scripts: `leaf_novelty_generator.py` → `leaf_novelty_data.npz`; `leaf_novelty_mindsos.py` →
`leaf_novelty_mindsos_results.json`. Learned `tau=0.45, eps=2.4` (fit on TRAIN by accuracy),
per-leaf Platt on CAL; polygon vocab {3-gon,4-gon}+circle atom human-given (AM-2). 3 seeds.
- **P0 (MindsOS side):** in-vocab accuracy **0.961 ± 0.006** (σ0 .97 / σ.05 .98 / σ.1 .98 / σ.2 .90).
  Earned by **learned** leaves — audit confirmed **LEARNED-FAIR**, not baked (no generator params
  reach the chain; verified by grep + trace). P0 *gate* is comparative → needs the Linux CNN.
- **Claim 4 MP-1 (no fabrication, clean circles):** high-conf polygon-fabrication **0.0 ± 0.0**
  (0/60). Non-trivial: forced ≤4-gon "temptation" grounding mean **0.341**. Audit: the operative
  mechanism is the {3,4} vocabulary/K-routing (circles give K≥5); the IoU grounding is a weak
  secondary (rect ≈ circle ≈ 0.34) but independently also 0/60 ≥ 0.5. Both hold.
- **Claim 4 MP-2 (repair):** polygon retention **exactly 1.0** (0/480 verdicts flip — architectural:
  the arc leaf is a fallback that never overrides a polygon), curved accuracy **0.965 ± 0.014**,
  rungs_changed 1, leaves_refit 0. Repair uses 100 labeled CAL circles (counted).
- **Near-miss (REPORTED, AM-3):** request-atom (detected) curve **0.0 → 0.045 → 0.6 → 0.967** as
  curvature f∈{.04,.08,.15,.30}; blind-rate 1.0→0.05. The predicted P17 continuous blind spot,
  fully disclosed — no novelty claimed on near-miss.
- **C1 inspectability (reported):** vertex-count recovery 0.954. **C2 localization (reported):**
  grounding drops on rung corruption. **C3 reuse:** same mechanism as MP-2.

### Step 2 — strong CNN baseline (torch, Linux, run 5 final) — **COMPLETE (audited 2026-06-29)**
`leaf_novelty_baseline.py`, BatchNorm net, 3 seeds, same frozen `.npz`. P0 **0.967 ± 0.007** →
**positive control PASSES** (parity with MindsOS 0.961; contest VALID). Mahalanobis OOD **0.953**.
Repairs vs MindsOS (retention 1.0 / curved 0.965): shared-softmax all forget (R-full ret ≤0.10;
R-head/R-row ret ~0.79 but curved ≤0.30). The **strongest fair modular repair** (fresh raw-pixel
circle detector routing an untouched polygon head): detector AUROC 0.79→0.938→**0.995** (k5/20/100),
retention@curved≥0.85 = 0/0/**0.792 ± 0.092** (curved 0.86).

### FINAL VERDICT — independent ML-advocate audit (2026-06-29) — **NOVELTY NARROWED, reported honestly**
- **P0 parity: TRUSTWORTHY-PASS, earned.** CNN 0.967 vs MindsOS 0.961; learned-not-baked verified.
- **The headline "retention 1.0 vs 0.792" is a UNIT MISMATCH** (audit): MindsOS's "1.0" is a *zero-flip
  delta* (absolute polygon acc 0.954, architecturally unchangeable since the arc leaf is a fallback);
  the CNN's 0.792 is *absolute joint* accuracy capped by its polygon head. Matched units: **0.954 vs
  0.792** (gap 0.16), or routing-loss **~0.18 vs 0**.
- **Not a ROC-frontier impossibility.** At AUROC 0.995 the CNN's frontier permits ~0.97 routing-
  retention at ~0.96 curved; the reported 0.792 is the tail/cap effect at k=100, and AUROC is already
  saturated → the gap is **sample-efficiency + crisp-categorical routing**, NOT "a CNN cannot match."
- **No-fabrication is CONCEDED**, not a differentiator (CNN Mahalanobis OOD 0.953; OOD flagging is
  explicitly allowed, §3).
- **Mechanism is substrate-contingent.** MindsOS's zero polygon-mis-route comes from vertex-count K
  being perfectly discrete on this clean grid; it erodes under occlusion/deformation — and MindsOS
  *already* collapses in the near-miss regime (blind 1.0 @f.04) where K stops being crisp.
- **Verdict on conjunction-at-parity (AM-4):** holds **only as a NARROWER claim** — *data-efficient,
  crisp-symbolic-routing repair with a named/inspectable request-atom* — **NOT** "a property strong
  baselines cannot match at parity." Per the pre-reg's own AM-8/AM-9 pre-committed reading, this is
  the case where v1 novelty narrows to **gap-naming (PB-K), which v1 deliberately does not contest.**
  AM-10 eval-fix confirmed correct; no leakage; CNN given *more* train data (generous to baseline).

## 8. Amendment log

**AM-10 (2026-06-29, after run 4 — FRESH-detector result was a BUG, invalidated + fixed, re-run).**
Run 4 (folded fresh-detector) returned `repair_R_modular_FRESH_raw_detector_STRONGEST` detector
AUROC **0.48–0.51 (chance)** across k — impossible for a fresh CNN on the trivial circle-vs-polygon
task (the *frozen-feature* detector scored 0.925 on the same task). Root cause: `repair_modular_fresh`
scored the detector **without `.eval()`**, so BatchNorm used per-batch stats; with polygons and
circles passed as *separate* batches, BN normalised the class difference away → uninformative scores.
**Fix:** `det.eval(); poly_model.eval()` before scoring (running stats). All other paths route through
helpers that already set eval (P0 0.967, Mahalanobis 0.953, frozen R-modular AUROC 0.925/retention
0.27, R-full/head/row) — **those run-4 numbers remain valid**; only the FRESH variant was corrupted
and is re-run. No threshold changed. The decisive reading (AM-8/AM-9) is unchanged and now rests on
the *fixed* FRESH retention@curved≥0.85 vs MindsOS 1.0. Run-4 FRESH numbers void on record.

**AM-9 (2026-06-28, after Linux run 3 — competence gate PASSED; strongest fair-modular probe added).**
Run 3 (BatchNorm net) cleared the §4.1 control: **CNN P0 = 0.967 ± 0.007 vs MindsOS 0.961 — parity
holds, contest VALID.** Mahalanobis OOD 0.953 (a fair OOD head flags circles, as allowed). Repairs:
shared-softmax (R-full/R-head/R-row) all forget (retention ≤ 0.79, curved ≤ 0.30). The frozen-
backbone modular repair (R-modular) reached detector AUROC 0.925 @k100 but only retention 0.27 at
curved≥0.85 — i.e. it did NOT tie MindsOS. **Caveat (self-critique):** R-modular's detector sits on
features trained without circles, so it may under-represent curvature. The ML-advocate's strongest
modular repair is a **FRESH raw-pixel circle detector**, folded into `leaf_novelty_baseline.py` as
the 5th repair variant `repair_R_modular_FRESH_raw_detector_STRONGEST` (new learned circle machinery
routes; the deployed polygon model left UNTOUCHED; identical arch/seeds/harness as every variant).
The baseline now emits a per-stage + per-model epoch heartbeat so a long run is observably healthy.
**Pre-committed
reading (unchanged from AM-8):** if the FRESH modular CNN reaches retention ≈ 1.0 at curved-acc ≥
0.85, the repair-cost discriminator **collapses** → v1 novelty narrows to gap-naming (PB-K), report
honestly; if it stays materially < 1.0, the discriminator **survives even against the strongest fair
modular CNN.** No MindsOS threshold changed. Run-3 numbers stand on record.

**AM-8 (2026-06-28, pre-run — FAIR modular CNN repair added; the decisive falsifier of Claim 4).**
Self-critique (extends PB-D): MindsOS's retention=1.0 is **architectural** — its arc leaf is a
fallback that never overrides a polygon. Every CNN repair shipped so far (R-full/R-head/R-row)
shares one softmax, so a new circle output can always steal a polygon — a **strawman in MindsOS's
favour**. Added `repair_R_modular_separate_detector_FAIR`: a separate binary circle detector on
frozen features ROUTES the input; the 2-class polygon head is left byte-identical and consulted only
when the detector says "not circle" — i.e. the **same fallback architecture MindsOS uses**. Reports
the detector's separability (AUROC) and the **retention achievable at curved-acc ≥ 0.85** (matching
MindsOS's curved-acc). **Pre-committed reading:** if the modular CNN reaches retention ≈ 1.0 at
curved-acc ≥ 0.85, the repair-cost discriminator **collapses** — local repair = the *known
modularity* (Claims 1–3), NOT Claim 4 — and the v1 novelty narrows to **gap-naming** (named,
inspectable `REQUEST_ATOM("curvature")` vs an opaque scalar OOD score), which v1 explicitly does
**not** contest (PB-K). Report that honestly; do not spin a shared-softmax-only contrast as a win.
This strengthens the baseline (harder for MindsOS); no MindsOS threshold changed.

**AM-7 (2026-06-28, after Linux baseline run 2 — STILL sub-competent, BatchNorm added).** Run 2
(2-pool, 2160 imgs, 24 ep) still FAILED the control: CNN P0 = **0.776**; frozen-backbone retention
≈ **0.51** (= 2-class chance), i.e. the conv features did not even separate triangle from
rectangle — the diagnostic signature of an **under-trained** net, not a capacity ceiling. Standard
competent fix (no threshold touched): add **BatchNorm** (conv + penultimate), a **StepLR** schedule,
**35 epochs**, train n→220/cell (2640). Backbone BN set to eval under freeze so the frozen-backbone
repair reads stable stats. Still gates on S-pos before any Claim-4 reading. If a BN net STILL can't
clear the control, that is reported as "opaque ML cannot reach parity on this substrate at this data
scale" → P0 NULL/void per §7, not a MindsOS win. Run-2 numbers stand on record.

**AM-6 (2026-06-28, after Linux baseline run 1 — POSITIVE CONTROL FAILED, baseline strengthened).**
Run 1 of `leaf_novelty_baseline.py` FAILED the §4.1 positive control: CNN P0 = **0.703** (flat
~0.70 even at σ=0) vs MindsOS 0.961, and OOD AUROC 0.351 (< 0.5). Per §4.1 ("a win against a weak
net is a FAIL of the test") + §5 (stop-and-fix on baseline-strength failure), run 1 is **VOID — not
a MindsOS win** and no verdict is read. Diagnosed under-powering (NOT threshold tuning): (1) three
2×2 max-pools collapse a 1-px outline to 8×8, erasing the triangle-vs-rectangle corner signal — cut
to **two pools** (→16×16) + more channels; (2) only 480 training images — give the CNN a **large
generated train set** (test set unchanged = the frozen npz, so P0 stays comparable); (3) 18 epochs →
**24**; (4) max-softmax OOD replaced/augmented with **Mahalanobis on penultimate features** (the
pre-reg's allowed stronger OOD). These are standard competent-baseline choices, applied to make the
contest fair to opaque ML; **no MindsOS threshold or any P0/Claim-4 bar changed.** Run-1 numbers
stand on record. Re-run gates on the same S-pos control before any Claim-4 reading.

**AM-5 (2026-06-28, pre-Linux-run — baseline strengthened per adversarial audit).** The in-sandbox
ML-advocate audit found the original baseline gave the opaque model a *weak* repair (its
frozen-backbone head was not warm-started and re-learned polygon rows from scratch), risking a
**strawman in MindsOS's favor**. Per the anti-strawman rule (§4.3), the baseline gains a third,
**stronger** repair variant `repair_R_row_frozen_warmstart_BEST`: frozen backbone + the trained
polygon head rows copied in and FROZEN + a single new trainable circle logit. This is the ML
advocate's best shot at matching MindsOS's exact-1.0 retention. **The decisive Claim-4 repair
comparison is now this variant vs MindsOS retention=1.0.** This strengthens the baseline (makes the
contest harder for MindsOS); no MindsOS threshold changed. Pre-committed reading: if the row-frozen
head still cannot reach exactly 1.0 polygon retention, the repair-cost discriminator stands; if it
*can*, the v1 novelty narrows to gap-naming (named atom vs OOD scalar), which v1 leaves undefended
(PB-K) — report that honestly, do not spin. (Recorded before the Linux baseline run.)

**AM-2 (2026-06-28, pre-build — operational "learned, not baked").** §0 made P0's NULL hinge
on "learned leaves, not a baked generator" without defining either. Frozen definition: a leaf is
**learned** iff (i) every decision threshold (foreground-intensity cut, collinearity tolerance,
polygon-closure tolerance, vertex-count split) is **fit from a labeled TRAIN split disjoint from
test**, and (ii) each leaf's `grounding_conf`/`decision_conf` is **per-leaf Platt-calibrated on a
held-out CAL split** (the P14 contract). The geometric *proposal* (least-squares segment/polygon/
circle fit) is a fixed inference algorithm whose **atom vocabulary is human-given** (allowed by
P2/P9); what is learned is the calibration + tolerances. **The generator's per-instance parameters
(which shapes, vertices, radii) are NEVER passed to the chain** — only the labeled rendered images
+ class/level labels. The ML-advocate auditor **adjudicates whether this is "baked"**; if the
auditor rules the geometric core is effectively the generator inverse, the result is **NULL**
(reported, not spun). No threshold relaxed; this fixes a missing definition.

**AM-3 (2026-06-28, pre-build — MP-1 scope vs the chat's own doctrine).** §3 MP-1 demanded "no
high-conf polygon fit on curved inputs, *including near-miss*." This **contradicts** the audited
cross-family/P15/P17 finding that the **near-vocabulary blind spot is continuous-substrate-specific
and irreducible at fixed vocab+resolution** — on sub-tolerance-curved shapes MindsOS is *expected*
to fabricate, and the numpy chain has no P17 multi-resolution descent. Frozen correction: **MP-1
(no-fabrication, ≤0.05) is gated on CLEAN circles only.** Near-miss (slightly-curved superellipse)
inputs remain **mandatory in the dataset** (PB-5 honored) but are **REPORTED, not gated** — they
are the honest-limit boundary, and the chain being blind there is a *predicted* result per P17, not
a failure. v1 makes **no novelty claim on near-miss**. No threshold relaxed (0.05 unchanged); scope
of the existing bar narrowed to the regime where it is a fair fight.

**AM-4 (2026-06-28, pre-build — novelty verdict = conjunction-at-parity).** v2's own demotions
(PB-2: Claims 1–3 overlap published neuro-symbolic work; PB-4: gap-naming demoted) risk hollowing
Claim 4 down to "local one-leaf repair = modularity," which the spec concedes is known. Frozen
reading: **the contested novelty is the CONJUNCTION at earned parity** — (no-fabrication on clean
circles) ∧ (localized one-leaf repair, zero re-fit, retention=1.0) ∧ (repair target is a *named,
inspectable* atom) — **achieved without sacrificing in-vocab accuracy (P0)**. No single MP is the
claim; opaque ML cannot match the conjunction *at parity* even if each piece individually overlaps
prior work. Claims 1–3 carry internal sanity thresholds but are **reported, NOT gating**; only
**P0 ∧ Claim 4** decide the verdict (§0/§7). Caveat recorded (PB-K): the recon-AE that PB-4 cited
to demote gap-naming is **deferred from v1**, so the "AE residual ≈ our gap-naming" equivalence is
*asserted, not demonstrated* here.

**AM-1 (2026-06-28, v1→v2 redesign, pre-build).** Skeptical pass-to-saturation (4 passes, 1
reversal at P2) tightened v1: (PB-1) leaves must be **learned from data**, no baked generator, or
P0 is meaningless; (PB-2/P2 reversal) **Claim 4 is the sole v1 novelty contest** — Claims 1–3
overlap published neuro-symbolic work, kept as **reported byproducts / the enabling mechanism**,
not cut; (PB-3) repair is a **measured cost** (rungs changed + labeled examples + old-task
retention), not a binary; (PB-4) "structured gap" **demoted to reported** (a recon-AE also yields a
residual map); (PB-5) **near-miss cases mandatory** so honest-failure isn't trivial; (PB-6) scope
cut to **one baseline**, B-ae/B-probe deferred; (PB-7) build **MindsOS half in-sandbox first**, CNN
contrast second. No thresholds relaxed; the change sharpens falsifiability and removes strawman risk.
