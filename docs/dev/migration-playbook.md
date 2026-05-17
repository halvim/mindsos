# Schema migration playbook

> **Stub** — landed Phase 11 (ADR-0134) as an anchor for the first
> real consumer. The full playbook content is owed when KL importers
> (Phase 12+) first bump a role-graph schema using
> `Schema.migrate_from` output.

## What Phase 11 ships

* `mindsos_core.schema.migrate_from(old, target, *, new=None,
  detail="summary", old_schema_name=None)` — detection-only scanner.
  See `docs/dev/internals/core.md` §"Schema migration scanner".
* `mindsos_core.reconstruction.load_graph_with_report` /
  `load_metagraph_with_report` — loader policy returning a structured
  drop report. See `docs/dev/internals/core.md` §"Loader policy
  plumbing".
* CLI: `mindsos schema migrate-check` + `mindsos persistence load
  --unknown-edges=warn|error|ignore`.

## What this playbook will document (when first consumer arrives)

The intended shape of this doc:

1. **Diagnose** — run `mindsos schema migrate-check --old <prior> --new
   <current> --metagraph <M> --json` against a representative dataset.
   Read `violation_count` and the per-bucket distribution.
2. **Classify** — categorise violations into "fix in data" (write a
   migration script) vs "accept as known stale" vs "roll back schema
   change."
3. **Author migration scripts** — domain-specific. KL imports re-flow;
   L3 derivations re-derive. The scanner output is the input.
4. **Verify** — re-run `migrate-check` post-migration; expect
   `violation_count: 0`.
5. **Audit-gate integration** — once ADR-0115 [Reserved] audit gate
   ships, `migrate_from` will be a release-time pre-check.

## Open items deferred from Phase 11

* **Apply-style migration in Core** (ADR-0134 §"Out-of-scope") — domain
  specific; layers handle their own apply paths.
* **Versioned schemas** with named migrations — first real schema bump
  surfaces the requirement.
* **`Schema.diff(old)` structural-diff helper** — useful for docs
  generation; deferred until a doc-generator consumer exists.
* **MetagraphSchema scanner** (PB-7 lock) — `MetaEdge` /
  `IntergraphEdge` / `MetaHyperEdge` / `IntergraphHyperEdge` type
  drops are out-of-scope for Phase 11; carry-forward to Phase 12+.

## Cross-references

* ADR-0134 — `docs/decisions/adr/0134-schema-migration-scanner.md` +
  §Revisions amendments-1 + 2 added Phase 11.
* `docs/dev/internals/core.md` §"Phase 11 — Loader policy + schema
  migration scanner".
* `confirmation_docs/PHASE_11_DESIGN_LOG.md` — design pushbacks
  PB-1..17 + 4 step-list PBs.
