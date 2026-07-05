---
last_confirmed_phase: 15a
---

# Global + Local Metagraphs (Bootstrap stage)

This page describes the **Bootstrap** stage of the
[knowledge-lifecycle](knowledge-lifecycle.md) synthesis. It documents
the shape of the two long-lived metagraphs L2 owns — the system-wide
Global and the per-user Local — and the lifecycle hooks the server
uses to bring them into and out of memory.

Phase 14 owns this page. Subsequent phases amend specific sections:

| Stage              | Lives here? | Owner page                                        |
|--------------------|-------------|---------------------------------------------------|
| Bootstrap          | yes         | this page                                         |
| Authoring (Local)  | no          | [user-local-authoring.md](user-local-authoring.md) |
| Shipping (Global)  | no          | [admin-global-shipping.md](admin-global-shipping.md) |
| Promotion          | no          | [promotion-bridge.md](promotion-bridge.md)        |
| Versioning         | yes         | [../usage/knowledge/versioning.md](../usage/knowledge/versioning.md) (Phase 17 retired; one graph per role, version is IRI-string per ADR-0150 §amendment-3) |

## The two metagraphs

Per [ADR-0061](../decisions/adr/0061-dual-metagraph-global-local.md),
KL owns **one Global Metagraph** and a **lazy per-user dict of Local
Metagraphs**.

### Global

- Holds system-wide knowledge: ontologies, lexicons, concept frames,
  promoted pipelines, task patterns, and problem-trace records.
- Per [ADR-0044](../decisions/adr/0044-memories-move-to-local-per-user.md),
  ``episodic_memories`` and ``capacity-state`` are **not** in Global —
  they're per-user Local (Phase 39 rename per §am-3).
- Per [ADR-0150 §amendment-1](../decisions/adr/0150-l2-knowledge-lifecycle.md)
  (Phase 14), alignment pair-graphs (``alignment:<a>:<b>``) live in
  Global only.
- Written by admin importers (Phase 15) and by release-ship from the
  Local promotion path (Phase 16/23/24).

Bootstrap-fresh Global has **6 role-graphs**:

| Role                  | Source / driver                              |
|-----------------------|----------------------------------------------|
| `ontology`            | DOLCE importer (Phase 15)                    |
| `lexicon`             | OEWN importer (Phase 15)                     |
| `concepts`            | FrameNet importer (Phase 15)                 |
| `promoted-pipelines`  | Local-Promotion ship (Phase 16/23/24)        |
| `task-patterns`       | Local-Promotion ship (Phase 16/23/24)        |
| `problem-trace`       | L4 orchestrator (Phase 28-31 / Phase 33-35)  |

Plus alignment pair-graphs (``alignment:<a>:<b>``) created on demand
by Phase 15's Alignments importer.

### Local (per user)

- One Metagraph per `user_id`. Name: `local_knowledge:<user_id>`.
- Holds the user's autobiographical data (memories) and their per-
  capacity state (capacity-state).
- Lazily created on first access; or installed from FalkorDB at user
  login by the server per
  [ADR-0042](../decisions/adr/0042-kl-install-extract-hooks.md).

Local has **2 role-graphs** when minted (lazy or installed):

| Role             | What it holds                                          |
|------------------|--------------------------------------------------------|
| `episodic_memories` | Per-user task history (Episode + Memory composite); not Global per ADR-0044 §am-3. |
| `capacity-state` | Per-user L3 capacity state snapshots.                  |

## Lifecycle

### Global lifecycle

Per [ADR-0042 §amendment-1](../decisions/adr/0042-kl-install-extract-hooks.md)
(Phase 14) + [ADR-0042 §amendment-2](../decisions/adr/0042-kl-install-extract-hooks.md)
(Phase 15a): Global is **constructor-supplied**, not install-hook-
supplied. Three paths:

* **Empty first install (admin convenience).**
  ```python
  kl = KnowledgeLayer.bootstrap()  # fresh Global with 6 named roles, empty
  ```
* **Populated first install (importer flow — Phase 15a).**
  ```python
  from mindsos_admin import bootstrap_global, DolceImporter, OewnImporter, FrameNetImporter
  mg = bootstrap_global(importers=[
      DolceImporter("data/datasets/dolce-dul-4.1.owl"),
      OewnImporter("data/datasets/oewn-2024.xml"),
      FrameNetImporter("data/datasets/framenet-1.7/"),
  ])
  kl = KnowledgeLayer(global_metagraph=mg)
  # mg has all 6 named roles ensured; 3 populated by importers.
  ```
