---
last_confirmed_phase: 15a
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

### Phase 15a (shipped 2026-05-19) — DOLCE / OEWN / FrameNet importers in `mindsos_admin/`

Importers live at
`mindsos_admin/importers/{dolce,oewn,framenet}.py` (Phase 15a).
Phase 15b adds `alignments.py`. Per ADR-0140 §amendment-1 (Phase
15a): `mindsos_admin/` is the **permanent** home for admin
operations; §Decision §1+§2 routing to `mindsos_server/` is
superseded. No relocation phase is needed; Phase 37 row in PHASE_MAP
retired.

Each importer:

1. Self-describes its target role-graph via the
   `target_roles: tuple[str, ...]` class attribute (Phase 15a PB-22).
2. Parses its source (external file or pinned dataset version) — DOLCE
   via `rdflib`, OEWN-LMF + FrameNet XML via `lxml` (stdlib fallback).
3. Mints IRIs per
   [ADR-0045](../decisions/adr/0045-per-role-iri-builders.md) using
   Phase 12's `mindsos_knowledge.identifiers` 14-builder surface.
4. Auto-ensures its target role-graph (Phase 15a PB-14) via
   `mindsos_knowledge.bootstrap.ensure_global_role_graph` and writes
   nodes/edges/hyperedges via L1 mutation primitives directly.
5. Returns an `ImportResult` summary (role / version / source /
   imported_at / per-importer stats dict).

The Phase 15a importers ship pinned to specific dataset versions (PB-6
Round 1):

| Source | Version | License | Repo-shippable? |
|---|---|---|---|
| DOLCE | DOLCE-DUL 4.1 | Creative Commons | yes |
| OEWN | 2024 | CC-BY-SA 4.0 | yes |
| FrameNet | 1.7 | Berkeley click-through | NO — synthetic fixture only; downloader refuses |

Real-dataset acquisition: `scripts/fetch_datasets.{sh,py}` downloads
DOLCE-DUL 4.1 + OEWN 2024 into `data/datasets/` (gitignored).
FrameNet 1.7 requires manual download per Berkeley license; see
[framenet.md](../knowledge-sources/framenet.md).

Reruns against newer source versions register additional
version-graphs side-by-side (no in-place overwrite of `ontology-1`;
v2 lands as `ontology-2` per the versioning model — Phase 17 owns
the dispatch).

### Caller pattern — `bootstrap_global` (Phase 15a)

Per ADR-0042 §amendment-2 (Phase 15a) — third first-install sequence:

```python
from mindsos_admin import bootstrap_global, DolceImporter, OewnImporter, FrameNetImporter
from mindsos_knowledge import KnowledgeLayer

mg = bootstrap_global(importers=[
    DolceImporter("data/datasets/dolce-dul-4.1.owl"),
    OewnImporter("data/datasets/oewn-2024.xml"),
    FrameNetImporter("data/datasets/framenet-1.7/"),
])
# mg has all 6 named Global role-graphs ensured (Phase 15a PB-21
# parity with KL.bootstrap() output).
kl = KnowledgeLayer(global_metagraph=mg)
# Caller persists mg to FalkorDB out-of-band per ADR-0043.
```

Phase 15b adds the parametric `AlignmentsImporter(pairs=[(...),...])`
to the same pattern.

### CLI verbs (Phase 15a)

```
mindsos admin import dolce    --source PATH [--version V] [--json]
mindsos admin import oewn     --source PATH [--version V] [--json]
mindsos admin import framenet --source PATH [--version V] [--json]
```

Each verb is a dry-run that returns an `ImportResult` to stdout. State-
file persistence is deferred to Phase 26; server-driven persistence
ships at Phase 18+.

## Why admin owns this (not L3, not server)

Importers run at install / upgrade / pinned-release-bump time, **not
at cognitive-orchestration time**. L4's planner never plans against
"import DOLCE." That makes importers admin operations, not L3
capacities.

Per [ADR-0140](../decisions/adr/0140-server-owns-admin-operations.md)
§amendment-1 (Phase 15a): admin operations belong in
`mindsos_admin/`, **not** `mindsos_server/`. Server is the runtime
envelope (sessions, auth, HTTP, capability gates); admin is the
operations. Server (when built at Phase 18+) imports admin for HTTP
endpoint handlers; admin code is not server code.

ADR-0043 (Accepted) forbids file-I/O in `mindsos_knowledge/`. The
original ADR-0140 §Decision routed file-I/O importers to
`mindsos_server/`; Phase 15a's design pass surfaced that this routes
file-I/O code to a layer hosting session/HTTP machinery — a category
mismatch. The `mindsos_admin/` permanent-home decision (ADR-0140
§amendment-1) closes both problems: file-I/O OK in admin (no
ADR-0043 equivalent); no session/HTTP machinery required (admin-CLI
boundary).

## Capabilities required

Phase 18+ (when server's capability framework lands):

- `CAN_BOOTSTRAP_GLOBAL` — first-install Global metagraph creation.
- `CAN_RUN_IMPORTER` — running any of the 4 importers.

Both admin-scoped per ADR-0140 (Proposed). Phase 15a-15b operate at
the admin-CLI boundary only (no capability framework yet).

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

- [ADR-0042](../decisions/adr/0042-kl-install-extract-hooks.md)
  §amendment-2 (Phase 15a, **Accepted parent**) — third first-install
  sequence: importer-built Global → KL constructor.
- [ADR-0134](../decisions/adr/0134-schema-migration-scanner.md) —
  schema migration scanner (still Proposed; Phase 15a PB-2 declined
  the flip — no real schema bump consumer yet).
- [ADR-0139](../decisions/adr/0139-hybrid-invariant-home.md) — hybrid
  validators (importers use KL validators post-Phase 36).
- [ADR-0140](../decisions/adr/0140-server-owns-admin-operations.md)
  §amendment-1 (Phase 15a) — admin permanent home is
  `mindsos_admin/`; §Decision §1+§2 superseded.
