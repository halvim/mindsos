# Phase 14 — Design Log

> Captured 2026-05-19. Records the 16 design pushbacks across 3 rounds
> + the Step-0 audit + L1 surface probe + carry-forward. Future
> amendments to ADRs 0042 / 0150 should consult this file for
> rationale.

## 0. Scope at chat-open

PHASE_MAP §Phase 14 row (handoff version, written by Phase 14a):

* `KnowledgeLayer` class + Global + Local metagraph bootstrap.
* `ensure_role_graph(metagraph, role)` idempotent + propagates
  `UnknownRoleError`.
* `MetagraphView` read-only.
* Per-edge alignment-anchor IRI builder (Phase 12 PB-4 / Phase 13
  PB-5 re-carry — "first consumer decides").
* MetagraphSchema scanner (Phase 11 PB-7 C / Phase 12 PB-5 / Phase
  13 PB-2 re-carry — "first MetagraphSchema-bump candidate").
* `docs/concepts/global-local.md` NEW + `overview.md` amend +
  Phase 14 lifecycle-table row flip.

Deps: 05, 07, 08, 12, 13, 14a. Layer: L2. Net-new? "Partial" per
the handoff; **re-classified to "Mostly Yes" by PB-12** — no
`KnowledgeLayer` Python source exists in `halvim_mindsos` or
`_source_backup/root/` to repackage. The v3 design lives only as a
markdown doc (`_source_backup/root/knowledge_layer_design.md`); the
class is being written NET-NEW from design + ADRs.

## 1. Design pushbacks (PB-1..16) — three rounds, all user-agreed

### Round 1 — scope and ownership locks (PB-1..6)

#### PB-1 — Defer the two carry-forwards to Phase 15

Phase 14 ships **only** bootstrap + `ensure_*_role_graph` (split into
two scope-typed methods per PB-4) + `MetagraphView` + install/extract
hooks + `global-local.md` + Phase 14 lifecycle-row flip. The two
carry-forwards (per-edge alignment-anchor IRI builder + MetagraphSchema
scanner) have **no concrete Phase 14 caller**:

* Alignment-pair graphs are minted by Phase 15's Alignments importer;
  no anchor IRIs are minted at Phase 14.
* The MetagraphSchema scanner has nothing meaningful to scan over a
  freshly-bootstrapped empty Global with no content yet.

Both re-carry to Phase 15 (which is their actual first consumer).
Cost: re-carry paperwork (4th hop for scanner; 3rd for alignment-IRI)
— cheap. Benefit: smaller cone of design risk; carry-forwards land
under their real first consumer instead of under bootstrap pressure.

#### PB-2 — `KL.bootstrap()` lives in `mindsos_knowledge`

ADR-0140 (Proposed) reads "`bootstrap()` for KL stays as the
install-time helper (server orchestrates)" — ambiguous on which
module owns the code. Lock: KL owns the in-memory builder; Phase 37
relocates orchestration per ADR-0140.

Justification: ADR-0042 install/extract precedent already establishes
KL hosts lifecycle methods that aren't "cognitive writes" in
ADR-0138's narrowed sense. Phase 37 relocation cost is one function
move; blocking Phase 14 on Phase 18 (server arrival) would force test
scaffolding for a layer that doesn't exist.

#### PB-3 — `MetagraphView` is a whitelist wrapper class

Not a subclass of `Metagraph`; not a `Protocol`; not a runtime
`__getattr__` blocklist. A dataclass holding a Metagraph reference,
exposing only read methods.

Justification: ADR-0138's "no public write methods on KL" is
honoured structurally, not socially. Subclassing keeps
`isinstance(view, Metagraph)` True (violates the intent). ADR-0143
`KLWriteHandle` (Proposed, Phase 33-35) reaches L1 mutation via the
underlying `Graph` reference returned by the handle's `.graph()` —
it does NOT route through `MetagraphView`, so the read wrapper
stays purely read with no future coupling.

#### PB-4 — Two methods: `ensure_global_role_graph` + `ensure_local_role_graph`

Not `ensure_role_graph(mg, role)` (caller discipline); not
`ensure_role_graph(mg, role)` with runtime scope-check requiring an
L1 `Metagraph.scope` field (L1 surface creep mid-L2 phase). Two
methods, each rejecting roles outside its scope set.

