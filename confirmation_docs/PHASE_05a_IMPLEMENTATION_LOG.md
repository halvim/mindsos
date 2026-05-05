# Phase 05a — Implementation Log

> Companion to `confirmation_docs/PHASE_MAP.md` Phase 05a row.
> Written by the implementing chat (2026-05-05). Tester reads this
> along with the row before kicking off `confirm-phase --phase 05a`.

---

## 1. Charter

Goal: ship the slim port of `Metagraph` + `MetaEdge` + `MetaHyperEdge`
from the parent `mindsos_core/models/metagraph.py`, plus a new
`mindsos metagraph` CLI subapp, plus the cumulative graph state-file
v=3 → v=4 migration adding the `metagraph_name` back-pointer (B2),
plus the new `metagraph-<name>.json` v=1 state-file kind. Per CASC-1
strict-sequential cascade, this unblocks Phase 05b
(IntergraphEdge + MetagraphSchema + 4 *EdgeTypes) and Phase 05c
(IntergraphHyperEdge).

**Out of scope** (carry-forward — picked up in subsequent phases):

* `IntergraphEdge` (binary 1-1 cross-graph node↔node) — Phase 05b.
* `IntergraphHyperEdge` (n-ary, NOT 1-to-1) — Phase 05c.
* `MetagraphSchema` + `MetaEdgeType` + `MetaHyperEdgeType` +
  `IntergraphEdgeType` — Phase 05b.
* `Metagraph.mint_id` — Phase 05b (consumer = IntergraphEdge per P7).
* `_compositional` reserved-key — Phase 05b (per P6 — defer alongside
  the actual flag).
* Soft-delete substrate uniform across all 4 edge variants
  (Edge / HyperEdge / MetaEdge / MetaHyperEdge) — Phase 10.
* `RemovalImpact` + `force=True` on `remove_graph` — Phase 10.
* `Graph.properties` graph-level property bag (ADR-0130) — Phase 10.
* `XRef` primitive (ADR-0128) — Phase 09.
* Element instancing (ADR-0024 / ADR-0025) — Phase 06
  (`mindsos_instances` package).
* `CompositionalMetaEdge` — **DROPPED entirely** (N3-D + P3 lock;
  ADR-0117 Withdrawn in 05a per P3 amendment). The compositional
  concept moves to a flag on the intergraph primitives in 05b/05c.
* `_kl_active_graph_ids` / `user_id` aliases — re-added in Phase 14 /
  Phase 18 with their consumers (N1-A2 strip).

---

## 2. Round-1-4 design picks (in addition to the locked PHASE_MAP §5 row)

The implementing chat ran four rounds of reanalysis on top of the
30-item PHASE_MAP §5 row. All 19 picks accepted by the user; folded
into the implementation:

