"""add_xref validation — M4 + P59 (validate-before-WAL ordering)."""

from __future__ import annotations

import pytest

from mindsos_core.exceptions import XRefIntegrityError
from tests._shared.cross_metagraph_fixture import (
    make_source_and_target_metagraphs,
)


def test_target_metagraph_kwarg_validates_present_target():
    """M4 — target_metagraph passed + target exists ⇒ no raise."""
    source, target = make_source_and_target_metagraphs()
    x = source.add_xref(
        source_id="src-node-1",
        target_metagraph_id=target.metagraph_id,
        target_role="lexicon",
        target_id="tgt-node-1",
        ref_type="SPECIALISES",
        target_metagraph=target,
    )
    assert x.target_id == "tgt-node-1"


def test_target_metagraph_kwarg_raises_on_missing_target():
    """M4 — target_metagraph passed + target missing ⇒ XRefIntegrityError."""
    source, target = make_source_and_target_metagraphs()
    with pytest.raises(XRefIntegrityError, match="not found"):
        source.add_xref(
            source_id="src-node-1",
            target_metagraph_id=target.metagraph_id,
            target_role="lexicon",
            target_id="ghost-tgt",  # not registered in target
            ref_type="SPECIALISES",
            target_metagraph=target,
        )


def test_target_metagraph_kwarg_raises_on_role_mismatch():
    """M4 — target id exists but in graph with different role ⇒ XRefIntegrityError.

    target has tgt-node-1 in role=lexicon. Asking for role=ontology
    misses even though id matches.
    """
    source, target = make_source_and_target_metagraphs()
    with pytest.raises(XRefIntegrityError, match="under role"):
        source.add_xref(
            source_id="src-node-1",
            target_metagraph_id=target.metagraph_id,
            target_role="ontology",  # tgt-node-1 lives in lexicon
            target_id="tgt-node-1",
            ref_type="SPECIALISES",
            target_metagraph=target,
        )


def test_no_target_metagraph_kwarg_accepts_soft_xref():
    """M4 — target_metagraph=None ⇒ soft accept; no validation."""
    source, _target = make_source_and_target_metagraphs()
    x = source.add_xref(
        source_id="src-node-1",
        target_metagraph_id="mg-anything",
        target_role="anyrole",
        target_id="any-target-id",  # not validated
        ref_type="SPECIALISES",
    )
    assert x.xref_id in source.xrefs


def test_p59_validation_runs_before_xref_added_to_state():
    """P59 — failed validation must NOT leave partial state in mg.xrefs."""
    source, target = make_source_and_target_metagraphs()
    n_before = len(source.xrefs)
    dirty_before = len(source._xrefs_dirty)
    with pytest.raises(XRefIntegrityError):
        source.add_xref(
            source_id="src-node-1",
            target_metagraph_id=target.metagraph_id,
            target_role="lexicon",
            target_id="ghost",
            ref_type="SPECIALISES",
            target_metagraph=target,
        )
    # No XRef added to in-memory state on failed validation.
    assert len(source.xrefs) == n_before
    assert len(source._xrefs_dirty) == dirty_before
