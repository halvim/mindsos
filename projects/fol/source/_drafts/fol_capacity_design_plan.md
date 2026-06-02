# FOL Capacity — Code Design Plan

**Status:** Interface-level design. No capacity bodies; pluggable prover / syntax backends; signatures ready to hand to engineers.
**Date:** 2026-04-23
**Depends on:** `fol_capacity_handoff.md` (scoping), `fol_capacity_review.md` (Opus 4.6 review — all must-fix items from §G items 1–7 are incorporated; items 8–13 are applied where structural).
**Target package:** `falkormg_capacity.fol` (subpackage under the existing L3 package; name change deferred per project-level rename plan).
**Language:** Python 3.11+.

---

## 0. Document map

- **Part I — Design plan** (below): package layout, pluggable prover interface, DataState catalogue, full capacity signature catalogue by category, registry wiring, test strategy.
- **Part II — Example walks**: 3 → 2 → 5 → 4 → 6, each walked against the design with specific FOL translations, capacity invocation sequences, and design updates surfaced.
- **Part III — Design-update delta**: consolidated changes to Part I that the walks forced.

---

# PART I — Design plan

## 1. Package layout

```
falkormg_capacity/
    fol/
        __init__.py                   # registers all FOL capacities on import
        datastates.py                 # DS_FOL_* dataclasses (§3)
        syntax.py                     # abstract FOL AST (prover-neutral) (§2.1)
        prover.py                     # abstract Prover / Unifier / Skolemizer protocols (§2.2)
        registry.py                   # capacity registration helpers
        context_schema.py             # documented context keys the FOL family reads (§6)

        comprehension/
            __init__.py
            compose_statement.py              # fol.compose_statement_from_parse
            extract_implicit_assumptions.py   # fol.extract_implicit_assumptions
            tag_epistemic_status.py           # fol.tag_epistemic_status
            re_translate_with_sense_hint.py   # fol.re_translate_with_sense_hint
            tense_to_temporal/
                __init__.py
                reichenbach.py                # fol.tense_to_temporal.reichenbach
                allen_interval.py             # fol.tense_to_temporal.allen_interval
                relative_to_now.py            # fol.tense_to_temporal.relative_to_now

        retrieval/
            __init__.py
            lookup_category_for_sense.py
            lookup_axiom_template.py
            enumerate_sense_alternatives.py
            apply_sense_correlation.py
            classify_axiom_strictness.py

        derivation/
            __init__.py
            unify.py                           # fol.unify (NEW — per review D1)
            apply_substitution.py              # fol.apply_substitution (NEW)
            instantiate_universal.py           # fol.instantiate_universal (NEW — per D2)
            skolemize.py                       # fol.skolemize (NEW — per D3)
            derive_alternative_forms.py
            detect_exception_relationship.py
            validate_rule_against_ledger.py
            justifications_for.py
            localise_conflict.py
            consistency/
                resolution.py                  # fol.consistency.resolution
                tableau.py                     # fol.consistency.tableau
                smt_bounded.py                 # fol.consistency.smt_bounded
            entailment/
                resolution.py                  # fol.entails.resolution
                tableau.py                     # fol.entails.tableau
                bounded.py                     # fol.entails.bounded (NEW — per D4)
            abduction/
                minimal.py                     # fol.abduce.minimal
                prime_implicates.py            # fol.abduce.prime_implicates
                kb_directed.py                 # fol.abduce.kb_directed

        decomposition/
            __init__.py
            enumerate_unbound_predicates.py

        combination/
            __init__.py
            instantiate_axiom_template.py
            extend_rule_with_exception.py
            compose_rule_with_exception.py
            rewrite_strict_as_exception_permitting.py
            apply_revision.py
            cascade_retract.py
            falsify_rule.py
            archive_falsified_rule.py          # returns DS_WRITE_INTENT, per review B7
            assign_default_category.py
            populate_exception_closure.py      # fol.populate_exception_closure (NEW — per B3)
            propose_rule_resolution.py         # fol.propose_rule_resolution (NEW — per B4)
            compact_dead_branches.py           # fol.compact_dead_branches (NEW — per B9)

        scoring/
            __init__.py
            gap_relevance/
                next_input_alignment.py
                goal_alignment.py
                memory_weighted.py
            priority/
                observed_first.py
                source_trust.py
                recency.py
                # each new priority rule is its own module

        trace/
            __init__.py
            classify_ingestion_role/           # decomposed per C1
                __init__.py
                detect_mode_marker.py
                extract_speech_act_features.py
                extract_session_role_context.py
                combine_signals.py             # takes a policy
                policies/
                    conservative.py            # default policy
                    trusted_source.py
                    teaching_session.py

        signalling/
            __init__.py
            signal_sense_confirmed.py          # returns DS_SIGNAL_RECORD (no "fires")
            emit_uncertainty_marker.py
            flag_analytic_contradiction.py     # returns DS_WRITE_INTENT + trace record

        interaction/
            __init__.py
            ask_human_for_category.py

        learning_methods/
            __init__.py
            enumerate_rule_templates_matching.py
            instantiate_rule_template.py
            assess_template_coverage.py
            emit_wsd_training_signal.py        # returns DS_TRAINING_SIGNAL record

        validation/
            __init__.py
            validate_assumption.py             # core capacity — per §4.8

        rules/                                  # ledger-management helpers
            __init__.py
            revive_retracted.py                # (NEW — per review B5)
            retraction_reason.py               # (NEW — per B5)
```

**Notes on the layout.**

- One Python module per capacity. Enforces I1 (pure function per capacity) and makes capacity IRIs line up with file paths.
- Strategy families (`tense_to_temporal/*`, `consistency/*`, `entailment/*`, `abduction/*`, `gap_relevance/*`, `priority/*`, `classify_ingestion_role/policies/*`) are sub-packages. Each strategy is its own L3 capacity; L4 picks.
- `rules/` holds ledger-mutation helpers that return intents rather than executing; they're not a new L3 category, just a source-code grouping.
- No category module contains stateful fixtures. All imports must be side-effect-free except for the registry call in `__init__.py`.

## 2. Abstract syntax and prover interfaces (prover-neutral)

The design does not commit to TPTP, SMT-LIB, or a specific prover. Capacities operate over an abstract FOL AST; a `Prover` protocol defines the proof surface. Concrete backends (Vampire, E, Z3 via SMT-LIB, in-process resolution) slot in behind these interfaces.

### 2.1 `falkormg_capacity.fol.syntax`

```python
# syntax.py — abstract FOL AST. No dependency on any prover library.

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable, Literal, Sequence

type Sort = str              # e.g. "ED", "PD", "Q", "AB" — DOLCE categories as sort tags
type VarName = str
type ConstName = str
type PredName = str
type FuncName = str

@dataclass(frozen=True)
class Var:
    name: VarName
    sort: Sort | None = None

@dataclass(frozen=True)
class Const:
    name: ConstName
    sort: Sort | None = None

@dataclass(frozen=True)
class Func:
    name: FuncName
    args: tuple["Term", ...]
    sort: Sort | None = None

type Term = Var | Const | Func

@dataclass(frozen=True)
class Atom:
    pred: PredName
    args: tuple[Term, ...]

@dataclass(frozen=True)
class Not:
    f: "Formula"

@dataclass(frozen=True)
class And:
    conjuncts: tuple["Formula", ...]

@dataclass(frozen=True)
class Or:
    disjuncts: tuple["Formula", ...]

@dataclass(frozen=True)
class Implies:
    ant: "Formula"
    con: "Formula"

@dataclass(frozen=True)
class Equiv:
    left: "Formula"
    right: "Formula"

@dataclass(frozen=True)
class Forall:
    var: Var
    body: "Formula"

@dataclass(frozen=True)
class Exists:
    var: Var
    body: "Formula"

@dataclass(frozen=True)
class Eq:
    left: Term
    right: Term

type Formula = Atom | Not | And | Or | Implies | Equiv | Forall | Exists | Eq
```

**Design notes.**

- Many-sorted by construction — every term and quantifier carries an optional `Sort`. Backends that want unsorted logic translate away the sort tags; sort-aware backends (most modern provers) exploit them.
- `Eq` is first-class, not a built-in `Atom` named `"="`. Per review §D7: equality is an explicit syntactic case, so prover backends can choose paramodulation vs equality axioms.
- `Func` vs `Atom` distinction is maintained — DOLCE uses both (e.g., `qlT(x) = t` is a functional equation; `PC(x, e, t)` is an atom).
- All AST nodes are frozen dataclasses → hashable → usable as dict keys and set elements. Important for dependency graphs and memoisation.
- No precedence / parsing concerns at this layer — parsing is a translator concern; this is already-parsed output.

### 2.2 `falkormg_capacity.fol.prover`

