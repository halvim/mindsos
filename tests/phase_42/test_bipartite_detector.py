"""Phase 42 — bipartite-state detector (PB-7 migrator->detector).

The detector (`tools/check_phase_42_bipartite_state.py`) replaces the
PHASE_MAP's planned one-pass migrator: the v1 CapacityLayer is
in-memory-first with no persisted Global capacity state, so a migrator
would be dead code. This test exercises the detector's structure without
a live FalkorDB (the actual scan runs in CI/ops).
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

_TOOLS = (
    pathlib.Path(__file__).resolve().parents[2]
    / "tools"
    / "check_phase_42_bipartite_state.py"
)


def _load():
    spec = importlib.util.spec_from_file_location(
        "check_phase_42_bipartite_state", _TOOLS
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_detector_file_exists():
    assert _TOOLS.is_file()


def test_detector_targets_capacity_node_types():
    mod = _load()
    assert mod.CAPACITY_NODE_TYPES == ("Capacity", "Monitor", "Adapter")
    assert callable(mod.main)


def test_detector_help_exits_zero():
    mod = _load()
    with pytest.raises(SystemExit) as exc:
        mod.main(["--help"])
    assert exc.value.code == 0
