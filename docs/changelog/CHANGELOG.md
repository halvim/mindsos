---
last_confirmed_phase: 05d
---

# Changelog

Append-only, one line per shipped phase. Phase 38 consolidates into a
release-style summary.

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
