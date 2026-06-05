"""Phase 41 — KIND_RESIDENT renamed to KIND_MONITOR (ADR-0155).

The node_kind property *value* changes from "resident" to "monitor"; the
node_kind triad is now REACTIVE / MONITOR / ADAPTER.
"""

from __future__ import annotations

import mindsos_capacity
from mindsos_capacity import KIND_MONITOR, Monitor, NODE_KINDS
from mindsos_capacity.identifiers import CATEGORY_PERCEPTION


def test_kind_monitor_value_is_monitor():
    assert KIND_MONITOR == "monitor"


def test_kind_monitor_in_node_kinds():
    assert KIND_MONITOR in NODE_KINDS


def test_kind_resident_removed():
    assert not hasattr(mindsos_capacity, "KIND_RESIDENT")
    assert "KIND_RESIDENT" not in mindsos_capacity.__all__
    assert "KIND_MONITOR" in mindsos_capacity.__all__


def test_monitor_node_kind_is_monitor():
    m = Monitor(
        name="x.mon",
        category=CATEGORY_PERCEPTION,
        inputs=(),
        outputs=(),
        subscribes_to=(),
        emits=(),
        implementation=lambda **kw: None,
        description="d",
    )
    assert m.node_kind == KIND_MONITOR
    assert m.to_properties()["node_kind"] == "monitor"
