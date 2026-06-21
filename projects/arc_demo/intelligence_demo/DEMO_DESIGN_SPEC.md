# Intelligence Demo — Design Spec

> **Audience:** AI/ML research community. **Status:** design, no code yet.
> **Binding contract:** `INTELLIGENCE_PARADIGM_HANDOFF.md` (§4 boundaries, §7 criteria, §8 anti-patterns). This spec must not assert past §4.
> **Posture pin:** the demo sells a **property layer** (named / audited / gap-surfacing / transferable learned unit), *not* a novel learning algorithm. The learner is deliberately mundane and honest. The held-out test must isolate a win the property delivers that a blind net structurally cannot — not a win the algorithm delivers.

---

## 1. Domain

**Regime-switching 1-D dynamical system:** a point mass under gravity above a floor. Two regimes:

- **Free-flight:** `y' = y + v·dt`, `v' = v − g·dt`.
- **Contact** (`y ≤ 0`): velocity reverses with restitution, `v' = −e·v`.

**Signals fed pre-decomposed** (perception conceded per handoff §4/§8): position `y`, velocity `v`, contact force `f`. No pixels. The task is next-state prediction `(y, v, f) → (y', v')`.

Chosen because it is the only candidate that exercises the §3 continuous→discrete primitive, has a *genuine latent switch* to discover (non-circular), supports an extrapolation holdout that provably breaks an interpolator, and runs thousands of trials cheaply.

---

## 2. What the five criteria map to (the script)

1. **Instructed learning.** The human teaches the *pipeline* (the middle): `SignalChannel decompose → predict-next-state (one leaf capacity)`. The system is given the structure of the task; it does not invent it — it fits and repairs it.
2. **Verify / repair + known-unknown.** The single-leaf pipeline runs; a `validate` capacity computes residual against data; residual spikes at contact; `phase6:attribute_blame` returns a `BlameVerdict` localizing the hole to the predict step in the contact region. The hole is *identified*, not silently fit over.
3. **Structure discovery (front 1).** A fixed `capacity:coherence_loop:<strategy>` (local split-search) searches `(signal × split-point)`, fits a leaf on each side, and mints a switch + two specialized leaves **iff** an MDL gate is cleared (§4). Provenance is recorded — not hardcoded.
4. **Held-out generalization.** An extrapolation split (§5): the minted switch + leaves extrapolate because the discovered *condition* is the true rule; MLP and memorizer baselines fail OOD.
5. **Auditability + honest don't-know.** Full chain-artifact trace (`HintSet→MappingResult→Plan→Pipeline→PipelineRun→TaskRun`) plus the mint provenance; on an out-of-scope regime the system surfaces "no pipeline for this" rather than emitting a confident wrong number.

---

## 3. Build vs mock (honest boundary)

**Built (real — the minimal new subsystem kernel):**

- `SignalChannel` continuous DataState (`perception` family, `DATASTATE_MARKER`) — the §3 representational primitive.
- A leaf **predict** capacity, parameterized (closed-form linear least-squares fit — cheap, mundane).
- A `validate` verify capacity (residual → `VALIDATION_RESULT` / `GoalVerdict`); blame via `phase6:attribute_blame`.
- `capacity:coherence_loop:split_search` (fixed L3 strategy) — enumerate split-points, fit both sides, MDL-score, return best split or `None`. **Local hill-climb only** (honors §4.4: no non-local leaps).
- The **mint** action: write the two leaf parameter sets + split-point to the `learned-parameters` role-graph (`LearnedParameter` nodes: `parameter_set_iri`, `target_parameter_iri`, `value`, `confidence`, `applied_at`), then `register_capacity` two specialized leaves + one `decision` switch predicate with `PRODUCES`/`CONSUMES` edges (ADR-0156) and provenance properties.
- **One** signal source (`signal.task_outcome` = residual) + **one** mechanism (`mechanism.ema` on leaf confidence). Stated plainly as one, not the full ALS.
- Baseline harness: MLP (matched parameter budget) + nearest-neighbor memorizer.