```python
# prover.py — pluggable backends

from typing import Protocol, Literal
from .syntax import Formula, Term, Var, Atom

type Substitution = dict[Var, Term]
type ProofBound = int | Literal["unbounded"]

class Unifier(Protocol):
    def unify(self, a: Term | Atom, b: Term | Atom) -> Substitution | None: ...

class Skolemizer(Protocol):
    def skolemize(self, f: Formula) -> Formula: ...

class Prover(Protocol):
    """Prover-neutral interface.

    All methods accept an immutable set of premises plus a single goal formula.
    `bound` gives the backend a chance to return 'unknown' rather than run forever.
    """

    def check_consistent(
        self, premises: frozenset[Formula], bound: ProofBound
    ) -> Literal["consistent", "inconsistent", "unknown_within_bound"]: ...

    def check_entails(
        self, premises: frozenset[Formula], goal: Formula, bound: ProofBound
    ) -> Literal["entails", "contradicts", "independent", "unknown_within_bound"]: ...

    def find_unsat_core(
        self, premises: frozenset[Formula], bound: ProofBound
    ) -> frozenset[Formula] | None: ...

    def build_proof_tree(
        self, premises: frozenset[Formula], goal: Formula, bound: ProofBound
    ) -> "ProofTree | None": ...
```

**Notes.**

- `ProofBound` makes the semi-decidability problem explicit: every prover method either terminates with a verdict or returns `unknown_within_bound`. Review §D4 comes out of hiding.
- Each concrete backend lives in a separate module (e.g., `falkormg_capacity.fol.provers.resolution_inprocess`, `falkormg_capacity.fol.provers.vampire_subprocess`, `falkormg_capacity.fol.provers.z3_smt`) and is selected by L4 via `context["prover_backend"]` → a key registered in `context_schema.py`.
- Unifier / Skolemizer are separate protocols so that non-prover capacities (e.g., `fol.unify` used by `re_translate_with_sense_hint`) can depend on just the piece they need.

## 3. DataState catalogue

All `DS_*` types live in `falkormg_capacity.fol.datastates` as frozen dataclasses. Per I2, they carry only structural fields; semantic weights live in `context` or L2.

```python
# datastates.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Mapping
from .syntax import Formula, Var

# ──────────────────────────────────────────────────────────────
# Epistemic tags — per review B5, 'retracted' is now a tag
# ──────────────────────────────────────────────────────────────

type EpistemicTag = Literal["observed", "inferred", "assumed", "hypothesised", "retracted"]
type IngestionRole = Literal["canonical", "operational", "observed_by_sensor", "self_hypothesised"]
type AssumptionKind = Literal["candidate", "default", "abduced"] | None
type RuleSource = Literal["ontology_taxonomy", "ontology_axiom", "observation", "learned_pattern", "human_declared"]

# ──────────────────────────────────────────────────────────────
# Upstream input
# ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SenseCandidate:
    sense_iri: str
    prior: float      # opaque_tag-shaped: L3 does not interpret; L4 owns semantics

@dataclass(frozen=True)
class DS_SENSE_CANDIDATES:
    parse_tree: "ParseTree"                     # upstream parse structure — out of FOL scope
    per_content_node: Mapping[str, tuple[SenseCandidate, ...]]
    tense_features: Mapping[str, str]
    utterance_context: Mapping[str, str]

# ──────────────────────────────────────────────────────────────
# Core statement / set / ledger — per review B5, B6, E4
# ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Provenance:
    source_utterance: str | None
    derived_from: tuple[str, ...]               # stmt_ids
    sense_commitments: tuple[tuple[str, str], ...]   # (token, sense_iri)
    ontology_rule_id: str | None
    ingestion_role: IngestionRole
    source_id: str | None                       # per review B6 — was source_trust
    assumption_kind: AssumptionKind             # per review E4 — only populated when tag is 'assumed'
    retraction_reason: str | None               # per B5 — only populated when tag is 'retracted'

@dataclass(frozen=True)
class DS_FOL_STATEMENT:
    stmt_id: str
    formula: Formula
    epistemic_tag: EpistemicTag
    provenance: Provenance
    time_bindings: tuple[tuple[Var, "TimeConstraint"], ...]
    is_time_variant: bool
    minted_at: str | None                       # per review B2 — time-anchor IRI at mint time

@dataclass(frozen=True)
class DS_FOL_SET:
    statements: tuple[DS_FOL_STATEMENT, ...]    # ordered

@dataclass(frozen=True)
class DS_FOL_LEDGER:
    statements: Mapping[str, DS_FOL_STATEMENT]                  # stmt_id -> stmt
    dependency_graph: Mapping[str, tuple[str, ...]]             # stmt_id -> derived_from
    sense_distributions: Mapping[str, tuple[SenseCandidate, ...]]
    open_gaps: tuple["GapEntry", ...]

# ──────────────────────────────────────────────────────────────
# Reasoning outputs
# ──────────────────────────────────────────────────────────────

type AnomalyKind = Literal["none", "ContradictionWithinLedger", "AnalyticContradiction"]

@dataclass(frozen=True)
class DS_CONSISTENCY_VERDICT:
    consistent: bool
    unsat_core: tuple[str, ...] | None          # stmt_ids
    anomaly_kind: AnomalyKind
    bound_exhausted: bool                       # per D4 — True if prover hit its bound

@dataclass(frozen=True)
class DS_ENTAILMENT_RESULT:
    status: Literal["entails", "contradicts", "independent", "unknown_within_bound"]
    proof_tree: "ProofTree | None"

@dataclass(frozen=True)
class DS_CONFLICT_LOCALISATION:
    unsat_core: tuple[str, ...]
    tags_in_core: Mapping[EpistemicTag, tuple[str, ...]]
    rule_form: Literal["strict", "exception_permitting"]
    candidate_resolutions: tuple["CandidateResolution", ...]

type CandidateResolution = (
    tuple[Literal["retract_assumption"], str, tuple[str, ...]]     # stmt_id, cascade stmt_ids
    | tuple[Literal["re_translate"], str, str]                     # sentence_id, alt sense
    | tuple[Literal["abduce_assumption"], Formula]                 # missing clause
    | tuple[Literal["falsify_rule"], str]                          # rule_id
    | tuple[Literal["refine_rule"], str, Formula]                  # rule_id, exception clause
)

@dataclass(frozen=True)
class DS_ASSUMPTION_CANDIDATES:
    candidates: tuple[DS_FOL_STATEMENT, ...]

@dataclass(frozen=True)
class GapEntry:
    predicate: str
    free_vars: tuple[Var, ...]
    provenance: Provenance

@dataclass(frozen=True)
class DS_GAP_REPORT:
    gaps: tuple[GapEntry, ...]
    relevance_scores: Mapping[str, float] | None    # gap_id -> score

@dataclass(frozen=True)
class DS_REVISION_PLAN:
    ordered_steps: tuple[CandidateResolution, ...]
    expected_ledger_after_apply: DS_FOL_LEDGER | None   # optional preview

# ──────────────────────────────────────────────────────────────
# Write intents — per review B7
# ──────────────────────────────────────────────────────────────

type WriteTarget = Literal["L2.fol-rules", "L2.memories", "L2.sense-correlations", "L2.wsd-model", "L5.ledger"]

@dataclass(frozen=True)
class DS_WRITE_INTENT:
    target: WriteTarget
    operation: Literal["insert", "update", "archive", "activate_version"]
    payload: object                             # schema depends on target; L4 validates
    requires_capability: str | None             # e.g., "CAN_WRITE_CANONICAL" (review B8)

# ──────────────────────────────────────────────────────────────
# Signals, traces, uncertainty
# ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DS_SIGNAL_RECORD:
    signal_kind: Literal["sense_confirmed", "analytic_contradiction_flagged", "assumption_promoted"]
    payload: Mapping[str, object]

@dataclass(frozen=True)
class DS_UNCERTAINTY_MARKER:
    unmapped_sense: str
    propagated_to: tuple[str, ...]
    confidence_hint: str                        # opaque tag

@dataclass(frozen=True)
class DS_CATEGORY_ASSIGNMENT:
    sense: str
    assigned_category: str
    source: Literal["human", "default", "correlation"]

@dataclass(frozen=True)
class DS_TRAINING_SIGNAL:
    target_model: Literal["wsd", "gap_scorer", "priority_chooser"]
    features: Mapping[str, object]
    label: Literal["positive", "negative", "undetermined"]
    weight_tag: str                             # opaque; L4 interprets (canonical vs operational)

# ──────────────────────────────────────────────────────────────
# Temporal bindings — per review B2
# ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TimeConstraint:
    kind: Literal["at", "before", "after", "during", "between"]
    anchor: str                                 # time anchor IRI
    second_anchor: str | None = None
```

## 4. Capacity signature catalogue

Every signature is `impl(inputs, *, context: Mapping[str, object]) -> Outputs`. `context` is immutable; capacities must not mutate it. Per ADR-013, exceptions become `ProblemTraceRecord`s rather than propagate.

Capacity IRI convention per ADR-007: `capacity:<category>:<name>`. Where a capacity is one member of a strategy family, the name is dotted: `capacity:derivation:consistency.resolution`.

**Key shown in tables below:** M = modification required from review; N = new capacity from review; = = unchanged from handoff §5.

### 4.1 Comprehension

