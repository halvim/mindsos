"""Phase 47 — replan invalidation + signal/ALS skeletons.

Covers replan_check.invalidate_at_and_below, the 10 signal-source
skeletons (S7 reserved), and the 11 ALS subsystem skeletons.
"""

from __future__ import annotations

import pytest

from mindsos_intelligence.als_registry import ALSSubsystemRegistry
from mindsos_intelligence.als_subsystems import (
    ALS_SUBSYSTEM_SKELETONS,
    register_als_subsystems,
)
from mindsos_intelligence.chain_artifacts import TaskRun
from mindsos_intelligence.replan_check import invalidate_at_and_below
from mindsos_intelligence.signal_sources import register_signal_sources


def test_invalidate_at_and_below_clears_pipeline_runs():
    tr = TaskRun(iri="taskrun:t:1", pipeline_runs=["pr:1", "pr:2"])
    invalidated = invalidate_at_and_below(tr, "pipeline")
    assert invalidated == ["pr:1", "pr:2"]
    assert tr.pipeline_runs == []


def test_invalidate_rejects_unknown_level():
    with pytest.raises(ValueError):
        invalidate_at_and_below(TaskRun(iri="taskrun:t:1"), "bogus")


def test_ten_signal_sources_s7_reserved():
    sources = register_signal_sources()
    assert len(sources) == 10
    assert sources["S7"].reserved is True
    assert sources["S7"].iri is None
    assert sources["S6"].iri == "signal.task_outcome"
    assert sources["S10"].iri == "signal.plan_decomposition_outcome"
    assert all(s.payload_contract == () for s in sources.values())


def test_eleven_als_subsystems_registered_as_skeletons():
    reg = register_als_subsystems(ALSSubsystemRegistry())
    assert len(reg) == 11
    assert len(ALS_SUBSYSTEM_SKELETONS) == 11
    for key in reg.keys():
        r = reg.get(key)
        assert r.update_mechanisms == {}
        assert r.validation_methods == ()
        assert r.audit_policy in {"auto-apply", "batched-summary", "individual-review"}
