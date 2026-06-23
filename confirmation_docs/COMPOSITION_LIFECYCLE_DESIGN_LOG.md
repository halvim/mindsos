# Composition Lifecycle — core-mod DESIGN LOG

**Status:** Design LOCKED 2026-06-21. This is a **general, project-independent core modification**,
scoped to **what the ARC chat requested** (its §5 four-part CORE PROPOSAL) **+ the bongard
composite-persistence residual**. Justified by a **real correctness defect** ARC surfaced
(`find_pipeline` is unsound for multi-input capacities — verified) plus ARC's **documented
resolution semantics** (three worked input-group cases). WSD/FOL/DWF/bongard are subsystems that
consume these core mechanisms, not owners.
**Branch (to open):** `feat/composition-lifecycle` off `main` (NOT a numbered phase).
**Base:** `main` @ `7d8584e` · core_version `phase50` · STATE.json last_shipped 50.
**Scope (core chat):** `mindsos_*`, `tests/`, `docs/`. WSD-independent.

---

## 0. Governing principle — subsystems consume, core owns

WSD/FOL/DWF/bongard are subsystems; general mechanisms (finder, DAG type, composite persistence,
promotion) live in **core**, owned by no subsystem; no core work is gated on an undesigned
subsystem. Promotion (when built) lands in core; WSD Phase 55 = *register a producer*, not *own
the loop*. This dissolves the WSD-decoupling thesis (D1/D3/D5) at the architecture level.

---

## 1. The driving defect (why this is core, not a feature request)

ARC's live probe + my code read confirm: `find_pipeline`'s BFS (`mindsos_capacity/pipeline.py`)
builds a step from **one** reachable input (`via_datastate`) and **never checks the capacity's
other declared inputs**. For any multi-input capacity it fires unsoundly (fires on one input,
drops the rest; folds taken as singletons). The defect is latent today (no production caller — I
verified), so the first real multi-input-composition consumer hits it. ARC won't route its reason
layer through the finder (provenance-only) — so this is **enablement for the multi-input case**,
durably justified by the defect + ARC's documented semantics, not by a runtime pin.

---

## 2. BOUNDARY LOCK (Decision 1 — split-layer)

| Concern | Layer |
|---|---|
| `Finder` interface + each algorithm (BFS, conjunction) | **L3** (`find_pipeline` lives here; algorithm = computation = L3) |
| *Which* strategy fires (selection/policy) | **L4** (ADR-0071: "abstraction is L4's to own") |
| DAG result type | **L3** (shared currency) |
| Composite persistence (Local descriptor) | **L2** (F9 model) |
| Composite promotion | **core, DEFERRED** (placement principle §0) |

No L4 "real finder" exists to defer to (`plan_construction.py` is a v0 stub). Conjunction is
net-new, an L3 strategy driven by L4. Requires an **ADR-0071 amendment**.

---

## 3. THE PLAN — one slice (ARC's 4 parts + persistence residual)

**Decision 7 USER-CONFIRMED (supersedes the Decision 3/6 deferrals):** build what ARC asked,
validated against ARC's documented cases.

**Slice 1 (one feat branch, gate-green):**

1. **Finder seam (ARC Part 1)** — L3 `Finder` interface + L4 selection (ADR-0071 §am). BFS becomes
   one strategy; the conjunction finder is the second (two real strategies — seam not premature).
2. **Conjunction/fold finder (ARC Part 2)** — hyperpath search whose resolution is **per
   input-group** `{all_required (AND) | any_of (optional-union) | fold (aggregate)}` **× OR over
   producers** (PB-B fix — NOT "AND over inputs"; pure-AND would mis-compose `any_of`/`fold`).
   Part 2 and Part 3 are **one coupled design** (the finder's resolution *is* the typed-group
   interpretation). Returns a DAG. **Validated for structural conformance** (PB-A) against ARC's
   three documented cases — `all_required` (`touching_delta`/`selector`), `any_of`
   (`build_correspondence`), `fold` (`reconcile_background`), §4 pt 5 + GF-3 of
   `PIPELINE_DECISIONS.md`. Conformance = the finder produces the DAG *shape* ARC documented; ARC
   won't *execute* those DAGs (provenance-only), so this is structural, not behavioral.
3. **Typed input-group `{all_required|any_of|fold}` (ARC Part 3) — declaration-field now, graph
   hyperedge deferred (Decision 8).** Verified: `register_capacity` emits **only binary**
   `PRODUCES`/`CONSUMES` edges; `views.py` has **no hyperedge walk**; the `IntergraphHyperEdge`
   primitive is instance-layer, not type-layer. So ARC's literal "hyperedge" would need new
   type-layer emission + a hyperedge view walk + finder graph-integration — with **no
   graph-walking consumer**. Instead: the typed group is a **field on `_CapacityBase`** (ADR-0159);
   the finder reads it from the **declaration registry** (mirrors `views.inputs_of`'s
   "declaration primary"). The graph hyperedge (ADR-0156 §am) defers until a graph-walking
   consumer lands. NOT blanket "all required."
