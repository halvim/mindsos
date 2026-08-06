"""Phase 05c — P14-A 16-step validation order at Metagraph.add_intergraph_hyperedge.

Canonicalize-BEFORE-cardinality (P14-A) catches dedup-collapse-to-1-1
under ordered=False types. First-failure most-specific error.

Step 10 held the P8-A refusal of compositional=True + ordered=False. It is
**retired at CORE-C2R2** (ADR-0205 §amendment-3.1) and the class below now
pins the lift instead of the refusal — including the interaction P14-A
still enforces: dedup runs BEFORE the cardinality check, so a compositional
set that collapses to 1-1 still refuses.
"""

from __future__ import annotations

import pytest

from mindsos_core import (
    CypherError,
    Graph,
    IdentityError,
    IntergraphHyperEdgeType,
    Metagraph,
    MetagraphSchema,
    PropertyShapeError,
    PropertyType,
    SchemaError,
    UnknownTypeError,
)


@pytest.fixture
def mg_with_schema():
    mg = Metagraph(name="m")
    g_word = Graph(name="word", role="word")
    g_letter = Graph(name="letter", role="letter")
    mg.add_graph(g_word)
    mg.add_graph(g_letter)
    g_word.add_node("cat", type_name="Word", node_id="cat")
    g_letter.add_node("c", type_name="Letter", node_id="c")
    g_letter.add_node("a", type_name="Letter", node_id="a")
    g_letter.add_node("t", type_name="Letter", node_id="t")
    ms = MetagraphSchema(strict=True)
    ms.add_intergraph_hyperedge_type(
        IntergraphHyperEdgeType(
            name="COMPOSED_OF",
            allowed_anchor_types=frozenset({"Word"}),
            allowed_member_types=frozenset({"Letter"}),
            allowed_anchor_graphs=frozenset({"word"}),
            allowed_member_graphs=frozenset({"letter"}),
            property_types={"weight": PropertyType.FLOAT},
        )
    )
    ms.add_intergraph_hyperedge_type(
        IntergraphHyperEdgeType(
            name="UNORDERED",
            ordered=False,
        )
    )
    mg.attach_schema(ms, schema_name="msx")
    return {"mg": mg, "g_word": g_word, "g_letter": g_letter}


class TestStep1AndStep2GraphExistence:
    def test_anchor_graph_missing(self, mg_with_schema):
        mg = mg_with_schema["mg"]
        with pytest.raises(IdentityError, match="anchor graph.*not in"):
            mg.add_intergraph_hyperedge(
                anchors=[("UNKNOWN_GRAPH_ID", "x")],
                members=[("letter", "c"), ("letter", "a")],  # type: ignore[arg-type]
                type_name="COMPOSED_OF",
            )

    def test_member_graph_missing(self, mg_with_schema):
        mg = mg_with_schema["mg"]
        g_word = mg_with_schema["g_word"]
        with pytest.raises(IdentityError, match="member graph.*not in"):
            mg.add_intergraph_hyperedge(
                anchors=[(g_word.graph_id, "cat")],
                members=[("UNKNOWN", "c"), ("UNKNOWN", "a")],
                type_name="COMPOSED_OF",
            )


class TestStep3AndStep4NodeExistence:
    def test_anchor_node_missing(self, mg_with_schema):
        mg = mg_with_schema["mg"]
        g_word = mg_with_schema["g_word"]
        g_letter = mg_with_schema["g_letter"]
        with pytest.raises(IdentityError, match="anchor node"):
            mg.add_intergraph_hyperedge(
                anchors=[(g_word.graph_id, "missing_node")],
                members=[(g_letter.graph_id, "c"), (g_letter.graph_id, "a")],
                type_name="COMPOSED_OF",
            )

    def test_member_node_missing(self, mg_with_schema):
        mg = mg_with_schema["mg"]
        g_word = mg_with_schema["g_word"]
        g_letter = mg_with_schema["g_letter"]
        with pytest.raises(IdentityError, match="member node"):
            mg.add_intergraph_hyperedge(
                anchors=[(g_word.graph_id, "cat")],
                members=[(g_letter.graph_id, "missing"), (g_letter.graph_id, "a")],
                type_name="COMPOSED_OF",
            )


