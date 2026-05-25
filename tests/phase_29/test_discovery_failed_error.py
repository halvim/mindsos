"""Phase 29 — DiscoveryFailedError shape + subclass invariant."""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    CapacityLayer,
    CapacityRegistrationError,
    DiscoveryFailedError,
)

from ._fixtures import (
    text_demo_capacity,
    text_raw_datastate,
    text_tokens_datastate,
)


def test_discovery_failed_error_is_subclass_of_capacity_registration_error():
    """Callers catching CapacityRegistrationError catch DiscoveryFailedError too."""
    assert issubclass(DiscoveryFailedError, CapacityRegistrationError)


def test_discovery_failed_error_wraps_underlying_exception():
    """If discovery's _add_edge raises, register_capacity surfaces DiscoveryFailedError."""
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    cl.register_datastate(text_raw_datastate())
    cl.register_datastate(text_tokens_datastate())
    cl.register_capacity(text_demo_capacity())

    # Monkey-patch the discover_for_capacity call to raise.
    import mindsos_capacity.capacity_layer as cl_module

    original = cl_module.discover_for_capacity

    def raiser(*args, **kwargs):
        raise RuntimeError("simulated discovery failure")

    cl_module.discover_for_capacity = raiser
    try:
        from ._fixtures import text_join_capacity
        with pytest.raises(DiscoveryFailedError) as excinfo:
            cl.register_capacity(text_join_capacity())
        assert "discover_for_capacity raised" in str(excinfo.value)
        assert isinstance(excinfo.value.__cause__, RuntimeError)
    finally:
        cl_module.discover_for_capacity = original
