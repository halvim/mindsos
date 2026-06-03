"""Phase 13 PB-3 — strict=False sentinel.

All 8 named-role schemas + alignment must default to ``strict=False``
per ADR-0149. Any future strict-tighten PR has to (a) flip this
sentinel, (b) document the per-role flip in ADR-0149 §Revisions, AND
(c) include the inventory-helper output justifying the flip.
"""

from __future__ import annotations

import pytest

from mindsos_knowledge.schemas import (
    build_alignment_schema,
    build_capacity_state_schema,
    build_concepts_schema,
    build_episodic_memories_schema,
    build_lexicon_schema,
    build_ontology_schema,
    build_problem_trace_schema,
    build_promoted_pipelines_schema,
    build_task_patterns_schema,
)


@pytest.mark.parametrize(
    "builder",
    [
        build_ontology_schema,
        build_lexicon_schema,
        build_concepts_schema,
        build_alignment_schema,
        build_promoted_pipelines_schema,
        build_task_patterns_schema,
        build_episodic_memories_schema,
        build_problem_trace_schema,
        build_capacity_state_schema,
    ],
)
def test_default_strict_is_false(builder) -> None:
    """ADR-0149 lock — none of the 9 builders default to strict=True."""
    s = builder()
    assert s.strict is False, (
        f"{builder.__name__}: ADR-0149 requires strict=False at launch; "
        "any per-role tightening must amend ADR-0149 §Revisions."
    )
