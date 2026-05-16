"""P85 — Graph.__init__ accepts properties (ADR-0130 Graph-side acceptance)."""

from __future__ import annotations

import pytest

from mindsos_core import Graph, PropertyShapeError


def test_graph_init_accepts_properties() -> None:
    g = Graph(name="g", properties={"source": "dolce"})
    assert g.properties == {"source": "dolce"}


def test_graph_properties_default_empty() -> None:
    g = Graph(name="g")
    assert g.properties == {}


def test_graph_properties_reserved_key_rejected() -> None:
    """Reserved key handling delegates to validate_user_properties(scope='graph')."""
    try:
        Graph(name="g", properties={"deprecated_at": "yes"})
        raise AssertionError("expected PropertyShapeError")
    except PropertyShapeError:
        pass
