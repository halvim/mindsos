---
title: End-to-end — L0→L5 trivial-task slice
last_confirmed_phase: 49
---

# End-to-end — L0→L5 trivial-task slice

This cookbook walks a **trivial task** through all eight shipped packages —
Server (L0) → Core (L1) → Knowledge (L2) → Capacity (L3) → Intelligence
(L4) → Mental-Model consolidation (L5). It transcribes the Phase 49
Integration C scenario into prose. It is the **substrate** walk-through: it
shows the layers wired and co-functional, not a feature-complete reasoning
demo.

## What this cookbook does and does not do

**Does:** Drive L0 login, a read-side L3 invoke (`text.space_split`), the L4
six-phase task lifecycle over the v0 catalogs, L5 consolidation into an
Episode + Memory, the live Falkor persistence machinery (the Phase-44 native
round-trip), and a background dream step — all on one Knowledge Layer for one
user.

**Does NOT** (read these honestly):

- **No real cognition.** The L4 lifecycle runs over the `planning.*` /
  `phase1.*` / `orchestration.*` **v0 placeholder catalogs** (Phase 47). The
  Plan is a single leaf Milestone; the leaf Pipeline executes a *notional*
  step (`mindsos_intelligence/execution.py`) — it dispatches **no real L3
  capacity**. The feature-complete NLU/skill demo lands with the **WSD**
  installation chat, which atomically replaces the v0 catalogs.
- **The two slices are stitched, not a single chain.** The read-side
  `text.space_split` invoke and the write-side L4→L5 lifecycle share one
  session + KL, but the lifecycle does **not** consume the tokenize output.
  A true "your text is tokenized, then becomes the Episode" data-flow is
  WSD-gated. This cookbook keeps them co-resident to show the full surface
  area is wired.
- **Dream is driven synchronously.** The Phase-46 `DreamCycleTimer` runs the
  driver on a background thread in a live `IntelligenceLayer`; here the
  scenario calls the dream driver directly for determinism. Faithful
  episode→MM reconstruction, `replay_recorded`-vs-`re_execute_capacities`
  behavioral differentiation, and real ALS firing are **WSD-gated**.
