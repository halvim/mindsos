# Phase 06 Design Log

**Status:** Row locked 2026-05-11 across 6 reanalysis rounds.
**Branch (implementation):** `phase-06` off `origin/main`.
**Tag on confirm:** `phase-06-confirmed`.
**Row text:** `confirmation_docs/PHASE_MAP.md` §5 Phase 06.
**Implementation log target:** `confirmation_docs/PHASE_06_IMPLEMENTATION_LOG.md` (round 7+ if implementation chat surfaces contradictions; expected per 05d precedent).

This log is the canonical record of *what was decided and why* during the design chat. Implementation chat reads the row text first; this log when "why was this picked?" needs answering.

User overrides flagged inline; otherwise picks are author-chosen with rationale.

---

## §0 Cascade position

CASC-1 strict-sequential: `05a → 05b → 05c → 05d → 06`. Phase 05d shipped 2026-05-08 (tag `phase-05d-confirmed`; 1013 + 2 skipped in-container). Phase 06 unblocked.

Open question carried forward from 05d round-7 P33 A: instance-graph role mutability (file at `_source_backup/root/mindsos_future_plans.md` "Instance-graph role mutability across `mindsos_instances` vocab consumption"). **Resolved in this chat via M6 A + P1 A: immutable.**

---

## §1 Meta-plan (M-series)

### M1 — Round-count target. **Pick: A.**

A. Pushback well dry (05d precedent: 6 design rounds + 7 in implementation).
B. Hard cap at 4 rounds.
C. 6 rounds + force-stop.

Rationale: phase scope and concern surface project >3 rounds anyway; arbitrary caps truncate productive pushback. Round count is not the target; "pushback well dry" is.

### M2 — ADR re-litigation scope. **Pick: C.**

A. All five ADRs locked.
B. All five amendable inline (05d P42 C precedent).
C. **Mixed — 0132 locked; 0015/0019/0025/0026 amendable.**

Rationale: ADR-0132 locked the package boundary at L1 redesign (M7 lock) and is structural — not the substance of this phase. ADRs 0015/0019/0025/0026 ship in this phase; pointer-line amendments per 05d's P42 C precedent are appropriate.

### M3 — Reading scope before round 1. **Pick: C.**

A. Full mandatory-read list (16 items).
B. Just-in-time per pushback.
C. **Top-5 critical reads first, then JIT.**

Rationale: top-5 (Phase 06 stub; future-work entry on role-mutability; ADRs 0015 / 0025 / 0132; PHASE_05d_IMPLEMENTATION_LOG) covers the highest-cost cross-cutting locks; JIT for the rest.

### M4 — CLI surface. **Pick: B → amended by P38 A.**

A. Library + tests only.
B. **Minimal CLI (instantiate / materialise / inspect).**
C. Full CRUD parity.

Original pick: minimal CLI. P38 A amended the verb shape to 4 combined verbs (`instantiate-node` / `-edge` / `-hyperedge` / `compose`) with `--materialise` flag; no separate `materialise` verb.

### M5 — Speculative-feature guard. **Pick: C.**

A. Every feature must have named Phase 07–17 caller.
B. Accept "designed for future L2/L4 consumer" if ADR-forced.
C. **Hybrid — concrete callers preferred; ADR-forced features need a one-line justification.**

Rationale: A is too tight given the role-mutability open question; B is too loose. C is the discipline 05d enforced de facto.

### M6 — Role-mutability resolution lane. **Pick: A with default (a) immutable.**

A. **Treat as M-series — pick default before round 1, only change if P-pushback unseats.**
B. Treat as P1 — engage on merits.

Rationale: asymmetric-cost analysis (option (a) is ~0 LOC + zero state churn; (b) introduces silent-vocab-violation; (c) bumps metagraph state file v=4→v=5) favors (a) overwhelmingly. Making (a) the default forces burden-of-proof onto (b)/(c) advocates. No use case for (b)/(c) surfaced through six rounds. **(a) held.**

---

