"""CompositeInstance mutability + duplicates + cycle + cross-metagraph
+ stale-ref tests (Phase 06 row §C + round-7 P50/P55)."""

from __future__ import annotations

import pytest

from mindsos_core import Graph, Metagraph
from mindsos_core.exceptions import IdentityError
import mindsos_instances as mi
from mindsos_instances.exceptions import (
    CompositeCycleError,
    CrossMetagraphCompositeError,
    OverrideScopeError,
)


# ── construction (round-7 P50 A — metagraph_id required) ───────────────────


def test_composite_construction_requires_metagraph_id(mg, reg=None):
    reg = mi.attach_registry(mg)
    comp = mi.CompositeInstance(
        metagraph_id=mg.metagraph_id,
        _registry=reg,
    )
    assert comp.metagraph_id == mg.metagraph_id


def test_composite_metagraph_mismatch_raises():
    mg_a = Metagraph(name="A")
    mi.attach_registry(mg_a)
    mg_b = Metagraph(name="B")
    reg_b = mi.attach_registry(mg_b)
    with pytest.raises(IdentityError):
        mi.CompositeInstance(
            metagraph_id=mg_a.metagraph_id,  # mismatch
            _registry=reg_b,
        )


def test_composite_empty_legal(mg, reg=None):
    reg = mi.attach_registry(mg)
    comp = mi.CompositeInstance(
        metagraph_id=mg.metagraph_id,
        _registry=reg,
    )
    assert comp.members == []


# ── bundle_overrides validation (round-7 P61 A scope="composite") ──────────


def test_bundle_overrides_accept_user_property():
    mg = Metagraph(name="MG")
    reg = mi.attach_registry(mg)
    comp = mi.CompositeInstance(
        metagraph_id=mg.metagraph_id,
        bundle_overrides={"category": "demo"},
        _registry=reg,
    )
    assert comp.bundle_overrides["category"] == "demo"


def test_bundle_overrides_reject_reserved_key():
    mg = Metagraph(name="MG")
    reg = mi.attach_registry(mg)
    with pytest.raises(OverrideScopeError):
        mi.CompositeInstance(
            metagraph_id=mg.metagraph_id,
            bundle_overrides={"role": "spoofed"},  # role is reserved
            _registry=reg,
        )


def test_bundle_overrides_reject_ov_prefix():
    mg = Metagraph(name="MG")
    reg = mi.attach_registry(mg)
    with pytest.raises(OverrideScopeError):
        mi.CompositeInstance(
            metagraph_id=mg.metagraph_id,
            bundle_overrides={"ov__forbidden": 1},
            _registry=reg,
        )


# ── member mutation (P37 A — duplicates allowed, ordered) ──────────────────


