# Leaf-Learning Process — Definitions (WORKING DRAFT)

**Status.** Working draft, agreed in the amii leaf-learning design chat, 2026-07-20.
Substrate-neutral doctrine. Staged for `main` under `docs/_workbench/`; a **core chat
promotes the reviewed version into `docs/concepts/leaf-learning.md`**. **Not authoritative
until reviewed — do not cite as official.** Sits directly on `PERCEPTION_PRINCIPLES.md`
(P1–P11) and `LEAF_LEARNING_SYSTEM.md`; read those first.

**File family.** This file is the **domain-neutral contract**. Each domain instantiates it in
its own **application file** — one per domain, none of them editing this one:
- amii NILM study → `projects/amii_study/LEAF_LEARNING_NILM_APPLICATION.md` (branch
  `chore/amii-study`).
- bongard demo → later.

No domain specifics appear below — they live in the application files.

**Append discipline.** This file grows one agreed block at a time. Each new definition is
added only after explicit agreement; open items live in §7 until they move up.

---

## 0. Purpose & governing decisions

- **Goal.** Formalize the *official* MindsOS leaf-learning process — the acquisition of a
  grounding front-end (raw signal → typed atoms) — generally, for any domain.
- **G0 — Fail-proof on the causal claim, lean elsewhere.** The one claim built to survive
  any skeptic is that **MindsOS's architecture is the cause** of the result. Breadth
  (hypotheses, baselines, seeds) stays economical.
- **G1 — Leaf-learning = grounded composition; opaque install pushed to the floor.** Build
  atoms as inspectable compositions of grounded lower atoms; install opaque primitives only
  at the smallest, most general floor, quarantined behind a typed atom.
- **G2 — Hand-off, not core edits.** This authors doctrine; it never edits `mindsos_*`.

---

## 1. The kinds (the vocabulary of the model)

The model is the MindsOS L3/L2 model (`ontology.py`, glossary).

- **DataState** — a typed node/value. Two flavours, split by dependency:
  - **atom** — a DataState that depends on *no* other DataState (irreducible *for the given
    representation*, §2).
  - **composition** — a DataState *produced from* other DataStates. (Still a DataState; the
    atom/composition split is *within* DataStates.)
- **Reading vs Concept** (the honesty line, T1 §2): a composition is a **reading** if it
  measures a property of the data; a **concept** if it *interprets* readings (meaning).
- **Capacity** — the transition (edge) DataState(s) → DataState. **Fixed-not-learned**
  (glossary: "Capacities are fixed-not-learned; state lives in L2"). Deterministic or
  learned-probabilistic.
- **Lexicon** — names/types with no capacity and no grounding. Pure taxonomy the system is
  *told*.

**L2 / L3 split (decisive).**
- **L3 capacity = fixed, declarative structure** — the composition/reading *shape*.
  Human-declared, inspectable, never learned.
- **L2 `LearnedParameter` = the learned content** — thresholds, calibration, confidence, or
  even opaque weights (a blob) — few-shot fit, persisted, per-parameter auditable
  (`confidence` + provenance), Local scope `mutable_with_retention`.

**Consequences.**
- **Unit of leaf-learning = a (DataState, Capacity) pair** (the *structure*, P11) **plus its
  L2 LearnedParameters** (the *learned* part). Never a bare DataState.
- **Opacity spectrum, one shape:** deterministic reading (no L2 param) · learned-transparent
  reading (threshold + calibration in L2) · opaque install (weight-blob in L2) — all behind
  the **same fixed typed L3 capacity**.
- **Additive / no-forgetting** = teaching writes a *new* Local L2 node; existing nodes are
  untouched.

---

## 2. The floor (the interpretation boundary)

- **Definition.** The floor is the set of capacities that turn **data as delivered** into the
  first typed atoms the system understands. Its **position is representation-relative**: the
  floor sits wherever an atom can only be obtained by reading it directly.
