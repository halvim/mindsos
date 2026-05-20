# Phase 15b — Design Log

> Captured 2026-05-20. Records 20 design pushbacks across 6 pre-impl
> rounds + the discovery that ADR-0134's scanner module shipped at
> Phase 11 + the resulting reframe of Phase 15b as a design-only phase
> closing carry-forwards. Future amendments to ADR-0134 / ADR-0150
> should consult this file for rationale.

## 0. Scope at chat-open

PHASE_MAP §Phase 15b row (handoff version, written by Phase 15a's PR):

* `mindsos_admin/importers/alignments.py` (AlignmentsImporter — parametric
  `target_roles`; writes alignment edges via L1; 3 ordered pairs with
  fallback per Phase 15a PB-23).
* `mindsos_core/schema/migration.py` NEW per ADR-0134 §Implementation
  references (`Schema.migrate_from(old_schema, on_violation="report")`;
  `SchemaViolation` dataclass).
* `mindsos_core/exceptions.py` additions: `SchemaMigrationError`,
  `UnknownEdgeTypeError`.
* `mindsos admin scan-schema [--role R] [--json]` CLI verb (backend
  location TBD between `mindsos_admin/scan.py` and
  `mindsos_cli/commands/admin.py`).
* `docs/dev/migration-playbook.md` full content (Phase 13/14/15a carry).
* ADR-0134 §amendment-3 (Phase 13/14/15a carry).
* `docs/knowledge-sources/alignments.md` NEW.
* PHASE_MAP §15b row + `knowledge-lifecycle.md` Phase 15b row flip to
  shipped.

Layer per handoff: L1 + L2 (admin) + CLI. Net-new? Partial. Deps: 15a.

**Re-classified across 6 rounds to: design-only phase per PHASE_MAP §1
exception, no code other than test sentinels, no version bump, no
tag.** Trigger: the `mindsos_core/schema/migration.py` module that
PB-9 (Phase 15a) carried forward to 15b ALREADY EXISTS at Phase 11
(432 LOC; `migrate_from(old, target, *, new, detail, old_schema_name)`;
five `ViolationKind` values including HyperEdge; summary/each modes;
`old_schema_name` policy warning; `SchemaMigrationError`;
`UnknownEdgeTypeError` at `mindsos_core/exceptions.py:415`; full
test surface at `tests/phase_11/test_migrate_from_*.py` +
`test_loader_policy_*.py`). The 15b carry-forward was based on a
mis-read of Phase 11's scope.

## 1. Design pushbacks (PB-1..20) — six rounds, all user-agreed

### Round 1 — initial architectural scoping (PB-1..7)

#### PB-1 — Pair-graph contents: XRef-based, not anchor-node intra-graph

**Trigger:** prompt says "AlignmentsImporter writes alignment edges via
L1 (intra-graph for now)" but alignments by definition connect nodes
across different role-graphs (DOLCE class in `ontology` ↔ OEWN synset in
`lexicon`). Phase 09 + ADR-0128 ship XRef for exactly this. Intra-graph
write in `alignment:<a>:<b>` requires inventing anchor nodes per
alignment — the per-edge-anchor-IRI question PB-C1 (Phase 15a) punted
four hops. Punting the IRI while keeping the construct that needs the
IRI is incoherent.

Three considered: (A) anchor-node intra-graph (current spec; opaque IDs);
(B) XRef-based (pair-graph empty; XRefs `(source, target, ref_type)`);
(C) hybrid — anchor node with deterministic IRI shipped now.

**Lock: B.** Phase 09's machinery does exactly what alignment needs;
pair-graph existence is the namespace marker only; survives re-imports
cleanly without anchor-node migration at Phase 33-35. C contradicts the
4-hop defer.

#### PB-2 — Scanner needs a synthetic-real-schema diff test [SUPERSEDED Round 3]

**Trigger:** ADR-0134 §closing requires "KL importers use scanner output
for at least one role-graph schema bump" to flip Accepted. Phase 15b's
scanner ships without a real consumer; CLI-shape tests don't validate
output contract.

Three considered: (A) ship as planned; (B) synthesize one real
role-graph schema diff in 15b test surface; (C) defer entire scanner.

**Lock: B.** Validate scanner against real schemas; give §amendment-3
something to document.

**SUPERSEDED (Round 3 finding):** Phase 11 already ships full scanner
test surface (`tests/phase_11/test_migrate_from_unit.py` +
`test_migrate_from_metagraph.py`). PB-2 reduces to bookkeeping.

#### PB-3 — `mindsos admin scan-schema` defers to Phase 26 [SUPERSEDED Round 3]

**Trigger:** Phase 14a round-3 lock — CLI state-file access is Phase 26
(integration A). Server is Phase 18+. What populated Global does
scan-schema scan at 15b?

Three considered: (A) in-memory only (CLI builds fresh `bootstrap_global`
and scans); (B) pre-empt Phase 26 state-file read; (C) ship L1 module
without CLI verb in 15b — CLI lands in Phase 26.

**Lock: C.** Respects layer ownership; defers CLI to its natural phase.

**SUPERSEDED:** With scanner module discovered already-shipped at Phase
11 (Round 3), scan-schema CLI verb carry-forward closes to Phase 26 per
this lock unchanged. PHASE_MAP §15b row drops the CLI verb entirely.

#### PB-4 — Source format: FN-WN real, DOLCE pairs deferred [MOOT under P5]

**Trigger:** real alignment data sourcing per pair — FN-WN is
well-studied (Berkeley FrameNet ships WN-mappings); DOLCE-OEWN and
DOLCE-FrameNet have no canonical datasets.

Three considered: (A) CSV universal format; (B) format-per-source; (C)
FN-WN only — drop DOLCE pairs from default; PB-23 fallback authorises.

**Lock: C.** Don't ship importers for pairs with no source data; PB-23
fallback already permits.

**MOOT under P5:** AlignmentsImporter defers entirely; pair-selection
question reopens at the closure phase.

#### PB-5 — ADR-0134 §amendment-3 defers to real-bump phase [SUPERSEDED Round 4]

**Trigger:** PB-2 / PB-B1 (Phase 15a) said no flip until real schema
bump; nothing in 15b is a real schema bump. Amendment-3's original
charter was "documents the importer-flow interaction" — but the
interaction is *importers don't call the scanner.*

Two considered: (A) defer §amendment-3 to real-bump phase; (B) land with
weak content.

**Lock: A.**

**SUPERSEDED (Round 4):** Round 3 finding (scanner already shipped at
Phase 11) means §amendment-3's content is now Phase 11's reality
documentation, not Phase 15b importer-flow content. §amendment-3
LANDS at 15b per pick F1 (Round 4) — with §closing relaxation enabling
the flip.

#### PB-6 — Importer idempotency carries forward [MOOT under P5]

**Trigger:** Phase 15a B-15a-T3 follow-up. Current contract single-shot.
AlignmentsImporter parametric over pairs makes mid-process partial
failure (pair 2 of 3 dies on a malformed row) a real risk.

Three considered: (A) per-pair idempotency in AlignmentsImporter only;
(B) tighten `ImporterProtocol` for all 4 importers; (C) carry forward
to whichever phase first needs mid-process re-import.

**Lock: C.** No 15b consumer forces the question; carrying past 15b
doesn't increase risk.

**MOOT under P5:** AlignmentsImporter defers; idempotency question
reopens at closure phase.

#### PB-7 — Layer-mixing in PHASE_MAP §15b row

**Trigger:** §15b row reads "L1 + L2 (admin) + CLI." Tolerable per Phase
15a PB-3a but means literal-audit + version-bump touch surfaces in
3 layers per phase. No counter-option short of sub-phasing.

**Lock: accept as flagged.** MOOT under P5 — design-only phase has no
production code in any layer.

### Round 2 — protocol + source format detail (PB-8..12)

#### PB-8 — AlignmentsImporter source coupling: CSV via extraction script [MOOT under P5]

**Trigger:** FN-WN mappings live INSIDE FrameNet 1.7's per-LU XML
(`<wordNet>` tags inside `lu/lu*.xml`). Not a separate dataset.

Three considered: (A1) AlignmentsImporter re-parses FN XML tree; (A2)
FrameNetImporter emits sidecar alignment data; (A3) pre-extracted CSV
via `scripts/extract_fn_wn_alignments.py`.

**Lock: A3.** Honest about where data lives; AlignmentsImporter stays
format-agnostic; script reusable for other extractions.

**MOOT under P5:** carry-forward bundle.

#### PB-9 — `target_roles` semantics under XRef-based writes [MOOT under P5]

**Trigger:** Phase 15a PB-22 locked `target_roles` as "role-graphs I
write into." AlignmentsImporter (XRef-based per PB-1) writes ZERO nodes
into the pair-graph — XRefs live in the Metagraph's XRef store per
Phase 09, not in any role-graph.

Three considered: (G1) soften semantics to "role-graphs I touch"; (G2)
add `target_xref_pairs` second protocol attribute; (G3)
`target_roles=()` for AlignmentsImporter; `pairs` attribute carries
pair-graph names.

**Lock: G3.** Honors PB-22 strict write-target semantics; surfaces
alignment's structural asymmetry. `bootstrap_global` doesn't change —
importer's `run()` auto-ensures pair-graphs per Phase 15a PB-14.

**MOOT under P5:** carry-forward bundle.

#### PB-10 — Scanner ships as planned despite no programmatic consumer [SUPERSEDED Round 3]

**Trigger:** With PB-3 dropping CLI verb and PB-5 deferring §amendment-3,
scanner ships unit-test-only — no programmatic consumer until first
real-bump phase.

Two considered: (D1) ship anyway (test surface validates contract); (D2)
defer entire scanner.

**Lock: D1.**

**SUPERSEDED (Round 3):** scanner module IS shipped — at Phase 11, not
15b. PB-10 reduces to "scanner has been shipped for two phases without
a programmatic consumer; this is acceptable given Phase 11's test
coverage." Informs §amendment-3 §closing relaxation (PB-13).

#### PB-11 — XRef `ref_type` vocabulary: per-pair [MOOT under P5]

**Trigger:** AlignmentsImporter writes XRefs (PB-1). Pick ref_type
string per ADR-0047 open vocabulary.

Three considered: (R1) single `"alignment"`; (R2) per-pair
`"alignment:<a>:<b>"`; (R3) source-typed (`"fn_wn_lexical"`).

**Lock: R2.** Per-pair string mirrors pair-graph namespace; vocab
growth bounded by closed pair set (ADR-0150 §amendment-1 keeps
alignment Global-only at v1; PB-23 caps at 3 ordered pairs).

**MOOT under P5:** carry-forward bundle.

#### PB-12 — Migration-playbook depth: API + 1 example + recipes pending [REFINED Round 5]

**Trigger:** With PB-3 dropping CLI verb and PB-5 deferring
§amendment-3, playbook documents L1 API for hypothetical importer
authors.

Three considered: (E1) full playbook (API + 3 patterns + recipes); (E2)
defer entirely; (E3) stub linking to Phase 11 tests.

**Lock: E3.**

**REFINED Round 5 (PB-17 below):** lock upgraded from E3 (stub) to C2
(API + one Phase 11-derived example; recipes section labelled
"pending first real-migration consumer"). Stub-only is worse than the
sentinel chain warrants; real-content-with-honest-recipes-placeholder
is the right depth.

### Round 3 — ADR-0134 signature probe + critical finding

#### PB-13 — ADR-0134 `migrate_from` signature ambiguity [RESOLVED by Phase 11 finding]

**Trigger:** ADR-0134 §1 spec reads `migrate_from(self, old_schema, *,
on_violation="report") -> list[SchemaViolation]`. Docstring says it
scans "persisted data validated under `old_schema`" — but signature has
no data-source parameter.

Four considered: (M1) `migrate_from(old_schema, metagraph)`; (M2)
per-graph dispatch; (M3) schema-symbolic (no data); (M4) stream of
nodes/edges.

**Lock: M2.** Per-graph scan keeps L1 surface narrow; metagraph-wide
convenience adds as sibling later.

**RESOLVED:** grep surfaced `mindsos_core/schema/migration.py` (432 LOC,
shipped at Phase 11). Actual signature: `migrate_from(old, target, *,
new, detail, old_schema_name)`. `target` accepts `Graph | Metagraph`
via isinstance dispatch — closer to **M1 + M2 hybrid via single entry
point** than to M2 alone. Phase 11 settled the ambiguity at impl time;
ADR-0134 never reflected it. PB-13 lock superseded by Phase 11's
shipped reality; §amendment-3 (Round 4 PB-14) documents the actual
signature.

### Round 3.5 — critical finding + scope reframe

#### PB-14 — Phase 15b reframes as design-only phase (P5)

**Trigger:** grep `UnknownEdgeTypeError|SchemaMigrationError` →
22 matches across:

* `mindsos_core/schema/migration.py` — 432 LOC; full scanner module.
* `mindsos_core/exceptions.py:415` — `UnknownEdgeTypeError`
  (Phase 11; ADR-0134 amendment-2 loader-warning surface).
* `tests/phase_11/test_migrate_from_unit.py` — unit coverage.
* `tests/phase_11/test_migrate_from_metagraph.py` — metagraph-wide
  coverage.
* `tests/phase_11/test_loader_policy_{unit,integration}.py` — loader
  surface.
* `confirmation_docs/PHASE_11_DESIGN_LOG.md` PB-1/7/8/17 — design
  decisions:
  * PB-1 A — detection only (ADR-0134 §"NOT do" honored).
  * PB-7 C — coverage = Schema-level (Node + Edge + HyperEdge); fifth
    `ViolationKind` value `removed_hyperedge_type` not in ADR-0134 §1.
  * PB-8 A — summary/each detail modes (caps pathological output); not
    in ADR-0134 §1.
  * PB-17 C — single entry point with isinstance routing (Graph /
    Metagraph); `old_schema_name` policy warning surface; not in
    ADR-0134 §1.

Phase 15b's promised L1 scanner module + `SchemaMigrationError` +
`UnknownEdgeTypeError` are NOT carry-forwards — they've been shipped
for two confirmed phases. The Phase 15a → 15b handoff was based on a
misread of Phase 11's scope.

Five considered:

* (P1) Ship Phase 15b as a real (small) phase — AlignmentsImporter +
  bookkeeping; own branch, tag, confirmation doc.
* (P2) Roll into Phase 15a as hotfix / supersession (v2).
* (P3) Roll into Phase 16 (promotion machinery already lands at
  `mindsos_admin/`).
* (P4) Defer AlignmentsImporter to Phase 33-35 alongside L3
  alignment-lookup capacity (build-for-first-consumer).
* (P5) Make Phase 15b docs-only — ratify ADR-0134 §amendment-3
  (Phase 11 reality), ship `docs/dev/migration-playbook.md` against
  Phase 11's actual API, ship lifecycle doc updates; AlignmentsImporter
  defers (P4 logic rolled in).

**Lock: P5.** Phase 11 + 15b together satisfy ADR-0134's
ship-criteria (with §closing relaxation per PB-16 below).
AlignmentsImporter has no read consumer until L3 alignment-lookup
capacity ships — building for no consumer is the YAGNI failure mode
Phase 15a PB-3 / PB-C1 declined four times. 15b joins Phase 14a as a
design-only phase under PHASE_MAP §1 exception.

PB-2 / PB-3 / PB-4 / PB-6 / PB-8 / PB-9 / PB-11 marked MOOT (carry into
the AlignmentsImporter closure phase, not 15b).

### Round 4 — closure targets + §closing relaxation (PB-15..17)

#### PB-15 — Carry-forward closure target: split by natural owner [REVISED Round 5]

**Trigger:** P5 lock relocates five items to a future phase:
AlignmentsImporter, per-edge alignment-anchor IRI builder,
scan-schema CLI, real FN-WN data extraction, L3 alignment-lookup
capacity (already-scheduled but uncertain phase). Phase 33-35 is L3
write capacities; piling 5 items there repeats Phase 15-monolith
mistake.

Three considered: (G1) all 5 land at 33-35; (G2) split by natural
owner — importer + IRI builder at NEW "Phase 32b" between L3 read and
Phase 32 integration; scan-schema CLI at Phase 26 (PB-3 locked);
L3 capacity stays at 33-35 with synthetic stub data; (G3) Phase 24
audit-gate slot.

**Lock: G2.** Distributes by natural owner; no phase overloaded.

**REVISED Round 5 (PB-18 below):** "Phase 32b" placement is WRONG —
Phase 32 is Integration B; inserting net-new code AFTER Phase 32
defeats the integration's purpose. Locked target re-relocates to E4
(TBD per design review at the alignment-lookup capacity phase).

#### PB-16 — ADR-0134 §closing relaxation (F1)

**Trigger:** ADR-0134 §closing reads "ADR moves to Accepted when
scanner + loader warning land, **KL importers use scanner output for
at least one role-graph schema bump**, and `docs/dev/migration-playbook.md`
documents the pattern." Phase 11 + 15b satisfy items 1 and 3 but the
middle clause never materialises — scanner's actual consumers are
admin-CLI scans (Phase 26+) and release-gate audits (Phase 24+ per
ADR-0144), not import-time schema migration. The original §closing
was written under a consumer model that didn't survive Phase 15a's
admin-package decision (ADR-0140 §amendment-1).

Three considered: (F1) relax §closing to drop the importer-consumer
clause — Accepted requires scanner + loader + playbook + Phase 11
test-coverage demonstrating the API contract; (F2) keep §closing
as-is, don't flip — Status stays Proposed; §amendment-3 documentary
only; (F3) reinterpret the importer-consumer clause as satisfied by
Phase 11's `test_migrate_from_metagraph.py`.

**Lock: F1.** Honest relocation of the criterion to match actual
consumers. F2 wastes Phase 11's work; F3 stretches "KL importers use
scanner output" past breaking. §amendment-3 §3b carries the
relaxation text + the flip.

#### PB-17 — Phase 15b as numbered design-only phase (H1)

**Trigger:** PHASE_MAP §1 design-only exception was carved for Phase
14a (mid-stream synthesis between code phases). 15b as design-only
right after 15a code-phase could read as "15a was incomplete."

Three considered: (H1) numbered design-only phase (P5 as stated); (H2)
fold under `phase-15a-v2-confirmed` supersession; (H3) skip the phase
entirely — non-phased docs PR.

**Lock: H1.** Design-only Phase 15b is structurally cleanest. "15a was
incomplete" reading is correct but harmless — 15a's design log
explicitly carried these items forward; closing them at 15b is doing
what the carry-forward promised. H2 abuses supersession (mechanism is
for regressions/expansions, not carry-forward closure). H3 invents a
new PR category to save ceremony.

### Round 5 — placement + amendment scoping (PB-18..21)

#### PB-18 — Carry-forward closure target re-relocates: TBD per Phase 28 review

**Trigger:** PHASE_MAP §1 explicitly: "Phases 26 and 32 are convergence
points that depend on all prior shipped phases." Phase 32 = Integration
B (L0+L1+L2+L3 read-side regression sweep). Inserting "Phase 32b"
AFTER Phase 32 means the integration sweep does not cover the new
admin importer. PB-15's G2 placement was wrong.

Also: Phase 15a PB-C1 cited "L3 alignment-lookup capacity at Phase
33-35" — but Phase 33-35 are L3 **write** capacities per PHASE_MAP;
alignment-lookup is a read capacity, which would live in Phase 27-31.
The original Phase 33-35 cite is suspect.

Four considered: (E1) Phase 25b before Integration A — alignment data
shipped so Phase 26 covers it; (E2) Phase 31b before Integration B; (E3)
Phase 28 absorbs (L3 12 categories + role-graph bootstrap); (E4) TBD —
defer the precise closure slot to whichever later phase first opens the
alignment-lookup capacity question.

**Lock: E4.** Phase 15b is design-only ADR-amendment work, not authority
to relocate code across 17 phases. PHASE_MAP §15b row writes "alignment
carry-forwards: closure phase TBD per Phase 28 design review";
ADR-0150 §amendment-2 footnotes the same. Phase 28 (L3 12 categories +
role-graph bootstrap) inherits the question because Phase 28 is where
the L3 capacity surface gets enumerated — if alignment-lookup is one
of the 12, the question is settled at 28.

#### PB-19 — ADR-0150 §amendment-2 scope: supporting-evidence correction (A2)

**Trigger:** ADR-0150 §amendment-1 (Phase 14) contains "Phase 15's
importers (DOLCE↔OEWN, OEWN↔FrameNet, etc.) all write Global
alignments." That sentence is now factually wrong — Phase 15a shipped
3 source importers + 0 alignment importers. §amendment-2 has to
either correct this evidence or lock new architectural scope.

Three considered: (A1) drop §amendment-2 entirely (PHASE_MAP carries
scheduling); (A2) §amendment-2 as supporting-evidence correction only —
fixes the stale sentence; explicitly states architectural decision
unchanged (alignment Global-only at v1); references PHASE_MAP §15b
row for deferred scheduling; (A3) §amendment-2 as architectural
scheduling lock.

**Lock: A2.** Correct the stale evidence; architectural decision
unchanged; doesn't lock phase numbers in the ADR (house style:
PHASE_MAP carries scheduling).