| # | Lock | Decision |
|---|---|---|
| P1 | Strip soft-delete fields | `MetaEdge` / `MetaHyperEdge` ship WITHOUT `deprecated_at` / `disputed_at`; matches Phase 03 Edge/HyperEdge precedent. Phase 10 lands the substrate uniformly across all 4 edge variants. |
| P2 | Q4-B + stderr suggestion | Standalone `mindsos graph` mutations refused on metagraph-owned graphs; refusal stderr suggests the equivalent `mindsos metagraph ...` invocation. |
| P3 | ADR-0117 Withdrawn in 05a | Code drops `CompositionalMetaEdge` here; ADR status flips to match (was: Reserved → Withdrawn in 05b). |
| P4 | ~45 tests baseline (then ~63) | Cover spec'd `update_*_properties`, label round-trip, back-pointer write-through, list output shapes. |
| P5 | `--yes` guard on `reset --force/--all` | Require `--yes` for destructive operations; refuse with exit 2 + actionable message. |
| P6 | Defer `_compositional` reserved-key to 05b | Avoid dead code in 05a; 05b adds atomically with the flag implementation. |
| P7 | Defer `Metagraph.mint_id` to 05b | No 05a consumer; ship with the IntergraphEdge factory in 05b. |
| P8 | `kw_only=True` dataclasses | `MetaEdge` and `MetaHyperEdge` use `@dataclass(kw_only=True)`. Resolves the field-ordering bug introduced by P1 (required `type_name` after defaulted `graphs`). |
| P9 | `__post_init__` cypher regex | Both edge types validate `type_name` at the dataclass boundary (ADR-0021), not just at the factory. Direct dataclass construction with invalid type raises `CypherError`. |
| P10 | Lock `inspect` / `list` JSON shapes | Documented in `metagraph.py` docstrings; tested in `test_metagraph_inspect_list.py`. |
| P11 | Factories take graph_id strings | `add_metaedge(source_graph_id, target_graph_id, type_name, ...)`; `add_metahyperedge(graph_ids: List[str], ...)`. CLI translates name→graph_id at the boundary. Persistence stores graph names. |
| P12 / P14 | Per-file migration chain | New `mindsos_cli/migrations/{__init__,graph,schema,metagraph}.py`. Each module exports `MIGRATIONS: List[Callable]` and `migrate(state) -> dict`. Loaders in `state.py` call `migrate()` after parsing JSON. Replaces inline switch statements that previously grew O(N) per phase. |
| P13 | Extend RESERVED_PROPERTY_KEYS | Added `_state_version`, `contained_graphs`, `metaedges`, `metahyperedges`, `metagraph_name`. Deliberately EXCLUDED `name` / `properties` (would break existing Phase 04 user-prop tests). |
| P15 | Refuse self-loop + 1-member | `add_metaedge` refuses `source_graph_id == target_graph_id`; `add_metahyperedge` refuses `len(graph_ids) < 2`; `MetaHyperEdge.__post_init__` enforces. |
| P16 | `add_graph` invariants locked | `g.identity is mg.identity` post-call (shared reference); `g.id_strategy` untouched (mixed-strategy metagraphs supported). |
| P17 | `--on-metagraph` marker flag | `mindsos metagraph set-prop` 3-way mutex `--on-metagraph | --metaedge-id | --metahyperedge-id`. ADR-0130 metagraph property bag has a CLI path mid-life (not just at create time per CR-A). |
| P18 | Two-file write order | `metagraph add-graph` writes graph state file (back-pointer set) FIRST, then metagraph state file. Recovery on metagraph-save failure: DM-A. |
| P19 | Drop `cascade` parameter | `Metagraph.remove_graph(graph_id)` is single-behavior always-cascade. No `cascade` / `force` flags, no `RemovalImpact` return. Phase 10 reintroduces the full ADR-0135 surface. |

---

## 3. Module changes

### Net-new files

* `mindsos_core/models/metagraph.py` — slim port (10 KB; original was 30+ KB).
* `mindsos_cli/commands/metagraph.py` — new Typer subapp (13 subcommands).
* `mindsos_cli/migrations/__init__.py`
* `mindsos_cli/migrations/graph.py` — chain v=1 → v=2 → v=3 → v=4.
* `mindsos_cli/migrations/schema.py` — chain v=1 → v=2.
* `mindsos_cli/migrations/metagraph.py` — chain (empty in 05a; v=1 current).
* `tests/phase_05a/__init__.py`
* `tests/phase_05a/conftest.py`
* `tests/phase_05a/test_*.py` — 14 test files (~99 tests).
* `docs/usage/core/metagraphs.md` (NEW)
* `docs/getting-started/first-metagraph.md` (NEW)
* `docs/api/core/metagraph.md` (NEW)
* `docs/api/core/metaedge.md` (NEW)
* `docs/api/core/metahyperedge.md` (NEW)
* `confirmation_docs/PHASE_05a_IMPLEMENTATION_LOG.md` (this file)

### Touched files

