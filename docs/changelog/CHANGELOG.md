---
last_confirmed_phase: 15a
---

# Changelog

Append-only, one line per shipped phase. Phase 38 consolidates into a
release-style summary.

## Phase 15a — L2 admin importers (DOLCE / OEWN / FrameNet) (2026-05-19)

**Ships the admin layer.** NEW top-level package `mindsos_admin/` per
ADR-0140 §amendment-1 permanent-home decision (supersedes ADR-0140
§Decision §1+§2 server-relocation; Phase 37 row in PHASE_MAP retired).
NEW `mindsos_admin/bootstrap.py` with `bootstrap_global(importers=[...])
-> Metagraph` helper per Phase 15a PB-13 — ensures all 6 Global named
role-graphs (PB-21 parity with `KnowledgeLayer.bootstrap()` output) +
each importer's `target_roles` + runs importers. NEW
`ImporterProtocol` (PB-22 — `target_roles: tuple[str, ...]` class/
instance attribute + `run(mg) -> ImportResult`). NEW `ImportResult`
frozen dataclass. NEW `mindsos_admin/importers/dolce.py` (DOLCE-DUL
4.1, rdflib). NEW `mindsos_admin/importers/oewn.py` (OEWN 2024,
lxml + stdlib fallback). NEW `mindsos_admin/importers/framenet.py`
(FrameNet 1.7, single-file + Berkeley dir layouts). Each importer
auto-ensures its target role-graph per PB-14. ADR-0042 §amendment-2
documents the third first-install sequence. ADR-0140 §amendment-1
documents the permanent-home supersession + Phase 37 retirement. NEW
`mindsos admin import {dolce,oewn,framenet}` CLI verbs. NEW
synthetic-shape fixtures + real-dataset downloader
(`scripts/fetch_datasets.{sh,py}`). 3 NEW per-source doc pages under
`docs/knowledge-sources/`. 7-site new-top-level-package checklist
complete. Cross-package version `+phase15a` across 5 packages. Scope-
split (15a/15b) per PB-D1 — Alignments + scanner deferred to 15b.
ADR-0134 NOT flipped (PB-B1). Per-edge alignment-anchor IRI 4th-hop
deferred to Phase 33-35 per PB-C1.

## Phase 14 — L2 KnowledgeLayer + role-graph bootstrap + MetagraphView (2026-05-19)

