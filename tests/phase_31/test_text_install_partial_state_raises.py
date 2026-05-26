"""Phase 31 — install_text_capacities raises on partial install state.

R1 PB-12 lock — some-present-some-missing → CapacityRegistrationError.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import CapacityRegistrationError, DataState, ShapeDescriptor
from mindsos_capacity.builtins import (
    DS_RAW_TEXT,
    install_text_capacities,
    text_datastates,
)
from mindsos_capacity.identifiers import CATEGORY_PERCEPTION

from ._fixtures import make_fresh_layer


def test_partial_state_raises():
    """Manually register one text DataState, then call install → raises."""
    layer = make_fresh_layer()
    # Insert only DS_RAW_TEXT (1 of 5).
    layer.register_datastate(
        DataState(
            name="text.raw",
            shape=ShapeDescriptor.scalar("str", opaque_tag="text.raw"),
            description="...",
            provenance_category=CATEGORY_PERCEPTION,
        )
    )
    with pytest.raises(CapacityRegistrationError) as exc_info:
        install_text_capacities(layer)
    msg = str(exc_info.value)
    assert "partial install state" in msg
    assert DS_RAW_TEXT in msg