#### PB-20 — ADR-0134 §amendment-3: subsections 3a + 3b (B3)

**Trigger:** §amendment-3 (per F1 + Phase 11 reality) carries two
distinct changes: (a) documentary update for Phase 11's signature +
5-kind violations + summary/each modes + `old_schema_name` policy;
(b) substantive §closing relaxation enabling the flip.

Three considered: (B1) single §amendment-3 covering both; (B2) split
into §amendment-3 (documentary) + §amendment-4 (substantive flip);
(B3) single §amendment-3 with explicit subsections (3a documentary,
3b substantive).

**Lock: B3.** Single amendment per phase is house convention;
subsections give auditor the documentary-vs-substantive distinction
without burning a second amendment number.

#### PB-21 — Migration-playbook depth refined to C2

**Trigger:** With PB-12's E3 stub deemed thinner than the sentinel
chain warrants, scope-up to API + one Phase 11-derived example +
recipes-pending placeholder.

**Lock: C2.** Real content for API surface + one Phase
11-test-derived example (`test_migrate_from_metagraph.py`
paraphrased); recipes section labelled "pending first real-migration
consumer" with one-line placeholder. Honest about what's exercised
and what isn't.

### Round 6 — sentinels + verification gate (PB-22..23 + process P1+D1)

#### PB-22 — Test sentinels for ADR amendments (T1)

