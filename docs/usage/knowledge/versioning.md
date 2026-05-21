# Versioning in MindsOS Knowledge

> *Phase 17 RETIRED 2026-05-20. The "side-by-side role-graphs +
> active-version routing" framing in the Phase 17 row of PHASE_MAP
> turned out to be vacuous against the shipped one-graph-per-role
> invariant; this doc replaces it with what actually ships.*

## The model — one graph per role, version in the IRI string

Per [ADR-0150 §amendment-3](../../decisions/adr/0150-l2-knowledge-lifecycle.md#amendment-3-phase-17-retirement--2026-05-20--version-dispatch-model-lock),
MindsOS Knowledge dispatches role-graphs by **role string alone**.
Each metagraph contains **at most one graph per role**:

```
Global metagraph
├── ontology       (one graph; holds IRIs at ALL ontology versions imported)
├── lexicon        (one graph; holds IRIs at ALL lexicon versions imported)
├── concepts       (one graph; ...)
├── promoted-pipelines
├── task-patterns
└── problem-trace
```

Version is encoded **inside the IRI body**, not as a graph-layer
property. So if you import DOLCE 4.1 and then later import DOLCE 4.2,
both end up in the same `ontology` role-graph:

```
ontology role-graph contains:
  dolce-dul-4.1:PhysicalObject
  dolce-dul-4.1:Event
  ...
  dolce-dul-4.2:PhysicalObject
  dolce-dul-4.2:Event
  ...
```

`parse_iri(...).version` is the single source of truth for extracting
the version from any node id.

## What "active version" means — nothing, by design

There is **no** active-version state on `KnowledgeLayer` or
`MetagraphView`. There is **no** `version=` kwarg on
`MetagraphView.step`. There is **no** `(role, version)` discriminator
anywhere in the L2 surface.

When a caller walks the `ontology` role-graph, they see every
version's IRIs interleaved. Filtering to a specific version is the
caller's responsibility — typically by IRI-prefix check or
`parse_iri(...).version` comparison.

## What ships at Phase 17 retirement

### `MetagraphView.versions_in_role(role: str) -> set[str]`

IRI-scan enumerator. For each node in the role-graph, attempts
`parse_iri(node_id)` and collects `.version`. Nodes whose `node_id`
is not a version-qualified IRI (e.g., bare fragments or alignment-
graph member ids) are silently skipped.

```python
from mindsos_knowledge import KnowledgeLayer

kl = KnowledgeLayer.bootstrap()
# ... after DOLCE 4.1 + 4.2 imports ...
view = kl.global_view()
view.versions_in_role("ontology")
# {"4.1", "4.2"}
```

### `mindsos knowledge versions` CLI verb

User-facing surface backed by the same enumerator. Reads a metagraph
state-file by `--metagraph NAME` (mirrors Phase 03+ CLI convention).

```bash
$ mindsos knowledge versions --metagraph global_knowledge
ontology: 4.1, 4.2
lexicon: 2024
concepts: 1.7
promoted-pipelines: (no version-qualified IRIs)
task-patterns: (no version-qualified IRIs)
problem-trace: (no version-qualified IRIs)

$ mindsos knowledge versions --metagraph global_knowledge --role ontology
ontology: 4.1, 4.2

$ mindsos knowledge versions --metagraph global_knowledge --json
{
  "concepts": ["1.7"],
  "lexicon": ["2024"],
  "ontology": ["4.1", "4.2"],
  "problem-trace": [],
  "promoted-pipelines": [],
  "task-patterns": []
}
```

## What does NOT ship — and why

**`step(version=)` kwarg.** Phase 14 PB-15 deferred the kwarg to
Phase 17. Pre-impl probe at retirement established the deferral was
vacuous: there is no `(role, version)` discriminator in the model,
so there is nothing for the kwarg to dispatch on. The carry-forward
is vacated, not amended.

**`mindsos knowledge active-version` CLI verb.** Phase 14 PB-13
named it alongside `versions`. Dropped at retirement: with one graph
per role and version-in-IRI, there is no graph-layer active-version
state to surface. The notion of "active version" is undefined.

**Per-role version map on `KnowledgeLayer`.** Same reason. The map
would be a derivative of `versions_in_role` over every role-graph;
callers compose it from the enumerator if they need it (e.g., the
JSON output of the CLI verb is exactly this).

## PROMOTED breadcrumbs

The `ref_type="PROMOTED"` breadcrumb on Local draft nodes (per
[ADR-0051](../../decisions/adr/0051-promoted-ref-type-marks-surviving-draft.md))
is **produced** by the L3 promote write capacity at Phase 33 (per
[ADR-0146](../../decisions/adr/0146-l3-symmetric-write-invocation-contract.md)).
The L2 reader for PROMOTED breadcrumbs ships symmetric with the
writer at Phase 33 — there is no Phase-17-era reader because there
is no Phase-17-era writer.

The one shipped L2 PROMOTED-aware code today is
`mindsos_admin/similarity.py::list_candidates`, which **excludes**
PROMOTED nodes from candidate enumeration by default (Phase 16
PB-C2). That defensive exclude is the only L2 reader needed before
Phase 33.

## The escape clause — if multi-version coexistence ever matters

ADR-0150 §amendment-3 includes an explicit escape clause: if future
pressure surfaces for true multi-version coexistence in L2 (e.g.,
L4 wants `dolce-dul-4.1` and `dolce-dul-4.2` ontology graphs
coexistent under one Global metagraph with separate dispatch; or
admin-curated rollback needs prior versions accessible without full
re-import), the amendment may be re-opened. The lock is current-best
architecture, not eternal architecture.

## See also

- [ADR-0150 §amendment-3](../../decisions/adr/0150-l2-knowledge-lifecycle.md#amendment-3-phase-17-retirement--2026-05-20--version-dispatch-model-lock) — the version-dispatch model lock
- [ADR-0045](../../decisions/adr/0045-per-role-iri-builders.md) — per-role IRI builders (where version flows into IRIs)
- [ADR-0051](../../decisions/adr/0051-promoted-ref-type-marks-surviving-draft.md) — PROMOTED breadcrumb (Local-draft-after-promote)
- [global-local.md](../../concepts/global-local.md) — the Global/Local metagraph split
- [knowledge-lifecycle.md](../../concepts/knowledge-lifecycle.md) — full L2 lifecycle synthesis (Phase 14a)