class TestStep5CypherRegex:
    def test_lowercase_type_name_refused(self, mg_with_schema):
        mg = mg_with_schema["mg"]
        g_word = mg_with_schema["g_word"]
        g_letter = mg_with_schema["g_letter"]
        with pytest.raises(CypherError):
            mg.add_intergraph_hyperedge(
                anchors=[(g_word.graph_id, "cat")],
                members=[(g_letter.graph_id, "c"), (g_letter.graph_id, "a")],
                type_name="lowercase",
            )


class TestStep6SchemaTypeLookup:
    def test_unknown_type_under_attached_schema(self, mg_with_schema):
        mg = mg_with_schema["mg"]
        g_word = mg_with_schema["g_word"]
        g_letter = mg_with_schema["g_letter"]
        with pytest.raises(UnknownTypeError, match="Unknown intergraph hyperedge"):
            mg.add_intergraph_hyperedge(
                anchors=[(g_word.graph_id, "cat")],
                members=[(g_letter.graph_id, "c"), (g_letter.graph_id, "a")],
                type_name="MISSING_TYPE",
            )


class TestStep7CanonicalizeBeforeCardinality:
    """P14-A — canonicalize-BEFORE-cardinality catches dedup-collapse-to-1-1."""

    def test_unordered_dedup_collapse_to_1_1_refused(self, mg_with_schema):
        # P14-A — under ordered=False, [a, a] + [b, b] dedups to [a] + [b],
        # which fails the NOT 1-to-1 cardinality check at step 8.
        mg = mg_with_schema["mg"]
        g_letter = mg_with_schema["g_letter"]
        with pytest.raises(SchemaError, match="NOT 1-to-1"):
            mg.add_intergraph_hyperedge(
                anchors=[(g_letter.graph_id, "c"), (g_letter.graph_id, "c")],
                members=[(g_letter.graph_id, "a"), (g_letter.graph_id, "a")],
                type_name="UNORDERED",
            )

    def test_ordered_preserves_duplicates(self, mg_with_schema):
        # Under ordered=True, duplicates within a side are preserved
        # (cat=c+a+t case where word "letter" has repeated chars).
        mg = mg_with_schema["mg"]
        g_word = mg_with_schema["g_word"]
        g_letter = mg_with_schema["g_letter"]
        ihe = mg.add_intergraph_hyperedge(
            anchors=[(g_word.graph_id, "cat")],
            members=[
                (g_letter.graph_id, "c"),
                (g_letter.graph_id, "a"),
                (g_letter.graph_id, "t"),
                (g_letter.graph_id, "a"),  # duplicate "a"
            ],
            type_name="COMPOSED_OF",
        )
        assert len(ihe.members) == 4

    def test_unordered_canonicalization_sorts_lex(self, mg_with_schema):
        mg = mg_with_schema["mg"]
        g_letter = mg_with_schema["g_letter"]
        # Provide [t, c, a] + [a, c]; canonicalizes to [a, c, t] + ...
        # but [a, c] dedups against [a, c] in members — overlap with anchors.
        # Use distinct sides: anchors [t, c], members [a, t]. Canonical
        # anchors=[c, t], canonical members=[a, t]. Overlap at "t" → step 9.
        with pytest.raises(SchemaError, match="overlap"):
            mg.add_intergraph_hyperedge(
                anchors=[(g_letter.graph_id, "t"), (g_letter.graph_id, "c")],
                members=[(g_letter.graph_id, "a"), (g_letter.graph_id, "t")],
                type_name="UNORDERED",
            )


