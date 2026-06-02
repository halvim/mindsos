# FOL — Open Design Decisions (2026-04-23)

**Purpose.** Three topics you asked to revise, each presented with: current state → alternatives → my recommendation → decision points for you. Nothing in here changes the code yet. When you pick, I'll fold the decisions into the handoff, review, and design plan.

**Topics.**

- §1. **Coherence Loop** — replace the "GAN-analogous" loop with a genetic learning capacity, L4-initialised, applied across every generator in the system.
- §2. **Analytic-rule contradictions** — you disagreed with flag-and-punt; here is the full current design and the alternatives.
- §3. **Authoritative vs evaluative roles** — apply your rename (canonical→authoritative, operational→evaluative) and pin the open scope questions.

---

# §1. Coherence Loop — Genetic Learning Capacity

## 1.1 What the legacy model committed (handoff §4.8, §13)

The legacy model named this the **GAN-analogous coherence loop**. Its committed shape:

- **Generator:** WSD's sense-ranking model (one generator, fixed identity).
- **Discriminator:** the FOL validation pipeline running in L5 after every ledger update.
- **Training signal:** sense-assumption verdict from `validate_assumption`:
  - *confirmed* (promoted to `inferred`) → positive signal
  - *retracted* (contradicted) → negative signal
  - *undetermined* (stays `assumed`) → no signal
- **Training cadence:** dreaming — replay *consolidated memories* from `L2.memories`, not the live ledger, for clean causality.
- **Weighting:** canonical confirmations weighted higher than operational.
- **Parameter storage:** tentative `L2.wsd-model` role-graph.
- **Pluggability:** none — the loop is WSD-specific.

## 1.2 What the review reframed (review §E1, §B1)

Two problems with the "GAN" framing:

- A GAN has **two** trainable networks adversarially pushing each other. Here the discriminator is a fixed logical-validation pipeline — it does not train. That's *distant supervision via a downstream oracle*, not adversarial learning.
- The "gradient" on discrete sense choices is actually a policy-gradient / REINFORCE shape, not a GAN loss.

The review recommended renaming to "oracle-distant-supervision." You have now renamed it to **Coherence Loop** — adopted. Further: you want the loop to be a **reusable genetic-learning capacity**, parameterisable over the target generator.

## 1.3 New proposal — Coherence Loop as a genetic-algorithm framework

### 1.3.1 The shape

Treat the Coherence Loop as a generic, population-based evolutionary learning framework. Every invocation of it is parameterised by:

| Parameter | What it names | Example |
|---|---|---|
| `target_generator` | Which subsystem's parameters are being evolved | WSD sense-ranker; pipeline generator; priority-rule chooser |
| `population_shape` | What a "candidate" looks like | weight vector; pipeline DAG; decision tree |
| `fitness_fn` | How oracle feedback translates to a scalar | confirmed/retracted ratio over N samples |
| `operator_config` | Which selection/crossover/mutation strategies run | `top_k` + `vector_interpolation` + `gaussian_noise` |
| `population_size` | How many candidates per generation | 32, 64, 128 |
| `generation_budget` | Max generations per training session | 50 |
| `oracle_source` | Where fitness evaluations come from | consolidated memories; live-but-sandboxed ledger |

### 1.3.2 The algorithm (one generation)

```
Input: population P_n (of size N), oracle O, operator_config ops
Output: population P_{n+1}

1. For each candidate c in P_n:
     score[c] := fitness_fn(c, O)                     ← oracle-supervised
2. parents := ops.selection(P_n, score)               ← e.g. tournament, top_k
3. children := []
4. While |children| < N:
     p1, p2 := pick two from parents
     child := ops.crossover(p1, p2)
     child := ops.mutation(child)
     children.append(child)
5. Optionally keep top-M elites from P_n (elitism)
6. P_{n+1} := elites ∪ children (trimmed to N)
```

