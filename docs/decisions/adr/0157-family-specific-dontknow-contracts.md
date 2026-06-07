---
title: L3 capacity dont-know contracts are family-specific, not universal
status: Accepted
date: 2026-06-01
layer: L3
aliases: [reframe-D46, L3-22, L3-35]
---

# ADR-0157: L3 capacity dont-know contracts are family-specific, not universal

**Status:** Accepted

**Date:** 2026-06-01

## Context

Chat A R6 (D46) stated directional preference: "every L3 capacity MUST implement `unhandled_inputs` semantics. No opt-out." Source: WSD UC-WSD-14 ("marker emission rather than silent junk").

Reanalysis: "no opt-out universal" is type-meaningless for several L3 families. Chat A R3 L3-35 explicitly says `decision.*`, `scoring.*`, `metric.*`, `combination.*`, `comparator.*`, `evaluator.*`, `validate.*` families return scalars/enums/method-specific objects (not DataStates). Their dont-know paths are already covered by R2 ReplanVerdict (Chat A) + R3 DontKnowReason + R3 TaskOutcome at the L4 level. Forcing a parallel `unhandled_inputs` contract on a `scoring.attention_score → int` capacity is meaningless ceremony.

ADR-0157 picks family-specific semantics, reversing the universal "no opt-out" framing.

## Decision

5-shape dont-know catalog:

1. **DATASTATE_MARKER** — DataState-producing families return `DS_UNHANDLED_INPUT` sentinel.
2. **OPTIONAL_RETURN** — families returning `Optional[T]` use `None` for dont-know.
3. **VERDICT** — families returning verdict objects with explicit dont-know channels (e.g., `ReplanVerdict.decision="abort"`).
4. **VALIDATION_RESULT** — `validate.*` family returns `ValidationResult(valid=False, reasons=[...])` per Phase 36 pattern.
5. **NO_DONT_KNOW** — function is total over its domain; dont-know impossible. `predicate.*` default.

Family rule is **implicit from capacity IRI prefix**. No registration field (`dont_know_contract_iri` not added; PB-D46-1 retracted earlier draft). Family→shape mapping in `mindsos_capacity/family_rules.py`:

```python
class FamilyDontKnowShape(Enum):
    DATASTATE_MARKER = "datastate_marker"
    OPTIONAL_RETURN = "optional_return"
    VERDICT = "verdict"
    VALIDATION_RESULT = "validation_result"
    NO_DONT_KNOW = "no_dont_know"

FAMILY_RULES: Dict[str, FamilyDontKnowShape] = {
    # method-library prefixes (name-position lookup)
    "combination": OPTIONAL_RETURN,
    "comparator": OPTIONAL_RETURN,
    "evaluator": OPTIONAL_RETURN,
    "metric": OPTIONAL_RETURN,
    "mechanism": OPTIONAL_RETURN,
    # top-level family categories
    "scoring": OPTIONAL_RETURN,
    "decision": VERDICT,
    "predicate": NO_DONT_KNOW,
    "validate": VALIDATION_RESULT,
    "transform": DATASTATE_MARKER,
    "derive": DATASTATE_MARKER,
    "perception": DATASTATE_MARKER,
    "process": DATASTATE_MARKER,
    "hint": OPTIONAL_RETURN,        # returns HintNode (intel-MM composite)
    "planning": OPTIONAL_RETURN,    # returns Plan/Milestone (intel-MM composites)
    "dream": OPTIONAL_RETURN,       # orchestration; None on no-aggregation
    "code": DATASTATE_MARKER,
    "retrieval": OPTIONAL_RETURN,
    "promotion_rule": OPTIONAL_RETURN,
    "signal": OPTIONAL_RETURN,      # renamed from "signal_source"
    "adapter": DATASTATE_MARKER,
    "pattern": OPTIONAL_RETURN,
    "als": OPTIONAL_RETURN,
    "phase6": OPTIONAL_RETURN,
}
```

Two-level lookup:

```python
def family_rule_for(capacity_iri: str) -> FamilyDontKnowShape:
    parts = capacity_iri.split(":")        # ["capacity", category, name]
    category = parts[1]
    name = parts[2]
    name_prefix = name.split(".")[0]
    # Try name prefix first (method libraries: combination.bayesian → "combination")
    if name_prefix in FAMILY_RULES:
        return FAMILY_RULES[name_prefix]
    # Fall back to category (top-level families: scoring.attention_score → "scoring")
    if category in FAMILY_RULES:
        return FAMILY_RULES[category]
    # Permissive default + info log
    log.info(...)
    return FamilyDontKnowShape.DATASTATE_MARKER
```

`DS_UNHANDLED_INPUT` registered v1 via this ADR: full IRI `datastate:marker.unhandled_input` per ADR-0158 naming convention. Constant exported from `family_rules.py`.

