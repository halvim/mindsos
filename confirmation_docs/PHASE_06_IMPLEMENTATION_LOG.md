# Phase 06 Implementation Log

> **Round-7 reanalysis pass (P45–P65) ran BEFORE any code landed**, per 05d precedent. The design-locked row in `confirmation_docs/PHASE_MAP.md` §5 (locked 2026-05-11 across 6 reanalysis rounds) was re-litigated against the on-disk state (`mindsos_core/` audit + ADR-file audit + `validate_user_properties` audit) and against the user's accepted picks. **21 numbered pushbacks (P45–P65) reshaped the row before implementation.** The shape that ships in this PR reflects the post-P45-P65 row text; the original lock is preserved in `PHASE_06_DESIGN_LOG.md` for historical record.
>
> Numbering convention: P1–P44 are design-chat picks (in `PHASE_06_DESIGN_LOG.md`); P45+ are implementation-chat picks (in this file). Cross-references to the original design picks are inline. The pushback density (21 in one round) reflects the design-chat's reliance on row-text rather than on-disk audits — three reanalysis passes by the implementation chat caught issues the design rounds missed.

---

## §1 Round-7 ledger (P45–P65)

### P45 — §G ADR file edits target files that don't exist on disk. **Pick: B.**

A. Create ADR-0132 + 0037 + 0014/0015/0017/0019/0025/0026 pointer-line targets from scratch (8 net-new files of ADR boilerplate).
B. **Defer all ADR file edits to Phase 38 per 5-cascade precedent. PHASE_MAP §5 row stays canonical until then.**
C. Create only ADR-0132 (renamed-package identity ref); defer rest.

**Audit:** `Glob **/0132* → no results`; `Glob **/0014* → no results`; `Grep ADR-0132 → only in confirmation_docs + mindsos_core/__init__.py + docs/dev/repo-layout.md`. 05d implementation log §70 confirms: *"05b and 05c amendments are NOT on disk in those ADR files (they're deferred to Phase 38 per shipped precedent)."* P2 A's "rewrite to match reality" justification is moot — there is no on-disk file describing the wrong reality.

**Consequences:** §G of the row collapses. The only on-disk amendment that survives is `mindsos_core/__init__.py:54` reference fix (P19 A, retained). No ADR files created; no status flips; no pointer lines added. Phase 38 ADR-port batch absorbs the full text.

### P46 — P11 A instance-ID derivation breaks under P27 A mutable overrides. **Pick: C.**

A. Drop overrides-hash; use `(template_id, occurrence_counter)`.
B. UUID4 per instance (drop UUID5 entirely).
C. **Delegate to metagraph's `id_strategy.generate("instance", content={"template_id": tid, "instance_seq": next_seq})` — no overrides in content; per-template per-metagraph sequence counter as disambiguator.**
D. Keep P11 A; reverse P27 A.

**Audit:** `UUID5FromContentStrategy.__init__` docstring (`identity.py:86-92`) explicitly warns: *"Content-addressable IDs change with content. Pivot's auto-upgrade contract requires id stability across mutation, so this strategy is not the right choice for a Metagraph whose nodes will be auto-upgraded under release."* Instance overrides ARE mutation; including them in hash input creates exactly the failure mode the docstring warns against.

**Consequences:** §B per-subclass dataclass gains `_instance_seq: int` derived from `mg.element_registry._next_seq_for(template_id)` at construction. Canonicalize utility (P34 B) survives — it's used for `set_override`-time validation and (deferred to Phase 07) persistence equality, not for ID derivation. Row §C ElementRegistry API gains private `_next_seq_for(template_id) -> int`.

### P47 — §B universally-forbidden list contradicts EdgeInstance allow-list on `source_id`. **Pick: C.**

A. Strike `source_id (where applicable)` from universal list.
B. Strike `source_id`/`target_id` from EdgeInstance allow-list (reverses P29 C / P36 A).
C. **Wording bug: `source_id` in universal list was meant to be the instance identity field (already covered by `id`). Strike `source_id (where applicable)` as redundant.**

**Consequences:** Row §B universally-forbidden list reduced to: `id`, `template_id`, `kind`, `metagraph_id`, `type_name` (Edge/HyperEdge/MetaEdge/MetaHyperEdge per P33 B). Per-subclass allow-list is authoritative for structural-field overrides.