Standard GA. The novelty is that **the fitness function is the coherence pipeline** — candidates that produce senses / pipelines / rules / assumptions consistent with the rest of the ledger and with memorised successful runs survive.

### 1.3.3 Where each piece lives

Applying the fixed-vs-learned discipline (L3 mechanics, L4 policy, L5 nothing-cross-task, L2 learned-state-at-rest):

**L3 — fixed mechanics** (each a pure capacity under `learning_methods`):

| IRI | What it does |
|---|---|
| `capacity:learning_methods:coherence_loop.selection.top_k` | Keep the k highest-fitness candidates |
| `capacity:learning_methods:coherence_loop.selection.tournament` | Repeated random-draws, keep winners |
| `capacity:learning_methods:coherence_loop.selection.fitness_proportional` | Roulette-wheel |
| `capacity:learning_methods:coherence_loop.crossover.vector_interpolation` | For numeric weight vectors |
| `capacity:learning_methods:coherence_loop.crossover.subgraph_exchange` | For pipeline DAGs |
| `capacity:learning_methods:coherence_loop.crossover.subtree_exchange` | For decision-tree policies |
| `capacity:learning_methods:coherence_loop.mutation.gaussian` | Numeric perturbation |
| `capacity:learning_methods:coherence_loop.mutation.bit_flip` | For binary policies |
| `capacity:learning_methods:coherence_loop.mutation.constraint_preserving` | Mutate-then-repair for structured candidates (e.g., valid pipelines only) |
| `capacity:learning_methods:coherence_loop.evaluate_fitness` | Given a candidate and a stream of oracle verdicts, computes a scalar |
| `capacity:learning_methods:coherence_loop.step` | Runs ONE generation: takes population + fitness scores + ops_config, returns new population. Pure function. |
| `capacity:learning_methods:coherence_loop.compose_fitness_fn` | Builds the per-generator fitness function from an oracle spec |

**L4 — process memory + policy**:

- Owns the **population** for each active (target_generator, task-domain) pair — this is learned state, stays out of L3.
- Decides the **dispatch schedule**: which generators to evolve when, how long to run, how often to run.
- Picks **which operators** (selection / crossover / mutation variants) to use for each generator — parametric choice, L4-picks-from-L3-options.
- Holds the **oracle source**: routes to consolidated memories during dreaming; to a sandbox ledger during online learning.
- Translates **oracle verdicts into fitness contributions** — the per-verdict weighting (authoritative > evaluative, recent > old, etc.).
- Writes evolved parameters back to **L2** on each generation's convergence signal.

**L2 — persisted learned state** (per-generator role-graphs):

- `wsd-model` (already proposed)
- `pipeline-templates` (new — candidate pipeline structures with fitness)
- `priority-policies` (new — learned priority-rule-chooser policies)
- `ingestion-combiners` (new — learned ingestion-role combine-signals policies)
- `gap-scorer-weights` (new — weights for gap-relevance scorers)
- etc.