**Trigger:** PHASE_MAP §1 design-only exception wording "no code"
permits or forbids test sentinels? Phase 14a precedent (the only prior
design-only phase) shipped `tests/phase_14a/test_adr_amendment_sentinels.py`
for its ADR-0150 §amendment work. Phase 15a (code phase) shipped
`tests/phase_15a/test_adr_amendment_sentinels.py`. The sentinel chain
detects amendment removal/edit.

Two considered: (T1) Phase 15b ships
`tests/phase_15b/test_adr_amendment_sentinels.py` (ADR-0134
§amendment-3 + ADR-0150 §amendment-2; skip-in-container per Model C);
(T2) no test sentinels.

**Lock: T1.** Sentinel chain is load-bearing across 14a→15a→15b.
PHASE_MAP §1 "no code" reads as "no production Python code" —
test sentinels are bookkeeping code and ship. Mirrors Phase 14a's
precedent.

#### PB-23 — Phase 28 row review note (B2)

**Trigger:** PB-18's E4 lock defers carry-forward closure to "whichever
later phase first opens the alignment-lookup capacity question." Which
PHASE_MAP row carries the review note?

Four considered: (B1) Phase 27 review note (current pick); (B2) Phase
28 review note — natural-owner phase for the alignment-lookup-vs-12-categories
enumeration; (B3) cross-reference on Phase 27-31; (B4) new
"Carry-forward closure registry" section in PHASE_MAP §1.

