"""feat/subminds Slice 1 — ADR-0155 reversal mechanics + layer isolation.

The reversal is *partial*: resident self-firing returns at **L4** (the
SubMindScheduler), NOT as the deleted L3 ``start_resident``/
``stop_resident`` lifecycle. ADR-0155's L3-purity must still hold — no
resident loop in ``mindsos_capacity``. The SubMind runtime lives in
``mindsos_intelligence`` and imports only downward.
"""

from __future__ import annotations

import inspect

import mindsos_capacity
import mindsos_intelligence
from mindsos_capacity.capacity_layer import CapacityLayer


def test_l3_has_no_resident_lifecycle():
    # ADR-0155 retirement preserved at L3 (the loop returns at L4 only).
    for banned in ("start_resident", "stop_resident", "active_subscriptions"):
        assert not hasattr(CapacityLayer, banned), (
            f"ADR-0155 reversal must NOT re-add {banned!r} to L3 "
            f"CapacityLayer; the resident loop lives at L4."
        )


def test_l3_still_declares_kind_monitor():
    # The check-capacity declaration reused by the Reflex feed (Slice 3).
    assert hasattr(mindsos_capacity, "KIND_MONITOR")


def test_submind_runtime_is_l4():
    for name in ("SubMind", "SubMindScheduler", "SubMindRegistry"):
        assert hasattr(mindsos_intelligence, name)
        cls = getattr(mindsos_intelligence, name)
        assert cls.__module__.startswith("mindsos_intelligence.")


def test_l3_does_not_import_intelligence():
    # No upward import: nothing in mindsos_capacity source pulls L4.
    src_dir = inspect.getfile(mindsos_capacity)
    import pathlib

    root = pathlib.Path(src_dir).parent
    offenders = []
    for py in root.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if "import mindsos_intelligence" in text or "from mindsos_intelligence" in text:
            offenders.append(py.name)
    assert not offenders, f"L3 must not import L4; offenders: {offenders}"