### P48 — `label` field is in no allow-list but exists as Core dataclass field on Edge/HyperEdge/MetaEdge/MetaHyperEdge. **Pick: A.**

A. **Add `label` to each applicable subclass's allow-list in §B.**
B. Lift `label` into user-property bag at instance-merge time (semantic shift).
C. Forbid label overrides; defer to Phase 10.

**Audit:** `Edge.label: Optional[str]` at `edge.py:39`; `HyperEdge.label: Optional[str]` at `edge.py:76`; `MetaEdge.label: Optional[str]` at `metagraph.py:121`; `MetaHyperEdge.label: Optional[str]` at `metagraph.py:167`. **Also: `RESERVED_PROPERTY_KEYS` already contains `label`** (`validation.py:45`) — confirms `label` is a structural field, not a user property. Per P64 A bifurcation, `label` belongs in the structural allow-list.

**Consequences:** Row §B table gains `label` for EdgeInstance/HyperEdgeInstance/MetaEdgeInstance/MetaHyperEdgeInstance.

### P49 — Cascade-observer attach point in §F + Risk section is under-specified and risks ADR-0010 boundary violation. **Pick: B + A.**

A. Lazy attach via `mindsos_instances.attach_registry(mg)` called on first instance addition; idempotent.
B. **Core ships `Graph.register_remove_observer(cb)` + `Metagraph.register_remove_observer(cb)` plumbing only. `mindsos_instances.ElementRegistry(mg)` subscribes itself.**
C. Core imports `mindsos_instances`. Breaks ADR-0010.

**Audit:** Row Risk says `Metagraph.__post_init__ constructs and attaches the registry`. But `Metagraph` is a plain class with `__init__` (verified `metagraph.py:240`), not a dataclass with `__post_init__`. Boundary check: `mindsos_core` must not import `mindsos_instances` (ADR-0010 mirror of ADR-0014 layer-boundary rule).

**Consequences:** Core gains `register_remove_observer(cb)` + observer-dispatch loop on each remove method (P65 A atomic). `mindsos_instances.attach_registry(mg)` is the idempotent caller-facing helper that constructs and attaches `ElementRegistry(mg)`. ElementRegistry's `__init__(mg)` subscribes itself to Core's observer plumbing. Row Risk text replaced.

### P50 — `CompositeInstance.metagraph_id` origin unspecified. **Pick: A.**

A. **Required at construction; empty composites legal; `add_member` validates equality, never infers.**
B. Infer from first `add_member`; lock after.
C. Composites must be non-empty (≥1 member required at construction).

**Consequences:** `CompositeInstance.__init__(*, metagraph_id, ...)` — required kw-only arg. Symmetric with the 7 other subclasses. `add_member(instance)` raises `CrossMetagraphCompositeError` if `instance.metagraph_id != self.metagraph_id`. Empty composites legal (matches "working memory" semantics).

### P51 — `SubGraphInstance.materialise` copy semantics undefined. **Pick: A.**

A. **Spec inline: fresh `IdentityRegistry`; nodes/edges via `dataclasses.replace(orig, id=new_uuid)` + deep-copy of properties; role inherited; no schema attached.**
B. Defer to Phase 07.
C. Ship `Graph.copy(*, new_identity=True)` helper in Core.

**Consequences:** Row §E SubGraphInstance materialise paragraph gains the explicit copy spec. No Core surface change. Pickle-based deep-copy of `properties` dict (sufficient for primitive-typed property bag).

### P52 — Test category "observer unsubscribe on registry teardown" targets behavior that doesn't exist. **Pick: A.**

A. **Strike teardown tests from §Tests (~5 tests). Document lifecycle as "while metagraph lives, registry lives, observer remains active."**
B. Add explicit `ElementRegistry.shutdown()`.
C. Implement via `weakref` callback.

**Consequences:** §Tests projected total reduced; documentation in §C ElementRegistry section explicit on Python-ownership lifecycle.

### P53 — CLI exit codes unspecified for instantiate-*/compose error paths. **Pick: A.**

