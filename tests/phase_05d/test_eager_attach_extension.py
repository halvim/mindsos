"""Phase 05d — eager-attach extension tests for metaedges + metahyperedges.

Locks the eager-walk semantics per round-7 row §D:
  - Empty MetaEdgeType vocab + non-strict + existing metaedges →
    skip walk silently (P39 A; mirrors 05b/05c Pushback 24-hybrid).
  - Empty vocab + strict + existing metaedges → fail.
  - Non-empty vocab → walk every metaedge / metahyperedge.

Critical for 05c-migration safety: 05c metagraphs with metaedges
attaching to a 05c-shipped schema migrated to v=3 (with empty
meta_edge_types: []) must SUCCEED on re-attach under non-strict.
"""

from __future__ import annotations

import pytest

from mindsos_core import (
    Graph,
    MetaEdgeType,
    MetaHyperEdgeType,
    Metagraph,
    MetagraphSchema,
    UnknownTypeError,
)


def _build_metagraph_with_metaedge(role_a="ontology", role_b="lexicon"):
    mg = Metagraph(name="mg")
    g_a = Graph(name="a", role=role_a)
    g_b = Graph(name="b", role=role_b)
    mg.add_graph(g_a)
    mg.add_graph(g_b)
    me = mg.add_metaedge(g_a.graph_id, g_b.graph_id, type_name="LINKS_TO")
    return mg, g_a, g_b, me


def _build_metagraph_with_metahyperedge(roles=("ontology", "lexicon", "concepts")):
    mg = Metagraph(name="mg")
    graphs = []
    for i, r in enumerate(roles):
        g = Graph(name=f"g{i}", role=r)
        mg.add_graph(g)
        graphs.append(g)
    mhe = mg.add_metahyperedge(
        [g.graph_id for g in graphs],
        type_name="GROUPS",
    )
    return mg, graphs, mhe


class TestEmptyVocabPassSilently:
    """P39 A: empty MetaEdgeType + non-strict + existing metaedge → skip."""

    def test_empty_meta_edge_type_non_strict_passes(self):
        mg, *_ = _build_metagraph_with_metaedge()
        ms = MetagraphSchema(strict=False)  # empty meta vocab.
        # No metaedge type registered; non-strict; should succeed.
        mg.attach_schema(ms, schema_name="ms")
        assert mg.schema is ms
        assert mg.schema_name == "ms"

    def test_empty_meta_hyperedge_type_non_strict_passes(self):
        mg, *_ = _build_metagraph_with_metahyperedge()
        ms = MetagraphSchema(strict=False)
        mg.attach_schema(ms, schema_name="ms")
        assert mg.schema is ms

    def test_empty_meta_edge_type_strict_fails(self):
        """P39 A: empty + strict still fails (vocab-existence is the
        strict invariant; mirrors 05b/05c IntergraphEdgeType precedent).
        """
        mg, *_ = _build_metagraph_with_metaedge()
        ms = MetagraphSchema(strict=True)  # empty meta vocab + strict.
        with pytest.raises(UnknownTypeError):
            mg.attach_schema(ms, schema_name="ms")
        # State unchanged on raise.
        assert mg.schema is None

    def test_empty_meta_hyperedge_type_strict_fails(self):
        mg, *_ = _build_metagraph_with_metahyperedge()
        ms = MetagraphSchema(strict=True)
        with pytest.raises(UnknownTypeError):
            mg.attach_schema(ms, schema_name="ms")


class TestNonEmptyVocabWalk:
    def test_meta_edge_type_present_passes(self):
        mg, *_ = _build_metagraph_with_metaedge()
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(name="LINKS_TO"))
        mg.attach_schema(ms, schema_name="ms")

    def test_meta_edge_type_missing_when_vocab_non_empty_fails(self):
        """If MetaEdgeType vocab is non-empty but doesn't include the
        existing metaedge's type_name, eager-attach must refuse.
        """
        mg, *_ = _build_metagraph_with_metaedge()
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(name="OTHER_TYPE"))  # unrelated.
        with pytest.raises(UnknownTypeError):
            mg.attach_schema(ms, schema_name="ms")

    def test_meta_edge_role_constraint_violation(self):
        mg, *_ = _build_metagraph_with_metaedge(role_a="ontology", role_b="lexicon")
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(
            name="LINKS_TO",
            allowed_source_graphs=frozenset({"concepts"}),  # mismatch.
        ))
        with pytest.raises(UnknownTypeError, match="source graph role"):
            mg.attach_schema(ms, schema_name="ms")

    def test_meta_hyperedge_type_present_passes(self):
        mg, *_ = _build_metagraph_with_metahyperedge()
        ms = MetagraphSchema()
        ms.add_meta_hyperedge_type(MetaHyperEdgeType(name="GROUPS"))
        mg.attach_schema(ms, schema_name="ms")

    def test_meta_hyperedge_type_missing_fails(self):
        mg, *_ = _build_metagraph_with_metahyperedge()
        ms = MetagraphSchema()
        ms.add_meta_hyperedge_type(MetaHyperEdgeType(name="OTHER"))  # unrelated.
        with pytest.raises(UnknownTypeError):
            mg.attach_schema(ms, schema_name="ms")


class TestMixedVocabsAndPrimitives:
    """Eager-attach walks all four vocab/primitive pairs uniformly."""

    def test_only_intergraph_edge_type_pre_existing_metaedges_pass_silently(self):
        """05c-migration safety case: metagraph has a metaedge; schema
        only has IntergraphEdgeType registered (meta vocab empty);
        non-strict — eager-attach succeeds.
        """
        from mindsos_core import IntergraphEdgeType

        mg, *_ = _build_metagraph_with_metaedge()
        ms = MetagraphSchema(strict=False)
        ms.add_intergraph_edge_type(IntergraphEdgeType(name="ANYTHING"))
        # No MetaEdgeType registered; metaedge exists.
        mg.attach_schema(ms, schema_name="ms")
        assert mg.schema is ms

    def test_atomic_failure_state_unchanged(self):
        mg, *_ = _build_metagraph_with_metaedge()
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(name="OTHER"))
        with pytest.raises(UnknownTypeError):
            mg.attach_schema(ms, schema_name="ms")
        assert mg.schema is None
        assert mg.schema_name is None


class TestDetachReattach:
    def test_detach_clears_schema_state(self):
        mg, *_ = _build_metagraph_with_metaedge()
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(name="LINKS_TO"))
        mg.attach_schema(ms, schema_name="ms")
        previous = mg.detach_schema()
        assert previous == "ms"
        assert mg.schema is None
        assert mg.schema_name is None

    def test_reattach_after_modify_succeeds_when_compatible(self):
        """Round-7 P31 A: no fingerprint mechanism — re-attach with
        modified vocab succeeds as long as eager-walk validates.
        """
        mg, *_ = _build_metagraph_with_metaedge()
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(name="LINKS_TO"))
        mg.attach_schema(ms, schema_name="ms")
        mg.detach_schema()
        # Add a new compatible type to the vocab.
        ms.add_meta_edge_type(MetaEdgeType(name="ALSO_VALID"))
        # Re-attach succeeds — no fingerprint refusal.
        mg.attach_schema(ms, schema_name="ms")
        assert mg.schema is ms

    def test_reattach_with_no_change_succeeds(self):
        """Round-7 P31 A: no consent flag — re-attach is just attach."""
        mg, *_ = _build_metagraph_with_metaedge()
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(name="LINKS_TO"))
        mg.attach_schema(ms, schema_name="ms")
        mg.detach_schema()
        mg.attach_schema(ms, schema_name="ms")
        assert mg.schema_name == "ms"
