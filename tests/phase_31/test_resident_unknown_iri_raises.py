"""Phase 31 — start_resident on unknown IRI passes through CapacityRegistrationError.

R3 PB-27 lock (pass-through; no wrap). Unknown IRI is a registration-table
miss, not a resident-lifecycle failure.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import CapacityLayer, CapacityRegistrationError


def test_start_resident_unknown_iri_passes_through():
    layer = CapacityLayer()
    with pytest.raises(CapacityRegistrationError):
        layer.start_resident("capacity:perception:never.registered")