Scope sets:
* `_GLOBAL_ROLES = {ROLE_ONTOLOGY, ROLE_LEXICON, ROLE_CONCEPTS,
  ROLE_PROMOTED_PIPELINES, ROLE_TASK_PATTERNS, ROLE_PROBLEM_TRACE}`
  + alignment-prefixed roles (per PB-8).
* `_LOCAL_ROLES = {ROLE_MEMORIES, ROLE_CAPACITY_STATE}`.

ADR-0044 enforced at the dispatch site, not callable discipline.

#### PB-5 — Install/extract hooks ship in Phase 14

`install_local_metagraph(user_id, metagraph)` + `extract_local_
metagraph(user_id) -> Metagraph` + `AlreadyInstalledError` /
`NotInstalledError`. Per ADR-0042 (Accepted, 2026-04-22). Phase 25's
SessionProtocol seam **drives** these hooks at login/logout; Phase
14 ships the API surface.

Cost: ~30 LOC of methods + two exceptions + a round-trip test.
Benefit: Phase 25 has wiring left, not API additions.

#### PB-6 — Implement per Proposed ADR-0138 / 0141; do NOT flip them Accepted

Phase 14 ships KL **without** any write API (`add_local_node`,
`add_local_edge`, `add_local_alignment`, `promote`, `similarity_
report`) — none exist on the class. But Phase 14 does NOT move
ADR-0138 / 0141 to Accepted; they stay Proposed until Phase 33-35
ship L3 write capacities (the ADR-0138 §Accepted-when criteria).

If either ADR flips Rejected (unlikely; the L1-mutates / L3-translates
partition is settled), restoring the write API is a Phase 33-equivalent
NEW-CODE bill, not a Phase 14 supersession.

### Round 2 — gap-filling locks (PB-7..13)

#### PB-7 — Global lifecycle via constructor parameter + ADR-0042 amendment-1

ADR-0042 (Accepted) names `install_local_metagraph` /
`extract_local_metagraph` only. **There is no hook for the server
to hand KL a pre-loaded Global.** Lock:

* `KnowledgeLayer.__init__(global_metagraph: Metagraph | None = None,
  *, id_strategy: IdStrategy = UUID4Strategy())` — server uses
  `KnowledgeLayer(global_metagraph=loaded)`; tests use empty.
* `KnowledgeLayer.bootstrap(*, id_strategy=UUID4Strategy()) ->
  KnowledgeLayer` — classmethod that calls
  `cls(global_metagraph=cls._fresh_global(id_strategy))`.
* Locals always installed post-construction via `install_local_
  metagraph` (no second constructor parameter); lazy
  `local_metagraph(user_id)` auto-creates per PB-9.

ADR-0042 §amendment-1 documents this Global counterpart. Symmetric
extension; no new lifecycle methods owed.

#### PB-8 — Alignment is Global-only at Phase 14 (ADR-0150 amendment-1)

ADR-0150's Decision table left alignment scope unspecified. Phase
14's two-method API (PB-4) forces a binding. Lock: Global-only.

* `ensure_global_role_graph(mg, role)` accepts `role.startswith
  ("alignment:")` and creates the pair-graph in Global.
* `ensure_local_role_graph(mg, role)` rejects alignment prefixes
  with `KnowledgeError` (not `UnknownRoleError` — the role IS
  known; the scope is wrong).

Rationale: every Phase 15 importer writes Global alignments
(DOLCE↔OEWN, OEWN↔FrameNet, etc.). User-Local alignment authoring
is not in ADR-0145's L3 capacity categories. If a future ADR
amendment adds Local alignment authoring, ADR-0150 §Revisions
captures the change.

ADR-0150 §amendment-1 makes this explicit so Phase 33-35 doesn't
inherit the ambiguity.

#### PB-9 — Lazy `local_metagraph(user_id)` auto-ensures `memories` + `capacity-state`

Symmetric with Global bootstrap auto-ensuring 6 Global named roles.
On first access (or `install_local_metagraph` of a Local missing
them), the 2 Local-scoped role-graphs are ensured before the Local
is returned.

Single mental model: any KL-managed Local has `memories` +
`capacity-state` available without further setup. `install_local_
metagraph` accepts a Local with or without them; missing ones are
auto-ensured at install time (idempotent).

