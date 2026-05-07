"""Phase 05c — IntergraphHyperEdge dataclass invariants.

Direct-construction safety: __post_init__ runs cypher regex + cardinality
+ overlap checks; tuple-conversion of anchors/members regardless of
compositional flag (P2-refined). __setattr__ enforces strict scope per
P27 — anchors/members/properties/compositional all blocked on direct
user mutation; factory bypasses via object.__setattr__.
"""

from __future__ import annotations

import pytest

from mindsos_core import (
    CompositionalImmutableError,
    CypherError,
    IntergraphHyperEdge,
    SchemaError,
)


class TestKwOnly:
    def test_dataclass_is_kw_only(self):
        # kw_only=True — positional construction fails.
        with pytest.raises(TypeError):
            IntergraphHyperEdge(  # type: ignore[call-arg]
                (("g1", "n1"),), (("g2", "n2"), ("g2", "n3")),
                "T",
            )

    def test_minimal_valid_construction(self):
        ihe = IntergraphHyperEdge(
            anchors=(("g1", "n1"),),
            members=(("g2", "n2"), ("g2", "n3")),
            type_name="T",
        )
        assert ihe.anchors == (("g1", "n1"),)
        assert len(ihe.members) == 2
        assert ihe.compositional is False
        assert ihe.label is None
        assert ihe.properties == {}
        assert ihe.edge_id  # auto-minted UUID4 string


class TestTupleConversion:
    def test_list_of_list_input_converts_to_tuple_of_tuple(self):
        # Tuple-conversion at __post_init__ regardless of compositional.
        ihe = IntergraphHyperEdge(
            anchors=[["g1", "n1"]],  # list-of-list
            members=[["g2", "n2"], ["g2", "n3"]],
            type_name="T",
        )
        assert isinstance(ihe.anchors, tuple)
        assert isinstance(ihe.members, tuple)
        assert all(isinstance(p, tuple) for p in ihe.anchors)
        assert all(isinstance(p, tuple) for p in ihe.members)

    def test_idempotent_on_already_tuple(self):
        anchors = (("g1", "n1"),)
        members = (("g2", "n2"), ("g2", "n3"))
        ihe = IntergraphHyperEdge(
            anchors=anchors, members=members, type_name="T",
        )
        assert ihe.anchors == anchors
        assert ihe.members == members


class TestCypherRegex:
    def test_valid_type_name(self):
        # Standard upper-snake-case passes.
        IntergraphHyperEdge(
            anchors=(("g1", "n1"),),
            members=(("g2", "n2"), ("g2", "n3")),
            type_name="COMPOSED_OF",
        )

    def test_lowercase_type_name_refused(self):
        with pytest.raises(CypherError):
            IntergraphHyperEdge(
                anchors=(("g1", "n1"),),
                members=(("g2", "n2"), ("g2", "n3")),
                type_name="composed_of",
            )

    def test_starts_with_digit_refused(self):
        with pytest.raises(CypherError):
            IntergraphHyperEdge(
                anchors=(("g1", "n1"),),
                members=(("g2", "n2"), ("g2", "n3")),
                type_name="9COMPOSED",
            )


class TestCardinality:
    def test_zero_anchors_refused(self):
        with pytest.raises(SchemaError, match="at least 1 anchor"):
            IntergraphHyperEdge(
                anchors=(),
                members=(("g2", "n2"), ("g2", "n3")),
                type_name="T",
            )

    def test_zero_members_refused(self):
        with pytest.raises(SchemaError, match="at least 1 member"):
            IntergraphHyperEdge(
                anchors=(("g1", "n1"),),
                members=(),
                type_name="T",
            )

    def test_one_to_one_refused_use_intergraph_edge(self):
        with pytest.raises(SchemaError, match="NOT 1-to-1"):
            IntergraphHyperEdge(
                anchors=(("g1", "n1"),),
                members=(("g2", "n2"),),
                type_name="T",
            )

    def test_one_to_many_accepted(self):
        IntergraphHyperEdge(
            anchors=(("g1", "n1"),),
            members=(("g2", "n2"), ("g2", "n3")),
            type_name="T",
        )

    def test_many_to_one_accepted(self):
        IntergraphHyperEdge(
            anchors=(("g1", "a"), ("g1", "b")),
            members=(("g2", "x"),),
            type_name="T",
        )

    def test_many_to_many_accepted(self):
        IntergraphHyperEdge(
            anchors=(("g1", "a"), ("g1", "b")),
            members=(("g2", "x"), ("g2", "y")),
            type_name="T",
        )

    def test_duplicates_within_a_side_allowed_at_dataclass_level(self):
        # Direct-construction stores already-canonicalized data; the
        # factory's canonicalization handles ordered=False dedup. At
        # the dataclass level, duplicates pass — they're the cat=c+a+t
        # / "letter" case where ordered=True preserves duplicates.
        ihe = IntergraphHyperEdge(
            anchors=(("g1", "n1"),),
            members=(
                ("g2", "l"), ("g2", "e"), ("g2", "t"),
                ("g2", "t"), ("g2", "e"), ("g2", "r"),
            ),
            type_name="COMPOSED_OF",
        )
        assert len(ihe.members) == 6


