"""Phase 14 — ``ensure_local_role_graph`` module function.

Covers per Phase 14 round-1 PB-4 + PB-8:

* Happy path for 2 Local-named roles (parametric).
* Idempotence.
* Scope-rejection: 6 Global-named roles raise ``KnowledgeError``.
* Alignment-prefix rejected (per ADR-0150 §amendment-1 — Global-only).
* Unknown roles raise ``UnknownRoleError``.
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
    ensure_local_role_graph,
)


_LOCAL_NAMED = (ROLE_EPISODIC_MEMORIES, ROLE_CAPACITY_STATE)
_GLOBAL_NAMED = (
    ROLE_ONTOLOGY,
    ROLE_LEXICON,
    ROLE_CONCEPTS,
    ROLE_PROMOTED_PIPELINES,
    ROLE_TASK_PATTERNS,
    ROLE_PROBLEM_TRACE,
)


@pytest.mark.parametrize("role", _LOCAL_NAMED)
def test_ensure_local_named_role_creates_graph(role: str) -> None:
    """Both Local-named roles create a Graph with the role attached."""
    mg = Metagraph(name="local_t")
    g = ensure_local_role_graph(mg, role)
    assert g.role == role
    assert g.schema is not None
    assert g in mg.graphs.values()


@pytest.mark.parametrize("role", _LOCAL_NAMED)
def test_ensure_local_named_role_idempotent(role: str) -> None:
    """Re-call returns the existing Graph."""
    mg = Metagraph(name="local_t")
    g1 = ensure_local_role_graph(mg, role)
    g2 = ensure_local_role_graph(mg, role)
    assert g1 is g2
    assert len(mg.graphs) == 1


@pytest.mark.parametrize("role", _GLOBAL_NAMED)
def test_ensure_local_rejects_global_role(role: str) -> None:
    """ADR-0044 enforced — 6 Global-named roles reject in Local scope."""
    mg = Metagraph(name="local_t")
    with pytest.raises(KnowledgeError, match="Global-only"):
        ensure_local_role_graph(mg, role)


def test_ensure_local_rejects_alignment_prefix() -> None:
    """ADR-0150 §amendment-1 — alignment is Global-only at v1."""
    mg = Metagraph(name="local_t")
    with pytest.raises(KnowledgeError, match="alignment is Global-only"):
        ensure_local_role_graph(mg, "alignment:ontology:lexicon")


def test_ensure_local_rejects_unknown_role() -> None:
    """Unknown role raises ``UnknownRoleError``."""
    mg = Metagraph(name="local_t")
    with pytest.raises(UnknownRoleError, match="Unknown role"):
        ensure_local_role_graph(mg, "not-a-real-role")


def test_local_schema_strict_false_per_adr_0149() -> None:
    """Per ADR-0149 — schemas ship strict=False by default."""
    mg = Metagraph(name="local_t")
    g = ensure_local_role_graph(mg, ROLE_EPISODIC_MEMORIES)
    assert g.schema is not None
    assert g.schema.strict is False
