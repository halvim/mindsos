"""metagraph_equality.py XRef extension — PB-3 + RR-4 (id-set + content-tuple)."""

from __future__ import annotations

import pytest

from mindsos_core import Metagraph
from mindsos_core.models.xref import XRef
from tests._shared.metagraph_equality import (
    assert_metagraphs_equal,
    assert_xref_contents_equal,
)


def _seed_with_xref(*, xref_id: str, target_id: str = "t1") -> Metagraph:
    mg = Metagraph(name="m", metagraph_id="mg-1")
    x = XRef(
        source_metagraph_id="mg-1",
        source_id="n1",
        target_metagraph_id="mg-tgt",
        target_role="lex",
        target_id=target_id,
        ref_type="SPECIALISES",
        xref_id=xref_id,
    )
    mg.identity.register("n1")
    mg.identity.register(xref_id)
    mg.xrefs[xref_id] = x
    mg._xrefs_by_source.setdefault("n1", set()).add(xref_id)
    mg._xrefs_by_target.setdefault(("mg-tgt", target_id), set()).add(xref_id)
    return mg


def test_equal_xrefs_pass_walker():
    a = _seed_with_xref(xref_id="x1")
    b = _seed_with_xref(xref_id="x1")
    assert_metagraphs_equal(a, b)


def test_xref_id_drift_fails_walker():
    a = _seed_with_xref(xref_id="x1")
    b = _seed_with_xref(xref_id="DIFFERENT")
    with pytest.raises(AssertionError, match="XRef ids drift"):
        assert_metagraphs_equal(a, b)


def test_xref_field_drift_fails_walker():
    """Same xref_id, different target_id ⇒ field-by-field check catches it."""
    a = _seed_with_xref(xref_id="x1", target_id="t1")
    b = _seed_with_xref(xref_id="x1", target_id="DRIFTED")
    with pytest.raises(AssertionError, match="target_id drift"):
        assert_metagraphs_equal(a, b)


def test_assert_xref_contents_equal_dict_input():
    a = _seed_with_xref(xref_id="x1")
    b = _seed_with_xref(xref_id="x2")  # different id, same content
    # Content equal even though xref_ids differ — migration test pattern.
    assert_xref_contents_equal(a.xrefs, b.xrefs)


def test_assert_xref_contents_equal_drift_raises():
    a = _seed_with_xref(xref_id="x1", target_id="t1")
    b = _seed_with_xref(xref_id="x2", target_id="DRIFTED")
    with pytest.raises(AssertionError, match="content drift"):
        assert_xref_contents_equal(a.xrefs, b.xrefs)


def test_assert_xref_contents_equal_iterable_input():
    a = _seed_with_xref(xref_id="x1")
    b = _seed_with_xref(xref_id="x2")
    assert_xref_contents_equal(list(a.xrefs.values()), list(b.xrefs.values()))


def test_empty_xrefs_pass():
    a = Metagraph(name="m1", metagraph_id="mg-1")
    b = Metagraph(name="m1", metagraph_id="mg-1")
    assert_metagraphs_equal(a, b)
