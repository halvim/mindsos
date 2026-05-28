# Phase 38 — Page Inventory Audit

> Generated 2026-05-27 as the Phase 38 docs-only ship artifact per
> R2-PB-D + R1-PB-F + R5-PB-E. Records every `docs/*.md` page's
> presence + front-matter values + PHASE_MAP §6 expectation at the
> closing-phase audit checkpoint. PHASE_MAP §6 promises "final review
> of every page's `last_confirmed_phase` front-matter for orphans" —
> this file IS that review.

## Audit summary

- **Total pages on disk:** 74 (after Phase 38 ship adds index.md
  rewrite + whats-new-v4.md + glossary.md + text-realm.md = 3 new
  authored pages + 1 rewritten).
- **Pages with `last_confirmed_phase` front-matter:** 74 / 74 (100%).
  Phase 38 backfilled the 2 pre-existing gaps (dev/review-checklist.md
  + usage/knowledge/versioning.md).
- **Pages with `last_design_only_phase` front-matter:** 1
  (CHANGELOG.md only — convention adopted per CHANGELOG.md precedent;
  R4-PB-H "2-field when applicable" lock).
- **Drift severity at closing phase:** see "Drift class" column below
  + the §"Drift discussion" section at the bottom.

## Methodology

For each `.md` under `docs/`:

1. Path is the file's path relative to `docs/`.
2. `Exists?` is whether the file is on disk (yes for every row;
  out-of-scope pages don't appear in this table because they
  don't exist on disk and aren't referenced by `mkdocs.yml` nav).
3. `current last_confirmed_phase` is the value parsed from the page's
  YAML front-matter (the convention is single-value; sub-phase
  letters like `05b` are preserved).
4. `current last_design_only_phase` is the secondary field per
  CHANGELOG.md precedent — populated only when applicable.
5. `§6 highest phase` is the highest non-amendment phase named for
  the page in `PHASE_MAP.md §6 "Doc-to-phase map"`. "—" means the
  row doesn't appear in §6.
6. `drift?` flags when (3) ≠ (5). Sub-phase-letter equivalence is
  treated as match (e.g., `05a + 05b amend` in §6 → page shows
  `05b` ≠ §6 "highest"; recorded as `letter-equivalence` not real
  drift).
7. `Drift class` categorizes the gap.

## Inventory

