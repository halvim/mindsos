"""Phase 46 — three-sub-MM container + thin root + deep-copy (ADR-0165)."""

from __future__ import annotations

import pytest

from mindsos_intelligence.mm import MentalModel, MMRoot
from mindsos_intelligence.rwlock import RWLock


def _mm():
    return MentalModel(session_id="s1", user_id="u1")


def test_three_sub_mms_present():
    mm = _mm()
    assert mm.knowledge_mm is not None
    assert mm.capacity_mm is not None
    assert mm.intelligence_mm is not None
    assert mm.knowledge_mm is not mm.capacity_mm is not mm.intelligence_mm
    assert isinstance(mm.root, MMRoot)
    assert isinstance(mm.lock, RWLock)


def test_thin_root_is_pointers_only():
    mm = _mm()
    assert mm.root.request_run_ref is None
    assert mm.root.problem_trace_ref is None
    assert mm.root.outcome_ref is None


def test_iri_namespace_dispatch():
    mm = _mm()
    assert mm.sub_mm_for_iri("ontology:Person") is mm.knowledge_mm
    assert mm.sub_mm_for_iri("episodic:e1") is mm.knowledge_mm
    assert mm.sub_mm_for_iri("capacity:text:tokenize") is mm.capacity_mm
    assert mm.sub_mm_for_iri("datastate:nlu.tokens") is mm.capacity_mm
    assert mm.sub_mm_for_iri("requestrun:abc") is mm.intelligence_mm
    assert mm.sub_mm_for_iri("plan:p1") is mm.intelligence_mm
    with pytest.raises(KeyError):
        mm.sub_mm_for_iri("unknown:thing")


def test_the_two_run_scoped_node_prefixes_have_a_room():
    """Both live IN the per-run capacity graph, and neither was in the table.

    ``sub_mm_for_iri`` raised ``KeyError`` on either — a node sitting in a
    capacity graph that the router said belonged nowhere. It went unseen because
    neither prefix had met the router: ``RunStopped`` is written only on a
    non-success, and the manifest was minted a layer above ``execute_pipeline``
    until the map-manifest CR moved it in.

    Asserted here, at the table, AND driven over real graphs in
    ``tests/phase_48/test_capacity_mm_writer.py`` and
    ``tests/terminal_node/test_run_stopped.py`` — a prefix table that agrees
    with itself is not evidence that anything routes."""
    mm = _mm()
    assert mm.sub_mm_for_iri("runmanifest:t1.t1-1") is mm.capacity_mm
    assert mm.sub_mm_for_iri("runstopped:t1.t1-1") is mm.capacity_mm


def test_deep_copy_is_independent():
    mm = _mm()
    mm.root.request_run_ref = "requestrun:orig"
    clone = mm.deep_copy()
    assert clone.root.request_run_ref == "requestrun:orig"
    clone.root.outcome_ref = "outcome:x"
    assert mm.root.outcome_ref is None
    assert clone.knowledge_mm is not mm.knowledge_mm
    assert clone.capacity_mm is not mm.capacity_mm
    assert clone.intelligence_mm is not mm.intelligence_mm
    assert clone.lock is not mm.lock