## §2 Round 1 (P1–P9)

### P1 — Ratify M6 A default (immutable role). **Pick: A.**

A. **Lock (a) immutable — instance-graphs propagate `Graph.role` read-only.**
B. Defer.
C. Re-open with all three options.

Rationale: M6 A already settled; P1 is the row-text ratification. Burden-of-proof on (b)/(c) unfilled.

### P2 — ADR-0132 "move from Core" is false. **Pick: A.**

A. **Amend ADR-0132 inline; strike "move" framing; no re-export shim; no factory wrapper.**
B. Keep ADR-0132 as-is and ship dead-code shim.
C. Hybrid.

Rationale: audit of `mindsos_core/models/` confirms no `instance.py`; `mindsos_core/__init__.py:54` is a deferral comment, not active code. ADR-0132's "move" framing was written assuming pre-redesign Core had instancing; current Core does not. Ship fresh; amend ADR inline.

### P3 — Speculative-API audit on 8 subclasses. **Pick: D, amended by P13 B.**

A. Ship all 8.
B. Ship Node+Edge+Composite only (3).
C. Ship Node+Edge+HyperEdge+Composite (4).
D. **Ship all 8; CLI for Node/Edge/HyperEdge/Composite only; 5 subclasses test-only.**

Original pick: D. P13 B subsequently locked SubGraphInstance as `(graph_id, node_ids: set[str], edge_ids: set[str])` triple — concrete semantic that satisfies M5 C with library-level test coverage. Final: 8 subclasses ship; 4 in CLI.

### P4 — Persistence-side classes (ElementRegistry / InstanceRepository / InstanceLoader) — 06 vs 07. **Pick: B.**

A. Ship all 3 in P06.
B. **`ElementRegistry` in-memory in P06; `InstanceRepository` + `InstanceLoader` deferred to Phase 07.**
C. Defer all 3 to Phase 07.

Rationale: ElementRegistry is in-memory and enables materialisation/composite tests without persistence; the repository/loader pair is persistence-shaped and belongs with Phase 07's W1–W6 mitigations.

### P5 — `MetagraphLoader.register_attach_handler` extension point — 06 vs 08. **Pick: B.**

A. Ship in Phase 06.
B. **Defer to Phase 08.**
C. Stub in 06; wire in 08.

Rationale: the extension point's caller (`MetagraphLoader`) doesn't exist until Phase 08. Defer. ADR-0132 amendment in row.

### P6 — Materialisation return type & ID determinism. **Pick: A, amended by P18 A.**

A. **Type mapping pinned + fresh UUIDs per call.** Specifically (under P13 B + P18 A): NodeInstance→Node, EdgeInstance→Edge, HyperEdgeInstance→HyperEdge, SubGraphInstance→Graph (fresh, containing materialised copies of `node_ids`/`edge_ids`), GraphInstance→Graph, MetaEdgeInstance→MetaEdge, MetaHyperEdgeInstance→MetaHyperEdge, CompositeInstance→`dict[str, Core-object | dict]` (tree).
B. UUID5 deterministic IDs.
C. IdStrategy-delegated.

Rationale: ADR-0019's "many cheap materialisations" intent. Fresh IDs prevent attach-collisions on repeated materialisation. Determinism is structural (property-bag merge), not identity-based.

### P7 — CLI verb selection. **Pick: B → amended by P12 → amended by P38 A.**

A. 4 verbs (no override mutation, no materialise).
B. **6 verbs (`instantiate-*` × 3 + `compose` + `set-override` + `materialise`).**
C. 8 verbs.
D. No CLI.

Original pick: B (6 verbs). P12 B (CLI single-call demo) collapsed `set-override` into repeatable `--override key=val` flag → 5 verbs. P38 A then collapsed `materialise` into a `--materialise` flag on each instantiate/compose verb → **4 verbs**. Final shape locked under P38 A.

### P8 — State-file impact + test scope. **Pick: B.**