| IRI | Signature | Origin |
|---|---|---|
| `capacity:comprehension:compose_statement_from_parse` | `(DS_SENSE_CANDIDATES, *, context) -> DS_FOL_SET` | = |
| `capacity:comprehension:extract_implicit_assumptions` | `(DS_FOL_STATEMENT, DS_FOL_LEDGER, *, context) -> DS_ASSUMPTION_CANDIDATES` | = |
| `capacity:comprehension:tag_epistemic_status` | `(DS_FOL_STATEMENT, EpistemicTag, *, context) -> DS_FOL_STATEMENT` | = |
| `capacity:comprehension:re_translate_with_sense_hint` | `(DS_FOL_LEDGER, sentence_id: str, hinted_sense: str, *, context) -> DS_FOL_LEDGER` | = |
| `capacity:comprehension:tense_to_temporal.reichenbach` | `(parse, now: str, *, context) -> tuple[TimeConstraint, ...]` | M (decomposed) |
| `capacity:comprehension:tense_to_temporal.allen_interval` | `(parse, now: str, *, context) -> tuple[TimeConstraint, ...]` | M |
| `capacity:comprehension:tense_to_temporal.relative_to_now` | `(parse, now: str, *, context) -> tuple[TimeConstraint, ...]` | M |

### 4.2 Retrieval

| IRI | Signature | Origin |
|---|---|---|
| `capacity:retrieval:lookup_category_for_sense` | `(sense: str, *, context) -> str` | = |
| `capacity:retrieval:lookup_axiom_template_for_relation` | `(relation: str, category: str, *, context) -> AxiomTemplate` | = |
| `capacity:retrieval:enumerate_sense_alternatives` | `(token: str, *, context) -> tuple[str, ...]` | = |
| `capacity:retrieval:apply_sense_correlation` | `(confirmed_sense: str, co_occurring_lemmas: tuple[str, ...], *, context) -> Mapping[str, tuple[SenseCandidate, ...]]` | = |
| `capacity:retrieval:classify_axiom_strictness` | `(rule, *, context) -> RuleSource` | M (returns enum per review E2) |

### 4.3 Derivation

Primitives and proof-related capacities.

| IRI | Signature | Origin |
|---|---|---|
| `capacity:derivation:unify` | `(a: Term\|Atom, b: Term\|Atom, *, context) -> Substitution \| None` | N (review D1) |
| `capacity:derivation:apply_substitution` | `(f: Formula, s: Substitution, *, context) -> Formula` | N (D1) |
| `capacity:derivation:instantiate_universal` | `(rule: Formula, binding: Substitution, *, context) -> Formula` | N (D2) |
| `capacity:derivation:skolemize` | `(f: Formula, *, context) -> Formula` | N (D3) |
| `capacity:derivation:derive_alternative_forms` | `(rule: Formula, *, context) -> tuple[Formula, ...]` | = |
| `capacity:derivation:detect_exception_relationship` | `(rule_a: Formula, rule_b: Formula, *, context) -> bool` | = |
| `capacity:derivation:validate_rule_against_ledger` | `(rule: Formula, ledger: DS_FOL_LEDGER, *, context) -> tuple[tuple[str, ...], tuple[str, ...]]` (supporting, contradicting) | = |
| `capacity:derivation:justifications_for` | `(ledger: DS_FOL_LEDGER, conclusion_id: str, *, context) -> tuple[str, ...]` | = |
| `capacity:derivation:localise_conflict` | `(ledger: DS_FOL_LEDGER, *, context) -> DS_CONFLICT_LOCALISATION` | = |
| `capacity:derivation:consistency.resolution` | `(DS_FOL_LEDGER, bound: ProofBound, *, context) -> DS_CONSISTENCY_VERDICT` | M (strategy) |
| `capacity:derivation:consistency.tableau` | `(DS_FOL_LEDGER, bound: ProofBound, *, context) -> DS_CONSISTENCY_VERDICT` | M |
| `capacity:derivation:consistency.smt_bounded` | `(DS_FOL_LEDGER, smt_fragment: str, bound: ProofBound, *, context) -> DS_CONSISTENCY_VERDICT` | M |
| `capacity:derivation:entails.resolution` | `(DS_FOL_LEDGER, candidate: Formula, bound: ProofBound, *, context) -> DS_ENTAILMENT_RESULT` | M |
| `capacity:derivation:entails.tableau` | `(DS_FOL_LEDGER, candidate: Formula, bound: ProofBound, *, context) -> DS_ENTAILMENT_RESULT` | M |
| `capacity:derivation:entails.bounded` | `(DS_FOL_LEDGER, candidate: Formula, bound: ProofBound, *, context) -> DS_ENTAILMENT_RESULT` | N (D4) |
| `capacity:derivation:abduce.minimal` | `(DS_FOL_LEDGER, target: Formula, bound: ProofBound, *, context) -> DS_ASSUMPTION_CANDIDATES` | M |
| `capacity:derivation:abduce.prime_implicates` | `(DS_FOL_LEDGER, target: Formula, bound: ProofBound, *, context) -> DS_ASSUMPTION_CANDIDATES` | M |
| `capacity:derivation:abduce.kb_directed` | `(DS_FOL_LEDGER, target: Formula, bound: ProofBound, *, context) -> DS_ASSUMPTION_CANDIDATES` | M |

### 4.4 Decomposition

| IRI | Signature | Origin |
|---|---|---|
| `capacity:decomposition:enumerate_unbound_predicates` | `(DS_FOL_LEDGER, *, context) -> DS_GAP_REPORT` | = |

### 4.5 Combination

| IRI | Signature | Origin |
|---|---|---|
| `capacity:combination:instantiate_axiom_template` | `(template: AxiomTemplate, args: Mapping[str, Term], *, context) -> DS_FOL_STATEMENT` | = |
| `capacity:combination:extend_rule_with_exception` | `(rule: Formula, exception_clause: Formula, *, context) -> Formula` | = |
| `capacity:combination:compose_rule_with_exception` | `(a: Formula, b: Formula, *, context) -> Formula` | = |
| `capacity:combination:rewrite_strict_as_exception_permitting` | `(rule: Formula, *, context) -> Formula` | = |
| `capacity:combination:apply_revision` | `(conflict: DS_CONFLICT_LOCALISATION, priority_ordering: tuple[str, ...], *, context) -> DS_REVISION_PLAN` | M (returns plan, not mutated ledger) |
| `capacity:combination:cascade_retract` | `(DS_FOL_LEDGER, stmt_id: str, *, context) -> tuple[DS_FOL_LEDGER, tuple[str, ...]]` (retracted_set) | = |
| `capacity:combination:falsify_rule` | `(rule: Formula, contradicting: DS_FOL_STATEMENT, *, context) -> Formula` | = |
| `capacity:combination:archive_falsified_rule` | `(rule: Formula, contradicting: DS_FOL_STATEMENT, *, context) -> DS_WRITE_INTENT` | M (B7) |
| `capacity:combination:assign_default_category` | `(unmapped_sense: str, *, context) -> DS_FOL_STATEMENT` | = |
| `capacity:combination:populate_exception_closure` | `(rule: Formula, binding: Substitution, *, context) -> DS_ASSUMPTION_CANDIDATES` | N (B3) |
| `capacity:combination:propose_rule_resolution` | `(rule: Formula, contradicting: DS_FOL_STATEMENT, ontology_view, *, context) -> CandidateResolution` | N (B4) |
| `capacity:combination:compact_dead_branches` | `(DS_FOL_LEDGER, policy: str, *, context) -> tuple[DS_FOL_LEDGER, DS_WRITE_INTENT]` | N (B9) |

### 4.6 Scoring

| IRI | Signature | Origin |
|---|---|---|
| `capacity:scoring:gap_relevance.next_input_alignment` | `(gap: GapEntry, predicted_shape, *, context) -> float` | M (decomposed per C4) |
| `capacity:scoring:gap_relevance.goal_alignment` | `(gap: GapEntry, goal_spec, *, context) -> float` | M |
| `capacity:scoring:gap_relevance.memory_weighted` | `(gap: GapEntry, memory_pattern, *, context) -> float` | M |
| `capacity:scoring:priority.observed_first` | `(conflict_set: tuple[str, ...], *, context) -> tuple[str, ...]` | = |
| `capacity:scoring:priority.source_trust` | `(conflict_set: tuple[str, ...], trust_scores: Mapping[str, float], *, context) -> tuple[str, ...]` | M (trust scores as explicit arg, not via context — review B6/E5) |
| `capacity:scoring:priority.recency` | `(conflict_set: tuple[str, ...], *, context) -> tuple[str, ...]` | = |

### 4.7 Trace

Decomposed classify_ingestion_role per review C1.

| IRI | Signature | Origin |
|---|---|---|
| `capacity:trace:classify_ingestion_role.detect_mode_marker` | `(input_raw: str, *, context) -> IngestionRole \| None` | N (C1) |
| `capacity:trace:classify_ingestion_role.extract_speech_act_features` | `(parse, *, context) -> Mapping[str, str]` | N |
| `capacity:trace:classify_ingestion_role.extract_session_role_context` | `(*, context) -> Mapping[str, str]` | N |
| `capacity:trace:classify_ingestion_role.combine_signals.conservative` | `(signals: Mapping[str, object], *, context) -> IngestionRole` | N |
| `capacity:trace:classify_ingestion_role.combine_signals.trusted_source` | `(signals: Mapping[str, object], *, context) -> IngestionRole` | N |
| `capacity:trace:classify_ingestion_role.combine_signals.teaching_session` | `(signals: Mapping[str, object], *, context) -> IngestionRole` | N |

### 4.8 Signalling

