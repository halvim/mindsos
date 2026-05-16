"""Phase 10 conftest — re-exports falkor_client (RR-10; B-08-T2 carry).

Per Phase 10 RR-10 + the Phase 08 B-08-T2 hotfix precedent (same
pattern as Phase 09 conftest): integration tests in ``tests/phase_10/``
get the live :class:`FalkorClient` fixture without per-file imports.
"""

from __future__ import annotations

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401
