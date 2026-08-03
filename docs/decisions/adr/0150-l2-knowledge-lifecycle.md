---
title: L2 role-set closure (Flavor B rejection)
status: Accepted
date: 2026-05-18
layer: L2
---

# ADR-0150: L2 role-set closure (Flavor B rejection)

**Status:** Accepted

**Date:** 2026-05-18 (number reserved by Phase 13; content drafted in Phase 14a)

**Renamed during Phase 14a** from "L2 knowledge lifecycle" per Phase 14a
round-2 PB-E. The lifecycle synthesis this ADR was originally chartered
with is now docs-tracked (not ADR-tracked) per Phase 14a round-1 PB-A:
the synthesis cites 7+ still-Proposed ADRs and would rot under an
Accepted stamp. ADR file slug `0150-l2-knowledge-lifecycle.md` retained
(filename not renamed); the ADR number is the cross-reference anchor.

**Related (Accepted):** [ADR-0017](0017-schema-strictness-opt-in.md)
(§amendment-1), [ADR-0044](0044-memories-move-to-local-per-user.md),
[ADR-0045](0045-per-role-iri-builders.md),
[ADR-0149](0149-l2-role-schemas-strict-false-and-tightening-rule.md).

**Related (Proposed, cited by sibling docs not by this ADR's Decision):**
[ADR-0118](0118-per-user-transactional-promotion.md),
[ADR-0138](0138-kl-drops-write-api.md),
[ADR-0139](0139-hybrid-invariant-home.md),
[ADR-0140](0140-server-owns-admin-operations.md),
[ADR-0143](0143-kl-write-handle-pattern.md),
[ADR-0144](0144-similarity-at-release-ship-audit-gate.md),
[ADR-0145](0145-l3-per-target-write-capacity-categories.md),
[ADR-0146](0146-l3-symmetric-write-invocation-contract.md),
[ADR-0147](0147-l3-per-flow-write-capacity-build-pattern.md).

**Companion docs (in halvim_mindsos repo):**
`docs/concepts/knowledge-lifecycle.md` (synthesis index),
`docs/concepts/user-local-authoring.md`,
`docs/concepts/admin-global-shipping.md`,
`docs/concepts/promotion-bridge.md`.

## Context

Phase 13 closed the L2 schema dispatch table at 9 schema builders (8
named-role + 1 parametric alignment template; see
[ADR-0149](0149-l2-role-schemas-strict-false-and-tightening-rule.md)).
The shape of "what is a role-graph" is now load-bearing infrastructure:
L1 mutation primitives plus L2 routing plus L3 write capacities (per
[ADR-0145](0145-l3-per-target-write-capacity-categories.md)) all key on
`role` as a discriminator.

Two operational models are possible for "what role-graphs exist":

- **Flavor A — closed role-set, content is open.** The set of
  role-graphs is fixed by ADR; content of each role-graph is added by
  ordinary writes (importers for Global, L3 capacities for Local,
  promotion for Local→Global crossings).
- **Flavor B — open role-set, addable at runtime.** Anyone with
  appropriate capability can register a new role at runtime; the
  dispatch table is a registry, not a fixed switch.

Flavor B was implicit in v3's `register_version_graph` shape (any graph
could be registered under any role string) but was never formalised.
Phase 13 PB-19 surfaced the question and locked closure at design time;
this ADR ratifies the lock.

## Decision

**The L2 role-set is closed at 9 entries.** Specifically:

| Scope                                  | Role                        | Schema builder                              |
|----------------------------------------|-----------------------------|---------------------------------------------|
| Global                                 | `ontology`                  | `build_ontology_schema(strict)`             |
| Global                                 | `lexicon`                   | `build_lexicon_schema(strict)`              |
| Global                                 | `concepts`                  | `build_concepts_schema(strict)`             |
| Global                                 | `promoted-pipelines`        | `build_promoted_pipelines_schema(strict)`   |
| Global                                 | `task-patterns`             | `build_task_patterns_schema(strict)`        |
| Global                                 | `problem-trace`             | `build_problem_trace_schema(strict)`        |
| Local                                  | `memories`                  | `build_memories_schema(strict)`             |
| Local                                  | `capacity-state`            | `build_capacity_state_schema(strict)`       |
| Per-pair (open vocabulary, parametric) | `alignment:<role-a>:<role-b>` | `build_alignment_schema(strict, extra_edge_types)` |

The 8 named roles are fixed. The alignment template admits an open
vocabulary of `<role-a>↔<role-b>` instantiations per pair (registered
through `register_version_graph` with the appropriate alignment-prefixed
role string), but **no new role outside this list is creatable at
runtime**.

**Runtime addition is rejected.** `schema_for_role(role)` raises
`UnknownRoleError` (Phase 13 PB-11) for any role not in the table above
(modulo the alignment-prefix branch). There is no `register_role(...)`
API; there will be no such API.

**Expansion requires an ADR amendment to this ADR (escape hatch
retained per round-3 PB-Q option (a)).** A future role addition — even
an admin-curated one — requires a §Revisions entry on this ADR naming
the new role, citing the consumer requirement, and listing the new
builder. The Phase 13 sentinel `tests/phase_13/test_dispatch.py` plus
the parametric `tests/phase_13/test_dimensional_snapshot.py` are the
enforcement surfaces; bypassing them bypasses this ADR.

Memories scope per [ADR-0044](0044-memories-move-to-local-per-user.md)
is locked into the table: `memories` is Local-per-user, not Global.

## Rationale

The role-set governs three load-bearing surfaces:

1. **L1 mutation primitives** keyed on `role` for routing (target
   metagraph + active version).