Each role-graph holds current + historical generations (versioned via L1's `register_version_graph` / `activate_version`).

**L5 — nothing directly**, but:

- L5's ledger is the substrate the oracle evaluates against when the Coherence Loop runs online (rare — mostly dreaming, which is L2-memories-sourced).

### 1.3.4 A visual of one Coherence Loop instance

```
     ┌───────────────────────────────────────────────────────────┐
     │                          L4                                │
     │                                                            │
     │   ┌─────────────────────────────────────────────────────┐  │
     │   │   Coherence Loop instance for target_generator=WSD  │  │
     │   │                                                      │  │
     │   │   population P_n  ───────┐                           │  │
     │   │        │                 │                           │  │
     │   │        ▼                 │                           │  │
     │   │   ┌────────────┐         │                           │  │
     │   │   │ dispatch   │         │                           │  │
     │   │   │ fitness    │         │                           │  │
     │   │   │ eval       │         │                           │  │
     │   │   └──┬─────────┘         │                           │  │
     │   └──────│───────────────────│───────────────────────────┘  │
     │          │                   │                              │
     │          ▼                   ▼                              │
     │   invoke capacity:  invoke capacity:                        │
     │   learning_methods: learning_methods:                       │
     │   coherence_loop.   coherence_loop.                         │
     │   evaluate_fitness  step                                    │
     │          │                   │                              │
     │          │                   ▼                              │
     │          │             new population P_{n+1}               │
     │          │                   │                              │
     └──────────│───────────────────│──────────────────────────────┘
                │                   │
                │                   │
     ┌──────────▼───┐   ┌───────────▼──────┐
     │ L2.memories  │   │ L2.wsd-model     │
     │ (oracle for  │   │ (candidate store │
     │  fitness)    │   │  — population    │
     │              │   │  snapshot on     │
     │              │   │  convergence)    │
     └──────────────┘   └──────────────────┘
```

Nothing in L3 knows about "populations" or "generations" as persistent concepts — L3 only offers pure-function step / mutate / crossover / select / eval operators. L4 owns the long-running state and the schedule. Same pattern you already use for every other learned-state concern.

## 1.4 Every generator in the system — full inventory

You asked me to check what else could use the Coherence Loop. Here's everything I found, grouped by what a "candidate" looks like.

### 1.4.1 Content generators (candidate = content produced)

| Generator | Candidate shape | Fitness signal (from oracle) |
|---|---|---|
| **WSD sense-ranker** | Parameter vector for scoring (sense, context) pairs | Fraction of sense-assumptions promoted vs retracted by `validate_assumption` |
| **Abduction strategies** (`abduce.minimal`, `abduce.prime_implicates`, `abduce.kb_directed`) | Strategy-specific parameters (bound, template weights) | Fraction of abduced assumptions later confirmed by incoming observations |
| **Rule-template generator** (`enumerate_rule_templates_matching` + `instantiate_rule_template` + `assess_template_coverage`) | Template library entries + coverage weights | Number of generated rules that ingest as active vs. fall back to `pending_validation` or never get promoted |
| **Hypothetical-rule generator** (post-review C2 decomposition) | Same as above, trained end-to-end | Rate at which hypothetical rules reach `active` status via accumulating support |
| **Purpose / cause template library** (U5.2 `lookup_purpose_templates_for_event`) | Template set per event type | Rate at which abduced purposes match user-validation or yield successful downstream plans |
| **Coreference resolver** (upstream, outside FOL strictly but a generator the loop can serve) | Resolver parameters | Rate at which the FOL translator's unification succeeds on resolved references (`emit_coreference_training_signal` U5.4 already plumbs this) |
| **Syntactic parser** (upstream) | Parser parameters | Similar — downstream-FOL-unification success is the oracle |

### 1.4.2 Selector / policy generators (candidate = policy over choices)

| Generator | Candidate shape | Fitness signal |
|---|---|---|
| **Pipeline Generator** (ADR-023 proposed) | Pipeline DAG template / rule-set | Task-outcome success × cost-efficiency on completed tasks |
| **Priority-rule chooser** (which of `observed_first`, `source_trust`, `recency`, ...) | Decision tree / learned classifier over conflict features | Post-revision ledger-health (stays consistent, preserves high-trust observations) |
| **Ingestion-role combine-signals chooser** (`conservative`, `trusted_source`, `teaching_session`, …) | Policy over signal-feature space | Rate of correctly-classified ingestion roles (compared against admin-override corrections) |
| **Tense-to-temporal strategy chooser** (Reichenbach vs Allen vs relative_to_now) | Feature → strategy mapping | Rate at which translated temporal constraints are consistent with the surrounding ledger |
| **Default-category fallback chooser** (`heuristic_from_morphology` vs `physical_endurant_fallback` vs …) | Morphology-feature classifier | Rate at which default assignments later survive human confirmation or consistent downstream inference |
| **Prover-backend chooser** (`consistency.resolution` vs `consistency.tableau` vs `consistency.smt_bounded`) | Feature → backend mapping per ledger shape | Wall-clock × correctness — backend picked should terminate and agree with slower-but-trusted backends |

### 1.4.3 Score / weight generators (candidate = weight vector)

| Generator | Candidate shape | Fitness signal |
|---|---|---|
| **Gap-relevance scorer weights** (`gap_relevance.next_input_alignment`, `goal_alignment`, `memory_weighted`) | Per-scorer weight vectors | Correlation between scored-gap relevance and downstream-pipeline use of that gap |
| **Source-trust scores** | Per-source-id weights | Rate at which high-trust sources' observations survive `validate_assumption` vs low-trust ones; calibration against admin-override adjustments |
| **Confidence tracker for promoted pipelines** | Per-pipeline success-rate estimator | Brier score / calibration error on actual task outcomes |
| **Memory retrieval rankers** | Ranker weights over memory features | Downstream-task success when top-k memories are used |
| **Negative-closure heuristic** (`populate_negative_closure` completeness assumption) | Per-session / per-predicate-family completeness threshold | Rate at which closure assumptions later retract due to contradicting observations |

### 1.4.4 Summary

Sixteen generator categories identified across the system. Every one of them is a candidate for Coherence-Loop-driven evolution. The framework's value compounds with each: one training infrastructure, sixteen applications, no per-generator bespoke machinery.

Generators that are **most valuable to prioritise** for initial Coherence Loop deployment:

1. **WSD sense-ranker** — immediate oracle (every `validate_assumption` call); highest-volume training signal.
2. **Pipeline Generator** — big pay-off when working, but depends on ADR-023 landing and on enough completed tasks for meaningful fitness.
3. **Source-trust scores** — straightforward, high-leverage, small parameter space.
4. **Negative-closure heuristic** — safety-critical (bad completeness assumption produces confident-but-wrong verdicts), evolvable, small parameter space.

## 1.5 Decision points for you (§1)

| # | Decision | Options | My recommendation |
|---|---|---|---|
| 1.A | Name: commit to "Coherence Loop" everywhere? | a) Coherence Loop; b) Keep GAN-analogous as subtitle too; c) Something else | (a) — adopt. |
| 1.B | Is the framework genuinely genetic (population-based with selection/crossover/mutation) or a broader "iterative evolutionary" umbrella? | a) Strict GA; b) GA as one strategy among several (CMA-ES, evolutionary strategies, Bayesian opt); c) Umbrella "evolutionary" term | (b) — design the step API so GA is the v1 strategy and non-GA evolutionary methods can slot in later. Matches the pluggable-strategy discipline already used for provers and priorities. |
| 1.C | Do Coherence Loop operators live in L3 as I've proposed, with populations in L4? | a) Yes (pure mechanics L3, stateful L4); b) Everything in L4 (simpler but violates fixed/learned discipline); c) Everything in L3 (requires threading state through context — ugly) | (a) — matches every other learned-state handling pattern in the system. |
| 1.D | Which generators should get Coherence Loop instances in v1? | Pick 1+ from the 16 identified | **WSD + source-trust + negative-closure** for v1. Pipeline Generator waits on ADR-023. |
| 1.E | Where do the evolved parameters live in L2? | a) One role-graph per generator (proposed); b) Single `learned-parameters` role-graph with sub-namespaces; c) Combine by generator category | (a) — matches the existing pattern (`wsd-model`, `sense-correlations`). Easier versioning. |
| 1.F | Oracle source during training? | a) Consolidated memories only (strict); b) Consolidated + current sandboxed task; c) Live ledger allowed | (a) — matches the legacy commitment. Online learning from the live ledger risks positive-feedback loops. |
| 1.G | Fitness-verdict weighting: honour authoritative > evaluative? | a) Yes (inherit legacy commitment); b) Uniform weighting; c) Parametric — L4 picks per target | (a) — preserves the write-boundary's epistemic hierarchy. Authoritative corrections are more informative training signal. |