* `mindsos_core/__init__.py` — exports `Metagraph` / `MetaEdge` / `MetaHyperEdge`; version bump.
* `mindsos_core/schema/validation.py` — `RESERVED_PROPERTY_KEYS` extended (P13).
* `mindsos_cli/state.py` — bumps `GRAPH_STATE_VERSION = 4`; adds `METAGRAPH_STATE_VERSION = 1` and metagraph helpers; refactored `_load_state_file` → `_load_and_migrate` calling per-file chains.
* `mindsos_cli/commands/graph.py` — `_state_to_graph` returns 3-tuple `(graph, schema_name, metagraph_name)`; every CLI command updated to track + persist `metagraph_name`; Q4-B refusal helpers added; `detach-metagraph` subcommand added (DM-A); `reset --name` refuses on metagraph-owned graphs.
* `mindsos_cli/app.py` — `register_metagraph_app` wired.
* `mindsos_cli/__init__.py` — `__version__ = "0.0.0+phase05a"`.
* `mindsos_cli/manifest.toml` — `[mindsos] phase = "05a"`; `version = "0.0.0+phase05a"`.
* `pyproject.toml` — version + description bumped.
* `docker-compose.yml` — image tags `mindsos:phase05a-{prod,test}`.
* `Dockerfile` — comment lines bumped; COPY blocks unchanged (existing wildcards cover new files).
* `tests/_shared/sentinel_paths.py` — +5 entries (per P14 chain modules + slim port + CLI subapp).
* `tests/phase_03/test_state.py` — `test_save_and_load_round_trip` updated for migration-chain semantics.
* `tests/phase_04/test_state.py` — multiple assertions updated for migrated-on-load behavior; `test_graph_state_v4_refused` → `test_graph_state_future_version_refused` using `GRAPH_STATE_VERSION + 1`; `GRAPH_STATE_VERSION == 3` → `== 4` + `METAGRAPH_STATE_VERSION == 1` added; schema round-trip updated for v=1 → v=2 migration.
* `tests/phase_04_v2/test_state_v3_round_trip.py` — literal `_state_version == 3` removed (dynamic-only).
* `docs/concepts/graphs-and-metagraphs.md` — Metagraph section + Q4-B + P16 invariants + recovery patterns.
* `docs/changelog/CHANGELOG.md` — Phase 05a entry appended.
* `mkdocs.yml` — nav entries for new pages.

---

## 4. Bug ledger / decisions made during implementation

* **B-05a-1 — Field-ordering bug surfaced by P1 + adding required `type_name` to `MetaHyperEdge`.** Parent code's `MetaHyperEdge.graphs: Set[Graph] = field(default_factory=set)` — defaulted. Adding required `type_name` after a defaulted field is illegal in stdlib dataclasses. **Resolution: P8 lock — `@dataclass(kw_only=True)` on both `MetaEdge` and `MetaHyperEdge`. Field ordering becomes irrelevant; symmetric across both edge types; future-aligns with `IntergraphEdge` / `IntergraphHyperEdge` shapes per INTERGRAPH_EDGES_DESIGN.**
* **B-05a-2 — `MetaEdge.type_name` regex validation gap.** Parent `MetaEdge` has no `__post_init__`; the cypher rel-type regex was enforced only at the factory boundary, not at the dataclass. Direct construction (rehydration paths, future tests) could produce a `MetaEdge` with invalid `type_name`. **Resolution: P9 lock — added `__post_init__` to both `MetaEdge` and `MetaHyperEdge` running `validate_edge_type_identifier(type_name)`.**
* **B-05a-3 — Two factory styles between `MetaEdge` (parent: Graph objects) and future `IntergraphEdge` (graph_id strings per INTERGRAPH_EDGES_DESIGN).** Inconsistent API style; 05b would inherit. **Resolution: P11 lock — `Metagraph.add_metaedge(source_graph_id, target_graph_id, ...)` takes strings. CLI translates name→graph_id. Persistence stores names (one source of truth: name-keyed JSON).**
* **B-05a-4 — Round 4 hard-coded `_state_version` constants in Phase 03/04/04-v2 tests.** Per amendment 21 audit: tests assert `loaded == state` literal where `state` was hand-written at v=N; with the migration chain those become migrated dicts at v=4. Tests fail. **Resolution: surgically updated 6 specific assertions across `tests/phase_03/test_state.py` + `tests/phase_04/test_state.py` + `tests/phase_04_v2/test_state_v3_round_trip.py` to assert dynamic `state_mod.GRAPH_STATE_VERSION` / new field defaults.**
* **B-05a-5 — `name` and `properties` initially included in P13 RESERVED_PROPERTY_KEYS extension.** Would break Phase 04 `test_legacy_node_set_prop_replace_recovers` (which legitimately uses `name=Alice` as a node property). **Resolution: scoped P13 to truly metagraph-structural keys only; documented exclusions in code comment.**
* **B-05a-6 — Migration chain error message mismatch.** Initial migration helpers raised `ValueError` with new phrasing ("missing/invalid _state_version"); Phase 03 test `test_load_missing_state_version_field_raises` expects `match="missing required field"`. **Resolution: harmonized migration helpers' error messages with original `_load_state_file` phrasing for back-compat ("missing required field '_state_version'", "this CLI supports v{N}").**
* **D-05a-1 — Test budget grew from ~45 (P4 baseline) → ~63 (round 1-4 additions) → ~99 (final, with edge cases and round-trip coverage).** Per user direction "test budget is not a concern", we erred on the side of more coverage. The 14 test files cover dataclass invariants, factory semantics, migration chains, CLI surface (all 13 subcommands + Q4-B refusals), state-file shape, P5/P9/P10/P11/P15/P16/P17/P18 picks individually.

