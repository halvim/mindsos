"""Fixtures for the L0-side half of ADR-0210 slice 2.

Mirrors the phase conftest pattern (``tests/phase_18/conftest.py``): a tmp
``server.db`` migrated to the current version, plus the two sessions every
capability-gated verb needs — one holding the capability and one without it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest


@pytest.fixture()
def tmp_server_db(tmp_path: Path) -> Iterator:
    from mindsos_server._db import open_db
    from mindsos_server._schema import init_or_migrate

    with open_db(tmp_path / "server.db") as conn:
        init_or_migrate(conn)
        conn.execute(
            "INSERT INTO users (user_id, password_hash, actor_role, disabled, "
            "created_at) VALUES ('alice', 'x', 'user', 0, '2026-09-06T00:00:00.000Z')"
        )
        conn.commit()
        yield conn


@pytest.fixture()
def alice():
    """A user holding the default bundle, which includes the capability."""
    from mindsos_server.session import Session

    return Session.for_testing("alice")


@pytest.fixture()
def alice_without_the_capability():
    """The same user with the capability withheld — the state an admin
    creates by declining it, and the denial path's only fixture."""
    from mindsos_server.capabilities import CAN_INSTALL_SKILL
    from mindsos_server.session import Session

    return Session.for_testing("alice", capabilities={CAN_INSTALL_SKILL})
