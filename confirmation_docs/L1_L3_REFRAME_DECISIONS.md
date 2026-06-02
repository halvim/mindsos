# L1/L3 Reframe Chat — Decisions Log

**Chat:** L1/L3 reframe chat
**Opened:** 2026-06-01 (post Chat A 2026-05-28 + Chat B 2026-05-31 closure)
**Closed:** 2026-06-01
**Purpose:** Per-decision settlement record. Ratifies Chat A R6 routed-to-reframe items (D36, D38, D46, D48) + the L3 family contract additions Chat A authored that need formal contract.

---

## ADR map

| Decision | ADR | Title | Phase |
|---|---|---|---|
| D36 — Monitor lifecycle ownership | ADR-0155 | Monitor lifecycle relocated from L3 to L4 substrate | X2 |
| D38 — Capacities-as-hyperedges | ADR-0156 | L3 capacity-to-DataState topology reframed as explicit bipartite | X3 |
| D46 — Universal `unhandled_inputs` | ADR-0157 | L3 capacity dont-know contracts are family-specific, not universal | X1 |
| D48 — DataState taxonomy | ADR-0158 | DataState naming convention with realm sub-namespace | X1 |
| Registration contract v2 | ADR-0159 | Capacity registration contract v2 | X3 |

ADR numbers renumbered from initial draft proposal (0151–0155) because 0151–0154 were taken by parallel L2 work (L2 storage tiers, L2 role-graph schema v2, L2 mutation discipline, alignment naming).

**Ship phase sequencing:**

- **Phase X1** = ADR-0157 + ADR-0158 bundled (shared `identifiers.py` realm constants + `family_rules.py` module). Lightweight; docs + module + small validator + DontKnowReason enum addition + `DS_UNHANDLED_INPUT` constant.
- **Phase X2** = ADR-0155 (monitor lifecycle relocation). Mid-size; retires Phase 31 module + tests + public exports; adds `cl.iter_monitors()` helper.
- **Phase X3** = ADR-0156 + ADR-0159 + Phase 27 audit deliverable. Largest; atomic `_CapacityBase` migration (bipartite topology + 5 new contract fields + typed CapacityContext + 4-method MMHandle Protocol + 5 verdict types + `mindsos_instances` Phase 06 amendment).

---

## §D36 — Monitor lifecycle ownership (ADR-0155)

### Settlement

Retire from L3: `start_resident()` / `stop_resident()` / `active_subscriptions()` methods, `_subscriptions` dict, `ResidentSubscription` dataclass, `ResidentError` exception, `KIND_RESIDENT` constant. Keep at L3: `Monitor` subclass + `subscribes_to` field with DataState IRI semantics + new `cl.iter_monitors()` helper. Rename `KIND_RESIDENT` → `KIND_MONITOR`. L4 substrate (downstream) owns session-scope subscription registry.

### Saturation history

| Round | Reversals | Refinements | Status |
|---|---|---|---|
| R1 | 0 | 0 (initial picks) | not saturated |
| R2 | 0 (1 missed pick added: `subscribes_to` semantic) | 4 | not saturated |
| R3 | 0 | 2 | **saturated** |

### Key picks

- **Core fork B (kept):** Monitor subclass stays + lifecycle methods drop + `cl.iter_monitors()` helper added. Rejected (A) full retire (loses authoring-time clarity), (C) subscription-as-edge (third edge type violates Chat B D-B46 v1 catalog lock).
- **subscribes_to semantic:** DataState IRIs (Phase 31 shipped form). WSD `coordinated_change_L3` capacity-IRI shorthand translates at authoring time. Locked at R2.
- **KIND_MONITOR rename** (not full retire). Preserves node_kind triad (REACTIVE/MONITOR/ADAPTER).
- **Hard-break public exports** (`KIND_RESIDENT`, `ResidentSubscription`, `ResidentError`) gated by consolidated R0 audit (shared with ADR-0156 hard-break audit).
- **L4-side subscription registry shape constrained** at session-scope `Dict[DataState IRI, List[Monitor IRI]]`, not per-task instance refs.
- **Sequencing:** D36 ships first (Phase X2) — reverses earlier sequencing pick; D36 is structurally smaller; shipping it first removes ~100 LOC of resident infrastructure that the D38 author would otherwise have to mentally bracket.

