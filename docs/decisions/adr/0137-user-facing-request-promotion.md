---
title: User-facing request_promotion API
status: Proposed
date: 2026-04-27
layer: Server
amends: [0118]
---

# ADR-0137: User-facing `request_promotion` API

**Status:** Proposed

**Date:** 2026-04-27

**Amends:** ADR-0118 (per-user transactional promotion + release-boundary atomicity — admin-only `propose_for_promotion` extended with user-initiated `request_promotion` upstream).

**Related:** PIVOT §7.1 (admin-only propose), PIVOT §7.9 (admin candidate-discovery deferred to v2).

## Context

ADR-0118 + PIVOT §7.1 specify `propose_for_promotion` as admin-only. Users author drafts in their Local but have no API to push their work toward Global. The intended path: admin browses every user's Local, finds promotion candidates, calls `propose_for_promotion(source_user_id=user)`.

PIVOT §7.9 defers admin candidate-discovery tooling (similarity-based search, frequency-based ranking) to v2.

The L1 redesign critique (N6) raised the resulting UX problem: with no candidate-discovery tool and no user-initiated path, admins have to scan every Local manually. At 10 users × 100 drafts each = 1000 candidates per release, this is hostile UX. The user picked option (2) — reopen the API surface and add a user-initiated path.

## Decision

Add `request_promotion` as an ordinary-user API. The flow becomes:

1. **User authors a draft** in their Local (existing).
2. **User calls `request_promotion`** identifying the draft they want promoted, with a justification.
3. The request lands in a new `promotion_requests` table in `server.db`.
4. **Admin reviews requests** via `admin_list_promotion_requests` and either:
   - **Approves** → admin's review action calls `propose_for_promotion(source_user_id=request.user_id, ...)` populating the proposal from the request.
   - **Rejects** → request status becomes `REJECTED`; user sees rejection (with reason) on their next read via `kl.list_my_promotion_requests`.

### API shape

```python
# User-facing (KL):
kl.request_promotion(
    session: SessionProtocol,
    draft_id: str,
    justification: str,
    *,
    target_role: str | None = None,   # which role-graph this is for; KL infers from draft if None
) -> PromotionRequest

kl.list_my_promotion_requests(
    session: SessionProtocol,
    *,
    status: PromotionRequestStatus | None = None,
) -> list[PromotionRequest]

kl.withdraw_promotion_request(
    session: SessionProtocol,
    request_id: int,
) -> None  # user can withdraw their own request before admin acts

# Admin-facing (server):
server.admin_list_promotion_requests(
    admin_session: SessionProtocol,
    *,
    status: PromotionRequestStatus | None = None,
    user_id: str | None = None,
) -> list[PromotionRequest]

server.admin_review_promotion_request(
    admin_session: SessionProtocol,
    request_id: int,
    decision: Literal["approve", "reject"],
    review_note: str,
) -> PromotionRequest
```

When `decision="approve"`, the server constructs a `PromotionProposal` from the request and calls `propose_for_promotion` internally. The user's draft is frozen (per ADR-0118) at that point.

### Capabilities

Two new capabilities:

- `CAN_REQUEST_PROMOTION` — user default; lets the user call `request_promotion`.
- `CAN_REVIEW_PROMOTION_REQUESTS` — admin default; lets the admin call `admin_list_promotion_requests` and `admin_review_promotion_request`.