**Lock: B2.** Phase 28 = "L3 12 categories + dual metagraph +
role-graph bootstrap + capability gate" — the enumeration point. PHASE_MAP
§28 row gains a note: "Review at design pass: does alignment-lookup
land as one of the 12 categories? If yes, schedule admin alignment
importer + per-edge IRI builder ship-slot accordingly (carry-forward
from Phase 15b §amendment-2)."

#### Process P1 — Verify Phase 15a remote state before 15b branch

**Trigger:** sandbox cannot `git fetch origin`. Local main tip
`5282ebd` ("Phase 14 backfill") — Phase 15a's squash-merge SHA not
visible. No local `PHASE_15a_CONFIRMED.md`. The Phase 15b prompt
asserted Phase 15a is shipped + tagged; prompt has already been wrong
once (PB-14 scanner-already-shipped finding).

**Lock: verify on Mac before any 15b branch creation.** `git fetch
origin && git log --oneline origin/main | head -3` should show the
15a squash-merge SHA at tip; `git tag -l | grep phase-15a` should
show the tag. Design log drafting (this file) proceeds in parallel.

#### Process D1 — ADR files in non-git parent tree: accept Model C trade

**Trigger:** Per memory entry `project_mindsos_phase_14a_shipped.md`:
"halvim_mindsos is own git repo separate from parent /Layered
Intelligence/ (parent has no .git; ADR lives at parent root per
Model C)." 15b's ADR amendments aren't in halvim_mindsos's PR diff;
no git history protects them; sentinel tests (PB-22) are the only
guard.

Three considered: (D1) accept Model C status quo; (D2) initialise git
on /Layered Intelligence/ in 15b — massive scope creep; (D3) mirror
ADRs into halvim_mindsos.

**Lock: D1.** Phase 14a settled Model C deliberately; reopening at 15b
is scope creep well beyond design-only mandate. Sentinel chain
carries the load. Flagged as known weakness in §3 below; revisit if
risk materialises.

### Round 7 — sign-off

No remaining material pushbacks across `doctor --self-test` parity,
`manifest.toml [mindsos] phase`, `release.yml`,
`requirements_txt_sha256`, branch-off semantics for Phase 16, Phase 14a
`NEXT_CHAT_PROMPT.md` precedent, mkdocs nav entries, CHANGELOG wording,
or knowledge-lifecycle row text. Remaining items are design-log-level
bookkeeping. Proceed.

## 2. What ships in Phase 15b (final scope)

**Design-only phase. No production Python code. No version bump. No
image rebuild. No `phase-15b-confirmed` tag. No `release.yml` run.**

