"""Phase 26a signature smoke — propose / release / audit_gate.run all
accept the new positional ``client: Client`` parameter per ADR-0118 §am3.

Pure signature inspection — does not exercise the wiring (that's in
the E2E smoke tests). Catches signature regressions cheaply.
"""

from __future__ import annotations

import inspect

from mindsos_admin import audit_gate
from mindsos_admin.promotion import propose_for_promotion
from mindsos_server.release import release_update


def _params(fn) -> list[str]:
    return list(inspect.signature(fn).parameters.keys())


def test_propose_for_promotion_has_client_as_second_positional() -> None:
    params = _params(propose_for_promotion)
    # Expected: conn, client, session=, proposal=, pending_global_mg=
    assert params[0] == "conn"
    assert params[1] == "client"


def test_release_update_has_client_as_second_positional() -> None:
    params = _params(release_update)
    # Expected: conn, client, session=, canonical_global_mg=, pending_global_mg=
    assert params[0] == "conn"
    assert params[1] == "client"


def test_audit_gate_run_has_client_as_second_positional() -> None:
    params = _params(audit_gate.run)
    # Expected: admin_session, client, pending_mutations=, canonical_global_mg=, pending_global_mg=, prior_failed_canonical_ids=
    assert params[0] == "admin_session"
    assert params[1] == "client"
