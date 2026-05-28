# Phase 36 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

L2 Hybrid Validators Home — semantic validators ship; KLWriteHandle.validate_node body wired (ADR-0139 flipped Accepted; §amendment-1 with 3 clauses)

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

### Background

Phase 36 ships ADR-0139's hybrid invariant home — L1 enforces
structural invariants at write (schema, XRef integrity, reserved
keys, ID uniqueness; already shipped Phase 04-13), KL exposes
pure-function semantic validators in `mindsos_knowledge/validators.py`
(NEW at Phase 36). L3 write capacities call validators as
preconditions before `handle.write_and_validate(...)` per ADR-0139
§Decision §Capacity-contract. Validator bypass is a code-review
failure, not a runtime error (review-checklist.md §4 — NEW at
Phase 36).

ADR-0139 flipped Proposed → Accepted via §amendment-1 (3 clauses:
literal §Accept(a) closure with all 5 validators shipping; §Accept(b)
via the 2 wired capacities calling `validate_role_routing` through
`handle.validate_node`; per-flow extension carry-forward for adapter
registry growth). ADR-0143 §Implementation Phase 36 footer documents
`validate_node` body wired + `validate_xref` body deferred per-flow
(no XRef-writing capacity at Phase 36). PHASE_MAP §36
§inline-amendment reframes features-line + Tests-line wording under
Option B (capacity-body composition, not runtime kwarg).

### Design saturation

6 design rounds (R0 + 5 re-litigations + R5 saturation pass). Picks
shifted twice:

- **R2 reverted R1-PB-A**: per-flow discipline doesn't extend to
  pure-function substrate. Ship all 5 validators (not just
  `validate_role_routing`). ADR-0139 §Accept(a) literal closure
  preserved; no §Accept-text edits.
- **R4 overturned R2-PB-I via R3-PB-E probe**:
  `mindsos_knowledge/__init__.py` re-exports all 5 existing
  exceptions consistently. `SemanticValidationError` +
  `ValidationResult` join the re-export set. No `len(__all__) == N`
  count sentinel exists in `mindsos_knowledge` test surface —
  non-breaking delta.

