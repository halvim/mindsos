"""Phase 13 PB-17 — dimensional-snapshot sentinel.

Each schema's exact (nodes, edges, hyperedges) dimensions pinned.
Any future edit forces an explicit table bump — the reviewer sees it
in the diff. Replaces 8 separate "node-type set + edge-type set"
assertions with one parametric table.

This is the "confirmation fixture" PHASE_MAP §13 Risks calls for.
"""

from __future__ import annotations

import pytest

from mindsos_knowledge.schemas import (
    build_alignment_schema,
    build_capacity_state_schema,
    build_concepts_schema,
    build_lexicon_schema,
    build_memories_schema,
    build_ontology_schema,
    build_problem_trace_schema,
    build_promoted_pipelines_schema,
    build_task_patterns_schema,
)


EXPECTED_DIMENSIONS: dict[str, dict[str, int]] = {
    "ontology":            {"nodes": 10, "edges": 13, "hyperedges": 7},
    "lexicon":             {"nodes": 4,  "edges": 22, "hyperedges": 0},
    "concepts":            {"nodes": 4,  "edges": 11, "hyperedges": 0},
    "alignment":           {"nodes": 1,  "edges": 8,  "hyperedges": 0},
    "promoted_pipelines":  {"nodes": 2,  "edges": 2,  "hyperedges": 0},
    "task_patterns":       {"nodes": 2,  "edges": 2,  "hyperedges": 0},
    "memories":            {"nodes": 1,  "edges": 2,  "hyperedges": 0},
    "problem_trace":       {"nodes": 1,  "edges": 0,  "hyperedges": 0},
    "capacity_state":      {"nodes": 1,  "edges": 0,  "hyperedges": 0},
}


_BUILDERS = {
    "ontology": build_ontology_schema,
    "lexicon": build_lexicon_schema,
    "concepts": build_concepts_schema,
    "alignment": build_alignment_schema,
    "promoted_pipelines": build_promoted_pipelines_schema,
    "task_patterns": build_task_patterns_schema,
    "memories": build_memories_schema,
    "problem_trace": build_problem_trace_schema,
    "capacity_state": build_capacity_state_schema,
}


@pytest.mark.parametrize("name", sorted(EXPECTED_DIMENSIONS))
def test_dimensional_snapshot(name: str) -> None:
    expected = EXPECTED_DIMENSIONS[name]
    s = _BUILDERS[name]()
    assert len(s.node_types) == expected["nodes"], (
        f"{name}: expected {expected['nodes']} node types, got {len(s.node_types)}"
    )
    assert len(s.edge_types) == expected["edges"], (
        f"{name}: expected {expected['edges']} edge types, got {len(s.edge_types)}"
    )
    assert len(s.hyperedge_types) == expected["hyperedges"], (
        f"{name}: expected {expected['hyperedges']} hyperedge types, "
        f"got {len(s.hyperedge_types)}"
    )