2. **L3 write capacities** organised per-role per
   [ADR-0145](0145-l3-per-target-write-capacity-categories.md)
   (categories `consolidate`, `trace`, `promote`, `author`, `state`
   each map to specific roles).
3. **L4 orchestration policies** plan against fixed role-graphs; a new
   role at runtime means an L4 policy with no slot to plan against.

A runtime-extensible role-set would force L3 and L4 to either (a) carry
generic role-handling code with no semantic discrimination, or (b)
accept that newly-added roles are unreachable from L4 until a code+ADR
pass anyway. (b) is what Flavor A is — the difference is whether the
mechanism is at the dispatch table (Flavor A) or hidden behind a
runtime registration that does nothing useful until code lands (Flavor
B). Flavor A is honest.

Closure also makes the lifecycle synthesisable. With a fixed role-set,
the answer to "how does Global content get added" or "how does a user
author Local content" is a finite enumeration of entry points (see
`docs/concepts/knowledge-lifecycle.md`). With an open role-set, the
lifecycle is undefinable — each new role introduces a new entry point.

## Consequences

**Good:**

- Lifecycle is finite + synthesisable (see
  `docs/concepts/knowledge-lifecycle.md`).
- L3 write-capacity table per ADR-0145 has a fixed surface (6-minimum
  capacities ↔ 5 categories ↔ closed role-set).
- `UnknownRoleError` (Phase 13 PB-11) is a hard guard, not a
  deprecation; enforcement persists indefinitely.
- L4 policies plan against a known finite set of role-graphs.
- Per-pair alignment vocabulary stays open (the `<role-a>:<role-b>`
  product space is finite-but-large; closing it would over-constrain).

**Tradeoffs:**

- Adding a new role is a v(N+1) ADR exercise, not a runtime
  registration. Cost: one ADR amendment + one schema builder +
  dispatch table entry + tests + per-role IRI builder + (if Local) a
  per-user lazy-hydration cell.
- Use cases that want per-tenant custom roles (multi-tenant white-label)
  must work inside the 9-entry table — typically by namespacing inside
  `concepts` / `memories` rather than minting new top-level roles.
- v3's `register_version_graph` flexibility narrows; consumers that
  registered ad-hoc role strings break loudly via `UnknownRoleError`.
  This is intended.

**Lifecycle entry points (Flavor A — docs-tracked, NOT ADR-locked
here):**

The role-set being closed is the necessary precondition for the
knowledge-addition lifecycle being finite. The synthesis lives in
`docs/concepts/knowledge-lifecycle.md` and its three sibling path docs:

- `docs/concepts/user-local-authoring.md` — user-Local writes via L3
  capacities (Phase 33-35) through `KLWriteHandle` (ADR-0143 Proposed).
- `docs/concepts/admin-global-shipping.md` — admin-Global writes via
  importers (Phase 15 + relocation in Phase 37 per ADR-0140 Proposed).
- `docs/concepts/promotion-bridge.md` — Local→Global crossings via
  `propose_for_promotion` + release-ship (Phase 16 + 23 + 24 per
  ADR-0118 Proposed + audit gate per ADR-0144 Proposed).

These docs cite Proposed ADRs and are expected to amend (via
`last_confirmed_phase` front-matter discipline) as those ADRs flip
Accepted. This ADR does not co-lock their content because the
underlying ADRs aren't ratified yet (see Alternatives §4).

## Alternatives considered

1. **Flavor B — runtime-extensible role-set via `register_role(name,
   schema_builder)`.** Rejected per Phase 13 PB-19. Three reasons:
   (a) breaks L3 write-capacity organisation per ADR-0145 (capacities
   are per-role by name); (b) breaks L4 orchestration's ability to plan
   against a known role-set; (c) the lifecycle becomes undefinable. The
   argued benefit (per-tenant flexibility) is achievable inside existing
   roles (concepts namespacing, memories per-user scope) without
   introducing a runtime mechanism that does nothing useful until code
   lands.

2. **Hybrid — closed seed set + runtime extension API gated by admin
   capability.** Rejected. Admin-gated runtime addition still produces
   roles L4 has no policy for; the gate is procedural, not
   architectural. If admin discipline can decide "this role belongs,"
   an ADR amendment captures the same decision durably and surfaces it
   for review.

3. **Defer the decision; ship 9 roles as a "starting set" without a
   closure lock.** Rejected per Phase 13 PB-19. Punts the question;
   consumer phases (Phase 14 KL bootstrap, Phase 28 L3 bootstrap) need
   to know whether to write defensive code for unknown roles or assume
   the set is fixed. Ambiguity is more expensive than either lock.

4. **Make ADR-0150 a synthesis ADR enumerating all Flavor A entry
   points (Phase 13 PB-19 original framing).** Rejected during Phase
   14a (round-1 PB-A → A2). The synthesis cites 7+ still-Proposed ADRs
   (0118, 0138, 0140, 0143, 0144, 0145, 0146, 0147); an Accepted
   synthesis ADR would carry a rot liability the underlying ADRs don't.
   Synthesis moves to `docs/concepts/knowledge-lifecycle.md`
   (amendable per phase via `last_confirmed_phase` discipline) and is
   cited by this ADR's §Consequences.

5. **Split into ADR-0150 (closed-roles) + ADR-0151 (lifecycle index).**
   Considered during Phase 14a round-2 (PB-E3). Rejected as
   bureaucratic: ADR-0151 with no decision would be a doc-pointer, and
   a doc-pointer is just a doc. The synthesis page directly cited from
   ADR-0150's §Consequences serves the same purpose without consuming
   an ADR number.

6. **Permanent closure with no amendment escape hatch (round-3 option
   (b)).** Rejected. No other ADR in the corpus uses
   permanent-forever language; ADR-0017's §amendment-1 demonstrates
   that the amendment pathway works. Closure-with-amendment-escape
   (option (a)) closes Flavor B at runtime — which is the failure
   mode being rejected — without foreclosing options that cost
   nothing to leave open.

