# Example 3 — Detailed System Walk-Through

**Example.** *"If the tenant fails to pay rent within 30 days of the due date, the landlord may terminate the lease by giving 14 days' written notice."*

**Operational query (used later in the walk).** *"Tenant Smith hasn't paid rent in 35 days — can the landlord terminate?"*

**What this document does.** This is a full trace of how the MindsOS FOL layer — as specified by `fol_capacity_handoff.md` + `fol_capacity_review.md` + `fol_capacity_design_plan.md` — processes Example 3, end-to-end. Every FOL atom is explained in plain English. Every capacity call is named, with its inputs and outputs. The ledger state is shown after each step. Two phases: (A) canonical ingestion of the law; (B) operational query against the ingested law.

---

## 0. What the system looks like before the example arrives

### 0.1 Relevant L2 role-graphs (read-only during this walk)

L2 is **already populated** when this walk begins. The four core role-graphs it carries are listed below. Nothing here is empty at Phase 0 — the system has been seeded, and Phase A will *add* to `fol-rules`, not *create* it.

| Role-graph | What's in it at Phase 0 | Why the example needs it |
|---|---|---|
| `ontology` (DOLCE + domain extensions) | Categories: `AG` (agent), `PD` (perdurant/event), `ED` (endurant), `Q` (quality/quantity), `T` (time), `ART` (artefact), `SA` (social agent). Relations: `PC` (participation in event), `theme`, `recipient`, `amount`, `due_date`, `party_to`, `acts_on_behalf_of`, etc. Axiom templates keyed by (relation, sort-signature). Every predicate carries `is_time_variant: bool`. | Provides sort tags and axiom templates for translation. |
| `lexicon` (WordNet + DOLCE alignment) | Sense entries — e.g., `tenant.n.01`, `pay.v.01`, `may.v.modal_deontic`, `terminate.v.01` — each mapped to one or more DOLCE categories via the alignments importer. | WSD outputs these sense IRIs; translation looks up categories here. |
| `concepts` (domain concepts) | Legal-domain concepts imported for this session: `lease_agreement`, `rent_obligation`, `notice_period`, `termination_right`, linked to ontology categories. | Grounds domain vocabulary the ontology alone doesn't reach. |
| `fol-rules` (pre-populated with foundational content) | Already carries: **(a)** equality axioms (reflexivity, symmetry, transitivity, substitution); **(b)** sort-discipline axioms derived from DOLCE (e.g., `∀x. PD(x) → ¬ED(x)` — perdurants and endurants are disjoint); **(c)** DOLCE's native axioms translated into rule form (mereology, temporal parthood, participation); **(d)** commonsense-causation / physics rules imported from their role-graphs if linked in; **(e)** any previously-ingested legal rules from other lease-law imports. Phase A will *add* `rule_L001` as a new node in this same graph. | Holds rules as first-class nodes, already active before Phase A. |

Supporting role-graphs also present but not touched by this walk: `sense-correlations`, `wsd-model`, `memories`, `problem-trace`, `promoted-pipelines`, `task-patterns`, `capacity-state`.

### 0.2 L4 state going in

- Session is flagged as a **legal-document-import** session.
- L4 context carries `can_write_canonical = True` for this session (set by the Server layer after an authority check — this is where the CAN_WRITE_CANONICAL capability, currently a filed-but-unaccepted Server ADR, is load-bearing).
- L4 context carries `now_anchor = "now_k0"` (a fresh time anchor IRI).
- L4 context carries `prover_backend = "resolution_inprocess"`, `proof_bound = 2000` (reasonable defaults for small ledgers).
- L4 context carries `ontology_graphs = ("dolce_v1.iri", "legal_domain_v1.iri")` — chained lookup first hits DOLCE, falls back to the legal-domain ontology for terms like "lease" and "rent".

### 0.3 Upstream pipeline output (before FOL sees anything)

The natural-language sentence is first processed by upstream capacities (tokenise → parse → word-sense-disambiguate). FOL consumes their output as a `DS_SENSE_CANDIDATES` value:

```
DS_SENSE_CANDIDATES {
  parse_tree: <conditional clause structure>,
  per_content_node: {
    "tenant":     [(tenant.n.01, 0.95)],
    "pay":        [(pay.v.01, 0.92)],
    "rent":       [(rent.n.02, 0.88)],
    "30":         [(numeric_literal_30, 1.0)],
    "day":        [(day.n.01_duration_unit, 0.97)],
    "due_date":   [(due_date.n.01, 0.99)],
    "landlord":   [(landlord.n.01, 0.98)],
    "may":        [(may.v.modal_deontic, 0.82), (may.v.uncertainty, 0.18)],
    "terminate":  [(terminate.v.01, 0.90)],
    "lease":      [(lease.n.01, 0.99)],
    "14":         [(numeric_literal_14, 1.0)],
    "notice":     [(notice.n.02_legal_document, 0.85)],
    "written":    [(written.a.01_inscribed, 0.91)],
  },
  tense_features: {main_clause: "modal_potential", conditional: "generic_present"},
  utterance_context: {source: "lease_law_2026_import.iri", speaker_role: "legislator"},
}
```

The only lemma with two candidate senses is `may`; the higher-prior deontic sense is the one we'll commit to (and the other is carried as an `assumed`-tagged alternative per §4.8 of the handoff).