A. Metagraph state file v=3 → v=4.
B. **No state-file change; in-memory only; persistence to Phase 07.**
C. Separate `instances-*.json` state file.

Rationale: aligns with P4 B (InstanceRepository deferred) and P5 B (loader hook deferred). Phase 06 ships pure in-memory vocabulary + materialisation. "Instances vanish between CLI calls" cost is acceptable per P12 B single-call demo intent.

### P9 — `propagate=True` future-work hook on `CompositeInstance`. **Pick: A.**

A. **No constructor parameter.**
B. Ship parameter with `NotImplementedError`.
C. Implement.

Rationale: M5 C requires concrete caller or ADR-forced. Neither holds. ADR-0026 deferral text preserved.

---

## §3 Round 2 (P10–P19)

### P10 — Where instances live. **Pick: B.**

A. `Metagraph.element_instances` + `composite_instances` direct attributes.
B. **`ElementRegistry` as standalone class; `Metagraph` holds `element_registry: ElementRegistry`.**
C. Module-level singleton.

Rationale: ADR-0132 names `ElementRegistry` — honor the class. Cross-metagraph composites blocked (locked in P43 C).

### P11 — Instance ID generation source. **Pick: A.**

A. **Shared `IdentityRegistry` from metagraph; under `UUID5FromContentStrategy`, derive from `(template_id, overrides_hash, "instance")` salt.**
B. Separate registry.
C. Hardcoded UUID4.

Rationale: matches all existing identity patterns. Collision space negligible. Canonicalization for the hash locked in P34 B.

### P12 — CLI cross-invocation state semantics. **Pick: B.**

A. JSON pipeline.
B. **Single-call demonstration only; multi-step composition is library-only.**
C. Per-session temp file.

Rationale: matches P8 B (no state file) intent; recipes are one-liners. Amends P7 B: `set-override` becomes `--override` flag, not a verb (5 verbs).

### P13 — `SubGraphInstance` referent. **User pick: B.**

A. Defer.
B. **Define as `(graph_id, node_ids: set[str], edge_ids: set[str])` triple inside one Graph; materialise produces fresh `Graph` containing copies of listed nodes/edges.**
C. Alias for GraphInstance with node-removal.

