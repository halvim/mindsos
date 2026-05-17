# Phase 11 — Design Log

> Captured at chat opening (2026-05-16). Records all design pushbacks
> (PB-1..17), the four step-list pushbacks (PB-18 / PB-25 / PB-26 /
> PB-31..33), and the locks each one produced. Future amendments to
> ADR-0134 should consult this file for rationale.

## 0. Scope at chat-open

PHASE_MAP §11 (pre-correction) read: "Cypher builders + integrity
scanner + schema migration; cypher-build debug; integrity verify with
report; schema-migrate dry-run vs apply (ADR-0134)." Deps: 07.

Step-0 inventory revealed three of the four nominal items were already
shipped:

* ADR-0021 rel-type regex — enforced at `builders.py:176/228/291`.
* ADR-0022 UNWIND batching — 7 builders shipped Phase 07.
* ADR-0023 MERGE-then-SET — every builder follows the pattern.
* ADR-0123 indexes + persist-time check + `verify_invariants` +
  `mindsos persistence verify` — all shipped Phase 07; ADR Accepted
  2026-05-13.
* 42 cypher builders shipped (Phase 07 + Phase 10's 22 additions).

Net-new = ADR-0134 only (~300 LoC) + 4-amendment doc work.

## 1. Design pushbacks (PB-1..17)

Six rounds of pushbacks. Each lists the question, the options
considered, and the lock. User agreed all picks (option A on every
shaper PB).

### PB-1 — "dry-run vs apply" contradicts ADR-0134

ADR-0134 §"What it does NOT do": *"Apply migrations. v1 is
detection-only."* PHASE_MAP wording was wrong.

**Lock: A — detection-only.** Drop "apply" from PHASE_MAP. Risk
callout obsolete.

### PB-2 — Right-size scope

Phase 11 net-new is ADR-0134 only. Phase-10-scale (160 tests) padding
rejected.

**Lock: A — ship narrow.** ~45 tests (revised to ~60 in PB-31).

### PB-3 — "cypher-build debug" undefined

No user story; no clear surface.

**Lock: A — kill it.** No `mindsos cypher build` verb.

### PB-4 — Loader default flip cascade

`silent → warn` could break log-cleanliness asserts.

**Lock: A — Step-0 grep + predict-and-patch in one commit.**
Outcome: Step-0 §5+6 surfaced ZERO log-cleanliness assertions.
Cascade prediction = 0.

### PB-5 — ADR-0134 acceptance contract

Ship scanner without KL consumer.

**Lock: A — keep Proposed.** Flip Accepted Phase 12+ when KL consumes.

### PB-6 — `migrate_from` input source

Three CLI input-source options.

**Lock: B (revised to A+B) — `--old <name>` (state-dir lookup) OR
`--old-file <path>` mutex.**

### PB-7 — Element-type coverage gap

ADR-0134 implied Node + Edge only; L1 has 6 families.

**Lock: C — Schema-level only (NodeType + EdgeType + HyperEdgeType).**
MetagraphSchema scanner deferred to Phase 12+.

### PB-8 — Output explosion

10k unknown rows = 10k violations.

**Lock: A — `detail="summary"|"each"`.** Summary default;
`each` for ops drill-down.

### PB-9 — `Graph.dropped_edge_count` mutation

Would trigger state-file v=6 bump.

**Lock: B — `LoadReport` sibling.** Drop count is a load-time stat,
not graph state. No state-file bump.

### PB-10 — Loader warning granularity

Per-edge vs per-distinct-type.

**Lock: A — per-distinct-type with counts.** ADR-0134 §amendment-1.

### PB-11 — Schema-less graph policy

What if `graph.schema is None`?

**Lock: A — policy is a no-op when no schema attached.**

### PB-12 — `load_graph` signature break vs additive sibling

4 internal CLI callsites + 1 Phase 10 contract test.

**Lock: B — additive sibling `load_graph_with_report`.** Zero
existing-caller churn; no Phase 10 contract test patch.

### PB-13 — MetagraphLoader aggregation symmetry

**Lock: A — sibling `MetagraphLoader.load_with_report` +
`load_metagraph_with_report`.** Aggregates per-Graph LoadReports.

### PB-14 — Policy plumbing location

ADR-0134 said `FalkorConfig`; wrong layer.

**Lock: A — per-call kwarg + env var.** ADR-0134 §amendment-2.

### PB-15 — CLI exit code

**Lock: A — exit 1 on violations; `--exit-zero` opt-out.**

### PB-16 — Doc surface lock

Avoid Phase 10 RPB-8 sentinel disaster.

**Lock: B — sentinel 2 Python modules
(`mindsos_core/schema/migration.py` +
`mindsos_core/reconstruction/load_report.py`); zero docs sentinels.**
Update `docs/dev/internals/core.md` §"Phase 11 …" + new
`docs/dev/migration-playbook.md` stub. Skip `docs/api/core/cypher.md`
edit — PHASE_MAP wording was wrong.

### PB-17 — Per-Graph vs per-Metagraph scope

ADR-0134 ambiguous on scanner unit.

**Lock: C — both, with mutex CLI flag.** `migrate_from(old, target:
Graph | Metagraph, ...)`. Per-Metagraph path walks every contained
graph with a schema. `old_schema_name` opt-in emits a logger WARNING
on name mismatch (NOT a `SchemaViolation`).

## 2. Step-list pushbacks (PB-18 / PB-25 / PB-26 / PB-31..33)

### PB-18 — Phase-bump ordering

Bumping `manifest.toml`/`pyproject.toml` early triggers red period
until cascade patches land.

**Lock: A — bundle phase-bump + cascade patches in ONE commit
(step 20).** Tests stay green throughout steps 8-19.

### PB-25 — confirm-phase flow split

`notes-phase-11.md` (input) vs `PHASE_11_CONFIRMED.md` (output)
conflated.

**Lock: A — split 25/26 into 4 sub-steps.** 25a init notes-stub; 25b
fill notes-stub with impl summary; 26a run confirm-phase; 26b
hand-fill `tester_notes` in auto-generated CONFIRMED doc.

### PB-26 — Design log step

**Lock: A — write `PHASE_11_DESIGN_LOG.md` (this file).** Step 18.

### PB-31 — Test count recalibration

`~45` lowballed; itemised ≈ 60.

**Lock: informational only — no scope change.** Cumulative target
~1720.

### PB-32 — Dockerfile COPY discipline probe

**Lock: A — Step 0 probe.** Outcome: tree-wide `COPY mindsos_core/`
+ `COPY mindsos_cli/` + `COPY mindsos_instances/` in both `prod`
and `test` stages. New Phase 11 modules land for free. No patches.

### PB-33 — confirm-phase pytest summary regex regression

**Lock: A — Step 0 probe + regression test.** Outcome: regex intact
at `mindsos_cli/commands/confirm_phase.py:284-286`; matches both
framed and bare forms per B-10-T6 fix.

## 3. Step-0 audit outcomes

| Audit | Result | Cascade |
|---|---|---|
| §3 state-file versions | Migration constants at 5/5/3/2; dynamic test patterns hold | 0 |
| §4 phase-string literals | 8 bump sites in non-test code/configs | 0 test patches |
| §4b Dockerfile COPY | Tree-wide; new files auto-COPYd | 0 |
| §4c confirm-phase regex | Intact post-B-10-T6 | 1 regression test added in step 19 |
| §5 caplog/capsys loader | Zero log-cleanliness asserts on loader | 0 |
| §6 stricter-schema loads | Moot under `warn` default | 0 |

**Total predicted cascade: 0 prior-phase test patches.** Cleanest
pre-impl audit of any phase to date.

## 4. Carry-forward (deferred to later phases)

* **Apply-style migration** (`apply(violations, *, dry_run=True)`) —
  Phase 14+ when first cross-layer consumer needs it.
* **MetagraphSchema scanner** (MetaEdge / IntergraphEdge / etc. types)
  — Phase 12+ when L2 first bumps a MetagraphSchema.
* **Versioned schemas** with named migrations — defer until first
  real schema bump (Phase 12+).
* **`Schema.diff(old)` structural-diff helper** — defer until a
  doc-generator consumer exists.
* **`mindsos persistence verify --repair` flag** (ADR-0123 v2) —
  Phase 14+.
* **Cypher-build debug CLI** — killed per PB-3; no carry-forward.
* **Migration playbook content** — stub ships Phase 11; full content
  with first KL consumer (Phase 12+).
* **ADR-0134 §amendment-3** — reserved for first KL consumer's
  structural feedback.

## 5. Cross-chat dependencies

### Closed (Phase 10 → Phase 11)

* Phase 10 RemovalImpact + soft-delete + MetagraphSnapshot — all
  shipped; Phase 11 builds on top without touching.
* Phase 10 `phase-10-confirmed` tag is the Phase 11 branch point.

### Forward (Phase 11 → Phase 12+)

* L2 (KL): consumer for `migrate_from` output; drives ADR-0134
  Proposed → Accepted flip.
* L2 (KL): if first KL hardening bumps MetagraphSchema, requires
  MetagraphSchema scanner (deferred per PB-7 C).

## 6. ADR matrix (Phase 11 touches)

| ADR | Pre-Phase-11 | Phase 11 action |
|---|---|---|
| 0021 rel-type regex | Accepted | No change |
| 0022 UNWIND batching | Accepted | No change |
| 0023 MERGE-then-SET | Accepted | No change |
| 0123 indexes + verify | Accepted | No change |
| 0134 scanner | Proposed | + §amendment-1 (WARN granularity) + §amendment-2 (policy on loader, not FalkorConfig); STAYS Proposed |

## 7. File ledger (Phase 11 modifications)

NEW:

* `mindsos_core/reconstruction/load_report.py` — LoadReport +
  MetagraphLoadReport (~140 LoC).
* `mindsos_core/schema/migration.py` — SchemaViolation +
  SchemaMigrationError + `migrate_from` (~310 LoC).
* `docs/dev/migration-playbook.md` — stub.
* `confirmation_docs/PHASE_11_DESIGN_LOG.md` — this file.
* `tests/phase_11/` — ~60 tests across 13 tiers.

MODIFIED:

* `mindsos_core/exceptions.py` — `UnknownEdgeTypeError` class (+43
  lines).
* `mindsos_core/reconstruction/graph_loader.py` — env-var resolver,
  policy filter in `_load_edges`/`_load_hyperedges`,
  `load_graph_with_report` sibling (+180 lines).
* `mindsos_core/reconstruction/metagraph_loader.py` —
  `load_with_report` method, `load_metagraph_with_report` module
  helper, `_attach_graph` policy plumbing (+90 lines).
* `mindsos_core/reconstruction/__init__.py` — re-exports.
* `mindsos_core/schema/__init__.py` — re-exports.
* `mindsos_cli/commands/persistence.py` — `--unknown-edges` flag on
  `load`, drop-count surfaces (Rich + JSON) (+60 lines).
* `mindsos_cli/commands/schema.py` — `migrate-check` verb (+210
  lines).
* `docs/dev/internals/core.md` — Phase 11 §"Loader policy + schema
  migration scanner" section.
* `docs/decisions/adr/0134-schema-migration-scanner.md` — §Revisions
  amendments-1 + 2.
* `confirmation_docs/PHASE_MAP.md` §Phase 11 row — full rewrite per
  PB-1 / PB-3 / PB-7 / PB-12 / PB-16 corrections.
* `tests/_shared/sentinel_paths.py` — +2 Python module entries (no
  doc sentinels per PB-16).
* Phase-bump (step 20 ONE commit per PB-18): `mindsos_core/__init__.py`,
  `mindsos_cli/__init__.py`, `mindsos_instances/__init__.py`,
  `mindsos_cli/manifest.toml`, `pyproject.toml`, `docker-compose.yml`.

## 8. Confirmation command

```
mindsos confirm-phase --phase 11 --notes-file notes-phase-11.md
```

Pre-build: `docker compose --profile test build mindsos-test` BEFORE
confirm-phase (timeout 1800s per `feedback_confirm_phase_timeout.md`).
Host-native invocation per PB-34 (avoid docker COPY-notes cascade
that cost Phase 10 B-10-T5).

Release CI tags `phase-11-confirmed` AFTER squash-merge to main per
8-step procedure in `feedback_release_tag_after_squash_merge_only.md`
(PB-35).
