"""Phase 17 retirement — minimal versioning corpus for CLI tests.

Constructs a small Metagraph with the 6 Global named role-graphs;
the ``ontology`` role-graph holds DOLCE IRIs at TWO versions (4.1
and 4.2) — exercising the canonical "two versions in one role-graph"
shape that ADR-0150 §amendment-3 ratifies as the model.

State-file persistence helper mirrors Phase 16
``save_corpus_to_state_dir`` so CLI tests can load via
``--metagraph NAME``.
"""

from __future__ import annotations

import os
from pathlib import Path

from mindsos_core import Metagraph
from mindsos_knowledge.bootstrap import ensure_global_role_graph
from mindsos_knowledge.identifiers import (
    dolce_iri,
    framenet_frame_iri,
    oewn_synset_iri,
)


CORPUS_NAME = "phase17_versioning_corpus"


def build_corpus() -> Metagraph:
    """Build the Phase 17 retirement versioning corpus deterministically.

    Layout:
    * ``ontology`` — 3 nodes at v4.1 + 2 nodes at v4.2 (mixed versions
      in the same role-graph per ADR-0150 §amendment-3).
    * ``lexicon`` — 1 node at v2024 (single-version).
    * ``concepts`` — 1 node at v1.7 (single-version).
    * ``promoted-pipelines`` / ``task-patterns`` / ``problem-trace`` —
      empty (the enumerator returns empty set).
    """
    mg = Metagraph(
        name=CORPUS_NAME, metagraph_id="phase17-versioning-corpus-mg-id"
    )
    for role in (
        "ontology",
        "lexicon",
        "concepts",
        "promoted-pipelines",
        "task-patterns",
        "problem-trace",
    ):
        ensure_global_role_graph(mg, role)

    onto = ensure_global_role_graph(mg, "ontology")  # idempotent → existing
    # v4.1
    onto.add_node(
        value="PhysicalObject",
        type_name="Class",
        node_id=dolce_iri("4.1", "PhysicalObject"),
    )
    onto.add_node(
        value="Event", type_name="Class", node_id=dolce_iri("4.1", "Event")
    )
    onto.add_node(
        value="Quality",
        type_name="Class",
        node_id=dolce_iri("4.1", "Quality"),
    )
    # v4.2 — same role-graph; distinct nodes
    onto.add_node(
        value="PhysicalObject",
        type_name="Class",
        node_id=dolce_iri("4.2", "PhysicalObject"),
    )
    onto.add_node(
        value="Process",
        type_name="Class",
        node_id=dolce_iri("4.2", "Process"),
    )

    lex = ensure_global_role_graph(mg, "lexicon")
    lex.add_node(
        value="00001",
        type_name="Synset",
        node_id=oewn_synset_iri("2024", "00001", "n"),
    )

    cnp = ensure_global_role_graph(mg, "concepts")
    cnp.add_node(
        value="Motion",
        type_name="Frame",
        node_id=framenet_frame_iri("1.7", "Motion"),
    )

    return mg


def save_corpus_to_state_dir(
    state_dir: Path, *, name: str = CORPUS_NAME
) -> None:
    """Persist the corpus :class:`Metagraph` as state-files under ``state_dir``."""
    from mindsos_cli import state as state_mod
    from mindsos_cli.commands.graph import _graph_to_state
    from mindsos_cli.commands.metagraph import _metagraph_to_state

    os.environ["MINDSOS_STATE_DIR"] = str(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    mg = build_corpus()
    for graph in mg.graphs.values():
        state_mod.save_graph_state(
            graph.name,
            _graph_to_state(graph, schema_name=None, metagraph_name=mg.name),
        )
    state_mod.save_metagraph_state(name, _metagraph_to_state(mg))
