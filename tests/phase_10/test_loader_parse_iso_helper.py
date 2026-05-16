"""Phase 10 — _parse_iso helper used by loaders to recover datetime fields."""

from __future__ import annotations

from datetime import datetime

from mindsos_core.reconstruction.graph_loader import _parse_iso as gl_parse_iso
from mindsos_core.reconstruction.metagraph_loader import _parse_iso as mgl_parse_iso
from mindsos_core.reconstruction.xref_loader import _parse_iso as xl_parse_iso


def test_parse_iso_none() -> None:
    for fn in (gl_parse_iso, mgl_parse_iso, xl_parse_iso):
        assert fn(None) is None


def test_parse_iso_valid_string() -> None:
    s = "2026-05-15T12:00:00+00:00"
    for fn in (gl_parse_iso, mgl_parse_iso, xl_parse_iso):
        v = fn(s)
        assert isinstance(v, datetime) and v.year == 2026


def test_parse_iso_malformed_returns_none() -> None:
    """Defensive — bad ISO → None (not a poison datetime)."""
    for fn in (gl_parse_iso, mgl_parse_iso, xl_parse_iso):
        assert fn("garbage") is None
        assert fn("") is None
        assert fn(12345) is None


def test_parse_iso_datetime_passthrough() -> None:
    d = datetime(2026, 5, 15, 12, 0)
    for fn in (gl_parse_iso, mgl_parse_iso, xl_parse_iso):
        assert fn(d) is d
