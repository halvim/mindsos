# ADR-0201 — Amendment 8: a run records where each of its starts came from

**Status:** Accepted (2026-10-24). Built as `mindsos_llm` plan item I-19
(`docs/plans/MINDSOS_LLM_PLAN.md`, rulings R46, R50–R52), DONE(659e46f). Gate 1
(start origins) merged as `48ae5de` (PR #269, tag `llm-start-origins-confirmed`);
gate 2 (a start that came through interpretation) as `0a010f8` (PR #270, tag
`llm-interpreted-start-confirmed`); gate 3 (the model declarations as they were
when the run ran) as `659e46f` (PR #271, tag `llm-declaration-snapshot-confirmed`).

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
| `interpreted` | the request's value as Phase-1 interpretation produced it; `model_capacities` lists every capacity interpretation dispatched that consults the model or declares answer inputs, in dispatch order (gate 2, plan R51) |

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

**5. `MANIFEST_CAPACITY_DECLARATIONS` (`"capacity_declarations"`, gate 3,
plan R52).** For every capacity the run composed, its model declarations as
resolved when the run started — `{capacity_iri: {"consults_llm": bool,
"model_answer_inputs": [ds, ...]}}` — beside `capacity_phrases` and for the
same reason (ADR-0207 amendment 1: the catalog is mutable; R45: an upsert
re-binds a declaration and a Local one shadows the Global). Every resolvable
capacity gets an entry with both fields, `False` and `[]` included; a
capacity MISSING from the map is *not recorded*, never *does not consult the
model*, and within an entry a field absent is *not recorded* — later items
(I-20's declared reads) add fields to the same entries. `execute_pipeline`
writes it on every manifest it mints; the no-route manifest writes `{}` (the
run composed nothing). A caller that passes none leaves the key ABSENT.

**5a. The reads (plan I-20 gate 2, R48, 2026-10-24).** Each entry gains
`reads_roles` (the L2 roles the capacity declared it reads, as declared;
ADR-0180 §amendment-5) and `reads_mm` (whether it declared the mental-model
channel; plan R53 names such a capacity and does not run it at re-run). Both
are always present in an entry minted from this gate on; in an entry minted
before it they are absent — *not recorded*, never *read nothing* — as §5
already provides. The map stays one key (owner, 2026-10-23, *"A for now"*).

## Consequences

- A renderer can tell a premise from a value computed by an earlier run, and
  name that run and instance.
- The manifest's key set grows by one on every run `execution` seeds;
  `tests/run_records/test_run_manifest.py` pins the set.
- **Gate 2:** `interpret` returns `model_capacities` (the four steps and the
  resolve pipeline's steps that ran), `Phase1Result` carries it, and the
  orchestrator hands `execution.run(seed_origins=...)` the seed's
  `interpreted` origin. Interpretation itself stays ungrounded; this is its
  only record.
- **Gate 3:** every manifest `execute_pipeline` mints carries
  `capacity_declarations`; R52's *"declared when it ran"* is read from it,
  never from today's registry. `model_answer_inputs` and `consults_llm`
  remain registration-time facts on the declaration and are not node
  properties; the manifest is their only record in a stored run.

## Alternatives considered

- **Edges between run graphs.** The graphs are persisted separately and
  references resolve by `graph_id` (S-F2); an intergraph edge would need a
  new edge vocabulary and a store change for what a manifest field says.
- **Properties on the seeded instance.** `Graph.add_node` accepts primitives
  only, and a collection's origin is a list.
- **Default every seeded start to `given`.** That is the defect.

Guard: `tests/llm_seam/test_a_start_names_where_it_came_from.py`.
