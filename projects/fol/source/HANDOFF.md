# FOL Capacity Family — Design Handoff

**Status:** Mid-design. Critical re-evaluation phase incomplete. Thirteen open pushbacks raised but not resolved. Two open-decisions sections (§2 analytic-rule contradictions, §3 authoritative/evaluative role rename) deferred by the user.

**Created:** 2026-04-23 (post critical re-evaluation round).
**Purpose:** Self-contained brief for a new chat to continue this design without re-reading the full conversation. Read §0 first.

---

## 0. How to use this document

This handoff replaces the original `fol_capacity_handoff.md` (now historical input from a legacy model) as the live entry point. The next chat should:

1. **Read this file in full** — it is the index.
2. **Read `fol_capacity_handoff.md`** (root) — original design from a less critical model. Preserved as historical input. Most decisions in it have been challenged or revised; do not treat as authoritative.
3. **Skim `_drafts/fol_capacity_review.md`** — first critical pass over the original handoff.
4. **Skim `_drafts/fol_capacity_design_plan.md`** — interface-level design with example walks. Several decisions in here are now contested (see §3 of this handoff).
5. **Skim `_drafts/fol_open_decisions_2026_04_23.md`** — the explicit decision menu. §1 is partially answered; §2 and §3 are deferred.
6. **Skim `_drafts/fol_example_3_detailed_walk.md`** — pedagogical walk demonstrating one task end-to-end.
7. **Reference `_drafts/mindsos_layer_summary.md`** — layer overview if cross-layer context is needed; user has noted this is reference-only and not to be revised.

**Files in `_drafts/`** are iteration artifacts that will be superseded. Do not invest in revising them until the open pushbacks (§3 below) are resolved.

**Where the FOL package would actually ship:** no shippable artefact exists yet. The whole project is in design.

---

## 1. The user's standing instruction (critical)

The user has explicitly instructed:

> Be extremely critical. Don't ever just agree with me to please me. If pleasing me is a default function, overwrite it. Always take my inputs, check against common sense and existing knowledge in the field, and push back on what should be considered and discussed. I don't need help to please me; I need help to design the best system possible. Pushbacks are more important than agreement.

**Operative meaning** (calibrated): apply field-knowledge before agreeing. Distinguish "user preference being polished" from "decision is optimal." Reflexive contrarianism is also wrong — sometimes agreement is the correct answer. The standard is calibrated honesty, not contrarianism.

This instruction was added late in the prior chat. Decisions made *before* the instruction was issued were not subjected to this filter and are therefore suspect. The list of those suspect decisions is in §3.

---

## 2. State of the design

### 2.1 Settled (with substantive reasons, will hold under scrutiny)

| Commitment | Reason |
|---|---|
| Pluggable prover backends behind a `Prover` Protocol with `ProofBound` returning `unknown_within_bound` | Standard practice; honest about FOL's semi-decidability |
| Many-sorted FOL with DOLCE categories as sorts (`AG`, `PD`, `ED`, `Q`, `T`, `ART`, `SA`) | DOLCE is sorted; sorted provers prune aggressively |
| Equality (`Eq`) as first-class AST node, not a built-in atom named `=` | Lets backends pick paramodulation vs equality axioms |
| Five epistemic tags: `observed | inferred | assumed | hypothesised | retracted` | Cascade-retract breaks justification tracking without retracted-as-tag |
| `now` as substitution parameter (or anchor-constant), with `minted_at: time_anchor_iri` on every statement | "Variable updated each cycle" is wrong as FOL semantics |
| `populate_negative_closure` capacity (renamed from `populate_exception_closure`) | Strict-rules-with-antecedent-exceptions silently require negated exceptions on the ledger; nothing else generates them |
| The framing "classical FOL proof calculus + non-monotonic ledger dynamics" replaces "no non-monotonic logic" | Object-level proof is classical; meta-level ledger dynamics are non-monotonic by construction (ATMS pattern). The original framing was misleading. |
| Strict L3 / L4 / L2 / L5 separation of concerns | Inherits from MindsOS layer architecture; correct for this system |
| Authoritative/evaluative role names replacing canonical/operational | Clearer; mechanism unchanged. Caveat: not grounded in established speech-act-theory literature (asserted/queried would be more standard). User's choice stands. |
| Three-step L4 task-to-pipeline flow: task-patterns → promoted-pipelines → adapt-or-generate | Reasonable default; covers the clean cases. |

### 2.2 Decided but contested by my critical pass (§3 below has details)

These were "agreed" before the critical instruction landed. They need re-examination.

