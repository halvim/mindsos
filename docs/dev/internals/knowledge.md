---
title: L2 Knowledge internals
tag: shipped
teaser: Metagraph-of-role-graphs, importers, and Global/Local architecture.
source: mindsos_knowledge_developer_guide.md + mindsos_knowledge_architecture.md
next: dev/internals/capacity.md
---

# L2 Knowledge internals

!!! note "Scope: this page is a Phase-13-era module map"
    The architecture (Global metagraph + per-user Locals; the importer/schema/validator layering) is still accurate, but the **counts and role list below predate later phases**. The closed role-set is now **14** (not the original 8/9), the `memories` role was renamed **`episodic_memories`** (Phase 39, ADR-0044 §am-3), and the L2-write/`value_codec` surface is not covered here. For the current role-set see [role-graphs.md](../../concepts/role-graphs.md).

The Knowledge Layer wraps one **Global metagraph** (ontology, lexicon, concepts, alignments) plus **N Local metagraphs**, one per user, that accumulate the user's private knowledge and episodic memories.

!!! info "Quick facts"
    - Layer: **L2 Knowledge**
    - Package: `mindsos_knowledge/`
    - Scope: ~3.4k LOC across 20 files
    - Tests: `tests/unit/knowledge` (~73 tests, <500 ms)
    - Invariants: I1–I8 (section 5 below)
    - Design reference: `knowledge_layer_design.md` (§4)

## Overview

Knowledge Layer depends only on Core. Nothing inside this package may import from layer 3+.

The package is **in-memory first**. FalkorDB persistence adapters are not yet wired in. After an importer's `run()` returns, the `ImportResult.graph` is a populated in-memory Graph. Downstream code is responsible for calling `GraphRepository.persist(...)` from Core.

## Architectural organization

```
identifiers.py ──┐
                 ├──► schemas/           (per-role type catalogues)
exceptions.py ───┤
                 ├──► bootstrap.py       (metagraph constructors)
versions.py   ───┤         ▲
                 │         │
                 ├──► proxies.py
                 │         ▲
                 ├──► views.py           ◄── read surface
                 │         ▲
                 ├──► knowledge_layer.py ◄── façade
                 │
                 └──► importers/         (parse → build)
                        base.py
                        dolce.py   oewn.py   framenet.py   alignments.py
```

`identifiers.py` and `exceptions.py` are leaves. Everything depends on them. `knowledge_layer.py` depends on everything else. Importers are siblings of the façade.

### The dual metagraph model

Two Python `Metagraph` instances represent the whole system:

- `self._global: Metagraph` — created at `KnowledgeLayer.__init__`.
- `self._locals: Dict[user_id, Metagraph]` — lazy per-user.

Every read path goes through a `MetagraphView(metagraph)` which enforces the active-pointer convention. Every write path goes through the `KnowledgeLayer` façade, which enforces ref invariants.

The only place a graph crosses boundaries is via the **proxy pattern** in `proxies.py`: a Local edge wanting a Global endpoint creates a proxy node inside Local. Proxies carry `ref:global_<role>` + `ref_type=PROXY` and are filtered out of `get_node()`.

## Module map

| Module | LOC | Job | Depends on |
|---|---|---|---|
| `exceptions.py` | ~30 | Error hierarchy | — |
| `identifiers.py` | ~240 | Stable-IRI toolkit + role/ref-key constants | `exceptions` |
| `versions.py` | ~65 | Active-pointer helpers attached to Metagraph | Core, `exceptions` |
| `schemas/ontology.py` | ~130 | Full-OWL node/edge/hyperedge types | Core |
| `schemas/lexicon.py` | ~90 | OEWN types | Core |
| `schemas/concepts.py` | ~55 | FrameNet types | Core |
| `schemas/alignment.py` | ~60 | Alignment-anchor + mapping vocabulary | Core |
| `bootstrap.py` | ~160 | `create_global`, `create_local`, `ensure_role_graph`, slugify | Core, `identifiers`, `schemas` |
| `proxies.py` | ~120 | Proxy lifecycle + dedupe cache | Core, `bootstrap`, `identifiers` |
| `views.py` | ~230 | `MetagraphView` + `WalkResult` | Core, `identifiers`, `versions` |
| `knowledge_layer.py` | ~380 | `KnowledgeLayer` façade | everything above |
| `importers/base.py` | ~170 | `Importer` ABC + pipeline | Core, `exceptions`, `versions` |
| `importers/dolce.py` | ~900 | Full-OWL support | `base`, `schemas/ontology`, `identifiers`, `rdflib` |
| `importers/oewn.py` | ~440 | WN-LMF XML + mapping | `base`, `schemas/lexicon`, `identifiers` |
| `importers/framenet.py` | ~360 | FrameNet JSON + mapping | `base`, `schemas/concepts`, `identifiers` |
| `importers/alignments.py` | ~260 | Shared-anchor pattern | `base`, `schemas/alignment`, `identifiers` |

## Key invariants

These must hold at all times. Tests exist to prove each.

**I1.** A `ref_to_global` property on a Local node resolves to an existing node in the active Global graph for the same role. Enforced at write time by `_check_global_target_exists`.

**I2.** `ref_to_global` and `ref_type` are both-or-neither. A Local node either is standalone (neither set) or specialises something in Global (both set). The XOR state is malformed and raises `RefTypeError`.

**I3.** `ref_to_global` is a version-qualified IRI. Bare fragments (`PhysicalObject`) are not allowed. Use the stable-IRI builders. Enforcement at write time via `is_version_qualified_iri`.

**I4.** `ref_type` is drawn from `REF_TYPES`. If you need a new `ref_type`, extend `REF_TYPES` in `identifiers.py` and document the semantics. Do not silently accept arbitrary strings.

**I5.** Proxy node ids are unique per `(metagraph_id, role, global_target_id)`. Multiple Local edges to the same Global target share the same proxy. The dedupe cache is a performance helper; correctness is re-checked by scanning the graph on cache miss.

**I6.** An alignment graph's `role` equals `alignment_role(role_a, role_b)` for exactly one sorted pair. The `AlignmentsImporter` overrides `graph.role` to the canonical name during `_build`.

**I7.** A metagraph has at most one active graph per role at any time. `set_active` overwrites. To swap versions, activate the new graph — the old one stays archived.

**I8.** `Metagraph._kl_active_graph_ids` is a `Dict[str, str]` or absent. It is never a list, tuple, or None. `_ensure_map` enforces this.

## Importers

The `Importer` ABC is a six-stage pipeline:

1. `_parse(source)` — stage 1; subclass responsibility.
2. `_resolve_version(parsed)` — stage 2-adjacent; default reads `parsed.version`.
3. `_build(parsed, version, graph)` — stage 3; subclass responsibility.
4. Align (stage 4) — specific to `AlignmentsImporter`.
5. Persist (stage 5) — lives outside the importer.
6. Verify (stage 6) — lives outside the importer.

`run()` orchestrates. Version resolution can be overridden by the caller passing `version=`, which is the escape hatch for sources that don't self-declare.

Every node creation inside a subclass should call `_stamp_provenance` to attach `imported_from` and `imported_version` to the properties dict.

Each importer defines a `@dataclass` that isolates the on-disk format from the build stage, allowing unit tests to construct test data directly without touching XML/JSON/RDF.

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
