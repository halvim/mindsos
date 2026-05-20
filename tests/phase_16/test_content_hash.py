"""Phase 16 — `metagraph_content_hash` determinism + scope.

Tests per ADR-0052 §amendment-1 (Phase 16): role-scoped hash;
6-decimal canonicalization on numeric inputs; cross-role mutation
does NOT invalidate.
"""

from __future__ import annotations

import pytest

from mindsos_admin import metagraph_content_hash
from mindsos_core import Graph, Metagraph


def _build_two_role_mg() -> Metagraph:
    """Two-role mg: ontology + lexicon, each with one node."""
    mg = Metagraph(name="test_mg")
    ont = Graph(name="o", role="ontology")
    ont.add_node(value="X", type_name="Class", node_id="dolce:Class:X")
    mg.add_graph(ont)
    lex = Graph(name="l", role="lexicon")
    lex.add_node(value="y.n.01", type_name="Synset", node_id="oewn:Synset:y.n.01")
    mg.add_graph(lex)
    return mg


class TestDeterminism:
    def test_same_inputs_same_hash(self) -> None:
        mg1 = _build_two_role_mg()
        mg2 = _build_two_role_mg()
        assert metagraph_content_hash(mg1, role="ontology") == metagraph_content_hash(
            mg2, role="ontology"
        )

    def test_hash_is_64_char_hex(self) -> None:
        mg = _build_two_role_mg()
        h = metagraph_content_hash(mg, role="ontology")
        assert len(h) == 64
        int(h, 16)  # parses as hex


class TestRoleScope:
    """Per ADR-0052 §amendment-1: cross-role mutation does NOT invalidate."""

    def test_unrelated_role_mutation_preserves_hash(self) -> None:
        mg = _build_two_role_mg()
        h_before = metagraph_content_hash(mg, role="ontology")
        # Mutate the lexicon role-graph — unrelated to scored role.
        lex = next(g for g in mg.graphs.values() if g.role == "lexicon")
        lex.add_node(
            value="z.v.02", type_name="Synset", node_id="oewn:Synset:z.v.02"
        )
        h_after = metagraph_content_hash(mg, role="ontology")
        assert h_before == h_after, (
            "Unrelated-role mutation invalidated ontology hash — "
            "ADR-0052 §amendment-1 role-scope violated."
        )

    def test_same_role_mutation_changes_hash(self) -> None:
        mg = _build_two_role_mg()
        h_before = metagraph_content_hash(mg, role="ontology")
        ont = next(g for g in mg.graphs.values() if g.role == "ontology")
        ont.add_node(
            value="W", type_name="Class", node_id="dolce:Class:W"
        )
        h_after = metagraph_content_hash(mg, role="ontology")
        assert h_before != h_after, (
            "Same-role mutation did NOT change hash — role-scope is too narrow."
        )

    def test_empty_role_graph_has_deterministic_hash(self) -> None:
        mg = Metagraph(name="empty_mg")
        h1 = metagraph_content_hash(mg, role="ontology")
        h2 = metagraph_content_hash(mg, role="ontology")
        assert h1 == h2

    def test_role_with_no_matching_graph_is_well_defined(self) -> None:
        """Hashing a role that has no graphs in the metagraph still returns a hex."""
        mg = _build_two_role_mg()
        h = metagraph_content_hash(mg, role="concepts")  # no concepts graph
        assert len(h) == 64
