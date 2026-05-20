"""Phase 14 — dimensional snapshot of KL post-bootstrap shape.

Per `feedback_dimension_table_cross_check.md` lesson from Phase 13
B-13-T1: derive expected counts from the actual builder output during
the Step-0 probe, then assert.

Bootstrapped KL shape:

* Global: 6 role-graphs (ontology, lexicon, concepts,
  promoted-pipelines, task-patterns, problem-trace). No alignment.
  No memories, no capacity-state.
* Per Local (lazy or installed): 2 role-graphs (memories,
  capacity-state).
"""

from __future__ import annotations

import pytest

from mindsos_knowledge import (
    KnowledgeLayer,
    ROLE_CAPACITY_STATE,
    ROLE_CONCEPTS,
    ROLE_LEXICON,
    ROLE_MEMORIES,
    ROLE_ONTOLOGY,
    ROLE_PROBLEM_TRACE,
    ROLE_PROMOTED_PIPELINES,
    ROLE_TASK_PATTERNS,
)


_EXPECTED_BOOTSTRAP_GLOBAL_ROLES = {
    ROLE_ONTOLOGY,
    ROLE_LEXICON,
    ROLE_CONCEPTS,
    ROLE_PROMOTED_PIPELINES,
    ROLE_TASK_PATTERNS,
    ROLE_PROBLEM_TRACE,
}

_EXPECTED_LAZY_LOCAL_ROLES = {
    ROLE_MEMORIES,
    ROLE_CAPACITY_STATE,
}


def test_bootstrap_global_dimensional_snapshot() -> None:
    kl = KnowledgeLayer.bootstrap()
    g = kl.global_metagraph()
    assert len(g.graphs) == 6
    observed = {gr.role for gr in g.graphs.values()}
    assert observed == _EXPECTED_BOOTSTRAP_GLOBAL_ROLES


def test_lazy_local_dimensional_snapshot() -> None:
    kl = KnowledgeLayer.bootstrap()
    local = kl.local_metagraph("alice")
    assert len(local.graphs) == 2
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
