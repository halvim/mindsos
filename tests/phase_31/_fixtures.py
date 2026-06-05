"""Shared fixtures for tests/phase_31/.

One shared file per R2 PB-18 (Phase 30 precedent).

The resident-lifecycle fixtures (``make_test_monitor`` /
``make_layer_with_test_monitor``) were removed in Phase 41 along with the
resident test suite when monitor lifecycle relocated to the L4 substrate
(ADR-0155). The text-builtins fixtures below survive.
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins import install_text_capacities


def make_fresh_layer() -> CapacityLayer:
    """Return a fresh empty in-memory CapacityLayer (no builtins installed)."""
    return CapacityLayer()


def make_layer_with_text() -> CapacityLayer:
    """Return a fresh CapacityLayer with text builtins installed."""
    layer = CapacityLayer()
    install_text_capacities(layer)
    return layer