- **T1 — Reading, not interpretation** *(definitional, always).* A floor capacity reports a
  measured property; it never emits a concept/task verdict.
- **T4 — Representation-irreducible** *(definitional).* A datum is floor *for a given input
  representation* iff it cannot be reached by composing atoms that representation already lets
  the system ground — it must be read directly. Judged **on the data, not on the capacity
  set**. (Ex.: given force `F` and acceleration `a`, both are floor readings and mass `m` is
  *won for free*; deliver `(m, a)` instead and `F` becomes the free one.)
- **T2 (shared) / T3 (load-bearing) — health-signals, not gates.** In a multi-concept brain,
  floor atoms tend to be shared and load-bearing; a "floor" atom serving one concept with
  nothing composed on it is a **smell** it is a bespoke concept-detector (fat-leaf risk). A
  single-concept brain legitimately violates both.
- **Win-for-free** = target ∈ the span of compositions the system already holds over its floor
  readings (zero-shot composition — no new leaf learned).
- **Fairness invariant.** Because entry-point is representation-relative, the input
  representation must be **fixed and identical across all compared systems**, or entry-point
  becomes a rigging knob.

---

## 3. The leaf and leaf-learning

- **Leaf** = a floor capacity (data-as-delivered → typed known atom).
- **Leaf-learning** = **fitting L2 LearnedParameters for a fixed L3 capacity**: few-shot,
  calibrated, inspectable. **Deterministic** where the reading is unambiguous (nothing to
  learn); **probabilistic-and-learned** at the noisy margin; **opaque-installed** only where
  no inspectable reading exists (the last-resort floor). It bites hardest at the ambiguous
  margin — which is also where honest-failure and the request-reference live.
- **Probability attaches to the reading, not the concept.** The learned confidence is on the
  *measurement* ("this reading is reliably present, conf 0.8"), never on a concept name
  ("P(kettle)") — that would collapse the floor into a concept-classifier.

---

## 3A. The composition vocabulary (agreed #1)

A composition is a **DAG of primitive capacities** grounding out at floor readings (the
`compose.py` composite-DAG). The **vocabulary** is the finite, human-authored **library of
primitive capacities** that may appear as DAG nodes. Concepts are *not* in the library — they
are compositions built from it. The library is domain-neutral; the domain-specific part is the
floor readings it runs on.

**Three families.**
- **Structural (L3, no learned value)** — aggregate (sum/mean/count/max/variance), compare
  (=, <, >, ratio, difference), select/segment (the sub-region where a predicate holds),
  project (re-represent onto a chosen basis/reference), bind (co-index two atoms sharing an
  ordinate — P6), logical (∧, ∨, ¬), order/temporal (over-window, periodic-at, sequence).
- **Parametric (L3, structure fixed, value in L2)** — threshold (`value ⋛ τ`), tolerance
  (`within ε`), calibration (raw score → probability). Learning enters here and *only* here at
  L3: the structure is readable, only the value (τ / ε / coeffs) is few-shot fit and persisted
  in L2.
- **Reasoning / attention (L4, resolve held ambiguity — §4)** — descend-for-discriminator,
  apply-a-certain-rule, consistency-check-against-a-confident-anchor, escalate (hold-for-data /
  request-reference). Input = an ambiguity; output = resolution *or* escalation; never fuse two
  ambiguities.

**Admission rule.** An operator enters the library iff: **faithful** (computation transparent
to the floor — a learned *threshold* qualifies; an opaque learned *feature* does not, that is a
floor primitive §3); **general** (reused across concepts/domains; a one-concept-only operator is
a disguised concept-detector, the fat-leaf smell); **enumerable** (small finite set → induction
over it is a bounded search yielding a *readable DAG*, not weights — the inspectability
guarantee).

**Closure — P2/P3 lifted to capacities.** Primitive capacities are **exogenous**
(human-installed, logged); composite capacities are **endogenous** (composed). The system
composes with the library; it never autonomously mints a new operator. "Cannot express this
concept with the current library" is an operator-level irreducibility → a **logged request for a
new operator**, the same honest move as request-reference (§5). The library is therefore
fixed-and-known at any moment; extending it is deliberate.

