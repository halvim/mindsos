"""Deterministic similarity-test corpus builder (Phase 16 PB-V2).

Constructs a small :class:`~mindsos_core.Metagraph` populated with
known-relationship nodes across the 3 Phase 15a importer-target roles
(ontology / lexicon / concepts). The corpus drives:

* Per-role extractor tests (deterministic feature outputs).
* Similarity tests (known Levenshtein / Jaccard pair scores).
* CLI tests (state-file rehydrate round-trip).

The corpus is built in-process by tests; the
:func:`save_corpus_to_state_dir` helper persists it to a state-dir
for CLI tests that need to load via ``--metagraph NAME``.

Per Phase 16 PB-V2 sentinel: :func:`build_corpus` is referentially
transparent — two calls produce equal Metagraph content.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

from mindsos_core import Graph, Metagraph


CORPUS_NAME = "phase16_corpus"

# Deterministic node IRIs — use the IRI builder convention (last
# `:`-separated segment is the tail used by the Levenshtein scorer).
ONT_CLASS_PHYS = "dolce:Class:PhysicalObject"
ONT_CLASS_PHYS_NEAR = "dolce:Class:PhysicalObjects"  # +1 char — Lev=0.94
ONT_CLASS_ABS = "dolce:Class:AbstractObject"
ONT_CLASS_ENT = "dolce:Class:Entity"

LEX_SYNSET_CAR = "oewn:Synset:car.n.01"
LEX_SYNSET_AUTO = "oewn:Synset:automobile.n.01"
LEX_SYNSET_VEHICLE = "oewn:Synset:vehicle.n.01"
LEX_LEMMA_CAR = "oewn:Lemma:car"
LEX_LEMMA_AUTO = "oewn:Lemma:automobile"

CON_FRAME_MOTION = "framenet:Frame:Motion"
CON_FRAME_MOTION_NEAR = "framenet:Frame:Movement"
CON_FRAME_EVENT = "framenet:Frame:Event"
CON_FE_AGENT = "framenet:FE:Agent"
CON_FE_THEME = "framenet:FE:Theme"


def build_corpus() -> Metagraph:
    """Build the Phase 16 similarity-test corpus deterministically.

    Returns a fresh :class:`Metagraph` with 3 contained graphs
    (ontology / lexicon / concepts), each populated with known-shape
    nodes + edges driving the scorers.
    """
    mg = Metagraph(name=CORPUS_NAME, metagraph_id="phase16-corpus-mg-id")

    # Ontology graph (DOLCE-style).
    ont = Graph(
        name=f"{CORPUS_NAME}_ontology",
        role="ontology",
        graph_id="phase16-corpus-ontology",
    )
    n_phys = ont.add_node(value="PhysicalObject", type_name="Class", node_id=ONT_CLASS_PHYS)
    n_phys_near = ont.add_node(
        value="PhysicalObjects", type_name="Class", node_id=ONT_CLASS_PHYS_NEAR
    )
    n_abs = ont.add_node(value="AbstractObject", type_name="Class", node_id=ONT_CLASS_ABS)
    n_ent = ont.add_node(value="Entity", type_name="Class", node_id=ONT_CLASS_ENT)
    ont.add_edge(source=n_phys, target=n_ent, type_name="SUBCLASS_OF")
    ont.add_edge(source=n_phys_near, target=n_ent, type_name="SUBCLASS_OF")
    ont.add_edge(source=n_abs, target=n_ent, type_name="SUBCLASS_OF")
    mg.add_graph(ont)

    # Lexicon graph (OEWN-style).
    lex = Graph(
        name=f"{CORPUS_NAME}_lexicon",
        role="lexicon",
        graph_id="phase16-corpus-lexicon",
    )
    n_synset_car = lex.add_node(
        value="car.n.01", type_name="Synset", node_id=LEX_SYNSET_CAR
    )
    n_synset_auto = lex.add_node(
        value="automobile.n.01", type_name="Synset", node_id=LEX_SYNSET_AUTO
    )
    n_synset_vehicle = lex.add_node(
        value="vehicle.n.01", type_name="Synset", node_id=LEX_SYNSET_VEHICLE
    )
    n_lemma_car = lex.add_node(value="car", type_name="Lemma", node_id=LEX_LEMMA_CAR)
    n_lemma_auto = lex.add_node(
        value="automobile", type_name="Lemma", node_id=LEX_LEMMA_AUTO
    )
    # car HYPERNYM_OF vehicle (taxonomic parent).
    lex.add_edge(source=n_synset_car, target=n_synset_vehicle, type_name="HYPERNYM_OF")
    lex.add_edge(
        source=n_synset_auto, target=n_synset_vehicle, type_name="HYPERNYM_OF"
    )
    # Senses link Lemma → Synset (we approximate via IN_SYNSET on the Lemma).
    lex.add_edge(source=n_lemma_car, target=n_synset_car, type_name="IN_SYNSET")
    lex.add_edge(source=n_lemma_auto, target=n_synset_auto, type_name="IN_SYNSET")
    mg.add_graph(lex)

    # Concepts graph (FrameNet-style).
    con = Graph(
        name=f"{CORPUS_NAME}_concepts",
        role="concepts",
        graph_id="phase16-corpus-concepts",
    )
    n_motion = con.add_node(
        value="Motion", type_name="Frame", node_id=CON_FRAME_MOTION
    )
    n_motion_near = con.add_node(
        value="Movement", type_name="Frame", node_id=CON_FRAME_MOTION_NEAR
    )
    n_event = con.add_node(value="Event", type_name="Frame", node_id=CON_FRAME_EVENT)
    n_fe_agent = con.add_node(
        value="Agent", type_name="FrameElement", node_id=CON_FE_AGENT
    )
    n_fe_theme = con.add_node(
        value="Theme", type_name="FrameElement", node_id=CON_FE_THEME
    )
    con.add_edge(source=n_motion, target=n_event, type_name="INHERITS_FROM")
    con.add_edge(source=n_motion_near, target=n_event, type_name="INHERITS_FROM")
    con.add_edge(source=n_motion, target=n_fe_agent, type_name="HAS_FE")
    con.add_edge(source=n_motion, target=n_fe_theme, type_name="HAS_FE")
    con.add_edge(source=n_motion_near, target=n_fe_agent, type_name="HAS_FE")
    mg.add_graph(con)

    return mg


def save_corpus_to_state_dir(state_dir: Path, *, name: str = CORPUS_NAME) -> None:
    """Persist the corpus :class:`Metagraph` as state-files under ``state_dir``.

    Used by CLI tests that need a state-file at a known path. Writes
    one ``graph-<name>.json`` per contained graph plus one
    ``metagraph-<name>.json`` per state-file conventions (Phase 03+).

    Sets ``MINDSOS_STATE_DIR`` to ``state_dir`` for the duration of the
    test caller's call (the env-var read by
    :func:`mindsos_cli.state.state_dir`).
    """
    from mindsos_cli import state as state_mod
    from mindsos_cli.commands.graph import _graph_to_state
    from mindsos_cli.commands.metagraph import _metagraph_to_state

    os.environ["MINDSOS_STATE_DIR"] = str(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    mg = build_corpus()
    # Save each contained graph by name.
    for graph in mg.graphs.values():
        state_mod.save_graph_state(graph.name, _graph_to_state(graph))
    # Save the metagraph anchor.
    state_mod.save_metagraph_state(name, _metagraph_to_state(mg))


def corpus_fingerprint() -> Tuple[int, int, int, frozenset[str]]:
    """Stable shape-summary used by the regenerate-determinism sentinel.

    Returns (#graphs, #nodes-across-graphs, #edges-across-graphs,
    frozenset-of-node-ids-across-graphs). Two ``build_corpus()`` calls
    MUST produce equal fingerprints.
    """
    mg = build_corpus()
    n_graphs = len(mg.graphs)
    n_nodes = sum(len(g.nodes) for g in mg.graphs.values())
    n_edges = sum(
        len(list(g.iter_edges(include_deprecated=False))) for g in mg.graphs.values()
    )
    node_ids = frozenset(
        n.node_id for g in mg.graphs.values() for n in g.nodes.values()
    )
    return (n_graphs, n_nodes, n_edges, node_ids)