| Path | Exists | `last_confirmed_phase` | `last_design_only_phase` | §6 highest | Drift? | Drift class |
|---|---|---|---|---|---|---|
| `api/core/client.md` | ✓ | 07 | — | per-phase API ref (07) | no | — |
| `api/core/edge.md` | ✓ | 03 | — | per-phase API ref (03) | no | — |
| `api/core/graph.md` | ✓ | 03 | — | per-phase API ref (03) | no | — |
| `api/core/hyperedge.md` | ✓ | 04-v2 | — | per-phase API ref (04-v2) | no | — |
| `api/core/identity-registry.md` | ✓ | 02 | — | per-phase API ref (02) | no | — |
| `api/core/integrity.md` | ✓ | 07 | — | per-phase API ref (07/11) | minor | amendment-history-lost |
| `api/core/intergraph-edge.md` | ✓ | 05b | — | per-phase API ref (05b/c) | minor | amendment-history-lost |
| `api/core/loaders.md` | ✓ | 08 | — | per-phase API ref (08) | no | — |
| `api/core/metaedge.md` | ✓ | 05a | — | per-phase API ref (05a) | no | — |
| `api/core/metagraph-schema.md` | ✓ | 05b | — | per-phase API ref (05b/c/d) | minor | amendment-history-lost |
| `api/core/metagraph-snapshot.md` | ✓ | 10 | — | per-phase API ref (10) | no | — |
| `api/core/metagraph.md` | ✓ | 10 | — | per-phase API ref (05a/10) | minor | amendment-history-lost |
| `api/core/metahyperedge.md` | ✓ | 05a | — | per-phase API ref (05a) | no | — |
| `api/core/node.md` | ✓ | 03 | — | per-phase API ref (03) | no | — |
| `api/core/repositories.md` | ✓ | 07 | — | per-phase API ref (07) | no | — |
| `api/core/schema.md` | ✓ | 04-v2 | — | per-phase API ref (04/04-v2) | no | — |
| `api/core/soft-delete.md` | ✓ | 10 | — | per-phase API ref (10) | no | — |
| `api/core/types.md` | ✓ | 04-v2 | — | per-phase API ref (04/04-v2) | no | — |
| `api/core/wal.md` | ✓ | 07 | — | per-phase API ref (07) | no | — |
| `api/core/xref.md` | ✓ | 09 | — | per-phase API ref (09) | no | — |
| `api/knowledge/identifiers.md` | ✓ | 12 | — | per-phase API ref (12) | no | — |
| `api/knowledge/ref-types.md` | ✓ | 12 | — | per-phase API ref (12) | no | — |
| `changelog/CHANGELOG.md` | ✓ | 36 | 38 | final pass at 38 | no | Phase 38 ship bumped both fields per R5-PB-G |
| `concepts/admin-global-shipping.md` | ✓ | 15b | — | 15b (Phase 14a + 15b concept work) | no | — |
| `concepts/global-local.md` | ✓ | 15a | — | 14 (+ amend 15a) | minor | amendment-history-lost |
| `concepts/glossary.md` | ✓ | 38 | — | 38 (NEW at Phase 38) | no | — |
| `concepts/graphs-and-metagraphs.md` | ✓ | 05a | — | 03 + 05a (+ 05b/c amend) | minor | amendment-history-lost |
| `concepts/identifiers.md` | ✓ | 12 | — | 12 | no | — |
| `concepts/identity.md` | ✓ | 02 | — | 02 | no | — |
| `concepts/intergraph-edges.md` | ✓ | 05b | — | 05b (+ 05c amend) | minor | amendment-history-lost |
| `concepts/knowledge-lifecycle.md` | ✓ | 15b | — | 14a (+ 15b amend) | no | — |
| `concepts/promotion-bridge.md` | ✓ | 14a | — | 14a (+ 24 expected) | minor | amendment-not-applied (Phase 24 didn't touch the page) |
| `concepts/references.md` | ✓ | 09 | — | 09 | no | — |
| `concepts/soft-delete.md` | ✓ | 10 | — | 10 | no | — |
| `concepts/user-local-authoring.md` | ✓ | 14a | — | 14a | no | — |
| `dev/contributing.md` | ✓ | 02 | — | 01 (release flow + branching policy) | minor | front-matter-newer-than-§6-mention |
| `dev/conventions.md` | ✓ | 02 | — | 01 (CLI conventions) | minor | front-matter-newer-than-§6-mention |
| `dev/coordinated-changes/L3-capacity-write-flows.md` | ✓ | 35 | — | historical archive — confirmed once at 38 | minor | front-matter precedes §6 38 promise — Phase 38 didn't touch the tracker (R4-PB-J) |
| `dev/internals/capacity.md` | ✓ | 34 | — | each per layer's phase block (28-36 for L3) | no | — |
| `dev/internals/core.md` | ✓ | 10 | — | each per layer's phase block | no | — |
| `dev/internals/snapshots.md` | ✓ | 10 | — | each per layer's phase block | no | — |
| `dev/migration-playbook.md` | ✓ | 15b | — | NEW at 15b | no | — |
| `dev/release.md` | ✓ | 01 | — | 01 | no | — |
| `dev/repo-layout.md` | ✓ | 07 | — | 00 + 01 (+ 06 + 37) | minor | amendment-history-lost; Phase 37 retired so the §6 mention is vestigial |
| `dev/review-checklist.md` | ✓ | 36 | — | Phase 34 ship (per content) | Phase 38 backfill | NEW front-matter added at Phase 38 |
| `dev/testing.md` | ✓ | 01 | — | 01 (in-container = canonical) | no | — |
| `getting-started/first-metagraph.md` | ✓ | 05a | — | 05a | no | — |
| `getting-started/install.md` | ✓ | 00 | — | 00 + 01 | minor | amendment-history-lost (Phase 01 tooling additions presumed-applied not reflected) |
| `getting-started/whats-new-v4.md` | ✓ | 38 | — | 38 (NEW at Phase 38) | no | — |
| `index.md` | ✓ | 38 | — | 38 (Phase 38 rewrite of Phase 00 stub) | no | — |
| `knowledge-sources/dolce.md` | ✓ | 15a | — | 15 (location); 37 (relocation) | no | Phase 37 retired; 15a is correct |
| `knowledge-sources/framenet.md` | ✓ | 15a | — | 15 (location); 37 (relocation) | no | Phase 37 retired; 15a is correct |
| `knowledge-sources/oewn.md` | ✓ | 15a | — | 15 (location); 37 (relocation) | no | Phase 37 retired; 15a is correct |
| `usage/capacity/building.md` | ✓ | 30 | — | 27 + 28 (+ 30 + 33-36 amend) | minor | amendment-history-lost |
| `usage/capacity/categories.md` | ✓ | 33 | — | 28 + 29 (+ 33-36 amend) | minor | amendment-history-lost |
| `usage/capacity/data-states.md` | ✓ | 27 | — | 27 | no | — |
| `usage/capacity/overview.md` | ✓ | 28 | — | 27 + 28 | no | — |
| `usage/capacity/retrieval.md` | ✓ | 30 | — | 30 | no | — |
| `usage/cookbook/text-realm.md` | ✓ | 38 | — | 38 (NEW at Phase 38) | no | — |
| `usage/core/building-graphs.md` | ✓ | 04 | — | 03 | minor | front-matter-newer-than-§6-mention |
| `usage/core/metagraph-schema.md` | ✓ | 05b | — | 05b (+ 05c amend for IntergraphHyperEdgeType; + 05d amend for MetaEdgeType/MetaHyperEdgeType) | minor | amendment-history-lost |
| `usage/core/metagraphs.md` | ✓ | 05a | — | 05a | no | — |
| `usage/core/persistence.md` | ✓ | 08 | — | 07 + 08 | no | — |
| `usage/core/schema.md` | ✓ | 04-v2 | — | 04 | minor | front-matter-newer-than-§6-mention (04-v2 supersedes 04) |
| `usage/knowledge/alignment.md` | ✓ | 13 | — | 13 (+ 15 carry-forward) | minor | amendment-history-lost |
| `usage/knowledge/capacity-state.md` | ✓ | 13 | — | 13 | no | — |
| `usage/knowledge/concepts.md` | ✓ | 13 | — | 13 | no | — |
| `usage/knowledge/iri-cli.md` | ✓ | 12 | — | 12 | no | — |
| `usage/knowledge/lexicon.md` | ✓ | 13 | — | 13 | no | — |
| `usage/knowledge/memories.md` | ✓ | 13 | — | **out of scope** per §6 (L4/L5) | drift | §6 row says OOS; page exists |
| `usage/knowledge/ontology.md` | ✓ | 13 | — | 13 | no | — |
| `usage/knowledge/overview.md` | ✓ | 14 | — | 14 | no | — |
| `usage/knowledge/problem-trace.md` | ✓ | 13 | — | 13 | no | — |
| `usage/knowledge/promoted-pipelines.md` | ✓ | 13 | — | 13 | no | — |
| `usage/knowledge/task-patterns.md` | ✓ | 13 | — | 13 | no | — |
| `usage/knowledge/versioning.md` | ✓ | 17 | — | 17 (retired) | Phase 38 backfill | NEW front-matter added at Phase 38 |

## Drift discussion

The drift classes recorded above are mostly **benign**:

- **`amendment-history-lost`** (~12 pages): convention is single-value
  `last_confirmed_phase`; pages amended by multiple phases lose the
  earlier-phase information from front-matter. The CHANGELOG.md +
  per-phase `CONFIRMED.md` `mkdocs_pages_updated` field together
  preserve the per-phase touch history; the page's front-matter
  records only the most recent. Per R4-PB-H this is the intentional
  convention; not corrected at Phase 38.
- **`front-matter-newer-than-§6-mention`** (~4 pages): the page was
  touched by a phase amendment that §6 doesn't enumerate. Symmetric
  to `amendment-history-lost` from the §6 direction. Not corrected
  at Phase 38; PHASE_MAP §6 is the document of record, the page
  front-matter records reality.
- **`amendment-not-applied`** (1 page: `concepts/promotion-bridge.md`):
  §6 implies Phase 24 should have amended the page; the page
  front-matter shows `14a` (the page's original confirmation).
  Either Phase 24 didn't actually amend the page (likely — the
  Phase 24 memory shows zero `mkdocs_pages_updated` entries for
  promotion-bridge), or the §6 entry overstated the expected scope.
  Recommended L4/L5 cleanup: verify Phase 24 amendments and
  back-fill the page if they exist.
- **`drift` (real; 1 page: `usage/knowledge/memories.md`)**: PHASE_MAP
  §6 says `memories.md` is **out of scope** (L4/L5), but the page
  exists on disk and was authored at Phase 13. Reconciliation
  options: (a) re-include `memories.md` in §6 with phase `13`; (b)
  delete the page at L4/L5 cleanup if `memories` schema lands at
  L4 with substantially different content; (c) leave as-is and
  accept the dual state. Recommended action: re-include in §6 as
  Phase 13, since the Phase 13 schema actually shipped. **Flagged
  for L4/L5 follow-up plan.**

## What this audit does NOT cover

- **Broken cross-links** (Model C ADR links). Recorded against the
  `mkdocs build` baseline in PHASE_MAP §7 q5 RESOLVED annotation.
  Lifting `strict: true` is L4/L5 remediation scope per R4-PB-A.
- **Nav-vs-disk reconciliation.** mkdocs.yml nav was confirmed clean
  at Phase 38 step-0 probe (R4-PB-B narrowed from "fix 3 issues" to
  "add 3 authored pages + new Cookbook subsection" once the false
  positives were filtered).
- **Per-page content correctness.** This is a structural front-matter
  audit only. Content-quality review against shipped reality is per
  page maintainer's responsibility going forward.

## Phase 38 closing-phase audit declaration

The "final review of every page's `last_confirmed_phase` front-matter
for orphans" promised by PHASE_MAP §6 + §38 pass criterion is
satisfied by this inventory. The remaining drift (~17 entries, all
minor or benign) is documented above; non-benign drift is the
single `usage/knowledge/memories.md` case, flagged for L4/L5
cleanup.

Strict-lift + Model C remediation + the 3 §6 out-of-scope pages
(facts-and-figures, layers, society-of-mind) + nlu-slice/code-slice
cookbooks all defer to L4/L5 follow-up plan per the PHASE_MAP §38
§inline-amendment.