## Revisions

### amendment-1 (Phase 14 ship — 2026-05-19) — alignment role is Global-only

**Trigger:** the §Decision table left `alignment:<role-a>:<role-b>`
scope unspecified (only "Per-pair (open vocabulary, parametric)").
Phase 14's two-method bootstrap API (`ensure_global_role_graph` +
`ensure_local_role_graph`) forces a scope binding for every role,
including alignment.

**Amended behavior:**

* Alignment-prefixed roles (`alignment:<a>:<b>`) are **Global-only**
  at v1. `ensure_global_role_graph(mg, role)` accepts alignment
  prefixes and creates the pair-graph in Global;
  `ensure_local_role_graph(mg, role)` rejects alignment prefixes
  with `KnowledgeError` ("alignment is Global-only at v1; ADR-0150
  §amendment-1").
* The 9-entry table is amended in spirit (no structural change):
  the alignment row's "Scope" column now reads `Global` instead of
  "Per-pair (open vocabulary, parametric)". The parametric per-pair
  shape is preserved within Global.

**Rationale:** Phase 15's importers (DOLCE↔OEWN, OEWN↔FrameNet,
etc.) all write Global alignments — administered content, not user-
authored. ADR-0145's L3 write-capacity categories do not list
alignment-authoring as a user-Local writeable category. Closing the
ambiguity now prevents Phase 33-35 from inheriting it.

**Future expansion:** if a future ADR amendment adds Local alignment
authoring (e.g., as a new L3 capacity category), this §Revisions
section gets a new amendment row naming the change. The amendment-
escape pattern (round-3 PB-Q option (a)) applies uniformly.

**Out-of-scope for amendment-1:** Local alignment minting (no
consumer); cross-scope alignment (Global concept ↔ Local memory)
— ADR-0044 keeps memories Local; cross-scope refs go through XRefs
(ADR-0128) at the L1 layer, not through an alignment pair-graph.

See `halvim_mindsos/confirmation_docs/PHASE_14_DESIGN_LOG.md` §1
PB-8 for the decision rationale.

### amendment-2 (Phase 15b ship — 2026-05-20) — supporting-evidence correction; architectural decision unchanged

**Trigger:** §amendment-1 (Phase 14) contains the load-bearing
sentence "Phase 15's importers (DOLCE↔OEWN, OEWN↔FrameNet, etc.) all
write Global alignments — administered content, not user-authored."
That sentence is now factually wrong as of Phase 15a ship + Phase 15b
reframe: Phase 15a shipped 3 source importers (DOLCE / OEWN /
FrameNet — none of which write alignments); Phase 15b ships no
importers; AlignmentsImporter is deferred to a closure phase TBD per
PHASE_MAP §Phase 28 design review. The §amendment-1 sentence
misrepresents what exists vs what's planned.

**Amended behavior:**

§amendment-1's supporting-evidence sentence is corrected as follows:

> ~~Phase 15's importers (DOLCE↔OEWN, OEWN↔FrameNet, etc.) all write
> Global alignments — administered content, not user-authored.~~
>
> **Corrected at amendment-2 (Phase 15b ship, 2026-05-20):** Phase
> 15a ships 3 source importers (`DolceImporter` / `OewnImporter` /
> `FrameNetImporter`) that populate `ontology` / `lexicon` /
> `concepts` role-graphs respectively — none of which write
> alignments. AlignmentsImporter is deferred to a closure phase TBD
> per PHASE_MAP §Phase 28 design review (see §Phase 28 row note
> "Review at design pass: does alignment-lookup land as one of the 12
> categories?"). Alignment writes, when they materialise, will be
> administered content per
> [ADR-0145](0145-l3-per-target-write-capacity-categories.md)'s
> exclusion of alignment-authoring from L3 write-capacity categories.

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
* [ADR-0044](0044-memories-move-to-local-per-user.md) memories
  Local-per-user binding unchanged.

**Rationale:**

ADR scheduling lives in PHASE_MAP, not in ADR text — house style. The
§amendment-1 sentence was supporting evidence (illustrating WHEN the
architectural lock matters), not part of the lock itself. As
scheduling shifts, ADR text needs minimal corrective edits to avoid
known-wrong statements; the underlying architectural decisions don't
move.

**Out-of-scope for amendment-2:**

* Re-opening the closed role-set §Decision. Closure stands.
* Re-opening alignment-Global-only §amendment-1 primary lock. Lock
  stands.
* Locking the alignment closure phase number at the ADR level. PHASE_MAP
  §Phase 15b row + §Phase 28 review note carry that.

See `halvim_mindsos/confirmation_docs/PHASE_15b_DESIGN_LOG.md` §1
Round 5 PB-19 for the rationale chain.

### amendment-3 (Phase 17 retirement — 2026-05-20) — version-dispatch model lock

**Trigger:** Phase 17 (originally "L2 Versioning + breadcrumbs") was
chartered to ship `step(version=)` active-version routing + a
per-role version map (Phase 14 PB-15 carry-forward). Pre-impl probe
at the Phase 17 retirement chat established that the shipped model
holds **one graph per role per metagraph** (`_find_role_graph` in
`mindsos_knowledge/bootstrap.py` keys on `g.role == role`; importers
write version-qualified IRIs into the same role-graph regardless of
the version argument; `parse_iri(...).version` extracts the version
from the IRI string itself). There is no `(role, version)`
discriminator at the graph layer; "active version" has nothing to
dispatch on.

Phase 17 retired (PHASE_MAP §17 RETIRED 2026-05-20). The retirement
implicitly locks an architectural decision that was previously
unstated; this amendment ratifies it.

**Amended behaviour:**

* **Version is an IRI-string property only.** Each role-graph holds
  IRIs whose body encodes the version (e.g.,
  `dolce-dul-4.1:PhysicalObject`); `parse_iri` is the source of
  truth for extraction. No `Graph.version` property; no
  `(role, version)` keyed lookup.
* **One graph per role per metagraph.** The §Decision closed
  role-set is dispatched by role string alone.
  `ensure_global_role_graph` and `ensure_local_role_graph` are
  idempotent on role identity; calling them with different version
  arguments does NOT mint per-version graphs.
* **No active-version state on `KnowledgeLayer` or `MetagraphView`.**
  `MetagraphView.step(role, node_id, ...)` returns edges from the
  single role-graph, no `version=` kwarg. The Phase 14 PB-15
  deferral ("Phase 17 amends with active-version selection") is
  vacated; PB-15 closure recorded in Phase 14 design log.
* **Version enumeration is IRI-scan.**
  `MetagraphView.versions_in_role(role) -> set[str]` (~5 LOC; ships
  at Phase 17 retirement) returns the distinct `parse_iri(node_id)
  .version` values observed in the role-graph. `mindsos knowledge
  versions [--role R]` CLI verb is the user-facing surface; Phase
  14 PB-13's `active-version` verb is dropped as vacuous.

**Out-of-scope for amendment-3:**

* The `ref_type="PROMOTED"` breadcrumb (ADR-0051) continues to live
  as a property on Local draft nodes; production-grade reader ships
  symmetric with the L3 promote write capacity at Phase 33 per
  ADR-0146. Phase 16's `list_candidates` already excludes PROMOTED
  defensively; that exclude is the only L2 reader needed before
  Phase 33.
* The ADR-0142 (Proposed) XRef cutover decision is unchanged.
  Cross-metagraph refs continue to live in `ref:global_<role>`
  properties (legacy) and/or XRef rows (post-cutover); version
  dispatch is unrelated.

**Escape clause (mirroring Phase 14a §Q option-(a) amendment-escape
pattern):**

If future pressure surfaces for multi-version coexistence in L2
(e.g., L4 wants `dolce-dul-4.1` and `dolce-dul-4.2` ontology graphs
coexistent under one Global metagraph; or admin-curated rollback
needs prior versions accessible without full re-import), this
amendment may be re-opened via §amendment-N citing:

* the specific use case driving the pressure,
* the impacted ADRs (likely 0042 / 0044 / 0045 / 0149 / this ADR
  §Decision §closure),
* whether the resolution is (a) per-version `Graph` properties
  with one graph per role (less invasive), (b) `(role, version)`
  discriminator with multi-graph-per-role (re-architecture), or
  (c) per-metagraph version maps with admin-set active selection.

The lock is current-best architecture, not eternal architecture.
Future-Claude amending this ADR is invited to challenge the lock if
real evidence of L4/L5 multi-version need surfaces.

**Rationale:**

The Phase 17 row promised an "active-version" surface that the
shipped invariants make vacuous. Three options were on the table at
the retirement chat:

| Option | Shape | Cost | Pick |
|--------|-------|------|------|
| Cosmetic only | IRI-scan enumerator + drop `step(version=)` | ~5 LOC + docs | **shipped** |
| Multi-graph-per-role re-architecture | `(role, version)` discriminator; importer + KL + view + tests cascade | weeks | rejected — re-does Phase 13/14 under "Net-new? No" label |
| `Graph.version` property + active-version map | Adds version slot per graph; KL holds `{role: active_version}` | medium | rejected — still doesn't enable coexistence (one graph per role); equals cosmetic in behaviour |

The cosmetic option matches what shipped invariants already support.
Locking the model formally prevents future chats from re-litigating
the question without explicit evidence of multi-version pressure.

See `halvim_mindsos/confirmation_docs/PHASE_17_RETIREMENT_DESIGN_LOG.md`
for the 4-round retirement design ledger (P1-P3 structural, R1-R7
retirement mechanics, N1-N7 mechanics-of-mechanics, M1-M6 stopping
criterion). See `halvim_mindsos/confirmation_docs/PHASE_14_DESIGN_LOG.md`
§PB-13 + §PB-15 for the retroactive closure amendments.

### amendment-4 (L2 chat — 2026-06-01) — `episodic_memories` rename + Episode/Memory entry-type split

**Trigger:** Chat B (L5 design-resolution, 2026-05-31) D-B48 renamed
the `memories` role-graph to `episodic_memories` and split its single
Memory entry type into two (Episode per-task entry +
Memory-as-clustering-composite) per D-B47 + L5 design notes §4.3 +
§4.6. The L2 chat (2026-06-01) closes the rename event under this
amendment. See `_workbench/L2_CHAT_DECISIONS.md` D-L2-16 + D-L2-17.

**Amended behavior.** The §Decision closed role-set row for `memories`
is renamed and restructured. The role count is unchanged by this
amendment (rename, not addition).

**Renamed row:**

| Scope | Role (was → is) | Schema builder |
|---|---|---|
| Local | ~~`memories`~~ → `episodic_memories` | ~~`build_memories_schema`~~ → `build_episodic_memories_schema(strict)` |

The renamed role hosts two entry types (Episode per-task entry,
Memory-as-clustering-composite) per Chat B D-B47 + D-B48. Storage
discipline `append_only_with_lazy_inline` per L2_CHAT_DECISIONS D-L2-3.
`memory_iri` IRI builder retired; replaced by `episode_iri` +
`memory_composite_iri`. See ADR-0044 §amendment-3 for the
Local-per-user invariant preservation; ADR-0146 §amendment-3 for the
multi-NodeType dispatch shape change forced by the entry-type split.

**Rationale:** Hard rename (no alias, no deprecation window) per
D-L2-16 — old `Memory` and new `Memory` are semantically different
objects (per-task entry vs clustering composite); soft alias is
incoherent because `memory_iri()` cannot map to a single new entry
kind. Codebase is internal; alias window has no users to protect. See
`_workbench/L2_CHAT_DECISIONS.md` D-L2-16 for the rename-vs-alias
rationale chain.

**Out-of-scope for amendment-4:**

* Cross-user `read_other_local` capability for `episodic_memories` —
  routed to L0 chat per L2_CHAT_DECISIONS D-L2-23 (new
  `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` audit constant + new
  capability distinct from generic `READ_OTHER_LOCAL`).

**Split to §amendment-5.** The 4 new role-graphs added under v1
L4-driven expansion (`parameter-staging`, `pending-promotions`,
`capacity-gaps`, `learned-parameters`) + the per-role-graph mutation
discipline framework + the "Explicitly NOT added" exclusion list + the
escape clause for future role additions ship as §amendment-5 at
Phase 43 (Rail A second slot per `POST_PHASE_38_PHASE_MAP.md` + Chat C
IL-3 split decision). The rename event (this amendment) and the
role-graph expansion event are separate architectural events with
separate phases; bundling them in a single amendment as drafted at the
L2 chat closure was the closure's correctness gap, repaired in place
per IL-3 + Phase 39 design pass R0 PB-5.

### amendment-5 (Phase 43 ship — 2026-06-03) — 4 new role-graph rows + exclusion list

**Trigger:** Phase 39 PB-R2-B + Chat C IL-3 (`POST_PHASE_38_PHASE_MAP.md §1` IL-3 row) split the original L2-chat single-bulk §am-4 into two surgical amendments — §am-4 holds the `memories` → `episodic_memories` rename row only (Phase 39 ship); §am-5 holds the 4-new-role-graph expansion + the exclusion list (Phase 43 ship). This split matches the §am-1 / §am-2 / §am-3 precedent of one event per amendment. See `_workbench/L2_CHAT_DECISIONS.md` D-L2-26 + `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §1` IL-3 + `confirmation_docs/PHASE_39_DESIGN_LOG.md` PB-R2-B.

**Amended behavior.**

The §Decision closed role-set expands by 4 named entries. Combined with §am-4's rename row, the post-§am-5 closed role-set is 12 named entries + alignment-prefix.

**New rows added:**

| Scope | Role | Schema builder |
|---|---|---|
| Local | `parameter-staging` | `build_parameter_staging_schema(strict)` |
| Local + Global | `pending-promotions` | `build_pending_promotions_schema(strict)` |
| Global | `capacity-gaps` | `build_capacity_gaps_schema(strict)` |
| Local + Global | `learned-parameters` | `build_learned_parameters_schema(strict)` |

Concrete schema contents per ADR-0152 §3-§6.

**Per-role-graph mutation discipline** for the 4 new roles per ADR-0153 §1:

| Role | Discipline |
|---|---|
| `parameter-staging` | `mutable_with_retention` |
| `pending-promotions` | `audit_only_after_settled` |
| `capacity-gaps` | `mutable_with_retention` |
| `learned-parameters` (Local) | `mutable_with_retention` |
| `learned-parameters` (Global) | `admin_authored` |

**Storage tier.** Among the 4 new role-graphs, only `learned-parameters.LearnedParameter.value` carries a large-payload field warranting an explicit `storage_mode = "falkor_blob"` declaration per ADR-0151 + ADR-0152 §6. `StagedEvidence`, `PendingPromotion`, and `CapacityGap` carry no large-payload fields; no `storage_mode` declaration needed.

**Explicitly NOT added in this amendment (migrated from §am-4):**

- `sense-correlations` — withdrawn; data lives in lexicon empirical layer per `_workbench/L2_CHAT_DECISIONS.md` D-L2-2. ALS subsystem #8 retains the name as a parameter-set label pointing at lexicon-empirical parameter key.
- `world-axioms` — WSD installation chat owns; future amendment row when WSD ships.
- `training-runs` — FOL installation chat owns per Chat A R5 D29; future amendment if FOL accepts.
- `fol-rules`, `fol-ledger` — FOL installation chat owns.

These items were originally listed in §am-4's "Explicitly NOT added" section; they migrate here per Phase 39 PB-R2-B to keep §am-4 narrowed to the rename-only surgical scope.

**Rationale.** The 4 new role-graphs are a single architectural event authored by Chat A + Chat B and closed by the L2 chat. Bulk amendment matches the per-amendment pattern. Splitting from §am-4 (rather than authoring 4 separate §am-5/6/7/8 rows) preserves the event coherence; the §am-4 / §am-5 split is between **rename** (one mechanical change touching identifiers + KL surface) and **expansion** (four schema-shape additions touching the closed role-set bound).

**Out-of-scope for amendment-5:**

* Schema field contents for each new role-graph (locked in ADR-0152 §3-§6).
* Bootstrap topological order field (`applies_after`) ships at Phase 43 per L2-37; the **consumer/scheduler** ships at Phase 44 per L2-37 split.
* `mutation_discipline` placement on the Schema surface — locked in ADR-0153 + §amendment-1 (L2Schema(Schema) subclass placement supersedes §6 L1-Schema text).
* `storage_mode` placement on NodeTypes — per ADR-0151 §Decision + ADR-0152 §6 (per-NodeType-property; not on L2Schema class).

**Escape clause** (preserved from §am-4): Future role additions require new §Revisions entries citing the consumer requirement + schema builder + mutation discipline. Phase 13 sentinel test enforces.

See `confirmation_docs/PHASE_43_R0_PICKS_SEED.md` for the Phase 43 R0 pick chain + cross-references to ADR-0151, ADR-0152, ADR-0153, ADR-0094 §am-1.

### amendment-6 (Phase 50 ship — 2026-06-10) — `installed-skills` role-graph

**Trigger:** SKILL_ACQUISITION_PROCESS_CHAT closure 2026-06-09 (design
log S5, ratified R1 PB-3): skill-bundle install state needs a durable
Global home; the closed role-set had none (probe §0.1-7). Authored at
SA-1 (Phase 50) ship R0 per the design log §5 ADR reservation. Consumer
requirement, schema builder, and mutation discipline cited per the
§am-5 escape clause.

**Amended behavior.**

The §Decision closed role-set expands by 1 named entry. The
post-§am-6 closed role-set is **13 named entries + alignment-prefix**.

**New row added:**

| Scope | Role | Schema builder |
|---|---|---|
| Global | `installed-skills` | `build_installed_skills_schema(strict)` |

**Per-role-graph mutation discipline** per ADR-0153 §1: `append_only`
(design log R2-2 — one `SkillInstallRecord` action record per
install / uninstall / failure event; current state = latest record per
`bundle_name`; no record is ever mutated). Same discipline row as
`problem-trace`.

**Storage tier.** `SkillInstallRecord.value` is a structured dict
(manifest digest + artifact roster + installer outcomes) — the first
production consumer of the ADR-0182 `_value_json` round-trip;
`storage_mode = "inline"` per ADR-0151 (trivial v1 bundles; oversize
fails loud at the ADR-0182 rule-4 persist boundary). Queryable fields
(`bundle_name`, `bundle_version`, `status`, `action`, `recorded_at`)
are lifted flat by the writer per ADR-0182 rule 5.

**Consumer:** the ADR-0183 install driver (writer) +
`apply_installed_skills` activation walk (reader). Concrete lifecycle
semantics in ADR-0183.

**Explicitly NOT added in this amendment:** the §am-5 exclusion list
(`world-axioms`, `training-runs`, `fol-rules`, `fol-ledger`) stands
unchanged — WSD/FOL installation chats own their own future amendment
rows; bundles cannot expand the role-set at install time (design log
S2/S4 — role-set expansion is a code-release + ADR-amendment event,
never bundle content).

### amendment-7 (feat/subminds Slice 1 — 2026-06-24) — `subminds` role-graph

**Backfilled here (2026-07-02) to reconcile the code reference** — the
Slice-1 ship added `ROLE_SUBMINDS` to `_GLOBAL_NAMED_ROLES` and cited
"ADR-0150 §am-7", but the amendment section was not authored at the
time. Authoritative record: `confirmation_docs/SUBMIND_DESIGN_LOG.md`
§19 + ADR-0190.

The §Decision closed role-set expands by 1 named entry (`subminds`).
The post-§am-7 closed role-set is **14 named entries + alignment-prefix**.
The role is **Global + Local by design**; Slice 1 bootstraps the Global
form only (authored, admin-gated endowment). The Local form lands with
the taught-endowment slice (subminds Slice 4).

### amendment-8 (feat/phase1-seam — 2026-07-02) — `task-patterns` gains a Local form

`task-patterns` shipped Global-only (§am-4 / Phase 13), but the general
L2 model is per-role Global **and/or** Local, and the Local→Global
promotion loop that already exists for `promoted-pipelines` /
`learned-parameters` applies equally to task-patterns: a user (or a
consumer such as the arc-solver / mOS-AS) authors and learns patterns in
its **Local** scope, which are then promoted into the shared **Global**
form.

**Amended behavior.** `task-patterns` becomes **dual-scope** — it now
appears in **both** `_GLOBAL_NAMED_ROLES` and `_LOCAL_NAMED_ROLES`
(joining `pending-promotions` + `learned-parameters` as a dual-scope
role). Consequences:

- The lazy Local metagraph auto-ensures a `task-patterns` graph
  (Local named-role count 5 → 6).
- Mutation discipline is unchanged (`immutable_successor`, §am-5 /
  ADR-0153 §1) — new pattern nodes are addable Local; existing nodes are
  never mutated. Local writes need no capability (own-user scope, per
  ADR-0180 `make_writeable`); Global writes still require
  `CAN_WRITE_GLOBAL`.
- `reset_run_state` (ADR-0187) is **unchanged**: task-patterns is
  durable learning, not run-state, so it is retained on reset (the
  `run_state_roles` list is not extended).
- The soft bootstrap edge `episodic_memories ← task-patterns` (Chat B
  D-B47) is now **within-Local-scope**, so the Local `kahn_sort` orders
  task-patterns before episodic_memories (previously cross-scope /
  ignored). No cycle.

**Closed role-set count is UNCHANGED** — this amendment adds no new named
role (task-patterns was already counted at §am-4); it only widens an
existing role's scope. The post-§am-8 closed role-set is still **14
named entries + alignment-prefix**.

**Consumer:** the Phase-1 interpretation seam (ADR-0195) — a consumer's
`map` body returns a `task-pattern:*` IRI it authored in its Local scope,
resolved (Local→Global) at interpretation time. First consumer =
arc-solver (interpretation-only). Reusable by WSD / FOL (many Local
patterns each).

### amendment-9 (joint arc1+arc3 — 2026-07-17) — `dataset:` role prefix (Local-only)

The L2 role vocabulary gains a **second parametric prefix**, `dataset:`,
alongside `alignment:`. It exists so a fully-Local intelligence (a resident
brain) can hold its own reference corpus as a first-class L2 role-graph in its
Local scope. Consumer of record: arc1 (`fetch_task` resolves `"solve task 7"`
against `dataset:arc1`); arc3 next (`dataset:arc3`, Games).

**Why a prefix, not a named role.** A named role has one fixed schema baked
into `_ROLE_SCHEMA_BUILDERS` (`schemas/__init__.py:75-93`). Datasets do not
share a shape — `dataset:arc1` holds `Task` nodes carrying train/test grid
content; `dataset:arc3` holds `Game` nodes carrying only a handle (id +
title, no content). One graph per dataset (L2 is a metagraph; a dataset is a
graph, not a node in a shared graph). A closed named entry cannot represent an
open, per-instance family — the prefix can.

**Why it cannot copy `alignment:`.** `alignment:` is parametric via a single
builder (`build_alignment_schema`, `schema_for_role` short-circuit at
`schemas/__init__.py:116-117`) because every alignment pair-graph has one
shape, and it is **Global-only** at v1 (§am-1). `dataset:` is the inverse on
both axes: **Local-only**, and **per-instance schema** (arc1 ≠ arc3), so the
schema must be **registered**, not built.

**Amended behavior.**

- **Vocabulary.** `dataset:<name>` is a recognized Local role prefix.
  `ensure_local_role_graph` (`bootstrap.py:341-427`) gains a `dataset:`
  branch that resolves the instance schema from the registry and attaches it
  to the freshly-minted graph; `ensure_global_role_graph` rejects `dataset:`
  (Local-only, mirroring how it treats Local-only named roles).
- **Schema registry.** A module-level `register_dataset_schema(name, schema)`
  in `mindsos_knowledge/schemas/` holds a `dataset:<name> → Schema` dict
  parallel to `_ROLE_SCHEMA_BUILDERS`. `schema_for_role` gains a `dataset:`
  branch: registry lookup, **miss → `UnknownRoleError`** (registered schema
  chosen over an unvalidated `strict=False` graph). The registry is
  process-local (schemas are never persisted — `metagraph_repository.py:129`
  stores only `schema_name`); the owning brain re-registers on module import,
  which on the boot path precedes any dataset access
  (`apply_installed_skills` → `boot_local`, `boot.py:151→167`).
- **Discipline.** `append_only` (`_base.py:42`) — a corpus is pure append; an
  entry is never superseded. (Note: `append_only` has no live write-boundary
  enforcement at v1 — `validate_mutation_discipline`, `validators.py:298-387`,
  has no production caller — so this is a declared discipline, matching the
  status of `task-patterns`' `immutable_successor`.)
- **Persistence.** No new machinery. A `dataset:<name>` graph lives inside
  `local_knowledge:<user>`, which `FalkorDBLocalPersister.save`
  (`local_persister.py:160-168`) already round-trips and
  `install_local_metagraph` reloads as-is (`knowledge_layer.py:490-495`,
  "permissive about extra content"). Written once, it reloads for free — the
  corpus is **not** re-materialised per boot.
- **NOT install content.** The corpus is authored by the brain into its own
  Local at first run, not shipped through `manifest.l2_content`. Therefore the
  install preflight (`preflight.py`) — its tier check, its role check, and the
  "role-set expansion is a non-goal" stance (`preflight.py:9-12`) — is
  **untouched**. This amendment does not reverse §am-6's `installed-skills`
  Global-only stance and does not open Local `l2_content`. A dataset is
  brain-owned Local data; you cannot ship it as install content.
- **`reset_run_state` (ADR-0187).** A dataset is durable data, not run-state;
  `run_state_roles` is **not** extended, so a corpus survives reset. (First
  boot after a full `delete` re-imports; a `reset_run_state` retains it.)

**Closed role-set.** No new named role — the named count stays **14**
(unchanged since §am-7). This amendment adds the **second prefix**. The
post-§am-9 closed role-set is **14 named entries + 2 prefixes
(`alignment:`, `dataset:`)**.

**Escape-clause refinement.** The §am-5 escape clause required a new
§Revisions entry per new **named** role. This amendment states the rule for
prefixes precisely: **registered prefixes are accommodated; names are not.** A
new dataset instance (`dataset:arcN`) needs only a `register_dataset_schema`
call by its owning brain — no ADR amendment, no named-role addition, no
sentinel churn. A new *prefix* (a third one) still requires an amendment; a
new *named* role still requires the §am-5 §Revisions entry. The Phase-13
role-count sentinel asserts the named count (14) and the prefix set, so a
stray named-role addition still fails loud.

**Out-of-scope for amendment-9.**

- **No Global `dataset:` form.** Datasets are Local-only at v1; a Global
  dataset (shared corpus) is a future amendment with its own consumer.
- **No Local `installed-skills` form.** The install *record* stays Global
  (§am-6, `installed_skills.py:1-13`); only the corpus is Local. Reopening
  §am-6 is a separate, larger event.
- **The general schema-rehydration gap.** Reloaded graphs are schema-less
  system-wide (loader passes `schema=None`, `metagraph_loader.py:135,258`),
  which silently disables `admin_authored` enforcement for the 6 roles that
  declare it until an explicit per-graph `mindsos graph attach-schema`
  (`graph.py:998`). Pre-existing; not introduced or fixed here. `dataset:`
  uses `append_only` (unenforced regardless), so it is unaffected.

**Consumer.** arc1 `fetch_task` (D1.6) reads `dataset:arc1` out of Local L2;
the resolve chain `[arc_resolve, fetch_task]` composed by `find_pipeline`
inside `interpret()` (`phase_1.py:137-175`) replaces arc1's current
closed-over Python `dataset` dict. arc3 (`dataset:arc3`, Games) is the second
consumer. The one-time corpus import trigger is a new absence-guarded step in
`boot_local` (CR §7-A / P-2) — the ADR-0183 §am-1 runtime-entry mechanism
(`records.py::skill_entries`, `mindsos brain execute`) was evaluated and
**rejected** for this: it is a manual, single-start, solve-pipeline verb
(`brain.py:581`), not an automatic first-run data-load, and it is itself a
*reader* of the corpus.

### amendment-10 (feat/skill-local-caps — 2026-07-28) — `installed-capacities` role-graph

Adds one **named** Local role, `installed-capacities`, the per-user store for
installed-skill Local capability **descriptors** (one dict node per capability:
`name`/`category`/`inputs`/`outputs`, `reactivation_key`, `params`,
`installed_by`). ADR-0183 §am-5 registers capabilities from these descriptors at
boot (metadata-only; function built on first use).

**Why a named role.** One fixed shape (all entries are capability descriptors),
so a single-schema named role fits — unlike the per-instance `dataset:` prefix.
Kept distinct from `learned-parameters` (user-*learned* params) so installed-app
provenance is separate and uninstall/upgrade can target it by role + tag.

**Scope.** **Local-only** (`ensure_global_role_graph` rejects it); auto-ensured on
Local mint/install (added to `_LOCAL_NAMED_ROLES`); persisted/reloaded by the
existing Local persister with no new machinery. Mutable
(`mutable_with_retention`) — descriptors are rewritten on upgrade, removed on
uninstall.

**Closed role-set update.** Named count **15 → 16**; prefixes unchanged
(`alignment:`, `dataset:`). The Phase-13 dispatch sentinel + `_ALL_NAMED_ROLES`
and the ALL_ROLES / dispatch-table count assertions across
`tests/{phase_12,phase_13,phase_14,phase_25,phase_34,phase_39,phase_44,dataset_role,learned_pipelines,phase_50,feat_subminds}` move to
16. Revises §am-9's "named count stays 14/15" to 16.

**Out of scope.** No Global `installed-capacities` form (Local-only at v1). Does
not reopen §am-6's Global-only install-record scope — only the capability
descriptors are Local.

## Source

Phase 13 design log §1 PB-19 (Flavor A vs Flavor B closure question);
Phase 13 PB-23 (number reserved for Phase 14a content drafting); Phase
14a chat transcript rounds 1-3 — PB-A (synthesis-vs-structural
narrowing → A2), PB-E (title rename → E2), PB-Q (Decision wording
option (a) — amendment escape hatch retained). See
`halvim_mindsos/confirmation_docs/PHASE_13_DESIGN_LOG.md` §1 +
Phase 14a chat transcript captured by Phase 14a's PR.

### amendment-11 (CORE-C2R1 — 2026-07-31) — `installed-skills` gains a Local form

**Trigger.** ADR-0205 §8 makes the **Skill** the unit of structural change and states that
**a user installs one**; an admin promotes it to Global. `installed-skills` shipped
Global-only at §am-6 on the earlier reading that skill installs are admin-gated Global
actions (SKILL_ACQUISITION design log S3). That reading no longer holds.

**What actually made install admin-only.** Not `CAN_INSTALL_SKILL`. Every write in
`mindsos_server/skills/` was hardcoded to `scope="global"`, and the ADR-0180
`make_writeable` gate guards Global writes with `CAN_WRITE_GLOBAL`. The **destination** was
the gate, not the capability — which is why a capability named "may install a skill" existed
and could not be granted to anyone usefully.

**Amended behavior.**

`installed-skills` becomes **dual-scope**, joining `pending-promotions`,
`learned-parameters` and `request-patterns`. **The closed role-set count is unchanged** — an
existing role gains a scope, exactly the §am-8 precedent for `request-patterns`. It remains
**16 named entries + 2 prefixes** (`alignment:`, `dataset:`).

| Scope | Role | Schema builder | Discipline |
|---|---|---|---|
| Global | `installed-skills` | `build_installed_skills_schema(strict)` | `append_only` |
| **Local** | `installed-skills` | *same builder* | `append_only` |

**One schema serves both scopes.** Unlike `learned-parameters`, whose forms differ in
mutation discipline, an install record is an action record in either realm, so
`build_installed_skills_schema` takes no `scope` kwarg.

**Writes are scope-parameterised.** `append_record`, `install_skill` and `uninstall_skill`
take a `scope`, defaulting to **`"local"`**. The default narrows rather than widens: a Global
install still requires `CAN_WRITE_GLOBAL` at the ADR-0180 gate, so admin promotion is
unchanged and no new write path exists.

**Reads union both realms.** `iter_skill_records`, `latest_records_by_bundle` and
`skill_entries` take an optional `user_id` and walk Global first, then that user's Local, so
a Local record shadows a Global one of the same bundle name (the `LocalPreferringView`
precedent — a user's own install state governs for that user). `seq` is minted across the
**unioned** set, so install order stays one sequence per principal and activation replays in
it regardless of realm.

**Every reader is scope-aware, and this is load-bearing.** `apply_installed_skills`,
`run_preflight`, `boot_brain` and five CLI call sites all pass `user_id`. Threading the write
half alone would have shipped a Skill a user could install and that **nothing would ever see**
— not activated at boot, not counted as a satisfied dependency, absent from the CLI.

**Capabilities.** `CAN_INSTALL_SKILL` and `CAN_UNINSTALL_SKILL` move into `USER_CAPS` — see
ADR-0002 §amendment-3. `USER_CAPS` is non-empty for the first time.

**Out-of-scope for amendment-11:** promotion of a Local install record to Global (the admin
path exists as `scope="global"`, but *promotion of an existing Local record* is skill-packaging
work); Local-artifact reverse-dependency on uninstall (the guard still covers
`requires_bundles` only); and the **skill ledger**, which the skill-packaging chat owns.