### Chat A R6 reconciliation

Chat A R6 stated "L3 `start_resident` / `stop_resident` retired (Chat A preference) **or repurposed**." Conflicted with R1 D32.4 ("`start_resident()` and `stop_resident()` MUST be called from orchestrator thread") and HANDOFF §3.1 ("settled" L3-surface-L4-consumes set). Chat B D-B13 ("no shadow state outside MM") + D-B15 ("L3 owns capacities only; threads are L4") + D-B38 (orchestration runtime state in intel-MM) jointly resolve the ambiguity toward full retire.

### Cascades

- HANDOFF §3.1 amendment — strike `cl.start_resident()` / `cl.stop_resident()` / `cl.active_subscriptions()` from L3-surface-L4-consumes list; add `cl.iter_monitors()`.
- L3-Q1 resolved: no L3-internal residents; Monitors and "residents" collapse to one concept.
- Test churn: Phase 31 retires whole (~6-8 files); Phase 27 + Phase 28 dataclass/register tests get `node_kind` rename edits. Total ~10 files.
- WSD installation chat: Monitor authoring shape unchanged.
- Chat A R1 D32.4 resident clarification reframed: thread discipline moves to L4 substrate's MonitorSubscriptionRegistry.

---

## §D38 — Capacities-as-hyperedges (ADR-0156)

### Settlement

L3 type-graph adopts bipartite topology mirroring Chat B D-B40 instance layer. Capacities + DataStates remain nodes; new explicit `produces` (capacity→DataState) + `consumes` (DataState→capacity) IntergraphEdges emitted at `register_capacity` time. TYPE_COMPAT retires; `discover_for_capacity` / `discover_for_datastate` / `rediscover_all` retire; `discovery.py` module (~330 LOC) deletes. `views.successors_of` + `pipeline.find_pipeline` rewrite against bipartite walks (semantic-preserving). `mindsos_instances` Phase 06 amendment ships `IntergraphEdgeInstance` + `IntergraphHyperEdgeInstance`.

### Saturation history

| Round | Reversals | Refinements | Status |
|---|---|---|---|
| R1 | 2 | 5 | not saturated |
| R2 | 1 | 4 | not saturated |
| R3 | 0 | 4 | **saturated** |

### Key picks

- **Core fork A — Bipartite** (capacity-as-node + explicit produces/consumes IntergraphEdges). Rejected (B) hyperedge (type/instance asymmetry; runtime never traverses type-graph hyperedge; primitive cost unpaid), (C) status quo (asymmetry persists).
- **Instance-layer mirrors type-layer** — both nouns separate in capacity-MM; `IntergraphEdgeInstance` ships as new instance subclass. Plus Chat B D-B41 (Pipeline composition via IntergraphHyperEdge) requires `IntergraphHyperEdgeInstance` — Chat B cascade gap surfaced and absorbed into ADR-0156 Phase 06 amendment.
- **`register_capacity` gains `if_exists` flag** (`Literal["raise", "upsert"]`) — `"upsert"` is migrator + partial-state recovery path with idempotent edge emission. Multi-statement Falkor transactions don't atomicize cross-statement; pre-validation catches declaration errors but not infra failures mid-loop. Recovery via re-register.
- **Strip `inputs`/`outputs` from node properties** — single source of truth = edges. Co-ship `views.inputs_of` / `views.outputs_of` helpers using two-source strategy (declaration registry primary; graph walk fallback).
- **DataStates append-only** — written invariant; deletion path = future ADR.
- **Migration scope is Global only** — per Phase 38 carry-forward #3 (`FalkorDBLocalPersister` unshipped), Locals are in-memory and re-registered each session.
- **Sequencing:** D38 / ADR-0156 ships in Phase X3 atomic-bundled with ADR-0159 (capacity registration contract v2) + Phase 27 audit deliverable. Two ADRs on `_CapacityBase` → single phase ship for atomic schema change.

### Cascades

