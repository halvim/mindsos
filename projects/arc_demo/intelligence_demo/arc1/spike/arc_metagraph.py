"""(b) The Arc metagraph — a GENERATED DEBUG-ONLY sectional view (GF-1).

**Not a source of truth.** Under GF-1 (LOCKED 2026-06-21) the executed
capability **bodies** are canonical; the registered bipartite PRODUCES/
CONSUMES topology is derived-and-asserted (provenance). This module is the
*third* representation that previously drifted — it asserted a
``moved → REQUIRES → same_shape`` IntergraphEdge as if REQUIRES were an
ontology relation. It is not: ``moved`` shares a private normalize/compare
helper, **not** the ``same_shape`` capacity (GF-2). REQUIRES is therefore
**dropped as an ontology relation**.

What remains is a flat **debug grouping** of the registered capability IRIs
into operand *sections* (``atoms`` / ``object_comparator`` / ``profile``) for
the Map panel. It asserts **no dependency edges**. The canonical dependency
substrate is the registered PRODUCES/CONSUMES topology (walked by
``find_pipeline``) plus the bodies — see ``arc_capacities.py``.
"""

from __future__ import annotations

from typing import Optional

from mindsos_core import Graph, Metagraph
from mindsos_capacity.identifiers import capacity_iri

from .arc_capacities import CATEGORY_COMPARATOR

#: section graph → the capabilities it contains (operand-axis debug grouping).
SECTIONS = {
    "atoms": ["same_object", "same_shape", "same_point"],
    "object_comparator": ["moved"],
    "profile": ["compare_grid_dimension", "compare_palette"],
}


def _iri(name: str) -> str:
    # All arc induce/profile capabilities register under the comparator family.
    return capacity_iri(CATEGORY_COMPARATOR, name)


def build_arc_metagraph() -> Metagraph:
    """Build the debug-only sectional view: section graphs of capability
    nodes, **no dependency edges** (REQUIRES dropped, GF-1)."""
    mg = Metagraph("arc")
    for section, caps in SECTIONS.items():
        g = Graph(section, role=section)
        mg.add_graph(g)
        for name in caps:
            g.add_node(value=name, type_name="Capacity", node_id=_iri(name))
    return mg


def summary(mg: Optional[Metagraph] = None) -> dict:
    """Compact JSON view for the debug UI. ``requires`` is intentionally
    empty: this is a debug-only view, not an ontology overlay (GF-1)."""
    mg = mg or build_arc_metagraph()
    graphs = {g.name: [n.value for n in g.nodes.values()] for g in mg.graphs.values()}
    return {
        "metagraph": mg.name,
        "graphs": graphs,
        "requires": [],  # GF-1: no asserted dependency edges (debug-only view)
        "note": "debug-only sectional view; canonical dependency = registered "
                "PRODUCES/CONSUMES topology + bodies (GF-1).",
    }
