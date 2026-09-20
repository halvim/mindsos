---
title: L2 Knowledge internals
tag: shipped
teaser: Metagraph-of-role-graphs, importers, and Global/Local architecture.
source: mindsos_knowledge_developer_guide.md + mindsos_knowledge_architecture.md
next: dev/internals/capacity.md
verified_at: c8f26d9
---

# L2 Knowledge internals

!!! note "Scope: the shape is current; the module map was re-measured 2026-09-20"
    The architecture — one Global metagraph plus per-user Locals, schemas per role, proxies for Local→Global endpoints — still holds. The Phase-13 module map did not: `views.py`, `proxies.py` and `versions.py` no longer exist as modules, and the importers moved out of this package. Both were replaced below. The closed role-set has grown since Phase 13 and its size is guarded, not stated here — see [role-graphs.md](../../concepts/role-graphs.md); `memories` was renamed **`episodic_memories`** (Phase 39, ADR-0044 §am-3).

The Knowledge Layer wraps one **Global metagraph** (ontology, lexicon, concepts, alignments) plus **N Local metagraphs**, one per user, that accumulate the user's private knowledge and episodic memories.

!!! info "Quick facts"
    - Layer: **L2 Knowledge**
    - Package: `mindsos_knowledge/`
    - Scope: 12 modules plus `schemas/` (measured 2026-09-20)
    - Tests: under `tests/phase_*` (e.g. `tests/phase_14/test_knowledge_layer_init.py`); the unit-test directory this page once named was never in this repo
    - Invariants: I1–I5 (below)
    - Design reference: ADR-0143 (the write handle) + ADR-0150 (the role set)

## Overview

Knowledge Layer depends only on Core. Nothing inside this package may import from layer 3+.

The package is **in-memory first**: L2 builds and validates graphs in memory, and persistence is Core's (`mindsos_core/persistence/` — `graph_repository.py`, `metagraph_repository.py`, `xref_repository.py`, `value_codec.py`, over FalkorDB per ADR-0121). Downstream code calls `GraphRepository.persist(...)` from Core; L2 does not persist for you.

## Architectural organization

Module list measured 2026-09-20 (`ls mindsos_knowledge`), rather than a
hand-maintained map that rots on the next ship:

```
identifiers.py   ── stable-IRI toolkit, role constants, REF_TYPES (a leaf)
exceptions.py    ── the error hierarchy (a leaf)
types.py         ── SessionProtocol, the structural shape L2 accepts
schemas/         ── one schema builder per named role + schema_for_role dispatch
bootstrap.py     ── metagraph constructors and role-graph ensure
metagraph_view.py── the read surface (MetagraphView)
validators.py    ── semantic validators + _VALIDATORS_BY_ROLE
write_handle.py  ── KLWriteHandle, the write path L3 capacities use (ADR-0143)
knowledge_layer.py ── the façade (writeable(), views, bootstrap)
policies.py / prompts.py / learned_parameters_snapshot.py ── role-specific surfaces
```

`identifiers.py` and `exceptions.py` are leaves; `knowledge_layer.py` depends on
everything else. **Importers are not in this package** — the DOLCE, OEWN and
FrameNet importers live at `mindsos_admin/importers/`.

### The dual metagraph model

Two Python `Metagraph` instances represent the whole system:

- `self._global: Metagraph` — created at `KnowledgeLayer.__init__`.
- `self._locals: Dict[user_id, Metagraph]` — lazy per-user.

