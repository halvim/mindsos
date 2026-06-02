---
title: Schema migration scanner + loader warning on unknown edge types
status: Accepted
date: 2026-05-20
layer: L1
---

# ADR-0134: Schema migration scanner + loader warning on unknown edge types

**Status:** Accepted (flipped at Phase 15b ship — 2026-05-20 — per §amendment-3 §3b below; originally Proposed 2026-04-27)

**Date:** 2026-05-20

**Related:** ADR-0017 (schema strictness opt-in), ADR-0123 (verify_invariants — schema scan can integrate).

## Context

Core has no schema migration tooling. Adding an `EdgeType` to a live `Schema` works in-memory but has no effect on already-persisted data. Existing rows of that edge type (if any existed under a looser schema) are not validated; new writes hit the tighter rules. There is no helper to "migrate existing data to the new schema."

Two consequences:

1. **L2 redesign** (the next chat) will harden role-graph schemas as part of the redesign work. Without migration tooling, the choice is "drop and reimport" (loses user Locals) or "ad-hoc migrations per PR" (no contract).
2. **Loader silently drops unknown edge types.** `GraphLoader` only loads edges whose type name is in the schema. An edge type persisted under an older/looser schema and dropped from the current schema becomes invisible on reload. Silent data loss.

The L1 redesign session resolved M11: scanner + loader warning. Versioned schemas with named migrations are deferred until first real version bump (likely L2's first hardening).

## Decision

Two pieces:

### 1. `Schema.migrate_from(old_schema, on_violation="report")`

```python
class Schema:
    def migrate_from(
        self,
        old_schema: "Schema",
        *,
        on_violation: Literal["report", "raise"] = "report",
    ) -> list[SchemaViolation]:
        """Compare `self` (the new schema) against persisted data validated under
        `old_schema`. Return a list of violations: nodes/edges whose persisted
        properties don't fit the new schema's stricter rules.

        on_violation="report": collect all violations, return them.
        on_violation="raise": raise SchemaMigrationError on first violation.
        """
```

**What it scans:**

- Node types in `old_schema` that are removed in `self` — every persisted node of that type is flagged.
- Edge types in `old_schema` that are removed in `self` — every persisted edge of that type is flagged.
- Property types tightened (e.g., `INT` → `INT_NOT_NULL`) — every persisted node/edge with a violating property value is flagged.
- New required properties added — every persisted node/edge missing them is flagged.

**What it does NOT do:**

- Apply migrations. v1 is detection-only. The caller handles the violations (write a migration script, drop-and-reimport, accept-as-known-stale).

**Output (`SchemaViolation`):**

```python
@dataclass
class SchemaViolation:
    kind: Literal["removed_node_type", "removed_edge_type",
                  "tightened_property", "missing_required_property"]
    type_name: str
    node_or_edge_id: str
    detail: str  # human-readable description
```

### 2. Loader warning on unknown edge types

`GraphLoader.load` today silently filters edges whose type isn't in the active schema. This becomes a configurable warning:

```python
class FalkorConfig:
    unknown_edge_type_policy: Literal["warn", "error", "ignore"] = "warn"
```

**Behaviour:**

- `warn` (default): logs WARNING for each unknown edge type encountered, continues loading. Loaded `Graph.dropped_edge_count` reports the number.
- `error`: raises `UnknownEdgeTypeError` on first unknown type. Use in CI to catch silent drift.
- `ignore`: silent (the v1-pre-redesign behaviour). Use when intentionally loading a subset.

The default flips from "silently ignore" to "warn." That is the L1 redesign's stance: silent data loss is the worst kind of bug; a warning is the cheapest fix.

### Out-of-scope (deferred)

**Versioned schemas.** Each `Schema` carries a version; migrations are named transitions. Deferred to "first real schema bump in L2 redesign." Tracked in `docs/decisions/proposed.md` under L1.

**Apply-style migrations.** A `migration_script(violations).apply()` mechanism that mutates persisted data. Deferred — apply semantics are domain-specific (KL might re-import; L3 might re-derive). Higher layers handle their own migrations using the scanner output as input.

**Schema diff helper.** `Schema.diff(old)` returning structural-only diffs. Useful for docs generation; deferred until first real consumer.

## Rationale

The two pieces together cover the most painful gaps:

- **Scanner** gives a structured input to migration tooling without forcing Core to invent migration semantics. Higher layers (KL importers, L3 derivations) read the violations and write their own migrations.
- **Loader warning** flips the silent-drop-on-load anti-pattern. Default WARNING is loud enough for ops to notice; configurable to ERROR for CI.

The full "apply migrations" surface is intentionally deferred. Migration application is domain-specific; building a generic apply layer in Core would either be too generic to be useful or would constrain higher layers' migration patterns. Detection-only scanner is the universal building block.

## Consequences

**Good:**

- L2 redesign's schema hardening pass has detection tooling on day one. Migrations can be authored against a known violation set.
- Silent edge-type drops become discoverable. CI can run with `unknown_edge_type_policy=error` to catch regressions.
- The pivot's audit gate (ADR-0115 [Reserved]) can call `migrate_from` against the previous release's schema as a pre-ship check.

**Tradeoffs:**

- Scanner is O(N) over persisted data per run. Acceptable as an admin-runnable tool; not run on every load.
- Loader's default-to-WARN may produce noise in tests that intentionally have schema mismatches. Tests can override the policy or pre-filter.
- Detection-only doesn't fix anything; the actual migration is owed to the caller. Documented as expected.

**Coordinated changes:**

- `mindsos_core/schema/migration.py` (new) — `Schema.migrate_from`, `SchemaViolation`.
- `mindsos_core/persistence/falkor_config.py` — `unknown_edge_type_policy`.
- `mindsos_core/reconstruction/graph_loader.py` — honor the policy; track `dropped_edge_count`.
- `mindsos_core/exceptions.py` — `SchemaMigrationError`, `UnknownEdgeTypeError`.
- KL: importer authors can call `Schema.migrate_from` when bumping role-graph schemas.
- Pivot: ADR-0115's audit gate may call `migrate_from` (release-time pre-check).
- Tests: `tests/unit/core/test_schema_migration.py`, `tests/integration/test_loader_unknown_edge.py`.

## Alternatives considered

1. **Versioned schemas with named migrations** (`Schema(version=2)`, `migrations/0001_add_works_at.py`). Rejected for v1 — bigger surface; first concrete consumer (L2) hasn't run a real schema bump yet; defer until needs are known.
2. **Apply-style migration in Core.** Rejected — apply semantics are domain-specific; pushing them into Core forces Core to know about KL/L3 mutation patterns.
3. **Status-quo (silent drop on load).** Rejected — silent data loss is the bug class the redesign is trying to fix.
4. **Out-of-band migration scripts in `scripts/`.** Rejected as the *only* answer — fine as a complement, but Core needs detection so the scripts can run programmatically.

## Implementation references

- `mindsos_core/schema/migration.py` — scanner.
- `mindsos_core/persistence/falkor_config.py` — config knob.
- `mindsos_core/reconstruction/graph_loader.py` — policy enforcement.
- `mindsos_core/exceptions.py` — new errors.
- Tests: `tests/unit/core/test_schema_migration.py`.
- Documentation: `docs/dev/internals/core.md` (schema migration section), `docs/dev/migration-playbook.md` (generic playbook).

ADR moves from Proposed to Accepted when scanner + loader warning land, KL importers use scanner output for at least one role-graph schema bump, and `docs/dev/migration-playbook.md` documents the pattern.

## Revisions

### amendment-1 (Phase 11 ship — 2026-05-16) — WARN granularity = per-distinct-type with running counts

**Trigger:** The original Decision text said the loader "logs WARNING for each unknown edge type encountered." Ambiguous: per-edge (one WARN per row — 10k unknown rows produces 10k WARNs, floods logs) or per-distinct-type (one WARN per type, with a running count). Phase 11 PB-10 A locked the latter.

**Amended behavior:**

* The loader emits **one WARN per distinct unknown `type_name`** at end-of-load, carrying the running drop count for that type: `dropped N edge(s) of unknown type X in graph G (policy=warn; schema does not list this edge type)`.
* The per-element drop is still tracked structurally in `LoadReport.dropped_by_type[X]` so callers see the full distribution; the WARN log surface is the per-type aggregate only.

**Out-of-scope for amendment-1:** structured logging (per-graph-per-type aggregation records consumed by a log aggregator) — defer until a log-aggregator consumer exists.

### amendment-2 (Phase 11 ship — 2026-05-16) — Policy lives on loader call surface + env var, NOT on `FalkorConfig`

**Trigger:** The original Decision text and §"Coordinated changes" placed `unknown_edge_type_policy` on `FalkorConfig`. But `FalkorConfig` is the FalkorDB-driver configuration (substrate layer); the loader is a reconstruction concern. Putting reconstruction policy on driver config inverts the layer boundary.

**Amended placement:** the policy lives on:

1. The per-call kwarg `unknown_edge_type_policy: Literal["warn", "error", "ignore"] | None` on:
   * `mindsos_core.reconstruction.load_graph_with_report(...)`
   * `mindsos_core.reconstruction.load_metagraph_with_report(...)`
   * `MetagraphLoader.load_with_report(...)`
   * `mindsos_core.reconstruction.iter_load_graph(...)` (internal threading)
2. Env var fallback `MINDSOS_UNKNOWN_EDGE_POLICY` (per `feedback_cli_config_manifest_fallback.md` — env wins over hard-coded default; per-call kwarg wins over env).
3. Hard-coded default `"warn"` (per the ADR's "default flips" lock; unchanged).

`FalkorConfig` is untouched.

**Sibling discipline (PB-12 B + PB-13 A):** the report-returning variants are **additive siblings** — the Phase 08 `load_graph` / `load_metagraph` / `MetagraphLoader.load` signatures stay exactly as shipped. Plain callers see no behavior change; only `load_graph_with_report` consumers exercise the policy.

### amendment-3 (Phase 15b ship — 2026-05-20) — documentary alignment with Phase 11's shipped API + §closing relaxation + Status flip

Phase 15b is a design-only phase (PHASE_MAP §1 exception) that closes
the §amendment-3 carry-forward open since Phase 12. The amendment lands
in two subsections: 3a documents Phase 11's actually-shipped surface
(which the original §1 spec never reflected); 3b relaxes the §closing
criterion to match scanner's actual consumer model and flips Status
`Proposed → Accepted`.

#### amendment-3, §3a — documentary alignment with Phase 11's shipped API

**Trigger:** ADR-0134 §1 (`Decision.1. Schema.migrate_from(...)`)
specified `migrate_from(self, old_schema, *, on_violation="report") ->
list[SchemaViolation]` with four `ViolationKind` values
(`removed_node_type`, `removed_edge_type`, `tightened_property`,
`missing_required_property`). Phase 11 (PB-1 / PB-7 / PB-8 / PB-17 per
`halvim_mindsos/confirmation_docs/PHASE_11_DESIGN_LOG.md`) shipped a
richer surface that ADR-0134 never reflected. This sub-amendment
documents the actual signature + extensions.

**Amended behavior:**

1. **Signature lives at module level** (not `Schema` method) in
   `mindsos_core/schema/migration.py`:
   ```python
   def migrate_from(
       old: Schema,
       target: Graph | Metagraph,
       *,
       new: Schema | None = None,
       detail: Literal["summary", "each"] = "summary",
       old_schema_name: str | None = None,
   ) -> list[SchemaViolation]: ...
   ```
   * `target` is `Graph | Metagraph`; single entry point dispatches on
     `isinstance` (Phase 11 PB-17 C — "both per-Graph and
     per-Metagraph dispatch through one entry point").
   * `new` defaults to `target.schema` (per-Graph) or each contained
     `graph.schema` (per-Metagraph). Skips graphs whose schema is
     `None`.
   * `on_violation` from ADR-0134 §1 is dropped in favor of `detail`
     (Phase 11 PB-8 A); raise-on-violation is achievable via caller
     post-check of the returned list.
   * Returns `list[SchemaViolation]` (empty list when schemas are
     compatible).

2. **`ViolationKind` extended to five values** (Phase 11 PB-7 C):
   ```python
   ViolationKind = Literal[
       "removed_node_type",
       "removed_edge_type",
       "removed_hyperedge_type",  # ← added at Phase 11
       "tightened_property",
       "missing_required_property",
   ]
   ```
   `removed_hyperedge_type` covers HyperEdge family per Schema's
   tripartite structure (Node / Edge / HyperEdge). ADR-0134 §1's
   four-kind list is superseded.

3. **`DetailMode` adds aggregation surface** (Phase 11 PB-8 A):
   ```python
   DetailMode = Literal["summary", "each"]
   ```
   * `summary` (default): one `SchemaViolation` per `(kind, type_name,
     graph_id, property_name)` quadruple with `count` aggregating.
     `element_id` is empty string.
   * `each`: one `SchemaViolation` per offending element. `element_id`
     carries the node / edge / hyperedge id. `count` is always 1.
   * Rationale: pathological inputs (10k violations of one kind)
     produce 1 summary entry vs 10k each entries.

4. **`SchemaViolation` dataclass extended** (Phase 11 PB-7 deferred
   items + PB-8 + PB-17):
   ```python
   @dataclass(frozen=True)
   class SchemaViolation:
       kind: ViolationKind
       type_name: str
       element_id: str    # "" in summary mode
       graph_id: str      # always set
       property_name: str # "" for removed_*_type kinds
       count: int         # aggregate in summary; 1 in each
       detail: str        # human-readable one-liner
   ```
   * `frozen=True` — value object.
   * `graph_id` is always populated (per-Metagraph scans surface which
     graph carried each violation).

5. **`old_schema_name` policy warning** (Phase 11 PB-17 C):
   ```python
   migrate_from(old, mg, *, old_schema_name="ontology-v1")
   ```
   When set AND target is a Metagraph, the scanner emits a logger
   WARNING for each contained graph whose `schema_name` differs from
   `old_schema_name`; that graph is skipped (not a SchemaViolation —
   caller decides whether the mismatch is meaningful).

6. **`SchemaMigrationError`** is raised for invalid `target` type or
   invalid `detail` value. Inherits from `CoreError`. Lives in
   `mindsos_core/schema/migration.py` (NOT `mindsos_core/exceptions.py`
   as ADR-0134 §"Coordinated changes" originally listed). The
   `UnknownEdgeTypeError` from §amendment-2 (loader surface) does
   live in `mindsos_core/exceptions.py`.

7. **Implementation references updated:**
   `mindsos_core/schema/migration.py` is the module home.
   `tests/phase_11/test_migrate_from_unit.py` +
   `test_migrate_from_metagraph.py` are the test surface.
   `halvim_mindsos/docs/dev/migration-playbook.md` (Phase 15b)
   documents the API.

#### amendment-3, §3b — §closing criterion relaxation + Status flip

**Trigger:** ADR-0134 §closing originally read: "ADR moves from
Proposed to Accepted when scanner + loader warning land, **KL
importers use scanner output for at least one role-graph schema
bump**, and `docs/dev/migration-playbook.md` documents the pattern."
Phase 15a's ADR-0140 §amendment-1 (admin-package permanent home) +
Phase 15b's design-only reframe (AlignmentsImporter deferred sine die
per ADR-0150 §amendment-2) mean the middle clause's consumer model
never materialises. Scanner's actual consumers are admin-CLI scans
(Phase 26+) and release-gate audits (Phase 24+ per ADR-0144), not
import-time schema migration. The original §closing was written under
a consumer model that didn't survive Phase 15a's admin-package
decision.

**Amended §closing criterion:**

ADR moves from Proposed to Accepted when:
1. Scanner module ships (`mindsos_core/schema/migration.py`).
   ✓ Phase 11.
2. Loader warning surface ships (per amendments 1 + 2). ✓ Phase 11.
3. `docs/dev/migration-playbook.md` documents the API + at least one
   usage example. ✓ Phase 15b (per PHASE_15b_DESIGN_LOG §1 PB-21).
4. ~~KL importers use scanner output for at least one role-graph
   schema bump.~~ **Dropped.** The original criterion presupposed a
   consumer model (import-time migration) that ADR-0140 §amendment-1
   relocated; actual consumers are admin-CLI scans and release-gate
   audits, which materialise at Phase 26 + Phase 24+ respectively.
   Item 5 (test coverage demonstrating contract) replaces it.
5. Phase 11 test surface
   (`tests/phase_11/test_migrate_from_{unit,metagraph}.py` +
   `tests/phase_11/test_loader_policy_{unit,integration}.py`)
   demonstrates the API contract end-to-end. ✓ Phase 11.

All five criteria satisfied as of Phase 15b ship. **Status flips
`Proposed → Accepted` at this amendment** (frontmatter updated
above).

**Out-of-scope for amendment-3:**

* The `Schema.migrate_from` method form (vs the shipped module-level
  function) is not re-introduced — Phase 11's module-level form is
  load-bearing; rewriting to method form would break Phase 11's tests
  + downstream consumers.
* New ViolationKind values beyond the five — defer to whichever later
  phase first needs them.
* The `on_violation="raise"` mode from ADR-0134 §1 — Phase 11 picked
  `detail`-based aggregation instead; callers wanting raise-on-first
  can post-check the returned list.

See `halvim_mindsos/confirmation_docs/PHASE_15b_DESIGN_LOG.md` §1
Round 3.5 + Round 4 PB-13 / PB-14 / PB-16 for the multi-round
rationale chain.
