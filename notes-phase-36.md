# Phase 36 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

L2 Hybrid Validators Home — semantic validators ship; KLWriteHandle.validate_node body wired (ADR-0139 flipped Accepted; §amendment-1 with 3 clauses)

## tester_notes

### Background

Phase 36 ships ADR-0139's hybrid invariant home — L1 enforces structural
invariants at write (schema, XRef integrity, reserved keys, ID uniqueness;
already shipped Phase 04-13), KL exposes pure-function semantic validators
in `mindsos_knowledge/validators.py` (NEW at Phase 36). L3 write capacities
call validators as preconditions before `handle.write_and_validate(...)`
per ADR-0139 §Decision §Capacity-contract. Validator bypass is a code-
review failure, not a runtime error (review-checklist.md §4 — NEW at
Phase 36).

ADR-0139 flipped Proposed → Accepted via §amendment-1 (3 clauses: literal
§Accept(a) closure with all 5 validators shipping; §Accept(b) via the 2
wired capacities calling `validate_role_routing` through
`handle.validate_node`; per-flow extension carry-forward for adapter
registry growth). ADR-0143 §Implementation Phase 36 footer documents
`validate_node` body wired + `validate_xref` body deferred per-flow
(no XRef-writing capacity at Phase 36). PHASE_MAP §36 §inline-amendment
reframes features-line + Tests-line wording under Option B
(capacity-body composition, not runtime kwarg).

### Design saturation

6 design rounds (R0 + 5 re-litigations + R5 saturation pass). Picks
shifted twice:

- **R2 reverted R1-PB-A**: per-flow discipline doesn't extend to pure-
  function substrate. Ship all 5 validators (not just `validate_role_routing`).
  ADR-0139 §Accept(a) literal closure preserved; no §Accept-text edits.
- **R4 overturned R2-PB-I via R3-PB-E probe**: `mindsos_knowledge/__init__.py`
  re-exports all 5 existing exceptions consistently. `SemanticValidationError`
  + `ValidationResult` join the re-export set. No `len(__all__) == N`
  count sentinel exists in `mindsos_knowledge` test surface — non-breaking
  delta.

Load-bearing R0 PB-1 — validator-composition scope shape — locked to
**Option B (capacity-body composition per ADR-0139 §Capacity-contract)**.
Rejected: A (handle-side `scope` kwarg — runtime-bypass knob for the
discipline ADR-0139 §Decision wants socially enforced; collides with
ADR-0143 §Constraint), C (hybrid optional `validators=()` kwarg — three
places "where composition lives"; over-engineering).

