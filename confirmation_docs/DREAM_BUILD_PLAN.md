# Dream Build Plan (dependency-ordered)

Status: DESIGN-READY. Build in its own chat/branch, AFTER the rename lands.
Signature target: `dream(task, objective, signal, strategy)`.
Concept reference: CONCEPT_REQUEST_TASK_EPISODE_DREAM.md.

## Critical path
```
finish in-flight pushes -> RENAME (task->Request) -> Dream prerequisites -> Dream driver -> Write-back + gate
```
Prerequisites are independent of each other and can be parallelized among
themselves, but all sit AFTER the rename so they are authored in the new
vocabulary (building pre-rename means re-churning this code in the rename).

## What already exists (reuse, don't rebuild)
- Dream harness scaffolding: `DreamCycleTimer`, `fork_dream_mm()` (isolated MM
  fork for sandboxed replay), pluggable `dream_driver` hook (ADR-0163..0169).
  The driver itself is unimplemented.
- Persistence: per-run capacity_mm graphs persist to the Episode
  (`capacity_root_ref`); plan/Milestone tree persists in the chain graph.

## Prerequisite CRs (each its own work-item)
0. **PRE-0 Streaming Episode persistence (mandatory, always-on).** Today
   consolidation is **terminal-only** — the Episode is assembled + written on the
   terminal path; crash recovery is a tombstone (`outcome=failed`,
   `mm_root_ref=None`), and partial-content recovery is deferred (ADR-0179 §3).
   This CR **promotes ADR-0179 §3 to mandatory**: Episodes are written
   incrementally *as the Request is solved*, never batched at the end.
   - **Model change:** open Episode at Request start -> append per pipeline-run
     (and per interpret/plan phase) -> close by stamping the terminal outcome.
   - **Streaming unit:** the per-pipeline-run capacity graph (execution.run
     already produces one per run; flush it when the run completes, not at end).
     Granularity = per-run / per-phase, NOT per-capacity-step.
   - **Durability spine = inline flush at run/phase boundaries** (crash-consistent,
     cheap). A background writer thread is an OPTIONAL optimization only if flush
     latency hurts solving AND the enqueue is itself durable — do NOT lead with an
     async queue (in-flight items lost on crash defeat the purpose).
   - **Hard dependency:** durable (Falkor-backed) checkpoint/marker store —
     crash_recovery's store is in-memory today.
   - **Reader contract:** the dream must tolerate OPEN / incomplete Episodes
     (use up to the last durable run; latest replan attempt wins).
   - Independently valuable (runtime crash durability), but build AFTER the rename
     (touches consolidation/execution/persister/crash_recovery). Forces PRE-1.
1. **PRE-1 Request-input persistence.** Store the actual raw input value (today
   `task_input_ref` is a bare label with no backing store). This is the dream's
   reload anchor — without it, necessity/alternative-map replay is impossible.
2. **PRE-2 Capacity side-effect declaration.** A per-capacity marker (side-effect
   class: pure / sandbox-safe / external-only). The dream composes only from
   sandbox-safe capacities; unsafe ones (and Tasks solvable only through them)
   are excluded. Nothing to filter on today.
3. **PRE-3 Episode searchable index.** An index over the Episode addressable by
   task / pipeline / capacity / datastate, so the dream queries content without
   walking the tree. (A per-episode reader does not exist yet — persister defers
   it "until dream reconstruction".)
4. **PRE-4 Baseline metric capture.** Record per-objective measurements at
   consolidation (step count, capacity cost, timing, confidence, result). Replay
   can backfill later episodes, but new episodes should capture the standard set.
5. **PRE-5 Alternative enumeration.** The mapper must be able to yield ranked
   candidate maps (not just the winner); path-finding must expose the multiple
   valid graph paths (not just the chosen one). The dream needs these to have
   alternatives to try.

## Dream core (after prerequisites)
6. **D-1 Dream driver** implementing `dream(task, objective, signal, strategy)`:
   - reload the Task/Request from the Episode onto a `fork_dream_mm()` fork;
   - run `strategy` to enumerate alternatives (via PRE-5);
   - execute alternatives in the sandbox (PRE-2 filter);
   - score with `objective` against `signal` (correctness-bearing).
7. **D-2 Objectives registry** (pluggable): fewer steps / cheaper / higher
   confidence / faster / ... Tag each intra-episode vs cross-episode.
8. **D-3 Strategies registry** (pluggable search over the alternative space,
   budget-bounded).
9. **D-4 Signal contract.** Mandatory; must encode CORRECTNESS, with a defined
   truth source per objective (not "matches the original result", which only
   confirms reproduction).

## Write-back (the payoff — gated)
10. **WB-1 Confidence updates** — hint/map/plan/path confidences from validated
    dream results.
11. **WB-2 Pipeline promotion to L2** — reuse the planned learned-pipeline
    persistence path (see `CR_LEARNED_PIPELINE_PERSISTENCE_REVIEW.md`).
12. **WB-3 Validation gate (REQUIRED for shared writes).** A Task-local pipeline
    change is safe. But L2 promotions and shared-confidence updates affect other
    Requests — they must pass a gate (no regression across related Episodes)
    before touching the live system. This is the guard against the dream
    degrading the system while "improving" one task.

## Cross-episode (later)
13. **XE-1 Cross-episode index + calibration** — "find all Tasks using capacity
    X"; corpus-level map-confidence calibration; judging reusability/generality.
    Different machinery than single-episode replay.

## Open decisions still owed (from concept doc §5)
- WB-3 gate criteria (what counts as "no regression").
- PRE-2 side-effect taxonomy.
- D-4 signal truth source per objective.
- XE-1 index structure.
- `task_pattern` rename decision (affects vocabulary of all the above).
