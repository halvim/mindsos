"""Tier 4 — Phase 08 loader signatures unchanged (PB-12 B + PB-13 A).

The Phase 11 additive-sibling discipline keeps existing
:func:`load_graph` / :func:`load_metagraph` /
:meth:`MetagraphLoader.load` callable surfaces identical to Phase 08
(including Phase 10's ``include_deprecated`` addition). Phase 11
exclusively adds the report-returning siblings.
"""

from __future__ import annotations

import inspect

from mindsos_core.reconstruction import (
    MetagraphLoader,
    iter_load_graph,
    load_graph,
    load_graph_with_report,
    load_metagraph,
    load_metagraph_with_report,
)


def test_load_graph_signature_unchanged_from_phase_10() -> None:
    """Phase 10 contract test parity — ``include_deprecated`` in sig."""
    params = inspect.signature(load_graph).parameters
    # Phase 10's contract test asserts this; Phase 11 must not break it.
    assert "include_deprecated" in params
    # Phase 11 must NOT add policy kwargs to the unchanged sibling.
    assert "unknown_edge_type_policy" not in params
    assert "report" not in params


def test_iter_load_graph_keeps_phase_10_kwargs_and_adds_phase_11_optional() -> None:
    """``iter_load_graph`` keeps existing kwargs; Phase 11 adds OPTIONAL."""
    params = inspect.signature(iter_load_graph).parameters
    # Phase 10 kwargs preserved.
    assert "include_deprecated" in params
    assert "batch_size" in params
    # Phase 11 — optional kwargs with defaults; existing callers
    # unaffected.
    assert "report" in params
    assert params["report"].default is None
    assert "unknown_edge_type_policy" in params
    assert params["unknown_edge_type_policy"].default is None


def test_load_metagraph_signature_unchanged_from_phase_10() -> None:
    """``load_metagraph`` signature unchanged from Phase 10."""
    params = inspect.signature(load_metagraph).parameters
    assert "include_deprecated" in params
    assert "batch_size" in params
    assert "unknown_edge_type_policy" not in params


def test_metagraph_loader_load_signature_unchanged_from_phase_10() -> None:
    """``MetagraphLoader.load`` signature unchanged."""
    params = inspect.signature(MetagraphLoader.load).parameters
    assert "include_deprecated" in params
    assert "batch_size" in params
    assert "unknown_edge_type_policy" not in params


def test_load_graph_with_report_signature_phase_11_surface() -> None:
    """New ``load_graph_with_report`` surface carries policy + report return."""
    params = inspect.signature(load_graph_with_report).parameters
    assert "unknown_edge_type_policy" in params
    assert params["unknown_edge_type_policy"].default is None


def test_load_metagraph_with_report_signature_phase_11_surface() -> None:
    """New ``load_metagraph_with_report`` surface carries policy kwarg."""
    params = inspect.signature(load_metagraph_with_report).parameters
    assert "unknown_edge_type_policy" in params
    assert params["unknown_edge_type_policy"].default is None


def test_metagraph_loader_load_with_report_signature_phase_11_surface() -> None:
    """New ``MetagraphLoader.load_with_report`` method exists with policy kwarg."""
    assert hasattr(MetagraphLoader, "load_with_report")
    params = inspect.signature(MetagraphLoader.load_with_report).parameters
    assert "unknown_edge_type_policy" in params


def test_load_graph_with_report_returns_tuple() -> None:
    """Return type annotation surfaces ``(Graph, LoadReport)``."""
    ret = inspect.signature(load_graph_with_report).return_annotation
    # Annotation may render as string or Tuple — check substring.
    assert "Tuple" in str(ret) or "tuple" in str(ret)
    assert "LoadReport" in str(ret) or "Graph" in str(ret)
