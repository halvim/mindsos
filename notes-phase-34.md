# Phase 34 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

L3 Symmetric Write Contract — KLWriteHandle bodies wired (ADR-0146 §am-1 clauses 4+5 closed; ADR-0143 flipped Accepted)

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

### Background

Phase 34 wires what Phase 33 stubbed. ADR-0146 §amendment-1 clauses 4 + 5
close (outputs=() navigation via runtime.invoke bypass; L2 handle bodies
graph()/mint_iri()/write_and_validate). Clauses 1 (failure-mode return-PTR),
2 (context routing — already works), 3 (placeholder DataStates — partial
close to mint-key surfacing) stay open per R0 PB-1 minimum-viable.
ADR-0143 flips Proposed → Accepted (all 3 §Accept criteria satisfied
including review-checklist.md ship). ADR-0147 stays Proposed (Phase 35
flip target). ADR-0139 untouched (Phase 36).

### Design saturation

5 design rounds (R0 + 4 re-litigations) + R4 (16 probes) + R5 (impl-start
gate). ~52 picks across rounds + ~13 §am-impl reconciliations at R4 + R5.
1 reverse pivot (R3 PB-A reversed at R4 §am-impl-2 — `ShapeDescriptor.record`
exists in datastate.py:69).

Key revisions:
- R0 PB-1: minimum-viable close (clauses 4 + 5 only); §amendment-1 clause 1
  text already documents deferral, so no §amendment-2 needed for that.
- R1 PB-A: bypass in runtime.invoke (not call_capacity); zero blast radius
  on Phase 27-shipped primitive.
- R1 PB-G: §amendment-2 narrowed to OCC defer + clause-3 partial close only.
- R2 PB-A: input-shape tighten REQUIRED (collision with mint_iri kwarg
  surface); minimum-required record-shape (memory_id/trace_id + value).
- R2 PB-B: write_and_validate does NOT catch L1 raises (clause 1 stays
  fully open; method honest about Phase 34 scope).
- R4 §am-impl-1: Graph.add_node takes `type_name` not `type_`; handle's
  type_ kwarg translates at the L1 boundary.
