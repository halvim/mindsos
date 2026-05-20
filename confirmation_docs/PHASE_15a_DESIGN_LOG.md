# Phase 15a — Design Log

> Captured 2026-05-19. Records 23 design pushbacks across 5 pre-impl
> rounds + the scope-split decision from the Phase-15-monolith handoff
> + the carry-forward to Phase 15b. Future amendments to ADRs 0042 /
> 0140 should consult this file for rationale.

## 0. Scope at chat-open

PHASE_MAP §Phase 15 row (handoff version, written by Phase 14):

* 4 importer modules in `mindsos_knowledge/importers/` — DOLCE, OEWN,
  FrameNet, Alignments.
* Per-edge alignment-anchor IRI builder in `mindsos_knowledge/
  identifiers.py` (Phase 12 PB-4 / Phase 13 PB-5 / Phase 14 PB-1 carry
  — 3rd hop).
* MetagraphSchema scanner consumer (Phase 11/12/13/14 carry — 4th hop).
* ADR-0134 Proposed → Accepted flip.
* `docs/dev/migration-playbook.md` full content.
* ADR-0134 §amendment-3.
* `mindsos knowledge import {dolce,oewn,framenet,alignments}` CLI
  verbs.
* `docs/knowledge-sources/*.md` per-importer reference pages.
* Phase 15 lifecycle-table row Status `planned → shipped`.

Deps: 13, 14. Layer: L2. Net-new? "No (locations may move in Phase 37
but stay in L2 for this phase)" per handoff. **Re-classified by PB-1**
across 5 rounds to: net-new top-level package `mindsos_admin/` (PB-1);
NO ADR-0134 flip (PB-2); NO per-edge alignment-anchor IRI builder
(PB-3); scope SPLIT into Phase 15a + Phase 15b (PB-4); 4 importers
become 3 (DOLCE / OEWN / FrameNet); permanent admin home (PB-17);
ADR-0140 §Decision §1+§2 superseded (PB-18); Phase 37 row retired
(PB-17 consequence).

## 1. Design pushbacks (PB-1..23) — five rounds, all user-agreed

### Round 1 — architecture locks (PB-1..6)

#### PB-1 — Importers ship in NEW top-level `mindsos_admin/` package