| IRI | Signature | Origin |
|---|---|---|
| `capacity:signalling:signal_sense_confirmed` | `(lemma: str, sense: str, *, context) -> DS_SIGNAL_RECORD` | M (returns record, no "fires" — B7) |
| `capacity:signalling:emit_uncertainty_marker` | `(unmapped_sense: str, propagated_to: tuple[str, ...], *, context) -> DS_UNCERTAINTY_MARKER` | = |
| `capacity:signalling:flag_analytic_contradiction` | `(rule: Formula, observation: DS_FOL_STATEMENT, *, context) -> tuple[DS_WRITE_INTENT, DS_SIGNAL_RECORD]` | M (B7) |

### 4.9 Interaction

| IRI | Signature | Origin |
|---|---|---|
| `capacity:interaction:ask_human_for_category` | `(unmapped_sense: str, *, context) -> DS_CATEGORY_ASSIGNMENT` | = |

### 4.10 Learning methods

Decomposed generate_hypothetical_rule per review C2.

| IRI | Signature | Origin |
|---|---|---|
| `capacity:learning_methods:enumerate_rule_templates_matching` | `(observations: tuple[DS_FOL_STATEMENT, ...], *, context) -> tuple[AxiomTemplate, ...]` | N (C2) |
| `capacity:learning_methods:instantiate_rule_template` | `(template: AxiomTemplate, observations: tuple[DS_FOL_STATEMENT, ...], *, context) -> Formula` | N |
| `capacity:learning_methods:assess_template_coverage` | `(template: AxiomTemplate, observations: tuple[DS_FOL_STATEMENT, ...], *, context) -> float` | N |
| `capacity:learning_methods:emit_wsd_training_signal` | `(lemma: str, sense: str, verdict: Literal["confirmed", "retracted", "undetermined"], *, context) -> DS_TRAINING_SIGNAL` | M (B7) |

### 4.11 Validation

| IRI | Signature | Origin |
|---|---|---|
| `capacity:validation:validate_assumption` | `(DS_FOL_LEDGER, *, context) -> tuple[tuple[str, ...], tuple[str, ...]]` (promoted, retracted) | = (core) |

### 4.12 Rule management (ledger side)

These are cross-category helpers grouped in `rules/` but registered under their functional category.

| IRI | Signature | Origin |
|---|---|---|
| `capacity:combination:revive_retracted` | `(DS_FOL_LEDGER, stmt_id: str, *, context) -> DS_FOL_LEDGER` | N (B5) |
| `capacity:retrieval:retraction_reason` | `(DS_FOL_LEDGER, stmt_id: str, *, context) -> str \| None` | N (B5) |

## 5. Registry wiring

Each capacity module defines a module-level `CAPACITY` constant and registers itself on import:

```python
# derivation/consistency/resolution.py

from falkormg_capacity.core import Capacity, ShapeDescriptor, register_capacity
from falkormg_capacity.fol.datastates import DS_FOL_LEDGER, DS_CONSISTENCY_VERDICT
from falkormg_capacity.fol.prover import ProofBound

CAPACITY_IRI = "capacity:derivation:consistency.resolution"

def impl(ledger: DS_FOL_LEDGER, bound: ProofBound, *, context) -> DS_CONSISTENCY_VERDICT:
    ...  # body TBD — calls the resolution-backend Prover

CAPACITY = Capacity(
    iri=CAPACITY_IRI,
    category="CATEGORY_DERIVATION",
    inputs={"ledger": ShapeDescriptor.for_class(DS_FOL_LEDGER), "bound": ShapeDescriptor.for_primitive("ProofBound")},
    outputs={"verdict": ShapeDescriptor.for_class(DS_CONSISTENCY_VERDICT)},
    impl=impl,
)

register_capacity(CAPACITY)
```

`falkormg_capacity.fol.__init__.py` imports every category module, triggering registration. This preserves ADR-007 (IRI at declaration time) and I3 (collision → `CapacityRegistrationError`).

`ShapeDescriptor` conforms to I2: only `kind`, `elem`, `fields`, `opaque_tag`.

## 6. `context` schema contribution

Per review B8 / L4 open concern D3, the FOL family contributes these keys to the global `context` schema. Naming a key here does not add it to the schema — this is a proposal the L4 session must ratify.

| Key | Type | Read by | Purpose |
|---|---|---|---|
| `prover_backend` | `str` IRI | consistency.*, entails.*, abduce.* | Which registered Prover to use on this call |
| `proof_bound` | `int \| "unbounded"` | consistency.*, entails.*, abduce.* | Default bound if the capacity takes no explicit `bound` arg |
| `ingestion_role_policy` | `str` IRI | classify_ingestion_role.combine_signals.* | Which combination policy |
| `now_anchor` | `str` IRI | compose_statement_from_parse, tense_to_temporal.*, validate_assumption | Current time anchor |
| `trust_scores` | `Mapping[str, float]` | priority.source_trust | Per-source trust — still passed explicitly to the capacity as an arg; context carries the table |
| `gap_scorer_weights` | `Mapping[str, float]` | gap_relevance.* | Scorer weights (learned in L4) |
| `wsd_model_version` | `str` IRI | compose_statement_from_parse (via WSD upstream) | Which WSD model snapshot |
| `can_write_canonical` | `bool` | classify_ingestion_role.combine_signals.* | Authority gate on canonical role assignment |
| `session_user_id` | `str` | all (auto-injected per ADR-022) | |
| `session_id` | `str` | all (auto-injected per ADR-022) | |

## 7. Test strategy

Three test layers, each with a fixed responsibility.

**L7a. Unit tests per capacity.** One test file per capacity module. Every capacity has at least: (a) a happy-path test with a canonical input, (b) a test for each structural output variant the type admits, (c) one test asserting the capacity is stateless (invoke twice, same inputs, identical outputs). Fixtures come from `tests/fol/fixtures/` and reuse a small worked example library so the unit tests compose into end-to-end checks.

**L7b. Ledger-property tests.** Property-based tests (hypothesis library) that generate small ledgers and assert invariants: `validate_assumption` is idempotent on a fixpoint; `cascade_retract` followed by `revive_retracted` (when the retraction cause is itself retracted) restores the original statement set; `apply_revision` never produces a ledger that fails `consistency.*` using a bounded prover on small fragments.

**L7c. Example walk-throughs.** One test per stress-test example (1–6). Each drives the full pipeline — upstream fixtures → translation → ledger → validation passes → revisions → final state — and asserts the specific outcomes committed in the example walks (Part II below). These double as regression tests against the design narrative: if you break the design, an example test fails.

---

# PART II — Example walks

Each walk follows the same structure:

1. **Input.** The exact sentence(s), plus upstream `DS_SENSE_CANDIDATES` for any ambiguous tokens.
2. **Translation.** The FOL `Formula` produced per statement, with sort annotations.
3. **Ledger trace.** Which capacities fire in which order, with their outputs.
4. **Pressure points.** What the example exposes.
5. **Design updates.** Any Part I change the walk forces. Collected in Part III.

Order per the handoff: 3 → 2 → 5 → 4 → 6.

---

## II.1 Example 3 — Legal conditional with deontic operators

**Input.** *"If the tenant fails to pay rent within 30 days of the due date, the landlord may terminate the lease by giving 14 days' written notice."*

**Upstream.** Parse yields a conditional with two clauses. WSD senses (disambiguated):
- `tenant` → `tenant.n.01` (renter)
- `pay.v.01` (transfer money)
- `rent.n.02` (periodic payment for use)
- `due_date.n.01`
- `landlord.n.01`
- `may.v.modal_deontic` ← the key one
- `terminate.v.01` (bring to an end)
- `lease.n.01` (contractual agreement)
- `notice.n.02` (written warning)

`classify_ingestion_role` → `canonical` if the session is flagged as a legal-document-import session, else `operational`. Assume canonical for the walk (law-import pipeline, L4 has checked `can_write_canonical`).

### Translation

Sort tags abbreviated: `AG` (agent), `SA` (social agent / role), `EV` (event), `T` (time), `Q` (quantity), `ART` (artefact / document).

The conditional translates as a single universally quantified rule. Deontic "may" becomes a **syntactic predicate** `Permitted(agent, action, conditions)` — uninterpreted by the FOL prover, interpreted downstream by a deontic reasoner (out of scope for this walk).

```
∀ t:AG, l:AG, lease:ART, r:Q, d:T.
    tenant(t) ∧ landlord(l) ∧ party_to(t, lease) ∧ party_to(l, lease)
    ∧ rent_obligation(t, r, lease) ∧ due_date(r, d)
    ∧ ¬∃ e:EV. pay(e) ∧ PC(t, e, t') ∧ recipient(e, l) ∧ amount(e, r) ∧ t' ≤ d + 30_days
    → Permitted(l, terminate(lease), notice_requirement(14_days, written))
```

Tagged `observed` (source is canonical / law), `ingestion_role="canonical"`, `source_id="lease_law_2026_section_42.iri"`, `minted_at=now_k`.

### Ledger trace

```
L4 dispatches:
  trace:classify_ingestion_role.detect_mode_marker      → None (no marker)
  trace:classify_ingestion_role.extract_speech_act_features → {mood: declarative, aspect: generic}
  trace:classify_ingestion_role.extract_session_role_context → {session_role: legal_import}
  trace:classify_ingestion_role.combine_signals.teaching_session → "canonical"

  comprehension:compose_statement_from_parse
    → retrieval:lookup_category_for_sense for each content word
    → retrieval:lookup_axiom_template_for_relation for each DOLCE relation
    → combination:instantiate_axiom_template × N
    → returns DS_FOL_SET with one statement (the rule above)

  comprehension:tag_epistemic_status(stmt, "observed")

  (statement added to L2 fol-rules via a DS_WRITE_INTENT, since role=canonical)
  → L4 validates DS_WRITE_INTENT.requires_capability="CAN_WRITE_CANONICAL"
  → L4 writes the rule into L2 fol-rules with source="human_declared"
```