Both join the existing capability registry (per ADR-0002 + pivot ADR-0115's enum).

### Storage

```sql
CREATE TABLE promotion_requests (
    request_id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,                       -- requester
    draft_id TEXT NOT NULL,                      -- node id in user's Local
    target_role TEXT NOT NULL,                   -- role-graph this is for
    justification TEXT NOT NULL,
    status TEXT NOT NULL,                        -- 'PENDING' | 'WITHDRAWN' | 'APPROVED' | 'REJECTED'
    requested_at TIMESTAMP NOT NULL,
    reviewed_by_admin_user_id TEXT,
    review_decision TEXT,
    review_note TEXT,
    reviewed_at TIMESTAMP,
    resulting_pending_mutation_id INTEGER,       -- FK to pending_mutations when approved
    audit_event_id INTEGER NOT NULL,
    FOREIGN KEY (resulting_pending_mutation_id)
        REFERENCES pending_mutations (mutation_id)
);

CREATE INDEX promotion_requests_user_id ON promotion_requests (user_id);
CREATE INDEX promotion_requests_status ON promotion_requests (status);
```

Lives in `server.db` alongside the existing `users`, `sessions`, `audit_log` tables.

### Audit events

Two new entries in the `AuditEventType` enum (per ADR-0115's enum file):

- `PROMOTION_REQUEST_SUBMITTED` (user submits)
- `PROMOTION_REQUEST_WITHDRAWN` (user withdraws before admin acts)
- `PROMOTION_REQUEST_APPROVED` (admin approves; precedes `MUTATION_PROPOSED`)
- `PROMOTION_REQUEST_REJECTED` (admin rejects)

All audit events carry `request_id` plus the standard `user_id` / `admin_user_id` fields.

### What this is NOT

- **Not candidate discovery.** PIVOT §7.9's deferred tooling (similarity search, frequency ranking) is still v2. `request_promotion` is *user push*; candidate-discovery would be *admin pull*.
- **Not a separate atomicity model.** Approved requests flow through `propose_for_promotion` exactly as if admin originated them. The atomicity boundaries from ADR-0118 are unchanged.
- **Not auto-approval.** Admin still reviews every request. The mechanism just gives users a discoverable path to surface their work.

## Rationale

PIVOT §7.1's "no user-facing propose" was the v1 default because it kept the surface small and avoided spec questions about user authorisation for cross-user promotion. The L1 redesign's N6 pushback identified that the cost of *no user push* + *no candidate discovery* is admin manual scanning — which is a UX failure mode at any non-trivial user count.

`request_promotion` is the cheapest fix: it adds a queue admins review, with the same atomicity model downstream. It doesn't open new authorisation questions (admin still gates everything) and doesn't duplicate the propose path.

The alternative (defer everything to v2 candidate-discovery) bets that admin manual scanning will be acceptable in v1. That bet is risky once user count exceeds 5–10.

## Consequences

**Good:**

- Users can surface their work for promotion without admin manually finding it.
- The admin's review queue is structured (`promotion_requests` table) instead of "scan every Local."
- Audit trail captures user intent (`PROMOTION_REQUEST_SUBMITTED` with justification) — useful for the audit gate's impact report.
- The mechanism composes with v2's candidate-discovery: discovery would surface candidates *to admin* via similarity/frequency; `request_promotion` surfaces candidates *from user* via explicit submission. Two complementary paths.

**Tradeoffs:**

- New table in `server.db`; new audit events; new capability constants. ~150 LOC + tests.
- Admin review queue can grow unbounded if admins ignore it. Mitigation: `mindsos-server promotion-requests --pending --older-than=30d` CLI surfaces stale requests; v2 may add auto-rejection of stale requests.
- A user who submits and the admin ignores has a stuck request. UX issue; mitigated by `withdraw_promotion_request`.
- Implementation depends on KL's user-Local being installed (request points at a `draft_id` in the user's Local). LocalRegistry (per ADR-0125) handles lazy hydration.

**Coordinated changes:**

- `mindsos_server/promotion_requests.py` (new) — `PromotionRequest` dataclass, store layer.
- `mindsos_server/server.py` — `admin_list_promotion_requests`, `admin_review_promotion_request` endpoints.
- `mindsos_knowledge/knowledge_layer.py` — `request_promotion`, `list_my_promotion_requests`, `withdraw_promotion_request`.
- `mindsos_server/capabilities.py` — `CAN_REQUEST_PROMOTION`, `CAN_REVIEW_PROMOTION_REQUESTS`. KL mirror per ADR-0010.
- `mindsos_server/audit_events.py` — four new event types.
- `mindsos_server/cli.py` — `promotion-requests` subcommand.
- `mindsos_server/version_db/schema.py` — actually `server.db` schema; the `promotion_requests` table lives in `server.db`, not the version_db (it's auth/lifecycle, not release manifest).
- Tests: `tests_server/integration/test_request_promotion.py`.
- Documentation: `docs/usage/server/promotion.md` (user request flow), `docs/usage/knowledge/writing.md` (user-side example), `docs/api/server/server.md` (new admin endpoints), `docs/api/knowledge/knowledge-layer.md` (new KL methods).

## Alternatives considered

1. **Defer entirely to v2 candidate-discovery (status quo per PIVOT §7.9).** Rejected — admin manual scanning is hostile UX; cost of inaction grows with user count.
2. **Direct user-initiated propose** (user calls `propose_for_promotion`). Rejected — opens user-authorisation question (can a user push to Global on their own?). Atomicity contract from ADR-0118 stays; admin still gates.
3. **No queue; user emails admin.** Rejected (frivolous). Mentioned only because it's literally the v1 fallback.
4. **Forum/comment style with upvotes.** Rejected — over-engineered; v1 doesn't need social mechanics.
5. **Auto-promote requests that pass audit gate.** Rejected — bypasses admin curation, which is the point of the release model.

## Implementation references

- New: `mindsos_server/promotion_requests.py`, `mindsos_knowledge/promotion_requests.py` (or extend KL facade).
- Modified: `mindsos_server/server.py`, `mindsos_server/capabilities.py`, `mindsos_server/audit_events.py`, `mindsos_server/cli.py`.
- KL: `mindsos_knowledge/knowledge_layer.py` (three new methods).
- Tests: `tests_server/integration/test_request_promotion.py`.
- Documentation: `docs/usage/server/promotion.md`, `docs/usage/knowledge/writing.md`, `docs/api/server/server.md`, `docs/api/knowledge/knowledge-layer.md`.

ADR moves from Proposed to Accepted when KL `request_promotion` lands, server review endpoints land, and `docs/usage/server/promotion.md` documents the user-initiated flow.
