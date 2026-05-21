"""
mindsos_server — Server Layer (L0).

Phase 18 — Server: user store + auth.

Introduces the first L0 package per ADR-0001. Sits ABOVE every domain layer
(Core → Knowledge → Capacity → Intelligence → Mental Model) in the dependency
DAG; per ADR-0010 §I-S1, domain layers must NOT import this package.

Phase 18 ships:

* **User store** — SQLite-backed (`server.db`) `users` table per ADR-0004;
  argon2id password hashing per ADR-0003; charset-constrained `user_id`
  inherited verbatim from KL per ADR-0044 §amendment-1 + Phase 18 PB-7.
* **`Session` dataclass + `Session.for_testing`** — minimal shape matching
  the KL-side SessionProtocol (ADR-0040) verbatim per Phase 18 PB-33;
  frozen + frozenset capabilities per ADR-0002.
* **Capability roster** — the seven UPPER-case capability constants from
  ADR-0002 per Phase 18 PB-4 + PB-12 (USER_CAPS strictly empty in v1;
  Proposed-status caps from ADR-0118 / ADR-0137 defer to their
  Accept-flip phase).
* **Audit substrate** — `audit` table + full ADR-0013 event-constant enum
  upfront per Phase 18 PB-34; `write_audit` writer; ISO-8601 UTC
  timestamps per Phase 18 PB-35.
* **Bootstrap helper + CLI verb** — `_insert_first_admin` (pure insert) +
  `mindsos server bootstrap` (idempotent CLI wrapper). Bootstrap CLI
  verb is lifted from Phase 20 to Phase 18 per PB-27 / ADR-0012
  §amendment-1.
* **Migration framework** — forward-only DDL + `schema_version` row +
  `init_or_migrate(conn)` per Phase 18 PB-2; v1 ships `users` + `audit`
  tables; v2 (Phase 19) adds `sessions`.

Phase 18 does NOT ship: sessions / login / tokens (Phase 19); LocalPersister
or MetagraphDump (Phase 19 per PB-18); reset-admin or last-admin protection
(Phase 20); audit query reader (Phase 21); cross-user reads or password
change (Phase 22); promotion (Phase 24); KL-side SessionProtocol seam +
KL capability constants (Phase 25).

See ``confirmation_docs/PHASE_18_DESIGN_LOG.md`` for the full 38-pick
design ledger.
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
from mindsos_server.errors import (
    AuthFailedError,
    UserAlreadyExistsError,
)
from mindsos_server.session import Session
from mindsos_server.users import User

__all__ = [
    "__version__",
    # Session + auth surfaces (PB-33 + PB-13 + PB-24).
    "Session",
    "User",
    # Capability roster (PB-4 + PB-12; ADR-0002).
    "CAN_READ_OTHER_LOCALS",
    "CAN_WRITE_GLOBAL",
    "CAN_PROMOTE",
    "CAN_HARD_DELETE_ARCHIVED",
    "CAN_KILL_SESSION",
    "CAN_VIEW_AUDIT_LOG",
    "CAN_MANAGE_USERS",
    "USER_CAPS",
    "ADMIN_CAPS",
    # Exceptions (PB-23 + PB-30).
    "AuthFailedError",
    "UserAlreadyExistsError",
]

__version__ = "0.0.0+phase18"