* **Server startup (warm restart).**
  ```python
  loaded_global = read_global_from_falkordb()  # server code
  kl = KnowledgeLayer(global_metagraph=loaded_global)
  ```

No `install_global_metagraph` hook exists; Global is lifetime-
coterminous with the KL instance. Both bootstrap paths produce
end-state-identical Metagraph shape (Phase 15a PB-21 parity); the
difference is content.

### Local lifecycle

Per [ADR-0042](../decisions/adr/0042-kl-install-extract-hooks.md): the
server brackets each user session with `install_local_metagraph` on
login and `extract_local_metagraph` on logout.

```python
# at login
loaded_local = read_local_from_falkordb(user_id)  # server code
kl.install_local_metagraph(user_id, loaded_local)

# at logout
local = kl.extract_local_metagraph(user_id)
write_local_to_falkordb(user_id, local)  # server code
```

* `install_local_metagraph(user_id, mg)` raises `AlreadyInstalledError`
  if a Local is already present for ``user_id``.
* `extract_local_metagraph(user_id)` raises `NotInstalledError` if
  no Local was installed.
* Both methods preserve object identity — the server gets back the
  exact `Metagraph` it installed.

If a caller skips the server entirely (testing / library use), lazy
`local_metagraph(user_id)` creates a fresh Local with the 2 Local-
named role-graphs ensured. Symmetric with bootstrap.

## Read access — `MetagraphView`

KL exposes two read views per [ADR-0138 Proposed](../decisions/adr/0138-kl-drops-write-api.md):

```python
global_view = kl.global_view()              # MetagraphView over Global
local_view = kl.local_view("alice")          # MetagraphView over alice's Local
```

`MetagraphView` is a **whitelist read-only wrapper** (Phase 14 PB-3
lock). It exposes:

- `metagraph_id` / `metagraph_name` — identity.
- `roles()` — set of contained role-graph roles.
- `graphs_by_role(role)` — list of contained `Graph`s with `role==role`.
- `alignment_graph(role_a, role_b)` — `alignment:<a>:<b>` convenience.
- `get_node(role, node_id)` — first match.
- `iter_nodes(role, type_=None)` — iterate role-graph nodes.
- `get_edges(role, node_id, edge_type=None)` — incident edges.
- `step(role, node_id, edge_type=None)` — within-view selective walk.

**Read-only contract.** `MetagraphView` exposes no write methods.
Returned `Node` and `Edge` references are mutable L1 objects;
**callers must not mutate them through the view**. The contract is
about the KL surface having no mutation methods — L1's own
`Graph.add_node` etc. is the canonical write path (which Phase 33-35
`KLWriteHandle` reaches through `MetagraphView.graphs_by_role(role)[0]`,
not through a mutation method on the view).

## What's NOT here

- **`follow_ref`** cross-metagraph helper — defers to Phase 25 or
  first L3 capacity phase per Phase 14 PB-10 (v3 `step()` overlay
  contradicted its own §1.2 out-of-scope clause; the post-pivot
  model puts cross-metagraph composition at L3 / Mental Model).
- **`version=`** kwarg on `step()` — VACATED at Phase 17 retirement
  (2026-05-20) per
  [ADR-0150 §amendment-3](../decisions/adr/0150-l2-knowledge-lifecycle.md).
  The shipped one-graph-per-role invariant leaves "active version"
  undefined; version lives in IRI strings, enumerable via
  `MetagraphView.versions_in_role(role)` (Phase 17 retirement
  delivery).
- **Validators** — defer to Phase 36 per
  [ADR-0139 Proposed](../decisions/adr/0139-hybrid-invariant-home.md).
- **Write methods on KL** — `add_local_node` / `add_local_edge` /
  `add_local_alignment` / `promote` / `similarity_report` are deleted
  per [ADR-0138 Proposed](../decisions/adr/0138-kl-drops-write-api.md);
  writes land via L3 capacities in Phase 33-35.
- **CLI verbs over KL** — Phase 14 PB-13 partially closed at Phase 17
  retirement: `mindsos knowledge versions` shipped;
  `active-version` verb dropped per PB-15 vacuum (no graph-layer
  active-version state to surface). Other CLI verbs still deferred
  (state-file access at Phase 26 per Phase 14a round-3 lock).

## Source

Phase 14 design log §1 PB-1..16; ADR-0042 + §amendment-1, ADR-0043,
ADR-0044, ADR-0061, ADR-0138 (Proposed), ADR-0149, ADR-0150 +
§amendment-1.