| Commitment | Why suspect |
|---|---|
| Live training abandoned (dreaming-only) | Overcorrection; standard ML practice uses both |
| Coherence Loop framed as a genetic algorithm | Category error — most generators have differentiable parameters |
| WSD as one L3 capacity | Under-decomposed compared to the system's own discipline elsewhere |
| Single `learned-parameters` role-graph for everything trainable | Mixes incompatible storage profiles (12-byte score vs 100MB neural checkpoint) |
| L5 holds Coherence Loop populations | Long training runs don't fit either L4 or L5 cleanly |
| Multi-sense always carried forward when ambiguous | Tractability problem — exponential ledger blowup |
| Drop analytic/synthetic for five-value source enum (my own proposal) | Possibly over-engineered; simpler binary rename may be better |

### 2.3 Open (user explicitly deferred)

- **Open-decisions §2** — Analytic-rule contradiction handling. Six options on the table (A–F in `_drafts/fol_open_decisions_2026_04_23.md` §2.3). User has not chosen.
- **Open-decisions §3** — Authoritative/evaluative full scope: binary + origin_kind metadata (P1) vs richer enum (P2). User has not chosen seven sub-decisions (3.A through 3.G).
- **Coherence Loop framework full specification** — User authorised this work to happen in the FOL chat as an exception to the "FOL-scope" rule. Framework spec is incomplete; pushback #2 below recommends a different framing before any further specification is produced.

---

## 3. The thirteen pushbacks (open)

Raised in the critical re-evaluation round. None resolved. Severity rated: **High** = blocks correctness or production reality; **Medium** = correct architecturally; **Low** = polish.

| # | Topic | Recommendation | Severity |
|---|---|---|---|
| 1 | Live training was abandoned | Reinstate live + dreaming with provenance-tagged signals; live writes never reach L2 directly (accumulate in L5, migrate after corroborating dream pass). Standard online-learning practice. | **High — corrective** |
| 2 | Coherence Loop as "genetic" | Reframe as **oracle-supervised iterative learning** with **plural strategies**: gradient descent (default for differentiable parameters), evolutionary strategies, GA (only for combinatorial structures), Bayesian optimization (expensive fitness), REINFORCE (for policy generators). Each is an L3 capacity; L4 picks based on the generator's parameter-space shape. The current GA-only framing privileges one strategy and violates the system's own decomposition discipline. | **High — corrective** |
| 3 | WSD as one L3 capacity | Decompose: tokenization, lemma+POS, sense-inventory lookup, **candidate-generator strategies** (each a separate L3 capacity — dictionary-based, neural-LM-based, KB-based, correlation-based), **scorer strategies** (each separate), confidence calibrator. "WSD" is then an L4 pipeline assembled from these. | **Medium — alignment with discipline** |
| 4 | Single `learned-parameters` role-graph | Split: `learned-scalars` (small numeric params, thresholds, vectors), `learned-policies` (decision trees, rule sets, FSCs), `learned-models` (large model artefacts, stored as IRI + hash with actual blobs in external content-addressed store). Real ML platforms do this; pretending one graph fits all parameter sizes doesn't survive contact with a 100MB neural checkpoint. | **Medium — scalability** |
| 5 | L5 holds populations | Add `training-runs` role-graph with checkpointed durability. Long training runs (hours-to-days) don't fit the L5 per-task framing; L4 process memory dies on restart. Honest answer: training state is its own beast and needs explicit checkpoint mechanism. | **Medium — durability** |
| 6 | Multi-sense always carried forward | Top-k with k=1 default; k>1 only when (a) two senses within a small confidence margin AND (b) downstream pipeline has a known disambiguator (like FOL coherence check). Otherwise commit. Otherwise the ledger is intractable. | **Medium — tractability** |
| 7 | Source enum (review §E2) | Reduce to binary `definitional | empirical`. The five-value enum was over-engineered; the operational distinction (immutable-from-FOL vs falsifiable) only needs two. The Kantian baggage was the problem; renaming away from analytic/synthetic is sufficient. | **Low — simplification** |
| 8 | No model-artefact storage story | Pick external blob store + IRI manifest pattern (S3/MinIO + content-addressed hashes; or filesystem with content-addressed naming). FalkorDB cannot reasonably store 500MB BERT checkpoints as node properties. Modern WSD almost always goes neural; this isn't exotic. | **High — production reality** |
| 9 | `context` threading hand-waved | Define typed `CapacityContext` schema with named accessors per capacity family. The current "context carries it" treatment will break under volume — heterogeneous stringly-typed dicts don't scale. Use dependency injection / Python `contextvars` patterns. | **Medium — implementability** |
| 10 | Pipeline-level confidence is the only confidence store | Add capacity-level **performance characterisation** (latency profile, applicability conditions, failure modes) as a separate concept. Different from confidence; auxiliary signal that L4 needs for backend selection. | **Low — signal richness** |
| 11 | DOLCE-locked | Allow parallel foundational ontologies in the L2 ontology metagraph. DOLCE is a 2002-era commitment; BFO is the de facto biomedical standard, UFO handles intentionality cleanly, YAMATO addresses purpose/teleology. Domain ontologies often align better with non-DOLCE foundationals. Locking forces awkward translations. | **Medium — long-term architecture** |
| 12 | No multi-user concurrency model | Specify single-process / multi-process / distributed before more design. The choice constrains: prover backend (in-process vs subprocess), `learned-parameters` write semantics, L4 process-memory placement, session-state sharing. Cheap now, expensive later. | **High — must-decide-soon** |
| 13 | Coherence Loop scope drift | When framework is finalised, formal hand-off to the L4 design chat. This chat was supposed to be FOL-only; user authorised an exception, but cross-system framework owned by a FOL chat creates two parallel sources of truth. | **Low — process** |

