"""Step admission — the checks a finder applies before it takes a capacity.

**Why this module exists at all.** ``ConjunctionFinder``'s producer checks live
as closures inside ``find()`` (``ds_reachable`` / ``cap_satisfiable`` /
``eligible``), and ``BFSFinder`` has no producer-selection stage whatsoever.
A closure cannot be called from a test, which is the recorded reason defects
**D-B** and **D-E** survived to a tagged commit
(``CORE_CR_FINDER_AS_CAPACITIES.md`` §8 item 2). Everything here is a
module-level function over plain values, so each rule can be made to fail on
its own.

**The three rules, and they are not the same kind of thing.**

``operand_arity`` and *outputs-meet-inputs* are answered from a capacity's
**declaration** alone — the same answer every time, for every start set. They
belong in a refusal set computed once per ``CapacityLayerView`` and read by
both finders. They arrive at the two items after this one.

:func:`unavailable_inputs` is different: it depends on **where the walk is**,
so it is evaluated per candidate, and it is **``BFSFinder``-local**.
``ConjunctionFinder`` answers the same case by *wiring* the missing input as
another step, so refusing it there would kill routes it correctly builds —
which is why the same three cases report NOT FOUND under Conjunction and
compose under BFS.

**Two of the three retire.** Under the Capacity Graph Traversal rewrite
(``CORE_CAPACITY_GRAPH_TRAVERSAL.md``) a capacity cannot feed itself, so the
outputs-meet-inputs rule has nothing left to refuse, and the walk only ever
uses DataStates it already holds, so availability is intrinsic. Only the
``operand_arity`` rule survives. Do not build a three-way structure that must
be unpicked — the same warning the five ``FIND_REASONS`` carry.
"""

from __future__ import annotations

from typing import AbstractSet, Iterable, Tuple

__all__ = ["unavailable_inputs"]


def unavailable_inputs(
    declared_inputs: Iterable[str], available: AbstractSet[str]
) -> Tuple[str, ...]:
    """Declared inputs that are **not on the path**, in declaration order.

    ``available`` is the walk's start DataStates together with the outputs of
    every step taken so far on *this* path — which is exactly the blackboard
    ``execute_pipeline`` will hand the capacity. It builds
    ``{ds: blackboard[ds] for ds in step.input_datastates if ds in blackboard}``
    and never consults ``DAGEdge``, so an input that is absent there is a
    dispatch-time ``InputContractError(kind="missing_required")`` however the
    edges are drawn.

    **Why availability and not reachability.** The rule was first stated as
    *"are the other declared inputs reachable from the starts?"*. That is
    over-permissive: an input can be reachable and still not have been
    produced along the branch the walk is currently on, and the route then
    composes and dies at dispatch exactly as before. Reachability is a
    property of the catalog; what execution checks is a property of the path.

    A capacity with one declared input is never refused — the walk arrives on
    that input, so it is available by construction. Refusals begin at two.
    """
    return tuple(ds for ds in declared_inputs if ds not in available)