- **No physical Falkor indexes ship.** The index *strategy* is decided
  (ADR-0181, PB-HHH) but no index DDL is created at v1 — see
  [Scaling](#scaling-falkor-indexes) below.

## Prerequisites

- A running `falkordb` sidecar (the docker-compose default) — required for
  the persister round-trip step.
- A working dir for `MINDSOS_SERVER_DB` + `HOME`.

## Seed

The read-side seed is the three-word string `"the cat sat"`;
`capacity:perception:text.space_split` returns `["the", "cat", "sat"]`. The
L4 task input is `{"text": "the cat sat"}`; the v0 lifecycle maps it to the
placeholder task-pattern `task-pattern:v0:trivial` regardless of content.

## Step-by-step

### 1. L0 — bootstrap admin + login

```
$ mindsos server bootstrap admin      # <stdin: a password>
$ mindsos server login admin          # <stdin: same password>
```

Auth via Argon2id, a session is issued, the token is written to
`~/.mindsos/token` (mode 0600), and `EVT_BOOTSTRAP` / `EVT_LOGIN` audit rows
are emitted. (L0 uses `server.db` (SQLite) + the token file — no Falkor.)

### 2. L2/L3 — build the stack + the read-side tokenize

The L4/L5 substrate has no CLI verb today; the scenario drives it through the
Python API. One `CapacityLayer` over one `KnowledgeLayer` holds every catalog
the slice needs:

```python
from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins import (
    install_planning_v0, install_phase1_v0, install_orchestration_v0,
    install_text_capacities, reset_v0_verdicts,
)
from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
from mindsos_capacity.builtins.dream import install_dream_capacities
from mindsos_capacity.builtins.text import DS_RAW_TEXT, DS_TOKENS
from mindsos_capacity.pipeline import find_pipeline
from mindsos_knowledge import KnowledgeLayer

kl = KnowledgeLayer.bootstrap()
layer = CapacityLayer(kl=kl)
for install in (install_planning_v0, install_phase1_v0, install_orchestration_v0,
                install_consolidate_capacities, install_text_capacities,
                install_dream_capacities):
    install(layer)
reset_v0_verdicts()

pipeline = find_pipeline(layer, start_datastate=DS_RAW_TEXT, target_datastate=DS_TOKENS)
# pipeline.steps[0].capacity_iri == "capacity:perception:text.space_split"
```

The read-side invoke goes through the L4 dispatcher (same path the lifecycle
uses):

```python
from mindsos_intelligence.dispatch import L4Dispatcher

class _Session:
    user_id = "alice"; session_id = "scenario-alice"
    def has(self, cap): return True   # Local own-user write needs no global cap

dispatcher = L4Dispatcher(layer, session=_Session(), kl=kl)
tokens = dispatcher.dispatch(
    "capacity:perception:text.space_split", {DS_RAW_TEXT: "the cat sat"}
).outputs[DS_TOKENS]
# tokens == ["the", "cat", "sat"]
```

### 3. L4 — run the six-phase task lifecycle

```python
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.orchestrator import Orchestrator

mm = MentalModel(session_id="scenario-alice", user_id="alice")
orch = Orchestrator(dispatcher, mm, task_scope="integration-c")
outcome = orch.run_lifecycle({"text": "the cat sat"}, task_id="T1")
# outcome.status == "succeeded"; outcome.outcome == "task-pattern:v0:trivial"
```

Phase 1 (interpretation) → Phase 2 (Plan/Pipeline) → Phases 3–5 (execution
with bounded replan) → Phase 5→completion. The full chain artifact (HintSet →
MappingResult → Plan → Pipeline → PipelineRun → TaskRun) is emitted to the
intelligence sub-MM.

### 4. L5 — consolidation writes the Episode + Memory

On the terminal path (retain-by-default), the orchestrator freezes the MM and
dispatches `capacity:consolidate:mm`, which writes a 6-field Episode into the
user's Local `episodic_memories`, materialises the Memory composite for the
task-pattern, and wires the `MEMORY_CONTAINS_EPISODE` edge (ADR-0176). The
Local write needs no `CAN_WRITE_GLOBAL` — the ADR-0180 scope-aware gate only
fires for Global writes.

```python
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
from mindsos_knowledge.metagraph_view import MetagraphView

g = MetagraphView(kl.local_metagraph("alice")).graphs_by_role(ROLE_EPISODIC_MEMORIES)[0]
episodes = [n for n in g.nodes.values() if n.type_name == "Episode"]
# len(episodes) == 1; episodes[0].value["outcome_classification"] == "succeeded"
# exactly one Memory node, with one MEMORY_CONTAINS_EPISODE edge to the Episode
```

### 5. L0 — Falkor persistence machinery (and the episode-flush gap)

The Phase-44 native round-trip (`MetagraphRepository.persist` /
`MetagraphLoader.load`, which `FalkorDBLocalPersister` wraps) is exercised
live on the Global pair:

```python
from mindsos_core.config import FalkorConfig
from mindsos_core.persistence.client import FalkorClient
from mindsos_core.persistence import MetagraphRepository
from mindsos_server.persistence import bootstrap_global_pair_from_falkordb

client = FalkorClient(FalkorConfig.from_env())
canonical_kl, _ = bootstrap_global_pair_from_falkordb(client)
MetagraphRepository(client).persist(canonical_kl.global_metagraph())   # native round-trip
client.close()
```

**Persisting episodes — a known gap (PB-RT).** Flushing the *consolidated
Episode* to FalkorDB does **not** work at v1. The L0 node persister stores node
values as **primitives** (`build_unwind_create_nodes` sets `n.value =
row.value`); ADR-0130's `_props_json` JSON-encodes *metagraph* properties only,
not node values. The Episode node's `value` is a structured 6-field dict, which
FalkorDB cannot store as a native property. So `FalkorDBLocalPersister.save` of
an episode-bearing Local would error. **v1 Episodes live in the in-memory
Local** (Step 4); durable episode persistence needs node-value serialization,
routed to `_workbench/L0_FUTURE_WORK.md` (and the durable Falkor checkpoint
store deferred at Phase 48). Integration C surfaced this seam — that is exactly
what the first end-to-end exercise is for.

### 6. Background dream step

```python
from mindsos_intelligence.dream_cycle import run_dream_cycle

episode_iris = [iri for iri, n in g.nodes.items() if n.type_name == "Episode"]
descriptors = [{"source_episode_iri": episode_iris[0], "failed": False}]
directives = run_dream_cycle(dispatcher, descriptors, re_executor=lambda d: None)
# a non-failed episode -> 2 directives: replay_recorded (maintenance) +
#   re_execute_capacities (exploration). A failed episode adds a third
#   (dream.retry) carrying a ReplanInjectionDirective.
```

Live re-execution + ALS firing are WSD-gated; the `re_executor` hook is a
no-op here.

## Scaling: Falkor indexes

At trivial-task scope there is no query volume, and the persister round-trips
the whole Local metagraph rather than running indexed Cypher. **PB-HHH
(ADR-0181)** decides the index *strategy* but ships **no index code** at v1:
the indexes a future query consumer (WSD retrieval) should create are
`Episode.task_pattern_iri`, `Memory.memory_id`, and the cross-sub-MM
`IntergraphHyperEdge` membership relation. Physical creation is routed to the
first real query consumer, where it can be sized against real query shapes.

## What's been demonstrated

You drove a trivial task through **L0** (auth/session/audit + Falkor persist),
**L1** (Graph/Node primitives backing the role-graphs), **L2** (KL +
`episodic_memories`), **L3** (DataStates + capacities + pipeline finder +
invoke), **L4** (six-phase orchestrator over the v0 catalogs + dispatch +
chain artifacts), and **L5** (consolidation → Episode/Memory + retention).

## Reference: the Phase 49 integration test

Source: `tests/phase_49/test_integration_c_scenario.py` (+ the
`tests/phase_49/integration_c.py` harness). `test_chain_inmemory` is the
deterministic companion; `test_integration_c_scenario`
(`@pytest.mark.integration`) is the live-Falkor headline. The test is the
load-bearing smoke target for this cookbook — if the prose drifts from the
test, the test wins.

## What's next

- **WSD installation** replaces the v0 catalogs with real `process.*` /
  `predicate.*` / `hint.*` / `decision.*` catalogs + the ALS subsystems, and
  authors the `nlu-slice.md` cookbook (per `_workbench/cookbook_routing.md`).
- Read [Text realm — vertical slice](text-realm.md) for the read-side L0→L3
  slice, and [Concepts: layers](../../concepts/layers.md) for the layer model.