---

## 5. Two-file atomicity (P18) — recovery patterns

The `metagraph add-graph` write flow:

```
1. Load metagraph state file (must exist).
2. Load candidate graph state file (must exist; check N7-A back-pointer).
3. Mutate metagraph in memory: add graph, unify identity (P16).
4. Save graph state file with metagraph_name back-pointer set. ← FIRST
5. Save metagraph state file with new contained_graphs entry. ← SECOND
```

**Failure on step 5 → recovery via DM-A:** the graph has a dangling
back-pointer pointing to a metagraph that doesn't list it. The
`mindsos graph detach-metagraph --name <graph>` command operates on
raw JSON (bypasses metagraph rehydration) and clears the back-pointer.
Phase 07 will introduce proper transactional persistence; J-02
single-tester carry-forward applies in the meantime.

The `metagraph remove-graph` flow uses the OPPOSITE order: metagraph
saved first (graph removed from contained_graphs), then graph
back-pointer cleared. This minimizes the window where the metagraph
thinks it owns a graph that doesn't back-point.

---

## 6. Cascade semantics

Per P19, `Metagraph.remove_graph(graph_id)` is single-behavior:

1. Compute incident metaedges (`source_graph_id == graph_id` OR
   `target_graph_id == graph_id`).
2. Compute incident metahyperedges (`graph_id in mhe.graph_ids`).
3. Remove all incident edges via `remove_metaedge` /
   `remove_metahyperedge` (each unregisters the edge_id from
   `mg.identity`).
4. Walk graph's owned ids (graph_id + all node/edge/hyperedge ids) and
   unregister from `mg.identity`.
5. Delete the graph entry from `mg.graphs`.

No `cascade=False` semantic. No `force=True` flag. No `RemovalImpact`
return. Phase 10 reintroduces the full ADR-0135 surface (with proper
incoming-ref impact reporting).

---

## 7. Forward-compat notes for 05b/05c

Per the §6 dry-run appendix in PHASE_MAP §5, the following are pre-resolved:

* **05b adds `intergraph_edges` array + optional `schema_name` field**
  to metagraph state file → bump v=1 → v=2. **05a's v=1 shape is
  forward-compat:** missing fields default to empty/null. No 05a change
  needed beyond the chain.
* **05b's `IntergraphEdgeType` schema validation** uses Phase 04's
  `PropertyType` 8-variant vocabulary + new
  `allowed_source_graphs` / `allowed_target_graphs` constraints. No
  05a change needed.
* **05b's `MetagraphSchema`** is attached to Metagraph similarly to how
  Phase 04's `Schema` attaches to Graph. **05a's `Metagraph` constructor
  does NOT yet accept a `schema` parameter** — 05b adds it.
* **`_compositional` reserved key** — per P6 amendment, **05b adds it
  alongside the actual flag** (round 1 originally pre-paid in 05a;
  amended to defer for atomicity).
* **05c's `compositional` cascade** through `Metagraph.remove_graph`
  applies equally to compositional intergraph edges. **05a's slim
  `remove_graph` is forward-compat:** it cascades incident
  metaedges/metahyperedges only (no intergraph edges in 05a). 05b/05c
  add the intergraph-edge cascade.

