"""Phase 43 PR2 — KL bootstrap discipline dispatch + write_and_validate enforcement.

Per ADR-0153 §2 startup invariant. Tests:

* ``KnowledgeLayer.bootstrap()`` populates the discipline dispatch
  table for every Global role-graph it creates.
* ``KnowledgeLayer.discipline_for(mg, role)`` returns the expected
  discipline for each of the 9 Global + 5 Local roles.
* ``KLWriteHandle.write_and_validate(...)`` raises
  :class:`MutationDisciplineError` on ``admin_authored`` writes
  without ``_is_admin=True``.
* Lazy-inline on ``episodic_memories`` is permitted at node CREATE
  time (the discipline check applies to subsequent edits of content
  fields, not to creation).
"""

from __future__ import annotations

import pytest

from mindsos_knowledge import (
    Discipline,
    KnowledgeLayer,
    MutationDisciplineError,
    ROLE_CAPACITY_GAPS,
    ROLE_CAPACITY_STATE,
    ROLE_CONCEPTS,
    ROLE_EPISODIC_MEMORIES,
    ROLE_LEARNED_PARAMETERS,
    ROLE_LEXICON,
    ROLE_ONTOLOGY,
    ROLE_PARAMETER_STAGING,
    ROLE_PENDING_PROMOTIONS,
    ROLE_PROBLEM_TRACE,
    ROLE_PROMOTED_PIPELINES,
    ROLE_TASK_PATTERNS,
)


_GLOBAL_EXPECTED = {
    ROLE_ONTOLOGY: Discipline.ADMIN_AUTHORED,
    ROLE_LEXICON: Discipline.ADMIN_AUTHORED,
    ROLE_CONCEPTS: Discipline.ADMIN_AUTHORED,
    ROLE_PROMOTED_PIPELINES: Discipline.IMMUTABLE_SUCCESSOR,
    ROLE_TASK_PATTERNS: Discipline.IMMUTABLE_SUCCESSOR,
    ROLE_PROBLEM_TRACE: Discipline.APPEND_ONLY,
    # Phase 43 Global-form additions per ADR-0150 §am-5.
    ROLE_PENDING_PROMOTIONS: Discipline.AUDIT_ONLY_AFTER_SETTLED,
    ROLE_CAPACITY_GAPS: Discipline.MUTABLE_WITH_RETENTION,
    ROLE_LEARNED_PARAMETERS: Discipline.ADMIN_AUTHORED,
}

_LOCAL_EXPECTED = {
    ROLE_EPISODIC_MEMORIES: Discipline.APPEND_ONLY_WITH_LAZY_INLINE,
    ROLE_CAPACITY_STATE: Discipline.MUTABLE_WITH_RETENTION,
    # Phase 43 Local-form additions per ADR-0150 §am-5.
    ROLE_PARAMETER_STAGING: Discipline.MUTABLE_WITH_RETENTION,
    ROLE_PENDING_PROMOTIONS: Discipline.AUDIT_ONLY_AFTER_SETTLED,
    ROLE_LEARNED_PARAMETERS: Discipline.MUTABLE_WITH_RETENTION,
}


def test_bootstrap_builds_global_dispatch() -> None:
    kl = KnowledgeLayer.bootstrap()
    global_mg = kl.global_metagraph()
    for role, expected in _GLOBAL_EXPECTED.items():
        actual = kl.discipline_for(global_mg, role)
        assert actual == expected, (
            f"Global {role!r}: discipline_for returned {actual!r}, "
            f"expected {expected!r}"
        )


def test_lazy_local_builds_local_dispatch() -> None:
    kl = KnowledgeLayer.bootstrap()
    local_mg = kl.local_metagraph("alice")
    for role, expected in _LOCAL_EXPECTED.items():
        actual = kl.discipline_for(local_mg, role)
        assert actual == expected, (
            f"Local {role!r}: discipline_for returned {actual!r}, "
            f"expected {expected!r}"
        )


def test_discipline_for_unknown_role_returns_none() -> None:
    kl = KnowledgeLayer.bootstrap()
    assert kl.discipline_for(kl.global_metagraph(), "no-such-role") is None


def _make_session(user_id: str = "alice"):
    from types import SimpleNamespace

    return SimpleNamespace(user_id=user_id)


def test_admin_authored_write_without_admin_flag_raises() -> None:
    """ontology / lexicon / concepts / learned-parameters (Global) reject
    write_and_validate when _is_admin=False."""
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(
        session=None,
        role=ROLE_ONTOLOGY,
        scope="global",
    )
    with pytest.raises(MutationDisciplineError) as exc:
        handle.write_and_validate(
            value="x",
            type_="Class",
            user_id="alice",
            evidence_id="e1",
        )
    assert exc.value.discipline == "admin_authored"
    assert exc.value.attempted_op == "admin_only"


def test_episodic_memories_write_passes_discipline_check() -> None:
    """append_only_with_lazy_inline does NOT block node CREATE — the
    discipline applies to edits of existing content fields, not to
    initial Episode/Memory creation."""
    kl = KnowledgeLayer.bootstrap()
    sess = _make_session("alice")
    handle = kl.writeable(
        session=sess,
        role=ROLE_EPISODIC_MEMORIES,
        scope="local",
    )
    # Should not raise MutationDisciplineError (admin_authored is the
    # only Phase 43 discipline that blocks CREATE).
    try:
        handle.write_and_validate(
            value="payload",
            type_="Episode",
            user_id="alice",
            episode_id="e1",
        )
    except MutationDisciplineError:
        pytest.fail(
            "episodic_memories write should not trigger discipline check"
        )


def test_mutable_with_retention_write_passes() -> None:
    kl = KnowledgeLayer.bootstrap()
    sess = _make_session("alice")
    handle = kl.writeable(
        session=sess,
        role=ROLE_CAPACITY_STATE,
        scope="local",
    )
    # No discipline error path; capacity_state has no IRI-builder
    # registration for direct mint via write_and_validate, so we only
    # exercise discipline_for here.
    assert kl.discipline_for(handle.metagraph(), handle.role) == (
        Discipline.MUTABLE_WITH_RETENTION
    )