A. **Adopt 05d split: 0 success / 1 invariant violation / 2 resource-not-found / 3 reserved.**
B. 0/1 only.
C. Defer to implementation.

**Consequences:** Row §H gains exit-code table. Concrete mapping: `OverrideScopeError`/`SubGraphInvariantError`/`CompositeCycleError`/`CrossMetagraphCompositeError`/`DanglingTemplateError` → exit 1; `IdentityError` (unknown template_id, unknown metagraph) → exit 2.

### P54 — GraphInstance materialise behavior under empty override scope undefined. **Pick: B.**

A. Empty fresh Graph carrying source role only.
B. **Deep-copy of source Graph: all nodes/edges/hyperedges/properties; fresh IDs; fresh IdentityRegistry; role inherited.**
C. NotImplementedError; defer to Phase 10.

**Consequences:** Row §E GraphInstance materialise = full clone. SubGraphInstance is the partial-copy variant; GraphInstance is the full-clone variant. Phase 10 will let users override role/properties; until then GraphInstance materialise has a real use ("clone with new identity").

### P55 — `CompositeInstance.add_member(instance)` doesn't validate instance is in the registry. **Pick: A.**

A. **`add_member(instance)` raises `IdentityError` if `instance.id not in registry`.**
B. No check; document caller responsibility.
C. Auto-re-register stale instances.

**Consequences:** Row §C ElementRegistry section adds the registry-membership check spec. After cascade-remove, a held instance ref cannot be re-added to any composite.

### P56 — Cascade chain doesn't unregister instance IDs from `mg.identity`. **Pick: A.**

A. **`ElementRegistry.remove(instance_id)` calls `mg.identity.unregister(instance_id)` after deleting from internal dict.**
B. Caller responsibility.
C. Don't share IdentityRegistry (reverses P11 A).

**Consequences:** Row §F step 2 amended: `registry.remove(instance_id)` includes `mg.identity.unregister(instance_id)`. Test category gains: "after cascade, `mg.identity` no longer contains cascaded instance IDs."

### P57 — JSON-fragment override parsing for set-typed fields needs explicit list→set coercion. **Pick: A.**

A. **Coerce list→set at override-set time per the per-subclass set-field allow-list. Duplicates in input dedup silently.**
B. Reject duplicates in input list.
C. Require canonical set-as-sorted-list everywhere.

**Consequences:** Row §B adds a "set-typed structural fields" note: keys `member_ids` (HyperEdgeInstance), `node_ids`/`edge_ids` (SubGraphInstance), `graph_ids` (MetaHyperEdgeInstance per P60 A) accept JSON list input + coerce to Python set/frozenset.

### P58 — Edge/HyperEdge materialise has no spec for resolving ID-overrides to Node objects. **Pick: A.**

A. **Walk `metagraph.graphs.values()` at materialise time to resolve override IDs to Node objects. Raise `IdentityError` if not found.**
B. Add `Metagraph._id_to_graph` reverse-index.
C. Materialise produces placeholder Node objects; Phase 07 attach resolves.

**Audit:** `Edge.source: Node`, `Edge.target: Node` (object refs, `edge.py:36-37`); `HyperEdge.nodes: Set[Node]` (`edge.py:74`). Override keys are ID strings. No reverse-index exists. O(G×N) walk is acceptable for single-call demo (P8 B + P12 B).

**Consequences:** Row §E gains explicit endpoint-resolution paragraph for Edge/HyperEdge/MetaEdge/MetaHyperEdge materialise. Helper: `mindsos_instances/_resolve.py` walks metagraph.graphs for each override ID.

### P59 — Cascade-observer doesn't route through SubGraphInstance's referenced nodes/edges. **Pick: A.**

A. **Extend §F step 2: callback also queries SubGraphInstances whose `node_ids`/`edge_ids` contain the removed id; cascade-removes them.**
B. On every remove event, re-check P20 A invariant on each SubGraphInstance.
C. Skip cascade for SubGraphInstance; caller responsibility.

**Consequences:** §F step 2 amended with the additional SubGraphInstance routing. Test category: "removing a Node referenced by a SubGraphInstance.node_ids cascade-removes that SubGraphInstance" + symmetric for edges.

### P60 — `MetaHyperEdgeInstance.member_graph_ids` allow-list name doesn't match Core's `MetaHyperEdge.graph_ids`. **Pick: A.**

