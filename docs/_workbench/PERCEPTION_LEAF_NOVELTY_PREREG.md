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

### Step 2 — strong CNN baseline (torch, user's Linux) — **PENDING (authored, unrun)**
`leaf_novelty_baseline.py` (deep-ensemble OOD head + 3 repair modes incl. the audit-mandated
row-frozen warm-started head, AM-5). Loads the same `.npz`. Run on Linux → fills the P0 parity gate
+ the decisive repair-cost contrast. **Pre-committed reading stands (§7 + AM-4 + AM-5).**

### Audit (independent ML-advocate, in-sandbox, 2026-06-28)
MindsOS half **TRUSTWORTHY-PASS** (P0-side, MP-1, MP-2, learned-not-baked, clean anti-tuning
process). Two risks to the conjunction-at-parity (AM-4) flagged for the Linux run: (1) P0 could
fail *either* direction (CNN ≫ MindsOS → NULL; or within 5 → pass); (2) the strengthened row-frozen
head (AM-5) might reach exactly 1.0 retention, narrowing novelty to gap-naming. Both are decided on
Linux, honestly, per the frozen readings.

## 8. Amendment log

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