No ledger inconsistency in isolation. The interesting work begins when operational input arrives: *"Tenant Smith hasn't paid rent in 35 days — can the landlord terminate?"*

```
operational input → translation:
  tenant(smith) ∧ landlord(jones) ∧ party_to(smith, lease_7) ∧ party_to(jones, lease_7)
  ∧ rent_obligation(smith, 1200, lease_7) ∧ due_date(1200, 2026-03-19)
  ∧ ¬∃ e. pay(e) ∧ PC(smith, e, t') ∧ recipient(e, jones) ∧ amount(e, 1200) ∧ t' ≤ 2026-04-18
  ∧ now_k = 2026-04-23

derivation:instantiate_universal(rule, {t↦smith, l↦jones, lease↦lease_7, r↦1200, d↦2026-03-19})
  → Permitted(jones, terminate(lease_7), notice_requirement(14_days, written))

derivation:entails.bounded(ledger, Permitted(...), bound=1000) → entails
```

The verdict `Permitted(jones, terminate(lease_7), notice_requirement(14_days, written))` returns to L4. An out-of-scope deontic reasoner consumes it to answer the user's "can?" question.

### Pressure points

**P3.1. Existential-negation translation is verbose.** `¬∃ e. pay(e) ∧ ...` is technically correct but explodes when multiple such clauses appear. The translator output shape is right; optimisation (e.g., Skolemisation on the outer negation) belongs to the prover, not to translation.

**P3.2. Date arithmetic is not FOL.** `d + 30_days` assumes a function symbol over `T × Duration → T`. Either (a) the ontology provides `add_days : T × ℕ → T` as a Func symbol with axioms in `fol-rules`, or (b) date arithmetic is pre-computed in translation and stored as a concrete `Const`. Option (b) is cleaner for a static legal rule; option (a) is needed if rents, durations, or due dates are themselves variables to reason over. The design must accommodate (a) — add a capacity family for temporal arithmetic.

**P3.3. `Permitted` as syntactic predicate works, but creates a second-class citizen.** The FOL layer can ingest, store, entail, and retract `Permitted(...)` atoms just like any other. What it cannot do: reason that `Permitted(x, φ)` and `Forbidden(x, φ)` are inconsistent, or that `Obligated(x, φ) → Permitted(x, φ)`. These deontic axioms belong in `fol-rules` as plain universally quantified rules and the FOL prover handles them classically. The only thing that genuinely can't live in this layer is **deontic model-theoretic consistency checking** (possible-worlds semantics). That remains out of scope.

**P3.4. The law-import session's write pipeline needs a CAN_WRITE_CANONICAL check.** The walk reached a point where L4 wrote to L2 fol-rules. Today this capability does not exist (review B8). Filing the Server-layer ADR is a precondition.

### Design updates

**U3.1.** Add a retrieval + combination family for temporal arithmetic:
- `capacity:retrieval:lookup_temporal_operator(op: str, *, context) -> AxiomTemplate`
- `capacity:combination:reduce_temporal_literal(formula, *, context) -> Formula` — folds constant date expressions at translation time.

**U3.2.** Document the deontic pattern: `fol-rules` may contain rules with deontic-predicate heads; these rules fire under standard FOL inference; no new capacity needed. Add a note to Part III.

**U3.3.** Promote the CAN_WRITE_CANONICAL ADR filing to a precondition (already in the review punch list §G item 7; reinforce).

---

## II.2 Example 2 — Biomedical process description

**Input.** *"In glycolysis, hexokinase phosphorylates glucose to form glucose-6-phosphate, consuming one ATP molecule."*

**Upstream.** Parse yields one sentence with two verbs (`phosphorylates`, `consuming`) and four domain nouns:
- `glycolysis` → no WordNet sense matches the biochemical process; WSD returns empty candidates
- `hexokinase` → specialised term; likely no WordNet sense
- `glucose` → has a WordNet sense, but DOLCE category mapping is thin
- `phosphorylate` → technical verb; no WordNet
- `glucose-6-phosphate` → chemical name; no WordNet
- `ATP` → acronym; no WordNet

This is the core stress: **most content words fail sense lookup**.

Assume role = `canonical` (biology textbook import).

### Translation attempt

Without ontology support, the translator can only produce:

```
∃ e1:EV, e2:EV, x1:?, x2:?, x3:?, x4:?.
    during(e1, glycolysis_process)
    ∧ phosphorylate(e1) ∧ PC(x1, e1, t1) ∧ theme(e1, x2) ∧ product(e1, x3)
    ∧ consume(e2) ∧ PC(?, e2, t1) ∧ theme(e2, x4)
```

Every `?` on a sort tag means "we don't know which DOLCE category". Every `hexokinase`, `glucose`, etc. is a free constant with no ontology binding.

### Ledger trace

```
L4 dispatches:
  comprehension:compose_statement_from_parse
    → for each content word, retrieval:lookup_category_for_sense
       - "hexokinase.n.01" → raises CategoryNotFound
    → capacity falls back to gap-handling trio:
        L4 invokes combination:assign_default_category("hexokinase.n.01")
            → returns DS_FOL_STATEMENT: PED(hexokinase_default)  (physical endurant — coarse default)
        L4 invokes signalling:emit_uncertainty_marker(
            unmapped_sense="hexokinase.n.01",
            propagated_to=(stmt_id1,))
            → returns DS_UNCERTAINTY_MARKER
  
    alternatively: L4 invokes interaction:ask_human_for_category("hexokinase.n.01")
        → returns DS_CATEGORY_ASSIGNMENT(assigned_category="PED", source="human")
    L4's choice among (default, ask, emit-and-propagate) is a learned policy.

  Repeat for glucose, phosphorylate, glucose-6-phosphate, ATP.
  
  comprehension:tag_epistemic_status(stmt, "observed")
  
  (write intents queue up; L4 batches them if the role=canonical session is authorised to write L2)
```

The statement lands in L5 with provenance listing the uncertainty markers. `validate_assumption` finds no inconsistencies (nothing to contradict), so no revision fires.

### Pressure points

**P2.1. The DOLCE ontology alone is insufficient for biochemistry.** This is the expected outcome per the handoff — the ontology's depth is the binding constraint on FOL expressive power. The gap-handling trio works as designed but produces a **shallow ledger** — every biochemical statement carries three-to-five uncertainty markers. `validate_assumption` cannot do meaningful work until the domain ontology is extended.

**P2.2. `assign_default_category` returns a `DS_FOL_STATEMENT` — but of what form?** The handoff says "assigns a default category to an unmapped sense." The concrete output for `hexokinase` would be something like `PED(hexokinase)` — i.e., an atom asserting that the referent is a physical endurant. But the sense IRI itself is not yet a constant in the FOL vocabulary. Translation needs a **sense-to-constant minting** step that `assign_default_category` implicitly performs. Pin this.

**P2.3. Uncertainty propagates through derivations.** If a later inference uses `hexokinase_default` as premise, the inferred statement should carry a downstream uncertainty marker. `emit_uncertainty_marker.propagated_to` is the right field, but no capacity automatically populates it on derivations. Add `capacity:signalling:propagate_uncertainty(derivation_result, sources) → DS_UNCERTAINTY_MARKER` or bake this into the proof-tree walker.

**P2.4. Biology ontology import is the real fix.** Long-term, `glycolysis`, `hexokinase`, etc. map to domain-ontology terms via `ref:global_<role>` links (ADR pattern). The FOL translator needs to consult multiple ontology graphs, not just DOLCE. Add `retrieval:lookup_category_for_sense` support for a **sequence** of ontology graphs (context-passed: `ontology_graphs: tuple[str, ...]`).

**P2.5. `assign_default_category` is currently unparameterised** — always falls back to `PED`? That seems too naive. Decompose per the review discipline:
- `capacity:combination:assign_default_category.physical_endurant_fallback`
- `capacity:combination:assign_default_category.perdurant_fallback`
- `capacity:combination:assign_default_category.quality_fallback`
- `capacity:combination:assign_default_category.heuristic_from_morphology` (uses upstream parse features)
L4 picks based on morphological / syntactic cues.

### Design updates

**U2.1.** Add **sense-to-constant minting** as a named step inside `compose_statement_from_parse`. The minted constants carry their source sense IRI in a provenance sub-field. Proposed helper: `capacity:retrieval:mint_constant_for_sense(sense_iri, *, context) -> Const`.

**U2.2.** Decompose `assign_default_category` into a strategy family (see P2.5). Rename existing capacity to `...default_category.physical_endurant_fallback` and add morphology-driven fallback.

**U2.3.** Extend `retrieval:lookup_category_for_sense` to accept a **sequence** of ontology graph IRIs via context key `ontology_graphs`. The capacity iterates through the sequence until a hit or exhausts — still pure, still I1-compliant.

**U2.4.** Add `capacity:signalling:propagate_uncertainty(derivation_stmt, source_markers) → DS_UNCERTAINTY_MARKER`. Invoked by L4 after every derivation that consumes uncertainty-marked premises.

