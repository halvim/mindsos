"""
KL-side structural types per ADR-0040.

Phase 25 first ship. The :class:`SessionProtocol` is the duck-typed shape
KL (and Capacity, later) consume in lieu of importing the concrete
:class:`mindsos_server.session.Session` dataclass.

ADR-0010 §I-S1 forbids ``mindsos_knowledge`` from importing
``mindsos_server`` at module load. KL write-API methods (when they
land in a later phase) accept a session-shaped argument typed against
this Protocol, treat it as opaque, and never instantiate one. Tests
exercising those methods pass either a real
:class:`mindsos_server.session.Session` (the test-shim
:meth:`Session.for_testing` per ADR-0013) or any structurally-matching
object.

The Phase 18 :class:`mindsos_server.session.Session` dataclass and this
Protocol MUST stay structurally aligned. The Phase 25
``tests/phase_25/test_session_protocol_satisfied.py`` test enforces the
match at CI time via ``isinstance(real_session, SessionProtocol)`` —
``runtime_checkable`` Protocols make this assertion cheap and reliable.

This module is the ONLY public surface in ``mindsos_knowledge`` that
references a session shape; the import-isolation test
``tests/phase_25/test_import_isolation_phase25.py`` asserts no
``from mindsos_server`` / ``import mindsos_server`` statements appear
anywhere in the ``mindsos_knowledge`` package.

See ADR-0040 for the structural-typing rationale and
``confirmation_docs/PHASE_25_DESIGN_LOG.md`` §4 + §5 for ship-phase
context.
"""

from __future__ import annotations

from typing import Iterable, Literal, Protocol, runtime_checkable

__all__ = ["SessionProtocol"]


@runtime_checkable
class SessionProtocol(Protocol):
    """
    Duck-typed Session shape per ADR-0040 §Decision.

    Structural counterpart to :class:`mindsos_server.session.Session`.
    KL imports this Protocol; KL never imports the concrete dataclass.

    Attributes:
        session_id: Stable per-issuance identifier (opaque to KL).
        user_id: User identity — charset-constrained at the server.
        actor_role: ``"user"`` or ``"admin"`` (informational; enforcement
            is via :meth:`has` per ADR-0046).
        capabilities: Iterable of capability constants the session
            holds. Server's concrete shape is ``frozenset[str]``; the
            Protocol relaxes to ``Iterable[str]`` so structural matches
            (e.g., L3 test doubles) aren't forced to a frozenset.

    Methods:
        has: Membership check against ``capabilities``. KL write-API
            gates call ``session.has(CAN_WRITE_*)`` — the actor_role
            field is never the gate per ADR-0046.
    """

    session_id: str
    user_id: str
    actor_role: Literal["user", "admin"]
    capabilities: Iterable[str]

    def has(self, capability: str) -> bool: ...
