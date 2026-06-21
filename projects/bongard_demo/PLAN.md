# Bongard Solver — Design Plan

**Status:** design, living · 2026-06-20 · standalone MindsOS instance (Track 2 of `intelligence_demo`)
**Posture:** critical design reviewer (skeptical, terse). This is a design record, not a build log.

---

## 0. What this is / scope boundary

A **standalone MindsOS instance** that solves **Bongard-LOGO** via auditable analysis-by-synthesis. Primary purpose is a **development forcing-function**: build real, currently-missing MindsOS features (perception capacities, the mint Skill) and surface integration gaps. A demo is a **byproduct**, not the goal.

- **Ours (build here):** the Bongard instance — its ontology + perception capacities + concept capacities + verifier + parse/control wiring.
- **External, coordinated:** the **Mint Skill** is owned by the Skill-Acquisition process (separate chat, not yet concluded). We design the **Bongard-grounded instance** of mint here as a concrete worked example that *feeds* that chat — not a parallel spec.
- **ARC:** reference-only. Patterns transfer (analysis-by-synthesis, the capacity-chain shape); artifacts/realm/ontology do **not**. ARC is reserved for another priority.

---

## 1. Capability target (the claim, deferred but anchored)

> Acquire a new, named, reusable concept from a handful of examples — by minting structure over an ontology — such that the result is an **inspectable parse**, it **generalizes** to held-out instances, it **abstains honestly** when it can't, and acquisition costs **few examples and no large training run**.

= auditable + low-compute-*learning* + bounded generality. "Can learn anything" is dropped as a selection criterion (proven by depth + transfer, not breadth).

**Thesis upgrade specific to this instance:** perception is **built from scratch as an auditable parse**, not a borrowed black box — licensed *only* because the shapes are clean/synthetic. This pushes the auditability moat down into the leaf.

---

## 2. Architecture (one frame)

Analysis-by-synthesis: **ontology graph (structured generative model) + perception leaves + a proposer + verify/backtrack/abstain inference + a mint Skill.** Perception and concept-acquisition use the **same** planning/mint machinery — pipelines composed from pipelines; a named shape/concept is a *minted composite* over seeds.

---

## 3. Domain

**Bongard-LOGO**, **clean synthetic shapes**, **polygon family first (curves deferred)**.

- **Held-out generator** = primary concept signal (sample fresh +/− per problem → measurable generalization, kills few-shot underdetermination).
- **Reconstruction / fit-error** = per-percept signal.
- Cheap symbolic verifier was *swapped*, not lost: held-out + reconstruction are the verifiers; the verify→blame→replan→abstain machinery is intact, just running on those signals.

---

## 4. Bongard instance — ontology (built fresh, own realm)

- **Atom layer (new, between Point and Shape):** **segment** + **vertex**.
- **Vertex = shared endpoint** of two segments (not an infinite-line intersection).
- **Shape = closed simple polygon.** `triangle ⟺ 3 segments, 3 vertices, each vertex joins exactly 2 segments, closed simple loop` (closure + simplicity exclude the hash/asterisk/3-loose-strokes cases).
- **The polygon *schema* is definitional** (closed-simple-loop over segments/vertices); you don't learn what "a polygon" is. But **individual shapes past the triangle seed are minted composites** — square/pentagon are acquired (milestone 2), not pre-given templates. (Resolves the §7/§9 tension: only the triangle seed is handed in.)
- **Two atom families:** straight (segment, vertex) — now; curved (arc/curvature) — deferred as a second family.

---

## 5. Perception subsystem (built, auditable)

**Capacity chain** (each a registered L3 capacity; recursive sub-pipeline — pipelines from pipelines):

| Capacity | consumes → produces | role |
|---|---|---|
| `pixels → point-set` | image → foreground point-set | grounding leaf, **swappable / domain-specific** |
| `point-set → segments` | point-set → straight segments | grounding (line-art) |
| `segments → vertices` | segments → shared-endpoint vertices | derivation |
| `{segments,vertices} → polygon` | → `Shape{type,…}` | comparator/predicate |

**Control = hypothesize-verify-backtrack loop** (completed shape):

