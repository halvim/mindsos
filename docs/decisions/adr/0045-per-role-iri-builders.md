---
title: Per-role IRI builders for all upper-layer roles
status: Accepted
date: 2026-04-22
layer: L2
aliases: [kl-ADR-008]
---

# ADR-0045: Per-role IRI builders for all upper-layer roles

**Status:** Accepted

**Date:** 2026-04-22

## Context

The seed roles (ontology, lexicon, concepts) had hand-written IRI helpers. Upper-layer roles — pipelines, task-patterns, subgoal-templates, episodic-memories (Phase 39 rename of `memories` per ADR-0044 §amendment-3), problem-traces, capacity-snapshots — were landing with ad-hoc IRI construction at call sites, risking drift.

## Decision

`identifiers.py` grows seven new builders: `pipeline_iri`, `pipeline_step_iri`, `task_pattern_iri`, `subgoal_template_iri`, `episode_iri` + `memory_composite_iri` (both include `user_id` per ADR-0044 §amendment-3; Phase 39 rename of the original single `memory_iri` to two builders per Chat B Episode/Memory split + ADR-0146 §amendment-3 multi-NodeType dispatch), `problem_trace_iri`, `capacity_snapshot_iri`. Each has a matching entry in `_PREFIXES` so `parse_iri` / `is_version_qualified_iri` stay in sync.

## Consequences

**Good:**
- One source of truth for IRI syntax per role.
- Tests can import the builder and assert equality.

**Bad:**
- A new role means touching `identifiers.py` + `_PREFIXES` + a parity test.

## Alternatives considered

None recorded; this was the consensus choice during the 2026-04-22 design session.