- ADR-0069 + ADR-0086 retire entirely.
- ADR-0070 + ADR-0071 amend.
- ADR-0132 (instancing moved to mindsos_instances) amends — catalog expands from 8 subclasses to 10.
- Phase 38 carry-forward #4 (`add_type_compat` admin API) retires.
- Phase 38 carry-forward #10 (mkdocs `--strict` lift) grows by 8-12 docs surfaces; bundled into ADR-0156 ship.
- L3-19 (`include_deprecated` discipline) folds into ADR-0156 scope.
- Chat B D-B46 v1 edge catalog locks honored verbatim at L3 type-graph.

---

## §D46 — Universal `unhandled_inputs` contract (ADR-0157)

### Settlement

Reverses Chat A R6 "universal no-opt-out" direction. Family-specific dont-know contracts via 5-shape catalog (DATASTATE_MARKER, OPTIONAL_RETURN, VERDICT, VALIDATION_RESULT, NO_DONT_KNOW). Family rule implicit from capacity IRI prefix; two-level lookup (name prefix first → category fallback → DATASTATE_MARKER permissive default + info log). New module `mindsos_capacity/family_rules.py` ships the FAMILY_RULES dict + lookup function. `DS_UNHANDLED_INPUT = "datastate:marker.unhandled_input"` constant ships. `DontKnowReason.UNHANDLED_INPUT` enum value added.

### Saturation history

| Round | Reversals | Refinements | Status |
|---|---|---|---|
| R1 | 0 | 0 (initial picks) | not saturated |
| R2 | 1 (dropped `dont_know_contract_iri` field; rule implicit from prefix) | 5 | not saturated |
| R3 | 0 | 6 | **saturated** |

### Key picks

- **Core fork C — Family-specific** contracts. Rejected (A) universal predicate (type-meaningless for non-DataState-returning families), (B) universal return-side marker (forces wrapper types on scalar returns), (D) hybrid (abstraction without simplification).
- **5-shape catalog** refined from 6 to 5 across saturation rounds — collapsed SCALAR_OPTIONAL + COLLECTION_SENTINEL into OPTIONAL_RETURN; replaced BOOL_DIAGNOSTIC with NO_DONT_KNOW for predicate family default.
- **Two-level prefix lookup** (PB-D46-8) — name prefix first, then category; handles both `capacity:scoring:attention_score` (category lookup) and `capacity:agglomeration:combination.bayesian` (name-prefix lookup for method libraries).
- **No `dont_know_contract_iri` registration field** — rule implicit from prefix; PB-D46-1 retraction.
- **Per-capacity override deferred to v2** — if a real case demands family-rule override, ADR-0159 amendment adds the field then.
- **WSD Monitor `update_state` dont-know discipline** — return `DS_UNHANDLED_INPUT` instead of new state on uninterpretable signal; L4 substrate skips SCMSState write + fires problem-trace event.

### FAMILY_RULES dict corrections (refined across saturation)

Initial draft mapped families to shapes; reanalysis with each family's actual return type surfaced 5 corrections from the Round 1 draft:

- `hint` → OPTIONAL_RETURN (returns HintNode composites in intel-MM, NOT DataStates).
- `planning` → OPTIONAL_RETURN (returns Plan/Milestone composites in intel-MM).
- `dream` → OPTIONAL_RETURN (orchestration; None on no-aggregation).
- `signal` → rename key from `signal_source` (Chat A R3 signal rename moved the prefix).
- `phase6` → added entry as OPTIONAL_RETURN (BlameVerdict per Chat B D-B26 has no explicit dont-know channel; None on dont-know natural).

### Cascades

- ADR-0157 reverses Chat A R6 direction — documented in §rationale + HANDOFF §3.1.5 footnote.
- Chat B D-B40 capacity-MM bipartite shape composes with `DS_UNHANDLED_INPUT` instances cleanly.
- `predicate.*` capacities must be `inline=True` per L3-36 family contract (max_latency_ms ≤ 5).
- Phase 27 audit deliverable `confirmation_docs/PHASE_27_DONT_KNOW_AUDIT.md` deferred to ADR-0156 ship phase X3 R0.

---

## §D48 — DataState taxonomy + naming convention (ADR-0158)

### Settlement