**Generality (decided): (a) with (b) as fallback.** Target **(a) one universal core** — even
higher operators (autocorrelation, periodicity) are expected to *decompose* into core operators
(shift · multiply · aggregate), so only the floor readings + a few domain constants are
domain-specific. Fall back to **(b) universal core + a small domain-*family* layer** (e.g.
signal-family project-onto-basis / window) only where an operator provably will not decompose.
Per-domain vocabularies **(c) are rejected**. Evidence for generality = **cross-domain reuse**:
the same library builds the vision (geometry) arm and the NILM (signal) arm — asserted here, to be
shown when the NILM atoms are built.

---

## 3B. The acquisition procedure (agreed #2)

**Two modes, checked in order.**
- **Endogenous (autonomous, no fit).** *Reach check* first (§2 win-for-free): if the target is
  expressible as a composition of already-grounded atoms over the vocabulary, consistent with the
  examples, with **no new parameter** → compose and promote it; nothing is learned in the weight
  sense. The majority case, and where the architecture visibly earns its keep.
- **Exogenous (taught, few-shot fit).** Only if not reachable: a human supplies **name + output
  type + labelled examples** (optionally a declared composition). The only path where L2 learning
  happens. Always human-initiated — may be *prompted* by the system's own request-reference (§5). The
  system never autonomously mints a fundamental atom (P2/P4).

**Learning method — declared or induced (peers, D1).** The composition DAG is obtained either by
**declaration** (a domain expert states the structure over the vocabulary using already-grounded
rungs) or by **induction** (a bounded search over the closed vocabulary for the **minimal DAG
that separates the examples and generalises to held-out** — not best-fit-the-handful). Induction
may cross-check a declaration; neither is primary.

**Understanding a declaration.** A declared structure is not opaque data — the system understands
it by **binding every node to the vocabulary it already grounds** (§3A): each referenced operator
and atom must resolve to an existing grounded capacity / DataState. A node that cannot be bound is
itself a **request** (for the missing operator/atom) — the same honest move as request-reference. So a
declaration is understood exactly to the extent its pieces are already grounded, and *verified* by
analysis-by-synthesis (does it reconstruct the examples; does it agree with induction).

**Teaching is bottom-up (P8 bootstrapping), never a flat classifier.** A leaf is a *thin rung* on
rungs that must already be grounded. Teaching a concept = building/reusing the ladder below it,
then adding one small `(DataState, Capacity)` rung on top; the learned part is only that rung's L2
parameters. "Handful of labelled inputs → concept" in one opaque step is the fat-leaf error,
forbidden.

**Confidence, not shot-count, sets the data (D2).** There is no fixed *k*. Acquisition takes
**enough** examples to reach the **task's required confidence** (L5); **surplus** validates it; a
**deficit** leaves confidence honestly low → held-ambiguity (§4). Stopping rule: *enough* = the
calibrated confidence **stabilises and validates on held-out**. Confidence **propagates through
the structure** (a whole's confidence is built from its parts'), **gated by the §4 invariant**
(two ambiguous parts never confirm a whole).

**Procedure (exogenous path).** (1) obtain structure (declare/induce); (2) fit parametric values
+ calibrate confidence → L2, to the required confidence; (3) register the `(DataState, Capacity)`
pair + L2, existing nodes untouched (additive, no-forgetting); (4) **verify** — faithfulness
(ablate a stated sub-atom → the verdict flips) + calibration reliability on held-out; fail either
→ not admitted.

**Learning from a generator (guards; deep-dive deferred).** A parametric generator gives unlimited
labelled draws (serves "enough shots"), but three guards hold: **(a)** never fit against the
instances used to test, and no generator parameters reach the chain (baked-inverse); **(b)** the
claim is "reaches confidence at a smaller budget than the baseline on the *shared* curve," never
"used unlimited data" (anti-efficiency); **(c)** synthetic ≠ real — a leaf must transfer to real
data or it is self-referential (reality-gap).

