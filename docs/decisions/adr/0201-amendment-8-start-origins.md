# ADR-0201 — Amendment 8: a run records where each of its starts came from

**Status:** Proposed (2026-10-09). Built as `mindsos_llm` plan item I-19
(`docs/plans/MINDSOS_LLM_PLAN.md`, rulings R46, R50–R52); flips to Accepted when
I-19 is DONE. Gate 1 (start origins) is built; gates 2 (a start that came
through interpretation) and 3 (the model declarations as they were when the
run ran) are not.

## Context

Amendment 4 made a parentless `DataStateInstance` decidable: inside the
manifest's `declared_starts` it is *"a premise the run was given"*. That holds
for one run. A request is many run graphs — one per milestone, per map member
and per fold — and values cross between them on an in-memory blackboard, so a
value an earlier run PRODUCED arrives in the next run as a parentless start,
structurally identical to one the caller handed in. A renderer then prints a
computed value as a premise: amendment 4's own failure, one level up. Only a
fold recorded which runs fed it (`member_graph_ids`, amendment 5), and that by
graph, not by instance.

It matters beyond rendering: re-running a conclusion without the borrowed
model (plan §1) has to know whether an input descends from a model reading,
and nothing in a stored Episode could say so (plan §6, 2026-10-09).

## Decision

**1. `MANIFEST_START_ORIGINS` (`"start_origins"`).** A run's manifest value
maps each SEEDED start's DataState IRI to its origin, whose `kind` is one of a
closed set (`START_ORIGIN_KINDS`):

| kind | meaning |
| --- | --- |
| `given` | handed to `execution.run` by its caller |
| `produced` | made by the instances under `by`, each `{"graph_id", "instance_id"}`; a collection assembled from map members lists every completed member's, in member order |
| `unrecorded` | seeded with a value whose origin nobody recorded — never read as `given` |

**2. Where it rides.** Origins travel on the blackboard beside the values
(`start_origin_key`, `member_origins_key`), for the lifetime argument of
amendment 5: a targeted re-run keeps the retained blackboard, so it keeps
these too and splices a member's origin exactly as it splices its output and
graph id. A retained blackboard from before this amendment says nothing about
the untargeted siblings, so the collection's origin is `unrecorded`.

**3. Who writes it.** `execution` passes origins at all three seeding sites
(leaf, map member — including a nested sub-plan — and fold).
`execute_pipeline(start_origins=...)` writes them; a seeded start it does not
name is `unrecorded`. A caller that passes none (`phase_1`'s ungrounded
resolve, the SubMind arbiter, a direct caller) leaves the key ABSENT: absence
means *not recorded*, never *given* — amendment 5's key-presence rule.
`PipelineExecutionResult.produced_instances` exposes which instance a step
produced for each DataState, so `execution` can name it.

**4. The kinds are checked where the manifest is minted.** An origin whose
kind is outside the closed set raises, as an empty `member_graph_ids` entry
does (amendment 5).

## Consequences

- A renderer can tell a premise from a value computed by an earlier run, and
  name that run and instance.
- The manifest's key set grows by one on every run `execution` seeds;
  `tests/run_records/test_run_manifest.py` pins the set.
- **Not yet:** a start that came through Phase-1 interpretation is recorded
  `given` (gate 2 labels it), and the run does not yet snapshot the model
  declarations of the capacities it composed (gate 3).

## Alternatives considered

- **Edges between run graphs.** The graphs are persisted separately and
  references resolve by `graph_id` (S-F2); an intergraph edge would need a
  new edge vocabulary and a store change for what a manifest field says.
- **Properties on the seeded instance.** `Graph.add_node` accepts primitives
  only, and a collection's origin is a list.
- **Default every seeded start to `given`.** That is the defect.

Guard: `tests/llm_seam/test_a_start_names_where_it_came_from.py`.