IRI form `datastate:<realm>.<name>` — 2 colon-segments with realm as dot-prefix within name; matches shipped Phase 27–33 form verbatim. No `mindsos:` prefix. 9 reserved v1 realms: core, marker, bridge, text, mm, problem_trace, nlu, code, dream. Single-dot at v1; multi-dot deferred to v1.5+. Strict-by-default realm validation at `register_datastate` with `allow_new_realm=True` opt-in for admin extensions. Realm-name constants in `identifiers.py`. Bridge family form documented in prose only; no shipped placeholder entry.

### Saturation history

| Round | Reversals | Refinements | Status |
|---|---|---|---|
| R1 | 0 | 0 (initial picks based on guess) | not saturated |
| R2 | 2 (probe surfaced shipped form) | 5 | not saturated |
| R3 | 1 (bridge example dropped) | 4 | not saturated |
| R4 | 0 | 3 | **saturated** |

### Key picks

- **IRI form A — Shipped 2-segment** (`datastate:<realm>.<name>`). Round 2 reversal: my R1 lock of `mindsos:datastate:<realm>:<name>` (4-segment colon form) was based on guessing without probing shipped form. Probe surfaced the actual shipped form; reversed without retroactive migration cost.
- **No `mindsos:` prefix** — Round 2 reversal; shipped form omits.
- **Bridge example entry dropped** — Round 3 reversal of R2 placeholder `datastate:bridge.example_a_to_b`. ADR-0158 documents form pattern in prose only; no shipped placeholder. Adapter family chat registers concrete bridges at authoring time.
- **9-realm reserved list** — Round 2 refinement; adds `mm` + `problem_trace` to match shipped reality.
- **Realm-name constants in `identifiers.py`** — Round 3 refinement (moved from `family_rules.py` initial home). Symmetric with other IRI-helper functions; `family_rules.py` imports `REALM_MARKER` directly (no `MARKER_NAMESPACE` alias).
- **Strict-by-default + opt-in** — admin typo (`mraker` for `marker`) catches at register-time; admin extension path explicit.
- **Sequencing:** Phase X1 bundled with ADR-0157 (shared `identifiers.py` realm constants + `family_rules.py` module).

### Cascades

- Chat B D-B42 `data_state_type_iri: IRI` accepts realm-tiered form without amendment.
- ADR-0157 marker namespace alignment satisfied via `REALM_MARKER` constant.
- Cataloging responsibility split: NLU → WSD installation; code → code-skill installation; bridge → adapter family chat; dream → L3-51 dream family chat.
- ADR-0150 §82 alignment naming reconciliation (DWF chat PB-7) unaffected — different prefix (`role:*` vs `datastate:*`).

---

## §Registration contract v2 (ADR-0159)

### Settlement

Atomic ratification of 5 new fields on `_CapacityBase` (`concurrent`, `inline`, `max_latency_ms`, `precondition_iri`, `effect_iri`, `reads_mm`) + new `mindsos_capacity/context.py` module shipping typed `CapacityContext` (9 fields) + 4 Protocols (MMHandle, KLHandle, CapacityLayerHandle, CancelToken) + `CancelTokenView` wrapper + 5 canonical decision verdict types. `register_capacity` validation expansion (~20 LOC). Phase 33-35 write capacity body migration `context["kl"]` → `context.kl`.

### Saturation history

| Round | Reversals | Refinements | Status |
|---|---|---|---|
| R1 | 0 (initial picks) | 0 | not saturated |
| R2 | 1 (`reads_mm` two-valued, not three-valued) | 6 | not saturated |
| R3 | 0 | 5 | **saturated** |

### Key picks

