"""
mindsos_server — Server Layer (L0).

Phase 18 — Server: user store + auth.
Phase 19 — Server: sessions (login / logout / session_from_token /
kill_my_own_sessions; sessions table + v2 migration).
Phase 20 — Server: admin reset (reset_admin lock-out recovery in
new mindsos_server/admin.py module; UserNotFoundError +
NotAnAdminError target-validation gate; first-fires EVT_KILL_SESSION
+ EVT_ADMIN_ENABLE_USER from the Phase 18 audit roster).
Phase 21 — Server: audit log reader (admin_query_audit + AuditRow in
admin.py; new mindsos_server/authz.py module with _require_or_audit
wrapper + PermissionDeniedError; EVT_AUDIT_QUERY happy-path audit
emission; schema v2→v3 with idx_audit_target).

Introduces the first L0 package per ADR-0001 at Phase 18. Sits ABOVE
every domain layer (Core → Knowledge → Capacity → Intelligence →
Mental Model) in the dependency DAG; per ADR-0010 §I-S1, domain layers
must NOT import this package.

Phase 18 ships (preserved):

* **User store** — SQLite-backed (`server.db`) `users` table per ADR-0004;
  argon2id password hashing per ADR-0003; charset-constrained `user_id`
  inherited verbatim from KL per ADR-0044 §amendment-1 + Phase 18 PB-7.
* **`Session` dataclass + `Session.for_testing`** — minimal shape matching
  the KL-side SessionProtocol (ADR-0040) verbatim per Phase 18 PB-33;
  frozen + frozenset capabilities per ADR-0002.
* **Capability roster** — the seven UPPER-case capability constants from
  ADR-0002 per Phase 18 PB-4 + PB-12 (USER_CAPS strictly empty in v1).
* **Audit substrate** — `audit` table + full ADR-0013 event-constant
  enum + `write_audit` writer; ISO-8601 UTC ms timestamps per PB-35.
* **Bootstrap helper + CLI verb** — `_insert_first_admin` +
  `mindsos server bootstrap` (lifted from Phase 20 per Phase 18 PB-27 /
  ADR-0012 §amendment-1).
* **Migration framework** — forward-only DDL + `schema_version` row +
  `init_or_migrate(conn)` per PB-2.

Phase 19 adds:

* **`sessions` table** at schema v2 — 5 columns (`session_id`, `user_id`,
  `token_hash`, `created_at`, `last_seen_at`); `expires_at` computed at
  lookup per PB-10 + ADR-0004 §amendment-1.
* **`login(conn, user_id, password, *, ttl, params) -> LoginResult`** —
  verify-then-lazy-expire-then-concurrent-check-then-mint per PB-8 +
  ADR-0005 §amendment-1.
* **`session_from_token(conn, token, *, ttl) -> Session`** — indexed
  SHA-256 equality lookup per ADR-0003 §amendment-1; sliding refresh;
  lazy expiry with InvalidSessionError on expired or not-found per
  PB-14.
* **`logout(conn, token) -> bool`** — by-token self-logout per PB-11;
  silent no-op on invalid token.
* **`kill_my_own_sessions(conn, user_id, password, *, ttl, params)
  -> int`** — ADR-0005 escape valve; deletes all sessions for the user
  after fresh-credentials verify.
* **`SessionTTL(sliding_seconds, absolute_seconds)`** +
  `PRODUCTION_TTL` (8h / 24h) + `_TEST_FAST_TTL` (1s / 2s) per PB-12.
* **`InvalidSessionError` + `InvalidSessionCause` enum** unifying
  expired-sliding / expired-absolute / not-found per PB-14 (replaces
  ADR-0003 §Decision's `SessionExpiredError`).
* **`AlreadyLoggedInError`** with 2-field payload per PB-3 +
  ADR-0005 §amendment-1.
* **`users.verify()` revision** per PB-9 + ADR-0013 §amendment-1 —
  pure predicate; callers own the audit emission.

Phase 19 does NOT ship: `LocalPersister` + `MetagraphDump` (Phase 25
per PB-2 / ADR-0011 §amendment-1 — supersedes Phase 18 PB-18);
`MindsOSServer` orchestrator class (Phase 25 per PB-13); reset-admin
or last-admin protection (Phase 20); audit query reader (Phase 21);
cross-user reads or password change (Phase 22); promotion (Phase 24);
KL-side SessionProtocol seam + KL capability constants (Phase 25);
sweeper thread (future HTTP daemon phase per PB-4); `source` field
on `AlreadyLoggedInError` (future HTTP daemon phase per PB-3).

See ``confirmation_docs/PHASE_18_DESIGN_LOG.md`` for the Phase 18
38-pick ledger and ``confirmation_docs/PHASE_19_DESIGN_LOG.md`` for
the Phase 19 15-pick ledger.
"""

