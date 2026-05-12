"""Canonicalize utility tests (Phase 06 row §D + P34 B)."""

from __future__ import annotations

import json

from mindsos_instances import canonicalize


def test_canonicalize_set_becomes_sorted_list():
    out = canonicalize({"a", "c", "b"})
    assert out == ["a", "b", "c"]


def test_canonicalize_frozenset_becomes_sorted_list():
    out = canonicalize(frozenset({3, 1, 2}))
    assert out == [1, 2, 3]


def test_canonicalize_dict_keys_stringified():
    out = canonicalize({1: "a", 2: "b"})
    assert set(out.keys()) == {"1", "2"}


def test_canonicalize_nested():
    out = canonicalize({"items": frozenset({3, 1, 2})})
    assert out == {"items": [1, 2, 3]}


def test_canonicalize_preserves_list_order():
    out = canonicalize([3, 1, 2])
    assert out == [3, 1, 2]


def test_canonicalize_primitives_passthrough():
    assert canonicalize(42) == 42
    assert canonicalize("hello") == "hello"
    assert canonicalize(True) is True
    assert canonicalize(None) is None
    assert canonicalize(3.14) == 3.14


def test_canonicalize_recursive_in_set():
    out = canonicalize({frozenset({"a", "b"}), frozenset({"c"})})
    # Sorted by JSON representation: [["a","b"],["c"]]
    assert isinstance(out, list)
    assert len(out) == 2


def test_canonicalize_stable_json():
    # Same logical content, different insertion orders, should yield
    # identical JSON.
    a = canonicalize({"keys": {"z", "a"}, "vals": [1, 2]})
    b = canonicalize({"vals": [1, 2], "keys": {"a", "z"}})
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
