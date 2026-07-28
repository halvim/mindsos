"""Reduction capability family (ADR-0204) — L4-support selection decisions.

Five pure selection capabilities the L4 orchestrator invokes as intelligence
decisions over a variable-size, per-member-scored collection:

- ``reduction.argmin`` / ``reduction.argmax`` → the member with the min / max
  score. Direction is fixed by the two named variants (not a parameter).
- ``reduction.top_k`` / ``reduction.bottom_k`` → the ``k`` highest- / lowest-score
  members, ranked best-first (largest-first for ``top_k``, smallest-first for
  ``bottom_k``). Direction is fixed by the two named variants, mirroring
  ``argmin``/``argmax`` — never a ``reverse`` parameter. ``k`` is a **declared
  input** the L4 layer supplies (never a literal); ``k > n`` clamps to ``n``.
- ``reduction.majority_vote`` → the modal label among the members.

These are **L4-invoked decisions**, not ``execution.py`` fold reducers: L4
dispatches each with its declared inputs (the map fan-out writes the scored
collection; L4 then invokes a reduction on it as the next step). No shipped
dispatch path is touched, and ``k`` needs no special channel.

**Scored-collection convention.** The single collection input is an ordered
list; each element (the *member*) is a mapping carrying a numeric score under
key ``"score"`` (and, for the vote, a label under key ``"label"``). Outputs are
**non-lossy** — a selection carries the member's ``index`` and ``score`` so the
caller need not re-derive them; the vote carries its tally.

**Ties / empties.** Ties resolve to **first-in-list** (input order is
authoritative — the caller controls order). An empty collection is a legitimate
"nothing found" **value**, never an error: ``argmin``/``argmax`` return ``None``,
``top_k``/``bottom_k`` return ``[]``, ``majority_vote`` returns ``{label: None,
won: 0, total: 0}``.

The family is **opt-in** (``install_reduction_v0``); its category graph is
created lazily at first register and it is NOT bootstrapped by ``create_global``
nor a member of ``FUNCTIONAL_CATEGORIES``. Bodies are real
(``placeholder=False``) — a permanent utility family, not a WSD placeholder.
Bodies are pure and context-agnostic (they ignore ``context``).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..bootstrap import ensure_datastate_graph
from ..capacity import Capacity
from ..datastate import DataState, ShapeDescriptor
from ..exceptions import CapacityRegistrationError
from ..identifiers import CATEGORY_REDUCTION, capacity_iri, datastate_iri


DS_SCORED_COLLECTION = datastate_iri("reduction.scored_collection")
DS_K = datastate_iri("reduction.k")
DS_SELECTION = datastate_iri("reduction.selection")
DS_K_SELECTION = datastate_iri("reduction.k_selection")
DS_VOTE = datastate_iri("reduction.vote")

#: Convention keys read off each member record.
SCORE_KEY = "score"
LABEL_KEY = "label"


def reduction_datastates() -> List[DataState]:
    return [
        DataState(
            name="reduction.scored_collection",
            shape=ShapeDescriptor.opaque("reduction.scored_collection"),
            description=(
                "Ordered collection of member records; each carries a numeric "
                "'score' (and 'label' for votes)."
            ),
            provenance_category=CATEGORY_REDUCTION,
        ),
        DataState(
            name="reduction.k",
            shape=ShapeDescriptor.scalar("int", opaque_tag="reduction.k"),
            description="How many members top_k/bottom_k select — an L4-supplied input.",
            provenance_category=CATEGORY_REDUCTION,
        ),
        DataState(
            name="reduction.selection",
            shape=ShapeDescriptor.opaque("reduction.selection"),
            description=(
                "Single selected member {index, member, score}, or None on an "
                "empty collection (argmin/argmax)."
            ),
            provenance_category=CATEGORY_REDUCTION,
        ),
        DataState(
            name="reduction.k_selection",
            shape=ShapeDescriptor.opaque("reduction.k_selection"),
            description=(
                "Ordered [{index, member, score}] of the k selected members, "
                "best-first — largest-first (top_k) or smallest-first (bottom_k); "
                "[] on an empty collection. Direction-neutral: the producing cap "
                "fixes the direction, mirroring reduction.selection for argmin/argmax."
            ),
            provenance_category=CATEGORY_REDUCTION,
        ),
        DataState(
            name="reduction.vote",
            shape=ShapeDescriptor.opaque("reduction.vote"),
            description=(
                "Modal-label verdict {label, won, total} (majority_vote); "
                "{label: None, won: 0, total: 0} on an empty collection."
            ),
            provenance_category=CATEGORY_REDUCTION,
        ),
    ]


# ── Pure selection logic ───────────────────────────────────────────────


def _arg_select(collection: Any, *, largest: bool) -> Optional[Dict[str, Any]]:
    """First member optimising the score. Strict comparison → first-in-list
    wins on ties. Returns None on an empty collection."""
    best: Optional[Dict[str, Any]] = None
    for index, member in enumerate(collection or []):
        score = member[SCORE_KEY]
        if best is None or (score > best["score"] if largest else score < best["score"]):
            best = {"index": index, "member": member, "score": score}
    return best


def _k_select(collection: Any, k: Any, *, largest: bool) -> List[Dict[str, Any]]:
    """The k best-scoring members, best-first — largest-first when ``largest``,
    smallest-first otherwise. Stable on ties (first-in-list), clamps k to the
    collection size, and returns [] for empty/k<=0. Direction is an internal
    argument; the two public caps (top_k / bottom_k) fix it, so there is no
    public reverse parameter (family convention, mirrors argmin/argmax)."""
    members = list(collection or [])
    k = int(k) if k is not None else 0
    if k <= 0 or not members:
        return []
    # sorted() is stable → equal scores keep original (first-in-list) order in
    # BOTH directions; slice to at most the collection size.
    order = sorted(range(len(members)), key=lambda i: members[i][SCORE_KEY], reverse=largest)
    return [
        {"index": i, "member": members[i], "score": members[i][SCORE_KEY]}
        for i in order[:k]
    ]


def _top_k(collection: Any, k: Any) -> List[Dict[str, Any]]:
    """The k highest-score members, best-first (largest-first)."""
    return _k_select(collection, k, largest=True)


def _bottom_k(collection: Any, k: Any) -> List[Dict[str, Any]]:
    """The k lowest-score members, best-first (smallest-first)."""
    return _k_select(collection, k, largest=False)


def _majority_vote(collection: Any) -> Dict[str, Any]:
    """Modal label. Ties resolve to the label appearing first in the input
    (dict preserves first-seen order; strict '>' keeps the first). Empty
    collection → a 'nothing found' verdict, not an error."""
    members = list(collection or [])
    counts: Dict[Any, int] = {}
    for member in members:
        label = member[LABEL_KEY]
        counts[label] = counts.get(label, 0) + 1
    winner: Any = None
    won = 0
    for label, count in counts.items():
        if count > won:
            winner, won = label, count
    return {"label": winner, "won": won, "total": len(members)}


# ── Capacity bodies (L4 dispatch surface) ──────────────────────────────


def _argmin_impl(**kwargs: Any) -> dict:
    return {DS_SELECTION: _arg_select(kwargs.get(DS_SCORED_COLLECTION), largest=False)}


def _argmax_impl(**kwargs: Any) -> dict:
    return {DS_SELECTION: _arg_select(kwargs.get(DS_SCORED_COLLECTION), largest=True)}


def _top_k_impl(**kwargs: Any) -> dict:
    return {DS_K_SELECTION: _top_k(kwargs.get(DS_SCORED_COLLECTION), kwargs.get(DS_K))}


def _bottom_k_impl(**kwargs: Any) -> dict:
    return {DS_K_SELECTION: _bottom_k(kwargs.get(DS_SCORED_COLLECTION), kwargs.get(DS_K))}


def _majority_vote_impl(**kwargs: Any) -> dict:
    return {DS_VOTE: _majority_vote(kwargs.get(DS_SCORED_COLLECTION))}


# ── Builders ───────────────────────────────────────────────────────────


def build_argmin() -> Capacity:
    return Capacity(
        name="argmin",
        category=CATEGORY_REDUCTION,
        inputs=(DS_SCORED_COLLECTION,),
        outputs=(DS_SELECTION,),
        implementation=_argmin_impl,
        description="Select the member with the minimum score (first-in-list on ties).",
    )


def build_argmax() -> Capacity:
    return Capacity(
        name="argmax",
        category=CATEGORY_REDUCTION,
        inputs=(DS_SCORED_COLLECTION,),
        outputs=(DS_SELECTION,),
        implementation=_argmax_impl,
        description="Select the member with the maximum score (first-in-list on ties).",
    )


def build_top_k() -> Capacity:
    return Capacity(
        name="top_k",
        category=CATEGORY_REDUCTION,
        inputs=(DS_SCORED_COLLECTION, DS_K),
        outputs=(DS_K_SELECTION,),
        implementation=_top_k_impl,
        description="Select the k highest-score members, best-first; k>n clamps to n.",
    )


def build_bottom_k() -> Capacity:
    return Capacity(
        name="bottom_k",
        category=CATEGORY_REDUCTION,
        inputs=(DS_SCORED_COLLECTION, DS_K),
        outputs=(DS_K_SELECTION,),
        implementation=_bottom_k_impl,
        description="Select the k lowest-score members, smallest-first; k>n clamps to n.",
    )


def build_majority_vote() -> Capacity:
    return Capacity(
        name="majority_vote",
        category=CATEGORY_REDUCTION,
        inputs=(DS_SCORED_COLLECTION,),
        outputs=(DS_VOTE,),
        implementation=_majority_vote_impl,
        description="Select the modal label; ties resolve to first-in-list.",
    )


_DS_IRIS = (
    DS_SCORED_COLLECTION,
    DS_K,
    DS_SELECTION,
    DS_K_SELECTION,
    DS_VOTE,
)
_CAP_IRIS = (
    capacity_iri(CATEGORY_REDUCTION, "argmin"),
    capacity_iri(CATEGORY_REDUCTION, "argmax"),
    capacity_iri(CATEGORY_REDUCTION, "top_k"),
    capacity_iri(CATEGORY_REDUCTION, "bottom_k"),
    capacity_iri(CATEGORY_REDUCTION, "majority_vote"),
)


def install_reduction_v0(capacity_layer) -> None:
    """Idempotent opt-in install of the reduction family (mirrors the v0
    catalogs). All-present → no-op; a partial state raises."""
    mg = capacity_layer.global_metagraph()
    cap_index = capacity_layer._capacity_index[mg.metagraph_id]
    ds_graph = ensure_datastate_graph(mg, strict=capacity_layer._strict)

    ds_present = {iri for iri in _DS_IRIS if iri in ds_graph.nodes}
    cap_present = {iri for iri in _CAP_IRIS if iri in cap_index}
    present_total = len(ds_present) + len(cap_present)

    if present_total == len(_DS_IRIS) + len(_CAP_IRIS):
        return
    if present_total > 0:
        raise CapacityRegistrationError(
            "install_reduction_v0: partial install state detected — "
            f"datastates_present={sorted(ds_present)}, "
            f"capacities_present={sorted(cap_present)}"
        )
    for ds in reduction_datastates():
        capacity_layer.register_datastate(ds, allow_new_realm=True)
    capacity_layer.register_capacity(build_argmin())
    capacity_layer.register_capacity(build_argmax())
    capacity_layer.register_capacity(build_top_k())
    capacity_layer.register_capacity(build_bottom_k())
    capacity_layer.register_capacity(build_majority_vote())


__all__ = [
    "DS_SCORED_COLLECTION",
    "DS_K",
    "DS_SELECTION",
    "DS_K_SELECTION",
    "DS_VOTE",
    "SCORE_KEY",
    "LABEL_KEY",
    "reduction_datastates",
    "build_argmin",
    "build_argmax",
    "build_top_k",
    "build_bottom_k",
    "build_majority_vote",
    "install_reduction_v0",
]
