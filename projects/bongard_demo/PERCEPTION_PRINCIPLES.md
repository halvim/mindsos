# MindsOS Perception Principles — Core Hand-off

**Scope:** MindsOS-GENERAL. Foundational principles that govern *anything* MindsOS
perceives — not owned by any demo or plan; plans and builds **use** them. Examples use
vision/pixels because that is where they surfaced (the Bongard-LOGO faithful diagnostic,
2026-06-26), but the principles are substrate-neutral.

**This document is a hand-off to a CORE chat.** It has three parts:
- **Part A — Principles (P1–P11).** Durable doctrine. **Lift this verbatim into core docs
  on `main`** (`docs/concepts/perception-principles.md`). The bongard plan only references it.
- **Part B — Core asks.** Concrete implications for the core (`mindsos_*`), actionable.
- **Part C — Evidence.** The grounded Bongard-LOGO case study that motivated all of this.

**Why staged here:** the discussion ran in the `demo/bongard` worktree, and a demo must not
author core docs on `main`. The core chat lands Part A; Parts B–C are guidance + motivation.

---

## Part A — Principles (P1–P11)

---

## P1 — Grounding (no ungrounded input)
All perception is composition of **known atoms**. There is no ungrounded input: the raw
signal is always known atoms (e.g. pixels). **"Noise" is a pattern of known atoms for
which no meaningful higher composition is (yet) recognized** — not "ungrounded." To
perceive = to find a composition over known atoms that is meaningful *for the task*;
the absence of such a composition is noise. (Same grounding test as ontology
concept-invention: meaning requires grounding, not statistical pattern.)

## P2 — Fundamental atoms are EXOGENOUS (human-given), never self-acquired
A system perceives only with the atoms it has been **given**. A *fundamental* atom is
the irreducible floor — not a composition — so the system cannot derive or invent one.
New fundamental atoms (pixel, bit, and any new primitive) are **created and added by an
external intelligence** (humans, relative to the machine). Atoms are substrate-specific
and supplied across the boundary: computers can't natively use human neural atoms;
humans can't natively use pixels — each was given to the other side by an external
intelligence.

## P3 — Two senses of "atom": fundamental (exogenous) vs derived (endogenous)
- **Fundamental atoms** — the irreducible floor; only humans add them (P2).
- **Derived / promoted atoms** — a *composition* recognized at level N, promoted to be
  treated as a single **element** at level N+1 (the recursive metagraph / graph-of-graphs).
  These the system makes itself.
Do not conflate: "new fundamental atoms need a human" is true; "every new perceptual unit
needs a human" is false (derived atoms are endogenous).

## P4 — The system's role re: fundamental atoms = DETECT + REQUEST + COMPOSE (not acquire)
When no composition of its current atoms can express/separate a phenomenon (**demonstrated
irreducibility** — a solve-failure), the system has hit the limit of recursive
combination. The correct response is to **signal that a new fundamental atom is needed**
(a human decision) — NOT to fabricate one (which forces noise into a bad fit; cf. the
~50-sided polygons our perception produced on raw Bongard-LOGO). When a human **adds** a
new atom, it **triggers an internal capability** to attempt to perceive inputs using it.
Division of labor: detect the gap (system) → supply the atom (human) → compose with it
(system).

## P5 — New perception = recursive composition of known atoms (the default)
The overwhelming majority of new perception is route (b): compose known atoms.
`point → line (aligned points) → angle (meeting lines) → rectangle (parallel ∧
perpendicular ∧ closed lines) → …`. A composed object can serve different functional
**ROLES** by task — a line *used as* a boundary / division / reference. Roles are
relational interpretations, not new atoms.

## P6 — Atoms stay MINIMAL and ORTHOGONAL; richness comes from COMBINING capacities
Do NOT pack everything into a fat atom. Each atom is one thing; each extraction or
combination is a separate capacity (a DataState transition):
`pixel→point` (position), `pixel→intensity` (brightness), `point→line` (aligned points),
`point + intensity → edge` (an intensity boundary localized at points). A point does
**not** carry intensity — intensity is its own perception, combined with points only
*when* an edge is needed (P8 laziness). The `point+intensity→edge` combine is co-indexed
by position (the intensity *at* those points), but that binding is just the shared pixel
grid, not an attribute on the point. *Current-system gap:* we have `pixel→point` but
discard intensity at threshold (no `pixel→intensity`) and have no combination capacities.

