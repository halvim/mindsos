"""Phase 29 R4 PB-34 — sentinel locking the no-MetagraphSchema precondition.

Phase 28 bootstraps both Global and Local Metagraphs WITHOUT attaching
a MetagraphSchema (`mg.schema is None`). Phase 29's cross-graph
MetaEdge discovery code path relies on this — `Metagraph.add_metaedge`
bypasses MetaEdgeType validation when `self.schema is None`. If a
future phase attaches a MetagraphSchema to the L3 metagraph, MetaEdge
writes for `EDGE_TYPE_COMPAT` will start failing unless that phase
ALSO registers `MetaEdgeType(EDGE_TYPE_COMPAT, ...)` atomically.

This sentinel will FAIL when that future phase ships — flag for the
implementer to add MetaEdgeType registration in the same change-set.
"""

from __future__ import annotations

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    CapacityLayer,
)


def test_global_metagraph_has_no_attached_schema():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    assert cl.global_metagraph().schema is None, (
        "L3 Global Metagraph unexpectedly has a MetagraphSchema attached. "
        "Phase 29 discovery's MetaEdge writes depend on schema=None to "
        "bypass MetaEdgeType validation. If a future phase attaches a "
        "schema, ALSO register MetaEdgeType(EDGE_TYPE_COMPAT, ...) in "
        "the same change-set (see ADR-0069 §Implementation + Phase 29 "
        "R4 PB-34)."
    )


def test_local_metagraph_has_no_attached_schema():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    local_mg = cl.local_metagraph("user1")
    assert local_mg.schema is None, (
        "L3 Local Metagraph unexpectedly has a MetagraphSchema attached. "
        "See test_global_metagraph_has_no_attached_schema for the "
        "implications + remediation."
    )
