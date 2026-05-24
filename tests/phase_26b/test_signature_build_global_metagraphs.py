"""Phase 26b — `_build_global_metagraphs(conn, client)` signature smoke.

Per Phase 26b design log R4-PB-2 (a) + ADR-0118 §am4 §"Decision §1".
Confirms the helper's signature change closes B-26a-T4; library symbol
shape only, not behavior (behavior covered by test_integration_a).
"""

from __future__ import annotations

import inspect

from mindsos_cli.commands.server import _build_global_metagraphs


def test_signature_takes_conn_and_client() -> None:
    """Helper signature: (conn, client) -> tuple[Metagraph, Metagraph]."""
    sig = inspect.signature(_build_global_metagraphs)
    params = list(sig.parameters)
    assert params == ["conn", "client"], (
        f"expected (conn, client) signature; got {params}"
    )


def test_helper_body_uses_pair_helper_and_pending_rehydrate() -> None:
    """Source-level smoke — body calls the pair helper +
    rehydrate_pending_global. Per Phase 26b §am4 §"Decision §1+§2"."""
    source = inspect.getsource(_build_global_metagraphs)
    assert "bootstrap_global_pair_from_falkordb" in source
    assert "rehydrate_pending_global" in source
    # Canonical content is FalkorDB-loaded by the pair helper — the OLD
    # rehydrate_global_metagraphs call MUST be gone.
    assert "rehydrate_global_metagraphs" not in source
    # OLD bootstrap_global + bootstrap_pending_global direct calls also gone.
    assert "bootstrap_global(importers=())" not in source
    assert "bootstrap_pending_global(" not in source