Load-bearing R0 PB-1 — validator-composition scope shape — locked
to **Option B (capacity-body composition per ADR-0139
§Capacity-contract)**. Rejected: A (handle-side `scope` kwarg —
runtime-bypass knob for the discipline ADR-0139 §Decision wants
socially enforced; collides with ADR-0143 §Constraint), C (hybrid
optional `validators=()` kwarg — three places "where composition
lives"; over-engineering).

R3-PB-A locked the dispatch shape: `_VALIDATORS_BY_ROLE` adapter
registry mirroring `_IRI_BUILDERS` pattern (symmetric with Phase
34's R1-PB-B). Heterogeneous validator signatures handled at the
adapter layer, not at the call site.

R3-PB-H locked the pre-mint timing rationale for
`validate_role_routing` despite structural overlap with
`handle.graph()` `KeyError`: semantic validator fires in capacity
precondition BEFORE `mint_iri` → fail-fast without IRI churn;
better diagnostics. Returns `ValidationResult` (not raise) →
capacity body decides raise-vs-PTR per call site (ADR-0146
§amendment-1 clause 1 stays open).

### Test results

- **Cumulative docker:** `3373 passed, 57 skipped` (Phase 35 baseline
  3342/52 → +31 net at Phase 36). Of the +31: ~28 new test cases
  in `tests/phase_36/` + 3 sentinel-flip recoveries that B-36-T2
  fixed.
- **`mindsos doctor --self-test`:** OK. Confirms B-36-T1 (manifest
  `phase` field bump) restored manifest+version+compose parity.
- **CLI end-to-end smoke** via `mindsos capacity invoke
  capacity:trace:problem` (Global, session=None per ADR-0080
  carve-out): `success: true`, IRI
  `problem-trace-v1:entry:smoke-1` minted, `WriteResult` returned
  through runtime envelope. Confirms Phase 36 wiring works through
  the full stack: CLI invoke → capacity body → `handle.validate_node`
  (validator chain returns ok) → `handle.write_and_validate` → L1
  `add_node` → WriteResult.
- **consolidate:mm CLI smoke deferred:** Local-write capacity
  needs session-injection machinery not on Phase 36's surface
  (Phase 38 cookbook concern). The capacity body is exercised by
  the unit + integration tests in `tests/phase_36/` directly via
  in-process invoke without a session-CLI verb dependency.

### Ship surface

**Halvim tree (committed at phase-36 branch):**

- NEW `mindsos_knowledge/validators.py` — 5 validators +
  `ValidationResult` + `_VALIDATORS_BY_ROLE` registry (2 adapters:
  memories + problem-trace).
- EDIT `mindsos_knowledge/exceptions.py` — `SemanticValidationError`
  (carries `.result: ValidationResult`).
- EDIT `mindsos_knowledge/__init__.py` — re-exports
  `SemanticValidationError` + `ValidationResult`; version
  `+phase34` → `+phase36`.
- EDIT `mindsos_knowledge/write_handle.py` — `validate_node` body
  wired via `_VALIDATORS_BY_ROLE`; `validate_xref` STAYS raising
  (per-flow deferred).
- EDIT `mindsos_capacity/builtins/consolidate.py` — body adds
  `handle.validate_node` precondition + `SemanticValidationError`
  raise before `write_and_validate`.
- EDIT `mindsos_capacity/builtins/trace.py` — same pattern.
- EDIT `tests/phase_33/test_kl_writeable.py` — sentinel flipped:
  `validate_node` now returns `ValidationResult`; `validate_xref`
  raise sentinel stays.
- NEW `tests/phase_36/` — 3 test files (`test_validators.py`,
  `test_capacity_preconditions.py`,
  `test_adr_amendment_sentinels.py`) + `__init__.py`. Sentinel
  chain extends `14a→15a→15b→35→36`.
- EDIT `confirmation_docs/PHASE_MAP.md` §36 — §inline-amendment
  block (1 clause covering features-line scope wording +
  Tests-line "both via write_and_validate" wording).
- EDIT `docs/dev/review-checklist.md` — item 1 split
  (`validate_node` wired; `validate_xref` deferred) + new section 4
  "Capacity preconditions call semantic validators (ADR-0139)".
- VERSION BUMP **11** sites (B-36-T1 added `mindsos_cli/manifest.toml`
  `phase` field to the 10-site list): pyproject.toml +
  docker-compose.yml (prod+test) + manifest.toml (`phase` +
  `version`) + 8 package `__init__.py` literals.

**Parent tree (filesystem-only, Model C; no commit):**

- EDIT `docs/decisions/adr/0139-hybrid-invariant-home.md` —
  Status Proposed → Accepted; §amendment-1 (3 clauses) appended;
  §Impl Phase 36 footer appended. Original §Implementation refs
  section untouched (Phase 35 §am-1 precedent).
- EDIT `docs/decisions/adr/0143-kl-write-handle-pattern.md` —
  §Impl Phase 36 footer appended documenting `validate_node` wired
  + `validate_xref` defers.
- EDIT `docs/dev/internals/knowledge.md` — "Validator surface"
  section appended per ADR-0139 §Accept(c).

### Hotfixes (B-36-T1/T2/T3)

3 hotfix classes during ship; all caught by container test run:

- **B-36-T1 — manifest `phase` field missed in version bump.**
  10-site bump covered `version = "0.0.0+phase34"` everywhere but
  `manifest.toml` also has a separate `phase = "34"` field that
  doctor parity-checks. Cascade: 10 doctor tests failed across
  phase_00/01/07/08/09/11/12 from manifest+version divergence.
  Fix: bump `phase = "34"` → `phase = "36"`. Memory note added:
  **the version-bump site list is now 11, not 10.** Future phases:
  step-0 probe must grep both `phase = "<NN>"` AND `+phase<NN>`
  literals.

- **B-36-T2 — export-slate literal-decay class extension.**
  3 hardcoded `+phase34` literals in
  `tests/phase_30/31/34/test_phase_NN_export_slate.py`. Forward-
  anchor sentinels per
  `[[feedback-export-slate-sentinel-audit]]`. Step-0 probe missed
  this — only grepped `WriteHandleNotWiredError|validate_node`,
  not version literals. Memory note: step-0 probe should also
  include version-literal grep at code-shipping phases that bump
  the version string.

- **B-36-T3 — PHASE_MAP §36 sentinel "capacity bodies" line-wrap.**
  My `§inline-amendment` text line-wrapped "capacity" + "bodies"
  across a newline; sentinel substring `"capacity bodies"` didn't
  match. Fix: unwrap onto a single line. Memory note:
  PHASE_MAP-substring sentinels are line-wrap-fragile; future
  sentinels should use shorter unique anchors that don't span line
  wraps.

### Carry-forwards to Phase 38 (37 RETIRED)

1. `handle.validate_xref` body still deferred; wires alongside
   first XRef-writing L3 capacity (per ADR-0139 §amendment-1
   clause 3).
2. The 4 unconsumed validators (`validate_local_to_global_ref`,
   `validate_alignment_role_naming`, `validate_ref_type`,
   `validate_promotion_candidate`) await per-flow consumer
   capacities. Pure-function tests cover them; no integration
   coverage until a capacity wires them.
3. ADR-0146 §amendment-1 clause 1 (raise vs return PTR) remains
   open. `SemanticValidationError.result` is the carry-forward
   hook for the eventual L4-driven flip — a future PTR-returning
   capacity body builds a `ProblemTraceRecord` from `exc.result`
   without re-running the validator.
4. ADR-0147 §amendment-1 clause 3 (per-flow strict for L3 write
   capacities) remains binding. Phase 36's `_VALIDATORS_BY_ROLE`
   adapter per-flow extension (ADR-0139 §amendment-1 clause 3) is
   the L2 substrate parallel.
5. Local-write CLI smoke needs session-injection verb. Phase 38
   cookbook flows surface the user-facing shape; if the cookbook
   needs Local-write smoke through CLI, a session-establishment
   verb lands as part of Phase 38 ship.

### Process notes

- **Phase 35 ship completed mid-chat** — Phase 35 squash-merged at
  sha `36d9125` (PR #45). Date-placeholder fill commit at
  `0cb216e`. Phase 36 branched off main at `0cb216e`. Mid-chat
  context-switch to handle Phase 35 mechanics was clean — the
  branch-off-prior-squash discipline holds.
- **R5 saturation gate fired clean.** R4 probes returned
  actionable confirmations; R5 produced 5 impl-locks (R5-PB-A
  through E) — all anticipated by earlier rounds, zero design
  reversals. Pattern matches Phase 35 §9 saturation signature.
- **PHASE_MAP §36 §inline-amendment under R3-PB-F is the third
  consecutive features-line wording correction** (Phase 34, 35, 36
  all amended). The pattern from Phase 35 §9 stands:
  features-line wording in PHASE_MAP is **not** authoritative once
  shipped reality diverges — ADR §Implementation footers + notes
  carry the load.
- **Two-machine workflow** (`[[user-two-machine-setup]]`):
  Mac for file edits + git; Linux for docker test runs. Hotfix
  iteration required Mac-push → Linux-pull → Linux-rebuild
  (`--no-cache`) → Linux-retest. Per
  `[[feedback-dockerfile-test-stage-file-reads]]`: test image must
  be rebuilt with `--no-cache` after pull for the new code to
  reach the container.
