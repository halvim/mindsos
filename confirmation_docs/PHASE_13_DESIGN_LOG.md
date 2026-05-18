# Phase 13 — Design Log

> Captured 2026-05-18. Records all design pushbacks (PB-1..27) + the
> Step-0 audit table + API-surface probe outcome + carry-forward.
> Future amendments to ADRs 0017 / 0149 / 0150 should consult this
> file for rationale.

## 0. Scope at chat-open

PHASE_MAP §13 (pre-correction) read: "Features: show role schema;
validate role-graph against schema. Tests: alignment / lexicon /
ontology / concepts schemas validate respective fixtures. Risks:
schema changes are breaking; anchor each role-schema's contract in
a confirmation fixture. Docs: docs/usage/knowledge/overview.md,
role-specific pages." Deps: 04, 12. Layer: L2. Net-new: No.

Pre-design inventory revealed two load-bearing mismatches:

* **Scope undershoot vs DESIGN_UPPER_LAYER_ROLES.md.** PHASE_MAP §13
  names 4 seed-role schemas. The legacy design doc §3.2-§3.3
  specifies 8 role-graph builders (4 seed + 5 upper-layer) and
  extends `_schema_for_role`'s dispatch table to register all 8.
  The 5 upper-layer role constants ALREADY shipped in Phase 12
  (`ROLE_PROMOTED_PIPELINES`, etc.) per PB-9 / PB-12 of that chat
  — only their schemas are missing. Mirrors Phase 12 PB-2's
  PHASE_MAP-undershoots-ADR-0045-closure pattern.
* **Knowledge-addition lifecycle is distributed across 6 phases
  (14, 15, 16, 17, 24, 37) with no single phase synthesising it.**
  Surfaced as PB-19; resolved by inserting a new design-only Phase
  14a.

User answered the scope question with "Ship all 8 schemas (closure)";
all subsequent pushbacks fold the 8-schema closure into the design.

## 1. Design pushbacks (PB-1..27)

Five rounds of pushbacks. User agreed all picks.

### PB-1 — 8-schema closure

8 schema builders (4 seed v3 ports + 5 NET-NEW upper-layer at
`strict=False`) + parametric alignment branch + dispatch function.
Closes the L2 schema dispatch table per legacy §3.3 + DESIGN doc
§2.1. PHASE_MAP §13 row Net-new flag flips `No → Partial — 5 net-new
schema builders for upper-layer roles`.

### PB-2 — MetagraphSchema scanner stays deferred

Phase 13 ships per-Graph `Schema` objects (NodeType+EdgeType inside
one graph), NOT `MetagraphSchema` objects (which govern inter-graph
wiring per Phase 05b/c/d). Phase 14 (KL bootstrap) is the first
MetagraphSchema-bump candidate. Phase 11 PB-7 C / Phase 12 PB-5
carry-forward re-carried to Phase 14.

### PB-3 — Schema strictness lock + sentinel + ADR-0017 amendment

All 9 schemas default `strict=False`. Sentinel test
(`test_strict_false_sentinel.py`) parametrises over all 9 builders
and asserts `schema.strict is False`. ADR-0017 §amendment-1
documents the 2-week-no-edit tightening rule.

### PB-4 — Ontology HyperEdgeType lift

