# Perception Principles

**Scope:** MindsOS-GENERAL. Foundational principles that govern *anything* MindsOS perceives —
not owned by any demo or plan; plans and builds **use** them. Examples use vision/pixels
because that is where they surfaced (the Bongard-LOGO faithful diagnostic, 2026-06-26), but the
principles are substrate-neutral.

**Provenance.** Part I (P1–P11) is the converged doctrine handed off from the bongard demo
chat (`projects/bongard_demo/PERCEPTION_PRINCIPLES.md`, Part A) and landed here verbatim. Part
II (P12–P17) records the probabilistic/learned extensions developed and empirically validated
in a core perception chat (2026-06-27); the full pre-registration, experiments, and five
independent adversarial audits are in `docs/_workbench/PERCEPTION_LEARNING_NOTES.md` +
`PERCEPTION_LEARNING_PREREG.md`, and the confidence contract is ADR-0191.

---

## Part I — Foundational principles (P1–P11, converged)

### P1 — Grounding (no ungrounded input)
All perception is composition of **known atoms**. There is no ungrounded input: the raw
signal is always known atoms (e.g. pixels). **"Noise" is a pattern of known atoms for
which no meaningful higher composition is (yet) recognized** — not "ungrounded." To
perceive = to find a composition over known atoms that is meaningful *for the task*;
the absence of such a composition is noise. (Same grounding test as ontology
concept-invention: meaning requires grounding, not statistical pattern.)

### P2 — Fundamental atoms are EXOGENOUS (human-given), never self-acquired
A system perceives only with the atoms it has been **given**. A *fundamental* atom is
the irreducible floor — not a composition — so the system cannot derive or invent one.
New fundamental atoms (pixel, bit, and any new primitive) are **created and added by an
external intelligence** (humans, relative to the machine). Atoms are substrate-specific
and supplied across the boundary: computers can't natively use human neural atoms;
humans can't natively use pixels — each was given to the other side by an external
intelligence.

### P3 — Two senses of "atom": fundamental (exogenous) vs derived (endogenous)
- **Fundamental atoms** — the irreducible floor; only humans add them (P2).
- **Derived / promoted atoms** — a *composition* recognized at level N, promoted to be
  treated as a single **element** at level N+1 (the recursive metagraph / graph-of-graphs).
  These the system makes itself.
Do not conflate: "new fundamental atoms need a human" is true; "every new perceptual unit
needs a human" is false (derived atoms are endogenous).

### P4 — The system's role re: fundamental atoms = DETECT + REQUEST + COMPOSE (not acquire)
When no composition of its current atoms can express/separate a phenomenon (**demonstrated
irreducibility** — a solve-failure), the system has hit the limit of recursive
combination. The correct response is to **signal that a new fundamental atom is needed**
(a human decision) — NOT to fabricate one (which forces noise into a bad fit; cf. the
~50-sided polygons our perception produced on raw Bongard-LOGO). When a human **adds** a
new atom, it **triggers an internal capability** to attempt to perceive inputs using it.
Division of labor: detect the gap (system) → supply the atom (human) → compose with it
(system).

### P5 — New perception = recursive composition of known atoms (the default)
The overwhelming majority of new perception is route (b): compose known atoms.
`point → line (aligned points) → angle (meeting lines) → rectangle (parallel ∧
perpendicular ∧ closed lines) → …`. A composed object can serve different functional
**ROLES** by task — a line *used as* a boundary / division / reference. Roles are
relational interpretations, not new atoms.

### P6 — Atoms stay MINIMAL and ORTHOGONAL; richness comes from COMBINING capacities
Do NOT pack everything into a fat atom. Each atom is one thing; each extraction or
combination is a separate capacity (a DataState transition):
`pixel→point` (position), `pixel→intensity` (brightness), `point→line` (aligned points),
`point + intensity → edge` (an intensity boundary localized at points). A point does
**not** carry intensity — intensity is its own perception, combined with points only
*when* an edge is needed (P8 laziness). The `point+intensity→edge` combine is co-indexed
by position (the intensity *at* those points), but that binding is just the shared pixel
grid, not an attribute on the point. *Current-system gap:* we have `pixel→point` but
discard intensity at threshold (no `pixel→intensity`) and have no combination capacities.