ADR-0043 (**Accepted**, 2026-04-22): "`mindsos_knowledge/` has zero
imports of any FalkorDB client, any persistence module, or any
**file-I/O primitive**." Handoff puts importers at `mindsos_knowledge/
importers/`. DOLCE/OEWN/FrameNet importers MUST read OWL/XML/JSON
from disk — literal violation of ADR-0043 (Accepted) by code shipped
under an L2-themed phase.

Three considered: (A1) split parser-pure-in-KL / I/O-wrapper-in-scripts;
(A2) amend ADR-0043 with importer-exemption; (A3) create
`mindsos_admin/` as a new top-level package (ADR-0140 §Alternatives #3,
"Held; reopen if `mindsos_server` itself becomes too large").

**Lock: A3.** Reopens ADR-0140 §Alternatives #3 on different grounds
(ADR-0043 invariant precedence, not server-size). New top-level
package = full 7-site checklist (§5 below). ADR-0043 untouched. End-
state per PB-17 (Round 4): permanent admin home, not interim.

#### PB-2 — Do NOT flip ADR-0134 Proposed → Accepted

ADR-0134 §closing: "moves to Accepted when scanner + loader warning
land, **KL importers use scanner output for at least one role-graph
schema bump**." Phase 15 imports against the **same** Phase 13
schemas — no bump. Fresh import ≠ migration. The handoff's "Phase 15
drives the flip" claim isn't supported by ADR-0134's own §closing.

Three considered: (B1) don't flip; (B2) flip on weaker grounds
("integrated" counts as adoption); (B3) amend §closing to relax the
bar.

**Lock: B1.** Premature-Accepted ADRs are how `Proposed` rot starts.
Carry forward to whichever phase first does a real role-graph schema
bump (likely DOLCE v2 re-import in some later admin phase).

#### PB-3 — Defer per-edge alignment-anchor IRI builder (4th hop)

Phase 12 PB-4 / Phase 13 PB-5 / Phase 14 PB-1 (3 hops) deferred the
per-edge alignment-anchor IRI builder for lack of a concrete
consumer. Handoff says "lock the IRI form here." But the read
consumer is L3's alignment-lookup capacity (Phase 33-35), 18 phases
away. Locking shape without the consumer's read pattern is exactly
what the prior 3 hops deferred for a reason.

Three considered: (C1) defer again (4th hop); (C2) ternary
`alignment:<a>:<b>:<anchor-id>`; (C3) entity-IRI-reuse
`<source-iri>--<target-iri>`.

**Lock: C1.** Phase 15b's Alignments importer (when sourced) writes
alignment edges via L1 primitives with whatever ID L1 mints; no
anchor IRI introduced. Phase 33-35 introduces the anchor when its
first read consumer materialises.

#### PB-4 — Split Phase 15 → Phase 15a + Phase 15b

Phase 11 was 1 concern (snapshot/soft-delete). Phase 12 was 1 (IRIs).
Phase 13 was 1 (schemas). Phase 14 was 1 (KL class). Handoff's
Phase 15 has 4 modules + 4 fixture datasets + 4 CLI verbs + scanner
wiring + IRI builder + ADR-0134 flip + migration-playbook content +
2 lifecycle doc edits. 5× the prior per-phase load.

Two considered: (D1) split 15a (DOLCE/OEWN/FrameNet — independent
parsers) + 15b (Alignments + scanner); (D2) ship as one phase.

**Lock: D1.** The 3 source-importers are independent (DOLCE doesn't
depend on OEWN; FrameNet has its own parser). Alignments structurally
depends on having all 3 source roles populated. Natural cleave line.
Mirrors Phase 05a/05b/05c/05d precedent. Each gets `phase-15{a,b}-
confirmed` tag + `+phase15{a,b}` version bump + separate retention
slot.

#### PB-5 — Scanner is admin CLI verb only, not write-hook

Three considered: (F1) admin CLI verb only — `mindsos admin scan-
schema [--role X]`; (F2) per-importer post-write scan (each importer
calls scanner before returning); (F3) batched post-all-importers scan.

**Lock: F1.** ADR-0134 §Consequences explicitly says "admin-runnable
tool; not run on every load." That's a CLI verb, not a write hook.
Scanner CLI ships in Phase 15b alongside the L1 module per PB-9
below.

#### PB-6 — Pin dataset versions explicitly

Handoff: "importer dataset versions must be pinned per phase" — no
version named anywhere. v3 design doc §4 (`_source_backup/root/
mindsos_knowledge_architecture.md`) yields DOLCE-DUL 4.0/4.1, OEWN
2024; FrameNet unversioned in §4. v3 §8.4 doesn't exist (handoff
cite was partly wrong).

Two considered: (E1) v3's picks verbatim; (E2) pick current-LTS
choices and document each.

**Lock: E2 with concrete pins.**

| Source   | Version       | License        | Repo-shippable? |
|----------|---------------|----------------|-----------------|
| DOLCE    | DOLCE-DUL 4.1 | Creative Commons | yes (~1 MB OWL) |
| OEWN     | 2024          | CC-BY-SA 4.0   | yes (~30 MB XML) |
| FrameNet | 1.7           | Berkeley click-through | **NO** — synthetic fixture only; downloader script |

License blocks repo-checked-in FrameNet fixtures; see PB-15 for
fixture stance.

### Round 2 — cascade (PB-7..12)

#### PB-7 — Importers BUILD a Metagraph; hand to KL constructor

Importers need write access to L1 graphs inside KL's Global metagraph.
Phase 14 PB-3 made `MetagraphView` whitelist-read-only; PB-16 said
"convention not to mutate via the view." ADR-0138 leaves KL with no
write API. So how does a `mindsos_admin/` importer reach into KL-
owned Global?

Three considered: (1a) importers build a fresh `Metagraph`, call
`ensure_global_role_graph(mg, role)` themselves, write via L1
directly, then caller hands populated `mg` to `KnowledgeLayer(
global_metagraph=mg)`; (1b) add `kl._global_metagraph_for_admin_
write()` back-door; (1c) importers go through
`MetagraphView.graphs_by_role(role)[0].add_node(...)`, violating
PB-16's social contract.

**Lock: PB-1a.** Construct-then-hand-to-KL. Importer never touches
KL. Aligns with ADR-0042 §amendment-1 (Global is constructor-
supplied). Same pattern works for fresh-install and re-import. Re-
import after KL is live = "build offline, swap on next process boot"
— matches admin/release-cadence mental model. ADR-0042 §amendment-1
§Out-of-scope already says "no Global-swap method; no consumer."

#### PB-8 — ADR-0140 §amendment-1 covers admin-package decision

PB-1 (A3) re-promoted ADR-0140 §Alternatives #3 (`mindsos_admin/`).
ADR-0140 §Decision (Proposed) still says importers relocate to
`mindsos_server/importers/`. End-state inconsistency.

Three considered: (2a) amend ADR-0140 §amendment-1 ("§Decision §1
amended — importers' permanent home is `mindsos_admin/importers/`"); 
(2b) narrow amendment importers-only; (2c) supersede with new
ADR-0151.

**Lock: PB-2a** (Round 2) — **scope expanded by PB-18** (Round 4) to
full §Decision §1+§2 supersession (not just additive amendment).
ADR-0140 stays Proposed; the amendment lands at Phase 15a's PR.

#### PB-9 — Scanner ships in Phase 15b alongside CLI verb (layer-mixing acknowledged)

ADR-0134 §Implementation references: `mindsos_core/schema/migration.py`
(L1 code). PB-5 puts the CLI verb in `mindsos_cli/`. Both belong to
non-L2 layers. Phase 15a/15b rows are L2. Layer-mixing question.

Three considered: (3a) ship `mindsos_core/schema/migration.py` in
Phase 15b alongside the CLI verb; mark §15b row as "Layer:
L1+L2+CLI"; (3b) defer scanner module entirely; (3c) carve Phase 11b
mini-phase for the L1 module.

**Lock: PB-3a.** Layer-mixing per row is a small honesty cost. Sub-
phasing for one module is overkill. Phase 15b's PHASE_MAP row
explicitly notes "Layer: L1+L2+CLI."

#### PB-10 — `mindsos admin import {...}` CLI namespace

Handoff: `mindsos knowledge import {...}`. With importers in
`mindsos_admin/`, the CLI namespace lies about who owns the code.

Three considered: (4a) `mindsos admin import {...}` matches package
home; (4b) keep `mindsos knowledge import {...}` for discoverability;
(4c) `mindsos import {...}` at top level.

**Lock: PB-4a.** Admin-grouped verbs scale (future admin verbs:
promotion, release-ship). Package-name parity matters for honesty.

#### PB-11 — Documentation cascade in Phase 15a

PB-1 invalidates parts of `admin-global-shipping.md` ("Phase 15
(interim) — Importers live at `mindsos_knowledge/importers/`. Phase
37 relocates to `mindsos_server/importers/`") and `knowledge-
lifecycle.md` Phase 37 row.

Two considered: (5a) Phase 15a rewrites both pages; (5b) leave docs
claiming `mindsos_knowledge/importers/`.

**Lock: PB-5a.** Doc rot is the slowest, costliest debt class.

#### PB-12 — Concrete dataset pins surface in design log + per-source docs

See PB-6 table. Decision recorded in `docs/knowledge-sources/{dolce,
oewn,framenet}.md` with: pin + license + import command + expected
stats.

### Round 3 — importer flow (PB-13..16)

#### PB-13 — `mindsos_admin.bootstrap_global(importers=[...])` helper

PB-7 (1a) makes the importer flow:
```python
mg = Metagraph(name="global_knowledge")
ensure_global_role_graph(mg, "ontology")
DolceImporter().run(mg, dataset_path)
# ... repeat for OEWN, FrameNet
kl = KnowledgeLayer(global_metagraph=mg)
```
Bootstrap() is now only for empty-install; importer path uses manual
ensure-loop. Two flows. Where does orchestration live?

Three considered: (1a-i) two documented flows; (1a-ii)
`KnowledgeLayer.bootstrap(importers=[...])` — KL grows admin
awareness, fighting ADR-0043; (1a-iii) module-level
`mindsos_admin.bootstrap_global(importers=[...]) -> Metagraph` helper.

**Lock: PB-1a-iii.** Orchestration belongs in admin. KL stays a data-
holding class.

#### PB-14 — Importers auto-ensure their target role-graph as step 1

Each importer's `run(mg, ...)` writes into an EXISTING role-graph.
What if caller invokes `DolceImporter().run(mg, ...)` directly without
the helper, and the `ontology` role-graph isn't there?

Two considered: (2-i) importer checks; raises `KnowledgeError` if
missing — clear fail-loud; (2-ii) importer auto-ensures internally
— zero pitfall.

**Lock: PB-2-ii.** Downward dependency on KL's `ensure_global_role_
graph` helper is correct architectural direction (admin → knowledge).
Each importer imports `ensure_global_role_graph` from
`mindsos_knowledge.bootstrap`. `bootstrap_global` (PB-13) also calls
ensure; the in-importer call is redundant-but-idempotent insurance.

#### PB-15 — Synthetic-shape fixtures in-repo + downloader for real datasets

PB-6 surfaced FrameNet 1.7 license blocks repo-checked-in fixtures.
Three stances for Phase 15a's test fixtures.

Three considered: (3-i) synthetic-shape fixtures (~10-100 nodes per
source) + downloader script in `scripts/fetch_datasets.{sh,py}`;
(3-ii) trimmed real-extract for DOLCE+OEWN + synthetic for FrameNet;
(3-iii) no fixtures; mock-parser-output dicts only.

**Lock: PB-3-i.** Synthetic-shape fixtures + downloader. Parsers ARE
tested in 15a (against format-accurate inputs); real-data integration
smoke is Phase 26's natural beat. FrameNet license stays untouched.

#### PB-16 — ADR-0042 §amendment-2 enumerates third first-install sequence

ADR-0042 §amendment-1 (Phase 14) names two sequences: (1) server
startup (warm restart), (2) first install (`KL.bootstrap()`).
PB-13's `mindsos_admin.bootstrap_global` adds a third: importer-built
Global → constructor.

Two considered: (4-i) ADR-0042 §amendment-2; (4-ii) no amendment;
constructor-parameter mechanism covers any source.

**Lock: PB-4-i.** Make the convention explicit. ADR amendments are
cheap; reverse-engineering install paths from code later is not.

### Round 4 — admin lifetime (PB-17..20)

#### PB-17 — `mindsos_admin/` is PERMANENT (not interim)

Three considered: (1-i) permanent — Phase 37 row killed; ADR-0140
§amendment-1 supersedes §Decision; (1-ii) interim — Phase 37 folds
into `mindsos_server/admin/`; (1-iii) hybrid — importers/scanner
permanent in admin; promotion/release move to server at Phase 37.

**Lock: PB-1-i (permanent).** Role-description (`CLAUDE.md`) is
explicit: server = runtime envelope; admin = operations. Importers,
promotion machinery, scanner — all admin operations. They share a
package. Server (whenever it ships) imports admin for HTTP endpoints.
Phase 37 retired or rewritten as "admin-package retrospective audit."

#### PB-18 — ADR-0140 §amendment-1 full supersession (not additive)

Three considered: (2-i) full supersession — §amendment-1 supersedes
§Decision §1+§2 (covers BOTH importer and promotion home); (2-ii)
narrow amendment — importers only; promotion question deferred to
Phase 16.

**Lock: PB-2-i.** Close all admin-location questions in one
amendment now. Amendment text below at §3.

#### PB-19 — Phase 16 promotion forward-cited as `mindsos_admin/promotion.py`

PB-17 + PB-18 mean Phase 16's `propose_for_promotion` ships in
`mindsos_admin/promotion.py` from day one (not `mindsos_knowledge/
promotion_v2.py` as ADR-0140 §Context implied).

Two considered: (3-i) Phase 15a design log explicitly forward-cites;
(3-ii) Phase 16 re-decides location.

**Lock: PB-3-i.** Lock the location now; Phase 16 just consumes.
Phase 15a's PR updates PHASE_MAP §Phase 16 row to cite admin home.

#### PB-20 — Conservative day-one package layout

Two considered: (4-i) conservative — only what Phase 15a ships
(structure grows organically); (4-ii) full-skeleton — pre-create
empty subpackages.

**Lock: PB-4-i.**

```
mindsos_admin/
  __init__.py
  bootstrap.py            # PB-13: bootstrap_global helper
  importers/
    __init__.py
    dolce.py              # PB-21: target_roles=("ontology",)
    oewn.py               # target_roles=("lexicon",)
    framenet.py           # target_roles=("concepts",)
