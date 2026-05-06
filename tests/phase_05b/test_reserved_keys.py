"""RESERVED_PROPERTY_KEYS extension tests (Pushback 18-A + 6 carry-forward).

Phase 05b adds three new reserved keys:
* ``intergraph_edges`` — top-level metagraph state v=2 array.
* ``schema_name`` — top-level metagraph state v=2 reference (also on
  graph state v=2 since Phase 04, but only reserved at user-property
  scope from 05b onward).
* ``_compositional`` — future Phase 07 Cypher emit's stamped property
  on the anchor-node Pattern B.
"""

from __future__ import annotations

import pytest

from mindsos_core import PropertyShapeError
from mindsos_core.schema.validation import (
    RESERVED_PROPERTY_KEYS,
    validate_user_properties,
)


class TestReservedKeysSetMembership:
    def test_intergraph_edges_reserved(self):
        assert "intergraph_edges" in RESERVED_PROPERTY_KEYS

    def test_schema_name_reserved(self):
        assert "schema_name" in RESERVED_PROPERTY_KEYS

    def test_underscore_compositional_reserved(self):
        assert "_compositional" in RESERVED_PROPERTY_KEYS

    def test_compositional_without_underscore_NOT_reserved(self):
        """Pushback 2-A — only the underscore-prefixed Cypher-property name."""
        assert "compositional" not in RESERVED_PROPERTY_KEYS

    def test_05a_p13_keys_still_reserved(self):
        """Phase 05a P13 keys carry forward."""
        for k in (
            "_state_version", "contained_graphs", "metaedges",
            "metahyperedges", "metagraph_name",
        ):
            assert k in RESERVED_PROPERTY_KEYS


class TestValidateUserPropertiesRejection:
    def test_intergraph_edges_rejected(self):
        with pytest.raises(PropertyShapeError):
            validate_user_properties({"intergraph_edges": []}, scope="x")

    def test_schema_name_rejected(self):
        with pytest.raises(PropertyShapeError):
            validate_user_properties({"schema_name": "ms1"}, scope="x")

    def test_underscore_compositional_rejected(self):
        with pytest.raises(PropertyShapeError):
            validate_user_properties({"_compositional": True}, scope="x")

    def test_compositional_without_underscore_accepted(self):
        """``compositional`` (no underscore) is a user-allowed key."""
        result = validate_user_properties({"compositional": True}, scope="x")
        assert result == {"compositional": True}

    def test_legacy_user_keys_still_accepted(self):
        """``name`` and ``properties`` are deliberately NOT reserved."""
        result = validate_user_properties(
            {"name": "Alice", "properties": "self-ref"}, scope="x",
        )
        assert result == {"name": "Alice", "properties": "self-ref"}
