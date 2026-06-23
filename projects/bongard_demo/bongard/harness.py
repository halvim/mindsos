"""Demo boot harness — a standalone in-memory MindsOS instance.

Milestone-1 perception is read-only and needs no durable persistence, so
the harness builds a fresh ``CapacityLayer`` (Global auto-built by
``create_global``) and a minimal Local-scoped session. This mirrors the
F9 test pattern (``tests/f9/_fixtures.DuckSession``): the Local
register/invoke path uses only ``session.user_id``.

Milestone-2 (mint + "survives a restart") will swap this for the F9
durable path (``mindsos_server.local_boot.boot_local`` over a
``FalkorDBLocalPersister``); that is deliberately out of scope here.
"""

from __future__ import annotations

from typing import Tuple

from mindsos_capacity import CapacityLayer

from .ontology import register_ontology

#: Default Local user for the single-instance demo.
DEFAULT_USER = "bongard"


class DuckSession:
    """Minimal Local-scoped session.

    The Local register/invoke path reads only ``user_id`` (it never calls
    ``.has()`` — that is the Global-write capability gate). Mirrors
    ``tests/f9/_fixtures.DuckSession``.
    """

    def __init__(self, user_id: str = DEFAULT_USER) -> None:
        self.user_id = user_id
        self.session_id = f"sess-{user_id}"

    def has(self, _cap) -> bool:  # pragma: no cover - never hit on Local path
        return False


def build_instance(
    user_id: str = DEFAULT_USER,
) -> Tuple[CapacityLayer, DuckSession]:
    """Construct a fresh in-memory instance with the ontology registered.

    Returns ``(cl, session)``. The CapacityLayer's Global is freshly
    bootstrapped; the bongard ontology atoms are registered into the
    user's Local DataState graph. Perception capacities and the control
    loop register on top of this (subsequent milestone-1 tasks).
    """
    cl = CapacityLayer()
    session = DuckSession(user_id)
    register_ontology(cl, session)
    return cl, session
