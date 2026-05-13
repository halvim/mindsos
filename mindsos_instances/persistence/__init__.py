"""``mindsos_instances.persistence`` — Phase 07 sibling-package InstanceRepository.

Per ADR-0132 + Phase 06 P49 B Core/instances boundary —
``InstanceRepository`` lives in ``mindsos_instances``, not in
``mindsos_core.persistence``. Core never imports the instance models.

The repository subscribes to ``Metagraph.register_persist_observer``
via the :func:`mindsos_instances.attach_registry` extension (Phase 07 —
M9 observer-driven persist). When ``MetagraphRepository.persist`` fires
``after_persist(mg)``, the registry routes element + composite
instances through this repository as STEP 3 of the 4-step lifecycle
(P96 A).
"""

from __future__ import annotations

from .instance_repository import InstanceRepository

__all__ = ["InstanceRepository"]