```

Phase 15b adds: `mindsos_admin/importers/alignments.py` + scanner
CLI backend home (either `mindsos_admin/scan.py` or `mindsos_cli/
admin_commands.py` — 15b decision).

Phase 16 adds: `mindsos_admin/promotion.py`.

Empty packages with `__init__.py` only are ceremony noise; grow into
the layout.

### Round 5 — impl edge cases (PB-21..23)

#### PB-21 — `bootstrap_global` ensures ALL 6 Global named role-graphs

Phase 14's `KnowledgeLayer.bootstrap()` ensures all 6 Global named
role-graphs (`ontology`, `lexicon`, `concepts`, `promoted-pipelines`,
`task-patterns`, `problem-trace`). Phase 15a's importers populate
only 3. If `bootstrap_global` ensures only importer-target roles, KL
receives a 3-role Global; the other 3 stay missing (KL has no lazy-
auto-ensure for Global per ADR-0042 §amendment-1).

Three considered: (1-i) ensure all 6 (parity with `KL.bootstrap()`);
(1-ii) ensure only importer-targets (caller burden); (1-iii) two
helpers — `bootstrap_global_empty()` + `bootstrap_global_with_
importers([...])`.

**Lock: PB-1-i.** End-state parity is non-negotiable. Helper name
documented to mean "produce a complete Global, optionally populated
by importers."

#### PB-22 — Importer protocol: `target_roles` self-describe via class/instance attribute

Three considered: (2-i) `target_roles: tuple[str, ...]` class attribute
(instance attribute for parametric AlignmentsImporter); (2-ii) caller
supplies — `bootstrap_global([(DolceImporter, ["ontology"]), ...])`;
(2-iii) importer exposes `run(mg)` only; each importer auto-ensures
(PB-14 only, no helper pre-ensure).

**Lock: PB-2-i.**

```python
# Phase 15a importers
class DolceImporter:
    target_roles: tuple[str, ...] = ("ontology",)
    def run(self, mg: Metagraph, source: str | Path | dict) -> ImportResult: ...

