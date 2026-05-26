"""Phase 33 — WriteHandleNotWiredError + CapabilityDeniedError exception classes."""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CapabilityDeniedError,
    CapacityLayerError,
    CapacityRegistrationError,
    WriteHandleNotWiredError,
)


def test_write_handle_not_wired_is_capacity_layer_error_subclass():
    assert issubclass(WriteHandleNotWiredError, CapacityLayerError)


def test_write_handle_not_wired_NOT_capacity_registration_error_subclass():
    """Wire-state is a lifecycle concern; not a registration concern."""
    assert not issubclass(WriteHandleNotWiredError, CapacityRegistrationError)


def test_capability_denied_is_capacity_layer_error_subclass():
    assert issubclass(CapabilityDeniedError, CapacityLayerError)


def test_capability_denied_NOT_capacity_registration_error_subclass():
    assert not issubclass(CapabilityDeniedError, CapacityRegistrationError)


def test_write_handle_not_wired_raisable():
    with pytest.raises(WriteHandleNotWiredError):
        raise WriteHandleNotWiredError("test")


def test_capability_denied_raisable():
    with pytest.raises(CapabilityDeniedError):
        raise CapabilityDeniedError("test")
