"""Phase 44 PR3 (S8) — episodic cross-user read capability + audit constant.

`CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY` + `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY`
(L2-39 / D-L2-23). Roster registration only — no v1 emit-site; registered
ahead of the first cross-user episodic-memory read flow. These assert the
roster shape + distinctness from the generic Local-read cap/event.
"""

from __future__ import annotations

from mindsos_server.audit import (
    EVT_CROSS_USER_READ_INSTALL,
    EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY,
)
from mindsos_server.capabilities import (
    ADMIN_CAPS,
    ALL_CAPABILITIES,
    CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY,
    CAN_READ_OTHER_LOCALS,
    USER_CAPS,
)


def test_capability_value_matches_identifier() -> None:
    assert (
        CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY
        == "CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY"
    )


def test_capability_distinct_from_generic_local_read() -> None:
    assert CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY != CAN_READ_OTHER_LOCALS


def test_capability_in_roster_and_admin_bundle() -> None:
    assert CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY in ALL_CAPABILITIES
    assert CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY in ADMIN_CAPS
    # Phase 50 (ADR-0183) added CAN_INSTALL_SKILL + CAN_UNINSTALL_SKILL.
    assert len(ALL_CAPABILITIES) == 12


def test_capability_default_deny_for_users() -> None:
    assert CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY not in USER_CAPS


def test_audit_constant_value_and_distinct() -> None:
    assert (
        EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY
        == "EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY"
    )
    assert EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY != EVT_CROSS_USER_READ_INSTALL
