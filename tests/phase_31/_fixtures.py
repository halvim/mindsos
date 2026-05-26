"""Shared fixtures for tests/phase_31/.

One shared file per R2 PB-18 (Phase 30 precedent).
"""

from __future__ import annotations

from typing import Tuple

from mindsos_capacity import (
    CapacityLayer,
    DataState,
    Monitor,
    ShapeDescriptor,
)
from mindsos_capacity.builtins import (
    DS_RAW_TEXT,
    install_text_capacities,
)
from mindsos_capacity.identifiers import (
    CATEGORY_PERCEPTION,
    capacity_iri,
)


def make_test_monitor(
    name: str = "resident.test",
    subscribes: Tuple[str, ...] = (DS_RAW_TEXT,),
) -> Monitor:
    """Build a Monitor declaration suitable for resident tests.

    Registers a thin Monitor in CATEGORY_PERCEPTION with the supplied
    name and ``subscribes_to`` set. The implementation is a no-op (L3
    is descriptive at Phase 31).
    """
    return Monitor(
        name=name,
        category=CATEGORY_PERCEPTION,
        inputs=(),
        outputs=(),
        subscribes_to=subscribes,
        emits=(),
        implementation=lambda **kw: None,
        description=f"Test Monitor {name!r} for resident-lifecycle tests.",
    )


def make_fresh_layer() -> CapacityLayer:
    """Return a fresh empty in-memory CapacityLayer (no builtins installed)."""
    return CapacityLayer()


def make_layer_with_text() -> CapacityLayer:
    """Return a fresh CapacityLayer with text builtins installed."""
    layer = CapacityLayer()
    install_text_capacities(layer)
    return layer


def make_layer_with_test_monitor(
    name: str = "resident.test",
    subscribes: Tuple[str, ...] = (DS_RAW_TEXT,),
):
    """Return (layer, monitor_iri) — fresh layer + registered test Monitor.

    Registers a fresh DataState ``test_input`` for the Monitor to
    subscribe to, then registers the Monitor itself. Returns the layer
    + the Monitor's IRI for ``start_resident`` calls.
    """
    layer = CapacityLayer()
    # Register the DataState the Monitor will reference (if not in
    # the supplied subscribes tuple — most callers pass DS_RAW_TEXT,
    # which would require the text-builtins family to be installed).
    if subscribes == (DS_RAW_TEXT,):
        install_text_capacities(layer)
    monitor = make_test_monitor(name=name, subscribes=subscribes)
    layer.register_capacity(monitor)
    return layer, capacity_iri(CATEGORY_PERCEPTION, name)