- R4 §am-impl-3: NodeType locks "Memory" + "ProblemTraceEntry" (Phase 13
  schema names; not ADR §Skeleton's "ConsolidatedMemory").

### Ship surface

Source NEW (0): no new source files.

Source EDITED (10):
- mindsos_capacity/capacity.py — +InvocationResult.write_outcome field.
- mindsos_capacity/runtime.py — invoke() bypass branch + lazy WriteResult
  import (avoid runtime ↔ write_outcome cycle per B-34-T1).
- mindsos_capacity/capacity_layer.py — +kl=None __init__ kwarg
  (Optional[Any] per B-34-T3) + conditional ctx.setdefault("kl") at
  invoke + start_resident (4 sites total — symmetric with Phase 33's
  session injection).
- mindsos_capacity/builtins/consolidate.py — body rewrite + record
  DataState shape.
- mindsos_capacity/builtins/trace.py — body rewrite + record DataState
  shape.
- mindsos_cli/commands/capacity.py — _construct_invoke_layer KL +
  install writes; _write_outcome_to_dict helper; render in _to_dict +
  _to_human.
- mindsos_knowledge/identifiers.py — _IRI_BUILDERS 2-entry registry +
  _mint_memory + _mint_problem_trace wrappers.
- mindsos_knowledge/knowledge_layer.py — writeable(..., *, version="v1")
  keyword.
- mindsos_knowledge/write_handle.py — _version: str field at end of
  frozen dataclass + wired bodies for graph()/mint_iri()/write_and_validate.
- Dockerfile — B-34-T2 COPY docs ./docs in test stage.

Tests NEW (tests/phase_34/, 12 files / 42 cases):
_fixtures.py + __init__.py + test_write_handle_graph_body.py (4) +
test_write_handle_mint_iri.py (7) + test_write_and_validate.py (5) +
test_writeable_version_kwarg.py (3) + test_capacitylayer_kl_injection.py
(4) + test_runtime_invoke_bypass.py (5) +
test_invocation_result_write_outcome_field.py (4) +
test_cli_invoke_write_capacities.py (3) + test_review_checklist_file.py
(3) + test_phase_34_export_slate.py (4).

Phase 33 tests REPURPOSED (R4 §am-impl-5; 5 + 2 shape sentinels):
test_consolidate_mm_capacity.py x3 (shape opaque→record + 2 success
path repurpose); test_trace_problem_capacity.py x4 (shape opaque→record
+ 3 success path repurpose); test_kl_writeable.py x2 (handle.graph()
+ mint_iri() WHN raises → return real values).

STAYS: cap-denial test (R0 PB-6), scope=local+session=None ValueError
test, validate_node/validate_xref WHN raise tests (Phase 36 wires).

Pre-emptive sentinel-flips at impl-start (4 files):
- 3 export-slate count files: function rename
  test_phase_33_export_count_is_110 → test_phase_34_export_count_is_110
  (count literal 110 unchanged; Phase 34 adds zero new exports).
- 1 version literal flip across tests/phase_30/ + tests/phase_31/ +
  test_version_bumped_to_phase_33 → _to_phase_34 + "0.0.0+phase33" →
  "0.0.0+phase34".

Version bump: 12 sites in 10 files (7 init.py + pyproject.toml +
manifest.toml [phase + version] + docker-compose.yml [2 image tags]).

### ADR amendments (parent tree per Model C)

3 ADR touches in /Layered Intelligence/docs/decisions/adr/:
- ADR-0146 §amendment-2 (R1 PB-G) — narrow 2-clause Phase 34 amendment
  (OCC retry defer + §am-1 clause 3 partial close — mint-key surfacing
  only). + §Implementation Phase 34 footer documenting clauses 4 + 5
  closure mechanism. Status STAYS Accepted.
- ADR-0143 Status FLIPPED Proposed → Accepted + §Implementation
  (Phase 34 — Accepted) footer. All 3 §Accept criteria satisfied.
- ADR-0147 §Implementation (Phase 34 — partial) footer documents the
  2-entry registry per-flow discipline. Status STAYS Proposed
  per R0 PB-9 (Phase 35 is the canonical flip target per PHASE_MAP).

### Hotfix ledger

3 hotfixes fired (within budget of 5):

- B-34-T1 (circular import): runtime.py top-level imported WriteResult
  from write_outcome.py, but write_outcome.py imports ProblemTraceRecord
  from runtime.py — cycle. Fix: moved WriteResult import inside the
  bypass branch body. **New class:** L2 ↔ L3 cross-module write-side
  imports need careful placement when both sides reference each other.
- B-34-T2 (docs/ not COPYed into test image): Phase 34's
  test_review_checklist_file.py reads /app/docs/dev/review-checklist.md
  at runtime; test image's COPY directives didn't include docs/. Fix:
  added `COPY docs ./docs` to Dockerfile test stage. **Class extension:**
  when a phase adds a test that asserts a docs/ file's presence,
  audit Dockerfile test stage COPYs.
- B-34-T3 (TYPE_CHECKING import still tripped Phase 28 AST walk):
  Phase 28 test_import_isolation_phase_28.py AST-walks every
  mindsos_capacity/*.py and forbids ANY top-level import of
  mindsos_knowledge — including `if TYPE_CHECKING: from
  mindsos_knowledge import KnowledgeLayer`. Fix: dropped the
  TYPE_CHECKING block; annotated `kl: Optional[Any]` instead. **Lesson:**
  AST-based layer-isolation tests forbid SOURCE-TEXT imports, not just
  RUNTIME imports.

### Test counts

- Docker (Linux, prod image): **3340 passed, 49 skipped, 109 warnings**
  in 1896.03s (0:31:36). Phase 34 isolated: 42 passed.
  Skip delta from Phase 33 baseline: 0 (no new ADR-amendment sentinels
  at Model C runtime parity — parent ADR dir not COPYed into runtime
  image, so the §am-2 footer doesn't add new skip cases).
- Sandbox (Python 3.10): tests/phase_34/ → 42 passed in 0.16s. Full
  cumulative blocked by mindsos_server.admin's datetime.UTC (Python 3.11+);
  runs on Linux Docker (Python 3.12).

### Smoke tests on prod image

1. doctor --self-test --json — all 7 packages at 0.0.0+phase34;
   expected_compose_image_phase: "34"; ok: true, failures: [].
2. CLI invoke capacity:trace:problem (--json) — success=true,
   write_outcome.iri="problem-trace-v1:entry:smoke-1", role="problem-trace",
   scope="global". Confirms ADR-0080 bootstrap carve-out + CLI render.
3. CLI invoke capacity:consolidate:mm without --session-token — success=false,
   error.type="ValueError" ("requires a session"). Confirms R2 PB-C
   limitation documented + envelope semantics.
4. CLI invoke capacity:trace:problem (--human) — stdout contains
   "write_outcome.iri='problem-trace-v1:entry:smoke-h'". Confirms R1 PB-E
   human render.
5. In-process KL.bootstrap() + writeable(scope='local') +
   write_and_validate — out.iri matches expected mint; node present
   in handle.graph(); node value + type match input. Confirms KL state
   actually mutates (handle's _metagraph shares object with KL._locals).
6. In-process CapacityLayer() without kl= + invoke write capacity —
   success=False, error=RuntimeError ("kl=<KnowledgeLayer>"). Confirms
   R3 PB-F missing-KL programmer-error surface.

### Carry-forwards to Phase 35+

Phase 30/31/33 carry-forwards still open (unchanged):
--session-token CLI flag, Falkor-backed L3 bootstrap, L3 state-file
serialization, per-user ProblemTraceSink, --install-builtins CLI flag,
additional text-family capacities, pathfinding registered-builtin form,
L4 resident scheduler, PROMOTED breadcrumb reader (phase that ships
capacity:promote:pipeline).

Phase 34 new carry-forwards:
1. validate_node() + validate_xref() body wiring — Phase 36 (ADR-0139);
   still raise WriteHandleNotWiredError.
2. ADR-0146 §amendment-1 clauses 1, 2, 3 stay open. Clause 1 (failure
   modes return PTR vs raise) is load-bearing — L4 consumer drives.
3. ADR-0146 §amendment-2 clause 1 OCC retry — defer until L1 grows OCC
   contract.
4. WriteResult.extras["retry_count"] key reserved by convention.
5. --session-token for CLI Local writes — without it, CLI
   capacity:consolidate:mm fails (scope='local' + session=None →
   ValueError). Phase 34 ships negative-path test.
6. _IRI_BUILDERS registry entries for the 4 deferred write capacities —
   added per-flow when each capacity's L4 flow closes design.

### Observed quirks / process notes

- B-34-T1 NEW HOTFIX CLASS: L2 ↔ L3 cross-module write-side import
  cycle. write_handle.py (L2) imports WriteResult from
  mindsos_capacity.write_outcome (L3); write_outcome.py imports
  ProblemTraceRecord from runtime.py; runtime.py needed WriteResult for
  the bypass-branch isinstance check. Fix: lazy-import inside the
  function body. Future write-side surface additions should be checked
  for this cycle shape.
- B-34-T2 class extension: test image Dockerfile COPY audit when a
  phase adds a test that reads docs/ files.
- B-34-T3 lesson: AST-based layer-isolation tests cannot distinguish
  TYPE_CHECKING-guarded imports from runtime imports — they forbid the
  SOURCE TEXT of the import statement. Use Optional[Any] or a Protocol
  defined locally instead.
- R4 §am-impl-2 reverse pivot: R3 PB-A's "stay opaque +
  docstring tighten" was a guess that ShapeDescriptor.record didn't
  exist. R4 probe found it at datastate.py:69; pick reversed cleanly
  to use `record({...}, opaque_tag=...)` preserving the opaque_tag for
  Phase 33 sentinel backward-compat.
- Phase 33 forward-anchor tests REPURPOSE pattern: 5 tests across 2
  files + 2 shape.kind sentinels. The tests' BODY changed (assertions
  flipped from raise → success path with WriteResult) but test function
  NAMES were updated where the old name lied about behavior. Pattern
  applicable any time a stub-phase test forward-anchors a wiring-phase.
- L2 imports L3 (WriteResult + WriteHandleNotWiredError in
  write_handle.py): inherited Phase 33 precedent. ADR-0010 amendment
  deferred per R5 PB-A. Phase 14 isolation test forbids only
  mindsos_cli + mindsos_server for KL — mindsos_capacity is not in the
  forbidden roots list, so L2→L3 stays unflagged.

### Memory edit at ship

Write [[project-mindsos-phase-34]] index entry per Phase 33 precedent.
Highlights: 3340/49 cumulative docker; squash sha + phase-34-confirmed
tag placement; 3 hotfixes B-34-T1/T2/T3 (all new classes); R3 PB-A
reverse pivot at R4 §am-impl-2; ADR-0146 §am-2 + §Impl footer; ADR-0143
flipped Accepted; ADR-0147 §Impl footer (stays Proposed); bypass-in-
runtime-invoke design pattern (R1 PB-A) as template for future write
capacities; clauses 1+2+3 of §am-1 stay open for L4-driven flip.