### ADRs (parent project tree per Model C)

* **`/Layered Intelligence/docs/decisions/adr/0134-schema-migration-scanner.md`**
  — §amendment-3 added (subsections 3a documentary + 3b §closing
  relaxation); Status frontmatter flips `Proposed → Accepted`; Date
  frontmatter updates to 2026-05-20.
* **`/Layered Intelligence/docs/decisions/adr/0150-l2-knowledge-lifecycle.md`**
  — §amendment-2 added (supporting-evidence correction; architectural
  decision unchanged).

### Docs (in halvim_mindsos repo)

* **`docs/dev/migration-playbook.md`** NEW — full content per PB-21
  (C2 depth):
  * §API surface (signature, ViolationKind taxonomy, DetailMode
    semantics, `old_schema_name` policy).
  * §Usage example — Phase 11's `test_migrate_from_metagraph.py`
    paraphrased: synthetic schema diff → call `migrate_from(old, mg)`
    → inspect `list[SchemaViolation]`.
  * §Migration recipes — labelled "pending first real-migration
    consumer"; one-line placeholder describes the gap.
  * front-matter `last_confirmed_phase: 15b`.
* **`docs/concepts/admin-global-shipping.md`** — Alignments row moves
  from "Phase 15b (planned)" to "Phase X TBD per PHASE_MAP §28
  review"; `last_confirmed_phase: 15a → 15b`.
* **`docs/concepts/knowledge-lifecycle.md`** — Alignments row moves
  similarly; `last_confirmed_phase: 15a → 15b`.
* **`mkdocs.yml`** — adds `Developer documentation → Migration
  playbook` nav entry.
* **`docs/changelog/CHANGELOG.md`** — Phase 15b entry (minimal;
  documents ADR-0134 flip + ADR-0150 §amendment-2 + playbook landing +
  alignment carry-forward closure target TBD).

### PHASE_MAP edits

* **§Phase 15b row** rewrites to design-only scope:
  * Status: Shipped 2026-05-20 (no tag per design-only exception).
  * Layer: design (no code-layer per PHASE_MAP §1).
  * Net-new? No.
  * Features: ADR-0134 §amendment-3 (3a + 3b) + flip Accepted;
    ADR-0150 §amendment-2; `docs/dev/migration-playbook.md`;
    knowledge-lifecycle + admin-global-shipping doc updates.
  * Tests: `tests/phase_15b/test_adr_amendment_sentinels.py` only
    (skip-in-container per Model C).
  * Carry-forward CLOSURES: ADR-0134 §amendment-3 (was open since
    Phase 13); `docs/dev/migration-playbook.md` content (was open
    since Phase 13).
  * Carry-forward OPENED (re-deferred): AlignmentsImporter; per-edge
    alignment-anchor IRI builder; real FN-WN data extraction;
    importer idempotency tightening. ALL: closure phase TBD per Phase
    28 review.
  * Carry-forward UNCHANGED: scan-schema CLI verb (still Phase 26 per
    Phase 15a PB-3 + Phase 14a round-3 lock on CLI state-file access).
  * In-flight pushbacks: PB-1..23 across 6 rounds, all user-agreed.
    See `confirmation_docs/PHASE_15b_DESIGN_LOG.md` §1.

* **§Phase 28 row** gains the alignment-lookup review note per PB-23.

* **§Phase 26 row** unchanged (scan-schema CLI carry-forward already
  noted from Phase 15a).

### Tests (sentinel-only per PB-22)

* **`tests/phase_15b/test_adr_amendment_sentinels.py`** — file
  existence + substring presence checks for:
  * ADR-0134 §amendment-3 sentinel: "amendment-3 (Phase 15b ship — 2026-05-20)".
  * ADR-0134 Status frontmatter: `status: Accepted`.
  * ADR-0150 §amendment-2 sentinel: "amendment-2 (Phase 15b ship — 2026-05-20)".
  * Skip-in-container per Model C (parent-tree path inaccessible from
    Docker test stage).

### Phase 16 handoff

* **`confirmation_docs/PHASE_16_NEXT_CHAT_PROMPT.md`** NEW — briefs
  Phase 16 (promotion machinery at `mindsos_admin/promotion.py` per
  ADR-0140 §amendment-1). Deps: 14, 15a (NOT 15b — 15b is design-only
  with no code dependency on Phase 16). Cites Phase 15b's ADR
  amendments + alignment carry-forward TBD-per-Phase-28-review.
  Branch-off point: 15b's squash-merge SHA per Phase 14a precedent
  (downstream code phases branch off main-tip after the design PR
  squash-merges, not off a tag).

### Explicitly NOT in Phase 15b scope

* AlignmentsImporter (`mindsos_admin/importers/alignments.py`).
* Per-edge alignment-anchor IRI builder.
* Real FN-WN data extraction script.
* `mindsos admin scan-schema` CLI verb (Phase 26).
* Importer idempotency tightening.
* `mindsos_core/schema/migration.py` net-new code (already shipped
  at Phase 11).
* `mindsos_core/exceptions.py` additions (already shipped at Phase 11).
* Phase 16's promotion machinery (Phase 16 owns).

## 3. ADR amendments (Phase 15b authors)

### ADR-0134 §amendment-3 (Phase 15b ship — 2026-05-20)

File: `/Layered Intelligence/docs/decisions/adr/0134-schema-migration-scanner.md`
(parent project tree per Model C).

**Status frontmatter:** `Proposed → Accepted` (per §3b below).
**Date frontmatter:** `2026-04-27 → 2026-05-20`.

#### amendment-3, §3a — documentary alignment with Phase 11's shipped API

**Trigger:** ADR-0134 §1 (`Decision.1. Schema.migrate_from(...)`)
specified `migrate_from(self, old_schema, *, on_violation="report") ->
list[SchemaViolation]` with four `ViolationKind` values (`removed_node_type`,
`removed_edge_type`, `tightened_property`, `missing_required_property`).
Phase 11 (PB-1 / PB-7 / PB-8 / PB-17 per `confirmation_docs/PHASE_11_DESIGN_LOG.md`)
shipped a richer surface that ADR-0134 never reflected. This
sub-amendment documents the actual signature + extensions.

**Amended behavior:**