---

# §2. Analytic-Rule Contradiction Handling — You Disagreed

## 2.1 What the legacy model committed (handoff §4.2, §5.4, §5.8)

Every rule in `fol-rules` has a **provenance** field:

- **analytic** — "true by virtue of what the concepts mean." Derived from ontology class relationships (e.g., `∀x. human(x) → mortal(x)` follows from `human ⊏ mortal` in the ontology's taxonomy).
- **synthetic** — "true by virtue of how the world is." Added by observation, reasoning, or learning.

Synthetic rules additionally carry a **status** field: `active | hypothetical | pending_validation | falsified`.

**Analytic rules have no status field. They are immutable within the FOL layer.**

When an **authoritative** observation contradicts an **analytic** rule, the design does **not** falsify the rule. Instead:

```
fol.flag_analytic_contradiction(rule, observation)
  → DS_WRITE_INTENT (to problem-trace, with ontology_revision_pending tag)
    + DS_SIGNAL_RECORD (so L4 knows to surface the anomaly)
```

The ontology-revision workflow is **outside** the FOL layer. A human or a separate ontology-management pipeline picks up the flag and decides:

- Was the ontology's class relationship wrong? → revise the taxonomy
- Was the observation misclassified? → retract or retag
- Is there a nuance the ontology didn't capture? → refine the rule

No auto-application; no immediate ledger change.

## 2.2 What this posture assumes — and why you might disagree

The posture assumes:

- **A1.** Ontology is *sacred* — changing it requires human review, because an incoherent ontology corrupts everything downstream.
- **A2.** Analytic rules are *epistemically privileged* — they follow from concept-meanings, not from contingent observation, so a contradicting observation is more likely wrong than the rule.
- **A3.** The FOL layer should not be an actor in ontology maintenance — it should only *detect* anomalies and *route* them to a separate workflow.

Possible reasons for disagreement:

- **D1.** The binary "analytic" vs "synthetic" is philosophically brittle (my review §E2 already raised this — Quine's critique of the analytic/synthetic distinction applies: many "analytic" ontology rules are actually empirical regularities dressed as definitions).
- **D2.** "Immutable within FOL" means the system is paralysed in the face of authoritative new information that contradicts the ontology — the FOL layer can't even propose a repair.
- **D3.** "Flag and punt" is slow and human-bottlenecked. In a deployed system, waiting for ontology-revision creates dead-letter anomalies that accumulate.
- **D4.** There's no principled difference between "analytic" and "synthetic" from the FOL prover's perspective — it just applies classical inference to rules. Treating analytic rules specially is a social commitment, not a logical one.
- **D5.** The mechanism for *detecting* analytic contradiction currently depends on a provenance field the translator is expected to stamp — but the translator may not always know whether a rule it inherits is analytic. This creates silent errors.
- **D6.** In Phase D.1 of Example 3, the hypothetical refutation of the law (Smith paid on time) was absorbed cleanly by the synthetic-rule machinery. Why should an ontology-derived rule (e.g., "all tenants are persons") be treated as immune to the same correction mechanism?

Let me know which of D1–D6 you find compelling, or describe your pushback in your own words.

## 2.3 Alternatives on the table

### Option A — Status quo (flag-and-punt)

*As described above.* Analytic immutable; synthetic falsifiable; contradictions with analytic rules raise a flag, ontology workflow handles.

- **Pro:** Clean separation of concerns; ontology integrity is protected; safe.
- **Con:** Slow, human-bottlenecked; paralyses in high-volume authoritative ingestion; philosophically brittle.

### Option B — Promote analytic rules to falsifiable

Drop the analytic-vs-synthetic distinction for immutability. *Every* rule in `fol-rules` carries a status field; *every* rule can be falsified by an authoritative contradicting observation.

Provenance is retained (so we know where the rule came from), but doesn't gate falsification.

- **Pro:** Uniform treatment; system repairs itself from authoritative evidence.
- **Con:** Easier for bad authoritative input to corrupt ontology-derived rules; loses the "ontology sacred" safeguard.

### Option C — Authoritative-gated falsification of analytic rules

Same as B, but the only rule that can falsify an analytic rule is a **canonically-authoritative** observation (and a high-confidence one). Evaluative or sensor-observed contradictions still flag without auto-applying.

- **Pro:** Balances B's self-repair with A's safeguards; maps onto the ingestion-role discipline (§3).
- **Con:** Requires the authoritative pipeline to be trusted enough.

### Option D — Drop the analytic/synthetic binary; use a `source` enum

Per my review §E2. Replace `provenance: analytic | synthetic` with `source: ontology_taxonomy | ontology_axiom | observation | learned_pattern | human_declared`.

Each `source` value has its own revision workflow:
- `ontology_taxonomy`: highly protected — flag-and-punt (like current analytic)
- `ontology_axiom`: same
- `observation`: falsifiable by higher-trust observation
- `learned_pattern`: falsifiable; mined for pattern revision during dreaming
- `human_declared`: flag-and-confirm (human notified, confirms or revises)

- **Pro:** Rich provenance, tailored workflow per source, no philosophical baggage.
- **Con:** More types to track; each workflow is a small L3/L4 policy.

### Option E — Two-stage for analytic: propose a refinement, then flag

When an authoritative observation contradicts an analytic rule, the system first attempts to refine the rule (add an exception clause) within FOL. If refinement succeeds and the refined rule is consistent with the rest of the ledger + all prior observations, the refinement is proposed (not auto-applied) with high confidence. If refinement fails, the original flag-and-punt fires.

- **Pro:** Turns flag-and-punt into flag-with-a-proposed-fix; reduces human burden.
- **Con:** Auto-refinement of ontology-derived rules is a non-trivial operation; risk of wrong refinements ossifying.

### Option F — Your own alternative

Describe the shape you actually want.

## 2.4 Decision points for you (§2)

| # | Decision | Options | My recommendation |
|---|---|---|---|
| 2.A | Which option? | A / B / C / D / E / F | **D** — drop the analytic/synthetic binary in favour of a source enum, because it preserves the protection where it matters (ontology-taxonomy, ontology-axiom) while allowing richer workflows elsewhere. **Combine with E** for the refinement attempt before flagging. |
| 2.B | Should the workflow *ever* auto-apply without human confirmation? | a) Never; b) For `source=observation`-vs-`source=observation` conflicts where both are evaluative, yes; c) For high-confidence authoritative vs lower-trust, yes | (b) — keep auto-apply bounded to the cases the existing priority capacities already handle (review §B3–§B4 precedent). |
| 2.C | Who files / handles the flag when flagging is chosen? | a) Trace sink + admin tool; b) User-notifier; c) Dedicated ontology-revision capacity family | (a) in v1; (c) as the human workflow matures. |
| 2.D | If we drop the analytic/synthetic binary (Option D), do we rename the role-graph? | a) Keep `fol-rules` as-is; b) Split into `ontology-rules` / `observation-rules` / `learned-rules`; c) One graph, sharper indexing | (a) — one graph, one node type, `source` field drives the workflow. |