---

## 8. Tester instructions

```sh
# [Linux] Tester host venv.
cd halvim_mindsos
git pull origin phase-05a
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e .

# Doctor self-test (static-only; no FalkorDB required for this).
mindsos doctor --self-test --static-only

# In-container tests.
docker compose run --rm mindsos-test pytest tests/

# Manual exploration: see docs/getting-started/first-metagraph.md.

# Confirmation.
mindsos confirm-phase --phase 05a --notes-file notes-phase-05a.md
```

Expected: `~99 added Phase 05a tests` + cumulative
(412 + 2 skipped from 04-v2 baseline) + minor adjustments from migration
chain assertion updates. **Final cumulative target: ~510 + 2 skipped
in-container.** Tester records the actual count in
`PHASE_05a_CONFIRMED.md`.

---

## 9. PHASE_MAP §5 amendment (round 1-4 picks)

The PHASE_MAP §5 Phase 05a row's "Final amendments" section gets the
following items appended (after the existing 30):

```
31. P1 (round-1) — soft-delete fields stripped from MetaEdge /
    MetaHyperEdge in 05a (overrides N2-B); Phase 10 adds across all 4
    edge variants uniformly per SOFT_DELETE_AUDIT_NOTE recommendation.
32. P2 (round-1) — Q4-B mutation refusals include stderr suggestion of
    the equivalent `mindsos metagraph ...` invocation.
33. P3 (round-1) — ADR-0117 status flips Reserved → Withdrawn in 05a
    (one phase earlier than the original CASC-1 placement).
34. P4 (round-1) — test plan expanded to ~45 (then ~63 with rounds 2-4
    additions; final ~99 with edge-case coverage).
35. P5 (round-1) — `mindsos metagraph reset --force` and `--all` require
    `--yes`.
36. P6 (round-1) — defer `_compositional` reserved-key addition to 05b
    (avoid dead code in 05a).
37. P7 (round-1) — defer `Metagraph.mint_id` to 05b (no 05a consumer).
38. P8 (round-2) — `@dataclass(kw_only=True)` on MetaEdge + MetaHyperEdge.
    Resolves the field-ordering bug introduced by P1 + required
    `type_name`.
39. P9 (round-2) — `__post_init__` cypher rel-type regex on both edge
    types (closes the dataclass-boundary validation gap on MetaEdge).
40. P10 (round-2) — `mindsos metagraph inspect` + `list` JSON shapes
    locked.
41. P11 (round-2) — `Metagraph.add_metaedge` takes graph_id strings (not
    Graph objects); `add_metahyperedge` takes `List[str]`. Persistence
    stores graph names (one source of truth: name-keyed JSON).
42. P12 / P14 (round-2 / round-3) — per-file migration chain at
    `mindsos_cli/migrations/{graph,schema,metagraph}.py`. Replaces
    inline switch statements.
43. P13 (round-3) — `RESERVED_PROPERTY_KEYS` extended with
    metagraph-structural keys (`_state_version`, `contained_graphs`,
    `metaedges`, `metahyperedges`, `metagraph_name`). EXCLUDED `name`
    and `properties` (would break Phase 04 user-prop tests).
44. P15 (round-3) — `add_metaedge` refuses self-loop;
    `add_metahyperedge` refuses < 2 members. Symmetric with
    INTERGRAPH_EDGES_DESIGN cardinality discipline.
45. P16 (round-3) — `add_graph` invariants: shared identity reference,
    untouched id_strategy. Documented in concepts/graphs-and-metagraphs.md.
46. P17 (round-4) — `mindsos metagraph set-prop --on-metagraph` marker
    flag for the metagraph's own ADR-0130 property bag (3-way mutex
    with `--metaedge-id` / `--metahyperedge-id`).
47. P18 (round-4) — `metagraph add-graph` two-file write order: graph
    state file (back-pointer set) FIRST, then metagraph state file.
    Recovery via DM-A.
48. P19 (round-4) — `Metagraph.remove_graph` is single-behavior
    always-cascade. No `cascade` parameter, no `force` flag, no
    `RemovalImpact` return. Phase 10 reintroduces.
```
