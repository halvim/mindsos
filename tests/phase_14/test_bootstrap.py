"""Phase 14 — ``KnowledgeLayer.bootstrap()`` ensures 6 named Global roles.

Per Phase 14 PB-1 lock: bootstrap auto-ensures the 6 Global named
roles (``ontology``, ``lexicon``, ``concepts``, ``promoted-pipelines``,
``task-patterns``, ``problem-trace``). Alignment pair-graphs are
**not** created at bootstrap — Phase 15's Alignments importer mints
those on demand.

Per ADR-0044 (§am-3 rename): ``episodic_memories`` + ``capacity-state``
are Local; bootstrap does NOT add them to Global.
"""

from __future__ import annotations

from mindsos_knowledge import (
    KnowledgeLayer,
    ROLE_CAPACITY_GAPS,
    ROLE_CAPACITY_STATE,
    ROLE_CONCEPTS,
    ROLE_INSTALLED_SKILLS,
    ROLE_LEARNED_PARAMETERS,
    ROLE_LEXICON,
    ROLE_EPISODIC_MEMORIES,
    ROLE_ONTOLOGY,
    ROLE_PENDING_PROMOTIONS,
    ROLE_PROBLEM_TRACE,
    ROLE_PROMOTED_PIPELINES,
    ROLE_TASK_PATTERNS,
)


_EXPECTED_GLOBAL_ROLES = frozenset({
    ROLE_ONTOLOGY,
    ROLE_LEXICON,
    ROLE_CONCEPTS,
    ROLE_PROMOTED_PIPELINES,
    ROLE_TASK_PATTERNS,
    ROLE_PROBLEM_TRACE,
    # Phase 43 (ADR-0150 §am-5) Global-form additions.
    ROLE_PENDING_PROMOTIONS,
    ROLE_CAPACITY_GAPS,
    ROLE_LEARNED_PARAMETERS,
    # Phase 50 (ADR-0150 §am-6) addition — Global-only.
    ROLE_INSTALLED_SKILLS,
})


def test_bootstrap_global_has_6_named_role_graphs() -> None:
    """Bootstrap ensures the 9 Global-named roles per ADR-0150 + ADR-0044.

    Phase 43 (ADR-0150 §am-5) expanded the Global-named set from 6 to 9
    (added pending-promotions + capacity-gaps + learned-parameters; the
    test function name retains the historical "6" for forensic
    continuity, but the assertion checks the full post-Phase-43 set
    via _EXPECTED_GLOBAL_ROLES).
    """
    kl = KnowledgeLayer.bootstrap()
    g = kl.global_metagraph()
    observed_roles = {gr.role for gr in g.graphs.values()}
    assert observed_roles == _EXPECTED_GLOBAL_ROLES


def test_bootstrap_no_local_roles_in_global() -> None:
    """ADR-0044 (§am-3) — ``episodic_memories`` + ``capacity-state`` are Local-only."""
    kl = KnowledgeLayer.bootstrap()
    g = kl.global_metagraph()
    observed_roles = {gr.role for gr in g.graphs.values()}
    assert ROLE_EPISODIC_MEMORIES not in observed_roles
    assert ROLE_CAPACITY_STATE not in observed_roles


def test_bootstrap_no_alignment_at_bootstrap() -> None:
    """Phase 14 PB-1 — alignment pair-graphs are importer-driven."""
    kl = KnowledgeLayer.bootstrap()
    g = kl.global_metagraph()
    for graph in g.graphs.values():
        assert graph.role is not None
        assert not graph.role.startswith("alignment:")


def test_bootstrap_zero_locals_initially() -> None:
    """Bootstrap creates Global only; Locals are server-driven post-bootstrap."""
    kl = KnowledgeLayer.bootstrap()
    assert kl.installed_user_ids() == frozenset()


def test_each_global_role_graph_has_schema_attached() -> None:
    """ADR-0149 — schemas at strict=False attached to each role-graph."""
    kl = KnowledgeLayer.bootstrap()
    for graph in kl.global_metagraph().graphs.values():
        assert graph.schema is not None, (
            f"Role-graph {graph.role!r} ships without schema attached "
            f"(expected per ADR-0149)."
        )
        assert graph.schema.strict is False


def test_bootstrap_is_independent_per_call() -> None:
    """Each ``bootstrap()`` call produces a distinct KL + Global."""
    kl_a = KnowledgeLayer.bootstrap()
    kl_b = KnowledgeLayer.bootstrap()
    assert kl_a is not kl_b
    assert kl_a.global_metagraph() is not kl_b.global_metagraph()
    assert kl_a.global_metagraph().metagraph_id != kl_b.global_metagraph().metagraph_id


def test_bootstrap_canonical_name() -> None:
    """v3 design doc §2 — Global metagraph name is ``global_knowledge``."""
    kl = KnowledgeLayer.bootstrap()
    assert kl.global_metagraph().name == "global_knowledge"
