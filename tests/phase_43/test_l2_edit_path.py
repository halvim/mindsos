"""Slice 1a — the L2 node-edit path (``KLWriteHandle.update_and_validate``).

The first shipped caller of :func:`validate_mutation_discipline` (ADR-0153 §3
per-field enforcement — deferred at Phase 43 "until the first capacity that
edits an existing node"; the Dream's streaming Episode lifecycle is that
caller). These tests prove the WIRING: ``update_and_validate`` resolves an
existing node, enforces the role's discipline per-field against the
caller-supplied content/metadata partition, and applies the in-memory merge
only when permitted. The discipline RULES themselves are unit-tested in
``test_validate_mutation_discipline.py``; here we prove the handle forwards
them and mutates correctly.

Uses ``episodic_memories`` (``append_only_with_lazy_inline``) as the driver —
the real target role — so content-blocked / lazy-allowed / metadata-allowed
are all exercised on the role the Episode lifecycle actually edits.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from mindsos_core.exceptions import IdentityError
from mindsos_knowledge import (
    KnowledgeLayer,
    MutationDisciplineError,
    ROLE_EPISODIC_MEMORIES,
)
from mindsos_knowledge.schemas.episodic_memories import EPISODE_CONTENT_FIELDS


def _episode_handle():
    kl = KnowledgeLayer.bootstrap()
    return kl.writeable(
        session=SimpleNamespace(user_id="alice"),
        role=ROLE_EPISODIC_MEMORIES,
        scope="local",
    )


def _make_episode(handle, episode_id: str = "e1") -> str:
    res = handle.write_and_validate(
        value="payload", type_="Episode", user_id="alice", episode_id=episode_id
    )
    return res.iri


def test_content_field_edit_without_lazy_raises_and_leaves_node_unchanged():
    handle = _episode_handle()
    iri = _make_episode(handle)
    with pytest.raises(MutationDisciplineError) as exc:
        handle.update_and_validate(
            iri=iri,
            field_updates={"outcome_classification": "succeeded"},
            content_fields=EPISODE_CONTENT_FIELDS,
            via_lazy_inline=False,
        )
    assert exc.value.discipline == "append_only_with_lazy_inline"
    assert exc.value.field == "outcome_classification"
    # Rejected BEFORE the merge — the property was never written.
    assert "outcome_classification" not in handle.graph().nodes[iri].properties


def test_content_field_edit_with_lazy_inline_applies():
    handle = _episode_handle()
    iri = _make_episode(handle)
    handle.update_and_validate(
        iri=iri,
        field_updates={"outcome_classification": "succeeded"},
        content_fields=EPISODE_CONTENT_FIELDS,
        via_lazy_inline=True,
    )
    assert (
        handle.graph().nodes[iri].properties["outcome_classification"]
        == "succeeded"
    )


def test_metadata_field_edit_applies_without_lazy():
    """A field NOT in ``content_fields`` is metadata — freely mutable (this is
    the ``state`` field the Episode lifecycle flips open->closed in Slice 1b)."""
    handle = _episode_handle()
    iri = _make_episode(handle)
    handle.update_and_validate(
        iri=iri,
        field_updates={"state": "open"},
        content_fields=EPISODE_CONTENT_FIELDS,
    )
    assert handle.graph().nodes[iri].properties["state"] == "open"


def test_empty_partition_treats_all_fields_as_metadata():
    """Partition wiring: with an empty ``content_fields`` an otherwise-content
    field name is metadata, so the edit is allowed without lazy-inline —
    proving the handle honours the caller-supplied partition, not a hard-coded
    one."""
    handle = _episode_handle()
    iri = _make_episode(handle)
    handle.update_and_validate(
        iri=iri,
        field_updates={"outcome_classification": "succeeded"},
        content_fields=frozenset(),
    )
    assert (
        handle.graph().nodes[iri].properties["outcome_classification"]
        == "succeeded"
    )


def test_missing_node_raises_identity_error():
    handle = _episode_handle()
    with pytest.raises(IdentityError):
        handle.update_and_validate(
            iri="episodic-memories-v1:episode:alice:nope",
            field_updates={"state": "closed"},
            content_fields=EPISODE_CONTENT_FIELDS,
        )
