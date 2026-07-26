"""Phase 17 retirement — MetagraphView.versions_in_role IRI-scan enumerator.

Per ADR-0150 §amendment-3: version is IRI-string only; this method
returns the distinct ``parse_iri(node_id).version`` values observed
in the role-graph. Nodes whose ``node_id`` is not a version-qualified
IRI (bare fragments, alignment-graph member ids) are silently
skipped.
"""

from __future__ import annotations

import pytest

from mindsos_core import Graph, Node
from mindsos_core.models.metagraph import Metagraph
from mindsos_knowledge.bootstrap import ensure_global_role_graph
from mindsos_knowledge.identifiers import (
    dolce_iri,
    framenet_frame_iri,
    oewn_synset_iri,
)
from mindsos_knowledge.metagraph_view import MetagraphView


def _fresh_global() -> Metagraph:
    """A bootstrap-empty Global metagraph with the 6 named role-graphs."""
    mg = Metagraph(name="test_global")
    for role in (
        "ontology",
        "lexicon",
        "concepts",
        "promoted-pipelines",
        "request-patterns",
        "problem-trace",
    ):
        ensure_global_role_graph(mg, role)
    return mg


def test_empty_role_graph_returns_empty_set() -> None:
    """Empty role-graph → empty version set."""
    mg = _fresh_global()
    view = MetagraphView(mg)
    assert view.versions_in_role("ontology") == set()


def test_single_version_observed() -> None:
    """One IRI written → one version returned."""
    mg = _fresh_global()
    onto = ensure_global_role_graph(mg, "ontology")  # idempotent → existing graph
    onto.add_node(
        value="PhysicalObject",
        type_name="Class",
        node_id=dolce_iri("4.1", "PhysicalObject"),
    )
    view = MetagraphView(mg)
    assert view.versions_in_role("ontology") == {"4.1"}


def test_two_versions_coexist_in_same_role_graph() -> None:
    """Per ADR-0150 §amendment-3: distinct versions live in the SAME role-graph."""
    mg = _fresh_global()
    onto = ensure_global_role_graph(mg, "ontology")
    onto.add_node(
        value="PhysicalObject",
        type_name="Class",
        node_id=dolce_iri("4.1", "PhysicalObject"),
    )
    onto.add_node(
        value="PhysicalObject",
        type_name="Class",
        node_id=dolce_iri("4.2", "PhysicalObject"),
    )
    onto.add_node(
        value="Event",
        type_name="Class",
        node_id=dolce_iri("4.1", "Event"),
    )
    view = MetagraphView(mg)
    assert view.versions_in_role("ontology") == {"4.1", "4.2"}


def test_multiple_roles_isolated() -> None:
    """`versions_in_role(R)` scans only R's role-graph."""
    mg = _fresh_global()
    onto = ensure_global_role_graph(mg, "ontology")
    lex = ensure_global_role_graph(mg, "lexicon")
    cnp = ensure_global_role_graph(mg, "concepts")
    onto.add_node(
        value="Foo", type_name="Class", node_id=dolce_iri("4.1", "Foo")
    )
    lex.add_node(
        value="00001",
        type_name="Synset",
        node_id=oewn_synset_iri("2024", "00001", "n"),
    )
    cnp.add_node(
        value="Motion",
        type_name="Frame",
        node_id=framenet_frame_iri("1.7", "Motion"),
    )
    view = MetagraphView(mg)
    assert view.versions_in_role("ontology") == {"4.1"}
    assert view.versions_in_role("lexicon") == {"2024"}
    assert view.versions_in_role("concepts") == {"1.7"}


def test_non_version_qualified_node_ids_silently_skipped() -> None:
    """Bare fragments / non-IRI ids don't break the scan."""
    mg = _fresh_global()
    onto = ensure_global_role_graph(mg, "ontology")
    onto.add_node(
        value="PhysicalObject",
        type_name="Class",
        node_id=dolce_iri("4.1", "PhysicalObject"),
    )
    # Non-version-qualified id (would raise RefFormatError from parse_iri).
    onto.add_node(
        value="bare-fragment", type_name="Class", node_id="bare-fragment"
    )
    view = MetagraphView(mg)
    assert view.versions_in_role("ontology") == {"4.1"}


def test_unknown_role_returns_empty_set() -> None:
    """`graphs_by_role` returns [] for unknown role → empty set."""
    mg = _fresh_global()
    view = MetagraphView(mg)
    assert view.versions_in_role("not-a-role") == set()


def test_return_type_is_set_of_str() -> None:
    """Type contract per docstring."""
    mg = _fresh_global()
    view = MetagraphView(mg)
    result = view.versions_in_role("ontology")
    assert isinstance(result, set)
    for v in result:
        assert isinstance(v, str)