**U2.5.** Document clearly: until domain ontologies are imported (DOLCE alone is thin on everything except foundational categories), biomedical / legal / scientific examples will produce shallow ledgers. This is a property of the ontology-driven translation commitment, not a design flaw.

---

## II.3 Example 5 — Causal / teleological commonsense

**Input.**
- S1: *"The plant wilted because it hadn't been watered in a week."*
- S2: *"Sarah, noticing this, filled a pitcher and watered it."*

**Upstream.** WSD:
- `plant` → `plant.n.02` (living organism, kingdom Plantae)
- `wilt` → `wilt.v.01` (lose turgidity)
- `water` (verb) → `water.v.02` (supply water to)
- `water` (noun, implicit) → `water.n.01` (liquid)
- `week` → `week.n.01` (time period)
- `pitcher` → `pitcher.n.01` (container for liquids)
- `notice` → `notice.v.01` (observe)
- `fill` → `fill.v.01` (put to capacity)
- Pronoun resolution: "this" ← the wilting event; "it" in S2 ← the plant

Role = operational (casual narrative; no teaching signal).

### Translation

```
S1 produces two events and a because-relation:
  ∃ e1:EV, e2:EV, t1:T.
      PD(e1) ∧ wilt(e1) ∧ PC(plant_1, e1, t1)  ∧ t1 < now_k
      ∧ ¬∃ e_water:EV. water.v.02(e_water) ∧ theme(e_water, plant_1)
                     ∧ PC(?, e_water, t') ∧ (now_k - 7days) ≤ t' < now_k
      ∧ because(e1, e2)    ← where e2 = the negated existential witness (¬∃ e_water...)
      ∧ plant.n.02(plant_1)

Tagged observed; role=operational; source_id="narrator_1".
```

Two issues at translation time:

(a) `because(e1, e2)` where `e2` is a *negated existential* is not a well-formed FOL atom — `because` takes terms, not formulas. Translation must either (i) reify the causal relation over event terms with a distinguished "absence event" constant, or (ii) use a higher-order workaround. DOLCE does not provide first-class causation. Option (i) looks like:

```
  ∃ e1, absence_1.
      wilt(e1) ∧ PC(plant_1, e1, t1)
      ∧ absence_of_watering(absence_1, plant_1, t_window)
      ∧ caused_by(e1, absence_1)
```

The absence-as-entity move is standard in linguistic semantics (Davidson / neo-Davidsonian) but forces the ontology to commit on a category for `absence_of_watering` events. Open question to the ontology: use a `Quality` or a dedicated `Absence` sub-category.

(b) "in a week" is a duration quantifier over the negated existential — a bounded window. `within(t_window, now_k - 7days, now_k)` predicate works.

```
S2 adds two events:
  ∃ e3:EV, e4:EV, e5:EV, pitcher_1:PED.
      PD(e3) ∧ notice(e3) ∧ PC(sarah, e3, t2) ∧ theme(e3, e1)
      ∧ PD(e4) ∧ fill(e4) ∧ PC(sarah, e4, t3) ∧ theme(e4, pitcher_1)
      ∧ pitcher.n.01(pitcher_1)
      ∧ PD(e5) ∧ water.v.02(e5) ∧ PC(sarah, e5, t4) ∧ theme(e5, plant_1)
      ∧ t2 ≤ t3 < t4  (narrative sequence)
      ∧ t4 < now_k
```

Role = operational.

### Ledger trace

```
After S1 ingestion:
  comprehension:compose_statement_from_parse      → DS_FOL_SET (5 atoms + 1 rule?)
  combination:assign_default_category("absence_of_watering") — gap-handling fires
  decomposition:enumerate_unbound_predicates(ledger) → DS_GAP_REPORT
    gaps: {cause(e1, ?), why_didn't_anyone_water(?), is_plant_alive(plant_1)?}
  L4 scores gap relevance (goal_alignment: "figure out what happens next in story" → low)
  L4 may invoke combination:populate_exception_closure on any strict rules with "plant" in the
      antecedent (defaults: ¬dead(plant_1), ¬artificial(plant_1))
  validation:validate_assumption → nothing to promote/retract

After S2 ingestion:
  comprehension:compose_statement_from_parse      → DS_FOL_SET
    Resolves "this" via coreference (upstream — not FOL's job, but FOL must accept the
    pre-resolved event-id reference)
    Resolves "it" ← plant_1
  validation:validate_assumption re-runs:
    The strict rule (assumed present in fol-rules graph, analytic from DOLCE+hort-domain):
      ∀ p. plant(p) ∧ watered(p, t) → ¬wilt_progresses(p, t+ε)
    now applies. No contradiction; the watering at t4 is consistent with the wilting at t1.
```

**The interesting case is abduction.** If a follow-up question asks *"Why did Sarah water the plant?"*, the FOL layer has no observed statement of Sarah's purpose. L4 dispatches:

```
derivation:abduce.kb_directed(
  ledger,
  target = Formula("purpose(e5, ¬wilt_progresses(plant_1, t))"),
  bound = 5000
) → DS_ASSUMPTION_CANDIDATES([
    purpose(e5, restore_turgidity(plant_1)),
    purpose(e5, ¬further_wilting(plant_1)),
    purpose(e5, keep_plant_alive(plant_1)),
  ])
```

Each candidate is tagged `assumed`, `assumption_kind=abduced`, and added to the ledger for validation against any further observations.

### Pressure points

**P5.1. Causation is not primitive in DOLCE.** The handoff acknowledged this. Practical options:
- (a) Commit to a `caused_by : EV × EV → Bool` predicate in a **commonsense causation** role-graph (new L2 role-graph).
- (b) Reify into a causal-chain ontology a la Mizoguchi or YAMATO.
- (c) Model causation as a pattern in the `fol-rules` graph (a synthetic rule linking wilting to water-absence).

Option (a) is the lightest lift and matches the handoff's "new L2 role-graph" pattern. The predicate itself is semantically opaque to the FOL prover — it's treated like any other atomic relation. Inference over causation happens via causal **rules** that L4-curated or learned.

**P5.2. Teleology (purpose) is also not primitive.** Same treatment: `purpose : EV × Formula → Bool` as a reified predicate. Abduction fills in purposes when ledger inconsistency or user query demands.

**P5.3. `fol.abduce.kb_directed` needs a target-shape parameter.** Abducing `purpose(e5, ?)` requires the prover to know that the placeholder is a formula-valued argument. This is higher-order peek-through, generally hard for FOL. Two workarounds:
- Use existential-over-constants: `∃ φ:Formula. purpose(e5, φ)` — requires formulas-as-terms reification.
- Precompile a **target-template library** from `fol-rules` that says "purposes of `water.v.02` events are typically drawn from {restore_turgidity, keep_alive, ...}" — then abduction picks from a finite candidate set.

The second option is more tractable and more honest about the learned prior. Add `retrieval:lookup_purpose_templates_for_event(event_pred, *, context) -> tuple[Formula, ...]` and have `abduce.kb_directed` consume it.

**P5.4. Absence-as-entity is a real ontology commitment.** Either the ontology gets an `Absence` category (simple: `Absence ⊑ AB` — abstract), or translation must avoid negated existentials in reified positions. Prefer the ontology commitment; the alternative contorts translation.

**P5.5. Multi-sentence reference resolution is upstream.** Coreference ("this", "it") is resolved before FOL sees the parse. The translator must trust the coreference decisions and translate on them. FOL can nonetheless *detect inconsistency* if coreference is wrong — e.g., if "it" resolved to the pitcher instead of the plant, the subsequent rule `water.v.02(e) ∧ theme(e, plant(p))` would fail to unify. This is a useful signal to send back to upstream coreference as a training signal — per the GAN-analogous pattern.

### Design updates

**U5.1.** Add a new L2 role-graph `commonsense-causation` holding:
- The `caused_by : EV × EV` predicate declaration (with `is_time_variant=False` — causation itself is time-invariant; the events it relates are time-tied).
- The `purpose : EV × Formula → Bool` predicate (reified-formula argument — flag as requiring special handling).
- Rules linking event patterns to typical causes (synthetic, status=pending_validation until ledger evidence promotes them).

**U5.2.** Add `capacity:retrieval:lookup_purpose_templates_for_event(event_pred, *, context) -> tuple[Formula, ...]`. Fed into `abduce.kb_directed` as context.

**U5.3.** Commit to an `Absence` sub-category in the ontology (or more precisely: flag the ontology-extension requirement and proceed with a placeholder). FOL capacities themselves don't change.

**U5.4.** Add back-signal capacity `capacity:learning_methods:emit_coreference_training_signal(resolution_attempt, unification_result, *, context) -> DS_TRAINING_SIGNAL`. Plugs upstream coreference into the oracle-distant-supervision pattern the review re-framed (B1/E1).

**U5.5.** Document: reified-formula arguments (`purpose(e, φ)`) require either formula-as-term lift in the AST or a finite template library. The design picks template library (simpler, more tractable).

---

## II.4 Example 4 — Multi-source contradiction

**Input.**
- Source A (Reuters): *"Candidate X won 52% to 48%."* — emitted 2026-04-23 08:00 UTC.
- Source B (local blog): *"Preliminary results show Candidate Y ahead by a clear margin."* — emitted 2026-04-23 07:45 UTC.