---

## Phase A — Canonical ingestion of the law

### A.1 Classify ingestion role (decomposed per review C1)

The first question L4 asks the FOL layer: *is this input teaching us something (canonical) or asking us something (operational)?*

L4 runs the decomposed ingestion-role pipeline:

```
Step A.1.a — fol.trace:classify_ingestion_role.detect_mode_marker
  input:   input_raw = "If the tenant fails to pay rent..."
  context: { ... }
  output:  IngestionRole | None = None
  reason:  No explicit "ingest-as-canonical:" or "query:" marker in the string.

Step A.1.b — fol.trace:classify_ingestion_role.extract_speech_act_features
  input:   parse_tree
  output:  {"mood": "declarative", "aspect": "generic", "modality": "deontic"}
  reason:  The sentence is a generic-present declarative with a deontic modal — the
           linguistic signature of a rule-statement, not a question.

Step A.1.c — fol.trace:classify_ingestion_role.extract_session_role_context
  input:   (reads from context only)
  output:  {"session_role": "legal_import", "speaker_role": "legislator",
            "can_write_canonical": True}

Step A.1.d — fol.trace:classify_ingestion_role.combine_signals.teaching_session
  input:   signals = { mode_marker: None,
                       speech_act: {mood: declarative, ...},
                       session_role_ctx: {session_role: legal_import, ...} }
  output:  IngestionRole = "canonical"
  reason:  Combine-signals policy for teaching sessions: if session_role is
           legal_import and speech_act is a declarative-generic-deontic, treat as
           canonical. The conservative default policy would have required an explicit
           marker; the teaching-session policy is more permissive because L4 has
           already verified CAN_WRITE_CANONICAL is granted on this session.
```

**Why these are decomposed this way.** Each of A.1.a through A.1.d is a purely deterministic function of its inputs (I1, I2 preserved). The *choice* of which combining policy to use (`teaching_session` vs `conservative` vs `trusted_source`) is an L4 decision based on the session's policy assignment — strategy = L3 options, choice = L4 pick.

**Result of A.1:** ingestion role tagged `canonical`. L4 proceeds to translation.

### A.2 Translation — building the FOL statement piece by piece

This is the hardest step in the example. The sentence translates into **one big universally-quantified conditional** with ten-ish conjuncts in its antecedent. Let's build it piece by piece.

The sentence's logical shape is: *"If [antecedent conditions involving a tenant, a landlord, a lease, rent, a due date, and non-payment] then [the landlord is permitted to do something under specific conditions]."*

The key capacity is `capacity:comprehension:compose_statement_from_parse`, but internally it orchestrates many retrievals and combinations. Here's what happens, one sub-step at a time.

#### A.2.1 Sort assignment for each bound variable

For each variable the rule will quantify over, translation looks up its DOLCE category:

```
fol.retrieval:lookup_category_for_sense(sense="tenant.n.01", context={...})
  → "SA"   (tenant is a social agent / role)

fol.retrieval:lookup_category_for_sense(sense="landlord.n.01", context)
  → "SA"

fol.retrieval:lookup_category_for_sense(sense="lease.n.01", context)
  → "ART"  (lease is a contractual artefact — social object)

fol.retrieval:lookup_category_for_sense(sense="rent.n.02", context)
  → "Q"    (rent is a quantity/amount)

fol.retrieval:lookup_category_for_sense(sense="due_date.n.01", context)
  → "T"    (due date is a time)
```

These become the sort tags on the quantifier-bound variables.

#### A.2.2 Axiom template lookup for each relation

For each relation the sentence implies, translation fetches an axiom template:

```
fol.retrieval:lookup_axiom_template_for_relation(relation="party_to", category="SA", context)
  → AxiomTemplate{ atom: party_to(arg_agent, arg_artefact), arity: 2, ... }

fol.retrieval:lookup_axiom_template_for_relation(relation="rent_obligation", category="SA", context)
  → AxiomTemplate{ atom: rent_obligation(arg_tenant, arg_amount, arg_lease), arity: 3 }

fol.retrieval:lookup_axiom_template_for_relation(relation="due_date", category="Q", context)
  → AxiomTemplate{ atom: due_date(arg_quantity, arg_time), arity: 2 }

fol.retrieval:lookup_axiom_template_for_relation(relation="pay_event", category="PD", context)
  → AxiomTemplate{ atoms: [pay(e), PC(ag, e, t), recipient(e, rec), amount(e, q)],
                   temporal: true }

fol.retrieval:lookup_axiom_template_for_relation(relation="Permitted", category="Deontic", context)
  → AxiomTemplate{ atom: Permitted(arg_agent, arg_action, arg_conditions) }
```

Note: `Permitted` is retrieved as a plain 3-ary atom template. The prover will never "understand" what `Permitted` means — it's a syntactic predicate the translator preserves verbatim, as committed in the review (§E7) and Example 3's Part II.5 walk (Part II.P3.3).

#### A.2.3 Temporal arithmetic reduction

The phrase "30 days of the due date" contains date arithmetic. Per design update U3.1:

```
fol.retrieval:lookup_temporal_operator(op="add_days", context)
  → AxiomTemplate{ signature: add_days : T × Q → T }

fol.combination:reduce_temporal_literal(
  formula = t' ≤ add_days(d, 30),
  context={now_anchor: "now_k0"}
)
  → Since d and 30 are variable/constant in context, this stays symbolic:
     t' ≤ add_days(d, 30)
   If d had been a concrete constant (e.g., due_date = 2026-03-19), this would
   collapse to the concrete date 2026-04-18.
```

For the law — which is a generic rule — we keep `add_days(d, 30)` symbolic. It'll reduce when a specific operational query binds `d` to a concrete date.

#### A.2.4 Tense-to-temporal translation

The main clause is in "modal potential" tense ("may terminate"). The conditional is in "generic present" ("if ... fails"). Both are expressible relative to a symbolic time variable; no specific time commitment. L4 picks the `relative_to_now` tense strategy for generic legal rules (not Reichenbach — this isn't narrative):

```
fol.comprehension:tense_to_temporal.relative_to_now(
  parse, now="now_k0", context
)
  → constraints: ∅
  reason: A generic rule has no concrete time binding. The rule itself is
          time-invariant. The temporal variables (t', d) are internal to the
          universal quantification.
```

#### A.2.5 Instantiating the axiom templates into a composed statement

`fol.comprehension:compose_statement_from_parse` now stitches the templates together. Here is the composed formula, annotated clause by clause:

```
∀ t:SA, l:SA, lease:ART, r:Q, d:T.                           [Q1]
    tenant(t)                                                [C1]
  ∧ landlord(l)                                              [C2]
  ∧ party_to(t, lease)                                       [C3]
  ∧ party_to(l, lease)                                       [C4]
  ∧ rent_obligation(t, r, lease)                             [C5]
  ∧ due_date(r, d)                                           [C6]
  ∧ ¬ ∃ e:PD, t':T, p_agent:SA.                              [Q2]
        pay(e)                                               [C7]
      ∧ PC(p_agent, e, t')                                   [C8]
      ∧ p_agent = t  ∨  acts_on_behalf_of(p_agent, t)        [C9]
      ∧ recipient(e, l)                                      [C10]
      ∧ amount(e, r)                                         [C11]
      ∧ t' ≤ add_days(d, 30)                                 [C12]
  →                                                          [->]
    Permitted(                                               [C13]
      l,
      terminate(lease),
      notice_requirement(14_days, written)
    )
```

**What each line means in plain English:**

- **[Q1] `∀ t:SA, l:SA, lease:ART, r:Q, d:T.`** — *For any tenant `t` and landlord `l` (both social-agent sorted), any lease `lease` (artefact sorted), any rent amount `r` (quantity sorted), and any date `d` (time sorted)...* This is the universal quantifier. The sort tags come from DOLCE — they tell the prover which entities these variables can range over, and will pay off performance-wise if the prover is sort-aware.

- **[C1] `tenant(t)`** — *...if `t` is a tenant...* One-argument predicate asserting role membership. The fact that `t` is a tenant of *this particular lease* is handled by [C3] — [C1] alone just asserts the role exists.

- **[C2] `landlord(l)`** — *...and `l` is a landlord...*

- **[C3] `party_to(t, lease)`** — *...and `t` is a party to `lease`...* This is what ties `t` as the *tenant of this specific lease*. DOLCE does not encode role-in-a-relationship directly; `party_to` is a domain-ontology relation we inherit from the legal-domain ontology.

- **[C4] `party_to(l, lease)`** — *...and `l` is a party to `lease`.* Likewise for the landlord.

- **[C5] `rent_obligation(t, r, lease)`** — *...and `t` has a rent obligation of amount `r` associated with `lease`.* Three-argument predicate — the tenant owes the amount under this specific lease.

- **[C6] `due_date(r, d)`** — *...and the rent amount `r` has a due date `d`.* Two-argument functional predicate.

- **[Q2] `¬ ∃ e:PD, t':T, p_agent:SA.`** — *...and there does not exist any event `e` (perdurant/event sorted), at any time `t'`, by any agent `p_agent`...* The negated existential that captures "fails to pay". The reviewer (and the review's §B3) flagged that negated existentials hide the closed-world assumption — this is the clause that will have to be reconciled with `populate_negative_closure` at query time.

- **[C7] `pay(e)`** — *...such that `e` is a payment event...*

- **[C8] `PC(p_agent, e, t')`** — *...and `p_agent` participates in `e` at time `t'`.* `PC` is DOLCE's participation-in-time relation. This is **how time enters the statement**: the event `e` is anchored to the time `t'` via `p_agent`'s participation.

- **[C9] `p_agent = t ∨ acts_on_behalf_of(p_agent, t)`** — *...and `p_agent` is the tenant `t`, or is someone paying on the tenant's behalf.* This is a subtle refinement the translator adds to handle the common case of a third party (e.g., a cosigner, a parent) paying rent for the tenant. Without this disjunction, the rule would be triggerable even when the tenant's representative paid on time.

- **[C10] `recipient(e, l)`** — *...and `l` (the landlord) is the recipient of `e`.* This stops the rule from firing when the tenant paid *someone else* an equal amount.

- **[C11] `amount(e, r)`** — *...and the amount paid in `e` equals the obligated amount `r`.* Stops the rule from firing if the tenant paid part of the rent.

- **[C12] `t' ≤ add_days(d, 30)`** — *...and the payment happened within 30 days of the due date.* `add_days : T × Q → T` is the DOLCE-domain function symbol from A.2.3.

- **[->] `→`** — The conditional: if everything above is the case, then below follows.

- **[C13] `Permitted(l, terminate(lease), notice_requirement(14_days, written))`** — *...the landlord is deontically-permitted to terminate `lease`, subject to the notice requirement of 14 days' written notice.*

  Three nested function-like symbols here:
  - `Permitted` is a 3-ary **predicate** (uninterpreted by the prover — just a syntactic marker).
  - `terminate(lease)` is a **function** producing an abstract action-term from the lease.
  - `notice_requirement(14_days, written)` is a **function** producing an abstract conditions-term from a duration and a notice type.

  The prover treats `Permitted(...)` like any other atom: it can be asserted, retracted, used in entailment chains. It cannot be reasoned about deontically (e.g., the prover will not automatically infer that `Permitted` and `Forbidden` are inconsistent) — that is out of FOL's scope and belongs to a deontic-reasoning sibling capacity family.

#### A.2.6 Putting it all together as a `DS_FOL_STATEMENT`

The composed `Formula` goes into a `DS_FOL_STATEMENT`:

```python
DS_FOL_STATEMENT(
  stmt_id="stmt_A001",
  formula=<the formula above as a nested syntax.Forall / And / Not / Exists tree>,
  epistemic_tag="observed",
  provenance=Provenance(
    source_utterance="lease_law_2026_section_42.iri",
    derived_from=(),
    sense_commitments=(
      ("tenant", "tenant.n.01"),
      ("pay", "pay.v.01"),
      ("rent", "rent.n.02"),
      ("may", "may.v.modal_deontic"),
      ("terminate", "terminate.v.01"),
      ("lease", "lease.n.01"),
      ("notice", "notice.n.02_legal_document"),
    ),
    ontology_rule_id=None,   # this statement IS a rule; no parent rule
    ingestion_role="canonical",
    source_id="lease_law_2026_section_42.iri",
    assumption_kind=None,    # not an assumption
    retraction_reason=None,
  ),
  time_bindings=(),
  is_time_variant=False,      # the rule as a rule is time-invariant
  minted_at="now_k0",
)
```

### A.3 Writing the rule to L2 `fol-rules`

Because the ingestion role is `canonical`, the FOL layer now produces a **write intent** that L4 will execute. Per review B7, L3 never executes writes — it returns a `DS_WRITE_INTENT` and L4 dispatches.

```
fol.combination:archive_canonical_rule(
  stmt = stmt_A001,
  source = "human_declared",
  context
)
  → DS_WRITE_INTENT(
      target = "L2.fol-rules",
      operation = "insert",
      payload = {
        node_shape: {
          antecedent: <the body of the formula minus the consequent>,
          consequent: <the Permitted(...) atom>,
          provenance: "human_declared",
          status: None,            # analytic? synthetic? Rules from statute are
                                   # canonical-by-law but factual-in-the-world —
                                   # per review E2, drop the analytic/synthetic
                                   # binary and use source="human_declared".
          exceptions: [],
          equivalent_forms: [],
          source_evidence: ["lease_law_2026_section_42.iri"],
          falsification_history: [],
        }
      },
      requires_capability = "CAN_WRITE_CANONICAL",
    )
```

L4 validates `requires_capability` against the session's granted capabilities; since `can_write_canonical = True` for this session, L4 executes the write. A new Rule node lands in L2 `fol-rules` at IRI e.g. `fol-rules:rule_L001`.

### A.4 Ledger state after Phase A

```
L2 fol-rules:  pre-existing foundational rules (equality, DOLCE sort-discipline,
               commonsense) + { rule_L001: <tenancy termination rule> }   ← ADDED
L2 ontology:   (unchanged — rule_L001 only references existing categories/relations)
L5 ledger:     empty
  (The law doesn't land in L5 because L5 is per-task working memory. The law is
   permanent knowledge, so it goes to L2. L5 will be populated when an operational
   query uses the rule.)
```

---

## Phase B — Operational query against the ingested law

Now a user asks: *"Tenant Smith hasn't paid rent in 35 days — can the landlord terminate?"*

### B.1 Classify ingestion role

```
Step B.1.a — fol.trace:classify_ingestion_role.detect_mode_marker
  input: "Tenant Smith hasn't paid rent in 35 days — can the landlord terminate?"
  output: None (no explicit marker)

Step B.1.b — fol.trace:classify_ingestion_role.extract_speech_act_features
  output: {"mood": "interrogative", "focus": "Permitted", "polarity": "question"}
  reason: The sentence ends with "?" and the question is whether a Permission holds.

Step B.1.c — fol.trace:classify_ingestion_role.extract_session_role_context
  output: {"session_role": "user_query", "can_write_canonical": False}

Step B.1.d — fol.trace:classify_ingestion_role.combine_signals.conservative
  signals: { mode_marker: None,
             speech_act: {mood: interrogative, ...},
             session_role_ctx: {session_role: user_query, ...} }
  output: IngestionRole = "operational"
  reason: Interrogative speech act + no teaching-session context → default to operational.
```

Operational means: **no writes to L2**. All ledger activity happens in L5 and returns a verdict to L4.

### B.2 Translation of the query

The query has two parts:
- **Fact:** "Tenant Smith hasn't paid rent in 35 days" → ledger observations.
- **Question:** "Can the landlord terminate?" → an entailment target.

Translation produces:

```
Fact — composed into several observed statements:

F1:  tenant(smith)                         [observed; source_id="user_query_001"]
F2:  landlord(jones)                       [observed]
F3:  party_to(smith, lease_7)              [observed]
F4:  party_to(jones, lease_7)              [observed]
F5:  rent_obligation(smith, 1200_usd, lease_7)    [observed]
F6:  due_date(1200_usd, date_2026_03_19)           [observed]
F7:  now_anchor = date_2026_04_23                  [context — not a statement,
                                                    but the anchor for "35 days ago"]

Query (entailment target — not added to ledger as a statement, but submitted as
the goal formula):

G:   Permitted(jones, terminate(lease_7), notice_requirement(14_days, written))
```

**Why Smith's landlord, lease, and amount appear even though the user didn't state them.** Real queries come with session context — the "lease_7", "jones", "1200_usd" bindings are supplied by the L4 pipeline from an upstream case lookup (the pipeline knows which lease the user is asking about). For this walk, assume the pipeline supplied them via `context["case_bindings"]`.

**A subtle point.** The sentence *"Smith hasn't paid rent in 35 days"* is a **negative fact**. The translator does not produce `¬pay(e)` for some specific `e` — that wouldn't capture the universal claim ("no such payment exists"). Instead, the translator:
- Asserts the positive observations (F1–F6).
- Lets the pipeline invoke `populate_negative_closure` at query time to assert `¬pay-by-Smith-to-Jones-within-window` as many `assumed`-tagged statements — i.e., for the window [date_2026_03_19, date_2026_04_23], the closure says "no payment events matching the pattern are known".

### B.3 Fact statements land in L5 ledger

```
L5 ledger after F1–F6 ingestion:
  statements = {
    F1: tenant(smith)                         [observed]
    F2: landlord(jones)                       [observed]
    F3: party_to(smith, lease_7)              [observed]
    F4: party_to(jones, lease_7)              [observed]
    F5: rent_obligation(smith, 1200_usd, lease_7)    [observed]
    F6: due_date(1200_usd, date_2026_03_19)   [observed]
  }
  dependency_graph: {}
  sense_distributions: { ... }
  open_gaps: []
```

`validate_assumption` runs after each insertion; nothing to promote or retract (no contradictions, no assumptions).

### B.4 Retrieve the law from L2

L4 asks: *"which rules in `fol-rules` are potentially relevant?"* A rule-retrieval capacity (whose details are out of scope here — lives in `capacity:retrieval:lookup_rules_by_predicate`) finds `rule_L001` by matching the query's target predicate `Permitted(...)` against the consequent of each rule:

```
fol.retrieval:lookup_rules_by_predicate(
  target_predicate="Permitted",
  context
)
  → [rule_L001]
```

### B.5 Bind the rule to concrete entities

L4 attempts to instantiate `rule_L001` with the concrete entities from the query:

```
fol.derivation:unify(
  rule_antecedent = <quantifier body of rule_L001>,
  query_facts = {F1, F2, F3, F4, F5, F6},
  context
)
  → Substitution = {
      t → smith,
      l → jones,
      lease → lease_7,
      r → 1200_usd,
      d → date_2026_03_19,
    }

fol.derivation:instantiate_universal(
  rule = rule_L001.formula,
  binding = Substitution,
  context
)
  → Formula (the rule with the quantifier peeled off and the substitution applied):

     tenant(smith)
   ∧ landlord(jones)
   ∧ party_to(smith, lease_7)
   ∧ party_to(jones, lease_7)
   ∧ rent_obligation(smith, 1200_usd, lease_7)
   ∧ due_date(1200_usd, date_2026_03_19)
   ∧ ¬ ∃ e:PD, t':T, p_agent:SA.
        pay(e) ∧ PC(p_agent, e, t')
        ∧ (p_agent = smith  ∨  acts_on_behalf_of(p_agent, smith))
        ∧ recipient(e, jones)
        ∧ amount(e, 1200_usd)
        ∧ t' ≤ add_days(date_2026_03_19, 30)
     →
     Permitted(jones, terminate(lease_7), notice_requirement(14_days, written))
```

`add_days(date_2026_03_19, 30)` is now a concrete date: `date_2026_04_18`. Per design update U3.1:

```
fol.combination:reduce_temporal_literal(
  formula = <the instantiated rule above>,
  context={now_anchor: "now_k0", date_arithmetic: enabled}
)
  → Formula (with add_days folded):
    ... ∧ t' ≤ date_2026_04_18 ...
```

### B.6 Populate the negative closure (the "hasn't paid" part)

This is where review §B3 / design update U6.4 earns its keep. The instantiated rule's antecedent requires `¬∃ e:PD, t':T, p_agent:SA. pay(e) ∧ ... ∧ t' ≤ date_2026_04_18` to hold. Under pure open-world FOL, "we have no payment-by-Smith records in the ledger" does NOT entail "no such payment exists." Something must generate the negated assumption.

```
fol.combination:populate_negative_closure(
  predicate_family = "pay",
  ledger = <current L5 ledger>,
  bound_entities = (smith, jones, lease_7),
  context = {
    temporal_window: (date_2026_03_19, date_2026_04_18),
    completeness_assumption: "ledger_is_authoritative_for_this_user_in_this_window"
  }
)
  → DS_ASSUMPTION_CANDIDATES([
      A1: ¬ ∃ e:PD, t':T, p_agent:SA.
            pay(e) ∧ PC(p_agent, e, t')
            ∧ (p_agent = smith ∨ acts_on_behalf_of(p_agent, smith))
            ∧ recipient(e, jones)
            ∧ amount(e, 1200_usd)
            ∧ date_2026_03_19 ≤ t' ≤ date_2026_04_18
          [assumed, assumption_kind=default, retraction_reason=None,
           provenance.derived_from=("closure_over_pay_family",),
           provenance.source_id="populate_negative_closure.v1"]
    ])
```

L4 adds A1 to the ledger at `assumed`-tag. **This is the defeasibility-on-assumptions commitment from handoff §4.1 working concretely.** A1 is defeasible: if later input reveals a payment we didn't know about, `validate_assumption` will retract it. For now, we proceed with it in place.

### B.7 Check entailment

Now the ledger contains all positive facts F1–F6 *plus* the negative closure A1. L4 asks the prover:

```
fol.derivation:entails.bounded(
  ledger = <L5 ledger with F1–F6 observed, A1 assumed>,
  candidate = G                  ← i.e. Permitted(jones, terminate(lease_7), ...)
  bound = 2000,
  context = {prover_backend: "resolution_inprocess"}
)
```

What the prover does internally (pluggable backend — the exact proof search depends on the backend, but the shape is):

1. **Forward-chain** from the ledger: match the instantiated rule's antecedent against F1–F6 ∪ {A1}. Clauses [C1]–[C12] all unify (with A1 satisfying the negated existential [Q2] ∧ [C7]–[C12]).
2. **Fire the rule.** Apply modus ponens: antecedent holds, so the consequent `Permitted(jones, terminate(lease_7), notice_requirement(14_days, written))` is entailed.
3. **Match against `G`.** The entailed consequent is syntactically identical to G.
4. **Return:** `entails`, with an optional proof tree.

```
fol.derivation:entails.bounded → DS_ENTAILMENT_RESULT(
  status = "entails",
  proof_tree = <a tree rooted at G, branching into
                rule_L001 used as: antecedent ↛ consequent; antecedent was
                satisfied by F1–F6 ∪ {A1}>
)
```

### B.8 Return verdict to L4

L4 packages the result and returns it to the caller:

```
Verdict to user: "YES — under lease_law_2026_section_42, the landlord (Jones) is
permitted to terminate lease_7 by giving 14 days' written notice. This permission
follows from:
  - The tenancy facts (F1–F6).
  - The absence of any matching rent payment from Smith to Jones for $1,200 in the
    30-day window after the due date (assumption A1, derived by negative closure).
  - The lease law (rule_L001)."
```

Note that the verdict **explicitly flags the assumption A1** — the user knows the verdict depends on the ledger being complete-enough-to-trust regarding Smith's payments. If Smith produces a receipt, L4 re-ingests it as an observed payment event, `validate_assumption` retracts A1 (it now contradicts an observation), and the verdict reverses.

### B.9 Ledger state at the end of Phase B

```
L5 ledger at end of query:
  statements = {
    F1: tenant(smith)                    [observed]
    F2: landlord(jones)                  [observed]
    F3: party_to(smith, lease_7)         [observed]
    F4: party_to(jones, lease_7)         [observed]
    F5: rent_obligation(smith, 1200_usd, lease_7)       [observed]
    F6: due_date(1200_usd, date_2026_03_19)              [observed]
    A1: ¬∃ e:PD, ...                      [assumed, kind=default]
  }
  dependency_graph: {}     (A1 does not derive from any observed stmt; it's a closure)
  sense_distributions: { ... }
  open_gaps: []

L2 fol-rules:  pre-existing foundational rules + rule_L001   (unchanged from Phase A)
```

On task completion, this ledger consolidates into L2 `memories` as a frozen record, per handoff §8.

---

## Phase C — What the system does NOT do (on purpose)

Three questions that **look** like they belong in Example 3 but don't, and why the design routes them elsewhere:

### C.1 "Is Permitted(...) and Forbidden(...) the same agent/action inconsistent?"

**Not FOL's job.** `Permitted` and `Forbidden` are syntactic predicates to the FOL prover. The prover will not automatically flag them as inconsistent. Deontic consistency is handled by a sibling L3 family (not scoped here) that runs deontic-modal inference on rules from `fol-rules` tagged with deontic-head consequents.

### C.2 "Should the landlord terminate?"

**Not FOL's job.** The question asks about a practical-reasoning decision — weighing cost, risk, reputation, tenant relations. FOL produces the verdict `Permitted(...)`, and the practical-reasoning pipeline (the one exercised in Example 6) takes it as one input among others.

### C.3 "Execute the termination."

Obviously not the FOL layer's job. Action execution is a separate capability family entirely.

---

## Phase D — What if: worked variations

Three small variations on Example 3 that exercise different parts of the pipeline.

### D.1 Smith paid late, but within 30 days

Suppose the user adds: "Actually, Smith paid on April 15."

```
L4 re-ingests:
  F7: ∃ e:PD, t':T.
        pay(e) ∧ PC(smith, e, date_2026_04_15)
        ∧ recipient(e, jones) ∧ amount(e, 1200_usd)
      [observed]

validate_assumption:
  Detects that F7 contradicts A1 (A1 says no payment in the window; F7 says there is one).
  Retracts A1 → tag becomes "retracted", retraction_reason = "contradicted by observation F7".

Re-run entailment with the updated ledger:
  Without A1, the antecedent of rule_L001 no longer holds (the ¬∃ clause fails).
  fol.derivation:entails.bounded → status = "independent"
  (The rule simply doesn't fire; Permitted(...) is not entailed, but its negation isn't either.)

Verdict to user: "NO — with Smith's April 15 payment observed, the 30-day condition
is satisfied; the landlord is not Permitted-by-this-rule to terminate."
```

### D.2 Third-party payer

Suppose a cosigner paid: "Smith's mother paid the rent on April 10."

```
L4 ingests:
  F8: parent(mother_of_smith, smith)                              [observed]
  F9: acts_on_behalf_of(mother_of_smith, smith)                   [observed]
  F10: ∃ e:PD, t':T.
         pay(e) ∧ PC(mother_of_smith, e, date_2026_04_10)
       ∧ recipient(e, jones) ∧ amount(e, 1200_usd)                [observed]

validate_assumption:
  F10 unifies with the existential in A1's body, with p_agent = mother_of_smith.
  The disjunct [C9] (p_agent = smith ∨ acts_on_behalf_of(p_agent, smith)) is
  satisfied by F9.
  → A1 is retracted.

Re-run entailment: same as D.1 — rule does not fire, Permitted is independent.
```

This is why clause [C9] was worth the extra translation complexity in A.2.5.

### D.3 Smith paid partially

Suppose: "Smith paid $800 on April 10." Partial payment.

```
L4 ingests:
  F11: ∃ e:PD.
         pay(e) ∧ PC(smith, e, date_2026_04_10)
       ∧ recipient(e, jones) ∧ amount(e, 800_usd)                 [observed]

validate_assumption:
  F11 does NOT unify with A1's existential — the amount clause requires
  amount(e, 1200_usd), but F11 has amount(e, 800_usd).
  → A1 stays in place (an $800 payment does not discharge the $1200 obligation).

Re-run entailment: rule still fires, Permitted is entailed.

Verdict: "YES — $800 partial payment does not satisfy the $1,200 obligation; the
landlord retains the permission to terminate."
```

Note: a richer domain ontology might include a rule like *"partial payment reduces but does not eliminate the obligation"*, which would open a different branch. With the current ontology, the strict amount-match forces the all-or-nothing outcome. This is the sort of thing Example 2 (biomedical ontology-depth pressure) foreshadowed for every domain.

---

## Phase E — The pipeline, seen as one sequence

The entire Example 3 processing, as a linear sequence of (capacity, inputs, outputs) tuples. Phase A is canonical-ingestion; Phase B is operational-query. Each row is one L3 capacity invocation.

```
PHASE A — Canonical ingestion of the law
─────────────────────────────────────────
 1. trace:classify_ingestion_role.detect_mode_marker           → None
 2. trace:classify_ingestion_role.extract_speech_act_features  → {declarative, deontic}
 3. trace:classify_ingestion_role.extract_session_role_context → {legal_import}
 4. trace:classify_ingestion_role.combine_signals.teaching_session → "canonical"
 5. retrieval:lookup_category_for_sense × N (per content word) → sort tags
 6. retrieval:lookup_axiom_template_for_relation × N            → templates
 7. retrieval:lookup_temporal_operator("add_days")              → add_days axiom
 8. comprehension:tense_to_temporal.relative_to_now             → no constraints (generic)
 9. combination:instantiate_axiom_template × N                  → atomic formulas
10. combination:reduce_temporal_literal                         → (no concrete reduction yet)
11. comprehension:compose_statement_from_parse                  → DS_FOL_SET (1 stmt)
12. comprehension:tag_epistemic_status(stmt, "observed")        → tagged DS_FOL_STATEMENT
13. combination:archive_canonical_rule                          → DS_WRITE_INTENT
14. [L4 executes write against L2 fol-rules]                    → rule_L001 persisted

PHASE B — Operational query against the law
─────────────────────────────────────────
15. trace:classify_ingestion_role.detect_mode_marker            → None
16. trace:classify_ingestion_role.extract_speech_act_features   → {interrogative}
17. trace:classify_ingestion_role.extract_session_role_context  → {user_query}
18. trace:classify_ingestion_role.combine_signals.conservative  → "operational"
19. comprehension:compose_statement_from_parse (for facts)      → DS_FOL_SET (F1–F6)
20. comprehension:tag_epistemic_status × 6                      → observed-tagged stmts
21. [L5 ledger populated with F1–F6]
22. validation:validate_assumption(ledger)                      → no change
23. retrieval:lookup_rules_by_predicate("Permitted")            → [rule_L001]
24. derivation:unify(rule_antecedent, query_facts)              → Substitution
25. derivation:instantiate_universal(rule, Substitution)        → bound rule formula
26. combination:reduce_temporal_literal                         → add_days folded
27. combination:populate_negative_closure("pay", ledger, ...)   → DS_ASSUMPTION_CANDIDATES(A1)
28. comprehension:tag_epistemic_status(A1, "assumed")           → tagged A1
29. [L5 ledger gains A1]
30. validation:validate_assumption(ledger)                      → no change (still consistent)
31. derivation:entails.bounded(ledger, G=Permitted(...), 2000)  → "entails" + proof tree
32. [Verdict returned to L4; L4 formats response to user]
```

**32 capacity invocations to answer one legal question.** Most of that work is concentrated in steps 5–12 (translation) and steps 23–31 (query resolution). Steps 1–4 and 15–18 are the ingestion-role decomposition (which looks verbose but each piece is cheap and pure). The architecture's discipline is visible: every step is a fixed L3 capacity; every *choice* (which policy, which prover backend, which scoring rule) lives in L4.

---

## Phase F — What the example tells us about the design

**F.1 Translation is the heavy lifter.** Every non-trivial move (minting constants, assigning sorts, choosing temporal strategy, handling negated existentials) happens inside `compose_statement_from_parse` or its helpers. The prover does comparatively little work in this example — most of the intelligence is front-loaded into getting the FOL right.

**F.2 `populate_negative_closure` is the single most important new capacity.** Without it, Phase B.6 cannot run, and therefore Phase B.7 cannot conclude. The review's §B3 called this out; the walk confirms it is load-bearing, not a footnote.

**F.3 The review's "classical FOL proof calculus + non-monotonic ledger dynamics" framing is vindicated.** The prover itself is classical-FOL and monotonic. The defeasibility — A1 retractable if F7 (or F10) arrives later — lives at the meta-level, in the `validate_assumption` pass. The re-named framing from the review is not cosmetic; it's the right way to describe what the pipeline does.

**F.4 The decomposed `classify_ingestion_role` is not overkill.** Each sub-capacity handles a distinct signal (mode marker, speech act, session role). The combining policy is where learned behavior lives, and L4 cleanly swaps `teaching_session` for `conservative` between Phase A and Phase B without either subsystem changing.

**F.5 Deontic predicates-as-syntactic-atoms work as predicted.** The prover never attempts deontic reasoning. It treats `Permitted(...)` as any other 3-ary atom. Inference about Permission-Obligation-Forbidden relations would require a deontic-reasoning sibling family, which is explicitly out of FOL's scope.

**F.6 The CAN_WRITE_CANONICAL capability is mission-critical.** Phase A step 13–14 depends on it existing. Until the Server ADR is filed and accepted, Phase A cannot run in production. Phase B can still run against an externally-populated `fol-rules` graph, but that's a manual-load stopgap.

**F.7 The translator's deep output is verbose but mechanical.** The ten-conjunct antecedent looks imposing, but every conjunct traces back to a specific lexical item, a specific DOLCE relation, or a specific disambiguation. The translator does not invent — it composes from templates. Changing the law changes the templates consulted; changing the DOLCE mapping changes the sort tags. The FOL capacity family itself is untouched by either kind of change. This is the handoff §13 meta-claim ("richer ontology → more powerful FOL with no L3 changes") landing in a specific walk.

---

## Phase G — Open items the walk surfaced for the next design pass

Things worth deciding before implementation.

**G.1 `acts_on_behalf_of` is unmodeled.** In Phase D.2 the disjunct `acts_on_behalf_of(p_agent, t)` depends on a relation that must exist in the legal-domain ontology. The translator currently produces it hopefully; the ontology team must confirm the relation is defined and when it holds (family relationships? power of attorney? cosigner status?).

**G.2 Partial-payment handling (Phase D.3) is currently blunt.** The strict amount-equality forces all-or-nothing. A more realistic legal system would model partial-payment reductions. This is a `fol-rules` / domain-ontology extension, not an L3-capacity addition, but worth scheduling.

**G.3 The negative closure's `completeness_assumption` is a policy.** In Phase B.6, `populate_negative_closure` was invoked with `completeness_assumption = "ledger_is_authoritative_for_this_user_in_this_window"`. This is a strong claim — it says "we trust we'd have seen any payment event Smith made in this window". Where does this trust come from? In a real system: some combination of bank-record access, user self-attestation, or time-window-based defaults. The design currently names the assumption but doesn't locate its source. A future design pass should specify how `completeness_assumption` is set (likely an L4 policy driven by session metadata and data-source availability).

**G.4 Rule indexing for `lookup_rules_by_predicate` is not designed.** Phase B step 23 looked up rules by their consequent's predicate. That works for small `fol-rules`; at scale, efficient indexing (by predicate, by antecedent head, by sort signature) will be required. This is an implementation concern, not a design one — but flag it.

**G.5 Proof-tree serialisation for verdicts.** The user-visible verdict in Phase B.8 mentioned the rule, the facts, and the assumption. In practice, what proof-tree format does L4 consume to generate this explanation? A structured record (AST of the proof steps)? A natural-language summary? Specify before implementation so the prover's `ProofTree` return type has a stable shape.

**G.6 The numeric literals.** `30`, `14`, `1200`, dates — these are all stored as `Const`s in the AST with informal sort tags. Formal number handling (arithmetic beyond date-addition, comparisons) will need an arithmetic sub-prover or SMT integration. Punt to a later design pass, but name the gap.

---

*End of Example 3 detailed walk.*
