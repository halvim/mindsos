This folder contains the code for MindsOS, a 5-layer intelligence system on FalkorDB metagraphs.

The five domain layers (the "stack"):

- **Layer 1 — Core** (`mindsos_core`). Graphs with nodes, edges, hyperedges; metagraphs (graph of graphs) with graphs as nodes, metaedges, metahyperedges. Plus identity, schema, persistence, reconstruction. **No reasoning.**

- **Layer 2 — Knowledge** (`mindsos_knowledge`). A metagraph where each contained graph is a knowledge role. **Currently shipped (Phase 13):** ontology, lexicon, concepts, alignment:* (canonical `alignment:<a>:<b>` per ADR-0154; D1 reconciliation lands Phase 39), `memories` (renames to `episodic_memories` at Phase 39 per ADR-0044 §am-3), promoted-pipelines, task-patterns, problem-trace, capacity-state. **Phase 43 (Rail A) adds:** parameter-staging (Local), pending-promotions (Local+Global), capacity-gaps (Global), learned-parameters (Local+Global). Closed role-set: 8 → 12 after Phase 43 ships ADR-0150 §am-5. `sense-correlations` **withdrawn** as standalone role-graph (L2 chat D-L2-2; data lives in lexicon empirical-layer). Global (shared) + per-user Local.

- **Layer 3 — Intellectual Capacity** (`mindsos_capacity`). Functions for acquiring and manipulating knowledge — perception, comprehension, derivation, decomposition, combination, path-finding, retrieval, scoring, trace, signalling, interaction, learning-methods. Capacities are fixed-not-learned (state lives in L4). **L1/L3 reframe ships Phases 40-42** retire TYPE_COMPAT + Phase 31 resident infrastructure; introduce bipartite `produces`/`consumes` IntergraphEdges + family-specific dont-know contracts + DataState realm naming + capacity registration contract v2 (ADRs 0155-0159).

- **Layer 4 — Intelligence** (**architecture settled at Chat A 2026-05-28; ships Phases 46-47**). Per-session orchestrator, learner, attention queue, dreaming, replan, promotion proposing. Per Chat A R1 boundary: L4 = substrate + control flow only; all decisions/computations are L3 capabilities.

- **Layer 5 — Mental Model** (**architecture settled at Chat B 2026-05-31; ships Phase 48**). Three-sub-MM (knowledge / capacity / intelligence) per task; 6-level chain artifact (HintSet → MappingResult → Plan → Pipeline → PipelineRun → TaskRun); D'1 retention model (version-IRI freeze + pin-at-instantiation + lazy inline-on-retire); episode retained by default at task completion. Note-fork mechanism **retired**.

Plus an **orthogonal Server layer** (`mindsos_server`) that owns auth, sessions, capability-based authorization, audit, persistence orchestration, and lifecycle. **Server is not on the layer-composition axis** — it provides a runtime envelope that any consumer of the domain layers (CLI, future web UI, batch jobs) needs. Domain layers do not import Server (per ADR-0010); Server imports downward into the stack.

Plus a sibling **Instances package** (`mindsos_instances`) per ADR-0132 (2026-04-27) that holds the mental-model instancing vocabulary (`ElementInstance`, `CompositeInstance`, etc.). `mindsos_core` retains backward-compat re-exports during the v4-v5 transition window.

Persistence layout: graphs live in **FalkorDB** (per ADR-0121); non-graph state lives in **SQLite** (`server.db` for auth/sessions/audit, `version_db/` for the pivot release manifest + node versions + peer deps).

---

## For Claude / Cowork chats

**Read `HANDOFF.md` at the root FIRST.** It is the canonical entry point — the current state of MindsOS, the L4/L5 design state (settled vs contested), the 3 sister projects (DWF/WSD/FOL), the carry-forward backlog, and the per-chat-type required-reading map.

**Project status as of 2026-06-02 end-of-day:** Phase 38 closed the L0-L3 numbered-phase rollout. Four foundation chats closed May-June 2026 (Chat A L4 / Chat B L5 / L1-L3 reframe / L2 chat). **Chat C plan-authoring closed 2026-06-02** with `confirmation_docs/POST_PHASE_38_PHASE_MAP.md` — active plan for **Phases 39-49** (4-rail DAG: A rename+schema-v2; B reframe X1/X2/X3; C L0 substrate; D dream family — converging at L4 substrate Phase 46 → orchestrator → L5 → Integration C). **Phase 39 design pass closed 2026-06-02** (`PHASE_39_DESIGN_LOG.md`). **Phase 43 pre-R0 design pass closed 2026-06-02 end-of-day** (`PHASE_43_R0_PICKS_SEED.md` + `PHASE_43_R0B_DERIVATIONS.md`; chat opens at R1 impl-locks post `phase-39-confirmed`).

**S9 BLOCKER ACTIVE.** Post-Phase-38 corpus (HANDOFF.md, 4 chat closures, ADRs 0150 §am-4 + 0151-0159, `docs/decisions/` tree, `docs/_workbench/` tree, Phase 39/43 design artifacts, sister projects, archive) is **uncommitted on `main`.** Last commit is `5236857` (Phase 38). `confirmation_docs/A0_HOUSEKEEPING_COMMIT_CHECKLIST.md` (4-commit grouping A0-1…A0-4) MUST land before Phase 39 branches off `main`. Pre-Phase-39 Stream A item A1 (`release.yml` retention amendment per PB-R; `docs/_workbench/STREAM_A_BACKLOG.md`) lands after A0.

Two design chats are named as Stream B rail prerequisites and have not yet opened: `L0_SUBSTRATE_CHAT` (gates Phase 44) and `DREAM_FAMILY_CHAT` (gates Phase 45). Five downstream installation chats are sequenced post-Phase-49: `SKILL_ACQUISITION_PROCESS_CHAT`, `WSD_INSTALLATION_CHAT`, `FOL_INSTALLATION_CHAT`, `DWF_INSTALLATION_CHAT` (parallelizable; L2-only), `CODE_SKILL_INSTALLATION_CHAT`, `ADAPTER_FAMILY_CHAT`, `MAINTENANCE_CHAT`, `L4-v2 follow-up chat`. See `POST_PHASE_38_PHASE_MAP.md §6` for sequencing.

**Sister projects:** `projects/dwf_mapping/` (knowledge acquisition), `projects/wsd/` + `projects/fol/` (skill acquisition). Each has an `ANALYSIS.md` + `FUTURE_CHAT_PROMPT.md` + `source/`. See `projects/README.md` for the recommended chat ordering.

**Folder structure:** See `HANDOFF.md` §7.3 for the canonical layout.

**Note on naming:** This folder is `MindsOS/` locally; the git origin remote is `git@github.com:halvim/mindsos.git` (GitHub repo name `halvim/mindsos` — discrepancy intentional, see HANDOFF.md §7.1).

## Cowork project setup

When you (or a fresh chat) first open this folder:

1. In Claude desktop app → Cowork mode → Add new project → point at this MindsOS/ folder.
2. The CLAUDE.md (you are reading it) loads automatically as project instructions.
3. Read `HANDOFF.md` at the root.
4. For mkdocs preview: `pip install mkdocs mkdocs-material && mkdocs serve` → http://127.0.0.1:8000.

## Memory

Cowork memory is **per-project**. If this folder is opened as a fresh Cowork project (different from "Layered Intelligence" where the housekeeping was done), the memory entries don't migrate. `HANDOFF.md` is fully self-contained for this reason — memory `[[name]]` pointers in any doc are optimizations, not load-bearing.
