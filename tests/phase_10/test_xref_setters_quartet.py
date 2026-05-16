"""PX2 — XRef quartet: mark_xref_stale / unmark / deprecate_xref / undeprecate."""

from __future__ import annotations

from datetime import datetime, timezone

from mindsos_core import Graph, IdentityError, Metagraph, SoftDeleteKind


def _mg_with_xref() -> tuple[Metagraph, str]:
    mg = Metagraph(name="t")
    g = Graph(name="g", role="ont"); mg.add_graph(g)
    n1 = g.add_node(value="a", type_name="Person")
    x = mg.add_xref(
        source_id=n1.node_id, target_metagraph_id="other",
        target_role="ont", target_id="tid", ref_type="SPECIALISES",
    )
    return mg, x.xref_id


def test_mark_xref_stale() -> None:
    mg, xid = _mg_with_xref()
    x = mg.mark_xref_stale(xid)
    assert x.target_stale is True
    assert xid in mg._soft_delete_dirty[SoftDeleteKind.XREF]


def test_unmark_xref_stale() -> None:
    mg, xid = _mg_with_xref()
    mg.mark_xref_stale(xid)
    x = mg.unmark_xref_stale(xid)
    assert x.target_stale is False


def test_deprecate_xref_with_explicit_at() -> None:
    mg, xid = _mg_with_xref()
    explicit = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
    x = mg.deprecate_xref(xid, at=explicit)
    assert x.deprecated_at == explicit


def test_undeprecate_xref_clears() -> None:
    mg, xid = _mg_with_xref()
    mg.deprecate_xref(xid)
    x = mg.undeprecate_xref(xid)
    assert x.deprecated_at is None


def test_xref_unknown_id_raises() -> None:
    mg, _ = _mg_with_xref()
    for fn in (mg.mark_xref_stale, mg.unmark_xref_stale,
               mg.deprecate_xref, mg.undeprecate_xref):
        try:
            fn("nope")
            raise AssertionError(f"{fn.__name__} should raise IdentityError")
        except IdentityError:
            pass


def test_xref_has_no_disputed_at_attr() -> None:
    """ADR-0128 amendment-3: XRef has no disputed_at field."""
    mg, xid = _mg_with_xref()
    x = mg.xrefs[xid]
    assert not hasattr(x, "disputed_at"), "XRef should not have disputed_at per ADR-0128 a-3"