**Ships the L2 entry point.** NEW `mindsos_knowledge/knowledge_layer.py`
(`KnowledgeLayer` class with constructor parameter for Global per
ADR-0042 §amendment-1; `bootstrap()` classmethod that auto-ensures
the 6 Global named role-graphs; lazy `local_metagraph(user_id)` that
auto-ensures the 2 Local named role-graphs per ADR-0044; install/
extract hooks per ADR-0042 §Decision with `AlreadyInstalledError` /
`NotInstalledError`). NEW `mindsos_knowledge/metagraph_view.py`
(whitelist read-only wrapper per PB-3 lock — methods: `roles`,
`graphs_by_role`, `get_node`, `iter_nodes`, `get_edges`, `step`,
`alignment_graph`, `metagraph_id`; no `follow_ref` overlay per
PB-10; no `version=` kwarg on `step()` per PB-15). NEW
`mindsos_knowledge/bootstrap.py` (two-method `ensure_global_role_graph`
+ `ensure_local_role_graph` with ADR-0044 scope enforcement; alignment
is Global-only at v1 per ADR-0150 §amendment-1 + Phase 14 PB-8;
`extra_edge_types` kwarg plumbs to `build_alignment_schema` for
forward-compatibility with Phase 15 importers). NEW
`AlreadyInstalledError(KnowledgeError)` + `NotInstalledError(KnowledgeError)`.
NEW `docs/concepts/global-local.md` (Bootstrap-stage owner per
Phase 14a's knowledge-lifecycle synthesis). ADR-0042 §amendment-1
documents the Global lifecycle via constructor parameter (PB-7);
ADR-0150 §amendment-1 documents alignment is Global-only (PB-8).
KL ships **no write API** per ADR-0138 Proposed (honoured by absence
per PB-6; ADR not flipped Accepted); **no validators** per
ADR-0139 Proposed (Phase 36 home per PB-14); **no CLI verbs** per
PB-13 (KL is in-memory-only per ADR-0043; state-file CLI deferred
to Phase 26 per Phase 14a round-3 lock); **no `request_promotion`**
(Phase 16+ owns; ADR-0137/0141 vs ADR-0140 attribution conflict
deferred). Per Phase 14 round-1 PB-1: carry-forwards (per-edge
alignment-anchor IRI builder + MetagraphSchema scanner) deferred
to Phase 15 (first concrete consumer is the Alignments importer).
Per Phase 14 round-2 PB-12 re-classification: Phase 14 is **mostly
NET-NEW** (no v3 `KnowledgeLayer` Python source existed to
repackage; the v3 design lives only in
`_source_backup/root/knowledge_layer_design.md` as a markdown doc).
Tests: 12 modules in `tests/phase_14/` covering KL init / bootstrap /
ensure_*_role_graph (parametric × 8 + scope-rejection × 8) /
lazy `local_metagraph` / install-extract / `MetagraphView` read
surface / `step()` without overlay / dimensional snapshot /
import-isolation / image-completeness / ADR-amendment sentinels.
~95-115 isolated; cumulative ~2120-2145. Cross-package version
parity bumped to `0.0.0+phase14` across 4 packages. Image tags
`mindsos:phase14-{prod,test}`. `manifest.toml [mindsos] phase =
"14"`. 3 new sentinel paths added to
`tests/_shared/sentinel_paths.py`. PHASE_15_NEXT_CHAT_PROMPT.md
written; Phase 15 inherits both deferred carry-forwards + bootstrap +
`KL.global_metagraph()` for importer targets.

## Phase 13 — L2 Schemas (alignment / lexicon / ontology / concepts + 5 upper-layer) (2026-05-18)

**Closes the L2 schema dispatch table — 8 named-role schema builders
+ a parametric `alignment` builder + `schema_for_role(role)` dispatch
function with alignment-prefix branch.** NEW `mindsos_knowledge/schemas/`
sub-package: ports the 4 v3 seed-role schemas (ontology / lexicon /
concepts / alignment) verbatim, lifts the 7 v3 ontology hyperedge
"label" constants to `HyperEdgeType` registrations per PB-4, and adds
5 NET-NEW upper-layer schemas (`promoted_pipelines`, `task_patterns`,
`memories`, `problem_trace`, `capacity_state`) at `strict=False` per
ADR-0149. Advisory NodeType properties live as module-level
`frozenset` constants per PB-8 (strict-tighten PR converts to typed
declarations). NEW `mindsos knowledge schema {show,validate}` CLI
sub-subgroup per PB-6 — `validate` runs L1 structural pass only;
semantic validation ships in Phase 36 per ADR-0139. NEW
`UnknownRoleError(KnowledgeError)` per PB-11 — raised by
`schema_for_role` on miss. ADR-0017 §Revisions amendment documents
the L2-role-schema strictness policy (Phase 13 PB-3); NEW ADR-0149
"L2 role-graph schemas at strict=False with 2-week tightening rule"
per PB-7; NEW ADR-0150 reserved (number only) — content drafted in
Phase 14a per PB-23. PHASE_MAP §1 amended with "design-only phases
are an exception" clause per PB-24; §14a row inserted; §14 deps
amended `12, 13` → `12, 13, 14a`; §3 table + §1 phase count adjusted
(43 → 44 phases). `tests/_shared/sentinel_paths.py` extended with
10 new module paths. PHASE_14a_NEXT_CHAT_PROMPT.md handoff written.
~76 isolated tests across 11 modules (2 skipped in container — ADR
amendment sentinels live in parent project tree per Model C).
Cumulative ~1966. Cross-package version-string parity bumped to
`0.0.0+phase13` (still 4 packages — sub-package add does not flip
parity count). Step-0 audit: 0 prior-phase patches across 10 probes
(streak of 3 — Phase 11 + 12 + 13). MetagraphSchema scanner (Phase 11
PB-7 C) re-carried-forward to Phase 14 (KL bootstrap); per-edge
alignment anchor IRI (Phase 12 PB-4) re-carried-forward to Phase 14;
ADR-0134 Proposed → Accepted flip + migration-playbook content
re-carried-forward to Phase 15.

## Phase 12 — L2 Identifiers + role IRIs + REF_TYPES (2026-05-16)

**Ships the first L2 package (`mindsos_knowledge`) — 14 IRI builders
per ADR-0045 (7 v3 seed-role + 7 upper-layer net-new), `alignment_role`
graph-name helper, table-driven `parse_iri` + `is_version_qualified_iri`,
`REF_TYPES` open vocabulary (ADR-0047) + extension recipe, ref-key
helpers (`global_ref_key` / `local_ref_key` / `REF_TYPE_KEY`), 8 role
constants + 3 frozensets (`SEED_ROLES` / `UPPER_LAYER_ROLES` /
`ALL_ROLES`).** NEW `mindsos_knowledge/__init__.py` +
`identifiers.py` (~340 LoC) + `exceptions.py`. NEW `mindsos knowledge
{iri build|parse|validate, ref-types --list, roles --list}` CLI surface
(sub-subgroup shape per PB-16). Doctor `--self-test` flipped from
3-pkg to 4-pkg version-string parity. ADR-0044 §Revisions amendment-1
documents `user_id` charset (`^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`)
per PB-11 + PB-17. ADR-0045 closure sentinel test confirms all 14
builders are exported. ADR-0067 L3 parity test deferred to Phase 27
(L3 doesn't exist yet). PB-18 import-isolation test asserts
`mindsos_knowledge ⇏ {mindsos_cli, mindsos_server}` from day one.
PB-8 lock: `capacity_snapshot_iri` body is opaque after `snapshot:`
(embeds colon-bearing `capacity_iri` per ADR-0066); full-string
round-trip holds. ~90 isolated tests across 7 tiers. Cumulative:
~1870. Cross-package version-string parity bumped to `0.0.0+phase12`
(4 packages). Phase 11 carry-forward (MetagraphSchema scanner,
ADR-0134 Proposed → Accepted flip, `docs/dev/migration-playbook.md`
content) re-carried-forward to Phase 13/15 per design-log §4.

## Phase 11 — L1 Loader policy + schema migration scanner (2026-05-16)

**Ships ADR-0134 — `migrate_from(old, target, *, new, detail,
old_schema_name)` detection-only scanner + `LoadReport` /
`MetagraphLoadReport` siblings + per-call `unknown_edge_type_policy`
kwarg on `load_graph_with_report` / `load_metagraph_with_report` /
`MetagraphLoader.load_with_report` + env-var fallback
`MINDSOS_UNKNOWN_EDGE_POLICY`.** NEW `mindsos_core/schema/migration.py`
(~310 LoC) — 5 violation kinds (`removed_node_type` /
`removed_edge_type` / `removed_hyperedge_type` / `tightened_property`
/ `missing_required_property`); summary / each detail modes per
PB-8 A; per-Graph + per-Metagraph dispatch per PB-17 C; Schema-level
coverage only (NodeType + EdgeType + HyperEdgeType per PB-7 C —
MetagraphSchema scanner deferred to Phase 12+). NEW
`mindsos_core/reconstruction/load_report.py` (~140 LoC) — drop count
on report not Graph per PB-9 B (no state-file bump). Loader policy
plumbing additive-sibling per PB-12 B + PB-13 A — existing
`load_graph` / `load_metagraph` / `MetagraphLoader.load` signatures
UNCHANGED. Per-distinct-type WARN with counts per PB-10 A (ADR-0134
§amendment-1). No-op when no schema attached per PB-11. Policy on
loader call surface NOT FalkorConfig per PB-14 A (ADR-0134
§amendment-2 corrects original ADR mis-placement). NEW
`UnknownEdgeTypeError` + `SchemaMigrationError`. CLI: `mindsos
schema migrate-check` (--graph G | --metagraph M mutex; --old <name>
| --old-file <path> mutex; --new <name>; --detail summary|each;
--json; --exit-zero; exit 1 on violations default per PB-15);
`mindsos persistence load --unknown-edges=warn|error|ignore` surfaces
drop count in Rich + JSON outputs. ADR-0134 stays Proposed; flips
Accepted Phase 12+ when KL consumer lands per PB-5 A. ADRs
0021/0022/0023/0123 untouched (already Accepted). 118 isolated
tests / 4 skipped (`test_adr_0134_amendments.py` — ADR file lives
in parent dir, not COPYd into runtime image). Cumulative: ~1780.
Step-0 audit predicted 0 prior-phase cascade; impl confirmed 0.
B-11-T1 (`tomllib` stdlib + `tomli` fallback per
`feedback_tomllib_stdlib_fallback.md`); B-11-T2 (state-file key
canonicalization: `edge_id`/`node_id` not `e["id"]`/`n["id"]`; new
audit class `feedback_state_file_key_canonicalization.md`).
3-package version-string parity bumped to `0.0.0+phase11`.

## Phase 10 — L1 Snapshot + soft-delete substrate + RemovalImpact + XRef setters (2026-05-16)

**Ships the snapshot mutate-in-place helper (ADR-0027/0028/0129), the
soft-delete substrate uniformly across 4 edge variants + XRef quartet
(ADR-0133), `RemovalImpact` return + raise-on-block contract on
`remove_graph` (ADR-0135), iterator + loader filter pass (P68 merge),
and the Phase 09 P53 reversal restoring XRef.target_stale +
deprecated_at.** NEW `MetagraphSnapshot.of(mg)` + `restore_into(mg)` at
`mindsos_core/metagraph_snapshot.py` (~280 LoC slim-port; 12-attribute
allow-list per M3 + P84). NEW `RemovalImpact` dataclass (4 fields:
incoming_xrefs / incoming_ref_properties / proceeded / blocked_reason);
NEW `RemoveGraphBlockedError` + `BlockedReason` str-Enum
(DANGLING_REFS / INCIDENT_META_EDGES_CASCADE_FALSE). `remove_graph`
signature changes to `remove_graph(graph_id, *, cascade=True,
force=False) -> RemovalImpact` (P67 cascade restored from v3, P75
unified exception, P81 cascade-vs-force independence). NEW `Edge` /
`HyperEdge` / `MetaEdge` / `MetaHyperEdge` fields `deprecated_at` +
`disputed_at` (M5). XRef restores `target_stale: bool` +
`deprecated_at: datetime | None` (P53 reversal). NEW 20 setter
methods: Graph quartet × Edge + HyperEdge (8; fixes SD1 v3 baseline
HyperEdge no-API), Metagraph quartet × MetaEdge + MetaHyperEdge (8;
fixes SD2 + SD3 v3 baseline API inconsistency + missing dispute path),
XRef quartet PX2 (4: mark_xref_stale / unmark / deprecate_xref /
undeprecate). NEW `_resolve_at(at)` helper (PB-2;
`datetime.now(timezone.utc)` modernization). NEW
`SoftDeleteKind` str-Enum (P72 typo-proof dirty-bucket keys). NEW 3
Graph iterators (P82): `iter_edges` / `iter_hyperedges` /
`get_edges_for_node` with `include_deprecated: bool = False`
parameter. Phase 09 `iter_xrefs` + Phase 05a `iter_metaedges` /
`iter_metahyperedges` extended with same parameter. 5 loader entry
points (`load_metagraph` / `MetagraphLoader.load` / `.refresh` /
`load_graph` / `iter_load_graph`) extended with parameter + Cypher
WHERE-clause filtering. NEW 22 Cypher builders (M16 PB-4a
per-method): 16 edge-side soft-delete setters + 4 XRef setters + 2
`_compute_removal_impact` query builders. NEW
`MetagraphRepository.persist` Step 1h drain in RPB-5 order (EDGE →
HYPEREDGE → METAEDGE → METAHYPEREDGE → XREF) with atomic per-bucket
clear. NEW 8 WAL replayer kinds (M8): 4 collapsed element-side
(`element_deprecate` / `undeprecate` / `dispute` / `undispute`) + 4
XRef-specific (`xref_mark_stale` / `unmark_stale` / `deprecate` /
`undeprecate`); wrapper `register_all_l1_replayers` grows 2 → 10
kinds. State-file v=4 → v=5 bumps (metagraph + graph) with
`_v4_to_v5` per-kind migrations (RR-7); deserializer + serializer
extended for soft-delete fields with ISO ↔ datetime conversion (RR-8
+ RR-18 + RR-19); P64 mirror — state-file deserialize clears dirty
buckets. `mindsos persistence xref-list` patched to 10-field `--json`
(M24); Rich table grows `target_stale` / `deprecated_at` columns only
when non-default (RR-6). NEW P85 Graph `properties` parameter
(ADR-0130 Graph-side acceptance via snapshot-preservation basis per
P69 caveat). NEW P86 Graph-side `_soft_delete_dirty[EDGE +
HYPEREDGE]` mirroring Metagraph `_soft_delete_dirty[METAEDGE +
METAHYPEREDGE + XREF]`. ADR file edits at project-root (chunk-10
commit per RPB-7): 0027 §Revisions a-1 (covered-fields + identity
rebuild + dirty sets); 0128 §Revisions a-3 (cleanup setter exists;
trigger Server-phase per O1); 0130 flip Graph-side §Acceptance with
P69 caveat; 0133 flip Proposed → Accepted with D1-rev clause-strip
(CompositionalImmutableError class retained per ADR-0148); 0135 flip
Proposed → Accepted with 3 amendments (cascade default flip +
raise-on-block + unified blocked_reason enum). Tests: ~145 unit + ~14
integration = ~159 Phase-10 files. Cumulative: 1660 passed. B-10-T1
(integration test XRefLoader.load_into idiom carry-from-Phase-09);
B-10-T2 (WAL recovery uses wal.begin() vs raw cypher); B-10-T3
(15 prior-phase tests patched to dynamic CURRENT_VERSION literals per
the feedback_phase_baseline_literal_audit.md audit-class). Cross-package
version-string parity bumped to `0.0.0+phase10` (3 packages);
`manifest.toml [mindsos] phase = "10"`; `docker-compose.yml` image
tags `mindsos:phase10-{prod,test}`. Confirmation manifest `phase =
"10"`; tag `phase-10-confirmed`. Tests pass in-container; CASC-1
strict-sequential dependency on Phase 09 honored.

## Phase 09 — L1 XRef (cross-metagraph refs) (2026-05-15)

**Ships the first-class cross-metagraph reference primitive (ADR-0128
hybrid model) + WAL-wrapped `XRefRepository` + clear-first
`XRefLoader` + `attach_xref_loader` after-load observer helper +
read-only `mindsos persistence xref-list` CLI verb + programmatic
`migrate_in_memory` callable for legacy `ref:global_*` properties.**
NEW `XRef` dataclass (`kw_only=True`; 8 fields — `target_stale` and
`deprecated_at` deferred to Phase 10). NEW `Metagraph.add_xref` /
`iter_xrefs` / `remove_xref` with optional `target_metagraph` write-
time validation (`XRefIntegrityError` on miss); validation runs
BEFORE the WAL entry opens (P59) so rejected writes never resurrect
on `recover()`. NEW `_xrefs_dirty: Set[str]` dirty-tracking on
`Metagraph`; programmatic `add_xref` without an attached client marks
dirty; `MetagraphRepository.persist` drains the set (P54). NEW
`build_create_xref` + `build_remove_xref` MERGE/DETACH-DELETE Cypher
builders. NEW `XRefRepository(client).persist/remove` with WAL
context-manager wrap (M16). NEW per-Client WAL replayer registration:
`register_replayer` / `clear_replayers` / `recover` all take `client`
as their first positional arg (P51 + P61); the prior module-level
`_REPLAYERS` global is gone. NEW `register_all_l1_replayers(client)`
wrapper composing per-kind module-owned registration functions
(RR-16); `FalkorClient.__init__` calls it after `bootstrap`.
WALReplayerMissingError narrow-catch in `MetagraphLoader.load`
REMOVED (P62) — unknown kinds now propagate loudly. NEW
`XRefLoader.load_into(mg)` clear-first semantics (PB-9 + P55 + P64):
clears `mg.xrefs` + inverse indexes + identity unregistrations +
dirty set BEFORE re-populating. NEW `attach_xref_loader(mg)`
idempotent helper (M18) subscribing the loader to the after-load
observer queue. CLI: NEW `xref-list --metagraph M [--source-id |
--target-metagraph | --target-id | --ref-type | --json]` verb with
direct-DB query path (P63 — does not load the metagraph or fire
recover); Rich table default + `--json` opt-in. CLI: `load
--metagraph M` summary REPLACED — Phase 08's 9-line flat list
becomes a single `Dependent state: graphs=N metaedges=N ...
xrefs=N ...` key=value line that grows additively (P52). CLI:
`_metagraph_has_dependent_state` query field PATCHED from
`metagraph_id` to `source_metagraph_id` (M11; closes the Phase 08
defensive deferral). State-file metagraph **v=3 → v=4** adding
`xrefs[]` array (M10 + RR-7 + RR-8 + RR-12); deserializer in
`_state_to_metagraph` reads xrefs[] directly into `mg.xrefs` +
manually rebuilds inverse indexes, leaves `_xrefs_dirty` empty
(RR-18 + P64). 4 new `:XRef` indexes in bootstrap (M15; bootstrap
grows 14 → 18) including `(target_metagraph_id, target_id)`
compound. NEW `tests/_shared/cross_metagraph_fixture.py
::make_source_and_target_metagraphs` helper (RR-13). EXTEND
`tests/_shared/metagraph_equality.py::assert_metagraphs_equal` for
XRef id-set + per-id field-by-field check; NEW sibling
`assert_xref_contents_equal` for content-tuple comparison (PB-3 +
RR-4). 30 test files in `tests/phase_09/` covering 53 active picks
(RPB-7 ratio). 3-package version-string parity bumped to
`0.0.0+phase09` (`mindsos_core` / `mindsos_cli` / `mindsos_instances`).
ADR-0130 flips Proposed → Accepted (M7; closes §7 Q4) and adds
`xref:` to the namespacing convention (item H). ADR-0128 stays
Proposed; flips Accepted in Phase 14 once L2 `MetagraphView.follow_ref`
consumes it (P50; §Revisions log appended with 5 amendments).
ADR-0142 stays Proposed; acceptance-criteria amended with the
3-commitment partition (Phase 09 ships L1 commitment; Phase 14 ships
L2 fallback; Phase 18+ ships Server first-start hook).

## Phase 08 — L1 Reconstruction (2026-05-14)

**Ships the FalkorDB → Python read surface for `mindsos_core` + sibling
`mindsos_instances/reconstruction/`.** Class `MetagraphLoader(client)`
+ module function `load_metagraph(client, mid, ...)` (RR-5 B + PB-2 C
hybrid). NEW `iter_load_graph(client, gid, batch_size=10_000)`
streaming variant (PB-3 A; RPB-1 A cross-batch trailer semantics;
RPB-10 A intra-graph only). Phase 07's `load_graph` refactored
internally to call `iter_load_graph` + assemble (RR-12 A). NEW
sibling-package `mindsos_instances/reconstruction/instance_loader.py`
(slim port from v3; RR-3 A override-allow-list validation at load;
RR-4 B orphan template log+skip). NEW
`Metagraph.register_after_load_observer` + `_dispatch_after_load`
helper with per-observer exception isolation (RR-9 A — diverges from
`_dispatch_after_persist`). NEW first L1 WAL consumer:
`load_metagraph` always calls `recover(client, mid)` before reads
(PB-6 B; narrow-catches `WALReplayerMissingError` per RPB-3 C).
NEW 3 exception classes: `RefreshUnsafeError` (PB-5 B class only;
no enforcement), `WALReplayerMissingError` (RPB-3 C sentinel),
`RoleMismatchError` (R4-2 D refresh DB-drift signal). All inherit
from `PersistenceError`; no `ReconstructionError` umbrella (R4-3 A).
NEW CLI: `mindsos persistence sync --metagraph M [--replace]` (PB-8 A;
`--replace` refuses on dependent state per RPB-4 C — exit 2);
`load --metagraph M [--to-json] [--json]` (PB-9 A; 9-line flat
summary per R4-5 A; `--to-json` writes
`~/.mindsos/metagraph-<name>.fromdb.json` sibling per RR-7 A);
`verify --source=db --metagraph M` UNBLOCKED (PB-7 A drops Phase 07
P49 A refusal). Typer mutex `--graph G | --metagraph M` on load +
verify + sync (R4-6 A; exit 1 on combo). P60 — additive `edge_id` +
`_validate=False` kwargs on `Metagraph.add_metaedge` +
`add_metahyperedge` to support round-trip id preservation (mirrors
Phase 05b/05c precedent on intergraph factories). P61 A — additive
fix to Phase 07's IntergraphHyperEdge persist: writes `:ANCHOR` rels
alongside `:MEMBER` so the `n_anchors >= 1` invariant survives round-
trip. ADR-0124 flipped Proposed → Accepted inline (M3 A); signature
amendment per PB-3 A; impl-refs amended per RR-6 A; acceptance
criterion per PB-14 C. ADR-0125 stays Proposed (PB-1 A — server-
side). NO state-file bumps (M0 carried). Manifest + 3-package
version-string parity bumped to `0.0.0+phase08` (R4-15 A); compose
image tags `mindsos:phase08-{prod,test}` (R4-16 A). 5 doc-footprint
items (RR-15 A): amend `persistence.md` + `core.md` (NEW
"Reconstruction layer" section) + NEW `loaders.md` API ref + ADR-0124
flip + changelog entry. NEW test fixtures: `metagraph_equality.py`
(round-trip walker) + `large_graph_factory.py` (N-node builder).
NEW `pytest.mark.slow` marker (RPB-12 B+C; 10K-node opt-in).

## Phase 07 — L1 Persistence (2026-05-13)

**Ships the FalkorDB persistence layer for `mindsos_core` + sibling
package** per Phase 07 row. `Client` Protocol (ADR-0030) +
`FalkorClient` + `InMemoryClient` + `AsyncClient` (ADR-0126) +
`bootstrap` with **14-index** `DEFAULT_INDEXES` (ADR-0123 amended per
P89 A relationship-index syntax + P95 B final count: 10 node-label +
3 relationship + 1 hot-path `:Node {graph_id}`) + `GraphRepository`
(persist with persist-time check per ADR-0123 §2 + always-bump
`_version` + opt-in OCC predicate per ADR-0127 + per-(graph, element)
tombstones per P69 A) + `MetagraphRepository` with **4-step lifecycle
P96 A** (Core → WAL commit → `after_persist` observer → return);
programmatic-only at 07 per P60 A + `WriteAheadLog` (ADR-0122) with
primary context-manager API per P50 B + 5-bucket `verify_invariants`
+ 3-bucket `verify_invariants_graph` sibling per P98 A + single-Graph
`load_graph` per M14 + `_props_json` canonical encoding per ADR-0130
+ P62 A with no size cap (P83 C) and narrow chained driver-exception
catch (P97 B) + `schema_name` plain Cypher property using the existing
dataclass field per P100 A + `_version: int = 1` field on 9 dataclasses
(7 core including Node restored per P26 A + 2 instance per P11 A) +
sibling-package `InstanceRepository` (M9 observer-driven persist via
`attach_registry` extension) + `mindsos persistence` 5-verb CLI subapp
(sync / load / diagnose / verify / inspect-state) with Rich tables per
P99 A + `--to-json` sibling `.fromdb.json` path per P85 B (M0 B JSON
authority preserved) + `sync --replace` WAL-refusal per P91 A + new
`[falkordb]` manifest section (host/port/graph; no username per
P86 B; password env-only per P15 A) + doctor self-test extension per
P59 A 5-cell matrix + collect-then-report per P75 B +
`_CONFIRM_PHASE_TIMEOUT_SECONDS` bump 600 → 900 (M12 + P93 pre-build
recipe) + 4 ADRs flipped `Proposed → Accepted` inline per M3 A (0122
/ 0123 / 0126 / 0127; acceptance-criteria amended per P27 C; ADR-0127
§Repository API amended per P28 B; `MissingExpectedVersionError`
ships at L0/L2 not L1 per P84 B).

Design locked 2026-05-12 across 3 design rounds + 4 meta-pick passes
(M0–M15 + P1–P25); Round-6 addendum applied 2026-05-12 (53 pushbacks
P26–P78); design-review supplement applied 2026-05-13 (22 pushbacks
P79–P100). Test suite ~110-140 added per `feedback_test_budget_
unlimited.md`.

## Phase 06 — L1 Instancing (`mindsos_instances` sibling package) (2026-05-11)

**Ships `mindsos_instances/` — new top-level package with 8 element-
instance subclasses (`NodeInstance` / `EdgeInstance` /
`HyperEdgeInstance` / `SubGraphInstance` / `GraphInstance` /
`MetaEdgeInstance` / `MetaHyperEdgeInstance` / `CompositeInstance`) +
`ElementRegistry` + materialise machinery + `canonicalize` utility +
cascade-observer plumbing on `mindsos_core`** per Phase 06 row §A-§K.
Design locked across 6 rounds (M1–M6 + P1–P44; 2 user overrides at
P13 B + P24 B) + 1 implementation round-7 pass (P45–P66) that reshaped
the row before code landed. Round-7 ledger at
`confirmation_docs/PHASE_06_IMPLEMENTATION_LOG.md` §1.

* **Round-7 P45 B** — ADR file edits deferred to Phase 38 per 5-cascade
  precedent. `docs/decisions/adr/` doesn't exist on disk; the row's
  original §G "rewrite ADR-0132 Decision section inline" plan dropped.
  Only on-disk amendment: `mindsos_core/__init__.py:54` stale ADR-0024
  reference → ADR-0015 (P19 A).
* **Round-7 P46 C** — Instance ID derivation drops the overrides hash.
  `UUID5FromContentStrategy` warns against content-addressable IDs for
  mutation-prone objects; instance overrides ARE mutation. ID now
  derives from `(template_id, instance_seq)` via the metagraph's
  pluggable `id_strategy`. Instances are stable under `set_override`.
* **Round-7 P49 B+A** — Core ships observer plumbing only; new
  `mindsos_instances.attach_registry(mg)` idempotent helper constructs
  + attaches `ElementRegistry`. ADR-0010 boundary preserved (no Core
  import of `mindsos_instances`).
* **Round-7 P58 A** — Edge/HyperEdge/MetaEdge/MetaHyperEdge materialise
  resolves ID-overrides to Node/Graph objects via a walk of
  `metagraph.graphs.values()` (O(G×N) — acceptable for Phase 06 single-
  call demo; Phase 07 may add a reverse-index).
* **Round-7 P59 A** — Cascade observer routes through
  `SubGraphInstance.node_ids` / `edge_ids` membership when an inner
  element is removed. Closes the stale-reference bug-class for
  subgraph instances.
* **Round-7 P64 A** — Override-validation routing is bifurcated:
  structural-allow-list keys bypass `validate_user_properties`;
  everything else routes through with `scope=KIND`.
* **Round-7 P65 A** — Observer-callback exceptions abort the originating
  Core `remove_*` method atomically (precheck-style dispatch — callbacks
  fire BEFORE the underlying mutation).
* **Round-7 P66 (implementation pushback)** —
  `Metagraph.register_graph_added_observer` so graphs added AFTER
  `attach_registry` get their per-Graph remove-observer subscription
  wired. Closes a cascade regression caught by 9 failing tests in
  `tests/phase_06/test_cascade_observer.py`.

CLI surface (4 verbs per row §H): `mindsos instances instantiate-node`
/ `instantiate-edge` / `instantiate-hyperedge` / `compose`. Each with
`--materialise` flag + `--override key=val` JSON-fragment parsing
(round-7 P57 A list→set coercion for set-typed structural fields).
Exit codes per round-7 P53 A (0/1/2 — adopts 05d split).

State files unchanged (P8 B — persistence is Phase 07).

## Phase 05d — L1 MetaEdgeType + MetaHyperEdgeType vocab + eager-attach extension (2026-05-07)

**`MetaEdgeType` + `MetaHyperEdgeType` vocabs ship on `MetagraphSchema`**
per ADR-0014 third amendment + 6-round-locked PHASE_MAP §5 row + a
round-7 reanalysis pass (P31–P44) that materially reshaped the row
before code landed. Round-7 pushback ledger at
`confirmation_docs/PHASE_05d_IMPLEMENTATION_LOG.md` §1.

* **Round-7 P31 A** — Drop the locked-design fingerprint mechanism
  entirely. No `last_attached_vocab_fingerprint`. No
  `--accept-vocab-change` flag on `attach-schema`. No metagraph
  state-file bump. Eager-attach + new walk extension is the consent
  surface.
* **Round-7 P32 A** — `mindsos metagraph-schema validate --metagraph
  MG [--schema MS]` ships read-only. `--schema MS` opt-in validates
  against an explicit schema without touching `MG.schema_name`.
  Useful for dry-running schema edits before attach.
* **Round-7 P33 A** — Strike P11 A's instance-graph forward-compat
  assertion. Phase 06 owns the role mutability decision.
* **Round-7 P38 B** — Cross-vocab same-name lookup hint becomes
  informational only (no editorial recommendation about vocab
  segregation; the 4-vocab namespace policy explicitly allows it).
* **Round-7 P39 A** — Empty `MetaEdgeType` / `MetaHyperEdgeType` vocab
  + non-strict eager-attach passes silently (mirrors 05b/05c
  Pushback 24-hybrid precedent for `IntergraphEdgeType`). Closes the
  05c-migration regression vector. `add_metaedge` / `add_metahyperedge`
  on empty vocab raises `UnknownTypeError` regardless of strict
  (precedent asymmetry preserved).
* **Round-7 P40 A** — `validate --json` shape drops the now-meaningless
  `vocab_fingerprint_match` field.
* **Round-7 P41 A** — Exit codes split: 0 pass, 1 violation, 2
  resource-not-found, 3 no-usable-schema.
* **Round-7 P42 C** — One-line pointer added to `0014.md` + `0017.md`
  ("See `confirmation_docs/PHASE_MAP.md` §5 for amendments through
  Phase 05d") replaces inline transcription. Full transcription stays
  Phase 38.
* **Round-7 P44 A** — `add_metaedge` / `add_metahyperedge` validation
  order mirrors actual 05b `add_intergraph_edge` precedent at
  `metagraph.py:735-798` (containment first; cypher regex deferred to
  `__post_init__`). The original P5 A claim "mirrors 05b precedent"
  was factually wrong — verified against source.
* **State-file bump** — `metagraph-schema-<n>.json` v=2 → v=3 (adds
  `meta_edge_types: []` + `meta_hyperedge_types: []` defaults; defensive
  null→[] normalization). `metagraph-<n>.json` stays at v=3.

Net new code: ~80 LOC vocab dataclasses + ~280 LOC `MetagraphSchema`
extension methods + ~50 LOC `attach_schema` walk extension + ~40 LOC
factory wiring + ~50 LOC migration step + ~250 LOC CLI verbs (3 new) +
~140 LOC `_walk_for_violations` helper + tests in `tests/phase_05d/`.

## Phase 05c — L1 IntergraphHyperEdge (n-ary, NOT 1-1) + IntergraphHyperEdgeType + replace-only update verb (2026-05-06)

**`IntergraphHyperEdge` (n-ary) + `IntergraphHyperEdgeType` +
`update_intergraph_hyperedge` ship** per ADR-0148 amended +
4-round-locked PHASE_MAP §5 row + 2 future-work entries filed at
`_source_backup/root/mindsos_future_plans.md`. 20 numbered pushbacks
locked in design chat plus 5 implementation pushbacks (P26-P30) +
2 follow-ups (P31-P32) accepted. Key shape:

* **P1-B** — Scope split: 05c ships `IntergraphHyperEdge` primitive +
  `IntergraphHyperEdgeType` vocab + replace-only update verb only.
  `MetaEdgeType` + `MetaHyperEdgeType` further deferred to NEW Phase
  05d.
* **P2-refined + P27** — Strict `__setattr__` scope on
  `IntergraphHyperEdge`: `compositional` always blocks; `anchors` /
  `members` / `properties` block on direct user mutation regardless of
  compositional flag; factory bypasses via `object.__setattr__`
  ("set-via-factory" contract).
* **P4-A** — CLI uses paired flags (`--anchor-graph G --anchor-node N`
  repeatable, paired by parsing index); mismatched counts refuse
  before any mutation.
* **P5-refined / P9-A / P18-A** — `IntergraphHyperEdgeType.ordered:
  bool = True` (default; permissive list semantics for cat=c+a+t case).
  `ordered=False` opt-in via `--unordered`; canonicalizes anchors +
  members at construction (sort+dedup).
* **P8-A** — `compositional=True` + `ordered=False` refused at
  validation step 10 (after canonicalization, before cardinality).
* **P10-C** — Single replace-only `update_intergraph_hyperedge`
  factory + CLI verb covers anchors + members + properties atomically.
  Refuses if compositional. Atomic rollback on validation failure.
* **P14-A** — 16-step validation order at
  `Metagraph.add_intergraph_hyperedge`; canonicalize-BEFORE-cardinality
  catches dedup-collapse-to-1-1 under `ordered=False`.
* **P17-A extended** — `Metagraph.remove_graph` precheck pass walks
  BOTH `intergraph_edges` AND `intergraph_hyperedges`; structured
  error includes edge_kind + side disambiguation.
* **P19-A** — Update collapsing to 1-to-1 cardinality refused at
  validation step 8. No in-place hyperedge→edge downgrade.
* **P20-A** — Update under detached schema validates structurally
  only (no schema/role/property-type check).
* **P32** — Cypher rel-type regex enforced at factory inline (step 5)
  AND `__post_init__` (belt-and-suspenders for direct-construction
  safety; rehydration paths defended).
* **P31** — 05b CHANGELOG amendment ships on this branch + permanent
  regression test for the P13-B workaround at
  `tests/phase_05c/test_cli_intergraph_hyperedge.py::TestP13BWorkaround`.
* **5-way set-prop mutex** — Extends 05b's 4-way with
  `--intergraph-hyperedge-id`.
* **P12-A** — Schema-mutation-while-attached footgun stderr warning
  on `metagraph-schema add-intergraph-hyperedge-type`.

**Filed as future work** (`_source_backup/root/mindsos_future_plans.md`
"Intergraph primitive structural mutation" section):

* Discoverable endpoint-update verb for IntergraphEdge (P11→P13-B).
* In-place hyperedge→edge downgrade with edge_id stability (P19-A).

State files: metagraph state v=2 → v=3 cumulative one-way migration
(adds `intergraph_hyperedges` array). MetagraphSchema state v=1 → v=2
cumulative one-way migration (adds `intergraph_hyperedge_types` array).
`RESERVED_PROPERTY_KEYS` extends with `intergraph_hyperedges`,
`intergraph_hyperedge_types`, `anchors`, `members`. P17-A:
`mindsos metagraph` subapp now ~26 subcommands (future-work 33-B
remains filed). ADR-0148 amended for n-ary primitive (file edit
Phase 38). ADR-0014 second amendment (file edit Phase 38).

## Phase 05b — L1 IntergraphEdge (binary) + IntergraphEdgeType + MetagraphSchema container (2026-05-05)

**`IntergraphEdge` + `IntergraphEdgeType` + `MetagraphSchema` ship** per
ADR-0148 first draft + 6-round-locked PHASE_MAP §5 row + 4 future-work
entries filed at `_source_backup/root/mindsos_future_plans.md`. 34
numbered pushbacks accepted by user across 6 reanalysis rounds. Key
shape:

* **Pushback 1-C** — Scope narrowing: 05b ships `IntergraphEdge` (binary)
  + `IntergraphEdgeType` + `MetagraphSchema` container ONLY. `MetaEdgeType`
  + `MetaHyperEdgeType` deferred to 05c (alongside `IntergraphHyperEdge`
  + `IntergraphHyperEdgeType`).
* **Pushback 2-A** — `compositional: bool` is a top-level dataclass field
  on `IntergraphEdge`. The reserved key `_compositional` (in
  `RESERVED_PROPERTY_KEYS` per Pushback 18-A) is reserved for the future
  Phase 07 Cypher emit's stamped property.
* **Pushback 3-A** — New top-level `mindsos metagraph-schema` subapp +
  `mindsos metagraph attach-schema` / `detach-schema` bindings.
* **Pushback 4-A** — Role-based graph constraints
  (`allowed_source_graphs` / `allowed_target_graphs` against
  `Graph.role`).
* **Pushback 6-A** — Compositional immutability has no escape hatch.
  Recovery via `mindsos metagraph reset --name <MG> --force --yes`.
* **Pushback 17-A** — `Metagraph.remove_graph` runs an atomic precheck:
  if any incident `intergraph_edge.compositional=True`, raise BEFORE
  any mutation.
* **Pushback 22-A** — `IntergraphEdge.__setattr__` enforces
  `compositional` immutability post-init.
* **Pushback 27-A** — `mindsos metagraph set-prop` 4-way mutex
  (extends 05a's 3-way with `--intergraph-edge-id`).
* **Pushback 28-A + DMS-A** — Unified `mindsos metagraph detach-schema`
  with raw-JSON fallback for stale `schema_name` references.
* **Test budget** — unlimited per `feedback_test_budget_unlimited.md`
  (locked rule for all future cascade phases). 145 in-process tests
  added; 3 CLI subprocess test files run in-container.

**Filed as future work** (`_source_backup/root/mindsos_future_plans.md`):

* Pushback 25-B — `Graph.role` immutability via `__setattr__` (Phase
  03 retroactive supersession trigger).
* Pushback 31-B — `update-intergraph-edge-label` CLI verb.
* Pushback 33-B — `mindsos metagraph` subapp two-level reorganization.
* Pushback 34-B — symmetric `remove-*-type` backfix across all schema
  kinds.

**2026-05-06 amendment (Phase 05c P11→P13-B retreat):**
A symmetric `update_intergraph_edge_endpoints` factory + CLI verb on
the binary primitive was considered for Phase 05c but rejected (cost
of triggering 05b-v2 supersession judged disproportionate to the
symmetry benefit). Documented workaround for re-pointing endpoints
on a NON-compositional `IntergraphEdge` while preserving `edge_id`:

```sh
mindsos metagraph remove-intergraph-edge --name MG --intergraph-edge-id E
mindsos metagraph add-intergraph-edge --name MG \
    --source-graph G --source-node N \
    --target-graph G2 --target-node N2 \
    --type T --intergraph-edge-id E
```

The `--intergraph-edge-id <orig>` override flag (Push14-A) is the
load-bearing mechanism that preserves edge_id stability across the
remove + add. Compositional edges have no recovery path — they are
truly immutable per design §4.3 + Pushback 6-A. Future work entry filed
at `_source_backup/root/mindsos_future_plans.md` "Intergraph primitive
structural mutation" / "Discoverable endpoint-update verb for
IntergraphEdge". Permanent regression test at
`tests/phase_05c/test_cli_intergraph_hyperedge.py::TestP13BWorkaround`
covers the workaround under 05c (P31).

State files: metagraph state v=1 → v=2 cumulative one-way migration
(adds `intergraph_edges` array + `schema_name` reference). New
`metagraph-schema-<n>.json` v=1 state-file kind. `RESERVED_PROPERTY_KEYS`
extends with `intergraph_edges`, `schema_name`, `_compositional`.
`CompositionalImmutableError` re-shipped (R3-B 05a stripped).
`Metagraph.mint_id` ADR-0131 helper landed (P7 carry-forward;
consumer = IntergraphEdge factory).

## Phase 05a — L1 Metagraph slim port (2026-05-05)

**`Metagraph` + `MetaEdge` + `MetaHyperEdge` ship** as a slim port of
the parent `mindsos_core/models/metagraph.py`, with 19 round-1-4 design
picks folded into the shape:

* **P1** — soft-delete fields (`deprecated_at` / `disputed_at`) stripped
  from `MetaEdge` / `MetaHyperEdge`. Phase 10 lands the substrate
  uniformly across all 4 edge variants (audit recommendation honored).
* **P3** — **`CompositionalMetaEdge` dropped entirely** (N3-D + P3 lock).
  ADR-0117 status flips Reserved → **Withdrawn in 05a** (one phase
  earlier than the original CASC-1 placement). The compositional concept
  moves to a flag on the intergraph primitives in 05b/05c.
* **P8** — `MetaEdge` and `MetaHyperEdge` use `@dataclass(kw_only=True)`.
* **P9** — `__post_init__` cypher rel-type regex (ADR-0021) enforced on
  `type_name` for both edge types.
* **P11** — Factories take graph_id strings (`source_graph_id` /
  `target_graph_id` / `graph_ids: List[str]`) — NOT `Graph` objects.
  Persistence stores graph **names** (CLI translates name→id at
  boundary).
* **P15** — `add_metaedge` refuses self-loop (`source == target`).
  `add_metahyperedge` refuses < 2 members.
* **P16** — `add_graph` invariants: `g.identity is mg.identity` post-call
  (shared reference, not clone); `g.id_strategy` is **untouched**
  (mixed-strategy metagraphs supported).
* **P19** — `remove_graph(graph_id)` is single-behavior always-cascade
  (no `cascade` parameter, no `force`, no `RemovalImpact` return).
  Phase 10 reintroduces.

**`mindsos metagraph` CLI subapp ships** with 13 subcommands (Q2 + CR-A):
`create / inspect / list / reset / add-graph / remove-graph /
add-metaedge / remove-metaedge / add-metahyperedge /
remove-metahyperedge / set-prop / list-metaedges / list-metahyperedges`.

* **P10 JSON shapes locked** for `inspect` and `list`.
* **P17** — `set-prop` 3-way mutex `--on-metagraph | --metaedge-id |
  --metahyperedge-id`. The `--on-metagraph` marker flag operates on the
  metagraph's own ADR-0130 property bag.
* **P5** — `reset --force` and `reset --all` require `--yes`.
* **Q4-B + P2** — Standalone `mindsos graph` mutations refused on
  metagraph-owned graphs with stderr suggestion of the equivalent
  `mindsos metagraph ...` invocation. Reads (`inspect`, `list-*`)
  warn-and-show.
* **DM-A** — `mindsos graph detach-metagraph` recovers a dangling
  back-pointer.
* **N7-A** — `metagraph add-graph` refuses if the graph already has a
  non-null `metagraph_name` back-pointer.
* **Q5-A** — Eager id-collision check on `metagraph add-graph`.
* **Q6-A** — `metagraph reset --name X` orphan check; `--force --yes`
  strips back-pointers from referencing graphs.
* **Q3-A** — `member_graphs` sorted by graph name (byte-stable).
* **P18** — `metagraph add-graph` two-file write order: graph state
  (back-pointer set) FIRST, then metagraph. Recovery on partial failure:
  DM-A.

**Graph state-file BUMPED to v=4** (B2 — adds optional
`metagraph_name: str | null` back-pointer field). Cumulative migration
chain at `mindsos_cli/migrations/graph.py` forward-migrates v=1 / v=2 /
v=3 → v=4 (P12/P14). **Phase 04-v2 binary loading v=4 file rejects**
with strict-version contract.

**Metagraph state-file v=1 — NEW state-file kind** at
`metagraph-<name>.json`. Migration chain at
`mindsos_cli/migrations/metagraph.py` (empty in 05a; future bumps in
05b / 05c / 10).

**Per-file migration chain modules** at `mindsos_cli/migrations/{graph,
schema,metagraph}.py` (P14). Replaces the inline switch statement in
`_state_to_graph` that previously grew O(N) per phase. Each module
exports `MIGRATIONS: List[Callable[[dict], dict]]` and a `migrate(state)
-> dict` entry point. Loaders in `mindsos_cli.state` call `migrate()`
after parsing JSON.

**`RESERVED_PROPERTY_KEYS` extended** (P13) at metagraph property scope:
`_state_version`, `contained_graphs`, `metaedges`, `metahyperedges`,
`metagraph_name`. `name` and `properties` deliberately **excluded**
(would break Phase 04 user-prop tests).

**ADR-0130 Accepted in 05a** (N1-A1) — `Metagraph.properties: Dict[str, Any]`
ships. Supersedes ADR-0029 (`:MetagraphSettings` JSON singletons).
Graph-level property bag deferred to Phase 10 per N1 distinction.

**Per-kind version constants:** `GRAPH_STATE_VERSION = 4`,
`SCHEMA_STATE_VERSION = 2` (unchanged from 04-v2),
`METAGRAPH_STATE_VERSION = 1` (NEW).

**Round-1-4 deferral list (carry-forward):**

* `Metagraph.mint_id` — Phase 05b (consumer = IntergraphEdge per P7).
* `_compositional` reserved-key addition — Phase 05b (per P6 — defer
  alongside the actual flag).
* `IntergraphEdge` (binary) — Phase 05b.
* `IntergraphHyperEdge` (n-ary) — Phase 05c.
* `MetagraphSchema` — Phase 05b.
* Soft-delete substrate uniform across 4 edge variants — Phase 10.
* `RemovalImpact` + `force=True` on `remove_graph` — Phase 10.
* `Graph.properties` (ADR-0130 graph-side) — Phase 10.
* `XRef` primitive — Phase 09.
* `mindsos_instances` package — Phase 06.

## Phase 04-v2 — L1 Schema additive expansion: HyperEdgeType (2026-05-04)

**Supersession trigger: expansion** (per PHASE_MAP §1 amended in this
phase to extend supersession-policy coverage from regression-only to
"regression OR additive scope expansion"). The `phase-04-confirmed` tag
remains in git history; install target for slot 04 is now
`phase-04-v2-confirmed`.

**`HyperEdgeType` ships (ADR-0017 amended in place — PA-1 lock).**
Frozen dataclass with `allowed_member_types: FrozenSet[str]`
(HET-1: simplest constraint surface; symmetric across all members; no
cardinality bounds; AME-1: empty list permitted, mirrors `EdgeType`
precedent), `property_types`, `description`. Validation extends:
`Schema.add_hyperedge_type` / `Schema.require_hyperedge_type` /
`Schema.validate_hyperedge` / `Schema.validate_hyperedge_properties`.
Schema attach eager validation runs Node → Edge → HyperEdge in order.

**`HyperEdge.type_name: str`** is now required (cypher rel-type regex
per ADR-0021 enforced at `__post_init__`). The CLI break (`add-hyperedge`
without `--type` no longer parses) is documented.

**Graph state-file BUMPED to v=3** (adds `type_name` per hyperedge
entry). **Schema state-file BUMPED to v=2** (adds `hyperedge_types`
map). Both migrations are **one-way cumulative**: 04-v2 binary tolerates
v=1 ∪ v=2 ∪ v=3 graph reads and v=1 ∪ v=2 schema reads; pre-current
files upgrade on first mutation.

**SENT-1 sentinel `"UNSPECIFIED"`** populates legacy hyperedges with no
`type_name` field on load (chosen to satisfy ADR-0021's cypher rel-type
regex — adversarial-round-1 surfaced the regex conflict with the
original `_unspecified` lowercase candidate).

**UHT-1: `mindsos graph update-hyperedge-type`** legacy-migration
recovery CLI. Asymmetric — `Edge.type_name` and `Node.type_name`
remain immutable; only `HyperEdge.type_name` is post-create mutable.

**`set-prop` 3-way mutex extends:**
`--node-id | --edge-id | --hyperedge-id`. `--replace` preserves `ref:*`
keys symmetrically.

**Per-kind version constants:** `GRAPH_STATE_VERSION = 3`,
`SCHEMA_STATE_VERSION = 2`. `STATE_VERSION` alias = `GRAPH_STATE_VERSION`.

**Tests added:** ~30 in `tests/phase_04_v2/`. Cumulative pytest baseline:
~409 + 2 skipped (in-container Python 3.12).

**Locks across rounds 0-7 + 5 adversarial rounds:**
MC-2 (override drop-MetaHyperEdgeType correction; ship symmetric
typed-hyperedge surface), HET-1, AME-1, MIG-1 (v=3 bump), SS-1
(schema v=2 bump), PA-1 (amend ADR-0017 in place), CASC-1 (sequential
04-v2 → 05a → 05b cascade), SENT-1, UHT-1, WARN-2 (empty-strict
warning unchanged), VERSTR-1 (`0.0.0+phase04.v2`), TRIG-1
(supersession trigger free-form in `tester_notes`).

## Phase 04 — L1 Schema (2026-05-04)

**Schema primitive (slim port of parent):** `Schema` class with opt-in
`strict=True`, `NodeType` / `EdgeType` (frozen dataclasses), full
8-variant `PropertyType` enum (`string` / `int` / `float` / `bool` +
4 list variants), `validate_user_properties` helper enforcing the
reserved-key + primitive-value contract. Two new exceptions
(`PropertyShapeError`, `UnknownTypeError`) inherit `CoreError`.

**Graph state file BUMPED to v=2.** Phase 03 wrote v=1; Phase 04 reads
both v=1 (legacy, `schema_name` field absent) and v=2 (current, with
optional `schema_name` field); writes v=2 on every save. **v=1 → v=2
migration is one-way**: first Phase 04 mutation upgrades the file;
Phase 03 binary then refuses with the existing strict-version contract.
Per-kind version constants split: `GRAPH_STATE_VERSION = 2`,
`SCHEMA_STATE_VERSION = 1`.

**`mindsos schema` CLI subapp (new):** `create [--strict]`, `add-node-type`,
`add-edge-type`, `inspect`, `list`, `reset`. Own state file at
`schema-<name>.json` (`SCHEMA_STATE_VERSION = 1`). `reset` walks every
graph state file checking `schema_name` references; refuses with exit 1
if any orphan would result; `--force` overrides (resulting graphs need
`graph detach-schema` to recover; warning emitted on stderr). Corrupt
PropertyType vocab in a state file raises `RuntimeError` → exit 1 with
the valid vocab listed (no Python traceback).

**`mindsos graph` extensions:**

* `create --schema <NAME>` — attach at creation time.
* `attach-schema --name G --schema S` — eager validation; first violation
  prints `node <id>: PropertyShapeError: ...` and exits 1; graph state
  file unchanged. Re-attach permitted; JSON output reports
  `previous_schema`. Empty-strict-schema warning on stderr.
* `detach-schema --name G` — clear `schema_name` via raw JSON
  manipulation (works even on dangling schema references). Exits 1 if
  no schema attached.
* `set-prop --name G (--node-id ID | --edge-id ID) --prop k=v ... [--replace]`
  — schema-validated property update. Flags renamed from `--node` /
  `--edge` for parity with `add-node --node-id`. `--replace` preserves
  `ref:*` cross-graph reference keys (user-supplied refs win on
  collision). NO CLI path to drop a `ref:*` key — recovery via
  hand-edit, or future Phase 09 XRef migration.

**`Graph.add_*` gain `_validate: bool = True` kwarg.** Rehydration
(`_state_to_graph`) calls with `_validate=False` to tolerate Phase 03
v=1 state files containing reserved-key or non-primitive properties
(Phase 03 had no `validate_user_properties` enforcement). Schema-level
checks always run; only the user-property contract is gated.
Mutations keep default `_validate=True`; recovery from poisoned
legacy nodes via `set-prop --replace`.

**Graph closures from Phase 03 deferral list:** `Schema` ctor param
restored on `Graph.__init__`; `update_node_properties` /
`update_edge_properties` added (no `_version` bump — Phase 07 OCC owns
that); `tests/unit/test_graph.py` ported back from parent (14 of 15;
1 skip for `_restore_node` pending Phase 08).

## Phase 03 — L1 Graph elements (2026-05-04)

Slim-port of `Graph` / `Node` / `Edge` / `HyperEdge` from the parent
project + Cypher rel-type validation (ADR-0021) + `mindsos graph` CLI
surface (create / inspect / add-{node,edge,hyperedge} / list-* / list /
reset) + JSON state-file persistence at
`${MINDSOS_STATE_DIR or ~/.mindsos}/graph-<name>.json` (parity with
Phase 02 identity-registry pattern; v1 schema with `_state_version: 1`,
atomic writes, byte-stable list ordering). Strips `Schema` (→ Phase 04),
graph-level `properties` (→ Phase 05/10), `_version` OCC (→ Phase 07),
soft-delete (→ Phase 10), reconstruction `_restore_*` (→ Phase 08).

## Phase 02 — L1 Identity (2026-05-04)

Slim `mindsos_core` (UUID / IdStrategy / IdentityRegistry) + `mindsos
identity {strategies, mint, registry}` CLI + entrypoint rework (drops
the doubled `mindsos` invocation; compose overrides entrypoint to
`["/usr/local/bin/entrypoint.sh", "mindsos"]`) + `doctor --self-test`
extension for version-string drift across manifest / pyproject /
`__init__.py` + `confirm-phase` preflight (`--static-only` flag on
doctor) + image-completeness regression test. IRI parsing deferred to
Phase 12 per ADR-0035.

## Phase 01 — Tooling infrastructure (2026-05-03)

GitHub Actions CI + Release workflows (push to `phase-*` runs in-container
tests; tag `phase-NN-confirmed` builds + creates Release with tarball +
Dockerfile snapshot + lockfile + checksums; retention prunes assets
older than 5 confirmed phases) + `mindsos confirm-phase` wrapper
(`--init-notes` writes notes template, `--phase --notes-file` generates
`PHASE_NN_CONFIRMED.md`) + extended `doctor --self-test` (workflow + compose
drift) + mkdocs-build CI step.

## Phase 00 — Runtime infrastructure (2026-05-02)

`mindsos` Docker image (multi-stage, Python 3.12.3 pinned by SHA256) +
FalkorDB sidecar (v4.18.3 pinned) + `docker-compose.yml` (host volumes
for FalkorDB persistence + CLI logs) + `mindsos_cli` skeleton (version /
help / doctor / doctor --self-test commands) + locked `requirements.txt`
via `pip-compile --generate-hashes` + `confirmation_docs/_template.md`
for hand-filled Phase 00 confirmation doc.
