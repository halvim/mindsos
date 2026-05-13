"""OCC unit tests (Phase 07 — P66 A unit/integration split).

Per M7 — L1 ships the mechanism, no policy. ``_version`` always bumps
on update path (P7 C); OCC predicate is opt-in via ``expected_version``.
``MissingExpectedVersionError`` lives at L0/L2 (P84 B), NOT at L1.
"""

from __future__ import annotations

import pytest

from mindsos_core import exceptions
from mindsos_core.exceptions import (
    OptimisticConcurrencyConflict,
    OptimisticConcurrencyExhausted,
    PersistenceError,
)
from mindsos_core.models.node import Node
from mindsos_core.models.edge import Edge, HyperEdge
from mindsos_core.models.metagraph import MetaEdge, MetaHyperEdge
from mindsos_core.models.intergraph_edge import IntergraphEdge
from mindsos_core.models.intergraph_hyperedge import IntergraphHyperEdge


def test_version_default_is_1_on_all_7_core_types() -> None:
    """P10 A + P26 A — every persistable Core element gains _version: int = 1."""
    n = Node(value="v", type_name="T")
    e = Edge(source=Node("a", "T"), target=Node("b", "T"), type_name="REL")
    h = HyperEdge(nodes={Node("a", "T"), Node("b", "T")}, type_name="HE")
    me = MetaEdge(source_graph_id="g1", target_graph_id="g2", type_name="MREL")
    mh = MetaHyperEdge(graph_ids=["g1", "g2", "g3"], type_name="MHE")
    ie = IntergraphEdge(
        source_graph_id="g1", source_node_id="n1",
        target_graph_id="g2", target_node_id="n2",
        type_name="XREL",
    )
    ih = IntergraphHyperEdge(
        anchors=(("g1", "n1"),),
        members=(("g2", "n2"), ("g3", "n3")),
        type_name="XHE",
    )
    for obj in (n, e, h, me, mh, ie, ih):
        assert obj._version == 1, (
            f"{type(obj).__name__}._version expected 1, got {obj._version}"
        )


def test_missing_expected_version_error_is_NOT_at_L1() -> None:
    """P84 B — exception lives at L0/L2 (Global-policy wrapper). L1 does not export it."""
    assert not hasattr(exceptions, "MissingExpectedVersionError")


def test_l1_exception_set_is_4_classes() -> None:
    """P21 A amended P84 B — L1 ships 4 persistence exceptions only."""
    for name in (
        "PersistenceError",
        "IntegrityCheckError",
        "OptimisticConcurrencyConflict",
        "OptimisticConcurrencyExhausted",
    ):
        assert hasattr(exceptions, name)


def test_occc_carries_element_id_expected_actual() -> None:
    e = OptimisticConcurrencyConflict("n123", 5, 7)
    assert e.element_id == "n123"
    assert e.expected_version == 5
    assert e.actual_version == 7
    assert "n123" in str(e) and "expected _version=5" in str(e)


def test_occ_exhausted_is_subclass_of_persistence_error() -> None:
    """P57 A — OptimisticConcurrencyExhausted ships as definition-only at L1."""
    assert issubclass(OptimisticConcurrencyExhausted, PersistenceError)
    # Instantiable (no raise-path test at L1 per P57 A).
    e = OptimisticConcurrencyExhausted("retries exhausted on update")
    assert "retries exhausted" in str(e)


def test_graph_repository_update_path_returns_new_version() -> None:
    """Update path returns ``int`` version from RETURN row."""
    from mindsos_core.persistence import GraphRepository, InMemoryClient

    c = InMemoryClient()
    c.script([{"id": "n1", "version": 7}])
    repo = GraphRepository(c)
    new_v = repo.update_node_properties("g1", "n1", {"k": "v"})
    assert new_v == 7


def test_graph_repository_update_raises_occ_on_stale_expected() -> None:
    """Stale expected_version → zero rows → OptimisticConcurrencyConflict."""
    from mindsos_core.persistence import GraphRepository, InMemoryClient

    c = InMemoryClient()
    c.script([])  # MATCH returns zero rows.
    repo = GraphRepository(c)
    with pytest.raises(OptimisticConcurrencyConflict) as exc_info:
        repo.update_node_properties("g1", "n1", {"k": "v"}, expected_version=2)
    assert exc_info.value.element_id == "n1"
    assert exc_info.value.expected_version == 2