**Upstream.** Role = operational for both (system is consuming news, not being taught canonical truths about the election).

`trust_scores` in L4 context: `{"reuters.iri": 0.9, "local_blog.iri": 0.3}`.

### Translation

```
Source A translates to:
  ∃ tally:Q.
      election(election_1)
      ∧ won(X, election_1)
      ∧ vote_share(X, election_1, 0.52)
      ∧ vote_share(Y, election_1, 0.48)
  Tagged observed; role=operational; source_id="reuters.iri";
  ingestion_role provenance: operational (not canonical).

Source B translates to:
  ∃ lead:Q.
      preliminary_results(election_1)
      ∧ ahead(Y, election_1)
      ∧ margin_size(Y, election_1, "clear")   ← qualitative; translator may reify or mint opaque Const
  Tagged observed; role=operational; source_id="local_blog.iri".
```

Source B has a qualitative margin ("clear") that has no numeric reduction. Options:
- Translate `margin_size` as an opaque `Const("clear")` — prover can't reason about it
- Translate to `∃ m:Q. margin_size(Y, election_1, m) ∧ m > small_threshold_iri` — still reifies but gives the prover something
- Refuse and emit `DS_UNCERTAINTY_MARKER`

Pick option (b): minimal reification, keeps the door open for later quantitative corroboration.

### Ledger trace

```
Both statements land in L5.
validation:validate_assumption → ledger consistency check:

  derivation:localise_conflict(ledger) → DS_CONFLICT_LOCALISATION:
    unsat_core = (stmt_A, stmt_B)
    tags_in_core = {observed: (stmt_A, stmt_B)}
    rule_form = "strict"
    candidate_resolutions = (
      ("retract_assumption", stmt_A, ()),
      ("retract_assumption", stmt_B, ()),
    )
```

But wait — "won(X)" and "ahead(Y)" are not classically contradictory without a rule tying them. The FOL layer needs the rule:

```
  ∀ c1, c2, e. election(e) ∧ won(c1, e) ∧ c1 ≠ c2 → ¬ahead(c2, e)   ← from political domain fol-rules
```

With this rule present (synthetic, status=active in `fol-rules`, source=`ontology_axiom` or `human_declared`), the unsat core expands to include it, and `derive_alternative_forms` lets the prover chase either direction.

Now the revision step:

```
L4 picks a priority ordering:
  scoring:priority.source_trust(
    conflict_set=(stmt_A_id, stmt_B_id),
    trust_scores={"reuters.iri": 0.9, "local_blog.iri": 0.3},
    *, context)
    → ordering: (stmt_B_id, stmt_A_id)   ← lower trust first (to retract first)

combination:apply_revision(
    conflict=DS_CONFLICT_LOCALISATION,
    priority_ordering=(stmt_B_id, stmt_A_id)
  ) → DS_REVISION_PLAN:
    ordered_steps = (("retract_assumption", stmt_B_id, ()),)

L4 applies the plan:
  combination:cascade_retract(ledger, stmt_B_id) → (ledger', retracted_set)
  retracted_set = (stmt_B_id,)   (no cascade; nothing depended on it)
```

The ledger now holds `won(X, election_1)` as observed, `ahead(Y, election_1)` as retracted with `retraction_reason="lower-trust source contradicted by higher-trust source"`.

### Pressure points

**P4.1. Priority rule can flip based on observed vs source_trust.** Under `priority.observed_first`, both statements are `observed` so the rule doesn't distinguish. Under `priority.source_trust`, B retracts. L4's choice depends on task: for a news-aggregation pipeline, source_trust is right; for a historical archive, recency might be preferred. The design correctly models this via separate priority capacities.

**P4.2. Multiple equally-trusted sources at contradiction require a different rule.** If both sources were equally-trusted (A=0.9, B=0.9), source_trust returns an arbitrary ordering. L4 should fall back to a tiebreak policy (recency, or "prefer more specific claim"). This is an L4 meta-policy, not a new L3 capacity — the existing capacity set supports it.

**P4.3. Retraction should not be silent.** When L4 retracts an observed statement, users will care. The trace sink (`capacity:signalling:*`) should carry a `DS_SIGNAL_RECORD(signal_kind="observed_retracted_by_trust", payload={retracted: stmt_id, reason: ...})`. Add this signal kind.

**P4.4. The domain-specific rule tying `won` and `ahead` is load-bearing.** Without it, FOL sees no contradiction. Where does it come from?
- If it's `source=ontology_taxonomy`, it's encoded as part of political-domain ontology.
- If it's `source=learned_pattern`, the system derived it from past elections.
Either way, FOL doesn't mint it — L2 contributes it. Example reinforces the handoff's meta-observation: FOL value scales with ontology depth.

**P4.5. Qualitative → quantitative bridging at translation.** "Clear margin" → `m > small_threshold_iri` is a translation-time decision that embeds ontology knowledge (what "clear" means). Better: `intensity_quale(margin_size_y, clear_intensity)` with a separate ontology mapping from intensity qualia to numeric ranges. Keeps the translator honest about what it's doing.

### Design updates

**U4.1.** Add a signal kind: `DS_SIGNAL_RECORD.signal_kind` gets `"observed_retracted_by_trust"`. No new capacity — existing `emit_uncertainty_marker` pattern or the more general signalling family absorbs it.

**U4.2.** Document tie-break fallback policy: when `priority.source_trust` returns equal scores, L4 chains another priority capacity. No new L3 capacity.

**U4.3.** Add `capacity:retrieval:lookup_intensity_quale_mapping(quale_iri, *, context) -> tuple[tuple[float, float], ...]` (maps qualitative intensity tags to numeric ranges). Used by translation to handle qualitative modifiers cleanly.

**U4.4.** In Part III, reiterate: every interesting contradiction requires a domain rule in `fol-rules`. FOL-family implementation effort buys little until `fol-rules` is populated.

---

## II.5 Example 6 — Practical reasoning under goal constraints

**Input.** *"I want to wash my car. The car wash is 50 meters away. Should I walk or drive?"*

**Upstream.** WSD:
- `wash` → `wash.v.02` (clean with water)
- `car` → `car.n.01`
- `car wash` → `car_wash.n.01` (commercial facility — distinct sense from the verb phrase)
- `meter` → `meter.n.01` (unit of length)
- `walk` → `walk.v.01` (locomote on foot)
- `drive` → `drive.v.02` (operate a vehicle)

Speaker = user (first person). Role = operational (the speaker is querying; not teaching).

### Translation

```
The three sentences translate to:
  (goal)   goal(speaker, washed(speaker.car))
  (fact)   distance(speaker.location, car_wash_1.location, 50_meters)
  (query)  decide_action(speaker, {walk, drive}, ?) ← not a well-formed FOL atom

Tagged observed for goal and fact; the query is a meta-request to a practical-reasoning
pipeline, not a FOL ingestion.
```

### Ledger trace

```
After ingestion of S1 + S2, ledger holds:
  goal(speaker, washed(speaker.car))
  car(speaker.car)
  car_wash(car_wash_1)
  distance(speaker.location, car_wash_1.location, 50_meters)
  (plus ontology-derived:)
  ∀ c. car(c) ∧ washed(c) → satisfied(washed(c))

L4 dispatches the practical-reasoning pipeline (out of FOL scope — a separate L3 family
handling "should-I" queries). That pipeline asks FOL:

  derivation:entails.bounded(
    ledger + {walk(speaker, car_wash_1.location)},
    goal(speaker, washed(speaker.car)),
    bound=1000
  ) → independent    ← walking doesn't entail the goal OR its negation

  derivation:entails.bounded(
    ledger + {walk(speaker, car_wash_1.location)},
    at(speaker.car, car_wash_1.location),
    bound=1000
  ) → contradicts    ← walking leaves the car at speaker.location (from ontology:
      ∀ a, loc. agent_motion(a, loc) ∧ ¬carries(a, c) → at(c, old_location(c)))

So walking → car-stays-put → goal unreachable via walking.

  derivation:entails.bounded(
    ledger + {drive(speaker, speaker.car, car_wash_1.location)},
    at(speaker.car, car_wash_1.location),
    bound=1000
  ) → entails        ← driving moves speaker and car together
```

