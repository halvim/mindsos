"""(b) The Arc metagraph — operand/section overlay in L1/L3 (choice A2).

A separate Core ``Metagraph`` whose contained graphs are the capability
**sections** (``atoms`` / ``object_comparator`` / ``profile``). It references the
same capabilities the ``CapacityLayer`` registers under their **functional**
families (``comparator``, …) by their capacity-IRI — this overlay is the
**operand axis**, additive, leaving the functional axis (and the Capacities
panel) intact (A2).

The ``moved → requires → same_shape`` dependency is a **binary IntergraphEdge**
(single requirement; colour is ``moved``'s internal guard). A *compositional*
``IntergraphHyperEdge`` would apply only if ``moved`` required ≥2 atoms (e.g. if
``same_colour`` were reintroduced) — hyperedges refuse 1:1 cardinality.
"""

from __future__ import annotations

from typing import Optional

from mindsos_core import Graph, Metagraph
from mindsos_capacity.identifiers import capacity_iri

from .arc_capacities import CATEGORY_COMPARATOR

#: section graph → the capabilities it contains (operand axis).
SECTIONS = {
    "atoms": ["same_object", "same_shape", "same_point"],
    "object_comparator": ["moved"],
    "profile": ["compare_grid_dimension", "compare_palette"],
}

#: requires edges: (source_section, source_cap, target_section, target_cap).
REQUIRES = [("object_comparator", "moved", "atoms", "same_shape")]


def _iri(name: str) -> str:
    # All arc induce/profile capabilities register under the comparator family.
    return capacity_iri(CATEGORY_COMPARATOR, name)


def build_arc_metagraph() -> Metagraph:
    mg = Metagraph("arc")
    graphs = {}
    for section, caps in SECTIONS.items():
        g = Graph(section, role=section)
        mg.add_graph(g)
        graphs[section] = g
        for name in caps:
            g.add_node(value=name, type_name="Capacity", node_id=_iri(name))
    for src_sec, src_cap, tgt_sec, tgt_cap in REQUIRES:
        mg.add_intergraph_edge(
            graphs[src_sec].graph_id, _iri(src_cap),
            graphs[tgt_sec].graph_id, _iri(tgt_cap),
            "REQUIRES",
        )
    return mg


def summary(mg: Optional[Metagraph] = None) -> dict:
    """Compact JSON view of the Arc metagraph for the debug UI / verification."""
    mg = mg or build_arc_metagraph()
    graphs = {g.name: [n.value for n in g.nodes.values()] for g in mg.graphs.values()}
    edges = [
        {"type": e.type_name,
         "from": e.source_node_id.split(":")[-1],
         "to": e.target_node_id.split(":")[-1]}
        for e in mg.intergraph_edges.values()
    ]
    return {"metagraph": mg.name, "graphs": graphs, "requires": edges}