class TestStep8Cardinality:
    def test_one_to_one_refused(self, mg_with_schema):
        mg = mg_with_schema["mg"]
        g_word = mg_with_schema["g_word"]
        g_letter = mg_with_schema["g_letter"]
        with pytest.raises(SchemaError, match="NOT 1-to-1"):
            mg.add_intergraph_hyperedge(
                anchors=[(g_word.graph_id, "cat")],
                members=[(g_letter.graph_id, "c")],
                type_name="COMPOSED_OF",
            )


class TestStep9AnchorMemberOverlap:
    def test_overlap_refused(self, mg_with_schema):
        mg = mg_with_schema["mg"]
        g_letter = mg_with_schema["g_letter"]
        with pytest.raises(SchemaError, match="overlap"):
            mg.add_intergraph_hyperedge(
                # Same (graph, node) pair on both sides.
                anchors=[
                    (g_letter.graph_id, "c"),
                    (g_letter.graph_id, "a"),
                ],
                members=[
                    (g_letter.graph_id, "c"),
                    (g_letter.graph_id, "t"),
                ],
                type_name="UNORDERED",
            )


class TestStep10CompositionalOrderedFalsePermitted:
    """CORE-C2R2 — the P8-A refusal is retired (ADR-0205 §amendment-3.1).

    ``ordered`` expresses a TOTAL order over members. A plan's milestones
    are a SET whose PARTIAL order lives in sibling dependency links
    (ADR-0206 §2), so the refusal made a plan with two parallel milestones
    inexpressible. These tests pin the lift and the two behaviours that
    survive it.
    """

    def test_compositional_unordered_now_constructs(self, mg_with_schema):
        mg = mg_with_schema["mg"]
        g_letter = mg_with_schema["g_letter"]
        ihe = mg.add_intergraph_hyperedge(
            anchors=[(g_letter.graph_id, "c")],
            members=[
                (g_letter.graph_id, "a"),
                (g_letter.graph_id, "t"),
            ],
            type_name="UNORDERED",  # ordered=False
            compositional=True,
        )
        assert ihe.compositional is True
        assert ihe.edge_id in mg.intergraph_hyperedges

    def test_set_semantics_still_apply_under_compositional(self, mg_with_schema):
        """ordered=False sorts AND dedups — the lift does not change that."""
        mg = mg_with_schema["mg"]
        g_letter = mg_with_schema["g_letter"]
        ihe = mg.add_intergraph_hyperedge(
            anchors=[(g_letter.graph_id, "c")],
            members=[
                (g_letter.graph_id, "t"),
                (g_letter.graph_id, "a"),
                (g_letter.graph_id, "t"),
            ],
            type_name="UNORDERED",
            compositional=True,
        )
        assert ihe.members == (
            (g_letter.graph_id, "a"),
            (g_letter.graph_id, "t"),
        )

    def test_compositional_dedup_collapse_to_1_1_still_refuses(
        self, mg_with_schema
    ):
        """P14-A survives the lift: dedup runs BEFORE the cardinality check.

        A single-member composition is an ``IntergraphEdge``
        (ADR-0205 §amendment-1.2), so 1-1 must stay refused here even now
        that compositional+unordered is legal.
        """
        mg = mg_with_schema["mg"]
        g_letter = mg_with_schema["g_letter"]
        with pytest.raises(SchemaError, match="NOT 1-to-1"):
            mg.add_intergraph_hyperedge(
                anchors=[(g_letter.graph_id, "c"), (g_letter.graph_id, "c")],
                members=[(g_letter.graph_id, "a"), (g_letter.graph_id, "a")],
                type_name="UNORDERED",
                compositional=True,
            )

    def test_compositional_ordered_true_accepted(self, mg_with_schema):
        mg = mg_with_schema["mg"]
        g_word = mg_with_schema["g_word"]
        g_letter = mg_with_schema["g_letter"]
        ihe = mg.add_intergraph_hyperedge(
            anchors=[(g_word.graph_id, "cat")],
            members=[
                (g_letter.graph_id, "c"),
                (g_letter.graph_id, "a"),
                (g_letter.graph_id, "t"),
            ],
            type_name="COMPOSED_OF",
            compositional=True,
        )
        assert ihe.compositional is True


