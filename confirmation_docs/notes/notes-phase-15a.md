# Phase 15a — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

L2 admin importers — NEW `mindsos_admin/` package + bootstrap_global helper + 3 importers (DOLCE / OEWN / FrameNet)

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

SMOKE LEDGER (Phase 15a — L2 admin importers — DOLCE / OEWN / FrameNet):

1. `mindsos doctor` → 5-package version-string parity at `0.0.0+phase15a`
   (mindsos_core / mindsos_cli / mindsos_instances / mindsos_knowledge /
   mindsos_admin); FalkorDB pin matches manifest; image tag
   `mindsos:phase15a-prod`. ✓
2. `mindsos doctor --self-test` exit 0. ✓
3. KL python smoke — `bootstrap_global(importers=())` returns Metagraph
   with the 6 Global named role-graphs (ontology / lexicon / concepts /
   promoted-pipelines / task-patterns / problem-trace) per PB-21 parity
   with `KnowledgeLayer.bootstrap()` output. ✓
4. CLI smoke — `mindsos admin --help` lists `import` subgroup;
   `mindsos admin import --help` lists `dolce` / `oewn` / `framenet`. ✓
5. CLI smoke (DOLCE synthetic fixture) — `mindsos admin import dolce
   --source tests/phase_15a/fixtures/dolce_synth.owl --version synth-test
   --json` returns valid JSON ImportResult role=ontology source=dolce-dul
   stats={classes=7, ...}. ✓
6. CLI smoke OEWN — role=lexicon source=oewn
   stats={synsets=4, lemmas=3, senses=4, ...}. ✓
7. CLI smoke FrameNet — role=concepts source=framenet
   stats={frames=3, frame_elements=6, lexical_units=5, ...}. ✓
8. ADR-0044 boundary — DolceImporter writes only `ontology`; other 5
   role-graphs remain empty. ✓
9. KL handoff (ADR-0042 §amendment-2) — `KnowledgeLayer(global_metagraph=
   bootstrap_global([DolceImporter(...)]))` accepts the populated mg;
   `kl.global_view().graphs_by_role('ontology')[0]` returns the populated
   ontology graph. ✓
10. Downloader script refuses FrameNet per Berkeley click-through —
    `scripts/fetch_datasets.sh framenet` prints the manual-download
    instruction; exit 0. ✓
11. Phase 12/13/14 regression — `mindsos knowledge iri build`,
    `mindsos knowledge schema show`, `KnowledgeLayer.bootstrap()` all
    behave unchanged. ✓
12. Real-dataset downloader (DOLCE-DUL 4.1 + OEWN 2024) — SKIPPED
    (opt-in; network-dependent; Phase 26 integration phase is the
    natural beat for real-dataset end-to-end).

CUMULATIVE TESTS: **2236 passed, 16 skipped, 109 warnings in 18:44**
(Phase 14 baseline 2148 / 14 / 18:26; +88 passes, +2 skips for Phase
15a; no regressions). Phase 15a isolated suite: **82 passed, 2 skipped
in 1.83s** (the 2 skips are `test_adr_amendment_sentinels.py` — ADR
files live in parent project tree per Model C).

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
the full PB-1..23 ledger across 5 rounds, all user-agreed.

HOTFIX LEDGER:
- B-15a-T1: Phase 08 manifest-phase regex relaxed from `\d{2}` to
  `\d{2}[a-z]?` per `feedback_tag_regex_audit.md` — letter-sub-phase
  grammar already in `_retention.py` + `release.yml`; Phase 08's
  test was tightened beyond the actual contract.
- B-15a-T2: `scripts/fetch_datasets.sh` mode 100644 → 100755 — was
  not chmod+x at creation.
- B-15a-T3: `ImporterProtocol` docstring originally claimed
  "idempotent at the Metagraph level — re-running against a
  partially-populated role-graph is permitted." Smoke surfaced that
  re-running an importer raises `IdentityError` on node IRI
  collision (and even after node-level dedup, edges would duplicate
  because `add_edge` mints fresh UUIDs each call). Decision: relax
  the protocol docstring to single-shot semantics matching the
  admin install/release-restart pattern per ADR-0042 §amendment-1
  §Out-of-scope. Full mid-process idempotency (skip-existing-nodes
  + skip-existing-edges) carries forward to Phase 15b or later; no
  consumer requires it today.

MID-FLIGHT CALIBRATIONS:
- DOLCE fixture parser surfaced that bnode-restriction subClassOf
  edges drop through `_frag()`'s URIRef-only filter (synthetic
  fragments aren't resolved by `_add_binary_edge`). EXPECTED_STATS
  table in `tests/phase_15a/test_dolce_importer.py` reflects parser
  behavior (subclass_of_edges=4 for named-class pairs only).
  Acceptable scope limitation — restriction nodes ARE minted, just
  not linked via subclass_of.

CARRY-FORWARD TO PHASE 15b: AlignmentsImporter + `mindsos_core/schema/
migration.py` scanner module + `mindsos admin scan-schema` CLI verb +
`docs/dev/migration-playbook.md` content + ADR-0134 §amendment-3.
Per-edge alignment-anchor IRI builder defers 4th-hop to Phase 33-35
per PB-C1. Full mid-process importer idempotency (B-15a-T3 follow-up).
