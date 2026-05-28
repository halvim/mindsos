---
title: MindsOS
last_confirmed_phase: 38
---

# MindsOS

MindsOS is a five-layer intelligence system built on FalkorDB metagraphs.

The stack:

- **Layer 1 — Core.** Graphs, metagraphs, schemas, persistence,
  reconstruction. No reasoning.
- **Layer 2 — Knowledge.** A metagraph whose contained graphs are
  knowledge roles (ontology, lexicon, concepts, alignments,
  memories, problem-trace, capacity-state, …). Global (shared) plus
  per-user Local.
- **Layer 3 — Intellectual Capacity.** Functions that acquire and
  manipulate knowledge — perception, comprehension, derivation,
  retrieval, scoring, trace, signalling, learning-methods. Fixed,
  not learned.
- **Layer 4 — Intelligence.** Applied knowledge. In design; out of
  scope for the L0–L3 release.
- **Layer 5 — Mental Model.** A per-task metagraph of L2 instances
  acting as working memory. In design; out of scope.

Orthogonally:

- **Server layer.** Auth, sessions, capability-based authorization,
  audit, persistence orchestration. Not on the layer-composition
  axis; provides the runtime envelope every consumer of the domain
  layers needs.

## Where to go next

- New to MindsOS? Read [Install](getting-started/install.md), then
  [Your first metagraph](getting-started/first-metagraph.md).
- Want the v4 release headlines? See
  [What's new (v4)](getting-started/whats-new-v4.md).
- Need a definition? The [Glossary](concepts/glossary.md) covers
  the terms-of-art.
- Want a worked end-to-end example? Walk the
  [Text-realm cookbook](usage/cookbook/text-realm.md) — it composes
  L0 → L1 → L2 → L3 via the CLI.
- Looking for an API reference? Each phase confirms its own pages
  under [API](api/core/graph.md).

## How this site is organised

| Section | What's there |
|---|---|
| Get started | Install + first-graph walkthroughs |
| Concepts | The mental model — graphs, metagraphs, identity, references, soft-delete, Global/Local, promotion, the layer stack |
| Usage | Per-layer walkthroughs of the CLI verbs and Python surface |
| Cookbook | End-to-end vertical slices stitching multiple layers together |
| Knowledge sources | DOLCE, OEWN, FrameNet ingest references |
| API | Per-class reference |
| Developer guide | Contributing, conventions, internals, release flow |
| Changelog | Per-phase ship log |

## Status

L0–L3 are shipped. L4 + L5 + FOL are out of scope for the present
plan; a separate follow-up plan will cover them. Phase 38 is the
final numbered phase of the L0–L3 rollout (Phase 37 retired
2026-05-19).
