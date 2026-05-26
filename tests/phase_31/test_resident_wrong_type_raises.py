"""Phase 31 — start_resident on non-Monitor IRI raises ResidentError.

ADR-0073 §amendment-1 clause 4 — halvim divergence: parent raises
``CapacityRegistrationError``; halvim raises ``ResidentError`` (residents
are lifecycle, not registration).
"""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CapacityLayer,
    Capacity,
    ResidentError,
)
from mindsos_capacity.builtins import DS_RAW_TEXT, install_text_capacities
from mindsos_capacity.identifiers import CATEGORY_PERCEPTION


def test_start_resident_on_reactive_capacity_raises_resident_error():
    """Pass a reactive Capacity (not a Monitor) — must raise ResidentError."""
    layer = CapacityLayer()
    install_text_capacities(layer)
    # text.space_split is a Capacity, not a Monitor.
    reactive_iri = "capacity:perception:text.space_split"
    with pytest.raises(ResidentError) as exc_info:
        layer.start_resident(reactive_iri)
    # The error message should name the IRI.
    assert "text.space_split" in str(exc_info.value)
    assert "Monitor" in str(exc_info.value)