#### PB-10 — `MetagraphView.step()` returns within-view edges only; no Local-overlay

v3 KL's `step(user_id, role, from_node, edge_type)` returned
`WalkResult` records that left-joined Local specialisation onto
Global edges — contradicting v3 §1.2's own explicit out-of-scope
clause. ADR-0138's narrowing reaffirms §1.2: KL stays separated;
Mental Model / L3 composes.

Phase 14 ships `MetagraphView.step(role, node_id, edge_type=None)
-> list[Edge]` returning edges from the wrapped metagraph only. No
WalkResult, no cross-metagraph overlay. `follow_ref` deferred to
Phase 25 or first L3 capacity phase.

#### PB-11 — UUID4Strategy default + parameter override

`KnowledgeLayer.__init__` and `KnowledgeLayer.bootstrap` accept an
optional `id_strategy: IdStrategy = UUID4Strategy()`. Matches the
Phase 06 constructor convention; tests override for deterministic
runs.

#### PB-12 — Phase 14 row re-classified "Net-new? Mostly yes"

PHASE_MAP §Phase 14 row's "Net-new? Partial" reads as a repackage
phase. No `KnowledgeLayer` Python source exists in `halvim_mindsos`
or `_source_backup/root/`. The class is being designed from the v3
markdown design doc (`_source_backup/root/knowledge_layer_design.md`)
+ post-pivot ADRs (0042, 0043, 0044, 0061, 0138, 0140, 0141, 0143,
0149, 0150). One-line PHASE_MAP edit included.

Implication: the "0 prior-phase patches" clean streak from Phase
11/12/13 likely **does not** extend to Phase 14. Expect 2-4
phase-baseline literal audit hits (Phase 09 lesson). Test surface
~95-115; cumulative ~2120-2145.

#### PB-13 — No new CLI verbs in Phase 14

KL is in-memory only (ADR-0043); without persistent state-file
access (deferred to Phase 26 per Phase 14a round-3 lock), a CLI
verb like `mindsos knowledge view --global` would construct a fresh
empty KL per invocation. Zero smoke value.

Tester relies on `pytest tests/phase_14/` for verification; doctor
reports `mindsos_knowledge.KnowledgeLayer` is importable as smoke
proxy. View verbs defer to Phase 17 (versioning ships natural
multi-version view verbs).

### Round 3 — final design touches (PB-14..16)

#### PB-14 — Zero validators in Phase 14

ADR-0138 Proposed §retains "Pure-function semantic validators on
KL." ADR-0139 Proposed (Phase 36) is the home for the full
validator surface. Phase 14 has no caller for validators
(`KLWriteHandle` lands Phase 33-35).

Lock: zero validators. Phase 36 introduces `mindsos_knowledge/
validators.py` NET-NEW. `KL retains validators` from ADR-0138 is
interpreted as a *future* retention, not a Phase 14 deliverable.
Phase 14's PR brief notes this interpretation so Phase 33-35
doesn't expect them.

#### PB-15 — `step()` ships without `version=` kwarg; Phase 17 amends

One version per role-graph at Phase 14 (no breadcrumb routing).
`step(role, node_id, edge_type=None)` returns edges from the only
graph for that role. Phase 17 adds the `version=` kwarg + active-
version selection when multi-version ships.

Justification: smallest Phase 14 surface; matches "ship what has
consumers"; Phase 17 has the consumer.

#### PB-16 — `MetagraphView.get_node()` returns reference + convention