from mindsos_server.capabilities import (
    ADMIN_CAPS,
    ALL_CAPABILITIES,
    CAN_APPROVE_RELEASE,
    CAN_HARD_DELETE_ARCHIVED,
    CAN_KILL_SESSION,
    CAN_MANAGE_USERS,
    CAN_PROMOTE,
    CAN_PROPOSE_MUTATION,
    CAN_READ_OTHER_LOCALS,
    CAN_VIEW_AUDIT_LOG,
    CAN_WRITE_GLOBAL,
    USER_CAPS,
)
from mindsos_server.admin import (
    AuditRow,
    DemoteUserResult,
    DisableUserResult,
    EnableUserResult,
    HardDeleteUserResult,
    KillSessionResult,
    PromoteUserResult,
    ResetAdminResult,
    _assert_not_sole_admin,
    admin_demote_user,
    admin_disable_user,
    admin_enable_user,
    admin_kill_session,
    admin_promote_user,
    admin_query_audit,
    admin_tx,
    hard_delete_user,
    reset_admin,
)
from mindsos_server.audit import (
    EVT_ADMIN_DEMOTE_USER,
    EVT_ADMIN_DISABLE_USER,
    EVT_ADMIN_ENABLE_USER,
    EVT_ADMIN_PROMOTE_USER,
    EVT_AUDIT_QUERY,
    EVT_HARD_DELETE_USER,
    EVT_PROMOTION_PROPOSED,
    EVT_PROMOTION_REJECTED,
    EVT_RELEASE_FAILED,
    EVT_RELEASE_SHIPPED,
)
from mindsos_server.locks import RELEASE_SHIP_LOCK, UserMutexRegistry
from mindsos_server.release import ReleaseResult, ReleaseStatus, release_update
from mindsos_server.authz import _require_or_audit
from mindsos_server.errors import (
    AlreadyAnAdminError,
    AlreadyLoggedInError,
    AuthFailedError,
    InvalidSessionCause,
    InvalidSessionError,
    LastAdminError,
    NotAnAdminError,
    PermissionDeniedError,
    SessionNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from mindsos_server.session import Session
from mindsos_server.sessions import (
    PRODUCTION_TTL,
    LoginResult,
    SessionTTL,
    kill_my_own_sessions,
    login,
    logout,
    session_from_token,
)
from mindsos_server.users import User

__all__ = [
    "__version__",
    # Session + auth surfaces (Phase 18 PB-33 + PB-13 + PB-24).
    "Session",
    "User",
    # Capability roster (Phase 18 PB-4 + PB-12; ADR-0002).
    "CAN_READ_OTHER_LOCALS",
    "CAN_WRITE_GLOBAL",
    "CAN_PROMOTE",
    "CAN_HARD_DELETE_ARCHIVED",
    "CAN_KILL_SESSION",
    "CAN_VIEW_AUDIT_LOG",
    "CAN_MANAGE_USERS",
    "USER_CAPS",
    "ADMIN_CAPS",
    # Exceptions (Phase 18 PB-23 + PB-30; Phase 19 PB-3 + PB-14;
    # Phase 20 PB-N + PB-O; Phase 21 PB-14; Phase 22 R1 PB-3 + R2 PB-13 +
    # R3 PB-23).
    "AuthFailedError",
    "UserAlreadyExistsError",
    "InvalidSessionError",
    "InvalidSessionCause",
    "AlreadyLoggedInError",
    "UserNotFoundError",
    "NotAnAdminError",
    "PermissionDeniedError",
    "LastAdminError",
    "AlreadyAnAdminError",
    "SessionNotFoundError",
    # Phase 19 sessions surface (PB-6 + PB-11 + PB-12 + PB-13 + PB-15).
    "login",
    "logout",
    "session_from_token",
    "kill_my_own_sessions",
    "LoginResult",
    "SessionTTL",
    "PRODUCTION_TTL",
    # Phase 20 admin surface (PB-Z module + PB-A/D/E/G/R/U semantics).
    "reset_admin",
    "ResetAdminResult",
    # Phase 21 audit-reader surface (PB-6 + PB-8 + PB-9 + PB-16).
    "admin_query_audit",
    "AuditRow",
    "_require_or_audit",
    "EVT_AUDIT_QUERY",
    # Phase 22 admin-ops surface (R1 PB-2 admin subgroup + 6 verbs;
    # R1 PB-7 _assert_not_sole_admin helper; R4 PB-24 admin_tx wrapper).
    "admin_promote_user",
    "admin_demote_user",
    "admin_disable_user",
    "admin_enable_user",
    "admin_kill_session",
    "hard_delete_user",
    "PromoteUserResult",
    "DemoteUserResult",
    "DisableUserResult",
    "EnableUserResult",
    "KillSessionResult",
    "HardDeleteUserResult",
    "_assert_not_sole_admin",
    "admin_tx",
    "EVT_ADMIN_PROMOTE_USER",
    "EVT_ADMIN_DEMOTE_USER",
    "EVT_ADMIN_DISABLE_USER",
    "EVT_ADMIN_ENABLE_USER",
    "EVT_HARD_DELETE_USER",
    # Phase 24 release-ship surface (ADR-0118 + ADR-0114 + ADR-0115
    # + ADR-0006 §am1 + ADR-0002 §am2).
    "CAN_PROPOSE_MUTATION",
    "CAN_APPROVE_RELEASE",
    "ALL_CAPABILITIES",
    "RELEASE_SHIP_LOCK",
    "UserMutexRegistry",
    "release_update",
    "ReleaseResult",
    "ReleaseStatus",
    "EVT_PROMOTION_PROPOSED",
    "EVT_PROMOTION_REJECTED",
    "EVT_RELEASE_SHIPPED",
    "EVT_RELEASE_FAILED",
]

__version__ = "0.0.0+phase24"