---

# §3. Authoritative vs Evaluative Roles (rename applied)

## 3.1 The rename

You have committed:

- **source-of-truth** = **authoritative** (replaces "canonical")
- **use** = **evaluative** (replaces "operational")

I agree these names are clearer. The mechanism is unchanged; only the labels change.

## 3.2 What the design currently commits (after rename)

### 3.2.1 Definitions

- **authoritative** — the speaker is presenting the statement *as truth*. The system should treat it with high trust; if the session is so empowered, it may update L2 via the authoritative-ingestion pipeline.
- **evaluative** — the speaker is making a *claim to be evaluated* against current knowledge. The system may produce verdicts (entails / contradicts / independent) but **never writes L2**. All ledger activity stays in L5.

### 3.2.2 Provenance field

Every `DS_FOL_STATEMENT.provenance.ingestion_role` carries one of the role labels.

### 3.2.3 L3 capacity (decomposed per review C1)

```
capacity:trace:classify_ingestion_role.detect_mode_marker
  → IngestionRole | None

capacity:trace:classify_ingestion_role.extract_speech_act_features
  → Mapping[str, str]

capacity:trace:classify_ingestion_role.extract_session_role_context
  → Mapping[str, str]

capacity:trace:classify_ingestion_role.combine_signals.{policy}
  → IngestionRole
```

