"""
Persistence sub-package — :class:`LocalPersister` Protocol + impls.

Phase 25 first ship. Re-exports the Protocol and the in-memory
implementation. SQLite + FalkorDB implementations defer to the first
user-Local-write phase per ADR-0011 §amendment-2.

See :mod:`mindsos_server.persistence.local_persister` for the body.
"""

from __future__ import annotations

from mindsos_server.persistence.local_persister import (
    InMemoryLocalPersister,
    LocalPersister,
)

__all__ = [
    "LocalPersister",
    "InMemoryLocalPersister",
]