1. **Signature:** the shipped function lives at module level (not
   `Schema` method) in `mindsos_core/schema/migration.py`:
   ```python
   def migrate_from(
       old: Schema,
       target: Graph | Metagraph,
       *,
       new: Schema | None = None,
       detail: Literal["summary", "each"] = "summary",
       old_schema_name: str | None = None,
   ) -> list[SchemaViolation]: ...
   ```
   * `target` is `Graph | Metagraph`; single entry point dispatches on
     `isinstance` (Phase 11 PB-17 C — "both per-Graph and
     per-Metagraph dispatch through one entry point").
   * `new` defaults to `target.schema` (per-Graph) or each contained
     `graph.schema` (per-Metagraph). Skips graphs whose schema is
     `None`.
   * `on_violation` from ADR-0134 §1 is dropped in favor of `detail`
     (Phase 11 PB-8 A); raise-on-violation is achievable via caller
     post-check of the returned list.
   * Returns `list[SchemaViolation]` (empty list when schemas are
     compatible).

2. **`ViolationKind` extended to five values** (Phase 11 PB-7 C):
   ```python
   ViolationKind = Literal[
       "removed_node_type",
       "removed_edge_type",
       "removed_hyperedge_type",  # ← added at Phase 11
       "tightened_property",
       "missing_required_property",
   ]
   ```
   `removed_hyperedge_type` covers HyperEdge family per Schema's
   tripartite structure (Node / Edge / HyperEdge). ADR-0134 §1's
   four-kind list is superseded.

3. **`DetailMode` adds aggregation surface** (Phase 11 PB-8 A):
   ```python
   DetailMode = Literal["summary", "each"]
   ```
   * `summary` (default): one `SchemaViolation` per `(kind, type_name,
     graph_id, property_name)` quadruple with `count` aggregating.
     `element_id` is empty string.
   * `each`: one `SchemaViolation` per offending element. `element_id`
     carries the node / edge / hyperedge id. `count` is always 1.
   * Rationale: pathological inputs (10k violations of one kind)
     produce 1 summary entry vs 10k each entries.

4. **`SchemaViolation` dataclass extended** (Phase 11 PB-7 deferred
   items + PB-8 + PB-17):
   ```python
   @dataclass(frozen=True)
   class SchemaViolation:
       kind: ViolationKind
       type_name: str
       element_id: str    # "" in summary mode
       graph_id: str      # always set
       property_name: str # "" for removed_*_type kinds
       count: int         # aggregate in summary; 1 in each
       detail: str        # human-readable one-liner
   ```
   * `frozen=True` — value object.
   * `graph_id` is always populated (per-Metagraph scans surface which
     graph carried each violation).

5. **`old_schema_name` policy warning** (Phase 11 PB-17 C):
   ```python
   migrate_from(old, mg, *, old_schema_name="ontology-v1")
   ```
   When set AND target is a Metagraph, the scanner emits a logger
   WARNING for each contained graph whose `schema_name` differs from
   `old_schema_name`; that graph is skipped (not a SchemaViolation —
   caller decides whether the mismatch is meaningful).

6. **`SchemaMigrationError`** is raised for invalid `target` type or
   invalid `detail` value. Inherits from `CoreError`. Lives in
   `mindsos_core/schema/migration.py` (NOT `mindsos_core/exceptions.py`
   as ADR-0134 §"Coordinated changes" originally listed). The
   `UnknownEdgeTypeError` from §amendment-2 (loader surface) does live
   in `mindsos_core/exceptions.py:415`.

7. **Implementation references updated:** `mindsos_core/schema/migration.py`
   is the module home. `tests/phase_11/test_migrate_from_unit.py` +
   `test_migrate_from_metagraph.py` are the test surface.
   `docs/dev/migration-playbook.md` (Phase 15b) documents the API.

#### amendment-3, §3b — §closing criterion relaxation + Status flip

**Trigger:** ADR-0134 §closing originally read: "ADR moves from
Proposed to Accepted when scanner + loader warning land, **KL importers
use scanner output for at least one role-graph schema bump**, and
`docs/dev/migration-playbook.md` documents the pattern." Phase 15a's
ADR-0140 §amendment-1 (admin-package permanent home) + Phase 15b's
P5 reframe (AlignmentsImporter deferred sine die) mean the middle
clause's consumer model never materialises. Scanner's actual consumers
are admin-CLI scans (Phase 26+) and release-gate audits (Phase 24+ per
ADR-0144), not import-time schema migration.

**Amended §closing criterion:**

ADR moves from Proposed to Accepted when:
1. Scanner module ships (`mindsos_core/schema/migration.py`).
   ✓ Phase 11.
2. Loader warning surface ships (per amendments 1 + 2). ✓ Phase 11.
3. `docs/dev/migration-playbook.md` documents the API + at least one
   usage example. ✓ Phase 15b (per PB-21 / C2 depth).
4. ~~KL importers use scanner output for at least one role-graph
   schema bump.~~ **Dropped.** The original criterion presupposed a
   consumer model (import-time migration) that ADR-0140 §amendment-1
   relocated; actual consumers are admin-CLI scans and release-gate
   audits, which materialise at Phase 26 + Phase 24+ respectively.
   Item 5 (test coverage demonstrating contract) replaces it.
5. Phase 11 test surface
   (`tests/phase_11/test_migrate_from_{unit,metagraph}.py` +
   `tests/phase_11/test_loader_policy_{unit,integration}.py`)
   demonstrates the API contract end-to-end. ✓ Phase 11.

All five criteria satisfied as of Phase 15b ship. Status flips
`Proposed → Accepted` at this amendment.

**Out-of-scope for amendment-3:**

* The `Schema.migrate_from` method form (vs the shipped module-level
  function) is not re-introduced — Phase 11's module-level form is
  load-bearing; rewriting to method form would break Phase 11's tests
  + downstream consumers.
* New ViolationKind values beyond the five — defer to whichever later
  phase first needs them.
* The `on_violation="raise"` mode from ADR-0134 §1 — Phase 11 picked
  `detail`-based aggregation instead; callers wanting raise-on-first
  can post-check the returned list.

See `confirmation_docs/PHASE_15b_DESIGN_LOG.md` §1 Round 3.5 + Round 4
PB-13 / PB-14 / PB-16 for the multi-round rationale chain.

### ADR-0150 §amendment-2 (Phase 15b ship — 2026-05-20)

File: `/Layered Intelligence/docs/decisions/adr/0150-l2-knowledge-lifecycle.md`
(parent project tree per Model C).

**Trigger:** §amendment-1 (Phase 14) contains the load-bearing sentence
"Phase 15's importers (DOLCE↔OEWN, OEWN↔FrameNet, etc.) all write
Global alignments — administered content, not user-authored." That
sentence is now factually wrong as of Phase 15a ship + Phase 15b
reframe: Phase 15a shipped 3 source importers (DOLCE / OEWN /
FrameNet — none of which write alignments); Phase 15b ships no
importers; AlignmentsImporter is deferred to a closure phase TBD per
Phase 28 design review. The §amendment-1 sentence misrepresents what
exists vs what's planned.

**Amended behavior:**

§amendment-1's supporting-evidence sentence is corrected as follows:

> ~~Phase 15's importers (DOLCE↔OEWN, OEWN↔FrameNet, etc.) all write
> Global alignments — administered content, not user-authored.~~
>
> **Corrected at amendment-2 (Phase 15b ship, 2026-05-20):** Phase
> 15a ships 3 source importers (DolceImporter / OewnImporter /
> FrameNetImporter) that populate ontology / lexicon / concepts role-graphs
> respectively — none of which write alignments. AlignmentsImporter
> is deferred to a closure phase TBD per Phase 28 design review (see
> PHASE_MAP §28 row "Review at design pass: does alignment-lookup
> land as one of the 12 categories?"). Alignment writes, when they
> materialise, will be administered content per ADR-0145's exclusion
> of alignment-authoring from L3 write-capacity categories.

**Architectural decision unchanged:**

* Alignment role (`alignment:<a>:<b>`) remains **Global-only at v1**
  per §amendment-1's primary lock. `ensure_global_role_graph` accepts
  alignment prefixes; `ensure_local_role_graph` rejects them with
  `KnowledgeError`. The lock is the architectural decision; the
  supporting sentence about Phase 15's importer flow was scheduling
  evidence that decayed.
* Closed role-set per §Decision unchanged (9 entries; expansion
  requires §Revisions entry per §Decision §"Expansion requires an
  ADR amendment").
* ADR-0044 memories Local-per-user binding unchanged.

**Rationale:**

ADR scheduling lives in PHASE_MAP, not in ADR text — house style. The
§amendment-1 sentence was supporting evidence (illustrating WHEN the
architectural lock matters), not part of the lock itself. As scheduling
shifts, ADR text needs minimal corrective edits to avoid known-wrong
statements; the underlying architectural decisions don't move.

**Out-of-scope for amendment-2:**

* Re-opening the closed role-set §Decision. Closure stands.
* Re-opening alignment-Global-only §amendment-1 primary lock. Lock
  stands.
* Locking the alignment closure phase number at the ADR level (PB-19
  A2 lock). PHASE_MAP §15b row + §28 review note carry that.

See `confirmation_docs/PHASE_15b_DESIGN_LOG.md` §1 Round 5 PB-19 for
the rationale chain.

## 4. Doc cascade (Phase 15b authors)

### NEW

* **`halvim_mindsos/docs/dev/migration-playbook.md`** — per PB-21 (C2
  depth). API surface + Phase 11-test-derived example + recipes-pending
  placeholder. `last_confirmed_phase: 15b` front-matter.

### Amend

* **`halvim_mindsos/docs/concepts/admin-global-shipping.md`** —
  Alignments row text amends from "Phase 15b (planned)" to "Phase X
  TBD per PHASE_MAP §28 review". `last_confirmed_phase: 15a → 15b`.

* **`halvim_mindsos/docs/concepts/knowledge-lifecycle.md`** —
  Alignments row amends similarly; matches admin-global-shipping
  wording. `last_confirmed_phase: 15a → 15b`.

* **`halvim_mindsos/mkdocs.yml`** — adds `Developer documentation →
  Migration playbook` nav entry under existing Dev group.

* **`halvim_mindsos/docs/changelog/CHANGELOG.md`** — Phase 15b entry
  (minimal; see template in §6 below).

* **`halvim_mindsos/confirmation_docs/PHASE_MAP.md`** — §15b row
  rewrite (per §2 above); §28 row review note (per PB-23); §26 row
  unchanged; no Phase 32b insertion.

## 5. Test sentinel surface

* **`halvim_mindsos/tests/phase_15b/test_adr_amendment_sentinels.py`** —
  file existence + substring presence checks (skip-in-container per
  Model C — parent-tree ADR path inaccessible from Docker test stage;
  `pytest.importorskip` or path-existence-based skip):

  ```python
  ADR_0134_PATH = Path("/Layered Intelligence/docs/decisions/adr/0134-schema-migration-scanner.md")
  ADR_0150_PATH = Path("/Layered Intelligence/docs/decisions/adr/0150-l2-knowledge-lifecycle.md")

  def test_adr_0134_amendment_3_sentinel():
      if not ADR_0134_PATH.exists():
          pytest.skip("Model C: parent-tree ADR path; sentinel runs on Mac only")
      text = ADR_0134_PATH.read_text()
      assert "amendment-3 (Phase 15b ship — 2026-05-20)" in text
      assert "status: Accepted" in text  # Status flip

  def test_adr_0150_amendment_2_sentinel():
      if not ADR_0150_PATH.exists():
          pytest.skip("Model C: parent-tree ADR path; sentinel runs on Mac only")
      text = ADR_0150_PATH.read_text()
      assert "amendment-2 (Phase 15b ship — 2026-05-20)" in text
  ```

  Matches Phase 14a + 15a sentinel patterns. NO production-code tests
  ship in this phase.

* **No `tests/phase_15b/__init__.py`** unless test-discovery requires
  it; mirror Phase 14a's convention.

## 6. CHANGELOG entry template

```markdown
## Phase 15b — 2026-05-20 (design-only)

* **ADR-0134** Schema migration scanner — Status `Proposed → Accepted`.
  §amendment-3 documents Phase 11's shipped API surface (signature,
  five ViolationKind values including `removed_hyperedge_type`,
  `summary` / `each` detail modes, `old_schema_name` policy warning)
  and relaxes §closing criterion to match actual consumer model
  (admin-CLI scans + release-gate audits, not import-time migration).
* **ADR-0150** L2 role-set closure — §amendment-2 corrects
  §amendment-1's stale supporting evidence about Phase 15's importer
  flow; architectural decision (alignment Global-only at v1) unchanged.
* **`docs/dev/migration-playbook.md`** — new dev doc; API surface +
  Phase 11-test-derived usage example + migration-recipes placeholder
  pending first real-migration consumer.
* **PHASE_MAP §15b row** rewrites to design-only scope; §28 row gains
  alignment-lookup capacity review note; no Phase 32b insertion.
* **AlignmentsImporter + per-edge alignment-anchor IRI builder + real
  FN-WN data extraction + importer idempotency tightening** —
  carry-forward closure target deferred to whichever phase opens the
  alignment-lookup capacity question (TBD per Phase 28 review).
* **scan-schema CLI verb** — carry-forward unchanged from Phase 15a;
  closure at Phase 26 alongside CLI state-file access work.
* No version bump (5 packages stay at `+phase15a`).
* No image rebuild (Docker tags stay at `mindsos:phase15a-{prod,test}`).
* No `phase-15b-confirmed` tag (design-only exception per PHASE_MAP §1).
* No `release.yml` invocation.
```

## 7. Forward-cited ADRs in this design log

* **ADR-0010 (Accepted)** — layer isolation; ADR-0134's
  `mindsos_core/schema/migration.py` honors L1 isolation.
* **ADR-0017 (Accepted)** — schema strictness opt-in; scanner respects
  schema strictness via `_value_matches_type` (Phase 11 implementation).
* **ADR-0042 (Accepted)** + Phase 14 §amendment-1 + Phase 15a
  §amendment-2 — first-install sequences; unchanged at 15b.
* **ADR-0043 (Accepted)** — KL in-memory only; unchanged at 15b.
* **ADR-0044 (Accepted)** — memories Local-per-user; unchanged.
* **ADR-0045 (Accepted)** — per-role IRI builders; per-edge
  alignment-anchor IRI builder remains carry-forward.
* **ADR-0047 (Accepted)** — REF_TYPES open vocabulary; alignment
  ref_type extension deferred with AlignmentsImporter.
* **ADR-0128 (Accepted)** — hybrid XRef; AlignmentsImporter (when it
  ships) writes XRefs per PB-1 lock.
* **ADR-0134** — Status flips `Proposed → Accepted` AT THIS PHASE per
  §amendment-3 §3b.
* **ADR-0138 (Proposed)** — KL drops write API; honored by absence.
* **ADR-0139 (Proposed)** — hybrid invariant home; validators stay
  Phase 36.
* **ADR-0140 (Proposed)** + Phase 15a §amendment-1 — admin permanent
  home; unchanged at 15b.
* **ADR-0144 (Proposed)** — release-ship audit gate; scanner's actual
  consumer category per §amendment-3 §3b §closing item 4 replacement
  ("admin-CLI scans + release-gate audits").
* **ADR-0145 / 0146 / 0147 (Proposed)** — L3 write capacities;
  alignment-authoring not in user-Local writeable category (preserved
  by ADR-0150 §amendment-2's restatement).
* **ADR-0150 (Accepted)** + Phase 14 §amendment-1 + Phase 15b
  §amendment-2 (NEW) — closed role-set + alignment Global-only +
  supporting-evidence correction.

## 8. Carry-forward closures + re-openings

### CLOSED at Phase 15b

* **ADR-0134 §amendment-3** — was open since Phase 13 (deferred to
  Phase 14 → 15a → 15b). Lands at 15b per §3 above.
* **ADR-0134 Status flip `Proposed → Accepted`** — was open since
  Phase 11. Flips at 15b per §amendment-3 §3b.
* **`docs/dev/migration-playbook.md` content** — was open since
  Phase 13. Lands at 15b per PB-21 (C2 depth).
* **ADR-0150 §amendment-1 stale-evidence correction** — surfaced at
  Phase 15a but not flagged for closure; closes at 15b per
  §amendment-2.

### RE-OPENED at Phase 15b (closure phase TBD per Phase 28 review)

* **AlignmentsImporter** (`mindsos_admin/importers/alignments.py`).
  Spec carried with PB-1 (XRef-based) + PB-9 (`target_roles=()`,
  `pairs` attribute) + PB-11 (per-pair ref_type vocabulary) + PB-8
  (CSV format via extraction script). Closure phase: per Phase 28
  design review.
* **Per-edge alignment-anchor IRI builder** — 4th-hop carry from
  Phase 12/13/14/15a. Closure phase: per Phase 28 design review.
* **Real FN-WN data extraction** — `scripts/extract_fn_wn_alignments.py`
  re-deferred per PB-4 (FN-WN sense-level extraction non-trivial;
  YAGNI without read consumer). Closure phase: alongside
  AlignmentsImporter.
* **Importer idempotency tightening** (Phase 15a B-15a-T3 follow-up).
  Closure phase: whichever phase first does mid-process re-import.

### UNCHANGED carry-forward (from prior phases)

* **`mindsos admin scan-schema` CLI verb** — Phase 26 alongside CLI
  state-file access (Phase 14a round-3 lock).

## 9. Process discipline reminders (design-only specifics)

* **Branch:** `git fetch origin && git checkout -b phase-15b origin/main`.
  Branch off `origin/main` after Phase 15a's squash-merge (verify per
  Process P1 below). 15b's branch contains: 15b design log + ADR
  amendments (parent tree) + docs + PHASE_MAP edits + 1 test file +
  CHANGELOG + Phase 16 next-chat-prompt.
* **Sandbox vs Mac git** — file edits in sandbox via Write/Edit; git
  ops (`add` / `commit` / `push`) run on Mac per
  `feedback_sandbox_vs_mac_git_separation.md`.
* **Process P1 — verify Phase 15a state BEFORE branching:** on Mac,
  `cd halvim_mindsos && git fetch origin && git log --oneline
  origin/main | head -3` should show the Phase 15a squash-merge SHA
  at tip; `git tag -l | grep phase-15a` should show
  `phase-15a-confirmed`. Sandbox cannot verify (no SSH); Mac is
  authoritative.
* **No `notes-phase-15b.md`** — design-only phases skip the
  confirm-phase artifact per Phase 14a precedent.
* **No `confirm-phase` invocation** — design-only exception per
  PHASE_MAP §1.
* **No pre-build of test image** — no Dockerfile changes; test image
  unchanged from Phase 15a.
* **Cumulative literal audit SKIPPED** — no version-string bumps; no
  `phase15a → phase15b` literal rewrites needed.
* **State-file version audit SKIPPED** — no schema bumps.
* **Tag AFTER squash-merge SKIPPED** — no tag per design-only
  exception. Phase 16's branch-off SHA is 15b's squash-merge SHA on
  `main` (per Phase 14a precedent: "downstream code phases branch off
  main-tip after the design PR squash-merges, not off a tag").
* **`release.yml` NOT invoked** — workflow trigger is tag-push;
  no tag = no workflow.
* **PR review IS the confirmation** per PHASE_MAP §1: "PR review is
  the confirmation; release.yml is not invoked."

### Known weakness (per Process D1)

* ADR amendments live in `/Layered Intelligence/docs/decisions/adr/`
  which is a non-git parent tree (Model C per Phase 14a). The
  sentinel chain (`tests/phase_15b/test_adr_amendment_sentinels.py`)
  is the only mechanical guard against silent edit/removal. If a
  future phase encounters a vanished amendment, escalate to Model C
  review (one option: mirror ADRs into halvim_mindsos under
  `docs/decisions/adr-mirror/`; another: initialise git on parent
  tree). Phase 15b explicitly DOES NOT reopen this trade.

---

**Sign-off:** Plan locked across 6 rounds; 23 design pushbacks all
user-agreed. No open questions remain on scope (design-only),
ADR amendment content, doc cascade, test sentinel surface, or
carry-forward closure targets (TBD per Phase 28 review). Implementation
may proceed against `phase-15b` branch — pending Mac-side verification
of Phase 15a's squash-merge state per Process P1.
