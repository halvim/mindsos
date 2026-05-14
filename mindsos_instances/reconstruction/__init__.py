"""Sibling-package reconstruction (Phase 08 — PB-4 A).

Phase 08 introduces ``InstanceLoader`` as the sibling-package observer
subscriber for :meth:`mindsos_core.models.Metagraph.register_after_load_observer`.
:func:`mindsos_instances.attach_registry` wires this in idempotently per
Phase 06 P49 B helper.

ADR-0132 boundary: instances live in :mod:`mindsos_instances`;
:mod:`mindsos_core` does NOT import this subpackage. The observer
pattern keeps the boundary clean — Core fires the after-load hook;
sibling-side rehydration is opaque to Core.
"""

from __future__ import annotations

from .instance_loader import InstanceLoader

__all__ = ["InstanceLoader"]
