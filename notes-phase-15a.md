# Phase 15a — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_15a_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

L2 admin importers — NEW `mindsos_admin/` package + bootstrap_global helper + 3 importers (DOLCE / OEWN / FrameNet)

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

SMOKE LEDGER (Phase 15a — L2 admin importers — DOLCE / OEWN / FrameNet):

1. `mindsos doctor` → 5-package version-string parity at `0.0.0+phase15a`
   (mindsos_core / mindsos_cli / mindsos_instances / mindsos_knowledge /
   mindsos_admin); FalkorDB pin matches manifest; image tag
   `mindsos:phase15a-prod`. [ ]
2. `mindsos doctor --self-test` exit 0. [ ]
3. `pytest tests/phase_15a -v` — isolated suite green (~50-70 passed /
   2 skipped in container; the 2 skips are
   `test_adr_amendment_sentinels.py` — ADR files live in parent project
   tree per Model C). [ ]
4. `pytest tests/` — cumulative sweep: ~2250 passed / 16 skipped (no
   regressions vs Phase 14 baseline 2148/14). [ ]
5. Importer python smoke — `bootstrap_global(importers=[DolceImporter(...),
   OewnImporter(...), FrameNetImporter(...)])` returns a Metagraph with
   all 6 named Global role-graphs ensured (ontology/lexicon/concepts
   populated; promoted-pipelines/task-patterns/problem-trace empty) per
   PB-21 parity with `KnowledgeLayer.bootstrap()` output. [ ]
6. CLI smoke — `mindsos admin --help` lists `import` subgroup;
   `mindsos admin import --help` lists `dolce` / `oewn` / `framenet`
   subcommands. [ ]
7. CLI smoke (synthetic fixture) — `mindsos admin import dolce
   --source tests/phase_15a/fixtures/dolce_synth.owl --version synth-test
   --json` returns valid JSON ImportResult with role=ontology,
   source=dolce-dul, stats={classes=7, ...}. [ ]
8. CLI smoke OEWN+FrameNet equivalents. [ ]
9. Phase 14 regression — `KnowledgeLayer.bootstrap()` still produces
   the 6-role empty Global; `kl.global_view().roles()` unchanged. [ ]
10. ADR-0044 boundary — importers write Global only; ontology importer
    never touches memories/capacity-state. [ ]
11. ADR-0010 isolation — import-isolation AST walk over
    `mindsos_admin/` finds no `mindsos_server` / `mindsos_cli`
    imports. [ ]
12. Real-dataset downloader smoke (Linux only; opt-in) —
    `scripts/fetch_datasets.sh dolce` downloads DOLCE-DUL 4.1 to
    `data/datasets/dolce-dul-4.1.owl`; `mindsos admin import dolce
    --source data/datasets/dolce-dul-4.1.owl --version 4.1 --json`
    completes. (Skip if no network; document.) [ ]

PRE-RUN STEPS [Linux]:

* `git fetch origin && git checkout -b phase-15a origin/main` (off main-
  tip post-Phase-14 squash-merge: 5282ebd).
* `cd halvim_mindsos && pip install -e . --user --break-system-packages`
  per `feedback_host_pip_refresh_on_new_package.md` (7th-site checklist
  — required because `mindsos_admin` is a NEW top-level package).
* `docker compose --profile test build mindsos-test` BEFORE
  `confirm-phase` per `feedback_confirm_phase_timeout.md` (timeout 1800s).
* `pip-compile` if requirements changed (Phase 15a adds rdflib + lxml
  to `pyproject.toml` dependencies; will need locked
  `requirements.txt` regeneration via `tools/lock.sh`).

DOCS:
- `docs/concepts/admin-global-shipping.md` full rewrite (importer
  permanent home; Phase 37 retired). `last_confirmed_phase: 14a → 15a`.
- `docs/concepts/knowledge-lifecycle.md` Phase 15 row split into 15a
  (shipped) + 15b (planned); Phase 37 row struck through.
  `last_confirmed_phase: 14 → 15a`.
- `docs/concepts/global-local.md` body amend (third install path via
  `bootstrap_global`). `last_confirmed_phase: 14 → 15a`.
- `docs/knowledge-sources/{dolce,oewn,framenet}.md` NEW per-source
  reference pages.
- `docs/changelog/CHANGELOG.md` Phase 15a entry.
- `mkdocs.yml` (Knowledge sources nav group; Admin cross-link).

ADR AMENDMENTS (parent tree per Model C):
- ADR-0042 §amendment-2 — third first-install sequence (Phase 15a PB-4-i
  Round 3).
- ADR-0140 §amendment-1 — admin permanent home; §Decision §1+§2
  superseded (Phase 15a PB-2-i Round 4). Phase 37 row in PHASE_MAP
  retired.

DESIGN LOG: see `confirmation_docs/PHASE_15a_DESIGN_LOG.md` §1 for
the full PB-1..23 ledger across 5 rounds, all user-agreed. Mid-flight
calibration: DOLCE fixture parser surfaced that bnode-restriction
subClassOf edges drop through `_frag()`'s URIRef-only filter (synthetic
fragments aren't resolved by `_add_binary_edge`). EXPECTED_STATS table
in `tests/phase_15a/test_dolce_importer.py` reflects parser behavior
(subclass_of_edges=4 for named-class pairs only). Acceptable scope
limitation — restriction nodes ARE minted, just not linked via
subclass_of.

CARRY-FORWARD TO PHASE 15b: AlignmentsImporter + `mindsos_core/schema/
migration.py` scanner module + `mindsos admin scan-schema` CLI verb +
`docs/dev/migration-playbook.md` content + ADR-0134 §amendment-3.
Per-edge alignment-anchor IRI builder defers 4th-hop to Phase 33-35
per PB-C1.
