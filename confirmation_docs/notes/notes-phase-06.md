# Phase 06 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

L1 Instancing — ships sibling package `mindsos_instances/` with 8 element-instance subclasses (`NodeInstance` / `EdgeInstance` / `HyperEdgeInstance` / `SubGraphInstance` / `GraphInstance` / `MetaEdgeInstance` / `MetaHyperEdgeInstance` / `CompositeInstance`), `ElementRegistry` (per-metagraph in-memory registry), materialise machinery (full per-subclass dispatch + endpoint-resolution walk + composite tree), `canonicalize` utility, and an idempotent `attach_registry(mg)` helper that preserves the ADR-0010 Core/instances boundary. `mindsos_core` gains observer plumbing only — `register_remove_observer` on `Graph` + `Metagraph` for cascade-delete notification (precheck-style dispatch; observer-callback exceptions abort the originating remove atomically) plus `register_graph_added_observer` on `Metagraph` so late-attached graphs get subscribed. New `mindsos instances` CLI subapp with 4 verbs (`instantiate-node` / `instantiate-edge` / `instantiate-hyperedge` / `compose`) with `--materialise` flag, JSON-fragment `--override` parsing, and list→set coercion for set-typed structural fields. NO state-file bumps in Phase 06 (persistence is Phase 07). ADR file edits deferred to Phase 38 per 5-cascade precedent — the only on-disk ADR-ref change is `mindsos_core/__init__.py:54` (ADR-0024 → ADR-0015). Doctor self-test extended to verify 3-package version-string parity (`mindsos_cli` / `mindsos_core` / `mindsos_instances`).

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

## tester_notes

Tester run on 2026-05-11 from Linux box (Python 3.12 + Docker Compose).
Final cumulative result: **1127 passed, 2 skipped** in-container
(`docker compose --profile test run --rm mindsos-test pytest -q` —
`578.40s / 0:09:38`). The 2 skips are the existing
`test_mkdocs_buildable.py` (mkdocs not in test image) and
`test_restore_node_registers_provided_id` (Phase 08 deferral). **+114
over 05d's 1013 baseline** = 90 Phase 06 library tests (in
`tests/phase_06/`) + 12 Phase 06 CLI subprocess tests + 12 newly-
passing existing-phase CLI tests (the in-container path is the canonical
baseline; sandbox-skipped because Python 3.10 lacks `tomllib`).

---

### Design + implementation timeline

**Design chat (locked 2026-05-11, 6 reanalysis rounds):** meta-plan
picks M1–M6 + design picks P1–P44 + 2 user overrides at P13 B
(SubGraphInstance defined as `(graph_id, node_ids, edge_ids)` triple)
and P24 B (template-removal cascade-removes instances). Full pick log:
`confirmation_docs/PHASE_06_DESIGN_LOG.md`.

**Implementation chat round-7 reanalysis (this chat, 2026-05-11):** four
sequential reanalysis passes added 21 pushbacks (P45–P65) BEFORE any
code landed. The pushback density (21 in one round) reflected the
design chat's reliance on row-text rather than on-disk audits — three
of the four passes caught factual errors in the original row. All 21
picks accepted by the user. Ledger:
`confirmation_docs/PHASE_06_IMPLEMENTATION_LOG.md` §1.

**Load-bearing round-7 reverses / refines:**

- **P45 B** — ADR file edits deferred to Phase 38 per cascade
  precedent. Audit found `docs/decisions/adr/` does not exist on disk
  (verified via Glob across `0014*`, `0015*`, `0017*`, `0132*` —
  zero matches). The original row §G plan to "rewrite ADR-0132's
  Decision section inline" was moot. 05d's implementation log §70
  documented the same finding for 0014/0017. Phase 38's batch port
  absorbs all amendments. Only on-disk ADR-ref fix that survives:
  `mindsos_core/__init__.py:54` stale `ADR-0024 / ADR-0025` →
  `ADR-0015` (per P19 A).
