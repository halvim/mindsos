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
