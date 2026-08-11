"""Phase 14 — dimensional snapshot of KL post-bootstrap shape.

Per `feedback_dimension_table_cross_check.md` lesson from Phase 13
B-13-T1: derive expected counts from the actual builder output during
the Step-0 probe, then assert.

Bootstrapped KL shape:

* Global: 6 role-graphs (ontology, lexicon, concepts,
  promoted-pipelines, request-patterns, problem-trace). No alignment.
  No episodic_memories, no capacity-state.
* Per Local (lazy or installed): 2 role-graphs (episodic_memories,
  capacity-state; Phase 39 rename per ADR-0044 §am-3).
"""

from __future__ import annotations

import pytest

from mindsos_knowledge import (
    KnowledgeLayer,
    ROLE_CAPACITY_GAPS,
    ROLE_CAPACITY_STATE,
    ROLE_CONCEPTS,
    ROLE_INSTALLED_CAPACITIES,
    ROLE_INSTALLED_SKILLS,
    ROLE_LEARNED_PARAMETERS,
    ROLE_LEARNED_PIPELINES,
    ROLE_LEXICON,
    ROLE_EPISODIC_MEMORIES,
    ROLE_ONTOLOGY,
    ROLE_PARAMETER_STAGING,
    ROLE_PENDING_PROMOTIONS,
    ROLE_POLICIES,
    ROLE_PROBLEM_TRACE,
    ROLE_PROMOTED_PIPELINES,
    ROLE_SUBMINDS,
    ROLE_REQUEST_PATTERNS,
)


_EXPECTED_BOOTSTRAP_GLOBAL_ROLES = {
    ROLE_ONTOLOGY,
    ROLE_LEXICON,
    ROLE_CONCEPTS,
    ROLE_PROMOTED_PIPELINES,
    ROLE_REQUEST_PATTERNS,
    ROLE_PROBLEM_TRACE,
    # Phase 43 (ADR-0150 §am-5) Global-form additions.
    ROLE_PENDING_PROMOTIONS,
    ROLE_CAPACITY_GAPS,
    ROLE_LEARNED_PARAMETERS,
    # Phase 50 (ADR-0150 §am-6) addition — Global-only.
    ROLE_INSTALLED_SKILLS,
    # feat/subminds (ADR-0150 §am-7) addition — Global form (Slice 1).
    ROLE_SUBMINDS,
    # CORE CR: the policy role — Global form.
    ROLE_POLICIES,
}

_EXPECTED_LAZY_LOCAL_ROLES = {
    ROLE_EPISODIC_MEMORIES,
    ROLE_CAPACITY_STATE,
    # Phase 43 (ADR-0150 §am-5) Local-form additions.
    ROLE_PARAMETER_STAGING,
    ROLE_PENDING_PROMOTIONS,
    ROLE_LEARNED_PARAMETERS,
    # feat/phase1-seam (ADR-0150 §am-8) — request-patterns dual-scope.
    ROLE_REQUEST_PATTERNS,
    # feat/learned-pipeline-persistence (ADR-0203) — Local-only.
    ROLE_LEARNED_PIPELINES,
    # ADR-0183 §am-5 — installed Local capabilities.
    ROLE_INSTALLED_CAPACITIES,
    # CORE-C2R1 (ADR-0150 §am-11) — installed-skills gained a Local form.
    ROLE_INSTALLED_SKILLS,
    # CORE CR: the policy role — Local form.
    ROLE_POLICIES,
}


def test_bootstrap_global_dimensional_snapshot() -> None:
    kl = KnowledgeLayer.bootstrap()
    g = kl.global_metagraph()
    assert len(g.graphs) == 12
    observed = {gr.role for gr in g.graphs.values()}
    assert observed == _EXPECTED_BOOTSTRAP_GLOBAL_ROLES


def test_lazy_local_dimensional_snapshot() -> None:
    kl = KnowledgeLayer.bootstrap()
    local = kl.local_metagraph("alice")
    assert len(local.graphs) == 10
    observed = {gr.role for gr in local.graphs.values()}
    assert observed == _EXPECTED_LAZY_LOCAL_ROLES


def test_kl_zero_locals_after_bootstrap() -> None:
    kl = KnowledgeLayer.bootstrap()
    assert len(kl.installed_user_ids()) == 0


def test_kl_n_locals_after_n_lazy_accesses() -> None:
    kl = KnowledgeLayer.bootstrap()
    for uid in ("alice", "bob", "carol"):
        kl.local_metagraph(uid)
    assert len(kl.installed_user_ids()) == 3
