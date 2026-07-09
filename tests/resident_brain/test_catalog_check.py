"""Unit tests for :func:`mindsos_capacity.catalog_check.catalog_check`.

Uses duck-typed fake views so the checks are exercised in isolation from a
full layer boot, plus one real ephemeral-boot smoke asserting the builtins
catalog is orphan-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from mindsos_capacity.catalog_check import catalog_check


@dataclass
class _N:
    node_id: str


class _FakeView:
    """Minimal CapacityLayerView surface catalog_check consumes."""

    def __init__(self, caps: Dict[str, dict], datastates: List[str]) -> None:
        # caps: iri -> {"in": [ds...], "out": [ds...]}
        self._caps = caps
        self._ds = datastates

    def iter_capacities(self, category=None):
        return (_N(iri) for iri in self._caps)

    def iter_datastates(self):
        return (_N(iri) for iri in self._ds)

    def get_datastate(self, iri):
        return _N(iri) if iri in self._ds else None

    def inputs_of(self, iri):
        return list(self._caps.get(iri, {}).get("in", []))

    def outputs_of(self, iri):
        return list(self._caps.get(iri, {}).get("out", []))

    def producers_of(self, ds):
        return [_N(c) for c, spec in self._caps.items() if ds in spec.get("out", [])]

    def consumers_of(self, ds):
        return [_N(c) for c, spec in self._caps.items() if ds in spec.get("in", [])]


def test_linear_chain_sources_and_sinks():
    view = _FakeView(
        caps={
            "cap:a": {"in": ["ds:raw"], "out": ["ds:mid"]},
            "cap:b": {"in": ["ds:mid"], "out": ["ds:done"]},
        },
        datastates=["ds:raw", "ds:mid", "ds:done"],
    )
    r = catalog_check(view)
    assert r.capacities == 2
    assert r.datastates == 3
    # ds:raw consumed but not produced -> entry point (source), NOT a defect.
    assert ("cap:a", "ds:raw") in r.sources
    # ds:done produced but not consumed -> terminal sink.
    assert ("cap:b", "ds:done") in r.sinks
    assert r.orphans == []
    assert r.ok is True


def test_source_is_not_a_defect():
    # A perception entry point (raw input) has no producer — must stay ok.
    view = _FakeView(
        caps={"cap:perceive": {"in": ["ds:raw_text"], "out": ["ds:tokens"]}},
        datastates=["ds:raw_text", "ds:tokens"],
    )
    r = catalog_check(view)
    assert ("cap:perceive", "ds:raw_text") in r.sources
    assert r.ok is True


def test_orphan_flips_ok():
    view = _FakeView(caps={}, datastates=["ds:lonely"])
    r = catalog_check(view)
    assert r.orphans == ["ds:lonely"]
    assert r.ok is False


def test_terminal_sink_reported():
    view = _FakeView(
        caps={
            "cap:src": {"in": [], "out": ["ds:in"]},
            "cap:sink": {"in": ["ds:in"], "out": ["ds:out"]},
        },
        datastates=["ds:in", "ds:out"],
    )
    r = catalog_check(view)
    assert ("cap:sink", "ds:out") in r.sinks
    assert r.orphans == []
    assert r.ok is True


def test_ephemeral_builtins_catalog_is_orphan_free():
    from mindsos_server.boot import boot_brain

    stack = boot_brain(user="checker")
    r = catalog_check(stack.global_view())
    assert r.capacities > 0
    assert r.datastates > 0
    assert r.orphans == [], f"builtins catalog has orphan datastates: {r.orphans}"
