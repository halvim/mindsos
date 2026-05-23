"""bootstrap_pending_global builds a Metagraph parallel to canonical.

Per Phase 24 design log PB-15(a) + Z11(a) + Z12(b).
"""

from __future__ import annotations


def test_bootstrap_pending_global_name(canonical_global_mg, pending_global_mg):
    """Pending Metagraph has the canonical name PENDING_GLOBAL_METAGRAPH_NAME."""
    from mindsos_admin import PENDING_GLOBAL_METAGRAPH_NAME

    assert pending_global_mg.name == PENDING_GLOBAL_METAGRAPH_NAME


def test_pending_global_mirrors_canonical_role_set(
    canonical_global_mg, pending_global_mg,
):
    """Z11(a) — pending has the same roles as canonical (parallel topology)."""
    canonical_roles = {g.role for g in canonical_global_mg.graphs.values()}
    pending_roles = {g.role for g in pending_global_mg.graphs.values()}
    assert canonical_roles == pending_roles
    # Phase 14 ships 6 named Global roles.
    assert len(canonical_roles) >= 6


def test_pending_global_starts_empty(pending_global_mg):
    """PB-15(a) — eager pending starts empty; admin propose populates."""
    for graph in pending_global_mg.graphs.values():
        assert len(graph.nodes) == 0, (
            f"Pending role {graph.role} should start empty; "
            f"has {len(graph.nodes)} nodes."
        )


def test_pending_global_is_independent_object(
    canonical_global_mg, pending_global_mg,
):
    """Z11(a) — pending is a separate Metagraph object (not the same instance)."""
    assert pending_global_mg is not canonical_global_mg
    assert pending_global_mg.metagraph_id != canonical_global_mg.metagraph_id
