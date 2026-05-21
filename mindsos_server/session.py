"""
Session dataclass for the Server Layer.

Minimal shape matching the KL-side SessionProtocol (ADR-0040) verbatim
per Phase 18 PB-33. Frozen + immutable; capabilities stored as
``frozenset[str]`` per ADR-0002.

Phase 18 ships:

* The concrete dataclass with four fields (``session_id``, ``user_id``,
  ``actor_role``, ``capabilities``) + the ``has(cap)`` method.
* :meth:`Session.for_testing` shim per ADR-0013 — returns a Session with
  ``ADMIN_CAPS`` or ``USER_CAPS`` based on ``is_admin`` without touching
  SQLite, argon2, or the login path.

Phase 18 does NOT ship: timestamp fields (``created_at`` /
``last_seen_at`` / ``expires_at`` live on the ``sessions`` table at
Phase 19, not on the Session object — see PB-33 rationale); token data;
session lookup / revoke / refresh paths.

The KL-side SessionProtocol at ``mindsos_knowledge/types.py`` (Phase 25
first consumer per ADR-0040) MUST structurally match this dataclass.
The Phase 18 ``tests/phase_18/test_capabilities_parity.py`` asserts the
server-side roster shape; the KL-side structural match is enforced when
Phase 25 ships the Protocol.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Literal

from mindsos_server.capabilities import ADMIN_CAPS, USER_CAPS


@dataclass(frozen=True, slots=True)
class Session:
    """
    Authorization session.

    Per ADR-0002 + ADR-0040 + Phase 18 PB-33:

    * Immutable after construction (``frozen=True``).
    * ``capabilities`` is a ``frozenset[str]`` of capability constants
      (see :mod:`mindsos_server.capabilities`).
    * ``actor_role`` is informational; enforcement is always via
      :meth:`has` against a specific capability per ADR-0046.

    Constructed at Phase 19 ``login()``; ``for_testing`` shim ships at
    Phase 18 per ADR-0013 so KL / L3 / Phase 18 unit tests can build
    Sessions without exercising SQLite + argon2.
    """

    #: Stable per-issuance identifier. Phase 19 generates via
    #: ``secrets.token_urlsafe`` for real sessions; ``for_testing`` uses
    #: a synthetic "test-<user_id>" form per ADR-0013.
    session_id: str

    #: User identity — charset-constrained per ADR-0044 §amendment-1
    #: (regex enforced at user-creation time by
    #: :func:`mindsos_server.users.insert_user`).
    user_id: str

    #: Coarse role label; informational per ADR-0002. Enforcement uses
    #: :meth:`has` against the capability set, not this field.
    actor_role: Literal["user", "admin"]

    #: Capability set — frozenset of constants from
    #: :mod:`mindsos_server.capabilities`. Immutable after construction
    #: per ADR-0002 §Rationale ("Frozenset for immutability — permissions
    #: can't drift mid-request").
    capabilities: frozenset[str] = field(default_factory=frozenset)

    def has(self, capability: str) -> bool:
        """
        Capability check. Returns True iff ``capability`` is in this
        session's capability set.

        Per ADR-0046 — admin enforcement is capability-based, not
        role-string-based. Server endpoints call ``session.has(CAP)``
        (or the audit-emitting ``_require_or_audit`` wrapper, Phase 21+);
        the ``actor_role`` field is never the gate.
        """
        return capability in self.capabilities

    @classmethod
    def for_testing(
        cls,
        user_id: str,
        *,
        is_admin: bool = False,
        session_id: str | None = None,
        capabilities: Iterable[str] | None = None,
    ) -> "Session":
        """
        Test-only constructor per ADR-0013 §Decision.

        Returns a Session whose capabilities default to ``ADMIN_CAPS`` if
        ``is_admin=True`` else ``USER_CAPS``. Touches no SQLite, runs no
        argon2, issues no token — bypasses the entire login path.

        ``session_id`` defaults to ``"test-<user_id>"`` per ADR-0013's
        "stable synthetic session_id" requirement. Callers who need a
        specific id can pass one.

        ``capabilities`` overrides the role-default bundle when set —
        used by tests that need to exercise a specific cap combination
        without using a full ADMIN bundle (e.g., "user with only
        ``CAN_VIEW_AUDIT_LOG``" for an auditor-role test).

        Convention per ADR-0013 §Consequences: only for tests; review
        catches stray production usage. Technically callable from
        production code; the discipline is human, not enforced.
        """
        if capabilities is not None:
            caps = frozenset(capabilities)
        else:
            caps = ADMIN_CAPS if is_admin else USER_CAPS

        return cls(
            session_id=session_id if session_id is not None else f"test-{user_id}",
            user_id=user_id,
            actor_role="admin" if is_admin else "user",
            capabilities=caps,
        )