---

## 4. System-wide changes already applied to sibling repo

These edits landed in `/Users/henriquealvim/Documents/Claude/Projects/Layered Intelligence/`:

### `layer4_intelligence_design_notes.md`

- **Added** "Task-to-pipeline flow (three-step default, 2026-04-23)" subsection after the existing "Pipeline-finding as an applied process" paragraph. Documents the three-step flow.
- **Added** two new role-graph entries to "New L2 role-graphs implied by L4's responsibilities":
  - `sense-correlations`
  - `learned-parameters`

### `mindsos_knowledge_handoff.md`

- **Updated** §12 header from "Five new roles" to "Seven new roles"; subtitle now reads "(driven by L3 vertical slice + L4/L5 design + FOL Layer design)".
- **Added** two rows to the role-graph table: `sense-correlations`, `learned-parameters`.
- **Added** corresponding role constants in §12.1's `identifiers.py` paste-ready code: `ROLE_SENSE_CORRELATIONS`, `ROLE_LEARNED_PARAMETERS`.
- **Added** corresponding schema-builder entries in §12.1's `bootstrap.py` paste-ready code.

**Note:** these changes are now flagged for re-examination because pushback #4 (above) recommends splitting `learned-parameters` into three role-graphs. If pushback #4 is accepted, the sibling-repo edits need a follow-up revision to replace the single `learned-parameters` entry with three.

---

## 5. Decision ledger from this chat (chronological)

For audit / context. Each entry: decision text, my critical re-evaluation status.

