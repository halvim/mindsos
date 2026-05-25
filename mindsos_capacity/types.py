"""Typing surface for session-bearing arguments into the L3 write API.

Phase 28 first ship — slim port of the parent reference layout. The
parent's ``types.py`` (313 LOC) ships a full deprecation shim
(``_resolve_session_arg`` + ``_LocalTestSession`` + ``_make_test_session``
+ bare-``str`` / ``Mapping``-shaped session migration paths). Halvim has
zero callers of that machinery — every test uses
:meth:`mindsos_server.session.Session.for_testing` directly — so the
shim is dead-code in halvim.

Phase 28 ships ONLY:

* :class:`SessionProtocol` — the structural protocol L3 accepts (mirror
  of :class:`mindsos_knowledge.types.SessionProtocol` per
  ADR-0040 §amendment-2).
* :data:`SessionArg` — the type alias L3 method signatures use
  (``Optional[SessionProtocol]``).

Phase 33 (write-API expansion) is the slot to add ``_resolve_session_arg``
+ ``_LocalTestSession`` IF a richer resolver becomes necessary; until
then the slim file stays slim.

**Why a Protocol and not an ABC.** Protocols are structural: anything
that quacks like a session (has ``session_id``, ``user_id``,
``actor_role``, ``capabilities``, and ``.has(capability)``) counts. The
alternative — importing :class:`mindsos_server.session.Session` as a
base class — would break layer isolation (ADR-0010 §I-S1). The parity
of the capability *string* is verified separately by
:mod:`mindsos_capacity.capabilities`.

**Why L3's own Protocol instead of L2's.** ADR-0040 §amendment-2
(Phase 28) explicitly defers re-export from
:mod:`mindsos_knowledge.types`. L3 stays library-installable without
bootstrapping L2's import graph (mirrors the REF_TYPES duplication
rationale in ADR-0067 §amendment-1).
"""

from __future__ import annotations

from typing import Iterable, Literal, Optional, Protocol, runtime_checkable

__all__ = ["SessionProtocol", "SessionArg"]


@runtime_checkable
class SessionProtocol(Protocol):
    """Shape L3 accepts for the ``session`` argument.

    Matches the shape produced by
    :class:`mindsos_server.session.Session` without importing it.
    Identical structure to :class:`mindsos_knowledge.types.SessionProtocol`
    per ADR-0040 §amendment-2 (Phase 28 ship). Every field is read-only
    from L3's perspective; L3 never mutates a session it was handed.

    Attributes:
        session_id: Opaque identifier for the session instance. L3 uses
            it only in log / error messages.
        user_id: The acting user. Used for Local-scope routing and as
            the provenance stamp on writes (``created_by``).
        actor_role: Coarse-grained role tag. L3 treats ``"admin"`` and
            ``"user"`` identically at the method surface; fine-grained
            authorization happens through :meth:`has` with a specific
            capability string per ADR-0046.
        capabilities: Iterable of capability strings the server bound
            onto the session. L3 inspects this through :meth:`has`.

    Methods:
        has: Membership check against ``capabilities``. L3 write-API
            gates call ``session.has(CAN_WRITE_GLOBAL)``; the
            ``actor_role`` field is never the gate per ADR-0046.
    """

    session_id: str
    user_id: str
    actor_role: Literal["user", "admin"]
    capabilities: Iterable[str]

    def has(self, capability: str) -> bool:
        """Return ``True`` if ``capability`` is present on the session."""
        ...


SessionArg = Optional[SessionProtocol]
"""Type alias used in :class:`mindsos_capacity.CapacityLayer` method
signatures during Phase 28 ship.

Accepts either a real :class:`SessionProtocol`-satisfying object (the
canonical path; tests use ``Session.for_testing(...)``) or ``None`` (the
ADR-0080 bootstrap carve-out — pre-server admin / library callers).

Phase 33 may widen this alias when a richer resolver lands; the alias
form keeps the widening single-site.
"""