1. global pass → candidate figures (individuation) + gist
2. per figure: proposer emits ranked atom hypotheses
3. verify top hypothesis — **reconstruction preferred** (render & compare), reusing detector/generator pairs
4. **conclude | re-hypothesize | re-segment | abstain** (dual backtrack: wrong label *or* wrong boundary; abstain on budget exhaustion)
5. assemble scene parse; concept hypothesis *may* feed back top-down to re-rank/disambiguate (the F seam — **interface-only at v1, body deferred**, see §F)

**Confidence = segment-fit residual** (scale-normalized point-to-line; whole-shape reconstruction demoted to optional — see §D). Shape-level verify is symbolic. **Abstain** when a region won't fit segments (e.g., it's a curve → route to curve family or abstain).

**Reusable feature = the grounding contract:** raw signal → normalized point-set → ontology shape. Generalizes as **"any point-set," not "any picture"** — the grounding leaf is swappable per domain; everything above it is shared.

**F — integration contract (DECIDED 2026-06-20, interface-only):**
- **Bottom-up half:** perception hands up `Shape{type, vertices, pose, confidence}` **or abstain**.
- **Top-down half:** down = `ParsePrior{ expected_atoms, expected_figure_count, pose_hint?, source_concept_iri, strength }`. Three rules: **rank-not-score** (reorders the candidate queue / breaks ties; never changes reconstruction-fit confidence, never injects a candidate bottom-up didn't generate), **held-out firewall** (priors apply only to training-example parses; held-out is always parsed prior-free — that is the generalization verdict), **provenance** (`prior_applied` tag).
- **Build now (mandatory seam):** the two interface slots only — proposer returns its **ranked candidate list** (not a collapsed winner) + accepts an optional `ParsePrior` in `CapacityContext` (default null). **Defer the `re_rank` body.** Empirically checked against the NVlabs dataset: Bongard-LOGO's clean-polygon subset never produces a genuine ambiguous-parse tie (vertices are exact via the action program; hard images = curves / edge-decoration / open free-form strokes → all **abstain**, not tie). So for this instance the body is **never built** — the reusable asset is the contract, not the algorithm.

---

## 6. Concept subsystem

A **concept = a predicate over the scene parse** (objects + relations). Search over predicates → verify against the **held-out generator** → conclude | abstain. Concept artifacts live in L2 `concepts`. The iconic open-ended Bongards will be **honest abstains**, not solves — that's the moat working, not a failure.

---

## 7. Mint Skill (Bongard-grounded instance → feeds Skill-Acquisition)

Mint is a **Skill**: cross-layer intelligence. **L3-the-layer is extensible; each capacity-function is fixed.** A minted capacity is a **new L3 node** (a *composite / specialization of seeds — never a new primitive*), with an **L2 footprint** (`learned-parameters`, `promoted-pipelines`). Adding nodes is allowed; inventing primitives is not.

**Five-step shape:**

1. **Identify** (L3, auto) — compression/reuse flags a recurring composite, or a **gap** if uncomposable.
2. **Validate** (L3, auto) — held-out/verifier confirms generalization.
3. **Provisional register** (new L3 node + L2 record, auto, **Local**, machine-named e.g. `composite_0427`) — usable immediately.
4. **Present + name** (**human**, at the **Local→Global** boundary) — show the parse + example occurrences; human supplies the label; route through `alignment` for dedup.
5. **Promote** (**Global, admin-gated** — existing Server machinery) — enters shared knowledge.

- **Composites** (self-grounding: meaning = parse) flow 1→5, provisional auto-name is fine.
- **Uncomposable structure** → `capacity-gaps` (L2) → human defines/names a new primitive. A true new primitive *requires* a human (it's un-grounded); the system never autonomously mints one.
- **Human placement:** at Local→Global, not per-Local-mint (per-mint human gating caps learning at review bandwidth and reintroduces the bottleneck autonomy was meant to remove).
- **Differentiator to foreground:** human-*namable* candidates are free from analysis-by-synthesis — the candidate is a parse you can show a person. A net's candidate is a weight cluster. Human-in-the-loop naming is a feature the architecture uniquely enables, not a concession.

---

## 8. Layer mapping

**Invariant:** compute/decide = **L3** · trigger/orchestrate = **L4** · knowledge artifact = **L2** · per-task trace = **L5** · graph substrate = **L1**.

| Step | L2 | L3 | L4 | L5 |
|---|---|---|---|---|
| Perception chain | ontology atoms + learned tolerance | the 4 capacities | hypothesize-verify-backtrack lifecycle | parsed instances + chain artifact |
| Shape-mint (Skill) | new polygon node + composite + params | mint computation | trigger + promotion-proposing | source episodes |
| Scene parse | relation types | comparator/predicate | multi-object orchestration | scene instances |
| Concept search+verify | `concepts` | search + `validate` | held-out loop | concept chain |
| Concept-mint (Skill) | predicate → `concepts`/`promoted-pipelines` | mint computation | promotion-proposing | evidence episodes |
| Top-down feedback | — | re-scoring | concept prior → perception loop (F seam) | updated parse |

---

## 9. Sequence / milestones

1. **Perception chain on a single polygon** — `pixels→…→polygon`, with abstain.
2. **Shape-mint = mint milestone 1** — after triangle, mint square/pentagon from the same atoms (cheapest test of the mint mechanism; the worked example handed to Skill-Acquisition).
3. **Multi-object scene parse** (objects + relations).
4. **Concept search + held-out verify** (no concept-mint yet).
5. **Concept-mint = mint milestone 2** (the research-hard 20%).
6. **Top-down feedback** (concept → perception disambiguation).

---

## 10. Open decisions

- ~~**F top-down half**~~ — **DECIDED 2026-06-20** (interface-only; see §5 §F). Build the two interface slots, defer the body, never build it for Bongard.
- **E proposer** — brute/deterministic for the first slice; learned prior later (mirror at perception + concept level).
- ~~**D reconstruction mechanics**~~ — **DECIDED 2026-06-20.** Two reframes + config:
  - **Tolerance lives at `point-set → segments`**, as a point-to-line residual — *not* whole-shape reconstruction. Shape-level verify (`{segments,vertices} → polygon`) is a **symbolic predicate** (count + closure + simplicity), no rendering. Whole-shape render-and-compare is **demoted to an optional global sanity check** (earns its place only when the leaf goes messy / borrow-the-leaf future). Departure from §5-as-written, accepted.
  - **Calibration is circular** (need ε to parse, need parses to calibrate ε) → **bootstrap ε off the definitional triangle seed** (known answer), then generalize. Ordering constraint.
  - **Fit metric:** scale-normalized point-to-line residual (normalized by figure bbox-diagonal — mandatory, size is a Bongard nuisance). **RMS = accept score; max-residual = abstain guard.** Maps onto §5's dual backtrack (RMS "good-enough line"; max-residual spike → missed corner/curve → re-segment/abstain).
  - **Abstain = two gates:** (a) *fit gate* — best segmentation RMS > τ_fit → "won't fit straight segments" → curve family / abstain (this is the curve + edge-decoration rejector); (b) *structure gate* — atoms don't close into a simple polygon → re-segment/abstain. A margin/tie gate is retained but expected **dormant** (per §F: clean Bongard yields no ties).
  - **Calibration → `learned-parameters`:** percentile from a handful of clean seed parses — `τ_fit = (max accepted residual)×(1+slack)`. Stored **Local per problem**, seeded by a **Global default**. Few examples, no training run (satisfies §1).
- **H budget policy** — max hypotheses/backtracks per figure → abstain thresholds.
- **Curve atom family** — deferred; known future decision.
- **Persistence** — CapacityLayer is in-memory-first (Phase-42 PB-7); "minted shape survives a restart" is an integration question to test, not an assumption.
- **Skill-Acquisition coordination contract** — the consume/produce interface; design mint here as the worked example, hand it over, avoid divergence.

---

## 11. Standing risks

- **The concept/relational mint loop (step 5) is the genuine unbuilt research piece.** Steps 1–4 will run fast and feel like progress; the project succeeds or fails at 5. Shape-mint (step 2) is the cheap early proof the mechanism works at all. "Pipe runs" ≠ "it can mint."
- **Perception is the easy-20% trap** — buildable and satisfying while the core sits untouched. Guard the budget.
- **Don't seal perception before F's top-down half** or step 6 forces a teardown.
- **Mint-design divergence** with the Skill-Acquisition chat — coordinate or the two specs drift.
- **"From scratch" perception expires** the moment shapes stop being clean; revert to borrow-the-leaf for messy images.
