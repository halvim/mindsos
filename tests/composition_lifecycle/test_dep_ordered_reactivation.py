"""composition-lifecycle — dep-ordered re-activation (server half, PB-C).

``mindsos_server.local_boot._dep_order_descriptors`` topologically orders
re-activatable composite descriptors via ``mindsos_knowledge.kahn_sort``
(placed in the server because ``mindsos_capacity`` may not import
``mindsos_knowledge``). A composite whose serialized DAG references
another in-batch composite re-activates after it.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    COMPOSITE_DAG,
    Capacity,
    DAGStep,
    PipelineDAG,
    REACTIVATION_KEY,
    register_reactivation_factory,
    unregister_reactivation_factory,
)
from mindsos_knowledge.exceptions import BootstrapCycleError
from mindsos_server.local_boot import _dep_order_descriptors

_KEY = "composition_lifecycle_test"


def _factory(descriptor):
    """Rebuild a composite as a bare Capacity named from the descriptor."""
    name = descriptor["name"]
    return Capacity(
        name=name,
        category=CATEGORY_PERCEPTION,
        inputs=(),
        outputs=(f"datastate:t.out_{name}",),
        implementation=lambda **kw: {},
    )


@pytest.fixture(autouse=True)
def _register_factory():
    register_reactivation_factory(_KEY, _factory, if_exists="upsert")
    yield
    unregister_reactivation_factory(_KEY)


def _composite(name: str, depends_on=()):
    """A re-activatable descriptor whose DAG references the deps' IRIs."""
    steps = tuple(
        DAGStep(f"capacity:perception:{d}", (), (f"datastate:t.out_{d}",))
        for d in depends_on
    )
    dag = PipelineDAG(
        start_datastates=(),
        target_datastate=f"datastate:t.out_{name}",
        steps=steps,
        edges=(),
    )
    return {REACTIVATION_KEY: _KEY, "name": name, COMPOSITE_DAG: dag.to_dict()}


def _names(ordered):
    return [d["name"] for d in ordered]


def test_dependency_ordered_before_dependent():
    # a depends on b; b depends on c  =>  c, b, a
    descriptors = [
        _composite("a", depends_on=("b",)),
        _composite("b", depends_on=("c",)),
        _composite("c"),
    ]
    ordered = _names(_dep_order_descriptors(descriptors))
    assert ordered.index("c") < ordered.index("b") < ordered.index("a")


def test_independent_composites_preserved_deterministically():
    descriptors = [_composite("b"), _composite("a")]
    # no deps -> kahn_sort breaks ties alphabetically
    assert _names(_dep_order_descriptors(descriptors)) == ["a", "b"]


def test_single_descriptor_unchanged():
    d = [_composite("solo")]
    assert _dep_order_descriptors(d) == d


def test_non_reactivatable_appended_after_composites():
    installer = {REACTIVATION_KEY: "installer", "name": "inst"}
    descriptors = [installer, _composite("a", depends_on=("b",)), _composite("b")]
    ordered = _names(_dep_order_descriptors(descriptors))
    assert ordered.index("b") < ordered.index("a")
    assert ordered[-1] == "inst"  # installer-backed, ordered after composites


def test_cycle_raises():
    descriptors = [
        _composite("a", depends_on=("b",)),
        _composite("b", depends_on=("a",)),
    ]
    with pytest.raises(BootstrapCycleError):
        _dep_order_descriptors(descriptors)
