"""M10 — schema reserved keys include deprecated_at + disputed_at."""

from __future__ import annotations

import pytest

from mindsos_core import RESERVED_PROPERTY_KEYS, validate_user_properties, PropertyShapeError


def test_deprecated_at_is_reserved() -> None:
    assert "deprecated_at" in RESERVED_PROPERTY_KEYS


def test_disputed_at_is_reserved() -> None:
    assert "disputed_at" in RESERVED_PROPERTY_KEYS


def test_user_property_named_deprecated_at_raises() -> None:
    try:
        validate_user_properties({"deprecated_at": "yes"})
        raise AssertionError("expected PropertyShapeError")
    except PropertyShapeError as e:
        assert "reserved" in str(e).lower()


def test_user_property_named_disputed_at_raises() -> None:
    try:
        validate_user_properties({"disputed_at": "yes"})
        raise AssertionError("expected PropertyShapeError")
    except PropertyShapeError as e:
        assert "reserved" in str(e).lower()


def test_target_stale_NOT_reserved() -> None:
    """ADR-0128 amendment-3: target_stale is a typed XRef field, not a
    property-bag key — NOT in RESERVED_PROPERTY_KEYS."""
    assert "target_stale" not in RESERVED_PROPERTY_KEYS