Every read path goes through a `MetagraphView(metagraph)` which enforces the
active-pointer convention. Writes go through the façade's `writeable(session,
role, scope)` → `KLWriteHandle` (ADR-0143); the handle validates and reaches L1
for the mutation itself.

The only place a graph crosses boundaries is the **proxy pattern**: a Local edge
wanting a Global endpoint creates a proxy node inside Local, carrying
`ref:global_<role>` + `ref_type=PROXY`, filtered out of `get_node()`.

## Key invariants

These are the ref-shape rules that still have an enforcement site in this
package. (The Phase-13 list also named `_check_global_target_exists`,
`set_active`, `_ensure_map` and a proxy dedupe cache; none of those symbols is
in the tree any more, and the invariants that rested on them were dropped rather
than restated from memory.)

**I1.** `ref_to_global` and `ref_type` are both-or-neither. A Local node either
is standalone (neither set) or specialises something in Global (both set). The
XOR state is malformed and raises `RefTypeError`.

**I2.** `ref_to_global` is a version-qualified IRI — bare fragments
(`PhysicalObject`) are not allowed. Use the stable-IRI builders;
`is_version_qualified_iri` in `identifiers.py` is the check.

**I3.** `ref_type` is drawn from `REF_TYPES` (`identifiers.py`). Extend that set
and document the semantics rather than passing an arbitrary string.

**I4.** An alignment graph's role is `alignment_role(role_a, role_b)` for exactly
one sorted pair (`identifiers.py`, checked in `validators.py`).

**I5.** A metagraph keeps its active-graph pointers in
`_kl_active_graph_ids`, which lives on Core's `Metagraph`
(`mindsos_core/models/metagraph.py`), not here.

## Importers — not in this package

The importers moved to `mindsos_admin/importers/` (`dolce.py`, `oewn.py`,
`framenet.py`). The `Importer` pipeline, its provenance stamping and the
alignment build live there; read that package rather than this page for their
current shape. `AlignmentsImporter` was scheduled and never built — see
`docs/concepts/admin-global-shipping.md`.

## Testing philosophy

- **Module-level** — `test_identifiers.py`, `test_bootstrap.py`, `test_views_versions_proxies.py`. Fast, pure, no fixtures beyond a minimal Metagraph.
- **Importer-level** — `test_importers.py`. One test per OWL construct class for `DolceImporter`; structural + provenance + version-qualification tests for each of the four importers.
- **Facade-level** — `test_knowledge_layer.py`. Invariant enforcement, proxy lifecycle, `step()`, version activation.

Total: 73 tests, ~200 ms runtime. Target stays under 500 ms.

## Common pitfalls

### Registering a version graph without activating it

`register_version_graph(..., activate=False)` adds the graph to the metagraph but does **not** update the active pointer. `active_graph(role)` returns `None` until you either activate this graph or another.

### Lazy Local creation order

Calling `kl.local_view("alice")` creates alice's metagraph if it didn't exist. Calling `kl.add_local_node("alice", ...)` also does. Neither populates role graphs — those are created by `ensure_role_graph` on first write.

### Proxy cache and test isolation

`proxies._proxy_cache` is module-level and survives between tests. Test setup should call `reset_cache()` to avoid cross-test pollution.

### Duplicate OEWN entries

OEWN ships occasional duplicate `LexicalEntry` headwords across dialects. The OEWN importer dedupes by `(lemma, pos)` in `lemmas_seen`.

### Alignment anchors are stored inside the alignment graph, not inside the source role

`anchor:lexicon:oewn-2024:sense:dog__n__1` lives inside the `alignment:concepts<->lexicon` graph — not inside the lexicon graph.

## Validator surface

Phase 36 added `mindsos_knowledge/validators.py` per ADR-0139 (hybrid invariant home — L1 structural, KL semantic). The module ships 5 pure-function validators + `ValidationResult` + `_VALIDATORS_BY_ROLE` per-role adapter registry.

### Validators

Each returns `ValidationResult` (`ok: bool` + `violation: Optional[str]`; frozen). Construct via `ValidationResult.success()` / `ValidationResult.violated(reason)`.

| Function | Checks |
|---|---|
| `validate_role_routing(role, scope, mg)` | `role` is a registered role-graph in `mg`. |
| `validate_local_to_global_ref(target_role, target_iri, mg)` | `target_iri` exists in the active version-graph of `target_role` (Global). |
| `validate_alignment_role_naming(role)` | `role` matches canonical `alignment:<a><->b>` sorted form. |
| `validate_ref_type(ref_type, target_role)` | `ref_type` ∈ `REF_TYPES`. |
| `validate_promotion_candidate(local_iri, mg)` | `local_iri` is a Local draft, not already PROMOTED, not deprecated. |

All validators are idempotent and side-effect-free.

### Composition contract

L3 write capacities call semantic validators as **preconditions** before invoking `handle.write_and_validate(...)`. Two equivalent styles:

**Canonical — `handle.validate_node(value, type_)` composite.** Wired for roles with a registered adapter in `_VALIDATORS_BY_ROLE` (Phase 36: `episodic_memories` + `problem-trace`; role renamed from `memories` at Phase 39). Returns `ValidationResult`; capacity body raises `SemanticValidationError(result)` on `not result.ok`. The composite owns metagraph routing internally and is the single place the role→chain mapping lives.

```python
vr = handle.validate_node(value=record["value"], type_="Memory")
if not vr.ok:
    raise SemanticValidationError(vr)
return handle.write_and_validate(value=..., type_="Memory", ...)
```

**Fallback — direct validator calls** per ADR-0139 §Capacity-contract. Valid for one-off checks or roles without a registered composite. Capacity body composes validators with explicit args from handle state.

```python
vr = validate_role_routing(role=handle.role, scope=handle.scope, mg=handle.metagraph())
if not vr.ok:
    raise SemanticValidationError(vr)
```

Prefer the composite when one exists for the role; the role→chain mapping in `_VALIDATORS_BY_ROLE` keeps capacity bodies short.

### Per-flow adapter extension

`_VALIDATORS_BY_ROLE` grows per-flow per ADR-0139 §amendment-1 clause 3 (mirroring ADR-0147 §amendment-1 clause 3 for L3 capacities). Phase 36 ships 2 adapter entries — one per shipped write capacity. Future L3 write capacities (`capacity:promote:pipeline` etc.) add their role's adapter alongside the capacity, with the role-appropriate validator chain.

The `KLWriteHandle.validate_xref` composite is **deferred** at Phase 36 — no XRef-writing capacity exists yet; the composite wires alongside the first one. The underlying validators (`validate_local_to_global_ref`, `validate_ref_type`) ship at Phase 36 as pure functions and may be called directly via the fallback style.

### Bypass discipline

ADR-0139 §Decision: "L3 capacities that skip validators are a code-review failure, not a runtime error." Bypass is sociologically enforced via `docs/dev/review-checklist.md` §4 "Capacity preconditions call semantic validators (ADR-0139)". Reviewers reject write-capacity PRs that call `handle.write_and_validate(...)` (or `handle.graph().add_node(...)`) without a preceding semantic-validator check.

---

**Next:** [L3 Capacity internals](capacity.md) — fixed techniques, reactive/resident modes, and retrieval.
