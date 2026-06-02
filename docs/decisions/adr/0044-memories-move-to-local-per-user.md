---
title: Memories move from Global to Local per user
status: Accepted
date: 2026-04-22
layer: L2
aliases: [kl-ADR-007]
---

# ADR-0044: Memories move from Global to Local per user

**Status:** Accepted

**Date:** 2026-04-22

## Context

The initial upper-layer roles design put `memories` in Global, arguing that cross-user pattern distillation was easier. But: (1) a user's raw task history is autobiographical data, not systemic knowledge; (2) cross-user patterns should be *distilled* into `promoted-pipelines` / `task-patterns` (Global), not derived by scanning raw memories.

## Decision

The `memories` role lives in each user's Local metagraph. Memory IRIs bake in the user_id (`memories-<v>:memory:<user_id>:<memory_id>`). `capacity-state` follows the same rule (per-user Local). `promoted-pipelines`, `task-patterns`, and `problem-trace` remain Global.

## Consequences

**Good:**
- A user's Local metagraph is a single-tenant artifact; load/save is clean per-user.
- Cross-user pattern extraction becomes an explicit admin workflow (promote into Global), not implicit scan.

**Bad:**
- Every upper-layer consumer that reads memories needs the user's Local installed.
- The IRI builders had to be extended to include user_id.

## Alternatives considered

Keep memories in Global with explicit Global promotion pathway — rejected because it mixes autobiographical + systemic knowledge.

## Revisions

### amendment-1 (Phase 12 ship — 2026-05-16) — `user_id` charset locked at IRI-builder layer