A. **Rename allow-list key to `graph_ids` (match Core).**
B. Keep `member_graph_ids`; rename in materialise merge.
C. Rename Core's field (Phase 05a Core surface change).

**Audit:** `MetaHyperEdge.graph_ids: FrozenSet[str]` (`metagraph.py:188`). EdgeInstance uses `source_id`/`target_id` (no Edge.source_id field exists; these are ID-references to the override Node — distinct name OK). MetaEdgeInstance uses `source_graph_id`/`target_graph_id` (matches Core's field names). MetaHyperEdgeInstance is the outlier.

**Consequences:** Row §B table corrected — `MetaHyperEdgeInstance: user properties + label + graph_ids (set)`.

### P61 — `CompositeInstance.bundle_overrides` validation scope undefined. **Pick: A.**

A. **Add `composite` scope to `validate_user_properties` calls (zero LOC Phase 04 change — `scope` is a free-form str per `validation.py:145`). Bundle_overrides validates against reserved-key + ov__ prefix rules.**
B. Skip validation; application-specific bag.
C. Defer scope decision to Phase 07.

**Audit:** `validate_user_properties(scope: str = "property")` — scope is a free-form string used only in error messages (`validation.py:142-190`). Adding "composite" requires no Phase 04 surface change.

**Consequences:** CompositeInstance `bundle_overrides` setter routes through `validate_user_properties(props, scope="composite")`. Reserved-key + ov__ prefix protection applies.

### P62 — Package integration unmentioned in row. **Pick: A.**

A. **Add §K "Package integration" checklist: (1) pyproject.toml packages entry; (2) compose.yml mount/build; (3) doctor import-check + version-string parity; (4) version bumps 4 sites.**
B. Trust implementation chat.
C. Defer doctor check to Phase 07.

**Consequences:** Row gains §K. Implementation includes pyproject.toml + doctor.py extension + version-string-parity test.

### P63 — `dataclasses.asdict` on materialised HyperEdge/MetaHyperEdge produces non-deterministic JSON. **Pick: A.**

A. **Composite materialise JSON path wraps `asdict` output with canonicalize (P34 B) for stable JSON.**
B. Weaken golden-output assertions to sorted-key comparisons.
C. Hand-rolled per-subclass serializers.

**Consequences:** `mindsos_instances/materialise.py` composite JSON output runs through canonicalize. Canonicalize utility serves dual purpose: ID-derivation-time validation (P34 B original use) + JSON-output stability (this use).

### P64 — Override validation routing (structural-allow-list vs user-property) unspecified. **Pick: A.**

A. **Spec inline in §B: override-dict split at validation time. Bucket 1 = keys in subclass structural allow-list → typed-validated. Bucket 2 = everything else → `validate_user_properties(scope=<KIND>)`. A key in `RESERVED_PROPERTY_KEYS` not in bucket 1 raises `OverrideScopeError`.**
B. Abandon structural overrides; revert to user-properties only.
C. Per-subclass `STRUCTURAL_BYPASS_KEYS` parameter on `validate_user_properties` (Phase 04 surface change).

**Audit:** `RESERVED_PROPERTY_KEYS` (`validation.py:34-105`) contains `source_id`, `target_id`, `label`, `type_name`, `role`, `value`, `node_id`, `edge_id`, `graph_id`, `metagraph_id`, `instance_id`, `kind`, `type`, `uuid` — several appear in per-subclass allow-list per P36 A + P48 A. Bifurcation is necessary; routing is currently implicit.

**Consequences:** `mindsos_instances/models/_overrides.py` ships the bifurcation: `split_overrides(overrides, structural_keys) -> (structural_bucket, property_bucket)`; structural-bucket goes through typed contract per key; property-bucket goes through `validate_user_properties(scope=KIND)`. Phase 04's `validate_user_properties` signature unchanged.

### P65 — Observer-callback exception semantics unspecified. **Pick: A.**

A. **Observer exceptions abort the remove atomically. State stays consistent. Implementation: precheck-observer-pass before mutation OR try/except with rollback.**
B. Catch + log; Core remove succeeds regardless.
C. Fail-fast: exception propagates after partial mutation.

**Consequences:** Each Core `remove_*` method wraps its mutation in a structure that allows rollback on observer exception. Simplest pattern: snapshot referenced dicts → mutate → call observers → on exception, restore from snapshot + re-raise. ~10 LOC per remove method; ~6 remove methods affected.

---

## §2 Pick summary table

| ID | Pick | Row text change |
|---|---|---|
| P45 | B | §G collapses; only `__init__.py:54` ADR-ref-fix survives |
| P46 | C | §B subclass gains `_instance_seq`; §C registry gains `_next_seq_for` |
| P47 | C | §B universally-forbidden list trimmed |
| P48 | A | §B table: `label` added to 4 subclasses |
| P49 | B+A | Core observer plumbing only; instances ships `attach_registry(mg)`; Risk text rewritten |
| P50 | A | `CompositeInstance.__init__` requires `metagraph_id` |
| P51 | A | §E gains SubGraphInstance copy spec |
| P52 | A | §Tests strikes teardown category |
| P53 | A | §H gains exit-code table |
| P54 | B | §E GraphInstance = full deep-copy clone |
| P55 | A | §C add_member registry-membership check |
| P56 | A | §F step 2 includes mg.identity.unregister |
| P57 | A | §B set-typed structural fields coerce list→set |
| P58 | A | §E gains endpoint-resolution paragraph + `_resolve.py` helper |
| P59 | A | §F step 2 routes SubGraphInstance referenced-element removal |
| P60 | A | §B `MetaHyperEdgeInstance: ...graph_ids (set)` |
| P61 | A | bundle_overrides uses `scope="composite"` |
| P62 | A | New §K Package integration |
| P63 | A | Composite JSON output wraps asdict with canonicalize |
| P64 | A | §B bifurcated routing spec |
| P65 | A | §F atomic-rollback semantics on Core remove methods |

---

## §3 Implementation bug ledger

### P66 — Late-added graphs miss per-Graph observer subscription. **Pick: A.**

Surfaced during the test run for `tests/phase_06/test_cascade_observer.py` — 9 cascade tests failed because `ElementRegistry.__init__` subscribes to `metagraph.graphs.values()` snapshot at attach time. Any graph added via `Metagraph.add_graph(g)` AFTER `attach_registry(mg)` would never get a per-Graph `register_remove_observer` subscription wired, so `g.remove_node(...)` fired no cascade and orphaned instances survived.

A. **Add a `_graph_added_observers` plumbing list on `Metagraph`; fire from `add_graph` after the unification step; `ElementRegistry` subscribes via `Metagraph.register_graph_added_observer(self._subscribe_to_graph)` on attach.**
B. Resubscribe every call to `attach_registry` (idempotent re-walk of `metagraph.graphs`).
C. Document the limitation; require callers to attach AFTER all graphs are added.

**Pick: A.** Cleanest; mirrors the `_remove_observers` pattern; closes the regression with ~15 LOC in Core + ~3 in registry. B is fragile (re-walking on every attach call is wasteful and only fires when the caller remembers to re-call). C is a UX trap.

**Consequences:** `Metagraph` gains `_graph_added_observers: List[Callable[[Graph], None]]` + `register_graph_added_observer(cb)`. `Metagraph.add_graph` fires every registered callback after the unification step. `ElementRegistry.__init__` subscribes to it. Row §F implicitly extended; `mg_with_graph` fixture pattern (attach first → add graph) now works correctly.

---

### Implementation snapshot — 2026-05-11

* `phase-06` branch off `main` at `6758bb6` (Phase 05d squash-merge).
* Sandbox tests: **90 passed + 12 skipped** in `tests/phase_06/` (CLI subprocess tests skip when Python < 3.11; tester picks them up in-container per row §Tests).
* Cross-phase regression check: **821 passed** in `tests/phase_02/03/04/05a/05b/05c/05d/06/` after excluding pre-existing sandbox CLI subprocess failures (Python 3.10 missing `tomllib` — unrelated to Phase 06).
* Projected in-container baseline ≈ **1250** (1013 in 05d + ~240 new in 06 + handful of newly-enabled CLI tests).

---

## §4 Tester confirmation

*(Populated post-tester-baseline.)*
