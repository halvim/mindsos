"""PB-7 A — `verify --source=db --metagraph M` unblock."""

from __future__ import annotations

import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


def test_verify_source_db_metagraph_M_unblocks_full_5_bucket_scanner(
    falkor_client, monkeypatch, capsys
) -> None:
    """PB-7 A — Phase 08 drops the Phase 07 P49 A refusal."""
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_cli.commands.persistence import verify_cmd

    mg = Metagraph(name="verify-mg", identity=IdentityRegistry())
    MetagraphRepository(falkor_client).persist(mg)

    monkeypatch.setattr(
        "mindsos_cli.commands.persistence._build_client",
        lambda: falkor_client,
    )
    monkeypatch.setattr(falkor_client, "close", lambda: None)

    # PB-7 A unblock — no longer refuses with exit 1; runs the scanner.
    # An empty metagraph is invariant-clean → exit 0.
    with pytest.raises(SystemExit) as excinfo:
        verify_cmd(metagraph="verify-mg", graph=None, source="db")
    assert excinfo.value.code == 0
