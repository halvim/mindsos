"""R4-3 A — 3 new exception classes ship and inherit from PersistenceError."""

from __future__ import annotations

import pytest

from mindsos_core.exceptions import (
    PersistenceError,
    RefreshUnsafeError,
    RoleMismatchError,
    WALReplayerMissingError,
)
from mindsos_core.reconstruction import (
    RefreshUnsafeError as RUE_reexport,
    RoleMismatchError as RME_reexport,
    WALReplayerMissingError as WALRME_reexport,
)


def test_three_new_exceptions_importable_from_core_exceptions() -> None:
    """All 3 classes live in :mod:`mindsos_core.exceptions`."""
    assert RefreshUnsafeError is not None
    assert WALReplayerMissingError is not None
    assert RoleMismatchError is not None


def test_three_new_exceptions_inherit_from_persistence_error() -> None:
    """All 3 inherit from :class:`PersistenceError` per R4-3 A."""
    assert issubclass(RefreshUnsafeError, PersistenceError)
    assert issubclass(WALReplayerMissingError, PersistenceError)
    assert issubclass(RoleMismatchError, PersistenceError)


def test_three_new_exceptions_reexported_via_reconstruction() -> None:
    """R4-12 A — re-exported from :mod:`mindsos_core.reconstruction`."""
    assert RUE_reexport is RefreshUnsafeError
    assert RME_reexport is RoleMismatchError
    assert WALRME_reexport is WALReplayerMissingError


def test_refresh_unsafe_error_class_only_no_enforcement() -> None:
    """PB-5 B — class ships but is never raised in Phase 08."""
    # Smoke: instantiable; doesn't have a special __init__.
    err = RefreshUnsafeError("test")
    assert isinstance(err, PersistenceError)


def test_role_mismatch_error_carries_both_roles() -> None:
    """R4-2 D — RoleMismatchError __init__ surfaces both roles."""
    err = RoleMismatchError(
        graph_id="g-123",
        in_memory_role="lexicon",
        db_role="ontology",
    )
    assert err.graph_id == "g-123"
    assert err.in_memory_role == "lexicon"
    assert err.db_role == "ontology"
    assert "g-123" in str(err)
    assert "lexicon" in str(err)
    assert "ontology" in str(err)


def test_no_reconstruction_error_umbrella() -> None:
    """R4-3 A — no `ReconstructionError` umbrella class."""
    import mindsos_core.exceptions as exc_mod

    assert not hasattr(exc_mod, "ReconstructionError")


def test_wal_replayer_missing_error_is_persistence_subclass() -> None:
    """RPB-3 C — narrow-catch sentinel must be catchable as PersistenceError."""
    try:
        raise WALReplayerMissingError("kind=foo not registered")
    except PersistenceError:
        # Expected — narrow-catch by load_metagraph still resolves via
        # the broader catch when a caller chooses.
        pass
    else:
        pytest.fail("WALReplayerMissingError did not propagate as PersistenceError")