4. **DAG result type (ARC Part 4)** — **replaces** the linear finder `Pipeline` (Decision 2). Now
   has a real producer: the conjunction finder (resolves the earlier PB-1). The BFS strategy's
   result construction also changes to emit a degenerate-linear DAG (PB-F — BFS is not untouched).
   Blast radius §5: finder type has zero production consumers.
5. **Composite persistence residual (bongard CC-1)** — serialize the composite (DAG) into the
   `learned-parameters` descriptor (ADR-0182 value codec) + a reactivation factory + **dep-ordered
   reactivation**. **Placement: `mindsos_server/local_boot.py`** (PB-C — `kahn_sort` lives in
   `mindsos_knowledge`; `mindsos_capacity` may not import it, boundary test-enforced; the server
   holds the descriptor-walk glue and may import both). ~80% F9. Consumer: bongard milestone 2.

**Deferred (each fails the consumer/defect test — kept out deliberately):**
- **Promoted-path-lookup strategy** — `promoted-pipelines` has **no writer** (verified: only a
  docstring + an ALS label reference it). Reads an empty store → defer until a writer (mint or
  promotion) exists. The seam survives on BFS + conjunction finder.
- **Composite `node_kind` (CC-2)** — `node_kind` is a free field; F9 re-mints a learned composite
  fine as `KIND_REACTIVE`. **Nothing dispatches on a composite kind.** A descriptor field at most;
  revisit only if the finder must recognise composites.
- **Promotion loop (CC-3/D2)** — zero writers (ARC none, bongard m5, WSD undesigned). Placement
  principle §0 locked; build into core when a real promoter lands, behind a target-applier seam.

---

## 4. ADR cross-check

- **ADR-0071** rejected a pluggable finder → seam + conjunction finder + DAG-result need an
  **ADR-0071 §am** (interface+algorithm L3, selection L4).
- **ADR-0159 §am** — typed input-group as a `_CapacityBase` field (Decision 8 declaration-field
  form). The **ADR-0156 §am** (type-layer typed hyperedge + view walk) **defers** until a
  graph-walking consumer exists (PB-E).
- **ADR-0150** — none (composites reuse shipped roles).
- Composite-kind 0159 §am — **deferred with CC-2**.

---

## 5. Replace blast-radius (Decision 2)

Finder `Pipeline` (`mindsos_capacity/pipeline.py`) has **zero production consumers**.

| Surface | Coupling | Effort |
|---|---|---|
| `pipeline.py` | defines type + BFS | the rewrite |
| `__init__`/`builtins/__init__`/`exceptions` | export + docstrings | mechanical |
| L4 `plan_construction`/`execution`/`orchestrator` | none (imports `planning_v0`) | zero |
| L5 `chain_artifacts.py` `Pipeline` | none — independent dataclass | zero |
| L2 `promoted_pipelines.py` | promotion-persistence; deferred with the loop | untouched |
| tests (13 files) | ~4 export-slate, ~7 BFS, 2 integration, 1 bipartite | update ~9 |

---

## 6. Per-item disposition

| Item | Disposition |
|---|---|
| **Finder seam (P1)** | BUILD. Strategies: BFS + conjunction finder. ADR-0071 §am. |
| **Conjunction finder (P2)** | BUILD, validated against ARC's 3 documented cases. |
| **Typed input-group (P3)** | BUILD as a `_CapacityBase` field (Decision 8); finder reads declaration. Graph hyperedge (0156 §am) DEFERRED — no graph-walking consumer (PB-E). |
| **DAG type (P4)** | BUILD, REPLACE `Pipeline`. Producer = conjunction finder. |
| **CC-1 persistence residual** | BUILD: serialize composite → descriptor + factory + `kahn_sort` dep-ordering. |
| **Promoted-path strategy** | DEFER — empty store, no writer (verified). |
| **CC-2 composite kind** | DEFER — nothing dispatches; `KIND_REACTIVE` suffices (verified). |
| **CC-3 / D2 promotion** | DEFER — placement principle §0; core-owned, WSD = producer. |
| **CC-4** | Bongard project item; out of scope (consumes the mechanisms). |
| **D1 / D3 / D5 (WSD-decoupling)** | Endorsed at the architecture level by §0. |

---

## 7. Next steps

