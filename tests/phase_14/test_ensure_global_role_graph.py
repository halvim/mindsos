"""Phase 14 — ``ensure_global_role_graph`` module function.

Covers per Phase 14 round-1 PB-4:

* Happy path for 6 Global-named roles (parametric).
* Happy path for alignment-prefix (parametric over a few examples;
  ADR-0150 §amendment-1 lock — Global-only).
* Idempotence: re-call returns the same Graph.
* Scope-rejection: Local-only roles raise ``KnowledgeError``.
* Unknown roles raise ``UnknownRoleError``.
* ``extra_edge_types`` plumbs through to the alignment builder.
"""

from __future__ import annotations

import pytest

from mindsos_core import Metagraph

from mindsos_knowledge import (
    KnowledgeError,
    ROLE_CAPACITY_STATE,
    ROLE_CONCEPTS,
    ROLE_LEXICON,
    ROLE_EPISODIC_MEMORIES,
    ROLE_ONTOLOGY,
    ROLE_PROBLEM_TRACE,
    ROLE_PROMOTED_PIPELINES,
    ROLE_TASK_PATTERNS,
    UnknownRoleError,
    ensure_global_role_graph,
)


_GLOBAL_NAMED = (
    ROLE_ONTOLOGY,
    ROLE_LEXICON,
    ROLE_CONCEPTS,
    ROLE_PROMOTED_PIPELINES,
    ROLE_TASK_PATTERNS,
    ROLE_PROBLEM_TRACE,
)


@pytest.mark.parametrize("role", _GLOBAL_NAMED)
def test_ensure_global_named_role_creates_graph(role: str) -> None:
    """6 Global named roles all create a Graph with the role attached."""
    mg = Metagraph(name="t")
    g = ensure_global_role_graph(mg, role)
    assert g.role == role
    assert g.schema is not None
    assert g in mg.graphs.values()


@pytest.mark.parametrize("role", _GLOBAL_NAMED)
def test_ensure_global_named_role_idempotent(role: str) -> None:
    """Re-call returns the existing Graph (idempotent no-op)."""
    mg = Metagraph(name="t")
    g1 = ensure_global_role_graph(mg, role)
    g2 = ensure_global_role_graph(mg, role)
    assert g1 is g2
    assert len(mg.graphs) == 1


@pytest.mark.parametrize(
    "alignment_role",
    [
        "alignment:ontology:lexicon",
        "alignment:lexicon:concepts",
        "alignment:ontology:concepts",
    ],
)
def test_ensure_global_alignment_prefix_accepted(
    alignment_role: str,
) -> None:
    """Per ADR-0150 §amendment-1 — alignment is Global-only at v1."""
    mg = Metagraph(name="t")
    g = ensure_global_role_graph(mg, alignment_role)
    assert g.role == alignment_role
    assert g.schema is not None


def test_ensure_global_alignment_idempotent() -> None:
    """Alignment pair-graph is also idempotent."""
    mg = Metagraph(name="t")
    g1 = ensure_global_role_graph(mg, "alignment:ontology:lexicon")
    g2 = ensure_global_role_graph(mg, "alignment:ontology:lexicon")
    assert g1 is g2


@pytest.mark.parametrize("role", [ROLE_EPISODIC_MEMORIES, ROLE_CAPACITY_STATE])
def test_ensure_global_rejects_local_role(role: str) -> None:
    """ADR-0044 enforced at the dispatch site (PB-4)."""
    mg = Metagraph(name="t")
    with pytest.raises(KnowledgeError, match="Local-only"):
        ensure_global_role_graph(mg, role)


def test_ensure_global_rejects_unknown_role() -> None:
    """Unknown role raises ``UnknownRoleError`` (mirrors schema_for_role)."""
    mg = Metagraph(name="t")
    with pytest.raises(UnknownRoleError, match="Unknown role"):
        ensure_global_role_graph(mg, "not-a-real-role")


def test_ensure_global_extra_edge_types_forwarded_to_alignment() -> None:
    """``extra_edge_types`` plumbs into ``build_alignment_schema``.

    Phase 14 calibration: forward-compatible with Phase 15's
    Alignments importer (which passes a non-empty tuple per its
    role-pair vocabulary).
    """
    mg = Metagraph(name="t")
    extra = ("CUSTOM_REL",)
    g = ensure_global_role_graph(
        mg, "alignment:ontology:lexicon", extra_edge_types=extra
    )
    # The schema's edge types include the custom one.
    schema = g.schema
    assert schema is not None
    edge_type_names = set(schema.edge_types.keys())
    assert "CUSTOM_REL" in edge_type_names


def test_ensure_global_extra_edge_types_ignored_for_non_alignment() -> None:
    """For non-alignment roles, ``extra_edge_types`` is silently ignored.

    Phase 14 calibration: kwarg present on the unified signature for
    forward compatibility; non-alignment branches don't use it.
    """
    mg = Metagraph(name="t")
    # Pass an extra edge type to a non-alignment role; should not error.
    g = ensure_global_role_graph(
        mg, ROLE_ONTOLOGY,
        extra_edge_types=("X_REL",),
    )
    schema = g.schema
    assert schema is not None
    # The ontology schema's edge types do NOT include the ignored kwarg.
    edge_type_names = set(schema.edge_types.keys())
    assert "X_REL" not in edge_type_names
