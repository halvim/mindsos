"""Phase 11 conftest — re-exports falkor_client (RR-10; Phase 10 carry).

Integration tests in ``tests/phase_11/`` get the live
:class:`FalkorClient` fixture without per-file imports.
"""

from __future__ import annotations

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401