class OewnImporter:
    target_roles: tuple[str, ...] = ("lexicon",)
    def run(self, mg, source): ...

class FrameNetImporter:
    target_roles: tuple[str, ...] = ("concepts",)
    def run(self, mg, source): ...

# Phase 15b AlignmentsImporter (parametric)
class AlignmentsImporter:
    def __init__(self, pairs: list[tuple[str, str]]):
        self.target_roles = tuple(f"alignment:{a}:{b}" for a, b in pairs)
    def run(self, mg, sources_per_pair): ...
```

`bootstrap_global` ensures all 6 named Global roles (PB-21) + each
importer's `target_roles` (covers alignment pairs / any non-named
additions) + runs importers in declared order.

#### PB-23 — Phase 15b ships all 3 ordered alignment pairs (with fallback)

Phase 15b's AlignmentsImporter writes `alignment:<a>:<b>` pair-graphs.
3 ordered pairs from the 3 importer-driven roles:

- `alignment:ontology:lexicon` (DOLCE-DUL ↔ OEWN)
- `alignment:lexicon:concepts` (OEWN ↔ FrameNet)
- `alignment:ontology:concepts` (DOLCE-DUL ↔ FrameNet)

Three considered: (3-i) ship all 3 ordered pairs; (3-ii) ship most-
studied pair only (OEWN↔FrameNet); (3-iii) defer enumeration to 15b.

**Lock: PB-3-i** with explicit fallback to PB-3-ii in 15b's design
log IF sourcing reveals an unavailable dataset. Plan-for-three, ship-
what-sources-allow. FN-WN is well-studied (Berkeley FrameNet provides
WordNet alignments); DOLCE-OEWN and DOLCE-FrameNet may need broader
academic sourcing.

## 2. What ships in Phase 15a (final scope)

### Code

* **NEW package `mindsos_admin/`** — 4 modules:
  * `mindsos_admin/__init__.py` — package marker; re-exports
    `bootstrap_global` + 3 Importer classes.
  * `mindsos_admin/bootstrap.py` (~150 LOC) — `bootstrap_global(
    importers: list[ImporterProtocol] = (), *, name: str =
    "global_knowledge") -> Metagraph`. Ensures all 6 named Global
    role-graphs (PB-21) + each importer's `target_roles` (PB-22) +
    runs importers in declared order. Returns populated `Metagraph`
    suitable for `KnowledgeLayer(global_metagraph=mg)`.
  * `mindsos_admin/importers/__init__.py` — re-exports the 3
    Importer classes.
  * `mindsos_admin/importers/dolce.py` (~250 LOC) — `DolceImporter`
    with `target_roles=("ontology",)` + `run(mg, source) ->
    ImportResult`. Parses OWL via `rdflib`; mints IRIs via
    `mindsos_knowledge.identifiers.dolce_iri`; writes Class/Property
    nodes + subClassOf/subPropertyOf/restriction edges + intersection
    / property-chain hyperedges. Auto-ensures `ontology` role-graph
    (PB-14).
  * `mindsos_admin/importers/oewn.py` (~250 LOC) — `OewnImporter`
    with `target_roles=("lexicon",)`. Parses OEWN XML; mints IRIs via
    `oewn_synset_iri` / `oewn_sense_iri` / `oewn_lemma_iri`; writes
    Synset/Lemma/Sense nodes + synset-relations / sense-relations
    edges. Auto-ensures `lexicon` role-graph.
  * `mindsos_admin/importers/framenet.py` (~250 LOC) —
    `FrameNetImporter` with `target_roles=("concepts",)`. Parses
    FrameNet XML; mints IRIs via `framenet_frame_iri` /
    `framenet_lu_iri` / `framenet_fe_iri`; writes Frame/FrameElement
    /LexicalUnit nodes + has_fe/evokes/frame_relations edges +
    fe_mappings hyperedges. Auto-ensures `concepts` role-graph.

* **`ImportResult` dataclass** (in `mindsos_admin/__init__.py`):
  ```python
  @dataclass(frozen=True)
  class ImportResult:
      role: str
      version: str
      source: str             # source-name (e.g. "dolce-dul")
      imported_at: datetime
      stats: dict[str, int]   # nodes_added/edges_added/per-type counts
  ```

* **CLI verbs in `mindsos_cli/`**:
  * `mindsos admin` — NEW top-level admin group.
  * `mindsos admin import dolce --source PATH --version STR [--json]`
  * `mindsos admin import oewn --source PATH --version STR [--json]`
  * `mindsos admin import framenet --source PATH --version STR [--json]`
  * Each verb instantiates a fresh `Metagraph`, calls
    `bootstrap_global` with the relevant importer, prints
    `ImportResult` (text by default; JSON on `--json`).

* **`mindsos doctor`** updates: 4-pkg parity → 5-pkg parity (adds
  `mindsos_admin.__version__` check).

### Synthetic-shape fixtures

* `tests/phase_15a/fixtures/dolce_synth.owl` — 10-20 Classes, 5-10
  Properties, 3-5 restrictions. Format-accurate OWL/XML.
* `tests/phase_15a/fixtures/oewn_synth.xml` — 20 Synsets, 30 Senses,
  20 Lemmas, 10 cross-synset relations. Format-accurate OEWN-LMF XML.
* `tests/phase_15a/fixtures/framenet_synth.xml` — 5 Frames, 10 FEs,
  15 LUs, 5 frame-relations. Format-accurate FrameNet XML
  (synthetic content; no Berkeley FrameNet text excerpted).

### Real-dataset downloader

* `scripts/fetch_datasets.sh` (POSIX) — downloads DOLCE-DUL 4.1 +
  OEWN 2024 to `data/datasets/`. Refuses FrameNet ("requires manual
  Berkeley license acceptance + download; place file at
  `data/datasets/framenet/fndata-1.7.zip`").
* `scripts/fetch_datasets.py` (Python) — same logic, opt-in
  cross-platform fallback.
* `data/datasets/` gitignored.

### ADR amendments

See §3 below.

### Doc rewrites

See §4 below.

### NOT in Phase 15a scope (per pushback locks)

* AlignmentsImporter (PB-4 → Phase 15b).
* MetagraphSchema scanner L1 module (PB-9 → Phase 15b).
* `mindsos admin scan-schema` CLI verb (PB-5+PB-9 → Phase 15b).
* `mindsos admin import alignments` CLI verb (Phase 15b).
* Per-edge alignment-anchor IRI builder (PB-3 → Phase 33-35).
* ADR-0134 Proposed → Accepted flip (PB-2 → real-bump phase).
* `docs/dev/migration-playbook.md` full content (deferred → Phase 15b).
* ADR-0134 §amendment-3 (deferred → Phase 15b).
* Validator surface (Phase 36 owns per ADR-0139).
* Promotion machinery (Phase 16 owns).
* `KLWriteHandle` (Phase 33-35 owns per ADR-0143).

## 3. ADR amendments (Phase 15a authors)

### ADR-0140 §amendment-1 (full supersession of §Decision §1+§2)

File: `/Layered Intelligence/docs/decisions/adr/0140-server-owns-
admin-operations.md` (parent project tree per Model C).

**Trigger:** ADR-0140 §Decision (Proposed, 2026-04-27) routes
importers and promotion machinery to `mindsos_server/`. Phase 15a's
design pass (PB-1 → PB-1-i → PB-2-i across rounds 1, 2, 4)
re-promoted §Alternatives #3 (`mindsos_admin/`) on different grounds:
ADR-0043 (**Accepted**) invariant precedence + role-description
("server = runtime envelope; admin = operations") + lifetime asymmetry
(admin operations don't need session/auth/HTTP; server does).

**Amended behavior:**

* **§Decision §1 superseded** — importer home is `mindsos_admin/
  importers/`, not `mindsos_server/importers/`. All 4 importers
  (DOLCE / OEWN / FrameNet / Alignments) ship at admin permanently.
* **§Decision §2 superseded** — promotion machinery home is
  `mindsos_admin/promotion.py`, not `mindsos_server/promotion.py`.
  Phase 16's `propose_for_promotion()` lands at admin from day one.
* **§Decision §3 (`release_update()` stays in `mindsos_server/
  release.py`)** — unchanged. Release-ship orchestration requires
  session + audit + HTTP envelope; that's server territory.
* **§Decision §4 (`bootstrap()` for KL stays as install-time helper)**
  — unchanged. KL retains its bootstrap; admin's `bootstrap_global`
  is a parallel orchestration helper for the importer flow (per
  ADR-0042 §amendment-2).
* **Phase 37 row in PHASE_MAP retired.** No admin → server relocation
  happens. If server (when built) needs admin operations exposed over
  HTTP, server imports admin (downward dependency, fine); admin code
  does not move.

**Rationale:**

ADR-0043 (Accepted) forbids file-I/O in `mindsos_knowledge/`. The
original §Decision routed file-I/O importers to `mindsos_server/`,
which solved ADR-0043 by relocation. PB-1 (Round 1) surfaced that
this routes file-I/O code to a layer that hosts session/HTTP envelope
— a category mismatch. The role-description partition (server =
envelope, admin = operations) makes `mindsos_admin/` the natural
home: file-I/O is OK there (no ADR-0043 equivalent for admin); no
session/HTTP machinery is required (admin operations run at admin-
CLI boundary).

**Out-of-scope for amendment-1:**

* Server-side HTTP exposure of admin operations (Phase 18+ owns;
  pattern is `mindsos_server` imports `mindsos_admin` for endpoint
  handlers).
* Capability gates (`CAN_BOOTSTRAP_GLOBAL`, `CAN_RUN_IMPORTER`,
  `CAN_PROPOSE_MUTATION`) — defer to Phase 18 when server's
  capability framework lands.
* ADR-0140's `Status: Proposed → Accepted` flip — defer to whichever
  later phase first wires capability gates around admin operations
  (Phase 18 or beyond). Phase 15a does not flip.

See `halvim_mindsos/confirmation_docs/PHASE_15a_DESIGN_LOG.md`
§PB-1 / §PB-8 / §PB-17 / §PB-18 for the multi-round rationale.

### ADR-0042 §amendment-2 (third first-install sequence)

File: `/Layered Intelligence/docs/decisions/adr/0042-kl-install-
extract-hooks.md` (parent project tree per Model C).

**Trigger:** ADR-0042 §amendment-1 (Phase 14) names two first-install
sequences: (1) server startup warm-restart from FalkorDB; (2)
`KnowledgeLayer.bootstrap()` for empty admin install. Phase 15a ships
`mindsos_admin.bootstrap_global(importers=[...]) -> Metagraph` (PB-13)
that builds a populated Global from importer output, then hands it
to `KnowledgeLayer(global_metagraph=mg)`. Amendment-1 doesn't
enumerate this third sequence.

**Amended behavior:**

Third first-install sequence — **importer-built Global**:
```python
from mindsos_admin import bootstrap_global, DolceImporter, OewnImporter, FrameNetImporter

