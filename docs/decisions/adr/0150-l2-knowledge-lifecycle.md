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

### amendment-4 (L2 chat — 2026-06-01) — v1 L4-driven role-graph expansion + `episodic_memories` rename

**Trigger:** Chat A (L4 design-resolution, 2026-05-28) + Chat B (L5
design-resolution + note-fork decision, 2026-05-31) together authored
a substantial L2 role-graph expansion required by the v1 L4 substrate.
The L2 chat (2026-06-01) closes this expansion under a single
amendment per the amendment-escape pattern (round-3 PB-Q option (a))
established by this ADR. See `_workbench/L2_CHAT_DECISIONS.md` D-L2-26
for the per-decision rationale.

**Amended behavior.**

The §Decision closed role-set is expanded from 9 entries (8 named +
alignment-prefix) to 13 entries (12 named + alignment-prefix). The
`memories` row is renamed and restructured. Sense-correlations is
explicitly NOT added (lexicon empirical-layer instead — see
`_workbench/L2_CHAT_DECISIONS.md` D-L2-2).

**Renamed row:**

| Scope | Role (was → is) | Schema builder |
|---|---|---|
| Local | ~~`memories`~~ → `episodic_memories` | ~~`build_memories_schema`~~ → `build_episodic_memories_schema(strict)` |

New role hosts two entry types (Episode, Memory-as-clustering-composite)
per Chat B D-B47 + D-B48. Storage discipline:
`append_only_with_lazy_inline` per L2_CHAT_DECISIONS D-L2-3.
`memory_iri` IRI builder retired; replaced by `episode_iri` +
`memory_composite_iri`. See ADR-0044 §amendment-3 for the rename
trigger + Local-per-user invariant preservation.

**New rows added:**

| Scope | Role | Schema builder |
|---|---|---|
| Local | `parameter-staging` | `build_parameter_staging_schema(strict)` |
| Local + Global | `pending-promotions` | `build_pending_promotions_schema(strict)` |
| Global | `capacity-gaps` | `build_capacity_gaps_schema(strict)` |
| Local + Global | `learned-parameters` | `build_learned_parameters_schema(strict)` |

Post-amendment closed role-set: 12 named entries + alignment-prefix.
`UnknownRoleError` (Phase 13 PB-11) continues to gate any role outside
this list at runtime; `register_role(...)` continues to not exist.

**Per-role-graph mutation discipline** is now a Schema-level
declaration per L2_CHAT_DECISIONS D-L2-3 (v1 disciplines:
`immutable_successor`, `append_only_with_lazy_inline`,
`mutable_with_retention`, `audit_only_after_settled`, `admin_authored`).
Discipline assignment for each role-graph is recorded in
L2_CHAT_DECISIONS D-L2-3 and enforced at `KnowledgeLayer.bootstrap()`.

**Explicitly NOT added in this amendment:**

- `sense-correlations` — withdrawn; data lives in lexicon empirical
  layer per L2_CHAT_DECISIONS D-L2-2. ALS subsystem #8 retains the
  name as a parameter-set label pointing at lexicon-empirical
  parameter key.
- `world-axioms` — WSD installation chat owns; future
  ADR-0150 amendment row when WSD ships.
- `training-runs` — FOL chat owns per Chat A R5 D29; future amendment
  if FOL accepts.
- `fol-rules`, `fol-ledger` — FOL chat owns.

**Rationale:** Chat A + Chat B authored these together; L2 chat
closes. v1 L4-driven role-graph expansion is a single architectural
event. Bulk amendment matches this ADR's per-amendment pattern
(§am-1 = single decision; §am-2 = single correction; §am-3 = single
retirement). Per-role mini-amendments would fragment a coherent event
into 5+ amendments citing each other. See L2_CHAT_DECISIONS D-L2-26
for the rejected alternative (per-role mini-ADRs) and reasoning.

**Out-of-scope for amendment-4:**

* Schema field contents for each new role-graph (locked in ADR-0152
  L2 role-graph schema v2 bundle).
* Promoted-pipelines `confidence` field removal (ADR-0094 §amendment-1
  separately tracks).
* HAS_STEP / PipelineStep shape under L1/L3 reframe (D38 routing);
  L2-25 schema-v2 partial lock per L2_CHAT_DECISIONS D-L2-6
  accommodates either reframe outcome.
* Cross-user `read_other_local` capability for `episodic_memories` —
  routed to L0 chat per L2_CHAT_DECISIONS D-L2-23.

**Escape clause** (per round-3 PB-Q option (a) — preserved):

Future role additions (e.g., `world-axioms` when WSD installation
ships, `training-runs` if FOL accepts) require new §Revisions entries
on this ADR naming the new role, citing the consumer requirement, and
listing the new schema builder + mutation discipline. The Phase 13
sentinel `tests/phase_13/test_dispatch.py` is the enforcement
surface; bypassing it bypasses this ADR.

See `MindsOS/docs/_workbench/L2_CHAT_DECISIONS.md` D-L2-26 for the
amendment rationale chain and routed-out items inventory.

## Source

Phase 13 design log §1 PB-19 (Flavor A vs Flavor B closure question);
Phase 13 PB-23 (number reserved for Phase 14a content drafting); Phase
14a chat transcript rounds 1-3 — PB-A (synthesis-vs-structural
narrowing → A2), PB-E (title rename → E2), PB-Q (Decision wording
option (a) — amendment escape hatch retained). See
`halvim_mindsos/confirmation_docs/PHASE_13_DESIGN_LOG.md` §1 +
Phase 14a chat transcript captured by Phase 14a's PR.
