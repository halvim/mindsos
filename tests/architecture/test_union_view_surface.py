"""Structural guard — ``LocalPreferringView`` must cover the read surface.

**Why this file exists.** An earlier attempt at the two-tier union view
shipped a duck-typed shim implementing five methods
(``producers_of`` / ``consumers_of`` / ``inputs_of`` / ``outputs_of`` /
``get_capacity``). It was written against a finder that only called those
five. ``admission.declaration_refusals`` then landed on ``main`` calling
``view.iter_capacities()`` and ``view.get_datastate()``, and because the
shim is deliberately NOT a ``CapacityLayerView`` subclass there was no
inheritance to absorb the difference — every session-scoped find would
have raised ``AttributeError``. Nothing caught it, because no test asserts
what a view *is*.

So this guard is structural, in the same spirit as
``test_finder_return_annotations.py``: it reads the finder path's actual
attribute accesses out of the source and fails if the union view cannot
answer one. A new ``view.<something>`` call site in ``pipeline.py`` or
``admission.py`` breaks this test at collection time rather than at the
bottom of a 34-minute gate.
"""

from __future__ import annotations

import ast
import inspect
from typing import Set

from mindsos_capacity import admission, pipeline
from mindsos_capacity.views import CapacityLayerView, LocalPreferringView


#: Members of ``CapacityLayerView`` that expose its single backing store.
#: A union has no one ``Metagraph`` and no one ``Graph`` per category, so
#: these have no honest answer and are deliberately not mirrored. They are
#: listed rather than pattern-matched so that deleting one from
#: ``CapacityLayerView`` fails the pairing test below instead of silently
#: widening the exemption.
STORE_EXPOSING = frozenset(
    {"metagraph", "name", "category_graph", "datastates_graph"}
)


def _view_attribute_calls(module) -> Set[str]:
    """Attribute names read off a local/parameter named ``view`` in ``module``."""
    tree = ast.parse(inspect.getsource(module))
    found: Set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "view"
        ):
            found.add(node.attr)
    return found


def test_union_view_answers_every_view_call_on_the_finder_path():
    """The exact regression: a ``view.<attr>`` the union view cannot answer."""
    required = _view_attribute_calls(pipeline) | _view_attribute_calls(admission)
    assert required, "found no `view.<attr>` accesses — this guard is inert"

    missing = sorted(a for a in required if not hasattr(LocalPreferringView, a))
    assert not missing, (
        f"LocalPreferringView is missing {missing}, which pipeline.py or "
        f"admission.py calls on the view returned by _view_for. A "
        f"session-scoped find would raise AttributeError."
    )


def test_union_view_mirrors_the_capacity_layer_view_read_surface():
    """Beyond current call sites: mirror the whole read surface but the store."""
    expected = {
        n for n in dir(CapacityLayerView) if not n.startswith("_")
    } - STORE_EXPOSING
    actual = {n for n in dir(LocalPreferringView) if not n.startswith("_")}

    missing = sorted(expected - actual)
    assert not missing, (
        f"CapacityLayerView exposes {missing} and LocalPreferringView does "
        f"not. Either mirror it with union semantics, or add it to "
        f"STORE_EXPOSING with a reason."
    )


def test_store_exposing_names_all_still_exist():
    """Keeps the exemption honest if ``CapacityLayerView`` is refactored."""
    stale = sorted(n for n in STORE_EXPOSING if not hasattr(CapacityLayerView, n))
    assert not stale, (
        f"STORE_EXPOSING lists {stale}, which CapacityLayerView no longer has. "
        f"Drop them — a stale exemption hides a real gap."
    )