1. **Open `feat/composition-lifecycle`** off `main` @ `7d8584e`. One gate-green PR.
2. Write **ADR-0071 §amendment-2** (seam + conjunction + DAG-result) + **ADR-0159 §amendment-1**
   (typed input-group declaration field). ADR-0156 §am (graph hyperedge) deferred. — **DONE.**
3. Record the promotion placement principle (§0) + an informational WSD note (Phase 55 = producer,
   not owner).
4. Build order: seam + DAG-replace → conjunction finder + typed hyperedge (validate vs ARC's 3
   cases) → composite persistence residual + dep-ordering.

---

## 8. Log

- **2026-06-21** — **Slice 1 GATE GREEN (Linux, live FalkorDB):** `3991 passed / 11 skipped /
  1 xpassed / 0 failed` in 1918s (`docker compose -p mindsos-core --profile test run --rm
  mindsos-test pytest`). Net +27 over the `main@7d8584e` baseline (the F9 "3988" was measured on
  a tree that included the D'1-roundtrip test commit not on `7d8584e`; +27 = the new
  `tests/composition_lifecycle/` suite — 22 capacity-only + 5 server-half). The sandbox-unrunnable
  half (server dep-order + F9 Falkor round-trips + phase_32/49 integration) all green. Branch tip
  for Slice 1 feature commit = `3253ce8`; ready to squash-merge to `main`.
- **2026-06-21** — **Slice 1 IMPLEMENTED on `feat/composition-lifecycle`** (build order
  per §3/§7.4). Production: `mindsos_capacity/pipeline.py` rewritten — `PipelineDAG` +
  `DAGStep` + `DAGEdge` (+ `START` sentinel, `to_dict`/`from_dict`) replace linear
  `Pipeline`/`PipelineStep`; `Finder` ABC + `BFSFinder` (degenerate-linear, PB-F) +
  `ConjunctionFinder`; `find_pipeline` kept as the BFS back-compat free fn (singular
  `start_datastate=` → integration tests phase_32/49 unchanged). `input_group` field on
  `_CapacityBase` + `INPUT_GROUP_*`/`INPUT_GROUPS` vocab (identifiers.py) +
  `register_capacity` value check. Composite persistence: `COMPOSITE_DAG` key +
  `composite_dependencies` (reactivation.py); dep-ordered re-activation
  `_dep_order_descriptors` via `kahn_sort` in `mindsos_server/local_boot.py` (PB-C — no
  `mindsos_knowledge` import added to `mindsos_capacity`; verified). Exports 128→**139**
  (+11 net: −2 retired, +7 finder/DAG, +2 composite, +4 input-group); count sentinels
  flipped in phase_29/30/31/33/34 slates; phase_30 dataclass + phase_42 isinstance tests
  rewritten to `PipelineDAG`. New tests under `tests/composition_lifecycle/` (mirrors
  `tests/f9/`): conjunction conformance (all_required/any_of/fold + diamond + start-root +
  not-found), finder seam, input-group field/validation, composite persistence, dep-order.
  **Impl-time decisions (within scope, no design reversal):**
  - **CI-1 (DAG shape):** explicit `DAGEdge(producer,consumer,datastate)` list over
    implicit datastate-keyed wiring — required because `fold` fans the *same* datastate IRI
    in from N producers, which implicit one-producer-per-datastate wiring cannot express.
  - **CI-2 (ConjunctionFinder soundness):** two-phase — a pure `_satisfiable`/`_reachable`
    pass then a `_fire` construction pass — so a producer subtree that fails deep never
    leaks partial steps. OR-over-producers selects the deterministic first (sorted by IRI);
    **no backtracking on a deep failure at v1** (ARC's three cases are unambiguous; `any_of`
    naturally tolerates an unproducible input by skipping it). Backtracking deferred.
  - **CI-3 (Decision 8 honoured):** `input_group` is NOT emitted to `to_properties` — stays
    on the declaration; finder reads the registry. Test-locked.
  - **CI-4 (gate split):** the Cowork build host is Python 3.10; `mindsos_server`
    (needs 3.11 `datetime.UTC`) + Falkor integration can't run there. Validated in-sandbox:
    73 finder/DAG/input-group/export-slate + 25 phase_45 + 6 F9-reactivation-contract pass.
    Server-half (`test_dep_ordered_reactivation`), F9 Falkor round-trips, and phase_32/49
    integration gate on Linux (RULES §4). F9 reorder is a no-op for ≤1-composite batches,
    so existing F9 tests are unaffected (verified).
