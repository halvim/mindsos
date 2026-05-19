---
last_confirmed_phase: 14a
---

# Admin-Global shipping (L2)

This page describes the lifecycle path for **admin-curated content**
that lands in the Global metagraph at install / upgrade / pinned-release
time. It's one of three sibling paths indexed by
[knowledge-lifecycle.md](knowledge-lifecycle.md); see also
[user-local-authoring.md](user-local-authoring.md) and
[promotion-bridge.md](promotion-bridge.md).

> Several ADRs cited below are still **Proposed**. This page amends
> (`last_confirmed_phase` flip) as each ADR's consumer phase ships.

## What ships via this path

Global role-graphs whose content originates from **external knowledge
sources** (importer-curated):

- `ontology` — DOLCE upper ontology.
- `lexicon` — Open English WordNet (OEWN).
- `concepts` — FrameNet semantic frames.
- `alignment:<role-a>:<role-b>` — cross-source alignments (per
  role-pair instantiation).

The other 3 Global role-graphs (`promoted-pipelines`, `task-patterns`,
`problem-trace`) carry **system-wide learned state** that originates
from Local promotion, not importers — see
[promotion-bridge.md](promotion-bridge.md).

## The import path

### Phase 15 (interim)

Importers live at
`mindsos_knowledge/importers/{dolce,oewn,framenet,alignments}.py`. Each
importer:

1. Parses its source (external file or pinned dataset version).
2. Mints IRIs per
   [ADR-0045](../decisions/adr/0045-per-role-iri-builders.md) (per-role
   builders).
3. Writes via the KL bootstrap path (`register_version_graph`).

The Phase 15 importers ship pinned to specific dataset versions; reruns
against newer source versions register additional version-graphs
side-by-side (no in-place overwrite of `ontology-1`; v2 lands as
`ontology-2` per the versioning model — Phase 17 owns the dispatch).

### Phase 37 (relocation per ADR-0140)

Importers relocate to `mindsos_server/importers/` per
[ADR-0140](../decisions/adr/0140-server-owns-admin-operations.md)
(Proposed). New capability gates:

- `CAN_BOOTSTRAP_GLOBAL` — first-install Global metagraph creation.
- `CAN_RUN_IMPORTER` — running any of the 4 importers.

Post-relocation, importers use L1 mutation primitives directly + KL
validators (per ADR-0139 Proposed). The pre-relocation L2 path emits
`DeprecationWarning` for one release window before being removed.

## Why admin owns this (not L3)

Importers run at install / upgrade / pinned-release-bump time, **not at
cognitive-orchestration time**. L4's planner never plans against "import
DOLCE." That makes importers admin operations, not L3 capacities.

Per [ADR-0140](../decisions/adr/0140-server-owns-admin-operations.md):
admin operations belong in `mindsos_server` alongside other admin paths
(`bootstrap`, `propose_for_promotion`, `release_update`). Co-location
keeps capability gating coherent (one module per capability category).

## Capabilities required

Post-Phase 37:

- `CAN_BOOTSTRAP_GLOBAL` — first-install Global metagraph creation.
- `CAN_RUN_IMPORTER` — running any of the 4 importers.

Both admin-scoped per ADR-0140 (Proposed).

## Release-ship vs admin-import (ownership boundary)

This page does **not** cover release-ship semantics (per-user
transactional promotion → pending_global → canonical ship). That is the
promotion path per Phase 14a round-3 PB-M1 ownership lock:

- **This page (`admin-global-shipping.md`)** = where Global content
  comes from when admin runs an importer.
- **[promotion-bridge.md](promotion-bridge.md)** = how Local-originated
  content reaches canonical Global via release.
- **`docs/concepts/release-model.md`** (forthcoming; Phase 24 owns) =
  per-user release semantics (`last_synced_release_id`, lazy migration,
  version-graph routing post-ship).

The three pages cross-link but do not overlap.

## Phase 13 carry-forward: real-user state-file access

The `mindsos knowledge schema validate` CLI shipped in Phase 13 (PB-6)
currently smokes via the `mindsos-test` image bind — `tests/phase_13/
fixtures/` is excluded from the prod image per
`feedback_sentinel_paths_runtime_only.md`. The real-user pattern (host
state-file in `~/.mindsos/`) requires explicit `-v` volume mount
discipline.

**Deferred to Phase 26 (Integration A)** per Phase 14a round-3 minor
lock. Phase 14 (the next code phase) is already loaded with bootstrap +
MetagraphSchema scanner + alignment-IRI builder; Phase 26 wires
real-user bind-mounts as part of its scripted scenario, natural home.

## References

Accepted:

- [ADR-0045](../decisions/adr/0045-per-role-iri-builders.md) — per-role
  IRI builders.
- [ADR-0150](../decisions/adr/0150-l2-knowledge-lifecycle.md) — closed
  role-set (defines the 4 importer-targeted Global roles).

Proposed (this page amends as they ship):

- [ADR-0134](../decisions/adr/0134-schema-migration-scanner.md) —
  schema migration scanner (Phase 15 flips Accepted).
- [ADR-0139](../decisions/adr/0139-hybrid-invariant-home.md) — hybrid
  validators (importers use KL validators post-Phase 36).
- [ADR-0140](../decisions/adr/0140-server-owns-admin-operations.md) —
  server owns admin operations + importers.