L1 `Node` is mutable; `view.get_node()` returns the reference, not
a defensive copy. The read-only contract is documented in
`docs/concepts/global-local.md` ("don't mutate Nodes returned by
MetagraphView") and enforced by KL not exposing methods that mutate.

ADR-0138's "no public write methods on KL" is about the API surface,
not about whether KL ever returns mutable objects. L1's
`Graph.add_node` etc. is the canonical write path; whether a caller
reaches L1 mutables via a write method or via a read accessor is
irrelevant — the L1 surface is where mutation lives, not KL.

Isolation test (extended from Phase 12 PB-18 AST walk) stays focused
on `mindsos_server` imports, not on Node-mutation patterns. Phase 36
hybrid validators detect post-write state drift on next read.

## 2. Calibration (design-log items, not full rounds)

* **`ensure_*_role_graph` location:** module-level functions in
  `mindsos_knowledge/bootstrap.py`. Pure operations; no KL state
  needed.
* **`KnowledgeLayer.__init__(global_metagraph)` validation:** permissive
  — server passes well-formed metagraphs; no Phase 14 name/structure
  checks.
* **`install_local_metagraph(user_id, mg)` validation:** permissive —
  ADR-0042 "exact object" contract.
* **`request_promotion()` (ADR-0137 / 0141 cite as KL method):** NOT
  shipped Phase 14; ADR-0137/0141 vs ADR-0140 attribution conflict
  deferred to Phase 16's chat.
* **Module file layout:**
  - `mindsos_knowledge/knowledge_layer.py` — `KnowledgeLayer` class.
  - `mindsos_knowledge/metagraph_view.py` — `MetagraphView` class.
  - `mindsos_knowledge/bootstrap.py` — `ensure_global_role_graph` +
    `ensure_local_role_graph` + scope-set constants.
* **`extra_edge_types` kwarg on `ensure_global_role_graph`:** accept
  in Phase 14 with default `()`; ignored for non-alignment roles.
  Phase 15's Alignments importer passes a non-empty tuple. Forward-
  compatible; no Phase 15 signature churn.
* **Metagraph property bag scope marker:** Phase 14 uses `mg.properties[
  "kl:scope"] = "global" | "local"` to mark Global vs Local
  metagraphs (ADR-0130 namespaced bag). Used by no-op assertions in
  ensure_*_role_graph; lets the server load a Metagraph from
  FalkorDB and immediately know which lifecycle path applies.
* **`Metagraph.graphs_by_role(role)`:** L1 does NOT ship a helper.
  `MetagraphView` provides role-keyed access by iterating
  `_metagraph.graphs.values()` filtering on `g.role`. Tiny method;
  no L1 surface creep.

## 3. Step-0 literal audit

Per `feedback_phase_baseline_literal_audit.md`. Phase 13 → Phase 14
literal bumps grepped on 2026-05-19:

* `+phase13` — 12 sites: `pyproject.toml`, 4× `__init__.py`,
  `manifest.toml`, `docker-compose.yml` (×2 image tags),
  `CHANGELOG.md`, `notes-phase-13.md` (historical — DO NOT EDIT),
  `PHASE_14_NEXT_CHAT_PROMPT.md` (Phase 14a handoff — DO NOT EDIT),
  `PHASE_MAP.md §Phase 14a row` (DO NOT EDIT — historical record).
* `mindsos:phase13-{prod,test}` — 2 sites: `docker-compose.yml`.
* `manifest.toml [mindsos] phase = "13"` — 1 site.
* `Phase 13` / `phase 13` in `mindsos_knowledge/` source — present
  in `__init__.py` docstrings + `schemas/__init__.py` docstrings +
  per-schema docstrings (`promoted_pipelines.py`, `lexicon.py`,
  etc.). These are HISTORICAL — they describe Phase 13's contribution
  and stay verbatim. Only the package-level `__version__` literal
  bumps.

**Edit set (12 literal bumps):**
1. `pyproject.toml` — `version = "0.0.0+phase14"`.
2. `mindsos_core/__init__.py` — `__version__`.
3. `mindsos_cli/__init__.py` — `__version__`.
4. `mindsos_instances/__init__.py` — `__version__`.
5. `mindsos_knowledge/__init__.py` — `__version__` + docstring
   Phase 14 section.
6. `mindsos_cli/manifest.toml` — `phase = "14"` + `version`.
7. `docker-compose.yml` — `mindsos:phase14-prod`.
8. `docker-compose.yml` — `mindsos:phase14-test`.
9. `CHANGELOG.md` — Phase 14 entry.
10. `tests/_shared/sentinel_paths.py` — Phase 14 sentinel paths
    section.
11. `docs/concepts/knowledge-lifecycle.md` — front-matter
    `last_confirmed_phase: 14a → 14` + Phase 14 row `planned →
    shipped`.
12. `confirmation_docs/PHASE_MAP.md` — §Phase 14 row Status
    + Net-new re-classification + scope deferrals.

## 4. L1 surface probe outcome

`Metagraph(name, *, identity, metagraph_id, properties, id_strategy)`.
`Graph(name, *, role, graph_id, identity, schema, properties)`.
`Metagraph.add_graph(graph)` unifies registries (P16 lock); raises
`IdentityError` on graph_id collision.
`Metagraph.attach_schema` ships in Phase 05b but governs MetagraphSchema
(intergraph_edges); per-Graph `Schema` attaches via `Graph(schema=...)`.

**No `Metagraph.graphs_by_role(role)` exists.** Phase 14
`MetagraphView` provides role-keyed access; no L1 method extension.

`UUID4Strategy` / `UUID5FromContentStrategy` / `IRIPassthroughStrategy`
all live in `mindsos_core.models.identity` per ADR-0131.

## 5. Forward-cited ADRs in this design log

* ADR-0010 (Accepted) — layer isolation; KL no `mindsos_server` imports.
* ADR-0042 (Accepted) + Phase 14 §amendment-1 — KL hydration; Global
  + Local lifecycle hooks.
* ADR-0043 (Accepted) — KL in-memory only; server owns I/O.
* ADR-0044 (Accepted) — memories Local-per-user.
* ADR-0061 (Accepted) — dual metagraph Global + Local.
* ADR-0130 (Accepted) — metagraph property bag (used for `kl:scope`).
* ADR-0131 (Accepted) — pluggable IdStrategy.
* ADR-0138 (Proposed) — KL drops write API; honoured by Phase 14
  shape; NOT flipped Accepted.
* ADR-0140 (Proposed) — server owns admin; bootstrap relocation
  deferred to Phase 37.
* ADR-0141 (Proposed) — `KL.promote()` stays deleted; NOT flipped
  Accepted.
* ADR-0143 (Proposed) — `KLWriteHandle` pattern for Phase 33-35;
  Phase 14 ships nothing that contradicts.
* ADR-0149 (Accepted) — schemas at strict=False; bootstrap calls
  `schema_for_role(role)` with default strict.
* ADR-0150 (Accepted) + Phase 14 §amendment-1 — closed role-set;
  alignment Global-only.

## 6. Carry-forward (Phase 14 → Phase 15)

* **Per-edge alignment-anchor IRI builder** — first consumer is
  Phase 15's Alignments importer; decide `(role-a, role-b, anchor-id)`
  ternary vs `(role-pair, anchor-id)` binary form when minting anchor
  nodes.
* **MetagraphSchema scanner** — Phase 15 (Importers) is first phase
  to bump a MetagraphSchema if its importer ships one.
* **ADR-0134 Proposed → Accepted flip** — Phase 11/12/13 carry
  retains for Phase 15.
* **`docs/dev/migration-playbook.md` full content** — Phase 15.

## 7. Cross-chat dependencies

### Closed (Phase 13 / Phase 14a → Phase 14)

* ADR-0150 number reserved by Phase 13 PB-23; Phase 14a drafted
  content (closure of 9-entry role-set with amendment escape).
  Phase 14 amends with §amendment-1 (alignment Global-only).
* Phase 14a docs (4 concept docs + mapping table) cite Phase 14 as
  Bootstrap-stage owner; Phase 14's `global-local.md` is the page
  the synthesis forward-cites.
* Phase 13 PB-11 `UnknownRoleError` propagates via Phase 14's
  `ensure_*_role_graph` for unrecognised roles (alignment-prefix
  branch + `_GLOBAL_ROLES` + `_LOCAL_ROLES` cover the rest).

### Forward (Phase 14 → Phase 15+)

* Phase 15 inherits the two carry-forwards + `KL.bootstrap()` +
  `KL.global_metagraph()` for importer targets.
* Phase 16/23/24 inherit `MetagraphView` for read paths + KL state
  shape for promotion machinery.
* Phase 17 inherits `MetagraphView.step()` and amends with
  `version=` kwarg (no signature churn for callers; default value
  preserves Phase 14 semantics).
* Phase 25 inherits install/extract hooks + the SessionProtocol
  seam.
* Phase 33-35 inherit the KL surface to build `KLWriteHandle` over.
* Phase 36 inherits the validator-shaped hole left by PB-14.
* Phase 37 inherits `KL.bootstrap()` as the relocation target per
  ADR-0140.
