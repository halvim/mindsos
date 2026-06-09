# Facts and figures (Phase 48)

Quick-reference tables for the L4/L5 substance shipped through Phase 48.

## Layers and packages

| Layer | Package | One-line role |
|---|---|---|
| L0 Server | `mindsos_server` | auth / sessions / authorization / audit |
| L1 Core | `mindsos_core` | graphs, metagraphs, schemas, persistence primitives |
| L2 Knowledge | `mindsos_knowledge` | role-graphs; Global + per-user Local |
| L3 Capacity | `mindsos_capacity` | fixed-not-learned capability families |
| L4 Intelligence | `mindsos_intelligence` | orchestrator + MM substrate + dispatch |
| L5 Mental Model | (L4 + L2) | per-task working memory → retained Episodes |

## The six-phase task lifecycle

| Phase | Name | Produces |
|---|---|---|
| 1 | Interpretation | HintSet + MappingResult |
| 2 | Plan + Pipeline construction | Plan (+ Milestones), per-leaf Pipelines |
| 3–5 | Execution | PipelineRuns (DFS order) |
| 6 | Failure diagnosis | BlameVerdict |

## The 6-level chain of artifacts

HintSet → MappingResult → Plan (+ Milestone tree) → Pipeline → PipelineRun →
TaskRun. All emitted into the intelligence sub-MM under the MM writer lock.

## Episode and Memory (L2 `episodic_memories`)

| Entry | Key fields |
|---|---|
| **Episode** | `task_input_ref`, `mm_root_ref`, `task_pattern_iri`, `outcome_classification`, `crash_marker`, `consolidated_at` |
| **Memory** | `task_pattern_iri` (cluster key), `created_at`, `admin_notes`, `rejected_promotions` |

Memory materialises on the first Episode of a task-pattern; later Episodes
attach via the `MEMORY_CONTAINS_EPISODE` edge. `outcome_classification` ∈
{`succeeded`, `failed`, `low_confidence`, `asked_user`, `dont_know`}.

## The three v1 dream pipelines

| Capacity | Execution policy | Purpose |
|---|---|---|
| `dream.maintenance` | `replay_recorded` | regression check under pinned state |
| `dream.exploration` | `re_execute_capacities` | drift detection / alt-strategy probe |
| `dream.retry` | `re_execute_capacities` (+ replan-injection) | re-execute failed episodes |

## Retention (D'1)

References are version-pinned `(iri, version)` tuples, pinned at instantiation.
On version retire, affected Episodes inline the retired content lazily on next
read (bounded transitive inflation — one level per read). v1 ships monitoring
instrumentation (episode count, size histogram, Falkor-row count); retention
*policy* (aging/eviction) is v1.5 if growth is observed.

## Crash recovery

Checkpoint markers are recorded at LifecyclePhase transitions and per replan;
on L4 startup an unconsolidated marker becomes a `crash_marker` Episode
(`outcome_classification = "failed"`). Partial-MM content recovery is v1.5.