FOL returns three verdicts (`independent`, `contradicts`, `entails`) to the practical-reasoning pipeline. That pipeline combines them with preference/cost weights (walking is cheaper but doesn't work; driving works but costs fuel) — **out of FOL scope**.

### Pressure points

**P6.1. The FOL layer produces well-typed verdicts, no decisions.** This confirms the handoff's scope commitment. The "should I" question is answered by combining FOL's entailment verdicts with practical-reasoning preferences in L4 / a sibling capacity family.

**P6.2. What-if hypotheticals are a new usage pattern.** The practical-reasoning pipeline added `walk(speaker, car_wash_1.location)` to the ledger **hypothetically** to check entailment. This is exactly what the `hypothesised` tag is for. But the design so far only generates `hypothesised` statements from rule-generation — not from practical-reasoning dispatch. Add a usage note:

> The `hypothesised` tag is also the landing place for what-if probes from upstream practical-reasoning, planning, and counterfactual pipelines. These probes are ingested as ordinary statements, tagged `hypothesised`, and revisit the ledger consistency check; results are returned to the dispatching pipeline without affecting the long-term ledger.

**P6.3. Ledger branching matters.** Probing "what if I walk" and "what if I drive" implies the ledger forks temporarily. The design so far has one ledger per task. Either:
- **(a)** The ledger supports branch/merge operations natively (overlays, diff-based).
- **(b)** L4 copies the ledger per probe.

Option (b) is simpler and fine for operational correctness. (a) is a performance optimisation. Committing to (b) as the default and leaving (a) as a post-v1 perf item is sane.

**P6.4. Rules about motion are themselves ontology-level.** `∀ a, loc. agent_motion(a, loc) ∧ ¬carries(a, c) → at(c, old_location(c))` is a commonsense-physics rule. It belongs in `fol-rules` as synthetic, source=`ontology_axiom`. Without it, the FOL layer cannot rule out walking — the walk-or-drive verdict depends entirely on the rule being present. Example reinforces: **shallow ontology → shallow FOL inference**.

**P6.5. Closed-world on `carries` is needed.** The rule above requires `¬carries(speaker, speaker.car)` to fire. Nothing observed says this — so either closed-world (`fol.populate_exception_closure` from review B3, at the carries-predicate level) or explicit translation of "walk" as "motion without carrying anything". Prefer the former; the exception-closure capacity naturally produces `¬carries(speaker, c)` for all c the ledger doesn't assert as carried.

### Design updates

**U6.1.** Document the `hypothesised` tag's role as a landing place for what-if probes from upstream pipelines. No new capacity; clarification only.

**U6.2.** Commit to **ledger copy-per-probe** as the v1 concurrency model for hypothetical reasoning. Post-v1: explore overlay/diff-based branching for performance.

**U6.3.** Add a commonsense-physics role-graph (or contribute to an existing `commonsense-causation` style graph per U5.1) with motion-and-transport rules.

**U6.4.** Reinforce review B3's `fol.populate_exception_closure` — it is load-bearing for practical reasoning, not just strict-rule-with-exceptions. Rename the capacity to reflect the broader role: `capacity:combination:populate_negative_closure(predicate_family, ledger, *, context) -> DS_ASSUMPTION_CANDIDATES`. Its job: generate `¬P(x, ...)` assumptions for every entity `x` the ledger hasn't asserted `P(x, ...)` for, within a bounded predicate family.

---

# PART III — Design-update delta

Changes Part I requires to absorb the five walks. Organized by section of Part I.

### Against §1 (package layout)

- Rename `combination/populate_exception_closure.py` → `combination/populate_negative_closure.py` (U6.4).
- Decompose `combination/assign_default_category.py` into a strategy sub-package (U2.2): `combination/assign_default_category/{physical_endurant_fallback,perdurant_fallback,quality_fallback,heuristic_from_morphology}.py`.
- Add `retrieval/mint_constant_for_sense.py` (U2.1).
- Add `retrieval/lookup_temporal_operator.py` (U3.1).
- Add `retrieval/lookup_intensity_quale_mapping.py` (U4.3).
- Add `retrieval/lookup_purpose_templates_for_event.py` (U5.2).
- Add `combination/reduce_temporal_literal.py` (U3.1).
- Add `signalling/propagate_uncertainty.py` (U2.4).
- Add `learning_methods/emit_coreference_training_signal.py` (U5.4).

### Against §3 (DataState catalogue)

- `DS_SIGNAL_RECORD.signal_kind` gains `"observed_retracted_by_trust"` (U4.1).
- No other DataState changes — the existing shapes absorb everything.

### Against §4 (capacity signature catalogue)

Rename + signature extensions:

| Old IRI | New IRI | Notes |
|---|---|---|
| `capacity:combination:populate_exception_closure` | `capacity:combination:populate_negative_closure` | Broader scope (U6.4). Signature: `(predicate_family: str, ledger: DS_FOL_LEDGER, bound_entities: tuple[Const, ...], *, context) -> DS_ASSUMPTION_CANDIDATES` |
| `capacity:combination:assign_default_category` | `capacity:combination:assign_default_category.{variant}` | Strategy family (U2.2) |
| `capacity:retrieval:lookup_category_for_sense` | (same) | Now accepts `context["ontology_graphs"]: tuple[str, ...]` for multi-ontology chained lookup (U2.3) |

Additions:

| IRI | Signature |
|---|---|
| `capacity:retrieval:mint_constant_for_sense` | `(sense_iri: str, *, context) -> Const` |
| `capacity:retrieval:lookup_temporal_operator` | `(op: str, *, context) -> AxiomTemplate` |
| `capacity:retrieval:lookup_intensity_quale_mapping` | `(quale_iri: str, *, context) -> tuple[tuple[float, float], ...]` |
| `capacity:retrieval:lookup_purpose_templates_for_event` | `(event_pred: str, *, context) -> tuple[Formula, ...]` |
| `capacity:combination:reduce_temporal_literal` | `(f: Formula, *, context) -> Formula` |
| `capacity:signalling:propagate_uncertainty` | `(derivation_stmt: DS_FOL_STATEMENT, source_markers: tuple[DS_UNCERTAINTY_MARKER, ...], *, context) -> DS_UNCERTAINTY_MARKER` |
| `capacity:learning_methods:emit_coreference_training_signal` | `(resolution_attempt: Mapping[str, str], unification_result: Literal["hit", "miss"], *, context) -> DS_TRAINING_SIGNAL` |

### Against §6 (context schema)

Add to the context-schema contribution:

| Key | Type | Read by | Purpose |
|---|---|---|---|
| `ontology_graphs` | `tuple[str, ...]` | `lookup_category_for_sense`, any retrieval chain | Ordered ontology graphs to consult |
| `purpose_template_library` | `str` IRI | `abduce.kb_directed` | Which purpose-template L2 graph is current |

### New L2 role-graph requirements (FOL family's asks on L2)

Reinforcing and consolidating from the walks:

| New role-graph | Purpose | Surfaced by |
|---|---|---|
| `commonsense-causation` | Hold `caused_by`, `purpose` predicate declarations and rules linking event patterns to typical causes and purposes | U5.1 |
| `commonsense-physics` | Motion, transport, containment rules | U6.3 |
| Ontology extension: `Absence` sub-category | For negated-existential reification | U5.3 |
| Ontology extension: `intensity_quale` mappings | Qualitative → quantitative bridging | U4.3 |
| Ontology extension: per-predicate `is_time_variant` flag | Handoff §4.3 already required; walks confirm necessity | Examples 3, 5 |

### Cross-walk meta-observations

**M1. The FOL layer is a thin shell on a thick ontology.** Every example's hardest moment was an ontology gap, not a capacity gap. The capacity catalogue is small and stable; the L2 work is large and ongoing. This is the handoff's own meta-claim, confirmed in five walks.

**M2. Strict-FOL + tags + rule transformations absorbed every pressure.** None of the walks required escape to non-monotonic, modal, or higher-order logic at the object level. Deontic (Ex 3), teleology (Ex 5), and practical reasoning (Ex 6) all reduced to FOL with domain predicates or to out-of-scope sibling pipelines consuming FOL verdicts. The review's re-framing ("classical proof calculus + non-monotonic ledger dynamics") is the right framing for these walks.

**M3. `populate_negative_closure` is load-bearing.** Originally proposed as the fix to a footnote (review B3); by Example 6 it is central. Rename + broaden to match the actual role.

**M4. Abduction needs templates, not blank-slate generation.** `abduce.kb_directed` with a purpose-template library is how teleology works without leaving FOL. Same pattern likely applies to cause templates and similar reified predicates. Generalise later if Example 7+ demand it.

**M5. Translation ≠ inference.** The walks show translation is where most ontology contact happens (sort assignments, default categories, constant minting, temporal-literal reduction). Translation is increasingly its own sub-system and should get its own developer guide chapter once the design plan is implementation-ready.

**M6. Copy-per-probe is the v1 concurrency story.** All hypothetical reasoning uses ledger copies. Overlay/diff is a post-v1 optimisation.

**M7. The CAN_WRITE_CANONICAL Server-layer ADR is a **hard** precondition.** Example 3 would have been blocked without it. File the ADR before implementation begins.

---

## IV. Implementation readiness checklist

Before opening a pull request against `falkormg_capacity/fol/`:

- [ ] Part III's package layout changes are applied.
- [ ] `syntax.py` and `prover.py` are in place with the protocols as specified.
- [ ] `datastates.py` has all dataclasses incl. `minted_at`, `assumption_kind`, `retraction_reason`, `source_id`.
- [ ] At least one concrete `Prover` backend is implemented (suggested: in-process resolution for testable correctness on small fragments).
- [ ] `context_schema.py` lists every context key the FOL family reads, aligned with L4's ratified schema.
- [ ] The Server ADR for `CAN_WRITE_CANONICAL` is filed and Accepted.
- [ ] `fol-rules` L2 role-graph is scaffolded (empty OK) with the node shape per handoff §7.1.
- [ ] `commonsense-causation` and `commonsense-physics` role-graphs are scaffolded (empty OK).
- [ ] Example 1–6 walk-throughs have fixture files in `tests/fol/fixtures/example_N/`.
- [ ] The L4 team has ratified the context-schema additions (§6 + Part III additions).
- [ ] The ontology team has committed to the `Absence` sub-category and to multi-ontology chained lookup.

---

*End of design plan + walk-through.*
