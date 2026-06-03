"""Phase 43 PR2 — confidence detector script smoke tests.

Per design log §6.2 + R0 PB-43-10. Asserts:

* The detector module imports + ``main()`` returns 0 when no
  ``confidence``-carrying Pipeline rows are visible (clean state).
* Exit code 1 when at least one ``confidence``-carrying row is
  injected via a mocked FalkorDB connection.

The detector connects to a live FalkorDB in production; here we mock
the connection so the test runs in CI without a Falkor instance.
"""

from __future__ import annotations

import importlib
import sys
import unittest.mock as mock
from pathlib import Path


# tools/ is not on sys.path by default; add the repo root + tools dir.
_REPO_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))

import check_phase_43_confidence_state as detector  # noqa: E402


def _fake_db_with(graphs: dict[str, list[str]]) -> mock.Mock:
    """Build a mock FalkorDB whose graphs report the given Pipeline IRIs.

    ``graphs`` maps ``graph_name -> list[iri]`` for Pipeline rows
    carrying ``confidence``. Empty list = clean graph; non-empty =
    findings.
    """
    db = mock.Mock()
    db.list_graphs.return_value = list(graphs.keys())

    def select_graph(name: str) -> mock.Mock:
        g = mock.Mock()
        rows = [[iri] for iri in graphs[name]]
        res = mock.Mock()
        res.result_set = rows
        g.query.return_value = res
        return g

    db.select_graph.side_effect = select_graph
    return db


def test_main_returns_0_on_clean_state() -> None:
    fake = _fake_db_with({
        "promoted-pipelines-v1": [],
        "ontology-v1": [],
    })
    with mock.patch.object(detector, "_connect", return_value=fake):
        assert detector.main([]) == 0


def test_main_returns_1_on_injected_confidence() -> None:
    fake = _fake_db_with({
        "promoted-pipelines-v1": [
            "promoted-pipelines-v1:pipeline:p_with_confidence"
        ],
    })
    with mock.patch.object(detector, "_connect", return_value=fake):
        assert detector.main([]) == 1


def test_main_skips_non_pipeline_graphs() -> None:
    """Only promoted-pipelines-* graphs are scanned (cost optimization)."""
    fake = _fake_db_with({
        # Pretend ontology has a "confidence" row — should NOT count
        # because we skip non-pipeline graphs.
        "ontology-v1": ["ontology-v1:Class:weird"],
    })
    with mock.patch.object(detector, "_connect", return_value=fake):
        assert detector.main([]) == 0