## P7 — Concepts = substrate-agnostic relational templates (scale-relative, tolerance-bounded)
A concept is a relation over elements, independent of what the elements ARE. "Rectangle"
= parallel ∧ perpendicular ∧ closed, over WHATEVER elements (pixels / glyphs / objects),
**at the scale where the template holds within tolerance** ("a rectangle from far
enough"). The same recognizer applies **recursively** up the hierarchy: a structure
recognized at level N is an element at level N+1. **Tolerance is scale-coupled** (coarser
resolution widens the parallel/90° tolerances). Scale/resolution is constitutive of
perception, not a nuisance.

## P8 — Top-down COGNITION: engage lower atom layers only when needed
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

## P9 — Learning at the perceptual boundary = learning an atom-COMPOSITION, not weights
You can only extract what you have atoms for — the atom vocabulary is the necessary bias;
without a bias, nothing can be extracted. A "learned extractor" is acceptable **iff its
output is a known atom** and its mechanism is an **inspectable composition/identification
of atoms**, not opaque weights. So "no ML at the leaf" is too strong; the correct rule is
**"no ungrounded output at the leaf, and the learned thing must be an atom-composition."**

## P10 — These principles ARE the MindsOS L3 model (the implementation bridge)
The arrows above are not new machinery: **atoms = DataStates; perceptions = capacities
(DataState→DataState transitions); the perception hierarchy = a graph of capacities over
DataStates = L3 + the metagraph (graph-of-graphs).** Therefore:
- a **new fundamental atom** = a new DataState **added by a human** (exogenous, P2); adding
  it **triggers** the system to attempt compositions that involve it;
- a **new perception** = a new **capacity** combining existing DataStates (endogenous, P5);
- a **derived/promoted atom** (P3) = a composite capacity's output promoted to an element
  at the next level.

## P11 — Adding a fundamental atom = (DataState + capacity), at the signal floor
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
  sensory floor*.
- **Signal-bounded.** You can only add atoms the raw signal actually contains — subpixels
  are addable only because the RGB data is physically present. Humans add the **reading**
  (atom + capacity) of structure already in the signal, never new data. This is what keeps
  additions grounded rather than invented, and bounds what "add a fundamental atom" means:
  teach the system to read what is there but unread.

Non-disruption is P8 in action: deepening the floor does not perturb higher cognition —
subpixels are simply never engaged when interpreting a line.

---

## Part B — Core asks (concrete implications for `mindsos_*`)

These follow from Part A. None require a new paradigm — perception **is** L3 (P10).

- **B1 — Encode the perception seam as P9.** The current grounding leaf documents a future
  "neural leaf swap." Constrain it in core: a learned leaf MUST emit a **known atom
  DataState** (grounded), never an opaque embedding/label. Rule: *no ungrounded output at
  the leaf, and the learned thing must be an inspectable atom-composition.*

- **B2 — Keep perception atoms minimal + orthogonal; richness via combination (P6).** The
  atom set should be small orthogonal DataStates (e.g. `point`=position, `intensity`=
  brightness) wired by explicit combination capacities (`point + intensity → edge`). Do
  NOT fold attributes into fat atoms. Concretely, vision needs at least: `pixel→point`,
  `pixel→intensity`, and a `point+intensity→edge` combine — the demo has only `pixel→point`
  and discards intensity.

- **B3 — First-class "add fundamental atom" operation (P11).** Support registering a new
  fundamental DataState **together with** a capacity that wires it into the existing graph
  (the unit is never a bare DataState). Adding it should **trigger** the system to attempt
  compositions involving it (the "atom → try to perceive with it" loop). Honor the floor
  being downward-extensible (`subpixel→pixel` reclassifies `pixel` to derived,
  non-disruptively) and signal-bounded (only atoms the raw signal actually contains).
  Connects to skill-acquisition.

- **B4 — Detect-irreducibility → request-atom signal (P4).** Define a "composition bottomed
  out" signal: when no combination of current atoms separates/explains a phenomenon, the
  system flags that a human fundamental atom is needed — rather than forcing a bad fit (cf.
  the 50-gons in Part C). Perceptual twin of "extend the vocabulary only on solve-failure."

- **B5 — Top-down cognition with on-demand descent (P8).** Perception control (L4/orchestration)
  should invoke the highest meaningful-layer capacity first and descend to lower-atom
  capacities only on a defined **insufficiency trigger** (ambiguity / template fails within
  tolerance / finer detail required). Lazy, demand-driven — not an all-scales search.

- **B6 — Concepts as recursive, scale-relative relational templates (P7).** A concept
  recognizer is substrate-agnostic (parallel ∧ perpendicular ∧ closed over *any* elements)
  applied **recursively** up the metagraph (a structure recognized at level N is an element
  at level N+1), with **scale-coupled tolerances**. This is the missing "arrangement
  perception" (group elements → segments → shape) that Part C exposes.

## Part C — Evidence (the Bongard-LOGO case study)

Faithful diagnostic (2026-06-26), `projects/bongard_demo/tests/test_real_bongard.py`, on
real NVlabs Bongard-LOGO `rectangle_vs_circle` panels (raw marks, binarize-only — no
fabrication):

- Bongard-LOGO draws contours as trails of small triangle/circle **glyphs** + arcs, so a raw
  panel is ~15–23 connected components. Our perception (vertex/segment/angle → polygon,
  closed-stroke gate, ~44–60px regime) produced **side-independent noise**: rectangle-side
  116 marks = 53 `fit`-abstain + 63 polygons of `polygon_47..65`; circle-side 110 marks =
  50 `fit`-abstain + 60 of the same range. **Statistically identical → zero discriminative
  signal**; the gestalt shape never formed (the ~12px glyphs are below the size floor; larger
  fragments are mis-fit as ~50-gons).
- An earlier morphological pipeline (`close→fill_holes→skeletonize`) *did* make rectangles
  parse and circles abstain — but that was **scipy doing the arrangement perception**
  (`fill_holes` decides the glyphs enclose a region), a cheat that masked the real gap. This
  is precisely why B6 (grounded arrangement perception) is the need, and B1 (no ungrounded
  perception) is the rule.
- Verified fact grounding B2: the current `pixels_to_points` is **one point per foreground
  pixel, 1:1, position-only** — intensity discarded at threshold.

Together these motivate B2 (intensity + combination), B6 (recursive arrangement templates),
B5 (top-down/on-demand), and B1 (grounded-output constraint) — i.e. Part A is not abstract;
it is the diagnosis of a concrete failure on real data.