### P7 — Concepts = substrate-agnostic relational templates (scale-relative, tolerance-bounded)
A concept is a relation over elements, independent of what the elements ARE. "Rectangle"
= parallel ∧ perpendicular ∧ closed, over WHATEVER elements (pixels / glyphs / objects),
**at the scale where the template holds within tolerance** ("a rectangle from far
enough"). The same recognizer applies **recursively** up the hierarchy: a structure
recognized at level N is an element at level N+1. **Tolerance is scale-coupled** (coarser
resolution widens the parallel/90° tolerances). Scale/resolution is constitutive of
perception, not a nuisance.

### P8 — Top-down COGNITION: engage lower atom layers only when needed
Two distinct modes, do not conflate them:
- **Bootstrapping (bottom-up, once):** a system builds up from atoms to *acquire* a
  concept/layer. Learning runs bottom-up.
- **Cognition (top-down, runtime):** to *use* what it has, the system starts at the
  **highest layer that is meaningful for the task** and **descends to lower atom layers
  only when necessary** to understand something. No need to understand bits if pixels
  suffice; no pixels if "button" suffices.
Descent **trigger** = the current layer is insufficient for the task (ambiguous / template
fails within tolerance / finer detail required). This is lazy, on-demand evaluation, and
it **bounds** level/scale selection (start high, descend on need — do not search all
scales).

### P9 — Learning at the perceptual boundary = learning an atom-COMPOSITION, not weights
You can only extract what you have atoms for — the atom vocabulary is the necessary bias;
without a bias, nothing can be extracted. A "learned extractor" is acceptable **iff its
output is a known atom** and its mechanism is an **inspectable composition/identification
of atoms**, not opaque weights. So "no ML at the leaf" is too strong; the correct rule is
**"no ungrounded output at the leaf, and the learned thing must be an atom-composition."**
*(See P12–P13 for the refined, validated form of this rule.)*

### P10 — These principles ARE the MindsOS L3 model (the implementation bridge)
The arrows above are not new machinery: **atoms = DataStates; perceptions = capacities
(DataState→DataState transitions); the perception hierarchy = a graph of capacities over
DataStates = L3 + the metagraph (graph-of-graphs).** Therefore:
- a **new fundamental atom** = a new DataState **added by a human** (exogenous, P2); adding
  it **triggers** the system to attempt compositions that involve it;
- a **new perception** = a new **capacity** combining existing DataStates (endogenous, P5);
- a **derived/promoted atom** (P3) = a composite capacity's output promoted to an element
  at the next level.

### P11 — Adding a fundamental atom = (DataState + capacity), at the signal floor
You never add a bare DataState — there is no point adding an atom without saying what it
is *for*. The unit of human-addition is a **new DataState + a capacity that wires it into
the existing atom graph** (and thus the DataState on the other end). Example: to deepen
vision below pixels, a human adds `subpixel_{r,g,b}` **and** the capacity
`(r,g,b)→pixel` — connecting the new atoms to one the system already has.

Three consequences:
- **The floor is downward-extensible.** "Most fundamental atom" is not absolute; humans can
  add atoms *below* the current floor (subpixels under pixel), deepening the grounding and
  enabling finer concepts (color, sub-pixel edges) the system could not perceive before.
- **"Fundamental" is a movable status, not an identity.** Adding `subpixel→pixel`
  reclassifies **pixel from fundamental to derived** — now *produced* by a capacity, not
  *given*. Non-disruptive: every capacity that consumed the pixel DataState still does; it
  just has an upstream producer now. The only invariant "fundamental" = the *current
  sensory floor*. (Implementation: "fundamental" = a DataState with no `PRODUCES` edge —
  a computed status, not a stored flag.)
- **Signal-bounded.** You can only add atoms the raw signal actually contains — subpixels
  are addable only because the RGB data is physically present. Humans add the **reading**
  (atom + capacity) of structure already in the signal, never new data.

Non-disruption is P8 in action: deepening the floor does not perturb higher cognition —
subpixels are simply never engaged when interpreting a line.

---

## Part II — Probabilistic & learned perception (P12–P17, validated 2026-06-27)

These refine P9's treatment of learned/probabilistic leaves. Each was pre-registered and
tested under independent adversarial audit; status is stated honestly. Full evidence:
`docs/_workbench/PERCEPTION_LEARNING_{NOTES,PREREG}.md`. Confidence contract: **ADR-0191**.

### P12 — Probabilistic ∝ input under-determination *(validated)*
A capacity is probabilistic in proportion to how much its declared input fails to fix its
output. Two causes: **under-specified input** (fix by widening the input — e.g. `pixel` →
`pixel-neighborhood`) vs **irreducible ambiguity** (accept and quantify). Diagnose by the
marginal error-reduction from widening the input.

### P13 — A groundable probabilistic capacity is a verified round-trip *(validated)*
A learned/probabilistic capacity is groundable only as half of a **(proposer, critic)
pair** — `A <-> B` (sugar for two directional capacities {A→B, B→A}), not a bare `A -> B`.
The `<->` is **fidelity-graded** (reconstruction within a scale-coupled tolerance, P7),
its confidence is the **weaker direction**, and only the **reconstructive** flavor (anchors
at a known atom) truly grounds — a discriminative-only critic is secondary/capped. This is
P9 made precise: *no ungrounded output at the leaf; weights are fine, but only at the floor,
producing atoms — no level-skipping.*

### P14 — Confidence is two numbers, not one *(validated on two substrates → ADR-0191)*
*Grounding* confidence (reconstruction fidelity — "is the output explainable by known
atoms") and *decision* confidence (peakedness over valid alternatives — "which one") are
**independent axes**; a single number is dishonest under irreducible ambiguity. Both are
**per-invocation output**, never learned capacity state (preserves L3 fixed-not-learned).
The **decision axis must be per-capacity calibrated** before any cross-capacity use (raw
margins are incommensurable — empirically falsified at AUROC 0.78; per-capacity Platt
calibration → 0.88/0.91, margin-driven). Calibration lives offline-at-registration or in
`learned-parameters` via the promotion loop. *Validated on 1D signals + 2D shapes —
substrate-neutral.*

### P15 — Grounding is reconstruction to the floor, and is novelty-distance-relative *(revised)*
Grounding = end-to-end reconstruction of the raw signal from the interpretation
(analysis-by-synthesis to the fundamental floor, the single anchor). Run as a **test**
(bootstrap + on-demand B5 descent) with a cheap per-level **proxy** at runtime.
**Path corollary:** a single bare `->` link severs grounding for everything above it.
**Empirically: grounding confidence is novelty-distance-relative, not absolute** — it
reliably flags *far* novelty and is **blind to near-vocabulary novelty** (substrate-
independent). Therefore grounding is characterized as an AUROC-vs-novelty-distance curve,
never a single threshold; near-vocabulary novelty is handled by P17, not by a grounding
threshold.

### P16 — Decomposition by reuse; reuse-driven propagation shown, unsupervised discovery open
Decompose for **reuse** (MDL), not purity: split out an intermediate atom iff it is shared
by ≥2 consumers (= P3 promotion). **Validated:** reuse pressure (downstream consumers)
determines which factor a bottleneck keeps — it encodes the *used* intermediate while a pure
reconstruction bottleneck discards it and keeps the high-variance nuisance instead. **Open:**
genuine *unsupervised* discovery of a novel atom (from *lossy* consumers + a nameability
gate) is **not yet established** — specced in `PERCEPTION_DISCOVERY_TEST_SPEC.md` for a
torch environment. Distinguish "reuse-driven propagation" (shown) from "unsupervised
discovery" (open).

### P17 — Near-miss handling is architectural, not a statistical detector *(design-validated)*
The P15 near-vocabulary blind spot **cannot** be closed by any generic residual statistic
(magnitude is intrinsically blind — a 10% deviation absorbed by the best-fit atom even at
near-zero noise; structure does no better). Detection requires **both** a feature *tuned to
the specific deviation* — which *is* the finer atom (P11) — **and** the deviation *above the
noise floor*, which **descent to finer resolution (P8/B5)** provides. Operationally: a
*borderline-grounding* zone is the **B5 descent trigger**; descend and re-test with
deviation-specific capacities; if still borderline at the finest resolution, emit the **B4
request-atom** signal or honestly abstain. The blind spot is **irreducible at fixed
vocabulary + resolution — by design.**