Four policies identified so far:
- `conservative` — default; requires strong positive signal for authoritative; otherwise evaluative.
- `trusted_source` — for sessions whose source is pre-vetted as trustworthy.
- `teaching_session` — for legal/scientific-import sessions where declarative-generic-deontic speech acts count as authoritative by default.
- `sensor_feed` (proposed) — for automated input streams where each observation is implicitly authoritative under a schema.

### 3.2.4 Authority check

Before L4 dispatches an authoritative ingestion pipeline (the one that might emit L2 writes), it checks whether the session holds `CAN_WRITE_AUTHORITATIVE` (previously called `CAN_WRITE_CANONICAL`).

This capability is a **proposed** Server-layer ADR. It is load-bearing for every authoritative ingestion path — including Phase A of Example 3. It must be filed and Accepted before implementation begins.

### 3.2.5 Default

**Evaluative** is the conservative default. Treating an evaluative statement as authoritative could corrupt L2 from unauthorised input; the reverse risks only inconvenience (the system produces a verdict instead of updating its knowledge).

### 3.2.6 Weighting in Coherence Loop (see §1)

Authoritative confirmations are weighted higher than evaluative in the Coherence Loop's fitness calculation. This is a policy in L4's fitness-translation step; L3 mechanics are role-agnostic.