- **Fork 1: scope = contract fields + CapacityContext only**; L3-36 predicate family ships as separate family-catalog doc.
- **Fork 2: `concurrent=True` default** (Chat A R1 D32.4 reaffirmed); Phase 27-33 audit annotates non-thread-safe capacities with `concurrent=False`.
- **Fork 3: `inline=True` requires `max_latency_ms`** registration-time enforcement.
- **Fork 4: `decision.should_replan` reads contract IRIs via `context.cl.get_declaration()`** — strict-line preservation; L4 substrate never reads contract IRIs directly.
- **Fork 5 (reversed R2): `reads_mm: bool = False`** two-valued. Three-valued `Literal["none", "read", "read_write"]` had no v1 consumer (Chat B invariant: L3 capacities never write to MM).
- **Fork 6: new `context.py` module** for typed CapacityContext + Protocols.
- **Fork 7: Python subclass + Protocol** for per-family CapacityContext extensions.
- **Fork 8: 4-method MMHandle** (`get_or_instantiate`, `find_instances_by_type`, `produces_of`, `consumes_of`) — refined from 2-method in R3 to add bipartite-walk helpers under D38 = A.
- **Fork 9: `version_snapshot` mutable L4-side, read-only via `Mapping` protocol** to capacity body. Refined from "frozen at task start" framing in R2 to reflect Chat B D-B14 lazy instantiation reality.
- **Fork 10: backward compat via defaults**; Phase 33-35 body migration is mechanical (~2-3 bodies).
- **Fork 11: all register-time validation checks**.
- **`kl` field uses `KLHandle` Protocol** (R3 refinement) — preserves Phase 28 import-isolation without sacrificing types.
- **`cl: CapacityLayerHandle` field added** (R3 refinement) — symmetric with `kl`; enables decision.should_replan registry reads.
- **`CancelTokenView` wrapper + `MappingProxyType` for version_snapshot** — defense-in-depth for body-side read-only views.
- **5 canonical decision verdict types** (R2 family batch refinement) — `decision.*` family bare-value returns wrap in verdict types so VERDICT family rule (ADR-0157) applies uniformly.

### Cascades

- ADR-0072 (invoke envelope) amends — context shape transitions to typed CapacityContext.
- ADR-0078 / ADR-0143 / ADR-0146 / ADR-0147 amend — typed access paths.
- L3-32 thread-safety audit lands at Phase X3 ship R0.
- L0-21 (`kl.read_at_version`) ships as Chat C plan-authoring scope.

---

## §L3-36 → L3-51 family contract batch

### Settlement

13 remaining L3-* items + 2 Chat B additions (L3-50, L3-51) ratified as family contracts in one batch. This chat ratifies family **contracts** (shape + naming + defaults); concrete capacity authoring is downstream (WSD installation, code-skill installation, adapter family chat, FOL installation, dream family chat).

### Family contract table

| L3# | Family Prefix | v1 Catalog | Family Rule | Realm | Reg Defaults | Owner Chat |
|---|---|---|---|---|---|---|
| L3-36 | `predicate.*` | 5-10 | NO_DONT_KNOW | n/a | `inline=True`, `max_latency_ms ≤ 5` | This chat (contract) + WSD (catalog) |
| L3-37 | `als.*` + `mechanism.*` + `validate.*` | 1 + 3 + 3 | OPTIONAL/OPTIONAL/VALIDATION_RESULT | n/a | `concurrent=True` | WSD installation |
| L3-38 | `pattern.*` | 1 | OPTIONAL_RETURN | n/a | `concurrent=True` | WSD installation |
| L3-39 | `decision.classify_dont_know_reason` | 1 | VERDICT | n/a | `concurrent=True` | WSD installation |
| L3-40 | (indexing infra) | n/a | n/a | n/a | n/a | WSD installation |
| L3-41 | (signal payload schema, dataclass) | n/a | n/a | n/a | n/a | This chat ratifies |
| L3-42 | `hint.*` | 20+ baseline | OPTIONAL_RETURN | n/a (HintNode intel-MM) | `inline=True`, `max_latency_ms ≤ 5` | This chat (contract) + WSD (catalog) |
| L3-43 | `process.*` | per-domain | DATASTATE_MARKER | text/code/business | `inline=True` | WSD + code-skill |
| L3-44 | `decision.derive_goal` | 1 | VERDICT | n/a | `concurrent=True` | WSD installation |
| L3-45 | `promotion_rule.*` | 6 | OPTIONAL_RETURN | n/a | `concurrent=True` | WSD installation |
| L3-46 | `decision.select_promotion_rule` | 1 | VERDICT | n/a | `concurrent=True` | WSD installation |
| L3-48 | `retrieval.by_admin_decision_similarity` | 1 | OPTIONAL_RETURN | n/a | `concurrent=True` | WSD installation |
| L3-49 | `adapter.*` | per-bridge | DATASTATE_MARKER | bridge | `concurrent=True` | adapter family chat |
| L3-50 | `planning.*` | 4 (Chat B D-B25) | OPTIONAL_RETURN | n/a (intel-MM composites) | `concurrent=True` | WSD installation |
| L3-51 | `dream.*` | 3 (Chat B D-B6) | OPTIONAL_RETURN | n/a | `concurrent=True` | dream family chat (future) |

