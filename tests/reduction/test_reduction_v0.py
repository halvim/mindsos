"""Reduction capability family (ADR-0204) — per-cap behaviour + install.

Bodies are exercised directly via each builder's ``implementation`` (they are
pure functions of their declared inputs); install idempotency + registration
go through a fresh ``CapacityLayer`` (mirrors the v0-catalog install tests).
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer
from mindsos_capacity.bootstrap import ensure_datastate_graph
from mindsos_capacity.builtins.reduction_v0 import (
    DS_K,
    DS_K_SELECTION,
    DS_SCORED_COLLECTION,
    DS_SELECTION,
    DS_VOTE,
    build_argmax,
    build_argmin,
    build_bottom_k,
    build_majority_vote,
    build_top_k,
    install_reduction_v0,
)


def _argmin(collection):
    return build_argmin().implementation(**{DS_SCORED_COLLECTION: collection})[DS_SELECTION]


def _argmax(collection):
    return build_argmax().implementation(**{DS_SCORED_COLLECTION: collection})[DS_SELECTION]


def _top_k(collection, k):
    return build_top_k().implementation(
        **{DS_SCORED_COLLECTION: collection, DS_K: k}
    )[DS_K_SELECTION]


def _bottom_k(collection, k):
    return build_bottom_k().implementation(
        **{DS_SCORED_COLLECTION: collection, DS_K: k}
    )[DS_K_SELECTION]


def _vote(collection):
    return build_majority_vote().implementation(
        **{DS_SCORED_COLLECTION: collection}
    )[DS_VOTE]


# A collection with a score tie (idx 1 and 2 both 0.9) and a label majority.
C = [
    {"score": 0.5, "label": "a"},
    {"score": 0.9, "label": "b"},
    {"score": 0.9, "label": "a"},
    {"score": 0.1, "label": "a"},
]


def test_argmax_picks_highest_first_on_tie():
    sel = _argmax(C)
    assert sel["index"] == 1
    assert sel["score"] == 0.9
    assert sel["member"] is C[1]


def test_argmin_picks_lowest():
    sel = _argmin(C)
    assert sel["index"] == 3
    assert sel["score"] == 0.1


def test_top_k_ranks_best_first_and_is_stable_on_ties():
    top = _top_k(C, 3)
    assert [t["index"] for t in top] == [1, 2, 0]
    assert [t["score"] for t in top] == [0.9, 0.9, 0.5]


def test_top_k_clamps_when_k_exceeds_n():
    assert len(_top_k(C, 99)) == len(C)


def test_top_k_non_positive_k_is_empty():
    assert _top_k(C, 0) == []
    assert _top_k(C, -3) == []


def test_bottom_k_ranks_smallest_first_and_is_stable_on_ties():
    # C scores: [0.5, 0.9, 0.9, 0.1] → ascending: idx3(0.1), idx0(0.5), idx1(0.9)
    bot = _bottom_k(C, 3)
    assert [b["index"] for b in bot] == [3, 0, 1]
    assert [b["score"] for b in bot] == [0.1, 0.5, 0.9]


def test_bottom_k_tie_at_boundary_resolves_to_first_in_list():
    tie = [{"score": 0.9}, {"score": 0.1}, {"score": 0.1}, {"score": 0.5}]
    bot = _bottom_k(tie, 2)
    assert [b["index"] for b in bot] == [1, 2]  # first-in-list among equal smallest


def test_bottom_k_clamps_when_k_exceeds_n():
    assert len(_bottom_k(C, 99)) == len(C)


def test_bottom_k_non_positive_k_is_empty():
    assert _bottom_k(C, 0) == []
    assert _bottom_k(C, -3) == []


def test_top_k_and_bottom_k_are_opposite_ends():
    # Full ranking one way is the reverse of the other (no ties across all four).
    coll = [{"score": 0.2}, {"score": 0.8}, {"score": 0.5}, {"score": 0.1}]
    top = [t["index"] for t in _top_k(coll, 4)]
    bot = [b["index"] for b in _bottom_k(coll, 4)]
    assert top == list(reversed(bot))


def test_majority_vote_modal_label_with_tally():
    assert _vote(C) == {"label": "a", "won": 3, "total": 4}


def test_majority_vote_tie_resolves_to_first_in_list():
    tie = [{"label": "x"}, {"label": "y"}, {"label": "y"}, {"label": "x"}]
    assert _vote(tie) == {"label": "x", "won": 2, "total": 4}


def test_empty_collection_is_nothing_found_not_error():
    assert _argmin([]) is None
    assert _argmax([]) is None
    assert _top_k([], 3) == []
    assert _bottom_k([], 3) == []
    assert _vote([]) == {"label": None, "won": 0, "total": 0}


def test_direction_pairs_share_one_neutral_output_datastate():
    # argmin/argmax share reduction.selection; top_k/bottom_k share
    # reduction.k_selection. Direction is fixed by the cap, not the output DS.
    assert build_argmin().outputs == build_argmax().outputs == (DS_SELECTION,)
    assert build_top_k().outputs == build_bottom_k().outputs == (DS_K_SELECTION,)


def test_install_is_idempotent_and_registers_family():
    layer = CapacityLayer()
    install_reduction_v0(layer)
    install_reduction_v0(layer)  # second call is a no-op
    ds_graph = ensure_datastate_graph(layer.global_metagraph())
    cap_index = layer._capacity_index[layer.global_metagraph().metagraph_id]
    assert len(ds_graph.nodes) == 5  # top_k + bottom_k share reduction.k_selection
    assert len(cap_index) == 5


def test_composition_top_k_then_majority_vote():
    """Nearest-then-vote composed as two reductions: score = similarity
    (higher = nearer), take the 3 best, then vote their labels."""
    library = [
        {"score": 0.95, "label": "fridge"},
        {"score": 0.90, "label": "kettle"},
        {"score": 0.88, "label": "fridge"},
        {"score": 0.10, "label": "kettle"},
    ]
    top = _top_k(library, 3)
    voted = _vote([t["member"] for t in top])
    assert voted["label"] == "fridge"
    assert voted["total"] == 3


def test_composition_bottom_k_then_majority_vote_distance_native():
    """k-NN stated in raw distance (lower = nearer): bottom_k selects the 3
    nearest directly — no score-negation adapter — then vote their labels."""
    library = [
        {"score": 0.05, "label": "fridge"},   # distance
        {"score": 0.10, "label": "kettle"},
        {"score": 0.12, "label": "fridge"},
        {"score": 0.90, "label": "kettle"},
    ]
    nearest = _bottom_k(library, 3)
    voted = _vote([n["member"] for n in nearest])
    assert voted["label"] == "fridge"
    assert voted["total"] == 3