- **2026-06-21** — **Reanalysis pass (PB-A..F, grounded) + Decision 8.** PB-E (verified):
  `register_capacity` emits only binary edges, `views.py` has no hyperedge walk, the hyperedge
  primitive is instance-layer — so Part 3's "tag a hyperedge" was undersized. **Decision 8
  USER-CONFIRMED:** Part 3 ships as a `_CapacityBase` declaration-field now (finder reads the
  declaration registry); the type-layer hyperedge (ADR-0156 §am) defers until a graph-walking
  consumer. PB-C (verified): `kahn_sort` is in `mindsos_knowledge`, `mindsos_capacity` can't import
  it (boundary) → dep-ordering placed in `mindsos_server/local_boot.py`. PB-B: finder resolution is
  per-typed-group `{AND|any|fold}`×OR-producers, not "AND over inputs" (Part 2 ≡ Part 3). PB-A:
  ARC validation is structural conformance, not behavioral. PB-F: BFS result construction changes
  to the DAG type. None reverse Decision 7 — all corrections within scope.
- **2026-06-21** — **Decision 7 USER-CONFIRMED — scope = ARC's §5 four parts + composite
  persistence residual** (supersedes the Decision 3/6 Part-2/3 deferrals). Trigger: ARC *requested*
  these and **documented the resolution semantics** (3 input-group cases) — my Decision-6 "semantics
  unvalidatable" pushback was too strong (conflated "ARC won't runtime-route" with "semantics
  unknown"). Durable justification = the verified `find_pipeline` multi-input unsoundness (§1).
  Un-deferring Part 2 **resolves PB-1** (DAG type now has a producer). Still deferred: promoted-path
  (empty store, PB-2 holds), composite-kind (nothing dispatches, PB-4 holds), promotion (no writer).
- **2026-06-21** — **Reanalysis pass (PB-1..4, grounded):** PB-1 DAG-replace had no producer once
  Part 2 deferred; PB-2 `promoted-pipelines` has no writer (verified); PB-3 seam premature on one
  strategy; PB-4 composite-kind unnecessary (`node_kind` free, F9 re-mints as `KIND_REACTIVE`).
  These drove the Decision-7 re-scope (build Part 2 → fixes PB-1; keep PB-2/PB-4 deferrals).
- **2026-06-21** — **Decision 4 REVISED:** DROP the promotion loop; lock placement principle (§0).
  Dropping it also drops the `promoted_pipelines` schema change + WSD sign-off → slice is
  WSD-independent.
- **2026-06-21** — **Governing principle (§0):** subsystems consume, core owns. Bongard files
  confirmed **not a dependency** — design derives from `mindsos_*` + ARC.
- **2026-06-21** — **Decision 5 USER-CONFIRMED:** composite persistence = F9 residual + dep-ordered
  reactivation (`kahn_sort`).
- **2026-06-21** — **Decision 2 USER-CONFIRMED:** REPLACE the finder `Pipeline` with the DAG type
  (blast radius measured §5; zero production consumers).
- **2026-06-21** — **Decision 1 USER-CONFIRMED:** finder seam = split-layer (L3 interface +
  algorithms; L4 selection). ADR-0071 amendment required.

---

## 9. Slice 2 — SCOPED 2026-06-21 (design pending; own chat)

Two items Slice 1 deliberately left out, surfaced by ARC's D3 one-specimen spike
(`projects/arc_demo/.../arc1/PIPELINE_DECISIONS.md` §5 pt 5–6 + §4 D3 log 2026-06-21). ARC
documents the semantics but ships **provenance-only** — it does not execute through these.
**Base:** `feat/composition-lifecycle-s2` off `feat/composition-lifecycle` (or the merged tag
if Slice 1 has landed). **Reopens:** ADR-0156 (binary edges / typed hyperedge), ADR-0159
(input_group / registration), ADR-0071 §am (finder threading), ADR-0072 / ADR-0146 (invoke +
write-gate).

**Part 6 — invoke INPUT contract (correctness; standalone, no consumer needed).**
`call_capacity` (`mindsos_capacity/capacity.py` ~263) + `runtime.invoke` (`runtime.py` ~157)
validate **outputs only**; inputs are splatted as `**kwargs` with no check against the declared
`CONSUMES`. Verified by the D3 spike: `touching_delta` declares `(touching, correspondence)`
but its body reads `(pair, background)` and still runs. So a body's real dependencies can
silently diverge from the declared topology that every finder (incl. the new ConjunctionFinder)
trusts. **Ask:** whether/how invoke validates inputs against declared `CONSUMES`, respecting
`input_group` (all_required ⇒ all present; any_of ⇒ ≥1; fold ⇒ the folded set). Options: strict
raise / warn-log / dev-mode assertion / separate lint.
**Strongest concern (flag for that chat):** blast radius. Strict-raise will break any shipped
body whose kwargs ≠ declared `CONSUMES` (the spike proves at least one such body exists). A
shipped-capacity audit is a prerequisite to picking strict vs warn — strict is not free.