User override: the user picked B (over the author's recommended A — defer). Result: all 8 ADR-0132 subclasses ship; SubGraphInstance has a concrete semantic.

### P14 — Override scope. **Pick: A → amended by P29 C.**

A. **User properties only; structural fields rejected.**
B. Per-type allow-list.
C. Anything except identity.

Original pick: A. P29 C subsequently amended to "user properties + named structural fields per subclass" after user clarification in P27 ("X could have different properties or edges if needed"). P14 A's intent (identity fields forbidden) is preserved as a sub-rule under P29 C's allow-list.

### P15 — MetaEdge / MetaHyperEdge endpoint override. **Pick: B → absorbed into P29 C.**

A. Forbid.
B. **Allow.**
C. Allow with eager validation.

Original pick: B (carve-out from P14 A). P29 C subsequently absorbed P15 B as one of the per-subclass structural allow-list entries — endpoint override is no longer a "carve-out", it's the rule.

### P16 — Materialise × schema validation. **Pick: A.**

A. **Materialise does NOT validate.** Validation is attach-time concern.
B. Validate if schema-bound.
C. `--validate` opt-in.

Rationale: separation of concerns. Materialisation produces objects; attach (Phase 07) validates + persists + registers.

### P17 — `ov__` two-scope validation. **Pick: A.**

A. **Override keys validated against user-property rules in-memory; `ov__` prefix is serialization-only (Phase 07).**
B. Defer to Phase 07.
C. Allow any in-memory; reject only at serialize.

Rationale: clean separation. In-memory keys are normal user-property keys. RESERVED_PROPERTY_PREFIXES already blocks `ov__` at user-property scope — parity for override keys.

### P18 — Composite-nesting materialisation. **Pick: A.**

A. **Tree representation — `dict[str, Core-object | dict]`** (recursive).
B. Flat with dotted keys.
C. Dict + separate tree-description.

Rationale: structure preserved. Consumer flattens if needed; can't reconstruct from B/C without convention. Amends P6 A.

### P19 — Stale ADR references. **Pick: A.**

A. **Fix `__init__.py:54` to ADR-0015 (was ADR-0024 — wrong); flip ADR-0037 Proposed → Superseded.**
B. Leave both.
C. Fix __init__.py; defer ADR-0037.

Rationale: small fixes; clean ADR graph entering Phase 07-17. Status flips are routine (different from inline-amendment-defer).

---

## §4 Round 3 (P20–P28)

### P20 — SubGraphInstance edge-validity invariant. **Pick: A.**

A. **Strict: every edge endpoint must be in `node_ids`; HyperEdge members must all be in `node_ids`. Enforced at construction (`SubGraphInvariantError`).**
B. Lenient (silent drop).
C. Lenient + warning.

Rationale: failure at construction, not materialisation. Matches Phase 03's invariant pattern (HyperEdge rejects empty member set).

### P21 — GraphInstance + SubGraphInstance override scope. **Pick: A → amended by P29 C.**

A. **Both ship with empty override scope.**
B. Allow node_ids/edge_ids overrides on SubGraphInstance.
C. Allow + defer GraphInstance.

Original pick: A. P29 C amended: SubGraphInstance gains `node_ids`/`edge_ids` structural overrides per the per-subclass allow-list. GraphInstance stays empty-scope (no structural override surface in Phase 06; user property bag is Phase 10).

### P22 — P15 B carve-out documentation. **Pick: A → collapsed under P29 C.**

A. **Document carve-out explicitly.**
B. Reverse P15 B.
C. Generalize.

Original pick: A. P29 C collapsed P22 entirely — endpoint override is no longer a "carve-out", it's a named structural-field-allow-list entry.

### P23 — Template reference: ID or object. **Pick: A.**

A. **By ID — `template_id: str`; materialise reads metagraph registry. Signature: `instance.materialise(metagraph)`.**
B. By object reference.
C. Both.

Rationale: matches existing identity patterns. Serialization trivial. Reload reconstructs from ID.

### P24 — Template removal handling. **Original pick: A. User override: B (with admin-release framing).**

A. Hard fail at materialise.
B. **Cascade remove on hard-delete.** (User pick.)
C. Refuse remove.
D. Soft-flag.

**User restatement of definition:** "Instances are live — they represent the current state of components. They shouldn't exist without a real component reference. If a component is deleted, instances delete at the same time. This is not practical at runtime — components are only deleted by admin before updates."

**Design alignment check:** matches ADR-0015 (instance ↔ template hard reference); matches L0 server pivot (admin-curated Globals via release boundary, RELEASE_SHIP_LOCK semantics); matches ADR-0019 (instance ≠ materialised object). Phase 10 soft-delete is orthogonal (P32 A).

**Implementation:** observer hook in `mindsos_core` (P31 A) so `Graph.remove_node`/`remove_edge`/`remove_hyperedge` + `Metagraph.remove_graph`/`remove_metaedge`/`remove_metahyperedge` cascade into `element_registry`. Recursive cascade through composites (P44 A).

### P25 — Composite cycle prevention. **Pick: A.**

A. **Detect at compose-time** — `add_member` walks reachable composites for self.
B. Detect at materialise.
C. No detection.

Rationale: cycle is structurally meaningless. Compose-time check O(reachable composites) — small.

### P26 — `kind` discriminator. **Pick: C.**

A. Per-instance `kind: str` field.
B. `type(instance).__name__`.
C. **Class-level constant — `class NodeInstance: KIND = "node"`.**

Rationale: no per-instance memory. Refactor-safe (rename class without changing constant).

### P27 — Library mutation API. **Original pick: A. User restatement confirmed alignment.**

A. **Library `set_override` / `clear_override` available; instances mutable.**
B. Constructor-only.
C. Functional `with_overrides`.

**User restatement:** "A component instance points to a real component. It's a reference that becomes working memory for the system to identify what component a task needs. Overriding never writes back to the original. If X is an instance of Y and the task needs to change something in X, X doesn't need to be exactly Y — it can have different properties or edges if needed."

**Design alignment check:** matches ADR-0015 (templates pristine); ADR-0026 (composite overrides don't propagate); ADR-0019 (fresh Core object). The "different properties or edges" wording surfaced P29 below — the mechanism question for structural deviation.

### P28 — Materialise JSON output. **Pick: B.**

A. Minimal shape (kind + id + metagraph_id + properties).
B. **Full Core-object JSON dump** (`dataclasses.asdict`-style; all public dataclass fields).
C. Defer JSON spec to Phase 07; repr() now.

Rationale: Phase 06 must produce parseable output. Shape = whatever the materialised Core object's public dataclass fields are. CompositeInstance output: `{"kind": "composite", "id": "...", "bundle_overrides": {...}, "members": {member_id: <recursive>}}` per P18 A + P39 A.

---

## §5 Round 4 (P29–P35) — cascade from user P27 clarification

### P29 — Structural deviation mechanism. **Pick: C.**

A. Composite-bundling only (single-instance overrides are property-bag).
B. Universal override dict.
C. **Hybrid — single-instance overrides cover property-bag + named structural fields per subclass.**

Rationale: matches user's "properties or edges" wording most directly. Simple deviations stay single-instance; complex multi-element deviations route through composite bundling.

**Cascades:**
- P14 A amended to "user properties + named structural fields per subclass" (P36 A enumerates).
- P15 B absorbed.
- P22 collapses.
- P21 A amended (SubGraphInstance gains structural overrides; GraphInstance stays empty-scope).

### P30 — Composite materialise combination algorithm. **Pick: A.**

A. **Caller combines — materialise returns dict per P18 A; no auto-combine.**
B. Materialise auto-combines for recognized patterns.
C. Library helper for combining.

Rationale: ADR-0026 (no propagation) + ADR-0019 (caller decides attachment) → combination is consumer concern (L4/L5 knows the context).

**Phase 06 test note:** tests verify per-member materialise correctness in isolation; no combined-scenario test in Phase 06 (those land when a combine consumer ships).

### P31 — Cascade-delete observer implementation. **Pick: A.**

A. **Observer hook in `mindsos_core`** — `Graph.register_remove_observer(callback)` + `Metagraph.register_remove_observer(callback)`; `mindsos_instances` subscribes per metagraph.
B. Direct coupling (monkey-patch).
C. Defer cascade-delete to Phase 07/08.
D. Direct import (Core → instances).

Rationale: observer pattern matches P5 B precedent for extension points. Unlike P5 B's MetagraphLoader hook, this one IS needed in Phase 06 (cascade is a Phase 06 invariant per user P24 framing).

ADR-0132 amendment: add the remove-observer hook to the "hooks Core gains" section alongside the deferred `register_attach_handler`.

### P32 — Cascade × Phase 10 soft-delete. **Pick: A.**

A. **Future-work; Phase 10 row decides.**
B. Pre-bind.
C. Lock hard-only forever.

### P33 — `type_name` override on Edge/HyperEdge/MetaEdge subclasses. **Pick: B.**

A. Allow; validate at attach.
B. **Forbid.** Type-name is "kind of relationship" identifier — overriding makes "X is an instance of Y" semantically empty.
C. Allow with eager validation.

Future-work entry: "Type-name override permission — revisit if L4/L5 surfaces a polymorphic-template use case."

### P34 — Override-hash canonicalization. **Pick: B.**

A. Hash dict directly.
B. **Canonicalize first** — sets→sorted lists; dicts→sorted-key JSON; recursive.
C. Defer canonicalization rule to Phase 07/09.

Rule lives at `mindsos_instances/utils/canonicalize.py` (~30 LOC + tests).

### P35 — ElementRegistry lifecycle. **Pick: A.**

A. **Python ownership — Metagraph owns element_registry; GC handles cleanup.**
B. Explicit `__del__`.
C. Defer to Phase 10.

---

## §6 Round 5 (P36–P40)

### P36 — Per-subclass structural allow-list enumeration. **Pick: A.**

A. **The list (final):**
- **NodeInstance:** user properties only.
- **EdgeInstance:** user properties + `source_id`, `target_id`.
- **HyperEdgeInstance:** user properties + `member_ids` (set of node IDs).
- **SubGraphInstance:** `node_ids`, `edge_ids` only (Phase 03 Graph has no graph-level user property bag).
- **GraphInstance:** empty override scope (Graph has no structural override surface in Phase 06; user property bag is Phase 10).
- **MetaEdgeInstance:** user properties + `source_graph_id`, `target_graph_id`.
- **MetaHyperEdgeInstance:** user properties + `member_graph_ids` (set).
- **CompositeInstance:** bundle-level user properties only (member-list mutation via dedicated API per P37 A).

`type_name` excluded for Edge/HyperEdge/MetaEdge/MetaHyperEdge per P33 B. Identity fields (`id`, `template_id`, `kind`, `metagraph_id`, `source_id` where applicable) excluded universally.

B. Same as A but defer GraphInstance.
C. Reverse P1 A; allow role override.

Future-work entry: "GraphInstance override surface fills in when Phase 10 ships ADR-0130 graph property bag."

### P37 — Composite member-list semantics. **Pick: A.**

A. **Mutable list, duplicates allowed.** `compose.add_member(instance)` / `remove_member(instance_id, occurrence=0)` / `remove_all_members(instance_id)`; `members: list[ElementInstance | CompositeInstance]`.
B. Mutable set.
C. Ordered set.
D. Immutable.

Rationale: matches user's working-memory framing (task can reference same component twice with different roles). Cycle-detection (P25 A) per add.

### P38 — CLI workflow shape. **Pick: A.**

A. **Combined-verb mode — `--materialise` flag on each `instantiate-*` and `compose` verb; no separate `materialise` verb.** Final: 4 verbs.
B. Pipeline mode.
C. Both.

Amends P12: 4 verbs, not 5.

### P39 — Composite-level overrides in materialise JSON. **Pick: A.**

A. **Top-level `bundle_overrides` field on composite JSON output.**
B. Sentinel-key inside `members`.
C. Drop from output.

Final composite materialise JSON shape:
```
{
  "kind": "composite",
  "id": "...",
  "metagraph_id": "...",
  "bundle_overrides": {<dict>},
  "members": {member_id: <Core-object JSON or recursive composite JSON>}
}
```

### P40 — Materialise call signature. **Pick: A.**

A. **Instance-method: `instance.materialise(metagraph)`.**
B. Library function.
C. Registry method.

---

## §7 Round 6 (P41–P44) — final scan; well dried

### P41 — `compose` CLI argument shape. **Pick: A.**

A. **Inline JSON member-specs** — repeated `--member-spec '{"kind":"...","template_id":"...","overrides":{...}}'` flags; `--bundle-override key=val` repeated; `--materialise` flag.
B. Drop `compose` from CLI.
C. File-based.

Rationale: matches P8 B + P12 B (single-call honest). Recipes use bash heredocs for the JSON. Library stays primary surface.

### P42 — `--override key=val` value typing. **Pick: A.**

A. **JSON-fragment parsing** — `--override age=31` parses as JSON; strings need quoting (`--override name='"Alicia"'`); lists `--override member_ids='["N1","N2"]'`.
B. Heuristic typing.
C. String-only.
D. Typed flags.

Rationale: complete type coverage; one syntax for all types. Documented in recipes with examples.

### P43 — Cross-metagraph composite members. **Pick: C.**

A. Forbid.
B. Allow.
C. **Forbid in Phase 06 + future-work entry** for revisit when L4/L5 demonstrates a concrete use case.

Future-work entry: "Cross-metagraph composite members — revisit when L4/L5 demonstrates a task-composite spanning multiple metagraphs; likely requires multi-metagraph cascade-observer coordination."

### P44 — Recursive cascade through composites. **Pick: A.**

A. **Recursive — composite is removed too if any member is cascade-removed.**
B. Partial — composite stays with broken-member reference removed.
C. `dangling=True` flag.

Rationale: matches user's "live instances represent current state" framing recursively. Cascade depth bounded by composite-nesting depth (small).

Future-work entry under P32: "Soft-delete + cascade-through-composites — Phase 10 row picks partial-cascade vs. stay-alive behavior under deprecate."

---

## §8 Locked scope summary

**Package:** `mindsos_instances/` (new sibling package; ADR-0132 amended per P2 A — fresh creation, no re-export shim, no factory wrappers).

**Subclasses (8):** `NodeInstance`, `EdgeInstance`, `HyperEdgeInstance`, `SubGraphInstance` (P13 B triple), `GraphInstance` (empty scope), `MetaEdgeInstance`, `MetaHyperEdgeInstance`, `CompositeInstance`.

**Override scope:** per-subclass allow-list per P36 A (user properties + named structural fields; identity fields + `type_name` forbidden).

**Materialise:** `instance.materialise(metagraph) → fresh Core object`; CompositeInstance → tree `dict[str, Core-object | dict]` with `bundle_overrides` top-level field.

**Persistence:** in-memory only. `ElementRegistry` per-metagraph (`mg.element_registry`). `InstanceRepository` + `InstanceLoader` deferred to Phase 07. `MetagraphLoader.register_attach_handler` deferred to Phase 08.

**Cascade:** hard-remove on Graph/Metagraph removes cascades through `mindsos_core` remove-observer hook (P31 A) → `element_registry` → composite members (P44 A recursive).

**CLI (4 verbs):** `mindsos instances instantiate-node`, `instantiate-edge`, `instantiate-hyperedge`, `compose` — each with `--materialise` flag, `--override key=val` JSON-fragment values, `--metagraph MG` required.

**State files:** no change. Metagraph stays at v=3, schema stays at v=3, graph stays at v=4. Migration to come in Phase 07.

**ADR amendments (per M2 C):**
- **ADR-0132:** strike "move from Core" framing; remove re-export shim plan; remove factory wrapper plan; add remove-observer hook to "hooks Core gains" section; flip status Proposed → Accepted on ship.
- **ADR-0037:** flip Proposed → Superseded (status routine; per P19 A).
- **ADR-0015 / 0019 / 0025 / 0026:** pointer line per 05d P42 C precedent — "*See `confirmation_docs/PHASE_MAP.md` §5 for amendments through Phase 06.*"
- **__init__.py:54:** fix stale ADR-0024 reference to ADR-0015.

**Future-work entries filed:**
- (i) GraphInstance override surface fills in when Phase 10 ships ADR-0130 graph property bag.
- (ii) Composite combine helper — revisit when L4 ships and the combination contract is concrete.
- (iii) Cross-metagraph composite members — revisit when L4/L5 surfaces a concrete use case.
- (iv) Soft-delete × cascade-through-composites — Phase 10 row picks partial-cascade vs. stay-alive.
- (v) Type-name override permission — revisit if L4/L5 surfaces a polymorphic-template use case.

---

## §9 Implementation chat expectations (round 7+)

Per 05d precedent, the implementation chat may run a round-7 reanalysis pass. Permitted to reverse or refine any P-pick if the surface contradicts implementation. Expected vector: the cascade-observer pattern (P31 A) may surface a tighter shape once `Graph.remove_*` signatures are examined; the composite materialise tree (P18 A) may surface a tighter dict shape once the test harness writes its first composite test.

The 6 design rounds are not "the design is final and immutable" — they're "the row is locked enough that the implementation chat can start with confidence." If a P-pick fails to implement, file P31+ in the implementation log.
