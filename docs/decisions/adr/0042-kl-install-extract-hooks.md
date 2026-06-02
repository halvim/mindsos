---
title: Server-driven hydration via install_local_metagraph/extract_local_metagraph hooks
status: Accepted
date: 2026-04-22
layer: L2
aliases: [kl-ADR-005]
---

# ADR-0042: Server-driven hydration via install_local_metagraph/extract_local_metagraph hooks

**Status:** Accepted

**Date:** 2026-04-22

## Context

The server loads a user's Local metagraph from FalkorDB on login and saves it back on logout. Before the seam, KL's `local_metagraph(user_id)` lazily bootstrapped a fresh empty Local — there was no way for the server to say "start using this pre-loaded object" or "give me back what you've been writing."

## Decision

`install_local_metagraph(user_id, metagraph)` refuses with `AlreadyInstalledError` if a Local is already present. `extract_local_metagraph(user_id) -> Metagraph` pops the Local and returns the exact object, or raises `NotInstalledError`. Extract never persists; persistence is the server's decision.

## Consequences

**Good:**
- The server can wrap a FalkorDB transaction around the install/extract bracket.
- Object-identity is preserved across install/extract — no cloning, no serialisation roundtrip.

**Bad:**
- The server must always extract before installing a second Local for the same user.

## Alternatives considered

1. **Let KL know about the persistence layer directly** — rejected because it couples the layer.
2. **Single `set_local(user_id, mg)` method that silently replaces existing Local** — rejected because precision is lost.

## Revisions

### amendment-1 (Phase 14 ship — 2026-05-19) — Global lifecycle via constructor parameter

**Trigger:** ADR-0042 §Decision (2026-04-22) names `install_local_metagraph` /
`extract_local_metagraph` only. Phase 14 ships `KnowledgeLayer` as the first
class with Global state, and the server (Phase 18+) needs to hand KL a
pre-loaded Global on startup. The 2026-04-22 ADR is silent on the Global
counterpart, leaving Phase 14 to either (a) ship `install_global_metagraph`
as a symmetric hook or (b) accept Global via the `KnowledgeLayer.__init__`
parameter. Phase 14 picks (b) per round-2 PB-7.

**Amended behavior:**

* `KnowledgeLayer.__init__(global_metagraph: Metagraph | None = None,
  *, id_strategy: IdStrategy = UUID4Strategy())` — caller supplies a
  pre-loaded Global directly to the constructor, OR passes `None` and
  uses `KnowledgeLayer.bootstrap()` for a fresh-Global construction.
* The `install_local_metagraph` / `extract_local_metagraph` original
  shape stays verbatim for Locals; this amendment adds a parallel
  Global lifecycle without a hook method.
* Asymmetry rationale: there is exactly one Global per KL instance
  (lifetime-coterminous with the class); Locals are per-user, multiple,
  and need install/extract under session lifecycle. The constructor
  parameter handles the once-per-process Global lifecycle; install/
  extract hooks handle the per-user-session Local lifecycle.
* Server startup sequence becomes:
  1. Read Global from FalkorDB → `Metagraph`.
  2. `kl = KnowledgeLayer(global_metagraph=loaded_global)`.
  3. Per logged-in-user (warm-restart recovery): read Local from
     FalkorDB → `kl.install_local_metagraph(user_id, loaded_local)`.
* First-install sequence (admin command):
  1. `kl = KnowledgeLayer.bootstrap()` — creates fresh Global with
     6 named role-graphs ensured.
  2. Server persists Global + (initially zero) Locals to FalkorDB.

**Why constructor parameter over `install_global_metagraph` hook:**

A hook would imply a swap-after-construction semantics that has no
use case — KL never replaces its Global once installed. The
constructor parameter is honest about lifetime-coterminous: Global
is part of "what a KL instance is," not "what gets attached to it."

**Out-of-scope for amendment-1:** Global re-loading mid-process
(would require a Global-swap method; no consumer); Global extraction
back to a Metagraph for re-persistence (the server already holds the
reference it passed into the constructor; ADR-0043 puts I/O at the
server, not at KL).

See `halvim_mindsos/confirmation_docs/PHASE_14_DESIGN_LOG.md` §1 PB-7
for the decision rationale.

### amendment-2 (Phase 15a ship — 2026-05-19) — third first-install sequence: importer-built Global → constructor

**Trigger:** §amendment-1 (Phase 14) enumerates two first-install sequences:
(1) server startup warm-restart from FalkorDB, (2) `KnowledgeLayer.bootstrap()`
for empty admin install. Phase 15a ships
`mindsos_admin.bootstrap_global(importers=[...]) -> Metagraph` (Phase
15a PB-13 Round 3) that builds a populated Global from importer output,
then hands it to `KnowledgeLayer(global_metagraph=mg)`. Amendment-1
doesn't enumerate this third sequence; Phase 15a PB-16 (Round 3) locked
the gap closure.

**Amended behavior — third first-install sequence (importer-built Global):**

```python
from mindsos_admin import bootstrap_global, DolceImporter, OewnImporter, FrameNetImporter
from mindsos_knowledge import KnowledgeLayer

mg = bootstrap_global(importers=[
    DolceImporter("data/datasets/dolce-dul-4.1.owl"),
    OewnImporter("data/datasets/oewn-2024.xml"),
    FrameNetImporter("data/datasets/framenet-1.7/"),
])
# mg has all 6 named Global role-graphs ensured (Phase 15a PB-21 parity
# with KL.bootstrap() output); ontology/lexicon/concepts populated by
# importers; promoted-pipelines/task-patterns/problem-trace empty.
kl = KnowledgeLayer(global_metagraph=mg)
# Caller persists mg to FalkorDB out-of-band per ADR-0043.
```

* `bootstrap_global` is in `mindsos_admin/` per ADR-0140 §amendment-1
  (permanent home; supersedes §Decision §1+§2).
* End-state Global shape is identical to `KnowledgeLayer.bootstrap()`'s
  output (Phase 15a PB-21); the difference is content — 3 role-graphs
  populated vs all-empty.
* `KnowledgeLayer.bootstrap()` remains the empty-install convenience;
  `mindsos_admin.bootstrap_global` is the populated-install convenience.

**Rationale:** ADR-0042 §amendment-1's constructor-parameter mechanism
already accepts any-source Metagraph. Amendment-2 documents the
admin-package convention so reverse-engineering admin install paths
from code isn't required. Parallels §amendment-1's two-sequence
enumeration.

**Out-of-scope for amendment-2:**

* Re-import after KL is live (Global-swap) — §amendment-1 §Out-of-scope
  retains the "no Global-swap method; no consumer" lock. Importer-built
  re-imports use the process-restart pattern (kill process, run
  `bootstrap_global` again, start new KL).
* Per-user Local importer flow — no consumer; Locals are user-
  authored per ADR-0044.
* Partial re-import (replace one role-graph) — no consumer.

See `halvim_mindsos/confirmation_docs/PHASE_15a_DESIGN_LOG.md` §PB-13 /
§PB-16 / §PB-21 for the rationale chain.
