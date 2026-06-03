"""Phase 39 ``_IRI_BUILDERS`` registry shape per ADR-0146 §amendment-3.

Registry keyed by ``(role, NodeType_name)`` tuple. Post-rename, 3 entries:

* ``(ROLE_EPISODIC_MEMORIES, "Episode") → _mint_episode``
* ``(ROLE_EPISODIC_MEMORIES, "Memory") → _mint_memory_composite``
* ``(ROLE_PROBLEM_TRACE, "ProblemTraceEntry") → _mint_problem_trace``

``KLWriteHandle.mint_iri(self, type_, **content) -> str`` signature.
"""

from __future__ import annotations

import inspect

import pytest

from mindsos_knowledge import KLWriteHandle, KnowledgeLayer
from mindsos_knowledge.identifiers import (
    ROLE_EPISODIC_MEMORIES,
    ROLE_PROBLEM_TRACE,
    _IRI_BUILDERS,
)


def test_registry_is_tuple_keyed() -> None:
    """Every key in the registry is a 2-tuple of strings."""
    for key in _IRI_BUILDERS.keys():
        assert isinstance(key, tuple), f"Key {key!r} is not a tuple"
        assert len(key) == 2, f"Key {key!r} is not a 2-tuple"
        assert all(isinstance(part, str) for part in key), (
            f"Key {key!r} parts are not all strings"
        )


def test_registry_contains_three_entries_post_rename() -> None:
    """Phase 39 closure: 3 entries (2 Episode/Memory + 1 ProblemTraceEntry)."""
    assert set(_IRI_BUILDERS.keys()) == {
        (ROLE_EPISODIC_MEMORIES, "Episode"),
        (ROLE_EPISODIC_MEMORIES, "Memory"),
        (ROLE_PROBLEM_TRACE, "ProblemTraceEntry"),
    }


def test_registry_entries_are_callable() -> None:
    for key, builder in _IRI_BUILDERS.items():
        assert callable(builder), f"Entry for {key!r} is not callable"


def test_mint_iri_signature_takes_type_then_content() -> None:
    """ADR-0146 §amendment-3 mint_iri signature: (type_: str, **content)."""
    sig = inspect.signature(KLWriteHandle.mint_iri)
    params = list(sig.parameters.values())
    # params[0] is `self`; params[1] is `type_`; params[2] is **content.
    assert params[0].name == "self"
    assert params[1].name == "type_"
    assert params[1].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert params[2].name == "content"
    assert params[2].kind == inspect.Parameter.VAR_KEYWORD


def test_mint_iri_episode_dispatch() -> None:
    """End-to-end: mint_iri('Episode', ...) hits _mint_episode."""
    kl = KnowledgeLayer.bootstrap()
    handle = KLWriteHandle(
        role=ROLE_EPISODIC_MEMORIES,
        scope="local",
        session=None,
        _kl=kl,
        _metagraph=kl.global_metagraph(),
        _version="v1",
    )
    iri = handle.mint_iri("Episode", user_id="alice", episode_id="e1")
    assert iri == "episodic-memories-v1:episode:alice:e1"


def test_mint_iri_memory_composite_dispatch() -> None:
    """End-to-end: mint_iri('Memory', ...) hits _mint_memory_composite."""
    kl = KnowledgeLayer.bootstrap()
    handle = KLWriteHandle(
        role=ROLE_EPISODIC_MEMORIES,
        scope="local",
        session=None,
        _kl=kl,
        _metagraph=kl.global_metagraph(),
        _version="v1",
    )
    iri = handle.mint_iri("Memory", user_id="alice", memory_id="m1")
    assert iri == "episodic-memories-v1:memory:alice:m1"


def test_mint_iri_unknown_pair_raises_keyerror_with_both_role_and_type() -> None:
    """KeyError message names both the role and the NodeType per ADR-0146 §am-3."""
    kl = KnowledgeLayer.bootstrap()
    handle = KLWriteHandle(
        role=ROLE_EPISODIC_MEMORIES,
        scope="local",
        session=None,
        _kl=kl,
        _metagraph=kl.global_metagraph(),
        _version="v1",
    )
    with pytest.raises(KeyError) as excinfo:
        handle.mint_iri("NonexistentNodeType", x="y")
    msg = str(excinfo.value)
    assert "episodic_memories" in msg
    assert "NonexistentNodeType" in msg
