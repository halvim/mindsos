"""source_user_id != None raises NotImplementedError (PB-11(a) → Phase 25)."""

from __future__ import annotations

import pytest

from mindsos_admin import (
    NodeSpec,
    PromotionItem,
    PromotionItemKind,
    PromotionProposal,
    propose_for_promotion,
)


def test_source_user_id_set_raises_not_implemented(
    seeded_admin, admin_session_propose, pending_global_mg,
):
    """Setting source_user_id triggers Phase 25 deferral per ADR-0008 §am1."""
    proposal = PromotionProposal(
        items=[
            PromotionItem(
                kind=PromotionItemKind.ATOM,
                node=NodeSpec(
                    node_type="Class", value="X",
                    properties={}, target_role="ontology",
                ),
                source_user_id="alice",  # Phase 25 path
            )
        ],
    )
    with pytest.raises(NotImplementedError, match="Phase 25"):
        propose_for_promotion(
            seeded_admin,
            session=admin_session_propose,
            proposal=proposal,
            pending_global_mg=pending_global_mg,
        )


def test_empty_proposal_raises_value_error(
    seeded_admin, admin_session_propose, pending_global_mg,
):
    """ValueError on empty proposal items list."""
    proposal = PromotionProposal(items=[])
    with pytest.raises(ValueError, match="empty"):
        propose_for_promotion(
            seeded_admin,
            session=admin_session_propose,
            proposal=proposal,
            pending_global_mg=pending_global_mg,
        )