### Saturation history

| Round | Reversals | Refinements | Status |
|---|---|---|---|
| R1 | 0 (initial picks) | 0 | not saturated |
| R2 | 0 | 3 (FAMILY_RULES corrections + decision verdict wrappers + process/text legacy doc) | **saturated** |

### Key picks

- **L3-36 predicate family `inline=True` strict-enforce** at registration — Phase 1 perf budget forces inline discipline; authors needing slow predicates split into sub-predicates rather than override.
- **L3-37 ALS three-sub-family bundled** in one ratification (`als.*` + `mechanism.*` + `validate.*` share authoring chat ownership).
- **L3-42 hint family rule corrected** to OPTIONAL_RETURN (returns HintNode intel-MM composite, not DataState).
- **L3-43 process.* single-dot lock** at v1 (`process.text_tokenize`); coexists with shipped `text.*` family per documented legacy.
- **L3-50 planning aggregate_outputs returns None on dont-know** — uniform OPTIONAL_RETURN family rule; aggregator returning DataState wraps in Optional.
- **L3-51 dream.* ownership deferred** — first dream consumer triggers chat; ADR-0157 + ADR-0159 sufficient for contract.
- **decision.* family wraps bare-value returns in 5 canonical verdict types** — ADR-0159 ships ReplanVerdict (Chat A R2) + TierVerdict + GoalVerdict + PipelineFindVerdict + PromotionRuleVerdict.

### Chat B amendments to family catalog

- **L3-50** + **L3-51** added per Chat B D-B25 (planning) + D-B6 (dream).
- **ALS subsystem #11** (planning decomposition calibration) per Chat B D-B52; signal source `signal.plan_decomposition_outcome` per D-B51 — folded into L3-37 scope.
- **v1 ALS subsystem count: 11** (was 10 in Chat A R3).
- **v1 signal catalog: 10** (was 9 in Chat A R3); S7 still reserved.

---

## §Phase 27–33 migration plan

### Code surfaces

| Surface | Migration | Phase | Sized |
|---|---|---|---|
| `_CapacityBase` schema | 5 new fields default-valued | X3 | trivial |
| `register_capacity` | edge emission loop replaces TYPE_COMPAT discovery | X3 | ~30 LOC |
| `discovery.py` module | retires whole | X3 | ~330 LOC delete |
| `pipeline.find_pipeline` BFS | bipartite walk algorithm | X3 | ~50 LOC |
| `views.successors_of` | bipartite walk | X3 | ~20 LOC |
| `mindsos_instances` Phase 06 | adds IntergraphEdgeInstance + IntergraphHyperEdgeInstance | X3 | ~80 LOC |
| `Monitor.subscribes_to` translation | docs-only at WSD authoring | downstream | docs |
| `start_resident` / `stop_resident` / `_subscriptions` / `ResidentSubscription` / `ResidentError` | retire whole | X2 | ~150 LOC delete |
| `KIND_RESIDENT` → `KIND_MONITOR` rename | global rename | X2 | trivial |
| Phase 33-35 write capacity bodies | `context["kl"]` → `context.kl` | X3 | ~5 LOC × 2-3 bodies |
| `family_rules.py` new module | ships v1 | X1 | ~50 LOC |
| `identifiers.py` realm constants | adds 9 `REALM_*` + frozenset | X1 | ~15 LOC |
| `register_datastate` validation | strict + opt-in | X1 | ~10 LOC |
| `DS_UNHANDLED_INPUT` registration | ships v1 marker | X1 | trivial |
| `DontKnowReason.UNHANDLED_INPUT` enum entry | ships v1 | X1 | trivial |
| `context.py` new module | typed CapacityContext + 4 Protocols + CancelTokenView | X3 | ~150 LOC |
| 5 verdict wrapper types | ships in context.py or verdicts.py | X3 | ~30 LOC |

