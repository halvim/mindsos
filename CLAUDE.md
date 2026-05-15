This folder contains the code for MindsOS, a 5-layer intelligence system on FalkorDB metagraphs.

The five domain layers (the "stack"):

- **Layer 1 — Core** (`mindsos_core`). Graphs with nodes, edges, hyperedges; metagraphs (graph of graphs) with graphs as nodes, metaedges, metahyperedges. Plus identity, schema, persistence, reconstruction. **No reasoning.**

- **Layer 2 — Knowledge** (`mindsos_knowledge`). A metagraph where each contained graph is a knowledge role: ontology, lexicon, concepts, alignments, memories, promoted-pipelines, task-patterns, problem-trace, capacity-state, sense-correlations, learned-parameters. Global (shared) + per-user Local.

- **Layer 3 — Intellectual Capacity** (`mindsos_capacity`). Functions for acquiring and manipulating knowledge — perception, comprehension, derivation, decomposition, combination, path-finding, retrieval, scoring, trace, signalling, interaction, learning-methods. Capacities are fixed-not-learned (state lives in L4).

- **Layer 4 — Intelligence** (in design). Applied knowledge: per-session orchestrator, learner, attention queue, dreaming, replan, promotion proposing.

- **Layer 5 — Mental Model** (in design). Metagraph of L2 instances per task; the system's working memory.

Plus an **orthogonal Server layer** (`mindsos_server`) that owns auth, sessions, capability-based authorization, audit, persistence orchestration, and lifecycle. **Server is not on the layer-composition axis** — it provides a runtime envelope that any consumer of the domain layers (CLI, future web UI, batch jobs) needs. Domain layers do not import Server (per ADR-0010); Server imports downward into the stack.

Plus a sibling **Instances package** (`mindsos_instances`) per ADR-0132 (2026-04-27) that holds the mental-model instancing vocabulary (`ElementInstance`, `CompositeInstance`, etc.). `mindsos_core` retains backward-compat re-exports during the v4-v5 transition window.

Persistence layout: graphs live in **FalkorDB** (per ADR-0121); non-graph state lives in **SQLite** (`server.db` for auth/sessions/audit, `version_db/` for the pivot release manifest + node versions + peer deps).
