---
title: Confidence storage - pipeline-level on promoted-pipelines records
status: Accepted
date: 2026-04-21
layer: L3
aliases: [L3-Q12]
---

# ADR-0094: Confidence storage - pipeline-level, not per-capacity

**Status:** Accepted

**Date:** 2026-04-21

## Context

Confidence in a pipeline's ability to solve a task needs to be tracked somewhere. The question is whether confidence lives on individual capacity nodes, on entire pipelines, or split across both.

## Decision

**Pipeline confidence** (learned, per `(pipeline, task-type)`) lives on `promoted-pipelines` records in L2. **Per-run output confidence** lives on the Mental Model in L5. **No `capacity-confidence` role-graph exists.** No reliability store on individual L3 nodes. A capacity that is unreliable at solving problems doesn't belong in L3 in the first place — the meaningful unit is (pipeline, task-type).

## Consequences

**Good:**
- Capacity nodes stay fixed and immutable (invariant I1).
- Confidence reflects the full context in which a pipeline was tested, not decontextualized per-capacity reliability.
- L4 learns at the right granularity — pipeline + task.

**Cost:**
- Can't directly compare two capacities' reliability in isolation; must look at the pipelines they're in.

## Alternatives considered

1. **Per-capacity confidence** — rejected (violates I1; capacities are fixed).
2. **Both per-capacity and per-pipeline** — rejected (adds storage complexity; which one does L4 trust?).

## Revisions

### amendment-1 (L2 chat — 2026-06-01) — `confidence` field removed from `promoted-pipelines`; migrates to ALS

**Trigger:** Chat A R3 (2026-05-28) settled the pipeline-confidence
migration under PB-R3-21 / PB-R3-22 / pipeline-binary-deterministic
framing. Pipelines are binary deterministic solvers tested before
approval; a `confidence` field on `promoted-pipelines` records is
therefore vestigial — selection across multiple valid pipelines is
ranked by ALS-learnable efficiency parameters, not a stored confidence
scalar. The L2 chat (2026-06-01) closes the migration by amending this
ADR; see `_workbench/L2_CHAT_DECISIONS.md` D-L2-24.

**Amended behavior:**

* **Pipeline-record `confidence` field DROPPED.** The
  `promoted-pipelines` schema v2 (ADR-0152) does not include
  `confidence` in `PIPELINE_PROPS`.
* **Per-pipeline confidence relocates to ALS subsystem parameters:**
  - **ALS subsystem #3 (Pipeline selection parameters)** — learnable
    efficiency ordering across valid pipelines for the same task-type.
    Track B, batched-summary audit. Storage:
    `learned-parameters` keyed by `(pipeline_iri, task_type)`.
  - **ALS subsystem #4 (Task-to-task-type mapping confidence)** —
    load-bearing replacement. Track B, individual-review audit.
    Storage: `learned-parameters` keyed by task-pattern IRI.
* **Per-run output confidence remains on `TaskRun` composite** in L5
  intelligence-MM (Chat B D-B33 + Chat A R3); not on
  `promoted-pipelines`.
* **No per-capacity confidence anywhere** (invariant unchanged from
  original §Decision; capacities are fixed-not-learned).
* **Pipeline failure handling.** Pipelines that fail get
  **quarantined** (system-triggered status transition per
  `_workbench/L2_CHAT_DECISIONS.md` D-L2-9 / Chat A R3 PB-R3-31).
  Admin reviews quarantined pipelines and either reinstates or
  retires. Status filter at read is L3 pipeline-finder's
  responsibility per L2_CHAT_DECISIONS D-L2-8 (L2 stays dumb-store);
  default `status="active"` excludes quarantined.

**Migration of shipped state:** Any Local-Pipeline records carrying
the old `confidence` property get the field stripped by a one-shot
maintenance migrator at v2 schema deploy (Chat C plan-authoring
sequences the migration phase).

**Out-of-scope for amendment-1:**

* The ALS subsystem #3/#4 mechanism choice + concrete
  `parameter_set_iri`s — WSD installation chat owns.
* Quarantine threshold tuning — admin-tunable per-pipeline
  (`quarantine_threshold: float`, default 0.85 per Chat A R3
  PB-R3-31).
* 5-state lifecycle enum semantics — locked at
  ADR-0152 / `_workbench/L2_CHAT_DECISIONS.md` D-L2-6.

See `MindsOS/docs/_workbench/CHAT_A_DECISIONS.md` R3 pipeline-
confidence migration + PB-R3-21 + PB-R3-22 + PB-R3-31 and
`_workbench/L2_CHAT_DECISIONS.md` D-L2-24 for the rationale chain.
