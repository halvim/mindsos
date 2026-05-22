"""
mindsos_server — Server Layer (L0).

Phase 18 — Server: user store + auth.
Phase 19 — Server: sessions (login / logout / session_from_token /
kill_my_own_sessions; sessions table + v2 migration).
Phase 20 — Server: admin reset (reset_admin lock-out recovery in
new mindsos_server/admin.py module; UserNotFoundError +
NotAnAdminError target-validation gate; first-fires EVT_KILL_SESSION
+ EVT_ADMIN_ENABLE_USER from the Phase 18 audit roster).

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
    CAN_HARD_DELETE_ARCHIVED,
    CAN_KILL_SESSION,
    CAN_MANAGE_USERS,
    CAN_PROMOTE,
    CAN_READ_OTHER_LOCALS,
    CAN_VIEW_AUDIT_LOG,
    CAN_WRITE_GLOBAL,
    USER_CAPS,
)
from mindsos_server.admin import ResetAdminResult, reset_admin
from mindsos_server.errors import (
    AlreadyLoggedInError,
    AuthFailedError,
    InvalidSessionCause,
    InvalidSessionError,
    NotAnAdminError,
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
    # Phase 20 PB-N + PB-O).
    "AuthFailedError",
    "UserAlreadyExistsError",
    "InvalidSessionError",
    "InvalidSessionCause",
    "AlreadyLoggedInError",
    "UserNotFoundError",
    "NotAnAdminError",
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
]

__version__ = "0.0.0+phase20"
