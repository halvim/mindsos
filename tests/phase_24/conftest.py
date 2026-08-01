"""Shared fixtures for Phase 24 tests.

Extends the Phase 22 conftest shape. Adds:

* :func:`admin_session_propose` — admin session with CAN_PROPOSE_MUTATION.
* :func:`admin_session_release` — admin session with CAN_APPROVE_RELEASE.
* :func:`admin_session_both` — admin with both Phase 24 caps + Phase 22 baseline.
* :func:`non_admin_session` — carries ``USER_CAPS`` (denial-path tests).
  ``USER_CAPS`` is no longer empty — CORE-C2R1 / ADR-0002 §am-3 added
  the two skill-lifecycle capabilities — but it holds none of the
  capabilities under test here, so the denial paths are unaffected.
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
def inject_pending_node(seeded_admin):
    """Helper to directly inject a pending node with a CONTROLLED node_id.

    Bypasses :func:`propose_for_promotion`'s UUID minter. Needed for tests
    that rely on similarity scores firing reliably — Phase 16
    ``_score_levenshtein`` compares ``node_id`` strings, so random UUIDs
    score near zero and never trip blocking thresholds. Controlled IDs
    (e.g. ``"dup-001"`` + ``"dup-002"``) produce Lev ~ 0.875 → blocking.

    Performs both:
    1. SQL INSERT into ``pending_mutations`` with payload_json carrying
       the controlled node_id.
    2. ``add_node(node_id=...)`` on the supplied pending Metagraph's
       role-graph.

    Returns ``(mutation_id, node_id)``.
    """
    import json

    from mindsos_server.audit import EVT_PROMOTION_PROPOSED, write_audit

    def _inject(
        *,
        pending_global_mg,
        node_id: str,
        value: str = "TestNode",
        node_type: str = "Class",
        properties: dict | None = None,
        target_role: str = "ontology",
        proposer: str = "admin",
    ) -> tuple[int, str]:
        # 1. Emit audit row for FK.
        write_audit(
            seeded_admin,
            actor=proposer,
            event=EVT_PROMOTION_PROPOSED,
            target=None,
            extra={"injected_for_test": True},
        )
        cur = seeded_admin.execute("SELECT last_insert_rowid()")
        audit_event_id = int(cur.fetchone()[0])

        # 2. Insert pending_mutations row.
        payload = {
            "kind": "ATOM",
            "node_id": node_id,
            "node": {
                "node_type": node_type,
                "value": value,
                "properties": dict(properties or {}),
                "target_role": target_role,
            },
            "source_user_id": None,
        }
        cur = seeded_admin.execute(
            "INSERT INTO pending_mutations "
            "(proposer_admin_user_id, source_user_id, proposed_at, "
            "mutation_type, payload_json, audit_event_id) "
            "VALUES (?, NULL, '2026-05-22T00:00:00.000Z', 'PROMOTION', ?, ?)",
            (proposer, json.dumps(payload), audit_event_id),
        )
        mutation_id = int(cur.lastrowid)
        seeded_admin.commit()

        # 3. Add to in-memory pending Metagraph.
        graph = next(
            g for g in pending_global_mg.graphs.values() if g.role == target_role
        )
        graph.add_node(
            value, node_type, properties=dict(properties or {}),
            node_id=node_id,
        )
        return mutation_id, node_id

    return _inject


@pytest.fixture()
def inject_canonical_node():
    """Helper to directly inject a node into the canonical Metagraph.

    Phase 24 v1 has no canonical persistence (Z21(b) deferred to P26),
    so canonical content arrives via either release_update OR direct
    add_node in tests. This helper provides the latter for tests that
    set up cross-mg blocking scenarios.
    """

    def _inject(
        *,
        canonical_global_mg,
        node_id: str,
        value: str = "TestNode",
        node_type: str = "Class",
        properties: dict | None = None,
        target_role: str = "ontology",
    ) -> str:
        graph = next(
            g for g in canonical_global_mg.graphs.values() if g.role == target_role
        )
        graph.add_node(
            value, node_type, properties=dict(properties or {}),
            node_id=node_id,
        )
        return node_id

    return _inject


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