**Mocked / conceded (stated plainly as out of scope):** perception-from-pixels; promotion to Global / peer transfer (single session only); the full 11-subsystem multi-signal ALS; dreaming; crowd pipeline-ranking; FalkorDB flush (run in-memory per known L0-26 gap).

**Nothing load-bearing is mocked.** Criteria 3 and 4 are fully built or the demo is void (§8).

---

## 4. The mint criterion (concrete, auditable)

Split a parameterized leaf into two named sub-capacities **iff all three hold:**

1. single-leaf residual on the dataset > misfit threshold τ (the hole);
2. ∃ a signal `s` and split-point `c` partitioning the data so both specialized leaves' residuals fall below τ;
3. the residual improvement beats an **MDL/BIC complexity penalty** — the split must pay for its added parameter.

On success: freeze the better-fit region, write params to `learned-parameters`, `register_capacity` the two leaves + switch, and record `{signal, split-point, residual-before, residual-after, MDL-delta}` as the audit trail.

The MDL gate is load-bearing twice: it defeats "it overfits by splitting forever," and it is the proof the split was **earned by data, not given** — the answer to the skeptic's "did you hardcode it?"

**Honesty pin (fixed-not-learned):** the minted unit is a *specialization/split of an existing primitive*, never a new primitive function. The demo must never claim it invented a primitive. Consistent with §3 reconciliation: fixed L3 strategy + learned L2 parameters + new signal primitive.

---

## 5. Generalization metric + baselines

**Three test partitions:**

| Partition | Construction | Expected result |
|---|---|---|
| **In-distribution** | both regimes, boundary crossings inside training range `[a,b]` | all methods succeed |
| **Held-out extrapolation** | crossings forced *outside* `[a,b]` (impact velocity of unseen magnitude) | minted structure succeeds (correct restitution extrapolation `v'=−e·v`); MLP + NN **fail** |
| **Out-of-scope** | a regime with no learned leaf (e.g. a wall / second surface) | MindsOS surfaces honest don't-know; baselines emit a confident wrong number |

**Metric:** next-state prediction error, reported per partition.

**Baselines:** (i) blind MLP, matched parameter budget, **unlimited in-range data**; (ii) nearest-neighbor memorizer.

**Money plot:** in-distribution all win; OOD the named structure wins, both baselines collapse.

**Pre-register the framing:** the baseline gets *unlimited in-range data*, so the gap is purely extrapolation — uncloseable by adding more data. The claim is **systematic/OOD generalization + honest refusal**, NOT "faster/better learner" (that claim is killable by "you starved the baseline" and must not be made). Do not benchmark on sample count or wall-clock — structure-search-by-trial is slower than a gradient step (§4.5); speed is a concession, not a selling point.

---

## 6. Pre-registered failure conditions (the demo is void if)

- the MLP with unlimited in-range data closes the OOD gap → claim void;
- the split-search finds the boundary only because the search range was hand-narrowed → circular, void;
- the MDL penalty is tuned post-hoc to force the split → void;
- the structure-discovery or generalization beat is faked in UI → void (§8).

State these in the write-up. A demo with pre-registered kill-criteria is what earns a research audience; one without reads as a sales artifact.

---

## 7. Firewall stance (AI-community)

Reveal the demo's *own* kernel in paper terms: fixed primitive set, MDL-penalized local split-search, learned leaves + minted switch, audit trail, the three-partition protocol. Researchers need falsifiability — a non-falsifiable demo proves nothing to them.

Keep black-boxed: the 5-layer / metagraph / role-graph / FalkorDB internals and the full ALS + chain-artifact ontology. Describe the kernel without making MindsOS's product architecture a prerequisite to read it.

---

## 8. What the demo does NOT prove (state in the write-up)

Per §4: leaves remain learned black boxes (small, named, replaceable — not eliminated); auditability holds at composition level, not inside a leaf; discovery is local (no non-local primitive leaps); transfer, fleet, crowd-teaching, dreaming, and perception are all out of scope here. The demo is **proof-of-path for one mechanism** (instructed structure discovery + auditable refusal + OOD transfer), not proof of the full paradigm.
