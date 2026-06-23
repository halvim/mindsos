"""
Persistence sub-package — :class:`LocalPersister` Protocol + impls
+ KL bootstrap wrapper(s).

Phase 25 first ship (LocalPersister Protocol + InMemoryLocalPersister).
Phase 26a adds the :func:`bootstrap_kl_from_falkordb` wrapper per
R6-PB-2 (b) — symmetric with sibling ``local_persister.py``.
Phase 26b adds :func:`bootstrap_global_pair_from_falkordb` per
R4-PB-1 (a) + R6-PB-1 (a) — canonical+pending symmetric load-or-mint;
closes B-26a-T4. SQLite + FalkorDB Local persister implementations
defer to the first user-Local-write phase per ADR-0011 §amendment-2.

See :mod:`mindsos_server.persistence.local_persister` and
:mod:`mindsos_server.persistence.bootstrap` for the bodies.
"""

from __future__ import annotations

from mindsos_server.persistence.bootstrap import (
    bootstrap_global_pair_from_falkordb,
    bootstrap_kl_from_falkordb,
)
from mindsos_server.persistence.local_persister import (
    FalkorDBLocalPersister,
    InMemoryLocalPersister,
    LocalPersister,
)

__all__ = [
    "LocalPersister",
    "InMemoryLocalPersister",
    # F9 (ADR-0186): the FalkorDB-backed durable Local persister was
    # shipped dormant at Phase 44 (ADR-0160); F9 promotes it to public
    # surface as the durable backing store for per-device Locals.
    "FalkorDBLocalPersister",
    "bootstrap_kl_from_falkordb",
    "bootstrap_global_pair_from_falkordb",
]
