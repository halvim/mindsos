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

from typing import AbstractSet, Callable, Dict, Iterable, Mapping, Tuple

__all__ = ["unavailable_inputs", "arity_unroutable_inputs", "declaration_refusals"]


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


def arity_unroutable_inputs(
    operand_arity: Mapping[str, int], is_collection: Callable[[str], bool]
) -> Tuple[str, ...]:
    """Declared inputs no route can satisfy, because of ``operand_arity``.

    A capacity emits **one value per output DataState**. So a consumer that
    declares ``operand_arity[k] = N > 1`` on a **scalar** input can never be
    fed by route-finding: whatever producer the walk picks supplies one value,
    ``_validate_inputs`` wants a length-N list, and the route composes and then
    raises ``InputContractError(kind="operand_arity")``. Measured in two real
    catalogs: **arc3 14 of 27, arc1 16 of 45**, on *both* finders.

    **The check is not "declares operand_arity" — it is "declares it on a
    scalar".** ADR-0205 §am-3's shape-2 ruling keeps ``operand_arity`` on the
    input after the collection migration, where it means *this collection must
    carry N members*. A producer of a collection input **can** satisfy that,
    and whether it does is a property of the value at run time, not of the
    declaration — so the executor keeps the length check and the finder must
    hold no opinion. Refusing every capacity that declares arity would delete
    the migration's own target.

    This is why the rule is a **declaration** predicate and not a walk one: the
    answer is the same for every start set, so it is computed once per view
    (:func:`declaration_refusals`) rather than per candidate. Contrast
    :func:`unavailable_inputs`, which depends on the path.

    Order follows the declaration's own mapping order.
    """
    return tuple(
        ds for ds, n in operand_arity.items() if n > 1 and not is_collection(ds)
    )


def declaration_refusals(
    capacity_layer, view, *, session=None
) -> Dict[str, Tuple[str, ...]]:
    """``capacity_iri -> the declared inputs that make it unroutable``.

    Computed **once per find** over the whole view, because every rule in it is
    answered from a declaration alone and would otherwise be recomputed for the
    same capacity at every step of a walk. Both finders read it: it is the
    shared half of step admission, where :func:`unavailable_inputs` is
    ``BFSFinder``-local.

    Resolution is **scope-correct** — a Local override of a capacity may
    declare different arity from the Global one, so this reads
    ``resolve_declaration`` rather than the merged ``get_declaration``.

    **A capacity node with no declaration is not refused.** That case is real
    and already documented at ``pipeline._input_group_of``: a graph-only node,
    such as a bare reference. Refusing on a declaration we do not have would
    invent a constraint; the honest default is to leave it to the executor.
    Only ``CapacityRegistrationError`` is caught — a broad ``except`` here
    would let the whole predicate go silently inert, which is this lane's
    recorded fifth blast-radius miss.

    C3R1b's *outputs meet inputs* rule joins this map; it is a declaration
    predicate too. It is not here yet.
    """
    from .exceptions import CapacityRegistrationError

    def is_collection(ds_iri: str) -> bool:
        node = view.get_datastate(ds_iri)
        return bool(node is not None and node.properties.get("collection"))

    refusals: Dict[str, Tuple[str, ...]] = {}
    for node in view.iter_capacities():
        iri = node.node_id
        try:
            declaration = capacity_layer.resolve_declaration(iri, session=session)
        except CapacityRegistrationError:
            continue
        arity = getattr(declaration, "operand_arity", None) or {}
        bad = arity_unroutable_inputs(arity, is_collection)
        if bad:
            refusals[iri] = bad
    return refusals