This is the "learned-leaf apparatus with calibrated confidence" the core still owes as a CR.

---

## 4. The recognition model (bidirectional joint inference + anti-hallucination)

- **Joint, bidirectional recognition.** When compositions are probabilistic, recognition is
  not one-way: each *engaged* layer draws on adjacent layers (bottom-up) and is checked
  against them (top-down); **confidence = calibrated degree of cross-layer agreement.**
  *This mechanism is prior art* (predictive coding, And-Or graphs, part-whole MRFs,
  routing-by-agreement, analysis-by-synthesis) — it is the **mechanism, never the pitched
  novelty.**
- **Anti-hallucination invariant (load-bearing).** A **confident** recognition (whole *or*
  part) may disambiguate an **ambiguous** one. **Two ambiguous recognitions may never
  validate each other** — ambiguity + ambiguity ≠ confidence. Unresolved ambiguity is
  **kept** as an explicit open question and dispatched to a dedicated **reasoning/attention**
  act (fetch more data · descend for a discriminating reading · apply a certain rule). If
  reasoning + available data cannot resolve it, the ambiguity **stays open** — never forced
  into false confidence. *Hallucination is thereby excluded by construction.*
- **What the invariant rests on:** (a) **audited calibration** (P14) — "confident enough to
  validate" is a calibrated L2 threshold, valid only if a 0.95 recognition is right ~95% of
  the time; (b) **the trade, named** — classic joint inference fuses two weak cues into a
  confident answer; we forbid that and instead **route rescue through reasoning** (which
  fetches the discriminating datum). Narrower and slower, but cannot hallucinate — the right
  trade for high-assurance operators.
- **Descent trigger = "confidence in what is needed."** Whole-part validation fires on a
  **confidence deficit relative to what the task requires**, not on depth. Descend/consult
  another layer *only when* (a) current confidence < the task's required confidence **and**
  (b) the data affords a more discriminating reading there. Bar met → no descent (P8 lazy).
  Data can't help → hold the ambiguity, don't force it. Adjacent-coupled (whole↔its-parts,
  propagating transitively), convergence-bounded.
- **Redundant-grounding validation.** When a probabilistic measurement is ambiguous *and* the
  required confidence isn't met, and the DataState participates in a **known composition** (it is
  derived from lower atoms, or is a component of higher ones), the system **measures those related
  DataStates and uses their *confident* recognitions to validate/sharpen it** — known compositions
  are the validation routes. Demand-gated (only when the ambiguity matters) and confident-only
  (the anti-hallucination invariant). This is the active, general form of the bidirectional check.
- **Layer mapping.** **L5** sets the required-confidence (the task/goal) → **L4** deliberates
  / descends / disambiguates (the joint-inference control loop; P8/B5, *designed-not-built
  core*) → **L3** recognizes → **L2** calibrates.
- **Three honest terminal states:** **confident answer** · **held-ambiguity** (need more
  data) · **request-reference** (need a new thing to match against). This trio is the "honest failure" surface an
  opaque classifier structurally cannot produce.

---

## 4A. The recognition template (every probabilistic recognition)

A probabilistic recognition is **not atomic** — it is an **L4 pipeline** that composes single-step
**L3 capacities** (the pipeline-finder sequences them; it is *not itself* one capacity). It has a
fixed shape, deterministic except one learned step. For a candidate recognition X (each numbered
step below = one **L3** capacity; the **sequencing + the verdict/descent = L4** control flow):

1. **propose** — fit/measure the candidate structure (from a **declared** or **induced**
   composition). Deterministic.