### Test surfaces

| Suite | Status | Phase |
|---|---|---|
| `tests/phase_29/*` | retires whole (~7 files) | X3 |
| `tests/phase_31/*` | retires whole (~6-8 files) | X2 |
| `tests/phase_27/test_capacity_dataclass.py` | edit (Monitor node_kind rename + new contract fields) | X2 + X3 |
| `tests/phase_28/test_capacity_layer_register_capacity.py` | edit (register_capacity edge emission + node_kind rename + new contract fields) | X2 + X3 |
| `tests/phase_28/test_schemas.py` | edit (EDGE_TYPE_COMPAT removal) | X3 |
| `tests/phase_30/find_pipeline tests` | edit (algorithm same, edges observed differ) | X3 |
| `tests/phase_32/integration_b scenario` | re-run + possibly amend | X3 |
| `tests/phase_33/test_outputs_terminator_discovery.py` | retire or rewrite | X3 |
| `tests/_shared/sentinel_paths.py` | one TYPE_COMPAT reference update | X3 |

**Estimated total test churn:** ~25 files across three phases (X1 minimal; X2 ~10 files; X3 ~15 files).

### Data migration

| Scope | Migration | Phase |
|---|---|---|
| Global capacities (Phase 27-33 shipped) | One-pass migrator under ADR-0134 schema migration; emits produces/consumes edges from existing `inputs`/`outputs` properties; strips properties; idempotent | X3 |
| Local capacities | No migration (`FalkorDBLocalPersister` unshipped; Locals are in-memory and re-registered each session) | n/a |
| Falkor schema | IntergraphEdge persistence pattern inherits from Phase 05b lock; no Cypher migration | n/a |
| Bootstrap importer | unchanged structurally; `register_capacity` internal change is invisible | n/a |

### Doc surfaces

- Phase 38 carry-forward #10 (mkdocs `--strict` lift) grows by 8-12 surfaces touching TYPE_COMPAT terminology — bundled into ADR-0156 ship phase X3.
- ADR-0070 + ADR-0071 + ADR-0072 + ADR-0078 + ADR-0132 + ADR-0143 + ADR-0146 + ADR-0147 amendment paragraphs.
- HANDOFF §3.1 amendment (strike resident methods; add `cl.iter_monitors()`).
- HANDOFF §6.1 carry-forward #4 (`add_type_compat`) marked retired.

---

## §Closure summary

**5 ADRs ratified:**

- ADR-0155 (D36) — saturated R3
- ADR-0156 (D38) — saturated R3
- ADR-0157 (D46) — saturated R3
- ADR-0158 (D48) — saturated R4
- ADR-0159 (registration contract v2) — saturated R3

**16 L3 family contracts ratified** (L3-36 through L3-51 batch; L3-47 absorbed into ADR-0159).

**3 ship phases sequenced:**

- X1 = ADR-0157 + ADR-0158 (bundled; lightweight)
- X2 = ADR-0155 (mid-size)
- X3 = ADR-0156 + ADR-0159 + Phase 27 audit (atomic `_CapacityBase` migration)

**Outstanding for downstream:**

- WSD installation chat: catalog of `predicate.*`, `hint.*`, `process.*`, `decision.*` v1 entries + 50+ family capacities.
- Code-skill installation chat: `code` realm DataState catalog + `process.code.*` capacities.
- Adapter family chat: `adapter.*` family + concrete bridge DataState registrations.
- FOL installation chat: typed CapacityContext extensions for FOL family.
- Dream family chat: `dream.*` orchestration capacity authoring.
- Chat C plan-authoring: phase-map authoring with X1 / X2 / X3 sequencing; L0-21 `kl.read_at_version` cascade scheduling.

**Closure handoff:** Chat C plan-authoring inherits this document + 5 ADR drafts. HANDOFF.md updated with §3.1.6 closure block.

---

*Chat closed 2026-06-01. Per-decision rationale complete. 5 ADRs + 16 family contracts + sequencing locked. Saturation discipline observed across all decisions (zero-reversal saturation per HANDOFF §9 criterion).*