R3-PB-A locked the dispatch shape: `_VALIDATORS_BY_ROLE` adapter
registry mirroring `_IRI_BUILDERS` pattern (R3-PB-A; symmetric with
Phase 34's R1-PB-B). Heterogeneous validator signatures handled at the
adapter layer, not at the call site.

R3-PB-H locked the pre-mint timing rationale for `validate_role_routing`
despite structural overlap with `handle.graph()` `KeyError`: semantic
validator fires in capacity precondition BEFORE `mint_iri` → fail-fast
without IRI churn; better diagnostics. Returns `ValidationResult` (not
raise) → capacity body decides raise-vs-PTR per call site (ADR-0146
§amendment-1 clause 1 stays open).

### Ship surface

**Halvim tree (committed at phase-36 branch):**

- NEW `mindsos_knowledge/validators.py` — 5 validators + `ValidationResult`
  + `_VALIDATORS_BY_ROLE` registry (2 adapters: memories + problem-trace).
- EDIT `mindsos_knowledge/exceptions.py` — `SemanticValidationError`
  (carries `.result: ValidationResult`).
- EDIT `mindsos_knowledge/__init__.py` — re-exports
  `SemanticValidationError` + `ValidationResult`; version `+phase34` →
  `+phase36`.
- EDIT `mindsos_knowledge/write_handle.py` — `validate_node` body wired
  via `_VALIDATORS_BY_ROLE`; `validate_xref` STAYS raising
  (per-flow deferred).
- EDIT `mindsos_capacity/builtins/consolidate.py` — body adds
  `handle.validate_node` precondition + `SemanticValidationError`
  raise before `write_and_validate`.
- EDIT `mindsos_capacity/builtins/trace.py` — same pattern.
- EDIT `tests/phase_33/test_kl_writeable.py` — sentinel flipped
  (R4-PB-B): `validate_node` now returns `ValidationResult`;
  `validate_xref` raise sentinel stays.
- NEW `tests/phase_36/` — 3 test files (`test_validators.py`,
  `test_capacity_preconditions.py`, `test_adr_amendment_sentinels.py`)
  + `__init__.py`. ~30 test cases total. Sentinel chain extends
  `14a→15a→15b→35→36`.
- EDIT `confirmation_docs/PHASE_MAP.md` §36 — §inline-amendment block
  (1 clause covering features-line scope wording + Tests-line "both via
  write_and_validate" wording).
- EDIT `docs/dev/review-checklist.md` — item 1 split (`validate_node`
  wired; `validate_xref` deferred) + new section 4 "Capacity
  preconditions call semantic validators (ADR-0139)".
- VERSION BUMP 10 sites: `+phase34 → +phase36` (skipping `+phase35`
  per design-only precedent). pyproject.toml + docker-compose.yml
  (prod+test) + 8 package `__init__.py` / `manifest.toml` literals.

**Parent tree (filesystem-only, Model C; no commit):**

- EDIT `docs/decisions/adr/0139-hybrid-invariant-home.md` — Status
  Proposed → Accepted; §amendment-1 with 3 clauses appended; §Impl
  Phase 36 footer appended. Original §Implementation refs section
  untouched (R5-PB-A; Phase 35 precedent).
- EDIT `docs/decisions/adr/0143-kl-write-handle-pattern.md` — §Impl
  Phase 36 footer appended documenting `validate_node` wired +
  `validate_xref` defers.
- EDIT `docs/dev/internals/knowledge.md` — "Validator surface" section
  appended (validators table + composition contract + per-flow
  extension + bypass discipline) per ADR-0139 §Accept(c) + R2-PB-C.

### Carry-forwards to Phase 38 (37 RETIRED)

1. `handle.validate_xref` body still deferred; wires alongside first
   XRef-writing L3 capacity (per ADR-0139 §amendment-1 clause 3).
2. The 4 unconsumed validators (`validate_local_to_global_ref`,
   `validate_alignment_role_naming`, `validate_ref_type`,
   `validate_promotion_candidate`) await per-flow consumer capacities.
   Pure-function tests cover them; no integration coverage until a
   capacity wires them.
3. ADR-0146 §amendment-1 clause 1 (raise vs return PTR) remains open.
   `SemanticValidationError.result` is the carry-forward hook for the
   eventual L4-driven flip — a future PTR-returning capacity body
   builds a `ProblemTraceRecord` from `exc.result` without re-running
   the validator.
4. ADR-0147 §amendment-1 clause 3 (per-flow strict for L3 write
   capacities) remains binding. Phase 36's `_VALIDATORS_BY_ROLE`
   adapter per-flow extension (ADR-0139 §amendment-1 clause 3) is
   the L2 substrate parallel.

### Open questions deferred

- **Validator-body drift risk.** ADR-0139 §Semantic-invariants lists 5
  validators as a starting set; new invariants get added per ADR-0139
  §Consequences "new invariants get one home (KL) and propagate to all
  capacities by code review." Phase 36 sets the precedent; no Phase 36
  evidence yet for how additions land in practice.
- **Multi-validator chain semantics.** Phase 36 adapters call exactly
  one validator each (`validate_role_routing`). First-failure-wins
  semantics (R3-PB-I) is documented but not exercised; the first
  multi-validator chain (per-flow phase) will be the first real test.

### Process notes

- **Phase 35 ship completed mid-chat** — Phase 35 squash-merged at
  sha `36d9125` (PR #45). Date-placeholder fill commit at `0cb216e`.
  Phase 36 branched off main at `0cb216e`. The chat had to pause
  Phase 36 design impl-start to complete Phase 35's ship-mechanics on
  the user side — `[[feedback-confirm-phase-machine-locality]]` +
  branch-off-prior-squash discipline both load-bearing.
- **R5 saturation gate fired clean.** R4 probes returned actionable
  confirmations; R5 produced 5 impl-locks (R5-PB-A through E) — all
  anticipated by earlier rounds, zero design reversals. Pattern
  matches Phase 35 §9 saturation signature.
- **PHASE_MAP §36 §inline-amendment under R3-PB-F is the third
  consecutive features-line wording correction** (Phase 34, 35, 36 all
  amended). The pattern from Phase 35 §9 stands: "features-line wording
  in PHASE_MAP is **not** authoritative once shipped reality diverges
  — ADR §Implementation footers + DESIGN_LOG carry the load."

### Observed nothing-surprising-yet

Test runs pending tester confirmation in container; design-only
predictions per R5 ship-surface freeze. No B-36-T* hotfixes identified
at impl-write time. Sentinel-flip in `tests/phase_33/test_kl_writeable.py`
covers the `validate_node`-now-returns-ValidationResult forward-anchor
class extension (B-27-T1 precedent).
