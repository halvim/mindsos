"""
Persistence sub-package — :class:`LocalPersister` Protocol + impls
+ KL bootstrap wrapper.

Phase 25 first ship (LocalPersister Protocol + InMemoryLocalPersister).
Phase 26a adds the :func:`bootstrap_kl_from_falkordb` wrapper per
R6-PB-2 (b) — symmetric with sibling ``local_persister.py``. SQLite +
FalkorDB Local persister implementations defer to the first
user-Local-write phase per ADR-0011 §amendment-2.

See :mod:`mindsos_server.persistence.local_persister` and
:mod:`mindsos_server.persistence.bootstrap` for the bodies.
"""

from __future__ import annotations

from mindsos_server.persistence.bootstrap import bootstrap_kl_from_falkordb
from mindsos_server.persistence.local_persister import (
    InMemoryLocalPersister,
    LocalPersister,
)

__all__ = [
    "LocalPersister",
    "InMemoryLocalPersister",
    "bootstrap_kl_from_falkordb",
]
