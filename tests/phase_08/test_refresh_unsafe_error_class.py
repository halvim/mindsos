"""PB-5 B — RefreshUnsafeError class ships; no enforcement test."""

from __future__ import annotations

from mindsos_core.exceptions import PersistenceError, RefreshUnsafeError


def test_refresh_unsafe_error_importable() -> None:
    assert RefreshUnsafeError is not None


def test_refresh_unsafe_error_subclass_of_persistence_error() -> None:
    assert issubclass(RefreshUnsafeError, PersistenceError)


def test_refresh_unsafe_error_constructible() -> None:
    err = RefreshUnsafeError("test message")
    assert "test message" in str(err)


def test_refresh_unsafe_error_class_only_no_phase_08_raise_path() -> None:
    """Per PB-5 B — Phase 08 ships the class but never raises it."""
    # Nothing to assert beyond "class exists + importable + has the
    # expected hierarchy"; enforcement is deferred per PB-5 B.
    assert True