**Part 5 — DataState operand-arity / role axis (enablement; consumer-gated; heavier).**
The invoke inputs map is keyed by DataState IRI and `register_capacity` emits one binary
`CONSUMES` per *distinct* input DataState (ADR-0156). A capability consuming **two operands of
the same DataState type** cannot express both — they collide on one key/edge; the operand axis is
invisible. Hits every comparator (`same_object`/`same_shape`/`moved`/`touching`; ARC's
`touching_delta` needs in- vs out-touching). **Ask:** an operand-position/role/arity notion on the
registration contract (ADR-0156/0159) **and** the invoke inputs contract, threaded through the
ConjunctionFinder (operands carried by role, not collapsed) and interacting with `input_group`.
**Concern:** this reopens the ADR-0156 binary-edge model *and* the invoke inputs-map keying —
deeper than all of Slice 1. **No scaffolding without a consumer:** ARC does not pin it; confirm a
real executing consumer (bongard / WSD / an L4 path) before sizing, or land a contract-only form
with one test consumer.

**Sequencing pick (recommended): split — do Part 6 first.** Part 6 is cheap, a standing
correctness fix, and defensible with no consumer; Part 5 is consumer-gated and a bigger redesign.
Bundling lets Part 5's open consumer question stall the Part-6 fix. Track as one Slice-2 design
chat, but ship Part 6 as the next increment and gate Part 5 behind a confirmed consumer.

---

## 10. Pre-Slice-2 fix (commit "a") — `PipelineDAG`→`Pipeline` rename + CLI repair

**Defect found during Slice-2 reanalysis (2026-06-22).** Slice 1's §5 blast-radius table has **no
`mindsos_cli` row** — it missed a consumer. `mindsos_cli/commands/capacity.py` unconditionally
imports `Pipeline` from `mindsos_capacity` (removed by Slice 1; only `PipelineDAG` exported) and its
`_pipeline_to_dict`/`_pipeline_to_human` read the **retired linear shape** (`.start_datastate`
singular, `step.via_datastate`). So `import mindsos_cli.app` raises `ImportError` on the merged
main tip — i.e. the CLI is broken on main. **This contradicts STATE.recent's "3991 passed / 0
failed" green gate → reconcile on Linux** (does the gate actually collect `mindsos_cli.app`-importing
tests? If yes, the recorded result is suspect; if no, those tests aren't gating). Flag, do not assume.

**Decision (USER-CONFIRMED 2026-06-22): rename `PipelineDAG`→`Pipeline`; do NOT keep the "DAG"
suffix.** Clean-slate principle: a type name names the domain concept (the converging plan *is* the
pipeline), not its data structure; "DAG" was a migration-only marker to distinguish from the old
linear `Pipeline` and earns nothing once that type is gone. The supposed collision with the L5
`chain_artifacts.Pipeline` was **verified a non-issue** — no file imports both, neither was ever
aliased; they only meet under qualified imports (the L5 one is really a *provenance record* of a
pipeline, arguably `PipelineRecord`). Rejected: **revert** is the same rename in the other
direction at higher churn; **alias `Pipeline = PipelineDAG`** fixes the import but the CLI still
crashes on `.start_datastate`/`.via_datastate` (the break is structural, not nominal).

**The fix (this commit, standalone, BEFORE Slice 2 Part 6):**
- Token rename `PipelineDAG`→`Pipeline` across `mindsos_capacity/{pipeline.py,__init__.py,
  reactivation.py}` + 9 test files (export slates + dataclass/finder tests). Export **count
  unchanged (139)** — a rename, not an add. Module docstrings describing the old
  `Pipeline`/`PipelineStep` linear shape updated.
- CLI render rewritten for the DAG shape: plural `start_datastates`, explicit dataflow `edges`,
  `via_datastate` dropped. The `Pipeline` import resolves again post-rename (no import-line change).
- **Verification (in-sandbox, Python 3.10):** 151 affected tests green (CLI find, pipeline
  dataclasses, finder seam/conjunction/composite-persistence, phase_29/30/31 export slates, phase_42
  bipartite, phase_45). No remaining consumer of the retired singular shape (grep-clean). Server-half
  (`test_dep_ordered_reactivation`, F9 Falkor), the CLI-importing perception suites (phase_03/04/…),
  and the full cumulative gate run on **Linux** (RULES §4) — the arbiter.

**Sequencing:** ship this as commit "a" (a Slice-1 regression fix, unrelated to the input
contract), then open Slice-2 Part 6 off the fixed tip.

