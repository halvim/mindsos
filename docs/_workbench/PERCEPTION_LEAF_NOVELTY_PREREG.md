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

## 8. Amendment log
**AM-1 (2026-06-28, v1→v2 redesign, pre-build).** Skeptical pass-to-saturation (4 passes, 1
reversal at P2) tightened v1: (PB-1) leaves must be **learned from data**, no baked generator, or
P0 is meaningless; (PB-2/P2 reversal) **Claim 4 is the sole v1 novelty contest** — Claims 1–3
overlap published neuro-symbolic work, kept as **reported byproducts / the enabling mechanism**,
not cut; (PB-3) repair is a **measured cost** (rungs changed + labeled examples + old-task
retention), not a binary; (PB-4) "structured gap" **demoted to reported** (a recon-AE also yields a
residual map); (PB-5) **near-miss cases mandatory** so honest-failure isn't trivial; (PB-6) scope
cut to **one baseline**, B-ae/B-probe deferred; (PB-7) build **MindsOS half in-sandbox first**, CNN
contrast second. No thresholds relaxed; the change sharpens falsifiability and removes strawman risk.