1. **WSD is L3 capacity, not an L2 role-graph.** Status: agreed too quickly. Pushback #3 — needs further decomposition.
2. **`fol-rules` continuously updated by L4 with synthetic rules** (not just seeded). Status: holds. But: needs confidence threshold + provenance gate so L4 can't just append rules unchecked. Add to open issues.
3. **Coherence Loop algorithms ALL in L3, L4 orchestrates, L5 holds populations, L2 holds converged.** Status: partially correct (algorithms in L3 = correct), partially contested (L5 placement in pushback #5; framework framing in pushback #2).
4. **Live training abandoned, dreaming-only.** Status: contested. Pushback #1.
5. **L4 task-to-pipeline three-step flow.** Status: holds as default. Caveat: doesn't handle multi-pattern, ensemble, or hybrid pipelines explicitly.
6. **Sense-correlations as INPUT to WSD.** Status: holds. Caveat: "promote multiple assumptions when ambiguous" is contested by pushback #6.
7. **Coherence Loop full design in this chat.** Status: scope decision; user-authorised. Pushback #13 about the parallel-sources-of-truth risk.
8. **Single `learned-parameters` graph.** Status: contested. Pushback #4.
9. **`_drafts/` folder organisation.** Status: holds.
10. **Authoritative/evaluative rename.** Status: holds. Names not literature-grounded, but acceptable.

---

## 6. Things that should have been raised but weren't

In addition to the thirteen pushbacks above:

- **Confidence threshold for L4-appended rules to `fol-rules`.** L4 cannot just write synthetic rules. They should enter as `hypothetical` and graduate via Coherence Loop signal accumulation.
- **Definition of "match" between a current task and a `task-pattern` / `promoted-pipeline`.** The three-step flow assumes this is well-defined; it isn't yet specified. Adapting requires a similarity metric.
- **Failure of pipeline-finding fallback policy.** When step 3 (adapt-or-generate) fails, what's the fallback? Surface to user? Try another pattern? Mark task unsolvable?
- **Validation that the FOL ledger fits in memory.** Long-running tasks with frequent assumptions can exhaust working memory. No back-pressure mechanism is specified.
- **Audit log for L2 writes.** L4 can write `memories`, `task-patterns`, `promoted-pipelines`, `sense-correlations`, `learned-parameters`, `fol-rules`. No audit trail is committed. For compliance / debugging / rollback, this matters.
- **Test data strategy for Coherence Loop fitness evaluation.** Training off consolidated memories means: who curates the training set? Cold start is unaddressed.

---

## 7. My self-critique of this chat's process

For the next chat to watch for:

- I exhibited classic LLM agreement-bias multiple times. When the user pushed on a decision, my default was to fold and produce elaborate scaffolding around the new position. The user issued the critical-thinking instruction late, partly in response to this pattern.
- I produced large documents (`fol_capacity_design_plan.md`, `fol_example_3_detailed_walk.md`, `fol_open_decisions_2026_04_23.md`) before settling foundational decisions. This created sunk-cost pressure to keep scaffolding rather than challenge premises. The next chat should resist this — defer documentation until decisions are firm.
- I treated "the user said it" as load-bearing evidence. It isn't. Field-knowledge and internal consistency are.
- I added "system-wide implication" tags as a partial hedge but kept ratifying decisions I should have contested.
- I wrote the §VI critical re-evaluation table only after the user issued the critical-thinking instruction. Earlier critical thinking would have prevented several recoverable-but-real errors.

---

## 8. Recommended next steps for the new chat

In dependency order. Each of these should be addressed before further specification work.

1. **Resolve pushback #12 (concurrency model).** Single-process / multi-process / distributed. This constrains everything below.
2. **Resolve pushback #1 (live training).** Reinstate or confirm dreaming-only with explicit field-knowledge reasoning. Don't accept a "just because" answer in either direction.
3. **Resolve pushback #2 (Coherence Loop framing).** Plural strategies vs single GA. If plural, the L3 capacity catalogue gets new strategy entries (gradient descent step, ES step, etc.) and L4's choice space expands.
4. **Resolve pushback #8 (model-artefact storage).** External blob store + manifest pattern. Decide concretely.
5. **Resolve pushback #4 (learned-parameters split).** Three role-graphs or one. If three, revise the sibling-repo edits accordingly.
6. **Resolve pushback #3 (WSD decomposition).** Sub-capacities for tokenization, lemma+POS, candidate-gen strategies, scorer strategies.
7. **Resolve open-decisions §2 (analytic-rule contradictions).** User has six options on the table.
8. **Resolve open-decisions §3 (authoritative/evaluative scope).** P1 vs P2; seven sub-decisions.
9. **Resolve pushback #6 (multi-sense top-k).**
10. **Resolve pushback #5 (training-runs durability).**
11. **Resolve pushback #9 (typed `CapacityContext`).**
12. **Resolve pushback #7 (binary rename instead of source enum).**
13. **Resolve pushback #11 (parallel foundational ontologies).**
14. **Resolve pushback #10 (capacity performance characterisation).**
15. **Resolve pushback #13 (hand-off process for the Coherence Loop framework).**

Once 1–8 are settled, the design plan in `_drafts/fol_capacity_design_plan.md` and the Example 3 walk in `_drafts/fol_example_3_detailed_walk.md` need targeted revisions to absorb the changes. Avoid wholesale rewrites — diff and patch.

---

## 9. File map (project root and `_drafts/`)

```
/Users/henriquealvim/Documents/Claude/Projects/First Order Logic Layer for MindsOS/
├── HANDOFF.md                              ← this file (entry point for the new chat)
├── fol_capacity_handoff.md                 ← original legacy-model design (historical input only)
└── _drafts/
    ├── fol_capacity_review.md              ← first critical pass over the legacy handoff
    ├── fol_capacity_design_plan.md         ← interface-level design + 5 example walks (contested in places)
    ├── fol_example_3_detailed_walk.md      ← pedagogical end-to-end walk (contested in places — Phase 0 has been corrected once)
    ├── fol_open_decisions_2026_04_23.md    ← decision menu; §1 partially answered, §2/§3 deferred
    └── mindsos_layer_summary.md            ← layer overview reference (user said do not revise)
```

External (sibling system, edited 2026-04-23):
```
/Users/henriquealvim/Documents/Claude/Projects/Layered Intelligence/
├── layer4_intelligence_design_notes.md     ← gained 3-step flow + 2 role-graphs
└── mindsos_knowledge_handoff.md            ← §12 expanded from 5 to 7 role-graphs
```

The Layered Intelligence repo also contains canonical L0–L5 docs that the FOL design depends on (`mindsos_capacity_handoff.md`, `mindsos_capacity_adrs.md`, `layer5_mental_model_design_notes.md`, `mindsos_knowledge_handoff.md`, etc.). Read on demand, not upfront.

---

## 10. One thing the new chat should NOT do

**Do not produce more documentation before resolving the open pushbacks.** The current pile of `_drafts/` files exceeds what the design state can support. Any further document inflation adds revision cost without proportional clarity. Resolve foundations first; document second.

---

*End of handoff. Stay critical.*