**SHIPPED 2026-06-22** — squash-merged to `main` @ `1f09228` (branch `fix/pipeline-rename-cli`
deleted). **Linux gate (live FalkorDB, `--build` fresh image): 4019 passed / 11 skipped /
1 xpassed / 0 failed / 0 errors.** The **+28 over the Slice-1 "3991"** = the
`mindsos_cli.app`-importing suites (phase_03/04/05a/…) that could not pass while the CLI import
was broken; they now collect and pass — confirming the green-gate reconciliation: Slice-1's
3991 under-counted behind the broken import, it was not hiding failures. **Root-cause of the
mask: the test image bakes source via `COPY` (no volume mount), and the first gate attempt ran
without `--build`, silently reusing a stale image. RULES §4 amended — `--build` is now mandatory.**

---

## 11. Slice 2 Part 6 — invoke INPUT contract (BUILT)

**Decisions (USER-CONFIRMED 2026-06-22).** D1 = **completeness + no-unexpected**. D2 = **enveloped +
tagged `error_kind`**. `all_required` fully checked; `any_of` ⇒ ≥1; **`fold` not enforced at v1**
(its "N values under one IRI key" shape needs Part 5's operand axis). **Part 5 stays deferred** —
the bongard consumer (the named candidate) self-validates *presence* only and dispatches through
core `invoke`, so Part 6 retires that self-check; it does not hit the same-type-operand case, so no
consumer un-defers Part 5. CC-2 / CC-3 are unrelated and remain deferred.

**Implementation.**
- `exceptions.py` — `InputContractError(CapacityRegistrationError)` with `kind` ∈
  {`missing_required`, `unexpected_input`}. Added to `exceptions.__all__` but **NOT** to the
  top-level `mindsos_capacity.__all__` (export count stays 139; consumer-discipline — public export
  deferred until a consumer needs the class; reachable via `mindsos_capacity.exceptions`).
- `capacity.py` — `_validate_inputs(declaration, inputs)` validates the **declaration's** input set
  (declaration-primary, not the dedup-lossy edge view), ignoring `context`; called at the top of
  `call_capacity` (read path + direct callers).
- `runtime.py` — `invoke` also calls `_validate_inputs` in the **write-bypass** branch (the second
  splat site, which never reaches `call_capacity`); the `except` branch tags
  `error_kind="input_contract:<kind>"` for `InputContractError` (else the existing
  `exception:<Type>`).

**Routing.** On the `invoke` path a violation is caught into the ADR-0072 envelope
(`success=False`, `error=InputContractError`) + a tagged problem-trace record. Direct
`call_capacity` callers and the write-bypass (when called outside `invoke`'s try) raise — the
documented L3-invariant asymmetry.

**Consumer proof.** The now-importable CLI: `mindsos capacity invoke … --input-json
'{"datastate:text.WRONG": …}'` returns `success=False` / `error.type=InputContractError` instead of
silently passing `None`.

**Verification (in-sandbox, Python 3.10):** 10 core contract tests pass + 148 across
phase_30/34/45 + composition_lifecycle with validation live — **no regression** (the existing
`exception:RuntimeError` trace tag preserved; the audit's "0 violations across 61 invocations" held
against live enforcement). The CLI typo test + `test_dep_ordered_reactivation` (server-half) gate on
**Linux** (RULES §4, `--build`). `tests/composition_lifecycle/test_invoke_input_contract.py` (11
tests; the CLI import is lazy so the core tests don't drag in the 3.11-only admin/server chain).

**ADR:** ADR-0072 §amendment-2. No version bump (non-phase, no public-surface add — the new error
is unexported).

---

## 12. Next chat + open follow-ups

**Next core-mod chat — bongard requests** (STATE `pending_designs.bongard-core-requests`). The
bongard chat (D-M2 series) is waiting on three things; status after this chat:
- **CC-3 promotion** — a `promote_capacity` / target-applier verb (Mint step 5 / SA-6, Global).
  Still **no writer**; the `mindsos_knowledge` `pending_promotion_iri` / `validate_promotion_candidate`
  are pre-existing schema, not the verb. Build behind a target-applier seam per §0; decide placement
  before sizing. **Deferred — addressed in the next chat.**
- **CC-2 composite `node_kind`** — still deferred (§3/§6: nothing dispatches; `KIND_REACTIVE`
  suffices). Next chat confirms keep-deferred vs build.
- **Part 6 consumption** — shipped here (§11) but bongard pins a core **tag** (`phase-50-confirmed`),
  and Part 6 is untagged on `main`. Bongard retires its D-M2-b presence self-validation only after a
  deliberate **pin bump** to a ref including `2676b9d` (RULES §3).

**Open follow-ups (not blocking, worth doing):**
1. **CLI not in the gate's collection.** The Slice-1 `mindsos_cli` break hid because the Linux gate
   never collected the `mindsos_cli.app`-importing suites (the +28 only appeared once Part-6's fix
   un-broke the import). Add the CLI suites to the gate collection so a CLI break can't hide again.
2. **Cut a core tag at the Part-6 commit** (`2676b9d` / `31d2baf`) so demos (bongard) can pin a
   convention-clean tag instead of a bare sha. These non-phase feats (Slice 1, F9, rename, Part 6)
   have all landed untagged on `main`.

---

## 13. Bongard core requests — CC-3 / CC-2 / Part-6 pin (core-mod chat 2026-06-23)

Three asks from the bongard chat (D-M2 series). Reanalysis converged after 4 skeptical passes
(stable on passes 3–4); the only movement was a CC-3 placement refinement (single verb →
two-half seam), no verdict reversals. All three resolve to **docs only — zero `mindsos_*` code**
(the Part-6 tag the analysis first called for was landed by concurrent work; see below).

### CC-3 — composite-capacity promotion seam → **DESIGN-ONLY (ADR-0184)**

**Strongest concern:** still **no writer**. The writer is bongard m5 (concept-mint) / Mint step 5
/ SA-6 — unbuilt; the promoter mechanism is routed to WSD (skill-acquisition design log S10),
undesigned. Building the verb now is the scaffolding §0 forbids and risks fixing the contract
against an imagined caller.

**Grounding (verified):** `promoted-pipelines` (Global) has no writer; the propose/release pivot
(`mindsos_admin.promotion.propose_for_promotion` → `mindsos_server.release.release_update`) is
ATOM-only (`PromotionItemKind.PIPELINE` raises `NotImplementedError`, Phase 24 PB-3a) and never
calls `register_capacity`; skill-install (ADR-0183) installs *authored bundles*, not runtime-minted
nodes.

**Refinement that moved across passes:** promotion is **two halves**, not one verb — (1) descriptor
half: Local `learned-parameters` composite → Global `promoted-pipelines` via the pivot's PIPELINE
branch; (2) activation half: Global-scoped `reactivate_from_descriptors` (ADR-0185) to re-register,
else the promoted node is **inert**. This corrects PLAN §7's "existing Server machinery"
(skill-install) misread.

**Pick: design-only.** ADR-0184 fixes seam shape + placement (pivot for the descriptor, reactivation
for activation; no new module) so the eventual writer is a fill-in. **Open risk:** the descriptor's
operand shape interacts with the deferred Part 5 (same-type operand arity) — confirm against the
Part-5 resolution before m5 sizes the build.

### CC-2 — composite `node_kind` → **KEEP DEFERRED (no code)**

Verified nothing dispatches on a composite kind: the `node_kind` triad is
REACTIVE/MONITOR/ADAPTER(+DATASTATE); only `KIND_MONITOR` is dispatched (L4
`MonitorSubscriptionRegistry`); composites re-mint as `KIND_REACTIVE`; dep-ordered reactivation
keys off the `COMPOSITE_DAG` descriptor + `composite_dependencies`, **not** node_kind; the
ConjunctionFinder composes from declared edges regardless. A `KIND_COMPOSITE` constant would be
unread. §3/§6 rationale holds verbatim. Revisit only if a finder must *recognise* composites.

### Part-6 pin → **ALREADY RESOLVED by concurrent work; bongard pins `composition-lifecycle-s2-confirmed`**

**Original concern (the convention gap) was real but is now closed.** Bongard pins
`phase-50-confirmed` (`cb5d207`), which predates **everything m2 needs** — Slice 1 composite
persistence (`b56e0ac`), F9 (`1be3a70`), the CLI rename fix (`1f09228`), **and** Part 6 (`2676b9d`).
While this analysis ran, the convention was landed as **RULES §7** (core-ship checklist: every
core ship — phases *and* non-phase feats/fixes — gets an annotated `<name>-confirmed` tag at the
squash commit; §7 bullet 2 also mandates the gate exercise the CLI, closing follow-up #1 above),
and the retroactive tags were cut: **`composition-lifecycle-s2-confirmed`** (annotated, → commit
**`2676b9d`** = Part 6) and **`f9-confirmed`** already exist on `main`. `s2-confirmed` transitively
includes Slice 1 + F9 + rename + Part 6 (all four reachable from `2676b9d`).

**Pick (revised — supersedes the dated-`core-YYYY-MM-DD` proposal this analysis first reached):**
no tag to cut. **Bongard pins `composition-lifecycle-s2-confirmed`** to consume invoke
input-validation and retire its D-M2-b presence self-check. **The pin-bump is bongard's (demo-side)
action** — `git merge composition-lifecycle-s2-confirmed` into `demo/bongard`, re-gate, set
`pinned_core`. Rejected: bare sha-pin (breaks the tag-shaped `pinned_core` convention); a separate
dated tag (redundant once §7's `<name>-confirmed` tag exists at the squash commit).

### Side-findings
- **STATE staleness — hand to Mac (not self-edited; STATE is Mac-owned + in flux during this
  chat):** `core_git_sha` reads `2676b9d` but `main` has advanced to `a2e8271`; `bongard.status`
  still reads `"not started; PLAN.md at 85115da"` though the D-M2 series + a dispatching runner
  imply it has started. Bump both on the next ship-ritual STATE update.
- **ADR README index is stale** past 0137 (0138–0187, incl. 0183/0185/0186/0187, unindexed). Left
  as-is to match current practice (ADR files are the source of truth); ADR-0184 follows suit.
  Pre-existing doc-debt for a maintenance pass.

**Gate:** this chat adds docs only (ADR-0184 + this §13) — no `mindsos_*` code, no test delta, no
new tag (the needed tag already exists). No gate run required beyond the standing green at
`s2-confirmed`.

---

## 14. Part 5 — R0 consumer-gate verdict (core-mod chat 2026-06-23) → **KEEP DEFERRED (no code)**

Part 5 (DataState operand-arity / role axis) was deferred at §9/§11 for "no executing consumer."
This chat's R0 deliverable was a single verdict — **does any path EXECUTE a same-type
multi-operand capability through `invoke` today?** Reanalysis converged after 4 skeptical passes
(stable passes 3–4, no reversal). **Verdict: NO.** Ratified keep-deferred. No branch, no code, no
tag.

### Grounding (verified)

- **ARC — not a consumer.** Provenance-only. The single cap it ran through `cl.invoke`
  (`touching_delta`) is a **monolith over `(pair, background)`** — `background` is not a declared
  input and it does **not** pass two same-type operands through the inputs map
  (`projects/arc_demo/.../arc1/PIPELINE_DECISIONS.md` §4 D3, the 2026-06-21 pass-2 entry; §5 pts 5–6).
- **Bongard — active milestone is m2** (polygon Local-mint + restart): a **flat composite,
  `input_group=all_required` over distinct DataState types** (`{segments,vertices}→polygon`). No
  same-type operand. `CORE_CHANGES.md`: "Milestone 2 is fully core-unblocked." Does not hit Part 5.
- **Bongard comparators (`same_object`/`same_shape` = two Objects/Shapes)** are **milestone 3**
  (scene parse / relation types, `PLAN.md` §9 + §8 mapping), downstream of the active m2 and
  **not built** (committed `demo/bongard` = 3 docs, no runner; any uncommitted runner lives on the
  unmounted `MindsOS-bongard` worktree, but the milestone sequence is decisive — m3 is unreached).
- **m5 fold / promotion** — upstream-gated: no writer, WSD-routed (ADR-0184; `PLAN.md` line 28
  "Build at m5 — not now").

### Trigger conditions (un-defer only when ONE is met)

1. **`invoke` must enforce `fold`.** Part 6 (§11) shipped `fold` *unenforced* because its
   "N-values-under-one-IRI" shape needs Part 5's operand axis. The first executing `fold` consumer
   (none today — `reconcile_background` is ARC provenance-only; m5 fold gated) makes Part 5 the
   prerequisite to closing that validation branch. **This is the one real coupling.**
2. **ConjunctionFinder must auto-compose a comparator from two separately-produced same-type
   operands.** The **monolith-over-pair workaround** (one composite "Pair" DataState, body unpacks
   internally — proven by ARC's `touching_delta`) lets a demo ship `same_object` *without* core
   change, but hides the two operands from the finder. Part 5 is required only if the finder itself
   must compose by role. Until a consumer needs that, the workaround stands.

### Conditional dep carried forward (no action now)

ADR-0184 (CC-3) ties m5's promotion-descriptor operand shape to the Part-5 resolution. Not
circular: only the *subset* of m5 mints with same-type-operand inputs needs Part 5; the built
polygon-family path does not. Fires conditionally if/when a same-type-operand concept is minted.
Captured as ADR-0184's "open contract risk" — unchanged.

### Side-finding (hand to Mac — STATE is Mac-owned)

`STATE.json` `pending_designs.composition-lifecycle-s2-part5` labels the comparators a
"concept-search milestone." Per `PLAN.md` §9 they are **scene-parse (m3)**; concept-search is m4.
Substance unchanged (both downstream of m2, unbuilt). One-word fix on the next STATE touch; add a
pointer to this §14.

**Gate:** docs only (this §14) — no `mindsos_*` code, no test delta, no new tag. No gate run
required beyond the standing green at `s2-confirmed`.