## 3.3 Scope questions — binary or richer enum?

Review §E3 flagged that the binary may be too narrow. Three cases don't fit cleanly:

- **Sensor observations.** A temperature sensor reports `temperature(room_1, 22_degrees)`. Neither taught nor queried — it's a direct observation from an automated source. Should it be treated as authoritative (it does update knowledge) or evaluative (it's a per-instance claim, not a general rule)?
- **Self-hypothesised statements.** During dreaming, the system proposes a rule from pattern-matching on consolidated memories. Neither external nor a user query.
- **Third-party relay.** A user quotes a source: "The Times says X." Is X authoritative (backed by the Times' authority) or evaluative (the speaker is just reporting)?

Two paths forward:

### Path P1 — Keep binary; use provenance sub-fields for the edge cases

`ingestion_role` stays `authoritative | evaluative`. The distinctions above become sub-fields:

```
provenance = {
  ingestion_role: authoritative | evaluative,
  origin_kind: human_speaker | sensor | dreaming | relayed_source,
  origin_iri: str,                    # who/what originated the statement
  relay_chain: tuple[str, ...] | None,
  ...
}
```

- Sensor: `ingestion_role="authoritative"`, `origin_kind="sensor"`.
- Dreaming: `ingestion_role="authoritative"`, `origin_kind="dreaming"`, status is always `hypothesised` initially.
- Relayed: `ingestion_role="authoritative"` or `"evaluative"` depending on the speaker's stance, with `relay_chain` populated.

### Path P2 — Expand the role enum

`ingestion_role: authoritative | evaluative | observed_by_sensor | self_hypothesised`.

- Each new role has its own L4 authority check and its own permitted write surface.
- `observed_by_sensor`: may write L5 directly as `observed`; may write to `L2.memories` on consolidation; never writes to `L2.ontology` / `L2.fol-rules`.
- `self_hypothesised`: writes only to L5 with `hypothesised` tag; never writes L2 until promoted through Coherence Loop evolution.

Path P1 is simpler and more extensible (add an `origin_kind` tag, not a role). Path P2 surfaces the distinctions at the capability-gate level.

## 3.4 Authority-check mechanism — detail

The authority check has three pieces:

1. **Capability grant.** At session creation, L0 decides what capabilities the session holds. For a legal-import session: `CAN_WRITE_AUTHORITATIVE`. For a user query session: no such grant.
2. **L4 precondition check.** Before L4 dispatches an authoritative-ingestion pipeline, it checks the session's capabilities. If missing, it either:
   a) refuses and raises to the user,
   b) downgrades to evaluative silently, or
   c) downgrades to evaluative with a trace record.
