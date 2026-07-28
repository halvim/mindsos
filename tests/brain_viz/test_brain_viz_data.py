"""Unit coverage for ``mindsos_cli.brain_viz.build_data`` — the headless core of
the ``view`` REPL verb. Pure duck-typed views; no FalkorDB / Stack.

Covers the brain-neutral labelling (per-brain ``CAP_LABELS`` / ``DS_LABELS`` /
``TITLE`` + generic heuristic ds labels, present-only legend filtering) and the
node-id uniqueness regression: two datastates that share a short name must stay
distinct nodes, or ``vis.DataSet`` raises "id already exists" and the graph never
renders (the arc1 blank-graph bug).
"""
from __future__ import annotations

from mindsos_cli.brain_viz import build_data


class _N:
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id


class _View:
    """Two datastates share the short name 'goal' across namespaces."""

    _DS = ["path_finding.goal", "phase1.goal", "arc.grid"]
    _CAPS = {"perceiver": ["arc.perceive"], "reasoning": ["arc.reason"]}
    _IO = {
        "arc.perceive": (["arc.grid"], ["path_finding.goal"]),
        "arc.reason": (["path_finding.goal"], []),
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


def test_shared_short_name_stays_distinct():
    """Regression: distinct IRIs with the same short name must be distinct nodes
    with unique ids (else vis.DataSet crashes and the graph is blank)."""
    data = build_data([_View()], spec=_Spec())
    ds = [n for n in data["nodes"] if n["kind"] == "ds"]
    ids = [n["id"] for n in ds]
    assert len(ids) == len(set(ids)), f"duplicate node ids: {ids}"
    assert "ds:path_finding.goal" in ids and "ds:phase1.goal" in ids
    # the short label is still what the user sees
    assert sorted(n["label"] for n in ds) == ["goal", "goal", "grid"]


def test_title_and_labels_emitted():
    data = build_data([_View()], spec=_Spec())
    assert data["title"] == "arc1_brain graph"
    assert data["capNames"] == {"perceiver": "Perceiver", "reasoning": "Reasoning"}
    assert data["dsNames"]["given"] == "given (entry input)"
    assert data["dsNames"]["derived"] == "derived"


def test_legend_is_present_only():
    data = build_data([_View()], spec=_Spec())
    node_ds_groups = {n["group"] for n in data["nodes"] if n["kind"] == "ds"}
    assert set(data["dsColor"]) == node_ds_groups
    assert set(data["dsNames"]) <= node_ds_groups
    assert "l2" not in data["dsColor"]  # nilm-specific default never leaks in


def test_no_spec_degrades_cleanly():
    data = build_data([_View()], spec=None)
    assert data["title"] is None
    assert data["capNames"] == {}
    assert data["dsNames"]["given"] == "given (entry input)"