v3 ontology exposes 7 hyperedge "label" constants (predates
Phase 04-v2's `HyperEdgeType`). Phase 13 lifts them to
`Schema.add_hyperedge_type(HyperEdgeType(name, allowed_member_types))`
registrations. Ordering semantics for `PROPERTY_CHAIN` etc. stay at
HyperEdge instance level (HyperEdge.members is a list — natural
insertion order). 7 hyperedge types ship; dimensional snapshot
verifies count.

### PB-5 — Alignment schema shape + per-edge alignment IRI carry-forward

Alignment schema is **parametric** — one `build_alignment_schema(strict,
extra_edge_types)` serves all role-pair alignment graphs. The
`AlignmentAnchor` NodeType + 8-element edge vocabulary ports from v3
verbatim. Anchor IRI minting (wrapper IRI vs entity-IRI-reuse) is
deferred to Phase 14 (KL bootstrap) — first consumer decides.
Phase 12 PB-4 carry-forward re-carried to Phase 14.

### PB-6 — CLI surface

`mindsos knowledge schema {show,validate}` sub-subgroup parallels
Phase 12's `iri / ref-types / roles` shape. `show` prints
NodeTypes/EdgeTypes/HyperEdgeTypes/strict flag. `validate` runs L1
structural pass on a graph state-file; `--exit-zero` flag surfaces
violations without failing exit code; Phase 36 (hybrid validators)
adds semantic. State-file loader uses canonical `node_id`/`edge_id`
keys per B-11-T2 lock.

### PB-7 — ADR-0149 only; defer `strict_support.py`

Single ADR (ADR-0149 "L2 role-graph schemas at strict=False with
2-week tightening rule") covers strictness policy. `strict_support.py`
inventory helper stays deferred until first-tightening phase.
ADR-0150 reserved number only.

### PB-8 — Advisory module-level property constants

Upper-layer property declarations live as `frozenset[str]` module
constants (`PIPELINE_PROPS`, `MEMORY_PROPS`, etc.), NOT in
`NodeType.property_types`. Reason: `NodeType` accepts
`Dict[str, PropertyType]` (verified via PB-25 probe) but committing
PropertyType enums now means inferring types from the legacy doc
without real consumer data. Strict-tighten phase converts to typed
declarations.

### PB-9 — `HAS_STEP` is regular EdgeType + `position` property

Not an ordered HyperEdge. The "ordered via position" claim is on the
*set of steps from one Pipeline*, not on the edge itself.
`HAS_STEP_POSITION_PROPERTY = "position"` constant exports the key
name. Upper-layer schemas stay HyperEdge-free; PB-4 HyperEdge lift
isolated to ontology.

### PB-10 — Inline library tests + 2 JSON fixture files for CLI

Library tier uses inline dicts in test modules. CLI tier uses 2
JSON fixture files (`lexicon_happy.json`, `memories_bad.json`)
under `tests/phase_13/fixtures/` — test-tree-only (not in image)
per `feedback_sentinel_paths_runtime_only.md`. Fixtures use
canonical `node_id`/`edge_id` per B-11-T2.

### PB-11 — `UnknownRoleError(KnowledgeError)`

`schema_for_role(role)` raises `UnknownRoleError` on miss with a
message naming `sorted(ALL_ROLES)` + the alignment-prefix hint.
New exception class in `mindsos_knowledge/exceptions.py`. Symmetric
with Phase 11's `UnknownEdgeTypeError` discipline.

### PB-12 — Test-count itemisation

~76 isolated (74 pass + 2 skipped in container). Cumulative target
~1966 (1890 Phase 12 + 76 Phase 13). Recount after PB-17 dimensional
snapshot consolidation removed ~7 separate per-schema assertions.

### PB-13 — Step-0 audit probe list

10 probes (9 from Phase 12 + 1 NEW for schema-shape literals).
Predicted 0-3 prior-phase patches; impl confirmed 0 — third clean
streak (Phase 11 + 12 + 13).

### PB-14 — Keep alignment's `extra_edge_types` kwarg

v3 parity; alignment vocabulary is intentionally open.

### PB-15 — `schema_for_role()` no cache

8 schemas × constant-time build = trivial. Caching adds invalidation
risk if tests ever mutate returned Schemas. Symmetric with v3.

### PB-16 — Schema immutability out of scope

`Schema.freeze()` would be a Phase 04-v3 amendment. Phase 13 doesn't
need it.

### PB-17 — Dimensional snapshot sentinels (parametric)

`EXPECTED_DIMENSIONS` table pins each schema's exact
(nodes/edges/hyperedges) counts. Single parametric test replaces
8 separate per-schema set assertions; future edits force explicit
table bump.

### PB-18 — Docs: 1 overview + 9 stub role pages

Per-role pages give Phase 14-17 a clean amendment surface. Mkdocs
nav under `Usage > Knowledge`.

### PB-19 — Phase 14a knowledge-lifecycle design pass

Insert Phase 14a (docs/ADR only; no code) between Phase 13 and
Phase 14. Deliverables: ADR-0150 "L2 knowledge lifecycle" + 3
lifecycle docs + 6 PHASE_MAP row amendments.

### PB-20 — Phase 14a process exemption

No tag, no `mindsos confirm-phase`, no version bump. Downstream
Phase 14 branches off main-tip. PHASE_MAP §1 "design-only phases are
an exception" clause amendment (PB-24) documents the policy.

### PB-21 — Phase 14a row content

`Net-new: No (ADR + docs only)`; `Tag on confirm: none`; pass
criterion = ADR-0150 written + 3 docs exist + 6 row amendments.

### PB-22 — Phase 13's PHASE_MAP edit grows from 1 to 5 sites

§13 rewrite + §14a insertion + §14 deps amendment + §3 table + §1
phase count.

### PB-23 — ADR-0150 reserved; Phase 14a drafts

Phase 13 only writes the 1-line reservation stub. Full ADR content
is Phase 14a's deliverable.

### PB-24 — Phase 13 PHASE_MAP edit grows from 5 to 6 sites

Add §1 "design-only phases are an exception" clause. 6 sites in
ONE commit.

### PB-25 — Current-API surface probe (BLOCKING gate)

Probe executed pre-impl (NOT deferred to step-list). Verified:
`Schema(*, strict)` kw-only ctor; `NodeType(name, property_types,
description)` accepts dict; `EdgeType(name, allowed_sources,
allowed_targets, property_types, description)` accepts frozenset;
`HyperEdgeType(name, allowed_member_types, property_types,
description)` — no `ordered` field. All assumptions match v3 + legacy
doc sketches. **No API drift.** Round 6 skipped.

### PB-26 — Phase 13 ships `PHASE_14a_NEXT_CHAT_PROMPT.md` only

Phase 14a chat authors `PHASE_14_NEXT_CHAT_PROMPT.md` after locking
lifecycle decisions.

### PB-27 — Hotfix-class prediction + 5 mitigations

B-13-T1 candidate: schema-API drift — mitigated by PB-25.
B-13-T2 candidate: state-file rehydration bug (B-11-T2 echo) —
mitigated by PB-10 fixture using canonical keys.
ADR file path skip-in-container, Phase 14a "no tag" trigger,
HyperEdgeType arity surprise — all mitigated.

## 2. Step-list pushbacks (folded)

Standard locks carried forward:

* notes-phase-13.md at REPO ROOT.
* Pre-build the test image; timeout 1800s.
* PB-18-equiv 9-site phase-bump cascade in ONE commit.
* PB-32-equiv Dockerfile COPY probe — Step 0 probe #4: no new top-level
  package; subpackage covered by existing `COPY mindsos_knowledge`.
* PB-34-equiv host-native confirm-phase.
* PB-35-equiv tag AFTER squash-merge to main.

## 3. Step-0 audit outcomes (probe table)

| # | Probe | Predicted | Observed |
|---|---|---|---|
| 1 | state-file version literals | 0 (no persistence change) | 0 |
| 2 | phase-string literals (`"12"`, `0.0.0+phase12`, image tags) | 9 known bump sites | 9 |
| 3 | caplog/capsys assertions over loader paths | 0 | 0 |
| 4 | Dockerfile COPY discipline | 0 new COPY blocks (subpkg covered) | 0 |
| 5 | confirm-phase pytest summary regex | 0 (B-10-T6 intact) | 0 |
| 6 | doctor 4-pkg version-string parity | 0 (no new top-level pkg) | 0 |
| 7 | ref-key helper literals in existing tests | 0 | 0 |
| 8 | cumulative-count literal | 0–1 | 0 |
| 9 | ADR-0045 closure sentinel still passes | 0 | 0 |
| 10 | NEW: Schema-shape literals (`len(s.node_types)` etc.) | 0–2 | 0 |
| **11** | **NEW: API-surface probe (PB-25)** | API matches assumptions | API matches |

**Total predicted cascade: 0 prior-phase test patches.** Confirmed
0. Third clean Step-0 streak.

## 4. Carry-forward (deferred to later phases)

Phase 13 re-carries-forward (does NOT close):

* **MetagraphSchema scanner** (Phase 11 PB-7 C / Phase 12 PB-5 /
  Phase 13 PB-2) → Phase 14 (KL bootstrap is the first
  MetagraphSchema-bump candidate).
* **Per-edge alignment anchor IRI builder** (Phase 12 PB-4 /
  Phase 13 PB-5) → Phase 14 (KL bootstrap alignment-graph wiring).
* **ADR-0134 Proposed → Accepted flip** → Phase 15 (Importers; first
  KL consumer of `migrate_from` output).
* **`docs/dev/migration-playbook.md` full content** → Phase 15.
* **ADR-0134 §amendment-3** → reserved for first KL consumer's
  structural feedback (Phase 15).
* **Per-builder inverse field helpers** → per-consumer phase
  (Phase 16 / 28 / 30 etc.).
* **REF_TYPES L3 parity test** → Phase 27.
* **Server-side `user_id` charset enforcement** → Phase 18.
* **`strict_support.py` inventory helper** (legacy §4.5) → first
  per-role strict-tightening phase (post-Phase-15 for seed roles;
  post-Phase-30 for upper-layer roles per consumer dates).

New carry-forward owed by Phase 13:

* **Schema property-type strict declarations** for the 5 upper-layer
  schemas — strict-tighten PR converts the module-level frozenset
  constants (PB-8) to `NodeType(name, property_types={...})` per-role
  per ADR-0149 §Revisions discipline.
* **ADR-0150 content** → Phase 14a (PB-23).
* **3 lifecycle docs + 6 PHASE_MAP row amendments** → Phase 14a.

## 5. Cross-chat dependencies

### Closed (Phase 12 → Phase 13)

* `phase-12-confirmed` tag was the Phase 13 branch point.
* All Phase 12 surfaces (IRI builders, REF_TYPES, ref-key helpers,
  role constants, parser) unmutated.

### Forward (Phase 13 → Phase 14a → Phase 14+)

* L2 Phase 14a (lifecycle design): consumer for ADR-0150 number
  reserved here; drafts the full ADR + 3 lifecycle docs + 6
  PHASE_MAP row amendments.
* L2 Phase 14 (KL bootstrap): consumer for `schema_for_role(role)`
  + `_ROLE_SCHEMA_BUILDERS` dispatch dict + `UnknownRoleError`;
  drives MetagraphSchema-scanner Proposed → first-use trigger if
  any Metagraph wiring schema bumps; consumer for per-edge
  alignment anchor IRI decision.
* L2 Phase 15 (Importers): consumer for the 4 seed-role schemas
  (DOLCE → ontology, OEWN → lexicon, FrameNet → concepts,
  Alignments → alignment).
* L2 Phase 16 (Promotion): consumer for `promoted_pipelines` /
  `task_patterns` schemas.
* L0 Phase 18 (Server user store): inherits user_id charset (already
  via ADR-0044 §amendment-1 from Phase 12).
* L0 Phase 25 (SessionProtocol seam): consumer for the
  import-isolation invariant Phase 12 PB-18 established + Phase 13
  PB-18 extended to `schemas/*`.
* L3 Phase 27 (DataStates): owes REF_TYPES parity test (Phase 12 PB-3
  carry-forward).
* L3 Phase 28 (12 categories): consumer for `capacity_state` schema.
* L3 Phase 30 (Pipeline finder): consumer for `problem_trace` schema.
* L2 Phase 36 (Hybrid validators home, NEW CODE per ADR-0139):
  semantic validation layer that builds on Phase 13's structural
  pass.

## 6. ADR matrix (Phase 13 touches)

| ADR | Pre-Phase-13 | Phase 13 action |
|---|---|---|
| 0010 (no cross-layer L2 → L0 import) | Accepted | No edit; `tests/phase_13/test_import_isolation_phase13.py` extends Phase 12 PB-18 over `schemas/*`. |
| 0014 (L1 Core-only-imports) | Accepted | No edit. |
| 0017 (Schema strictness opt-in; Phase 04 baseline) | Accepted | **+ §amendment-1** documenting the 9 L2 role-schemas at strict=False + 2-week tightening rule per PB-3. STAYS Accepted (Revisions amendment per Model C). |
| 0044 (memories Local + user_id in IRI) | Accepted | No edit; charset enforced inside `memory_iri` since Phase 12. |
| 0045 (per-role IRI builders) | Accepted | No edit; closed in Phase 12. |
| 0047 (REF_TYPES open vocabulary) | Accepted | No edit. |
| 0066 (capacity IRI form) | Accepted | No edit. |
| 0067 (REF_TYPES shared with KL) | Accepted | No edit; L3 parity test deferred to Phase 27. |
| 0134 (schema migration scanner) | Proposed | No edit; STAYS Proposed (no Phase 13 KL consumer; re-carry to Phase 14/15). |
| 0139 (L2 hybrid validators home) | Proposed (Phase 36) | No edit; Phase 13 CLI `validate` ships L1 structural only; semantic layer is Phase 36's deliverable. |
| **0149** (L2 role-schemas strict=False + 2-week rule) | (NEW) | **Accepted in Phase 13** per PB-7. |
| **0150** (L2 knowledge lifecycle) | (NEW) | **Reserved in Phase 13** per PB-23; content drafted in Phase 14a. |

## 7. File ledger (Phase 13 modifications)

NEW:

* `mindsos_knowledge/schemas/__init__.py` — dispatch dict +
  `schema_for_role(role, strict=False)` function.
* `mindsos_knowledge/schemas/ontology.py` (PB-1 + PB-4 lift).
* `mindsos_knowledge/schemas/lexicon.py` (PB-1 v3 verbatim).
* `mindsos_knowledge/schemas/concepts.py` (PB-1 v3 verbatim).
* `mindsos_knowledge/schemas/alignment.py` (PB-1 + PB-14
  `extra_edge_types`).
* `mindsos_knowledge/schemas/promoted_pipelines.py` (NET-NEW).
* `mindsos_knowledge/schemas/task_patterns.py` (NET-NEW).
* `mindsos_knowledge/schemas/memories.py` (NET-NEW).
* `mindsos_knowledge/schemas/problem_trace.py` (NET-NEW).
* `mindsos_knowledge/schemas/capacity_state.py` (NET-NEW).
* `tests/phase_13/` — 11 test modules + 2 JSON fixtures.
* `confirmation_docs/PHASE_13_DESIGN_LOG.md` — this file.
* `confirmation_docs/PHASE_14a_NEXT_CHAT_PROMPT.md` — handoff.
* `docs/usage/knowledge/overview.md`.
* `docs/usage/knowledge/{ontology,lexicon,concepts,alignment,
  promoted-pipelines,task-patterns,memories,problem-trace,
  capacity-state}.md` — 9 stub pages.
* `/Layered Intelligence/docs/decisions/adr/0149-l2-role-schemas-strict-false-and-tightening-rule.md`
  (Accepted).
* `/Layered Intelligence/docs/decisions/adr/0150-l2-knowledge-lifecycle.md`
  (Reserved — Phase 14a drafts content).

MODIFIED:

* `mindsos_knowledge/__init__.py` — bump `__version__`; re-export
  `UnknownRoleError` + 9 builders + `schema_for_role` +
  `_ROLE_SCHEMA_BUILDERS`.
* `mindsos_knowledge/exceptions.py` — add `UnknownRoleError`.
* `mindsos_cli/__init__.py` — bump `__version__` (phase-bump
  cascade).
* `mindsos_core/__init__.py` — bump `__version__` (phase-bump
  cascade).
* `mindsos_instances/__init__.py` — bump `__version__` (phase-bump
  cascade).
* `mindsos_cli/manifest.toml` — bump `[mindsos] phase = "13"`,
  `version = "0.0.0+phase13"`.
* `mindsos_cli/commands/knowledge.py` — append `schema` sub-subgroup
  + `show` + `validate` verbs (PB-6 + state-file canonical-keys
  per B-11-T2).
* `pyproject.toml` — bump `[project] version`.
* `docker-compose.yml` — bump image tags `phase12-{prod,test}` →
  `phase13-{prod,test}`.
* `tests/_shared/sentinel_paths.py` — append 10 new module paths
  (9 schema files + dispatch init).
* `docs/dev/repo-layout.md` — mention `mindsos_knowledge/schemas/`
  sub-package.
* `docs/changelog/CHANGELOG.md` — append Phase 13 line.
* `mkdocs.yml` — add 10 nav entries under `Usage > Knowledge`.
* `confirmation_docs/PHASE_MAP.md` — 6-site edit per PB-22 + PB-24:
  §1 amendment + §13 rewrite + §14a insertion + §14 deps + §3
  table + §1 phase count.
* `/Layered Intelligence/docs/decisions/adr/0017-schema-strictness-opt-in.md`
  — append §Revisions amendment-1.

Phase-bump cascade (PB-18-equiv, ONE commit late in step list, 9
sites — same as Phase 12; no new top-level package):

* `mindsos_core/__init__.py:__version__`
* `mindsos_cli/__init__.py:__version__`
* `mindsos_instances/__init__.py:__version__`
* `mindsos_knowledge/__init__.py:__version__`
* `mindsos_cli/manifest.toml [mindsos] phase`
* `mindsos_cli/manifest.toml [mindsos] version`
* `pyproject.toml [project] version`
* `docker-compose.yml mindsos image tag (prod)`
* `docker-compose.yml mindsos image tag (test)`

## 8. Confirmation command

```
mindsos confirm-phase --phase 13 --notes-file notes-phase-13.md
```

Pre-build: `docker compose --profile test build mindsos-test` BEFORE
confirm-phase (timeout 1800s per `feedback_confirm_phase_timeout.md`).
Host-native invocation per PB-34-equiv.

Release CI tags `phase-13-confirmed` AFTER squash-merge to main per
8-step procedure in `feedback_release_tag_after_squash_merge_only.md`
(PB-35-equiv).
