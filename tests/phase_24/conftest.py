"""Shared fixtures for Phase 24 tests.

Extends the Phase 22 conftest shape. Adds:

* :func:`admin_session_propose` — admin session with CAN_PROPOSE_MUTATION.
* :func:`admin_session_release` — admin session with CAN_APPROVE_RELEASE.
* :func:`admin_session_both` — admin with both Phase 24 caps + Phase 22 baseline.
* :func:`non_admin_session` — USER_CAPS empty (denial-path tests).
* :func:`canonical_global_mg` — canonical-Global Metagraph from
  ``bootstrap_global(importers=())``.
* :func:`pending_global_mg` — pending-Global Metagraph from
  ``bootstrap_pending_global(canonical_global_mg)``.
* :func:`seeded_admin_with_proposer` — admin row 'admin-caller' inserted.
* :func:`atom_proposal_factory` — helper for building one-item ATOM
  PromotionProposals against a target_role.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from mindsos_admin import (
    NodeSpec,
    PromotionItem,
    PromotionItemKind,
    PromotionProposal,
    bootstrap_global,
    bootstrap_pending_global,
)
from mindsos_server._argon2 import _TEST_FAST_PARAMS, Argon2Params
from mindsos_server._db import open_db
from mindsos_server._schema import init_or_migrate
from mindsos_server.capabilities import (
    ADMIN_CAPS,
    CAN_APPROVE_RELEASE,
    CAN_PROPOSE_MUTATION,
)
from mindsos_server.session import Session
from mindsos_server.users import _insert_first_admin


@pytest.fixture()
def fast_params() -> Argon2Params:
    return _TEST_FAST_PARAMS


@pytest.fixture()
def tmp_server_db_path(tmp_path: Path) -> Path:
    return tmp_path / "server.db"


@pytest.fixture()
def tmp_server_db(tmp_server_db_path: Path) -> Iterator:
    with open_db(tmp_server_db_path) as conn:
        init_or_migrate(conn)
        yield conn


@pytest.fixture()
def seeded_admin(tmp_server_db, fast_params):
    """One admin 'admin'. Required for FK to users.user_id from
    pending_mutations.proposer_admin_user_id + releases.proposer_admin_user_id.
    """
    _insert_first_admin(
        tmp_server_db, "admin", "adminpw",
        params=fast_params, os_user="test-host",
    )
    return tmp_server_db


@pytest.fixture()
def admin_session_propose() -> Session:
    """Admin session with only CAN_PROPOSE_MUTATION (Phase 24 cap)."""
    return Session.for_testing(
        "admin", is_admin=True,
        capabilities=frozenset({CAN_PROPOSE_MUTATION}),
    )


@pytest.fixture()
def admin_session_release() -> Session:
    """Admin session with only CAN_APPROVE_RELEASE (Phase 24 cap)."""
    return Session.for_testing(
        "admin", is_admin=True,
        capabilities=frozenset({CAN_APPROVE_RELEASE}),
    )


@pytest.fixture()
def admin_session_both() -> Session:
    """Admin session with the full ADMIN_CAPS roster (9 caps at Phase 24)."""
    return Session.for_testing("admin", is_admin=True)


@pytest.fixture()
def non_admin_session() -> Session:
    """User session — capabilities frozenset() per ADR-0002 §am2 strict."""
    return Session.for_testing("alice-caller", is_admin=False)


@pytest.fixture()
def canonical_global_mg():
    """Fresh canonical-Global Metagraph with 6 named roles ensured."""
    return bootstrap_global(importers=())


@pytest.fixture()
def pending_global_mg(canonical_global_mg):
    """Pending-Global Metagraph parallel to canonical per PB-15(a) + Z11(a)."""
    return bootstrap_pending_global(canonical_global_mg)


@pytest.fixture()
def atom_proposal_factory():
    """Factory to construct a one-item ATOM PromotionProposal.

    Usage::

        proposal = atom_proposal_factory(
            node_type="Class",
            value="MyClass",
            properties={"label": "MyClass"},
            target_role="ontology",
        )
    """

    def _make(
        *,
        node_type: str = "Class",
        value: str = "TestNode",
        properties: dict | None = None,
        target_role: str = "ontology",
        source_user_id: str | None = None,
        reason: str = "",
    ) -> PromotionProposal:
        return PromotionProposal(
            items=[
                PromotionItem(
                    kind=PromotionItemKind.ATOM,
                    node=NodeSpec(
                        node_type=node_type,
                        value=value,
                        properties=properties or {},
                        target_role=target_role,
                    ),
                    source_user_id=source_user_id,
                )
            ],
            reason=reason,
        )

    return _make
