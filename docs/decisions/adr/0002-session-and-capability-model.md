# ADR-0002: Session-plus-capability authorization model

- **Status:** Accepted
- **Date:** 2026-04-22
- **Related:** ADR-0001, ADR-0005, ADR-0013

## Context

Every write into KL, every admin action, and every upper-layer call against a user's Local needs a uniform way to answer "is this caller allowed to do this?" The prior design used a single `is_admin: bool`, which couldn't express fine-grained authority (e.g., "read other Locals, but not promote them") and left no room for future separation of duties.

We also needed an answer for authority that persists across a login but expires, and that bundles the user identity, role, and permission set in a single object that domain layers can treat opaquely.

## Decision

Authorization is expressed as a `Session` object bundling:

- `user_id: str` — identity.
- `actor_role: Literal["user", "admin"]` — coarse role label (informational; capabilities are the enforcement mechanism).
- `capabilities: frozenset[str]` — the actual gate.

Seven capabilities are defined in `mindsos_server.capabilities`:

| Capability | Grants |
| --- | --- |
| `CAN_READ_OTHER_LOCALS` | Admin cross-user read via `read_other_local()` context manager |
| `CAN_WRITE_GLOBAL` | Direct writes into Global-scope role graphs (rare; most Global writes go through promote) |
| `CAN_PROMOTE` | Invoke `similarity_report()` and `promote()` |
| `CAN_HARD_DELETE_ARCHIVED` | `hard_delete_user` and similar destructive ops |
| `CAN_KILL_SESSION` | `admin_kill_session` (evict another user's session) |
| `CAN_VIEW_AUDIT_LOG` | `admin_query_audit` |
| `CAN_MANAGE_USERS` | Create/promote/demote/disable/enable/list users |

Two standard bundles: `USER_CAPS` (empty for now; reserved for future per-user grants) and `ADMIN_CAPS` (all seven).

Every privileged endpoint calls `authz.require(session, CAP)` or the wrapper `_require_or_audit(session, CAP)` which emits a `PERMISSION_DENIED` audit row on denial and raises `PermissionDeniedError` (HTTP 403).

## Rationale

- **Fine-grained separation of duties.** Different admin roles can be issued subsets (e.g., an auditor holding only `CAN_VIEW_AUDIT_LOG`) without re-plumbing.
- **Frozenset for immutability.** A `Session` is immutable after issue; permissions can't drift mid-request.
- **String constants, not enums.** Keeps parity trivial between `mindsos_server.capabilities` and the test-side assertion that the capability strings match across layers.
- **Audit on denial.** A failed check is a security event worth recording, not an exception to swallow.

## Consequences

- Every new privileged endpoint must declare its capability before it can be called.
- Tests build sessions with `Session.for_testing(user_id, is_admin=True)` to get `ADMIN_CAPS` without touching SQLite.
- Capability strings are now part of the stable API surface; renaming them is a breaking change.
- A future "role templates" layer (read-only admin, break-glass admin) slots in cleanly as named capability bundles.

## Alternatives considered

1. **Single `is_admin: bool`.** Rejected — the concerns review identified at least four admin actions that should be grantable independently (promote, read, delete, manage users).
2. **RBAC with role inheritance.** Over-engineered for current needs; capability sets are strictly more expressive and require no tree traversal.
3. **ACLs on resources.** Rejected — Globals, Locals, and audit rows are uniform enough that a flat capability model covers them without per-row policies.

## Revisions

### amendment-1 (Phase 18 ship — 2026-05-21) — documentary: USER_CAPS strictly empty in v1; UPPER casing locked

**Trigger:** Phase 18 ships the canonical capability roster at
`mindsos_server/capabilities.py`. Two cross-ADR ambiguities surfaced
during the round-2 ADR audit:

1. **Casing inconsistency.** ADR-0002 §Decision spells constants
   UPPER (`CAN_READ_OTHER_LOCALS`); ADR-0041 §Decision + ADR-0046
   §Decision spell them lower (`can_read_other_locals`). Capability
   strings are wire-format-equivalent (`session.has("…")`), so casing
   IS load-bearing.
2. **Bundle membership.** ADR-0118 (Proposed) introduces
   `CAN_PROPOSE_MUTATION` + `CAN_APPROVE_RELEASE`. ADR-0137 (Proposed)
   introduces `CAN_REQUEST_PROMOTION` (user default per its §Capabilities)
   + `CAN_REVIEW_PROMOTION_REQUESTS`. ADR-0137 §Capabilities contradicts
   ADR-0002's "`USER_CAPS = frozenset()`" — but ADR-0137 is Proposed,
   not Accepted.

**Amended behavior:**

* **UPPER casing is canonical.** All seven capability constants ship at
  Phase 18 as UPPER (matching ADR-0002 §Decision). ADR-0041 + ADR-0046
  documentary §amendment-1 entries record the alignment. Renaming any
  constant is a breaking change going forward.
* **`USER_CAPS = frozenset()` strict in v1.** Proposed-status caps from
  ADR-0118 + ADR-0137 do NOT ship at Phase 18; they land at their
  Accept-flip phase (24 / 25), at which point those ADRs' amendments
  add the new constants to the roster + update `USER_CAPS` /
  `ADMIN_CAPS` membership accordingly.

**Rationale:** Phase 18 PB-4 + PB-12 picked strict ADR-0002 conformance
to avoid pre-shipping caps for Proposed decisions that may still change
shape during Phase 24/25 design. UPPER matches Python module-level
constant convention (PEP 8) and is more grep-able as a "this is a
capability string" marker than the lower-case alternative.

**Out-of-scope:** the four KL-side capability constants per ADR-0041
(subset of the seven) ship at Phase 25 when
`mindsos_knowledge/capabilities.py` lands. Phase 18 ships the
server-side parity test
(`tests/phase_18/test_capabilities_parity.py`) — the KL-side
comparison subtests skip on ImportError until Phase 25.

See `halvim_mindsos/confirmation_docs/PHASE_18_DESIGN_LOG.md` §1
rounds 1-2 PB-4 + PB-5 + PB-12 for the round-by-round rationale.

### amendment-2 (Phase 24 ship — 2026-05-22) — +CAN_PROPOSE_MUTATION + CAN_APPROVE_RELEASE; roster 7 → 9; CAN_READ_PENDING_GLOBAL deferred

**Trigger:** Phase 24 ships `mindsos_admin/promotion.py::propose_for_
promotion` (admin-direct ATOM) + `mindsos_server/release.py::release_
update` per ADR-0118 + ADR-0141 + ADR-0144 §am2. Two new capabilities
gate these surfaces; one inferred third cap (CAN_READ_PENDING_GLOBAL)
has no direct-read consumer at Phase 24 and defers.

**Amended roster (7 → 9 capabilities):**

| Capability | Grants | Phase shipped |
| --- | --- | --- |
| `CAN_READ_OTHER_LOCALS` | Admin cross-user read via `read_other_local()` context manager | 18 (declared); 25 (first consumer) |
| `CAN_WRITE_GLOBAL` | Direct writes into Global-scope role graphs (rare) | 18 |
| `CAN_PROMOTE` | Invoke `similarity_report()` and `promote()` (vestigial in halvim per ADR-0138 / ADR-0141 §am1; cap retained for compatibility) | 18 |
| `CAN_HARD_DELETE_ARCHIVED` | `hard_delete_user` and similar destructive ops | 18 (declared); 22 (first consumer) |
| `CAN_KILL_SESSION` | `admin_kill_session` (evict another user's session) | 18 (declared); 22 (first consumer) |
| `CAN_VIEW_AUDIT_LOG` | `admin_query_audit` | 18 (declared); 21 (first consumer) |
| `CAN_MANAGE_USERS` | Create/promote/demote/disable/enable/list users | 18 (declared); 22 (first consumer) |
| **`CAN_PROPOSE_MUTATION`** | Invoke `mindsos_admin.propose_for_promotion()` per ADR-0118 / ADR-0141 §am1 | **24 (declared + first consumer)** |
| **`CAN_APPROVE_RELEASE`** | Invoke `mindsos_server.release_update()` per ADR-0118 / ADR-0115 | **24 (declared + first consumer)** |

`ADMIN_CAPS` extends from 7 to 9 members; `USER_CAPS` stays empty
(strict per §am1).

**Capability deferred to a future phase:**

| Capability | Grants | Reason for defer |
| --- | --- | --- |
| `CAN_READ_PENDING_GLOBAL` | Read access to `mindsos_pending_global_<role>` FalkorDB graphs (per PIVOT §7.2) | Phase 24 audit gate is server-internal (no independent session check inside the gate; outer caller already validated CAN_APPROVE_RELEASE). No direct-read consumer at Phase 24. Lands at first direct-read consumer phase (admin pending-inspection verb v2, or Phase 25 if `MindsOSServer` needs it). |

**Capability rename consideration deferred:** `CAN_APPROVE_RELEASE`
at v1 semantic = "can ship a release" (no separate approve step per
ADR-0118 §Tradeoffs override-path-is-v2). v2 quorum-approve will
extend the semantic to actual approve-vs-ship distinction; the cap
name is forward-compatible without rename. Per §Consequences
"renaming them is a breaking change," the cap stays as named.

**Rationale:** Phase 24 design log PB-23(a) picked 2-caps-not-3 per
YAGNI; `CAN_READ_PENDING_GLOBAL` ships when first direct consumer
ships (no audit-gate-internal call counts as direct consumer).

**Coordinated changes at Phase 24 ship:**

* `mindsos_server/capabilities.py` — `+CAN_PROPOSE_MUTATION +
  CAN_APPROVE_RELEASE` constants; `ADMIN_CAPS` extends; `ALL_
  CAPABILITIES` extends.
* `tests/phase_24/test_capability_denial_propose.py` + `test_
  capability_denial_release.py` — assert PermissionDeniedError
  raised + EVT_PERMISSION_DENIED audit row for non-admin caller.
* `tests/phase_18/test_capabilities_parity.py` (Phase 18 baseline
  test) — auto-extends via dynamic-baseline pattern per
  `feedback_phase_baseline_literal_audit.md` (count derived from
  `ALL_CAPABILITIES` length, not hardcoded literal).

**Phase 24 design log:** `halvim_mindsos/confirmation_docs/PHASE_24_
DESIGN_LOG.md` §1 Round 4 PB-23 (2-caps-not-3 lock) + §4 ADR delta.