class TestAnchorMemberOverlap:
    def test_overlap_refused(self):
        with pytest.raises(SchemaError, match="overlap forbidden"):
            IntergraphHyperEdge(
                anchors=(("g1", "shared"), ("g1", "a")),
                members=(("g1", "shared"), ("g2", "x")),
                type_name="T",
            )

    def test_distinct_node_ids_in_same_graph_no_overlap(self):
        # Same graph but distinct node ids on each side → no overlap.
        IntergraphHyperEdge(
            anchors=(("g1", "a"),),
            members=(("g1", "b"), ("g1", "c")),
            type_name="T",
        )


class TestSetAttrImmutability:
    """P27 (this chat A) — strict scope: anchors / members / properties /
    compositional / type_name / edge_id / label all blocked on direct
    user mutation. Factory bypasses via ``object.__setattr__``."""

    def _ihe(self, *, compositional: bool = False) -> IntergraphHyperEdge:
        return IntergraphHyperEdge(
            anchors=(("g1", "n1"),),
            members=(("g2", "n2"), ("g2", "n3")),
            type_name="T",
            compositional=compositional,
        )

    def test_compositional_immutable_post_init_when_false(self):
        ihe = self._ihe(compositional=False)
        with pytest.raises(CompositionalImmutableError):
            ihe.compositional = True

    def test_compositional_immutable_post_init_when_true(self):
        ihe = self._ihe(compositional=True)
        with pytest.raises(CompositionalImmutableError):
            ihe.compositional = False

    def test_anchors_immutable_post_init_non_compositional(self):
        # P27 (this chat A) — strict scope; non-compositional ALSO blocks.
        ihe = self._ihe(compositional=False)
        with pytest.raises(CompositionalImmutableError):
            ihe.anchors = (("g1", "different"),)

    def test_members_immutable_post_init_non_compositional(self):
        ihe = self._ihe(compositional=False)
        with pytest.raises(CompositionalImmutableError):
            ihe.members = (("g2", "x"), ("g2", "y"))

    def test_properties_dict_reassignment_blocked(self):
        ihe = self._ihe()
        with pytest.raises(CompositionalImmutableError):
            ihe.properties = {"k": "v"}

    def test_type_name_immutable_post_init(self):
        ihe = self._ihe()
        with pytest.raises(CompositionalImmutableError):
            ihe.type_name = "OTHER"

    def test_edge_id_immutable_post_init(self):
        ihe = self._ihe()
        with pytest.raises(CompositionalImmutableError):
            ihe.edge_id = "new-id"

    def test_label_immutable_post_init(self):
        ihe = self._ihe()
        with pytest.raises(CompositionalImmutableError):
            ihe.label = "new"

    def test_factory_bypass_via_object_setattr(self):
        # Update path uses object.__setattr__; verify that path still works.
        ihe = self._ihe()
        new_anchors = (("g1", "different"),)
        object.__setattr__(ihe, "anchors", new_anchors)
        assert ihe.anchors == new_anchors


class TestEqualityAndHashing:
    def test_eq_by_edge_id(self):
        a = IntergraphHyperEdge(
            anchors=(("g1", "n1"),),
            members=(("g2", "n2"), ("g2", "n3")),
            type_name="T",
            edge_id="same-id",
        )
        b = IntergraphHyperEdge(
            anchors=(("gA", "x"),),
            members=(("gB", "y"), ("gB", "z")),
            type_name="OTHER",
            edge_id="same-id",
        )
        assert a == b
        assert hash(a) == hash(b)

    def test_neq_different_edge_ids(self):
        a = IntergraphHyperEdge(
            anchors=(("g1", "n1"),),
            members=(("g2", "n2"), ("g2", "n3")),
            type_name="T",
            edge_id="A",
        )
        b = IntergraphHyperEdge(
            anchors=(("g1", "n1"),),
            members=(("g2", "n2"), ("g2", "n3")),
            type_name="T",
            edge_id="B",
        )
        assert a != b

    def test_repr_carries_compositional_marker(self):
        ihe = IntergraphHyperEdge(
            anchors=(("g1", "n1"),),
            members=(("g2", "n2"), ("g2", "n3")),
            type_name="T",
            compositional=True,
        )
        assert "compositional" in repr(ihe)


class TestEdgeIdOverride:
    def test_caller_supplied_edge_id_preserved(self):
        ihe = IntergraphHyperEdge(
            anchors=(("g1", "n1"),),
            members=(("g2", "n2"), ("g2", "n3")),
            type_name="T",
            edge_id="custom-edge-id",
        )
        assert ihe.edge_id == "custom-edge-id"
