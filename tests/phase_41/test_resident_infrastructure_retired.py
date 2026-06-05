"""Phase 41 — resident infrastructure retired (ADR-0155); hard-break sentinel.

Two-pronged per the Phase 41 R0 PB-2 decision:

1. **Importability** — none of the retired symbols resolve from the
   ``mindsos_capacity`` package (nor remain in ``__all__``); the
   ``CapacityLayer`` lifecycle methods are gone.
2. **Scoped grep** — no retired symbol token appears in any shipped
   ``mindsos_capacity/**/*.py``. Docs, ADRs (ADR-0073/0155), the
   CHANGELOG, and this sentinel file are intentionally **out of scope**:
   they legitimately reference the retired API as history.

A repo-wide grep is deliberately NOT used — ADR-0155 documents the
retirement and would self-trip it.
"""

from __future__ import annotations

import pathlib

import mindsos_capacity


_RETIRED = (
    "start_resident",
    "stop_resident",
    "active_subscriptions",
    "ResidentSubscription",
    "ResidentError",
    "KIND_RESIDENT",
)

_PKG_DIR = pathlib.Path(mindsos_capacity.__file__).resolve().parent


def test_retired_symbols_not_importable():
    for name in _RETIRED:
        assert not hasattr(mindsos_capacity, name), (
            f"{name} still importable from mindsos_capacity after ADR-0155"
        )
        assert name not in mindsos_capacity.__all__, (
            f"{name} still listed in mindsos_capacity.__all__"
        )


def test_capacity_layer_lifecycle_methods_removed():
    from mindsos_capacity import CapacityLayer

    for meth in ("start_resident", "stop_resident", "active_subscriptions"):
        assert not hasattr(CapacityLayer, meth), (
            f"CapacityLayer.{meth} was not removed (ADR-0155)"
        )


def test_no_retired_token_in_shipped_package():
    """Scoped grep — the shipped package carries zero references to the
    retired surfaces (docstrings + comments included)."""
    offenders = []
    for py in sorted(_PKG_DIR.rglob("*.py")):
        text = py.read_text(encoding="utf-8")
        for tok in _RETIRED:
            if tok in text:
                offenders.append((py.relative_to(_PKG_DIR).as_posix(), tok))
    assert not offenders, f"retired tokens in shipped package: {offenders}"
