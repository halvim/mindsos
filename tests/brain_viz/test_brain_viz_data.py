"""Unit coverage for ``mindsos_cli.brain_viz.build_data`` — the headless core of
the ``view`` REPL verb. Pure duck-typed views; no FalkorDB / Stack.

Covers the brain-neutral labelling landed alongside the arc1/arc3 viz_spec hooks:
per-brain ``CAP_LABELS`` / ``DS_LABELS`` / ``TITLE`` pass-through, the generic
heuristic ds-group labels, present-only legend filtering, and the node-id
collision warning (distinct IRIs that collapse to one ``cap:``/``ds:`` short id).
"""
from __future__ import annotations

import logging

from mindsos_cli.brain_viz import build_data


class _N:
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id


class _View:
    """A minimal capacity view: two datastates collide on their short name."""

    _DS = ["arc.grid", "arc.palette", "other.grid"]  # arc.grid & other.grid -> ds:grid
    _CAPS = {"perceiver": ["arc.perceive"], "reasoning": ["arc.reason"]}
    _IO = {
        "arc.perceive": (["arc.grid"], ["arc.palette"]),
        "arc.reason": (["arc.palette"], []),
    }

    def iter_datastates(self):
        return [_N(x) for x in self._DS]

    def iter_categories(self):
        return list(self._CAPS)

    def iter_capacities(self, cat=None):
        if cat is None:
            return [_N(c) for cs in self._CAPS.values() for c in cs]
        return [_N(c) for c in self._CAPS.get(cat, [])]

    def get_capacity(self, iri):
        return _N(iri) if any(iri in v for v in self._CAPS.values()) else None

    def inputs_of(self, iri):
        return self._IO.get(iri, ([], []))[0]

    def outputs_of(self, iri):
        return self._IO.get(iri, ([], []))[1]


class _Spec:
    DS_GROUPS: dict = {}  # force the topology heuristic
    CAP_LABELS = {"perceiver": "Perceiver", "reasoning": "Reasoning"}
    DS_LABELS: dict = {}
    TITLE = "arc1_brain graph"


def test_title_and_labels_emitted():
    data = build_data([_View()], spec=_Spec())
    assert data["title"] == "arc1_brain graph"
    # per-brain cap labels pass through, filtered to families actually present
    assert data["capNames"] == {"perceiver": "Perceiver", "reasoning": "Reasoning"}
    # generic heuristic ds labels appear for the groups the heuristic assigns
    assert data["dsNames"]["given"] == "given (entry input)"
    assert data["dsNames"]["derived"] == "derived"


def test_legend_is_present_only():
    data = build_data([_View()], spec=_Spec())
    # only groups/families that occur in nodes are legended
    node_ds_groups = {n["group"] for n in data["nodes"] if n["kind"] == "ds"}
    assert set(data["dsColor"]) == node_ds_groups
    assert set(data["dsNames"]) <= node_ds_groups
    assert "l2" not in data["dsColor"]  # nilm-specific default never leaks in


def test_id_collision_warns(caplog):
    with caplog.at_level(logging.WARNING, logger="mindsos_cli.brain_viz"):
        build_data([_View()], spec=_Spec())
    msgs = [r.getMessage() for r in caplog.records]
    assert any("ds:grid" in m and "collides" in m for m in msgs), msgs


def test_no_spec_degrades_cleanly():
    data = build_data([_View()], spec=None)
    assert data["title"] is None
    assert data["capNames"] == {}          # no per-brain labels -> template falls back to key
    assert data["dsNames"]["given"] == "given (entry input)"  # generic labels still there
