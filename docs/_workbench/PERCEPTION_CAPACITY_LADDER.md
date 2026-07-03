# Perception Capacity Ladder — design log

**Started 2026-07-01. Supersedes the Study-2 *implementation* approach (not its study design).**

## 0. Why this exists (the pivot)
The first Study-2 implementation (blob classifier + edge-completion + gates 3a/3b, in
`leaf_validation_mindsos.py` / `leaf_validation_complete.py`) was **scaffolding and is discarded**.
A skeptical pass found: hand-coded geometry (the Study-1 sin), design-level **test leakage**, two
incoherent classifiers, and a rigged internal comparison. The honest, unified re-build collapsed to
~0.55. Conclusion: build perception **as a genuinely-grounded, staged capacity ladder — one capacity
at a time, each frozen before the next builds on it.**

The **study design is unchanged** and still frozen: `PERCEPTION_LEAF_VALIDATION_PREREG.md` §0–§10 +
amendments **AM-1..AM-16** (H1–H6, baselines, metrics, two substrates, supervision ledger, H6 mixed
stream, etc.). What changed is only *how MindsOS perception is implemented* underneath it.

## 1. The ladder
```
pixel  (given substrate, P2)
  └─ capacity 2  (grounding):  pixel -> structural-pixel     DETERMINISTIC.  COMMITTED.
       └─ capacity 2.1:        structural-pixels -> segment   FIRST learned composition.  NEXT.
            └─ 2.2 segment -> vertex,  2.3 -> shape, curvature atom, ...  (later)
```
Build/freeze one rung at a time. A higher rung imports the lower one and **never edits it**.

## 2. Capacity 2 — LOCKED + COMMITTED
- **Artifact:** `capacity2_filter.py` (`structural_pixels(img, tau=0.3)`, numpy-only, standalone)
  + `leaf_validation_generator.py`. Branch `perception-capacity2`. **Frozen forward/inverse pair.**
- **What it is:** a structural-pixel = a location where **local contrast magnitude > tau**. Contrast,
  **not** absolute intensity/color (decisive case: a filled shape's bright interior is flat → no
  contrast → correctly no structural-pixel; only the boundary fires).
- **Deterministic, not learned.** Once noise-judgment is removed (below), nothing is left to learn — a
  learned MLP merely (imperfectly) approximated the deterministic contrast label. Learning lives at
  composition, not at the given-substrate boundary.
- **No noise judgment (P1).** Permissive: it also lists noise structural-pixels. Signal-vs-noise is
  **not** a capacity-2 decision — it is decided later by whether a pixel composes into a segment.
- **"point" ≠ derived atom.** As defined, a structural-pixel is a *filtered pixel* — a **selection** of
  the given atoms, not a *composition* (P3). So capacity 2 is **grounding** (a real, if trivial,
  capacity: structure vs flat-nothing). The **first genuine derived atom is the segment**.
- **Two-way pair (analysis-by-synthesis).** generator = forward (structure→pixels); filter = inverse
  (pixels→structural-pixels). Recovery test = inverse(forward)=input.
- **Validation (recovery, held-out `dev`):** clean outline **exact (recall 1.0 / precision 1.0)**;
  clean filled ~0.93 (boundary-pixel edge effects, not real misses); σ0.2 recall **1.0** / precision
  **0.14** (noise adds structural-pixels — expected, permissive).

## 3. Principles locked this chat (reuse up the ladder)
- **Grounding is a capacity** (distinguishing structure from nothing), even when trivial.
- **Learning lives where there is genuine ambiguity = composition**, not the pixel boundary.
- **Corners / orientation are higher-level.** A corner = two segments meeting (2.2). Orientation is a
  *segment* property, not a point property. Forcing orientation onto points created a fake "corner
  problem" and made mining backfire (it drilled on ambiguous corner labels).
- **Confidence = attention; disambiguation is cross-level.** A shaky low-level detection is resolved by
  higher-level context (does it compose?). It cannot be resolved at a single isolated level — needs the
  ladder to have more than one rung.
- **Analysis-by-synthesis verification needs STRUCTURE to ground against.** Point-level verification was
  built (verify_local / verify_global) and **empirically produced no useful signal** — a single point is
  too impoverished to reconstruct. Verification belongs at **segments and up**.
- **Adversarial hard-example mining** (generator hunts the capacity's failures) is the *safe* adversarial
  form (never let the true generator learn/cheat); it is useless for a deterministic capacity and needs
  learnable content + genuinely-learnable failures (not ambiguous labels).

## 4. Capacity 2.1 (NEXT PHASE) — what it must do
- **Input:** the structural-pixels from **frozen** capacity 2 (import `structural_pixels`; do not edit).
  Train on capacity 2's **real (noisy) output**, not on clean pixels.
- **Output:** named **segment** atoms — a segment = a straight run of collinear structural-pixels,
  **compressing** the redundant run into a line (endpoints + "straight"). This is the first
  *composition*, so here the **learned-probabilistic-atom** doctrine (P14, calibrated confidence)
  actually applies.
- **Noise falls out here:** noise structural-pixels don't line up into segments → dropped. That is where
  P1's deferred signal-vs-noise judgment gets paid.
- **Verification becomes real here:** a *wrong segment* fails to reconstruct the pixels → the two-way
  loop finally tests something. Revisit the local/global verifier idea with actual structure.
- **Open questions for 2.1 R0:** how "learned" (fixed collinear-grouping proposal + learned
  segment-validity + calibration? vs heavier) — decide before building; segment endpoints/arity; a
  correctness/grounding metric that tests *segment faithfulness* (the point-level AUROC-vs-correctness
  metric conflated faithfulness with meaning — re-derive for segments).

## 5. Discipline (locked)
- **Communication:** say what is needed concisely, enough context to understand/decide, not too long.
- **Never `git add -A` / `git add .`** — stage explicit paths only. Git ops on the **Mac** only, never
  from the sandbox.
- **Pair-exec:** Cowork builds; Mac commits + pushes; Linux gates. numpy runs in-sandbox; torch on Linux.
- **Test hygiene:** tune on a `dev` split; the frozen `test` set is read once, never during design.
