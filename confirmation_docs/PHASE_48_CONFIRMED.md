# Phase 48 — Confirmation

> Hand-assembled from the green cumulative gate (per the env invariant the
> `confirm-phase` tool is absent on the gate host and would re-run the 32-min
> suite; this phase reuses the gate already run on the squashed tree). CI's
> smoke check verifies "exists and non-empty".

---

## phase_number

48

## phase_title

L5 v1: MM consolidation + Episode/Memory authoring + dream hookup + D'1 retention + crash recovery + concepts docs

## git_sha

af331e8

## image_build_hash

unknown (image not built locally — run `docker compose build`)

## falkordb_version

falkordb/falkordb:v4.18.3@sha256:30c530c193ac48cb6ea8c6cae745f793d2c098a0a138f7b3e46c1d90848845ba

## automated_test_summary

- count: 3873
- passed: 3863
- skipped: 10
- failed: 0
- pytest_summary: 3863 passed, 10 skipped, 109 warnings in 1952.05s (0:32:32)

## tester_notes

Phase 48 (the final convergence phase) makes the Phase-47 chain artifacts
*persist* as Episodes and wires dream as live re-execution. Shipped across an
R0 design pass (3 rounds + grounding probe; `PHASE_48_DESIGN_LOG.md`) + five
commit groups + two gate-fix commits on `phase-48`, squash-merged to `main` at
`af331e8`.

Shipped (by surface):

- **S6 — D'1 KL hooks (commit-group 1).** `kl.read_at_version` +
  `kl.retire_version` + the `_retired_inline_pending` marker write +
  `RESERVED_PROPERTY_KEYS` registration (`mindsos_core/schema/validation.py`).
  ADR-0161's forward-contract shipped **none** of this at Phase 44 (grounding
  finding); Phase 48 lands the full stack. ADR-0161 §amendment-1 corrects the
  stale "Phase 44 ships both" text. Opt-C signature (ADR-0177 §note): the hooks
  keep the shipped `CapacityContext.KLHandle.read_at_version(iri, version)`
  Protocol; multi-version-per-node is latent (exercised on synthetic data).
- **S4/S12 — S12 write-half close (commit-group 2a; ADR-0180).** A pre-authorized,
  session-bound `writeable` capability is injected onto `CapacityContext` (11th
  field) by a shared `make_writeable(kl, session)` factory; the scope-aware
  capability gate fires **at write-time inside the capability** (Local → none;
  Global → `CAN_WRITE_GLOBAL`; `session is None` = ADR-0080 bootstrap). The gate
  travels *with the capability*, built by the session-holder — L4 `dispatch.py`
  for task lifecycles, `CapacityLayer.invoke` (write-body branch) for the CLI /
  direct path. `consolidate`/`trace` bodies migrate off dict context;
  ADR-0146/0170 both preserved (L3 holds no principal). **A1/A1′ scope boundary
  (user-ratified):** the read-path dict + the transitional union annotation are
  retained one more phase (no read-corpus churn mid-convergence); the cosmetic
  union-drop is deferred. PB-23's authorization half **closes**.
- **S2/S3 — Episode/Memory authoring (commit-group 2b).** `consolidate:mm`
  finalises to the 6-field D-B47 Episode `value` + materialises the Memory
  composite on first episode per task-pattern (content-hash `memory_id`) +
  wires the `MEMORY_CONTAINS_EPISODE` edge.
- **S1 — MM consolidation write path (commit-group 3a; ADR-0176).** New L4
  `consolidation.py` freezes the MM (writer lock) + assembles the Episode record
  from the TaskRun chain + dispatches `consolidate:mm`; wired into all three
  orchestrator terminal paths (success/dont-know/abort = retain-by-default).
  Guarded — gracefully skipped in simplified mode and when no consolidate
  capacity / KL is wired (the v0 smoke). `mm_root_ref` is a v1 reference to the
  intelligence sub-MM id (the MM metagraph is persisted by the L0 persister; the
  heavy full-MM snapshot is deferred).
- **S8 — crash recovery (commit-group 3b; ADR-0179).** v1 tombstone mechanism:
  checkpoint markers recorded at the D-B50 triggers (LifecyclePhase transitions
  + per-replan) via `crash_recovery.py`; `IntelligenceLayer.start` scans
  unconsolidated markers and writes a `crash_marker` Episode
  (`outcome_classification="failed"`, `mm_root_ref=None`), idempotent on the
  task id; the orchestrator clears the marker on consolidation. Partial-MM
  content recovery → v1.5.