`DontKnowReason` enum (Chat A R3 + R4 D20 retirement) gains new value `UNHANDLED_INPUT`. Full enum: `NO_MATCHING_PATTERN`, `LOW_MAPPING_CONFIDENCE`, `PIPELINE_UNAVAILABLE`, `UNRESOLVED_AMBIGUITY`, `UNHANDLED_INPUT`.

WSD Monitor `update_state` capacities (`wsd-update`, `fol-update`, etc.) follow DATASTATE_MARKER discipline: return `DS_UNHANDLED_INPUT` instead of new state on uninterpretable signal; L4 substrate skips SCMSState write + fires problem-trace event with `unhandled_at_capacity_iri` + `unhandled_signal_payload`.

`decision.*` family wraps bare-value returns in canonical verdict types per L3-36 family contract: `TierVerdict`, `GoalVerdict`, `PipelineFindVerdict`, `PromotionRuleVerdict`, plus shipped `ReplanVerdict`. Uniform VERDICT family rule preserved.

Phase 27–33 audit (`confirmation_docs/PHASE_27_DONT_KNOW_AUDIT.md`) deferred to ADR-0156 ship phase X3 R0; verifies each shipped capacity's existing return path matches its family rule.

## Consequences

**Good:**

- Type-natural per family; reuses R2 ReplanVerdict + R3 DontKnowReason + Phase 36 ValidationResult; no parallel dont-know type system.
- Phase 27–33 audit shrinks to "verify each shipped capacity's existing return path encodes dont-know honestly" (most do).
- WSD UC-WSD-14 satisfied via DATASTATE_MARKER family for SCMS Monitor update_state path.
- L4 dispatch logic per family rule is deterministic from `capacity_iri` prefix.

**Cost:**

- Reverses Chat A R6 universal direction — documented in §rationale + HANDOFF §3.1.5 footnote.
- Catalog of dont-know shapes (5 patterns) + family→shape mapping table — paid once in ADR-0157, never again.
- Admin authoring requires knowing per-family discipline; partially mitigated by family rule being implicit from prefix.

## Alternatives considered

1. **A — Universal predicate** (`def can_handle(self, inputs) -> bool` on every capacity) — rejected: predicate type-meaningless for `scoring.attention_score(task, context) -> int`; default-True makes contract toothless.

2. **B — Universal return-side marker** (every capacity returns `Result | UnhandledMarker`) — rejected: forces `Optional[bool]` on predicates (where bool IS the dont-know signal); semantically incoherent.

3. **D — Hybrid** (universal method + family-specific defaults) — rejected: abstraction without simplification; universal signature doesn't compose with non-DataState return values.

## Sequencing

Ship phase **X1** — bundled with ADR-0158 (DataState naming convention). Shared `identifiers.py` realm constants + `family_rules.py` module. Smallest scope; saturates at R3.

## Rationale

Per-decision rationale, 3-round saturation, the 5-shape catalog refinement from 6→5, and the family rule corrections (`signal_source` → `signal`, `phase6` added, `hint`/`planning`/`dream` corrected to OPTIONAL_RETURN) at `docs/_workbench/L1_L3_REFRAME_DECISIONS.md` §D46 + §L3-36-to-L3-51-family-batch.

## Amendment 1 (Phase 42 / L3-57) — FAMILY_RULES key reconciliation

Phase 40 transcribed the `FAMILY_RULES` dict verbatim, leaving a latent
key-vocabulary mismatch against the shipped `FUNCTIONAL_CATEGORIES`
(ADR-0065): the keys `derive`/`signal` did not match the shipped category
names `derivation`/`signalling`, and seven categories had no key — so 9 of
the 13 categories resolved via the permissive `DATASTATE_MARKER` default
rather than by intent (Phase 40 ship pushback PB-8; tracked L3-57). The
Phase 27 dont-know audit (`confirmation_docs/PHASE_27_DONT_KNOW_AUDIT.md`)
decided **Option 3** — fix the groundable, defer the genuinely unknown:

- **Rename** `derive` → `derivation`, `signal` → `signalling` (typo-class
  mismatches; intended shape unchanged: DATASTATE_MARKER / OPTIONAL_RETURN).
- **Add** `consolidate` → DATASTATE_MARKER and `trace` → DATASTATE_MARKER
  (shapes grounded by the shipped `consolidate:mm` / `trace:problem`).
- **Defer** `comprehension`, `decomposition`, `path-finding`,
  `interaction`, `learning-methods` to their owning installation chats;
  recorded as `family_rules.DEFERRED_DEFAULT_CATEGORIES` and pinned by
  `tests/phase_42/test_phase_27_audit_doc.py` so the deferred set cannot
  grow silently. Each owning chat adds the explicit key when it ships the
  first capacity in that category.

The two-level lookup and the 5-shape catalog are unchanged.