def test_composite_add_member(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    n_template = next(iter(g.nodes.values()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=n_template.node_id,
        _registry=reg,
    )
    reg.add(ni)
    comp = mi.CompositeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        _registry=reg,
    )
    reg.add(comp)
    comp.add_member(ni, _registry=reg)
    assert comp.members == [ni]


def test_composite_duplicates_allowed(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    n_template = next(iter(g.nodes.values()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=n_template.node_id,
        _registry=reg,
    )
    reg.add(ni)
    comp = mi.CompositeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        _registry=reg,
    )
    reg.add(comp)
    comp.add_member(ni, _registry=reg)
    comp.add_member(ni, _registry=reg)
    assert len(comp.members) == 2


def test_composite_remove_member_by_occurrence(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    n_template = next(iter(g.nodes.values()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=n_template.node_id,
        _registry=reg,
    )
    reg.add(ni)
    comp = mi.CompositeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        _registry=reg,
    )
    reg.add(comp)
    comp.add_member(ni, _registry=reg)
    comp.add_member(ni, _registry=reg)
    comp.add_member(ni, _registry=reg)
    comp.remove_member(ni.id, occurrence=1)
    assert len(comp.members) == 2


def test_composite_remove_member_oob_raises(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    n_template = next(iter(g.nodes.values()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=n_template.node_id,
        _registry=reg,
    )
    reg.add(ni)
    comp = mi.CompositeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        _registry=reg,
    )
    reg.add(comp)
    comp.add_member(ni, _registry=reg)
    with pytest.raises(IndexError):
        comp.remove_member(ni.id, occurrence=5)


def test_composite_remove_all_members(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    n_template = next(iter(g.nodes.values()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=n_template.node_id,
        _registry=reg,
    )
    reg.add(ni)
    comp = mi.CompositeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        _registry=reg,
    )
    reg.add(comp)
    comp.add_member(ni, _registry=reg)
    comp.add_member(ni, _registry=reg)
    count = comp.remove_all_members(ni.id)
    assert count == 2
    assert comp.members == []


# ── cycle detection (P25 A) ────────────────────────────────────────────────


def test_composite_cycle_self_rejected(mg, reg=None):
    reg = mi.attach_registry(mg)
    comp = mi.CompositeInstance(
        metagraph_id=mg.metagraph_id,
        _registry=reg,
    )
    reg.add(comp)
    with pytest.raises(CompositeCycleError):
        comp.add_member(comp, _registry=reg)


def test_composite_cycle_through_nested_rejected(mg, reg=None):
    reg = mi.attach_registry(mg)
    a = mi.CompositeInstance(
        metagraph_id=mg.metagraph_id,
        _registry=reg,
    )
    reg.add(a)
    b = mi.CompositeInstance(
        metagraph_id=mg.metagraph_id,
        _registry=reg,
    )
    reg.add(b)
    a.add_member(b, _registry=reg)
    # b → a would close the cycle a → b → a
    with pytest.raises(CompositeCycleError):
        b.add_member(a, _registry=reg)


# ── cross-metagraph rejection (P43 C + round-7 P50 A) ──────────────────────


def test_composite_cross_metagraph_rejected():
    mg_a = Metagraph(name="A")
    reg_a = mi.attach_registry(mg_a)
    g_a = Graph(name="GA")
    mg_a.add_graph(g_a)
    n_a = g_a.add_node("a", type_name="T")
    ni_a = mi.NodeInstance(
        metagraph_id=mg_a.metagraph_id,
        template_id=n_a.node_id,
        _registry=reg_a,
    )
    reg_a.add(ni_a)

    mg_b = Metagraph(name="B")
    reg_b = mi.attach_registry(mg_b)
    comp_b = mi.CompositeInstance(
        metagraph_id=mg_b.metagraph_id,
        _registry=reg_b,
    )
    reg_b.add(comp_b)
    with pytest.raises(CrossMetagraphCompositeError):
        comp_b.add_member(ni_a, _registry=reg_b)


# ── stale-ref rejection (round-7 P55 A) ────────────────────────────────────


def test_composite_add_member_rejects_unregistered(mg_with_graph, reg):
    """An instance not added to the registry can't be a composite
    member."""
    g = next(iter(mg_with_graph.graphs.values()))
    n_template = next(iter(g.nodes.values()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=n_template.node_id,
        _registry=reg,
    )
    # NOT calling reg.add(ni) — ni is unregistered.
    comp = mi.CompositeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        _registry=reg,
    )
    reg.add(comp)
    with pytest.raises(IdentityError):
        comp.add_member(ni, _registry=reg)


def test_composite_add_member_rejects_cascade_removed_instance(
    mg_with_graph, reg
):
    """After cascade-remove, the instance object exists but is not in
    the registry — add_member must reject it."""
    g = next(iter(mg_with_graph.graphs.values()))
    template = next(iter(g.nodes.values()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=template.node_id,
        _registry=reg,
    )
    reg.add(ni)
    # Cascade-remove the template → ni is removed from registry.
    g.remove_node(template.node_id)
    assert ni.id not in reg
    comp = mi.CompositeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        _registry=reg,
    )
    reg.add(comp)
    with pytest.raises(IdentityError):
        comp.add_member(ni, _registry=reg)
