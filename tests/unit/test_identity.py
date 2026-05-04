"""Unit tests for the IdentityRegistry and UUID generation.

Preserved verbatim from the parent project's ``tests/unit/test_identity.py``.
PHASE_MAP §1 — pre-existing tests must continue to pass on every phase.
"""

from __future__ import annotations

import pytest

from mindsos_core import IdentityError, IdentityRegistry, generate_uuid


def test_generate_uuid_is_unique():
    assert generate_uuid() != generate_uuid()


def test_register_and_contains():
    r = IdentityRegistry()
    uid = generate_uuid()
    r.register(uid)
    assert uid in r
    assert r.contains(uid)
    assert len(r) == 1


def test_register_duplicate_raises():
    r = IdentityRegistry()
    uid = generate_uuid()
    r.register(uid)
    with pytest.raises(IdentityError):
        r.register(uid)


def test_unregister_is_idempotent():
    r = IdentityRegistry()
    r.unregister("no-such-id")  # no error


def test_replace_preserves_atomicity():
    r = IdentityRegistry()
    a, b, c = generate_uuid(), generate_uuid(), generate_uuid()
    r.register(a)
    r.register(b)
    with pytest.raises(IdentityError):
        r.replace(a, b)
    # a still present
    assert a in r


def test_replace_swaps_ids():
    r = IdentityRegistry()
    a = generate_uuid()
    b = generate_uuid()
    r.register(a)
    r.replace(a, b)
    assert a not in r
    assert b in r