2. **synthesize** — reconstruct the input from the candidate (the forward model). Deterministic.
3. **residual** — input − synthesis. Deterministic.
4. **features** — measure the residual: its **magnitude**, and its **structuredness** measured on
   *every axis the residual carries* (for a signal: **time** *and* **frequency**). Unstructured on
   **all** axes = noise; concentrated on **any** axis = structure. Kept **per-axis** so a
   request can name *which* axis the missing reference lives on. Deterministic; reusable.
5. **confidence** — calibrate the features → a probability. **LEARNED (L2) — the only learned
   step.**
6. **verdict** (§4 rules) — confident / held-ambiguity / request-reference.

Two consequences:
- **The confidence is grounded, not opaque** — it's a calibration over *measurable* residual
  features, so the system can state *why* it is low. This is the analysis-by-synthesis
  verification the doctrine already requires; steps 2–4 reuse the §3A vocabulary, added once and
  shared by every rung.
- **Residual structuredness is the request-reference criterion.** A residual *flat on every axis*
  is **noise** (P1 — nothing to explain). A residual *concentrated on any axis* that **no known
  reference matches** is a **request-reference** (name the structure + the axis). This gives #3 its
  computable shape.

---

## 5. Irreducibility → request-reference

**Recognition is matching against known references.** A *reference* is a known pattern the system
compares an observation against (a named model/template). References are **L2 knowledge** (the
`concepts` role-graph + their `learned-parameters`) — the library of what the system knows. What
grows additively, on-device, on one metagraph, is exactly this L2 reference library; L3 (matching
operators) and L4 (orchestration) are fixed.

**Request-reference (the honest failure).** When the system has *measured* structure (a grounded
residual) that matches **no known reference**, and neither more data nor reasoning resolves it, it
emits a **request-reference**: it names the measured structure and asks for a **new reference** to
match it against. Data and reasoning are exhausted first; the request is actionable (the named
signature tells a person *what kind* of reference to add). Teaching it adds one new L2 reference,
existing ones untouched.

**A request is *only ever* for a reference, never for a sense.** The system can request a match for
structure it can *measure*. It can never request a missing **fundamental/sensory** atom: if it
lacked a sense, it couldn't perceive the structure at all — the residual would look flat — so it
could not know something was there to ask for. A missing sense is an un-self-reportable blind spot
(P17), not a request. This is why "request-atom" was the wrong name: the ask is for a *recognition
target*, not a perceptual primitive.

---

## 6. Architecture is the cause

- **The claim lives at the lifecycle, not a single leaf.** One learned leaf is numpy-trivial.
  The causal claim is the **lifecycle**: acquire → persist (L2) → compose → reuse → **teach
  additively without forgetting** → load on demand — on one inspectable metagraph.
- **Ablation isolates it.** "MindsOS − structure" = collapse the ladder to one level
  (flat/monolithic). If the win dies, the **layering** (which the metagraph provides) was the
  cause. A monolithic classifier is a ready "− structure" arm: it forgets on incremental add
  and cannot name the gap.
- **Why not reproducible-away.** The **cross-layer joint inference (§4)** and the **persisted
  L2/L3 lifecycle** are what a flat model / a numpy pipeline lack; reproducing them means
  rebuilding the architecture. "No numpy reproduction exists" is *not* the bar (Turing);
  **the ablation losing the property** is.

---

## 7. OPEN — not yet defined (do not treat as decided)

- **#3 Request-atom trigger — mechanical criterion** *(one remaining open definition).*
  §4A gives it its **shape**: request-reference fires when the residual's **structuredness** (on any
  axis) exceeds a calibrated threshold *and* no known reference matches it (a residual flat on all
  axes is noise → no request). What stays open is the **calibration** of the per-axis structuredness
  thresholds and false-trigger avoidance (novelty vs noise) — to be finalised against Test 1.
- **Logistics.** Placement: staged to `main:docs/_workbench/`; core chat promotes to
  `docs/concepts/`. Domain specifics tracked in the per-domain application files (see File
  family, top). Control protocol: no sandbox git; Mac commits explicit paths.
