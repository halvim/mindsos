# Phase 14 — Tester notes (filled at confirm-phase time)

> Repo root location per `feedback_confirm_phase_file_paths.md`. The
> `mindsos confirm-phase --init-notes 14` wrapper reads this file and
> writes `confirmation_docs/PHASE_14_CONFIRMED.md`. Sections below are
> the wrapper's expected fields; the prefilled rows are Phase 14's
> design-time view of pass criteria, the tester edits if reality
> diverges.

## phase_title

L2 KnowledgeLayer + role-graph bootstrap + MetagraphView (read-only)

## scope_summary

Phase 14 ships the L2 entry point: `KnowledgeLayer` class with Global
+ Local metagraph lifecycle, idempotent `ensure_global_role_graph` /
`ensure_local_role_graph` keyed on ADR-0150's closed role-set,
read-only `MetagraphView` (whitelist wrapper), install/extract hooks
per ADR-0042 (amended with Global lifecycle in Phase 14 PB-7), and
two ADR amendments (ADR-0042 amendment-1, ADR-0150 amendment-1).

NOT in this phase (deferred per Phase 14 round-1 PB-1):

* Per-edge alignment-anchor IRI builder → Phase 15 (first importer).
* MetagraphSchema scanner → Phase 15 (first phase writing content).
* Validators surface → Phase 36 (per ADR-0139, when consumers land).
* `follow_ref` cross-metagraph helper → Phase 25 or first L3 capacity.
* CLI verbs over KL → Phase 17 (versioning ships natural view verbs).

## packages_modified

4-package version parity: `mindsos_core`, `mindsos_cli`,
`mindsos_instances`, `mindsos_knowledge` all at `0.0.0+phase14`.
`manifest.toml [mindsos] phase = "14"`; image tags
`mindsos:phase14-{prod,test}`.

## doctor_self_test_expected

Phase 14 adds no new top-level package (KL stays in
`mindsos_knowledge`). Doctor self-test checks (1)-(6) all unchanged
in shape; only literal values flip from `+phase13` → `+phase14` and
`phase13-{prod,test}` → `phase14-{prod,test}`.

## automated_test_summary

* `tests/phase_14/` — ~12 modules; ~95-115 isolated tests expected.
* Cumulative `tests/` — Phase 13's 2027 + Phase 14's ~100 (Phase 12+13
  unchanged surfaces) + 10 root-level `test_image_completeness.py`
  fanout from new sentinel paths.
* `B-14-T*` hotfix ledger — filled if static-grep audits missed a
  baseline literal. Per `feedback_phase_baseline_literal_audit.md`,
  Step 0 grep ALL tests for `+phase13` / `phase 13` / `Phase 13` /
  `phase13-{prod,test}` before patching.

## tester_notes

(Tester fills during confirm-phase. Suggested smoke ledger:

1. `mindsos doctor` exits 0; reports 4-pkg parity at `+phase13`
   pre-bump baseline THEN at `+phase14` post-bump.
2. `mindsos doctor --self-test` exits 0 post-bump.
3. `docker compose run --rm mindsos-test pytest tests/phase_14`
   green; isolated count matches design log estimate.
4. `docker compose run --rm mindsos-test pytest tests/` green
   (cumulative).
5. Phase 13 regression checks unmutated:
   `mindsos knowledge schema show --role ontology` still works;
   `mindsos knowledge schema validate ...` still works.
6. Phase 12 regression: `mindsos iri build ...` still works.
7. KL python smoke: import `KnowledgeLayer`, call `bootstrap()`,
   assert `global_view().roles()` returns the 6 named Global roles.
8. Install/extract round-trip smoke in python (no CLI in Phase 14).
9. `last_confirmed_phase: 14` on `knowledge-lifecycle.md`.
10. mkdocs nav shows `Concepts > Knowledge lifecycle > Global +
    Local Metagraphs (Phase 14)`.
)

## mkdocs_pages_updated

* `docs/concepts/global-local.md` — NEW (Phase 14 deliverable).
* `docs/concepts/knowledge-lifecycle.md` — Phase 14 row Status
  `planned → shipped`; front-matter `last_confirmed_phase: 14a → 14`.
* `docs/usage/knowledge/overview.md` — amended with KL bootstrap
  section.
* `docs/changelog/CHANGELOG.md` — Phase 14 entry.
* `docs/dev/repo-layout.md` — if new module files surface.
* `mkdocs.yml` — `global-local.md` added under `Concepts > Knowledge
  lifecycle` group.

## adr_amendments

* ADR-0042 amendment-1 (Global lifecycle) — Phase 14 PB-7 lock.
* ADR-0150 amendment-1 (alignment Global-only) — Phase 14 PB-8 lock.

## git_sha + image_build_hash + falkordb_version + timestamp_utc

(Filled by `mindsos confirm-phase` wrapper at run time.)
