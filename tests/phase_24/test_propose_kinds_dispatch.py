"""PromotionItemKind dispatch — only ATOM works at Phase 24.

Per PB-3(a) — STRUCTURE / SUBGRAPH / PIPELINE raise NotImplementedError.
"""

from __future__ import annotations

import pytest

from mindsos_admin import (
    NodeSpec,
    PromotionItem,
    PromotionItemKind,
    PromotionProposal,
    propose_for_promotion,
)


@pytest.mark.parametrize(
    "kind", [
        PromotionItemKind.STRUCTURE,
        PromotionItemKind.SUBGRAPH,
        PromotionItemKind.PIPELINE,
    ],
)
def test_non_atom_kinds_raise_not_implemented(
    kind, seeded_admin, admin_session_propose, pending_global_mg,
):
    """STRUCTURE/SUBGRAPH/PIPELINE dispatch raises NotImplementedError."""
    # PromotionItem.__post_init__ allows non-ATOM (only ATOM-without-node
    # is rejected at construction); the dispatch fires in propose.
    proposal = PromotionProposal(
        items=[PromotionItem(kind=kind)],
    )
    with pytest.raises(NotImplementedError, match=kind.value):
        propose_for_promotion(
            seeded_admin,
            session=admin_session_propose,
            proposal=proposal,
            pending_global_mg=pending_global_mg,
        )


def test_atom_dispatch_works(
    seeded_admin, admin_session_propose, pending_global_mg,
    atom_proposal_factory,
):
    """ATOM kind dispatches to validator + works."""
    proposal = atom_proposal_factory()
    result = propose_for_promotion(
        seeded_admin, session=admin_session_propose,
        proposal=proposal, pending_global_mg=pending_global_mg,
    )
    assert len(result.mutation_ids) == 1


def test_promotion_item_atom_without_node_rejected_at_construction():
    """PromotionItem(kind=ATOM) requires node:NodeSpec; ValueError at __post_init__."""
    with pytest.raises(ValueError, match="ATOM"):
        PromotionItem(kind=PromotionItemKind.ATOM, node=None)


def test_promotion_item_kind_enum_has_four_values():
    """Forward-shape contract per PB-18(a) — all 4 enum values ship."""
    assert {k.value for k in PromotionItemKind} == {
        "ATOM", "STRUCTURE", "SUBGRAPH", "PIPELINE",
    }
