"""Phase 34 — ``KnowledgeLayer.writeable(..., version=)`` keyword."""

from __future__ import annotations

from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.identifiers import ROLE_PROBLEM_TRACE


def test_writeable_default_version_v1():
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(None, role=ROLE_PROBLEM_TRACE, scope="global")
    assert handle._version == "v1"


def test_writeable_accepts_explicit_version_kwarg():
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(
        None, role=ROLE_PROBLEM_TRACE, scope="global", version="v3"
    )
    assert handle._version == "v3"


def test_writeable_version_threads_into_mint_iri():
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(
        None, role=ROLE_PROBLEM_TRACE, scope="global", version="vexp"
    )
    iri = handle.mint_iri(trace_id="t1")
    assert iri == "problem-trace-vexp:entry:t1"
