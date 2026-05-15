"""XRefIntegrityError — RR-3 PersistenceError subclass + importable surface."""

from __future__ import annotations

from mindsos_core.exceptions import (
    PersistenceError,
    XRefIntegrityError,
)


def test_xref_integrity_error_is_persistence_error():
    """RR-3 — XRefIntegrityError inherits from PersistenceError."""
    assert issubclass(XRefIntegrityError, PersistenceError)


def test_xref_integrity_error_importable_from_top_level():
    """RR-3 — re-exported from mindsos_core for caller convenience."""
    from mindsos_core import XRefIntegrityError as X
    assert X is XRefIntegrityError


def test_xref_integrity_error_constructable_with_message():
    e = XRefIntegrityError("target n1 not found in mg2")
    assert "target n1" in str(e)


def test_caught_by_persistence_error_handler():
    """Downstream code catching PersistenceError still catches XRefIntegrityError."""
    try:
        raise XRefIntegrityError("missing")
    except PersistenceError as e:
        assert "missing" in str(e)
    else:
        raise AssertionError("PersistenceError did not catch XRefIntegrityError")