class TestStep11ReservedKeyAndPrimitiveCheck:
    def test_reserved_key_refused(self, mg_with_schema):
        mg = mg_with_schema["mg"]
        g_word = mg_with_schema["g_word"]
        g_letter = mg_with_schema["g_letter"]
        with pytest.raises(PropertyShapeError, match="reserved"):
            mg.add_intergraph_hyperedge(
                anchors=[(g_word.graph_id, "cat")],
                members=[
                    (g_letter.graph_id, "c"),
                    (g_letter.graph_id, "a"),
                ],
                type_name="COMPOSED_OF",
                properties={"intergraph_hyperedges": "boom"},
            )


class TestStep12ValidateConstraints:
    def test_role_mismatch_refused(self, mg_with_schema):
        # Validator order: anchor types → member types → anchor graphs →
        # member graphs. With COMPOSED_OF requiring anchor type=Word AND
        # role=word, the FIRST violation triggers; supplying a letter
        # node (type=Letter) hits anchor-type check first. To exercise
        # the role-mismatch branch directly, we add a Word-typed node
        # to the letter graph (type matches; role mismatches).
        mg = mg_with_schema["mg"]
        g_letter = mg_with_schema["g_letter"]
        # Word-typed node placed in letter-role graph.
        g_letter.add_node("synth_word", type_name="Word", node_id="synth_word")
        with pytest.raises(UnknownTypeError, match="anchor graph role"):
            mg.add_intergraph_hyperedge(
                anchors=[(g_letter.graph_id, "synth_word")],
                members=[
                    (g_letter.graph_id, "a"),
                    (g_letter.graph_id, "t"),
                ],
                type_name="COMPOSED_OF",
            )

    def test_node_type_mismatch_refused(self, mg_with_schema):
        mg = mg_with_schema["mg"]
        g_word = mg_with_schema["g_word"]
        g_letter = mg_with_schema["g_letter"]
        # Need an anchor node with type != "Word".
        g_word.add_node("non_word", type_name="NotWord", node_id="non_word")
        with pytest.raises(UnknownTypeError, match="anchor node type"):
            mg.add_intergraph_hyperedge(
                anchors=[(g_word.graph_id, "non_word")],
                members=[
                    (g_letter.graph_id, "c"),
                    (g_letter.graph_id, "a"),
                ],
                type_name="COMPOSED_OF",
            )


class TestStep13StrictPropertyType:
    def test_property_type_mismatch_refused(self, mg_with_schema):
        mg = mg_with_schema["mg"]
        g_word = mg_with_schema["g_word"]
        g_letter = mg_with_schema["g_letter"]
        with pytest.raises(PropertyShapeError):
            mg.add_intergraph_hyperedge(
                anchors=[(g_word.graph_id, "cat")],
                members=[
                    (g_letter.graph_id, "c"),
                    (g_letter.graph_id, "a"),
                ],
                type_name="COMPOSED_OF",
                properties={"weight": "not_a_float"},
            )


class TestNoSchemaPath:
    def test_no_schema_attached_passes_with_default_ordered_true(self):
        # Per P9-A — no schema → ordered=True default (permissive).
        mg = Metagraph(name="m")
        g_word = Graph(name="word", role="word")
        g_letter = Graph(name="letter", role="letter")
        mg.add_graph(g_word)
        mg.add_graph(g_letter)
        g_word.add_node("cat", type_name="Word", node_id="cat")
        g_letter.add_node("c", type_name="Letter", node_id="c")
        g_letter.add_node("a", type_name="Letter", node_id="a")
        # No schema. Allows duplicates within a side (ordered=True default).
        ihe = mg.add_intergraph_hyperedge(
            anchors=[(g_word.graph_id, "cat")],
            members=[
                (g_letter.graph_id, "c"),
                (g_letter.graph_id, "a"),
                (g_letter.graph_id, "a"),  # duplicate accepted
            ],
            type_name="ANYTYPE",
        )
        assert len(ihe.members) == 3
