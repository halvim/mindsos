"""Phase 41 — cl.iter_monitors() enumerates registered Monitors (ADR-0155).

L3 ships the enumeration producer; the L4 substrate (Phase 46) consumes
it to build the session-scope MonitorSubscriptionRegistry. There is no
v1 consumer (acceptable per the Stream-B DAG — same pattern as Phase 40
family_rules ahead of its L4 consumer).
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer, Monitor
from mindsos_capacity.builtins import DS_RAW_TEXT, install_text_capacities
from mindsos_capacity.identifiers import CATEGORY_PERCEPTION, capacity_iri


def _make_monitor(name: str) -> Monitor:
    return Monitor(
        name=name,
        category=CATEGORY_PERCEPTION,
        inputs=(),
        outputs=(),
        subscribes_to=(DS_RAW_TEXT,),
        emits=(),
        implementation=lambda **kw: None,
        description=f"Test monitor {name!r}.",
    )


def test_iter_monitors_empty_on_no_monitor_layer():
    layer = CapacityLayer()
    assert layer.iter_monitors() == []


def test_iter_monitors_enumerates_registered_monitor():
    layer = CapacityLayer()
    install_text_capacities(layer)
    layer.register_capacity(_make_monitor("text.change_monitor"))

    monitors = layer.iter_monitors()
    assert [m.iri for m in monitors] == [
        capacity_iri(CATEGORY_PERCEPTION, "text.change_monitor")
    ]
    assert all(isinstance(m, Monitor) for m in monitors)


def test_iter_monitors_excludes_reactive_capacities():
    layer = CapacityLayer()
    # install_text_capacities registers reactive Capacity declarations.
    install_text_capacities(layer)
    layer.register_capacity(_make_monitor("text.change_monitor"))

    monitors = layer.iter_monitors()
    assert len(monitors) == 1
    assert all(isinstance(m, Monitor) for m in monitors)