**Trigger:** ADR-0044 declares `memories-<v>:memory:<user_id>:<memory_id>` but does not pin the `user_id` charset. Phase 12 ships the L2 IRI builder `memory_iri(version, user_id, memory_id)` (and `capacity_snapshot_iri(version, user_id, capacity_iri, taken_at)`, which inherits the same `user_id` slot per ADR-0044's "capacity-state follows the same rule"). Without a charset constraint, a `user_id` containing `:` would silently break `parse_iri` (the body would split ambiguously). Phase 18 (Server: user store + auth) is the next downstream consumer and would either inherit the looseness or retrofit a tighter contract.

**Amended behavior:**

* `user_id` MUST match the regex `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`.
* `mindsos_knowledge.identifiers._ensure_user_id(user_id)` enforces this at builder call time; `memory_iri` and `capacity_snapshot_iri` call it. Violation raises `mindsos_knowledge.RefFormatError`.
* Phase 18 server user-store creation MUST inherit the same charset for `user_id` validation (preserves the IRI-parseability invariant end-to-end).

**Rationale:** Matches the state-file `<name>` regex Phase 03 §3 (24-character alphanumeric-plus-`_-`, leading-char restricted) — a contract pattern already proven across the codebase. Keeps `:` (parser separator), whitespace, and any high-Unicode codepoints out of the IRI body so `parse_iri` can split safely without per-role escape rules.

**Out-of-scope for amendment-1:** server-side `user_id` collision policy (Phase 18); cross-tenant user_id isolation (Phase 22); UUID-as-user_id convention (consumer choice — the regex accepts both UUIDs with hyphens and shorter human-readable identifiers).

See `halvim_mindsos/confirmation_docs/PHASE_12_DESIGN_LOG.md` §PB-11 + §PB-17 for the decision rationale and `mindsos_knowledge/identifiers.py:_USER_ID_RE` for the canonical regex.

### amendment-2 (Phase 18 ship — 2026-05-21) — server inherits `_USER_ID_RE` via import; ADR-0010 permits direction

**Trigger:** §amendment-1 mandates that "Phase 18 server user-store
creation MUST inherit the same charset for `user_id` validation".
Phase 18 design pass evaluated three implementation options
(PB-7):

1. Duplicate the regex constant in `mindsos_server.users` + ship a
   parity test asserting equality with KL (mirrors ADR-0041 pattern).
2. Import `_USER_ID_RE` directly from `mindsos_knowledge.identifiers`.
3. Move the regex into a shared `mindsos_contracts` package
   (rejected by ADR-0010 §Alternatives §2).

**Amended behavior:** Phase 18 PB-7 picked option (2). The server
imports `_USER_ID_RE` from `mindsos_knowledge.identifiers` directly:

```python
# mindsos_server/users.py — Phase 18
from mindsos_knowledge.identifiers import _USER_ID_RE
```

**Rationale:** ADR-0010 §I-S1 forbids only the KL → server direction
("KL must not import `mindsos_server`"). The reverse direction
(server → KL) is permitted; ADR-0010 §Consequences notes that
domain layers stay installable standalone (no server dep), not that
the server must stay KL-free. Direct import keeps a single source of
truth for the regex; duplicate-with-parity is a workaround for
layer-isolation, not warranted here.

**Downstream:** `mindsos_server` pyproject lists `mindsos_knowledge`
as a hard runtime dep per Phase 18 PB-25.

See `halvim_mindsos/confirmation_docs/PHASE_18_DESIGN_LOG.md` §1
rounds 1-3 PB-7 + PB-25 for the dep-edge rationale.

### amendment-3 (L2 chat — 2026-06-01) — role rename `memories` → `episodic_memories` + entry-type restructure

**Trigger:** Chat B (L5 design-resolution, 2026-05-31) D-B48 renamed
the role-graph from `memories` to `episodic_memories` and
restructured it from a single Memory entry type to two entry types
(Episode + Memory-as-clustering-composite) per D-B47 + L5 design
notes §4.3 + §4.6. The L2 chat (2026-06-01) closes the rename + the
shipped-surface migration plan; see `_workbench/L2_CHAT_DECISIONS.md`
D-L2-16 + D-L2-17 + D-L2-25.

**Amended behavior:**

* **Role name:** `memories` → `episodic_memories`. Closed role-set
  per ADR-0150 §amendment-4.
* **Entry types:** single `Memory` (pre-amendment) → two entry types
  per Chat B locks:
  - **Episode** — per-task entry; frozen full MM + outcome
    classification; immutable externally; lazy inline-on-retire is
    the only permitted internal mutation (D-B17 + L2_CHAT_DECISIONS
    D-L2-3 `append_only_with_lazy_inline` discipline).
  - **Memory** — clustering composite over Episodes, keyed by
    `task_pattern_iri`. Materializes on first episode of a task-
    pattern; subsequent episodes attach via
    `memory_contains_episode` IntergraphEdge (NOT an embedded list;
    Chat B PB-VV).
* **IRI builders:**
  - `memory_iri(version, user_id, memory_id)` **retired**.
  - **NEW** `episode_iri(version, user_id, episode_id)` — Local-per-
    user; `user_id` charset per §amendment-1 unchanged.
  - **NEW** `memory_composite_iri(version, user_id, memory_id)` —
    Local-per-user; `user_id` charset per §amendment-1 unchanged.
* **Local-per-user binding PRESERVED.** Episodes + memories are
  always Local. No Global L5 per Chat B D-B4 + L5 design notes §1.3.
  Cross-user learning travels via ALS (`parameter-staging` →
  `learned-parameters`), not via memory promotion. ADR-0118 per-user
  transactional promotion semantics carry forward unchanged for any
  episode/memory promotion (single-episode-per-promotion granularity
  per Chat B PB-3).
* **Bootstrap discipline:** schema-only bootstrap importer per
  Chat B D-B49. Per-user Local references schema at first task; no
  Global seed content.
* **`user_id` charset (§amendment-1) and server import discipline
  (§amendment-2) unchanged.** Both new builders enforce
  `_USER_ID_RE` at builder-call time; `mindsos_server` continues to
  import `_USER_ID_RE` directly.

**Migration plan (hard rename, atomic; no alias):**

* Constant rename: `ROLE_MEMORIES` → `ROLE_EPISODIC_MEMORIES` in
  `mindsos_knowledge/identifiers.py`. Atomic PR; all imports updated
  in same change (no alias-with-deprecation window).
* `_PREFIXES` entry `"memories-"` → `"episodic-memories-"`.
* `_KINDS_PER_ROLE` entries for new role: `frozenset({"episode",
  "memory"})`.
* Schema file: `schemas/memories.py` → `schemas/episodic_memories.py`;
  exports updated in `schemas/__init__.py`.
* `_IRI_BUILDERS` dispatch table entry renamed and split (one entry
  per new IRI builder).
* Shipped Phase 33 `consolidate:mm` L3 capacity
  (`mindsos_capacity/builtins/consolidate.py`) retargets new
  Episode entry shape; symmetric write contract per ADR-0146 /
  ADR-0147 preserved.
* Phase 12 / 14 / 25 / 33 / 34 / 36 test fixtures renamed atomically.
* Maintenance migration script (Chat C plan-authoring scope) handles
  any pre-rename `memories-*:memory:<u>:<m>` IRIs found in
  pre-production user data; v1 production has none (L4 substrate is
  in design — see HANDOFF §3.1).

**Rationale (hard rename vs alias):**

* Old `Memory` and new `Memory` are semantically *different* objects
  with overlapping names (per-task entry vs clustering composite).
  Soft alias is incoherent because `memory_iri()` cannot map to a
  single new entry kind.
* Codebase is internal; no external consumers; alias window has no
  users to protect.
* Phase 33 `consolidate:mm` writes through `KLWriteHandle` per
  ADR-0143; atomic migration is one-PR-scoped.

**Out-of-scope for amendment-3:**

* Cross-user `read_other_local` capability for `episodic_memories`
  — routed to L0 chat per L2_CHAT_DECISIONS D-L2-23 (new
  `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` audit constant + new
  capability distinct from generic `READ_OTHER_LOCAL`).
* Episode/Memory composite *internal* schemas — locked by Chat B
  D-B47 + L5 design notes §4.3 + §4.6; L2 chat scope is the
  role-graph registration + bootstrap + container lifecycle only.
* Episode retention policy fine-tuning (PB-QQ in Chat B) — deferred
  to v1.5 if storage growth surfaces.

See `MindsOS/docs/_workbench/CHAT_B_DECISIONS.md` D-B17 + D-B47 +
D-B48 + D-B49 for the Chat B locks and
`_workbench/L2_CHAT_DECISIONS.md` D-L2-16 + D-L2-17 + D-L2-25 for
the L2-side closure + migration plan rationale.