mg = bootstrap_global(importers=[
    DolceImporter(),
    OewnImporter(),
    FrameNetImporter(),
])
# mg now has all 6 named Global role-graphs ensured (PB-21 parity
# with KL.bootstrap()); ontology/lexicon/concepts populated by
# importers; promoted-pipelines/task-patterns/problem-trace empty.
kl = KnowledgeLayer(global_metagraph=mg)
# Caller persists mg to FalkorDB out-of-band per ADR-0043.
```

* `bootstrap_global` is in `mindsos_admin/` per ADR-0140 §amendment-1.
* End-state Global shape is identical to `KnowledgeLayer.bootstrap()`'s
  output (PB-21); the difference is content: 3 role-graphs populated
  vs all-empty.
* `KnowledgeLayer.bootstrap()` remains the empty-install convenience;
  `bootstrap_global` is the populated-install convenience.

**Rationale:** ADR-0042's constructor-parameter mechanism (§amendment-1)
already accepts any-source Metagraph. Amendment-2 documents the
admin-package convention so reverse-engineering admin install paths
from code isn't required. Parallels §amendment-1's two-sequence
enumeration.

**Out-of-scope for amendment-2:**

* Re-import after KL is live (Global-swap) — §amendment-1
  §Out-of-scope says no swap method; importer-built re-imports use
  process-restart pattern.
* Per-user Local importer flow — no consumer (Locals are user-
  authored per ADR-0044; admin doesn't import per-user content).
* Partial re-import (replace one role-graph) — no consumer.

See `halvim_mindsos/confirmation_docs/PHASE_15a_DESIGN_LOG.md`
§PB-13 / §PB-16 / §PB-21 for the rationale chain.

## 4. Doc cascade (Phase 15a rewrites)

* **`halvim_mindsos/docs/concepts/admin-global-shipping.md`** — full
  rewrite of "Phase 15 (interim)" and "Phase 37 (relocation)"
  subsections. Importer permanent home is `mindsos_admin/importers/`.
  Phase 37 retired. `last_confirmed_phase: 14a → 15a`.

* **`halvim_mindsos/docs/concepts/knowledge-lifecycle.md`** —
  Phase 15 row Status `planned → shipped (15a partial — 3/4
  importers; Alignments in 15b)`; Phase 15 row split implicit via
  PHASE_MAP. Phase 37 row retired (struck-through with note).
  Front-matter `last_confirmed_phase: 14 → 15a`.

* **`halvim_mindsos/docs/concepts/global-local.md`** — front-matter
  `last_confirmed_phase: 14 → 15a`. Body amend: §"Bootstrap-fresh
  Global has 6 role-graphs" table now cross-references both
  `KL.bootstrap()` (empty) AND `mindsos_admin.bootstrap_global()`
  (populated) as install paths. Cross-link ADR-0042 §amendment-2.

* **`halvim_mindsos/docs/knowledge-sources/dolce.md`** — NEW. Pin:
  DOLCE-DUL 4.1. License: Creative Commons. Source URL. Import
  command. Expected stats (Classes / Properties / restrictions /
  intersection-hyperedges / property-chain-hyperedges).

* **`halvim_mindsos/docs/knowledge-sources/oewn.md`** — NEW. Pin:
  OEWN 2024. License: CC-BY-SA 4.0. Source URL. Import command.
  Expected stats (Synsets / Lemmas / Senses / synset-relations /
  sense-relations).

* **`halvim_mindsos/docs/knowledge-sources/framenet.md`** — NEW. Pin:
  FrameNet 1.7. License: Berkeley click-through (not redistributable;
  user-acceptance required). Source URL. Manual download instruction
  (downloader refuses). Import command. Expected stats (Frames / FEs
  / LUs / frame-relations / fe-mappings).

* **`halvim_mindsos/docs/usage/knowledge/overview.md`** — amend with
  Phase 15a import section (admin importer flow + KL hand-off).

* **`halvim_mindsos/docs/changelog/CHANGELOG.md`** — Phase 15a entry.

* **`halvim_mindsos/mkdocs.yml`** — `Knowledge sources` nav group
  with the 3 NEW pages.

## 5. 7-site new-top-level-package checklist for `mindsos_admin`

Per `feedback_new_top_level_package.md` (6 sites) +
`feedback_host_pip_refresh_on_new_package.md` (1 site = 7th).

1. **`pyproject.toml`** — `[tool.setuptools.packages.find]`
   `include = ["mindsos_core*", "mindsos_cli*", "mindsos_instances*",
   "mindsos_knowledge*", "mindsos_admin*"]`. `description` updated.
2. **`Dockerfile`** — BOTH prod and test stages get `COPY
   mindsos_admin/ /app/mindsos_admin/` (between existing
   `mindsos_knowledge/` and the entrypoint COPY).
3. **`tests/_shared/sentinel_paths.py`** — add `mindsos_admin/__init__.py`,
   `mindsos_admin/bootstrap.py`, `mindsos_admin/importers/__init__.py`,
   `mindsos_admin/importers/dolce.py`, `mindsos_admin/importers/oewn.py`,
   `mindsos_admin/importers/framenet.py` (6 sentinels).
4. **`mindsos_cli/commands/doctor.py`** — version-parity check now
   5-pkg: `mindsos_core` + `mindsos_cli` + `mindsos_instances` +
   `mindsos_knowledge` + `mindsos_admin`. Existing test
   `tests/cli/test_doctor_version_parity.py` (or equivalent)
   parameter-expanded.
5. **Linux host pip refresh recipe** — `notes-phase-15a.md` includes
   `cd halvim_mindsos && pip install -e . --user --break-system-packages`
   step after the branch checkout, before any host-native `mindsos`
   invocation.
6. **Cumulative literal audit for `mindsos_admin`** — grep ALL
   `tests/` for `mindsos_knowledge.importers` and replace with
   `mindsos_admin.importers` (none expected — no such code shipped
   yet — but the grep is the safety net per
   `feedback_phase_baseline_literal_audit.md`).
7. **`tests/phase_15a/test_image_completeness_phase15a.py`** — assert
   all 6 sentinel paths from item 3 exist in the test-stage image.

Plus version-string bumps to `+phase15a` across 5 packages + manifest
phase + image tags (§ Process discipline below).

## 6. Test surface (`tests/phase_15a/`)

* `test_dolce_importer.py` — parser unit (synthetic OWL → expected
  parsed dict shape); builder unit (parsed dict → expected L1 node/
  edge counts); IRI round-trip per Phase 12 PB-10 contract; smoke
  end-to-end (`DolceImporter().run(mg, fixture_path)` → expected
  stats dict); ADR-0044 boundary (writes ONLY to `ontology`); auto-
  ensure idempotency (PB-14).
* `test_oewn_importer.py` — same matrix for OEWN.
* `test_framenet_importer.py` — same matrix for FrameNet.
* `test_bootstrap_global.py` — PB-21 parity (Metagraph after
  `bootstrap_global([])` has 6 named Global role-graphs identical to
  `KnowledgeLayer.bootstrap().global_view().roles()`); PB-22 protocol
  (registered importer's `target_roles` are ensured + importer's
  `run` is called); 3-importer end-to-end (DOLCE + OEWN + FrameNet
  → expected combined stats); hand-off to KL constructor (`KL(
  global_metagraph=mg)` accepts the populated mg).
* `test_importer_protocol.py` — `target_roles` attribute presence on
  all 3 importer classes; `target_roles` type is `tuple[str, ...]`;
  `target_roles` non-empty.
* `test_admin_cli.py` — `mindsos admin --help` lists `import` group;
  `mindsos admin import --help` lists 3 verbs; each verb's `--json`
  output is valid JSON ImportResult shape; exit-0 on success; exit-
  nonzero on missing `--source`.
* `test_dimensional_snapshot_phase15a.py` — parametric: pre-import
  vs post-import counts per role-graph (uses synthetic fixtures so
  counts are deterministic; cross-checks against `len(parser(...))`
  output during Step-0 probe per
  `feedback_dimension_table_cross_check.md`).
* `test_import_isolation_phase15a.py` — AST walk over
  `mindsos_admin/` (no `mindsos_server` imports per ADR-0010
  extended; downward deps OK: `mindsos_admin` may import
  `mindsos_knowledge`, `mindsos_core`).
* `test_image_completeness_phase15a.py` — 6 sentinel paths from §5
  item 3.
* `test_adr_amendment_sentinels.py` — ADR-0140 §amendment-1 + ADR-
  0042 §amendment-2 file checks (skip in container per Model C;
  mirrors Phase 12/13/14 pattern).

Cumulative target: previous baseline (2148 passed / 14 skipped) +
~100-130 new passing tests + 2 new skips for ADR amendment sentinels
= ~2250 passed / 16 skipped.

## 7. Forward-cited ADRs in this design log

* **ADR-0010 (Accepted)** — layer isolation; `mindsos_admin/` no
  `mindsos_server/` imports; `mindsos_admin` may import
  `mindsos_knowledge` + `mindsos_core` (downward).
* **ADR-0042 (Accepted)** + Phase 14 §amendment-1 + Phase 15a
  §amendment-2 (NEW) — third first-install sequence.
* **ADR-0043 (Accepted)** — KL in-memory only; **load-bearing trigger
  for PB-1**. Importers go to admin precisely because admin is not
  bound by ADR-0043.
* **ADR-0044 (Accepted)** — memories Local-per-user; importers write
  Global only; `ensure_global_role_graph(mg, ROLE_MEMORIES)` raises.
* **ADR-0045 (Accepted)** — per-role IRI builders; importers consume
  Phase 12's 14-builder surface verbatim.
* **ADR-0061 (Accepted)** — dual metagraph Global + Local.
* **ADR-0130 (Accepted)** — metagraph property bag.
* **ADR-0131 (Accepted)** — pluggable IdStrategy; admin importers
  honour caller-supplied IdStrategy on `bootstrap_global`.
* **ADR-0134 (Proposed)** — schema migration scanner; NOT flipped at
  Phase 15a per PB-2.
* **ADR-0138 (Proposed)** — KL drops write API; honoured by absence;
  not flipped.
* **ADR-0139 (Proposed)** — hybrid invariant home; importers do NOT
  call validators at Phase 15a (Phase 36 ships validator surface);
  L1 structural invariants enforced at write time as today.
* **ADR-0140 (Proposed)** + Phase 15a §amendment-1 (NEW) — admin
  permanent home; §Decision §1+§2 superseded.
* **ADR-0149 (Accepted)** — schemas at `strict=False`;
  `ensure_global_role_graph` continues to call `schema_for_role(role)`
  with default strict.
* **ADR-0150 (Accepted)** + Phase 14 §amendment-1 — closed role-set;
  alignment Global-only (Phase 15b consumer).

## 8. Carry-forward (Phase 15a → Phase 15b)

* **AlignmentsImporter** — Phase 15b lands; ships at `mindsos_admin/
  importers/alignments.py`. Parametric `target_roles` per PB-22.
  All 3 ordered pairs per PB-23 (with fallback to single pair if
  sourcing fails).
* **Per-edge alignment-anchor IRI builder** — PB-3 (4th hop); first
  consumer is Phase 33-35's alignment-lookup capacity. Phase 15b's
  AlignmentsImporter writes edges via L1 with whatever ID L1 mints;
  no anchor IRI introduced.
* **MetagraphSchema scanner L1 module** — Phase 15b ships
  `mindsos_core/schema/migration.py` + adds `SchemaMigrationError` /
  `UnknownEdgeTypeError` to `mindsos_core/exceptions.py` per ADR-0134
  §Implementation references. Layer-mixing acknowledged (PB-9).
* **`mindsos admin scan-schema` CLI verb** — Phase 15b. Backend
  module location (between `mindsos_admin/scan.py` and
  `mindsos_cli/admin_commands.py`) decided at 15b impl time.
* **ADR-0134 Proposed → Accepted flip** — NOT in 15b either; defer
  to whichever later phase first does a real role-graph schema bump
  (PB-2).
* **`docs/dev/migration-playbook.md` full content** — Phase 15b.
* **ADR-0134 §amendment-3** — Phase 15b.
* **`docs/knowledge-sources/alignments.md`** — Phase 15b.

## 9. L1 + L2 surface probe outcome

Confirmed available from prior phases:

* **L1 (Phase 02-11):** `Metagraph(name, *, identity, metagraph_id,
  properties, id_strategy)`. `Graph(name, *, role, graph_id,
  identity, schema, properties)`. `Metagraph.add_graph(graph)`
  unifies registries (P16 lock). `Graph.add_node`,
  `Graph.add_edge`, `Graph.add_hyperedge` per Phase 03/05.
  `Graph.add_xref` per Phase 09 (importers use only intra-graph
  writes at 15a; xrefs reserved for cross-metagraph cases —
  AlignmentsImporter at 15b).
* **L2 (Phase 12-14):** Full 14-builder IRI surface via
  `mindsos_knowledge.identifiers`:
  * Seed: `dolce_iri(version, fragment)`, `oewn_synset_iri(version,
    synset_id, pos)`, `oewn_sense_iri(version, sense_id)`,
    `oewn_lemma_iri(version, lemma, pos)`, `framenet_frame_iri(
    version, frame_id)`, `framenet_lu_iri(version, lu_id)`,
    `framenet_fe_iri(version, frame_id, fe_id)`.
  * Upper-layer: `pipeline_iri`, `pipeline_step_iri`,
    `task_pattern_iri`, `subgoal_template_iri`, `memory_iri`,
    `problem_trace_iri`, `capacity_snapshot_iri`.
  * Graph-name helper: `alignment_role(role_a, role_b)`.
  * Round-trip: `parse_iri(builder(*args)).full == builder(*args)`.
* **L2 (Phase 13):** 9 schema builders via
  `mindsos_knowledge.schemas`; `schema_for_role(role)` dispatch
  raises `UnknownRoleError` on miss.
* **L2 (Phase 14):** `ensure_global_role_graph(mg, role, *,
  extra_edge_types=())` + `ensure_local_role_graph(mg, role)` in
  `mindsos_knowledge.bootstrap`. `KnowledgeLayer(global_metagraph=
  Metagraph | None = None, *, id_strategy=UUID4Strategy())`. Both
  consumed verbatim by Phase 15a's `bootstrap_global`.

**Parser dependencies (NEW at Phase 15a):**

* `rdflib` (BSD 3-clause) — DOLCE OWL parsing. Add to `requirements.txt`
  via `pip-compile`; pin via hash per project Reproducibility rule.
  Pure-Python; no native deps.
* `lxml` (BSD; libxml2-based) — OEWN + FrameNet XML parsing. Faster
  than stdlib `xml.etree.ElementTree` for the dataset sizes involved;
  also handles XPath needed for OEWN-LMF traversal. Add to
  `requirements.txt`. Native dep on libxml2; Docker base image
  (`python:3.12-slim-bookworm` per current pin) ships it; add `libxml2-
  dev` only if pip wheel doesn't cover the platform (typically not
  needed on slim-bookworm amd64).

**Risks surfaced by probe:**

* `lxml` adds a native dep; if the slim-bookworm wheel doesn't cover
  the build platform, `pip install` falls back to source build
  requiring `libxml2-dev` + `libxslt-dev`. Mitigation: prefer
  `lxml >= 5.0` (wheels available); document fallback in
  `notes-phase-15a.md`.
* `rdflib` pulls `pyparsing` transitively; `requirements.txt` grows.
  Acceptable — `pip-compile` resolves; no action needed.

## 10. Process discipline reminders (per feedback memories)

* **Branch:** `git fetch origin && git checkout -b phase-15a origin/main`.
  Branch off `origin/main` (5282ebd), NOT off `phase-14`.
* **Sandbox vs Mac git** — file edits in sandbox via Write/Edit; git
  ops (`add`/`commit`/`push`/`tag`) run on Mac per
  `feedback_sandbox_vs_mac_git_separation.md`.
* **`notes-phase-15a.md` at REPO ROOT** per
  `feedback_confirm_phase_file_paths.md`.
* **Pre-build test image** before confirm-phase per
  `feedback_confirm_phase_timeout.md`: `docker compose --profile test
  build mindsos-test`. Timeout 1800s.
* **Cumulative literal audit** before patching per
  `feedback_phase_baseline_literal_audit.md`: grep ALL `tests/` for
  `+phase14` / `phase 14` / `Phase 14` literals; replace as needed.
* **Test order:** `tests/phase_15a/` GREEN before `tests/` cumulative
  sweep per `feedback_test_order_current_then_cumulative.md`.
* **Dimension-table cross-check** per
  `feedback_dimension_table_cross_check.md`: EXPECTED counts derived
  from `len(parser(synthetic_fixture))` output during Step-0 probe,
  never hand-tabulated.
* **Tag AFTER squash-merge** per
  `feedback_release_tag_after_squash_merge_only.md`:
  `phase-15a-confirmed` tag pushed from main commit containing
  `confirmation_docs/PHASE_15a_CONFIRMED.md`, not from `phase-15a`
  branch sha.
* **Batch-fix-don't-iterate** per
  `feedback_batch_fix_dont_iterate.md`: enumerate ALL failures via
  static grep BEFORE patching; one commit, one push, one rebuild.
* **Version bump:** `+phase15a` across 5 packages
  (`mindsos_core` / `mindsos_cli` / `mindsos_instances` /
  `mindsos_knowledge` / `mindsos_admin`); `pyproject.toml [project]
  version`; `mindsos_cli/manifest.toml [mindsos] phase = "15a"`;
  `docker-compose.yml` image tags `mindsos:phase15a-{prod,test}`.

---

**Sign-off:** Plan locked across 5 rounds; 23 design pushbacks all
user-agreed. No open questions remain on architecture, package
location, importer protocol, ADR amendments, or doc cascade.
Implementation may proceed against `phase-15a` branch.