3. **L3 write-intent emission.** The FOL layer's `DS_WRITE_INTENT` records the `requires_capability` field; L4 executes only if the check passes.

## 3.5 Decision points for you (§3)

| # | Decision | Options | My recommendation |
|---|---|---|---|
| 3.A | Apply rename everywhere — canonical→authoritative, operational→evaluative? | a) Yes; b) No, keep legacy names | (a) — adopt. I'll update handoff, review, design plan, and this walk's documents in one pass. |
| 3.B | Rename `CAN_WRITE_CANONICAL` to `CAN_WRITE_AUTHORITATIVE`? | a) Yes; b) No, keep capability name for inter-layer stability | (a) — consistent with the role name. |
| 3.C | Role enum: binary + origin_kind (P1), or richer enum (P2)? | P1 / P2 | **P1** — binary is the write boundary (write-L2 vs don't). Origin-kind is metadata. Simpler. |
| 3.D | Default role? | a) evaluative (current); b) authoritative; c) None — reject if ambiguous | (a) — matches the safety-first posture. |
| 3.E | If session lacks CAN_WRITE_AUTHORITATIVE but the combine_signals classifier votes authoritative, what happens? | a) Refuse + raise; b) Downgrade to evaluative silently; c) Downgrade + trace record | (c) — fail-safe without being opaque to auditing. |
| 3.F | Does a dreaming-emitted hypothesis ever get to be authoritative? | a) No — always evaluative-equivalent; b) Yes, once survives Coherence Loop convergence; c) Yes, with origin_kind=dreaming flagged | (b) — promote by evidence, not by automatic trust. |
| 3.G | Does a sensor feed count as authoritative? | a) Yes, always; b) Yes but L2-write-scope limited to `memories`; c) No — always evaluative unless paired with user confirmation | (b) — sensors inform but don't teach ontology. |

---

# Summary of open decisions

A compact table for quick reference:

| § | Decision ID | Short form |
|---|---|---|
| 1 | 1.A | Commit to name "Coherence Loop"? |
| 1 | 1.B | Strict GA / pluggable evolutionary / umbrella? |
| 1 | 1.C | L3 mechanics + L4 populations split? |
| 1 | 1.D | Which generators get v1 Coherence Loop instances? |
| 1 | 1.E | One role-graph per generator? |
| 1 | 1.F | Oracle source = consolidated memories only? |
| 1 | 1.G | Authoritative > evaluative weighting? |
| 2 | 2.A | Option A / B / C / D / E / F for analytic-rule handling? |
| 2 | 2.B | Is auto-apply ever allowed? |
| 2 | 2.C | Flag recipient — trace sink / notifier / dedicated family? |
| 2 | 2.D | Keep single `fol-rules` graph or split by source? |
| 3 | 3.A | Apply the rename system-wide? |
| 3 | 3.B | Rename the capability to `CAN_WRITE_AUTHORITATIVE`? |
| 3 | 3.C | Binary + origin_kind (P1) or richer enum (P2)? |
| 3 | 3.D | Default role = evaluative? |
| 3 | 3.E | Classifier-vs-capability mismatch → refuse / downgrade-silent / downgrade-trace? |
| 3 | 3.F | Can dreaming promote hypotheses to authoritative? |
| 3 | 3.G | Sensor observations — authoritative with limited L2 scope? |

---

*End of open-decisions document. Mark your picks and I'll fold them in.*
