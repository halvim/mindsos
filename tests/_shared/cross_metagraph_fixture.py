"""Cross-metagraph fixture for Phase 09 XRef integration tests (RR-13).

Phase 09 needs two distinct :class:`Metagraph` instances per integration
test (one source, one target) so XRef writes can verify cross-metagraph
behavior. This helper produces a function-scoped pair with disjoint
identity registries + minimal seeded graphs + nodes — enough surface
for ``add_xref`` write-time validation (M4) without overpopulating the
test fixture.

Usage::

    from tests._shared.cross_metagraph_fixture import make_source_and_target_metagraphs

    def test_something():
        source, target = make_source_and_target_metagraphs()
        source.add_xref(
            source_id="src-node-1",
            target_metagraph_id=target.metagraph_id,
            target_role="lexicon",
            target_id="tgt-node-1",
            ref_type="SPECIALISES",
            target_metagraph=target,
        )

The pair is returned plain — callers can mutate freely. Both
metagraphs use UUID4 strategy with explicit IDs for deterministic
test output.
"""

from __future__ import annotations

from typing import Tuple

from mindsos_core import Graph, Metagraph


def make_source_and_target_metagraphs() -> Tuple[Metagraph, Metagraph]:
    """Build two distinct Metagraph instances ready for cross-XRef tests.

    Source metagraph:
      * 1 contained graph (``role="ontology"``)
      * 2 nodes registered (``src-node-1``, ``src-node-2``)
      * disjoint identity registry

    Target metagraph:
      * 1 contained graph (``role="lexicon"``)
      * 2 nodes registered (``tgt-node-1``, ``tgt-node-2``)
      * disjoint identity registry

    Both metagraphs have explicit deterministic ids
    (``mg-source-test`` / ``mg-target-test``) so tests asserting
    against specific IDs survive ordering changes.
    """
    source = Metagraph(name="source-test", metagraph_id="mg-source-test")
    src_g = Graph(name="src-onto", role="ontology")
    source.add_graph(src_g)
    src_g.add_node("src-node-1", type_name="Concept", node_id="src-node-1")
    src_g.add_node("src-node-2", type_name="Concept", node_id="src-node-2")

    target = Metagraph(name="target-test", metagraph_id="mg-target-test")
    tgt_g = Graph(name="tgt-lex", role="lexicon")
    target.add_graph(tgt_g)
    tgt_g.add_node("tgt-node-1", type_name="Word", node_id="tgt-node-1")
    tgt_g.add_node("tgt-node-2", type_name="Word", node_id="tgt-node-2")

    return source, target


__all__ = ["make_source_and_target_metagraphs"]