- **S5 — dream-cycle driver (commit-group 4; ADR-0178).** `dream_cycle.py` wires
  the Phase-46 `DreamCycleTimer` callback to the 3 Phase-45 `dream.*` capacities:
  pulls episode descriptors, collects `DreamDirective`s (with
  `source_episode_iri` provenance; `dream.retry` carries the
  ReplanInjectionDirective on failed episodes), and re-executes via a hook. v1
  re-runs from the episode `task_input` (PB-9); faithful episode→MM
  reconstruction + `replay_recorded`-vs-`re_execute_capacities` behavioral
  differentiation + real ALS firing are WSD-gated.
- **S7 — D'1 inline-on-retire read consumer (commit-group 4).** `retention.py`
  `resolve_ref`/`resolve_refs` consult the retire marker and report inlined
  content. **Unit-test-only at v1 (PB-9)** — no live consumer (dream re-runs from
  task_input, not full reconstruction); real consumers = WSD reconstruction /
  retrieval.
- **S9 — retention monitoring (commit-group 5).** `monitoring.py`
  `export_retention_metrics` — episode count + size histogram + Memory count +
  Falkor-row count. **Instrumentation only** (PB-QQ); retention policy → v1.5.
- **S12 — docs (commit-group 5).** New `concepts/layers.md`,
  `concepts/society-of-mind.md`, `getting-started/facts-and-figures.md` + nav;
  `concepts/dream.md` Phase-48 hookup section.
- **S13 — version bump 47→48 (commit-group 5).** 10 surfaces: 8 package
  `__version__` + pyproject + manifest `version` **and** `phase` + 2
  docker-compose tags + the export-slate assertions (phase_30/31/34).
- **S11 — ADRs.** 0176 (consolidation write path) + 0177 (D'1 retention) + 0178
  (dream driver) + 0179 (crash recovery) + 0180 (write-capability + scope-aware
  gate); amendments to 0175 (§am-2 write-half + A1 deferral), 0161 (§am-1), 0170
  (§am-1 gate-timing), 0146 (§Amendment handle source).

Grounding-driven decisions (probe-first, consumer-discipline):

- **D'1 KL hooks absent at Phase 44** — Phase 48 lands the full stack, not just
  two methods (ADR-0161 §am-1 correction).
- **CLI is a write path** — `capacity_layer.invoke` (via `mindsos capacity
  invoke`) dispatches `consolidate`/`trace`; A1′ added the write-body branch so
  the gate factory is shared and the CLI keeps working (ADR-0180 generalised
  "gate in L4" → "gate in the capability, built by the session-holder").
- **PB-10 Local-write fix** — the Phase-47 blanket pre-gate demanded
  `CAN_WRITE_GLOBAL` for any write-body, which would have denied a normal user's
  Local `consolidate:mm`; replaced by the scope-aware call-time gate. Verified
  live: an ordinary user (no global cap) consolidates a Local Episode.
- **Gate-fix commits:** (1) the `consolidate.py` local `memory_iri` tripped the
  Phase-39 retired-builder-name sentinel (renamed `mem_iri`); (2) the docs-nav
  test read `mkdocs.yml`, which is not copied into the test image (skips when
  absent — nav validated by `mkdocs build` on the docs host).

Host smoke (docker test image): `mindsos_cli.__version__ == 0.0.0+phase48`;
trivial task → 1 Episode + 1 Memory + 1 edge (ordinary user, no global cap);
crash recovery → tombstone; dream → 3 directives (retry with replan injection).

Gate: full cumulative **3863 passed / 10 skipped / 0 failed** (Linux docker,
32:32) at the squashed `phase-48` tree.

Open for Phase 49 (Integration C): end-to-end L0→L5 trivial-task scenario +
`usage/cookbook/end-to-end.md` + Falkor index decisions. Deferred follow-ups:
union-annotation drop + `capacity_layer.invoke` read-path → CapacityContext;
faithful episode→MM reconstruction + `replay_recorded` differentiation + real
ALS firing (WSD); partial-MM crash-content recovery (v1.5); retention policy
(v1.5); durable Falkor-backed checkpoint store.

## timestamp_utc

2026-06-09T00:00:00Z

## mkdocs_pages_updated

- docs/concepts/layers.md (new)
- docs/concepts/society-of-mind.md (new)
- docs/getting-started/facts-and-figures.md (new)
- docs/concepts/dream.md (Phase-48 hookup section)
- mkdocs.yml nav (3 new entries)