- **P46 C** — Instance ID derivation drops the overrides hash. The
  original P11 A formula `uuid5(NAMESPACE, f"{template_id}|{hash(overrides)}|instance")`
  was incompatible with P27 A mutable overrides; on top of that
  `UUID5FromContentStrategy`'s own docstring (`identity.py:86-92`)
  explicitly warns against content-addressable IDs for mutation-prone
  objects. New formula: `mg.id_strategy.generate("instance", content={
  "template_id": tid, "instance_seq": next_seq})` where `next_seq` is
  a per-template monotonic counter sourced from
  `ElementRegistry._next_seq_for(template_id)`. Instances stay stable
  under `set_override`. Canonicalize utility survives — repurposed for
  bundle-override change detection + round-7 P63 A composite-asdict
  JSON stability.
- **P47 C** — Universally-forbidden override-key list wording fix. The
  row's "universally forbidden: `id, template_id, kind, metagraph_id,
  source_id (where applicable), type_name`" contradicted the
  EdgeInstance per-subclass allow-list which permits `source_id`.
  `source_id` struck from the universal list as redundant wording.
- **P48 A** — `label` added to the EdgeInstance / HyperEdgeInstance /
  MetaEdgeInstance / MetaHyperEdgeInstance allow-lists. Audit found
  `label` is in `RESERVED_PROPERTY_KEYS` (`validation.py:45`) AND
  exists as a dataclass field on all 4 edge-family primitives — so
  it's structural, not a user property; admit it to the allow-list or
  forbid the natural deviation.
- **P49 B + A** — Core ships observer plumbing only (boundary-
  preserving per ADR-0010); new idempotent
  `mindsos_instances.attach_registry(mg)` helper constructs +
  attaches `ElementRegistry`. Original row Risk text wrongly said
  `Metagraph.__post_init__` constructs the registry, but `Metagraph`
  is a plain class with `__init__`, not a dataclass.
- **P50 A** — `CompositeInstance.__init__` requires `metagraph_id`
  kw-only argument. Empty composites legal; `add_member` validates
  member's metagraph_id equality (P43 C cross-metagraph rejection).
- **P51 A** — SubGraphInstance materialise spec made explicit: fresh
  `IdentityRegistry`, nodes via `dataclasses.replace(orig,
  node_id=new_uuid)` + deep-copy of `properties`, edges similar with
  endpoint remapping through `node_remap`, `role` inherited, no
  schema carried over.
- **P52 A** — Strike "observer unsubscribe on registry teardown" test
  category (~5 tests projected). P35 A locked Python-ownership
  lifecycle: while the metagraph lives the registry lives; there is
  no explicit teardown event to test.
- **P53 A** — CLI exit codes for the 4 verbs adopt the 05d split: 0
  success / 1 invariant violation (Override/SubGraph/CompositeCycle/
  CrossMetagraph/DanglingTemplate errors) / 2 resource-not-found
  (unknown template_id, unknown metagraph) / 3 reserved.
- **P54 B** — GraphInstance materialise = full deep-copy clone of the
  source Graph (all nodes/edges/hyperedges with fresh IDs, fresh
  IdentityRegistry, `role` inherited). Without this, GraphInstance
  would have been a useless class until Phase 10's property-bag work
  arrives.
- **P55 A** — `CompositeInstance.add_member` raises `IdentityError`
  if the member's id isn't currently in the registry. Closes the
  stale-ref bug-class: a cascade-removed instance object can still be
  held in caller code; without this check a ghost member would slip
  into a composite.
- **P56 A** — `ElementRegistry.remove(instance_id)` calls
  `mg.identity.unregister(instance_id)` after dict-delete. Closes the
  IdentityRegistry leak on cascade (instance IDs were registered into
  the shared mg.identity per P11 A; unregister was missing from the
  cascade chain).
- **P57 A** — Set-typed structural-field override keys
  (`member_ids` / `node_ids` / `edge_ids` / `graph_ids`) accept JSON
  list input + coerce to Python `frozenset` at override-set time.
  Duplicates dedup silently (matches Python set semantics).
- **P58 A** — Edge / HyperEdge / MetaEdge / MetaHyperEdge materialise
  with ID-overrides resolves to actual Core objects via a walk of
  `metagraph.graphs.values()` (`_resolve.resolve_node`,
  `resolve_nodes`, `resolve_graph`). O(G×N) walk; acceptable for
  Phase 06 single-call demo (P8 B + P12 B).
- **P59 A** — Cascade observer routes through
  `SubGraphInstance.node_ids` / `edge_ids` membership when an
  inner element is removed. Without this, removing a Node referenced
  inside a SubGraphInstance left the SubGraphInstance's P20 A
  invariant silently broken.
- **P60 A** — Rename `MetaHyperEdgeInstance.member_graph_ids` →
  `graph_ids` in the allow-list to match Core's
  `MetaHyperEdge.graph_ids: FrozenSet[str]` field (`metagraph.py:188`).
- **P61 A** — `CompositeInstance.bundle_overrides` validation routes
  through `validate_user_properties(scope="composite")`. Adds zero
  Phase 04 LOC (the `scope` parameter is a free-form `str`); gains
  reserved-key + `ov__` prefix protection on bundle overrides.
- **P62 A** — Package-integration checklist explicit in the row §K:
  `pyproject.toml` `packages.find` list, Dockerfile COPY directive,
  doctor self-test extension for 3-package version-string parity, +1
  new bump site at `mindsos_instances/__init__.py:__version__`. This
  pushback anticipated the B-06-T1 hotfix that surfaced when the
  Dockerfile COPY list missed the new package.
- **P63 A** — Composite materialise JSON output wraps `asdict` output
  in `canonicalize` for stable JSON ordering of set-typed fields.
  `asdict` on `HyperEdge.nodes: Set[Node]` produces non-deterministic
  list ordering — golden-output tests on `--materialise` flag would
  flake without this.
- **P64 A** — Override validation bifurcates routing: structural-
  allow-list keys go through typed validation (string for ID
  overrides, set/list for set-typed fields, primitive types for
  `label`); everything else routes through `validate_user_properties(
  scope=KIND)`. A key in `RESERVED_PROPERTY_KEYS` that lands in the
  user-property bucket raises `OverrideScopeError`. Lives in
  `mindsos_instances/models/_overrides.py` — zero Phase 04 surface
  change.
- **P65 A** — Observer-callback dispatch is precheck-style: each Core
  `remove_*` method invokes observer callbacks BEFORE the mutation; a
  callback that raises aborts the remove cleanly, no state mutation
  happens, the exception propagates to the caller. Replaced the
  original "snapshot → mutate → call observers → rollback on
  exception" pattern with the simpler precheck pattern.

**P66 (implementation pushback surfaced during library test run, 2026-05-11):**
9 of 90 `tests/phase_06/test_cascade_observer.py` cases failed because
cascade didn't fire when `Metagraph.add_graph(g)` happened AFTER
`attach_registry(mg)`. Root cause: `ElementRegistry.__init__`
subscribes to `metagraph.graphs.values()` snapshot at attach time
only — graphs added later got no per-Graph remove-observer
subscription. Fix: added `Metagraph._graph_added_observers` plumbing
list + `register_graph_added_observer(cb)` method; `add_graph` fires
every registered callback after the unification step;
`ElementRegistry.__init__` subscribes via the new hook. ~15 LOC in
Core + ~3 in registry. Mirrors the existing `_remove_observers`
pattern.

---

### Hotfix ledger (3 issues surfaced during tester run; fixed same chat)

**B-06-T1** — `Dockerfile` (both `prod` + `test` stages) + `tests/_shared/sentinel_paths.py` did not reference `mindsos_instances/`. Surfaced on first in-container pytest: collection errored 41× with `ModuleNotFoundError: No module named 'mindsos_instances'`. Fix: added `COPY mindsos_instances ./mindsos_instances` to both Dockerfile stages; extended `SENTINEL_PATHS` with 11 new Phase 06 entries (the new package's files + `mindsos_core/_observers.py` + `mindsos_cli/commands/instances.py`). First top-level package addition since Phase 02 — the round-7 P62 A package-integration checklist anticipated this footgun.

**B-06-T2** — CLI subprocess test fixture `populated_mg` in `tests/phase_06/test_cli_instances.py` used invented flag names (`--metagraph` on `graph create`, `--type-name`, `--source-id` / `--target-id`, `--value` as a flag). Real Phase 03/05a signatures (audited from `mindsos_cli/commands/graph.py`): `graph create --name N --role R` (NO `--metagraph` — metagraph attachment is a separate `metagraph add-graph` step); `graph add-node <value> --name N --type T --json` (value positional, `--type` not `--type-name`); `graph add-edge --name N --source ID --target ID --type T --json` (NO `-id` suffix on endpoint flags). Additionally: mutations on metagraph-owned graphs are REFUSED by `_refuse_if_metagraph_owned` (Q4-B), so the fixture had to reorder: **build the graph standalone first, THEN attach to the metagraph**. Fix: rewrote `populated_mg` with correct signatures + the standalone-first ordering.

**B-06-T3** — Unknown `--metagraph` argument exited 1 instead of 2. `test_instantiate_node_unknown_metagraph_exits_2` asserted `1 == 2`. Phase 06 row §H (round-7 P53 A) maps "resource-not-found" → exit code 2; the underlying Phase 05a `_load_or_die` raises `typer.Exit(code=1)` on `FileNotFoundError`. Fix: wrapped `_load_or_die` in `mindsos_cli/commands/instances.py` (`_load_or_die_local`) to convert exit code 1 → `EXIT_NOT_FOUND` (=2) for all `instances` verbs. Phase 05's other subapps unaffected.

---

### Files created / modified

**Created (15 new files):**
- `mindsos_instances/__init__.py` — public API: 8 subclasses + ElementRegistry + attach_registry + canonicalize + 5 exceptions.
- `mindsos_instances/exceptions.py` — DanglingTemplate / CompositeCycle / CrossMetagraphComposite / SubGraphInvariant / OverrideScope errors.
- `mindsos_instances/_resolve.py` — `resolve_node`, `resolve_nodes`, `resolve_graph` helpers (round-7 P58 A endpoint resolution).
- `mindsos_instances/materialise.py` — per-subclass materialise dispatch + composite tree + `_clone_graph_subset` shared by SubGraph/Graph instances.
- `mindsos_instances/registry.py` — ElementRegistry (add/get/remove/iter/_next_seq_for/_mint_instance_id) + idempotent `attach_registry(mg)`.
- `mindsos_instances/utils/__init__.py` — re-export.
- `mindsos_instances/utils/canonicalize.py` — `canonicalize()` function: recursive set→sorted-list / dict→str-keyed / primitives passthrough.
- `mindsos_instances/models/__init__.py` — re-exports.
- `mindsos_instances/models/_overrides.py` — `validate_overrides` + `split_single_override` (round-7 P64 A bifurcation).
- `mindsos_instances/models/element_instance.py` — base `ElementInstance` + 7 concrete element subclasses + `CompositeInstance`.
- `mindsos_core/_observers.py` — observer plumbing: `ObserverHandle`, `_register`, `_dispatch_precheck`, `RemoveCallback` type alias.
- `mindsos_cli/commands/instances.py` — 4-verb CLI subapp + `_parse_override_pairs` + `_load_or_die` wrapper + error→exit-code mapper.
- `tests/phase_06/__init__.py` + `conftest.py` (mg / mg_with_graph / reg fixtures).
- `tests/phase_06/test_subclass_construction.py`, `test_overrides_bifurcation.py`, `test_subgraph_invariant.py`, `test_materialise.py`, `test_composite.py`, `test_cascade_observer.py`, `test_canonicalize.py`, `test_cli_instances.py` (102 net new tests; 90 in-process + 12 subprocess CLI).
- `confirmation_docs/PHASE_06_IMPLEMENTATION_LOG.md` — round-7 ledger (P45–P65) + §3 implementation bug-ledger (P66 + B-06-T1/T2/T3).

**Modified:**
- `mindsos_core/__init__.py` — line 54 stale ADR-0024/0025 reference → ADR-0015 (P19 A); version bump line 163 `+phase05d` → `+phase06`.
- `mindsos_core/models/graph.py` — observer plumbing imports + `_remove_observers` field in `__init__` + `register_remove_observer` method + `_dispatch_precheck` calls in `remove_node` / `remove_edge` / `remove_hyperedge`.
- `mindsos_core/models/metagraph.py` — observer plumbing imports + `_remove_observers` + `_graph_added_observers` (round-7 P66) fields in `__init__` + `register_remove_observer` + `register_graph_added_observer` methods + `_dispatch_precheck` calls in 5 remove methods (remove_graph / remove_metaedge / remove_metahyperedge / remove_intergraph_edge / remove_intergraph_hyperedge) + add_graph fires graph_added callbacks.
- `mindsos_cli/app.py` — registers `instances_app`; help-string bumped to Phase 06.
- `mindsos_cli/__init__.py` — version bump `+phase05d` → `+phase06`.
- `mindsos_cli/manifest.toml` — `phase = "06"`, `version = "0.0.0+phase06"`.
- `mindsos_cli/commands/doctor.py` — extracted `_read_package_init_version(package)` helper; extended self-test to assert `mindsos_core` AND `mindsos_instances` `__version__` match manifest (round-7 P62 A — 3-package version-string parity).
- `pyproject.toml` — `packages.find` includes `mindsos_instances*`; project version + description bumped.
- `docker-compose.yml` — image tags `mindsos:phase05d-*` → `mindsos:phase06-*` (2 sites).
- `docs/changelog/CHANGELOG.md` — Phase 06 entry prepended; `last_confirmed_phase` bumped to `06`.
- `confirmation_docs/PHASE_MAP.md` — Phase 06 row §A–§J amended to reflect P45–P65 picks; new §K Package integration added; row §G ADR-edits-deferred-to-Phase-38 + the single on-disk fix at `__init__.py:54`.
- `confirmation_docs/PHASE_05d_DESIGN_LOG.md` — historical-pointer banner added (round-7 reshape narrative for forward readers).
- **B-06-T1 hotfix files:** `Dockerfile` (prod + test stages COPY `mindsos_instances`); `tests/_shared/sentinel_paths.py` (+11 entries).
- **B-06-T2 hotfix files:** `tests/phase_06/test_cli_instances.py` (fixture rewrite with correct flag signatures + standalone-first ordering).
- **B-06-T3 hotfix files:** `mindsos_cli/commands/instances.py` (`_load_or_die` wrapper for exit-code conversion 1→2).

---

### Manual exploration outcomes (Phase 06 surface)

- **Step 1** branch push: clean (init commit + 2 hotfix commits + notes file commit, all on `phase-06`).
- **Step 2** image rebuild: clean after B-06-T1 hotfix (`Successfully tagged mindsos:phase06-test`).
- **Step 3** in-container baseline: **1127 passed, 2 skipped** in 578.40s.
- **Step 4** doctor `--self-test` exit 0; 3-package version-string parity check confirms `mindsos_cli` / `mindsos_core` / `mindsos_instances` all at `0.0.0+phase06`.
- **Step 5a** CLI setup (3 nodes + 1 hyperedge + metagraph + add-graph): all exits 0; UUIDs captured.
- **Step 5b** `instances instantiate-hyperedge` with `--override "member_ids=[a,b]" --materialise`: exit 0; materialised HyperEdge has `type_name=SPELLS` + 2 nodes (a + b only, c filtered) — validates round-7 P57 A list→set coercion + P58 A endpoint resolution at the CLI boundary.
- **Step 5c** `instances compose` with repeated `--bundle-override`: exit 0; bundle_overrides has both `priority=5` + `tag="demo"` — validates the repeatable flag.
- **Step 5d** subapp discoverability: `mindsos --help` lists `instances`; `mindsos instances --help` lists exactly the 4 verbs (compose / instantiate-edge / instantiate-hyperedge / instantiate-node).

---

### Recipe deviations corrected during run (recipe text now matches reality)

- Original Step 5 recipe used `--metagraph` on `graph create` (does not exist), `--type-name`/`--source-id`/`--target-id` (real flags: `--type`/`--source`/`--target`), `--value` as a flag (real: positional argument), `--node` on `graph add-hyperedge` (real: `--member`). All corrected.
- Original Step 5 ordering created the metagraph first then tried to attach the graph at create-time; real flow is `graph create` standalone → populate nodes/edges → `metagraph create` → `metagraph add-graph` (after which the graph is metagraph-owned and further mutations are refused by `_refuse_if_metagraph_owned`).

### Open questions surfaced during testing

*(none)*
