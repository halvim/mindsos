---
last_confirmed_phase: 04-v2
---

# Changelog

Append-only, one line per shipped phase. Phase 38 consolidates into a
release-style summary.

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
