"""Phase 14 — ``KnowledgeLayer.__init__`` / ``bootstrap`` / repr.

Covers:

* Empty construction (no Global) — :meth:`global_metagraph` raises.
* Constructor with pre-loaded Global (ADR-0042 §amendment-1 path).
* ``bootstrap()`` classmethod fresh-Global path.
* ``id_strategy`` parameter override (PB-11 lock).
* ``__repr__`` shape.
"""

from __future__ import annotations

import pytest

from mindsos_core import Metagraph
from mindsos_core.models.identity import UUID4Strategy, IRIPassthroughStrategy

from mindsos_knowledge import KnowledgeLayer


def test_empty_kl_constructible() -> None:
    """KL() with no arguments constructs an empty instance.

    Per Phase 14 PB-7 + PB-12 calibration: permissive constructor;
    empty KL is a valid test fixture state.
    """
    kl = KnowledgeLayer()
    # No Global installed → global_metagraph raises.
    with pytest.raises(RuntimeError, match="No Global metagraph"):
        kl.global_metagraph()
    # No Locals installed.
    assert kl.installed_user_ids() == frozenset()


def test_kl_with_preloaded_global() -> None:
    """KL(global_metagraph=mg) accepts the constructor parameter.

    Per ADR-0042 §amendment-1 server-load path.
    """
    mg = Metagraph(name="test_global")
    kl = KnowledgeLayer(global_metagraph=mg)
    assert kl.global_metagraph() is mg


def test_bootstrap_creates_fresh_global() -> None:
    """``bootstrap()`` mints a fresh Global with the canonical name."""
    kl = KnowledgeLayer.bootstrap()
    g = kl.global_metagraph()
    assert g.name == "global_knowledge"
    # Bootstrap minted 11 named Global role-graphs (Phase 43 §am-5: 6
    # base + 3 dual-scope additions; Phase 50 §am-6: + installed-skills;
    # feat/subminds §am-7: + subminds); no alignment-pair graphs
    # (Phase 15 importers do those).
    assert len(g.graphs) == 12


def test_bootstrap_with_id_strategy_override() -> None:
    """``bootstrap(id_strategy=...)`` plumbs through (PB-11 lock).

    Per ADR-0131 pluggable IdStrategy.
    """
    strategy = IRIPassthroughStrategy()
    kl = KnowledgeLayer.bootstrap(id_strategy=strategy)
    assert kl.global_metagraph().id_strategy is strategy


def test_default_id_strategy_is_uuid4() -> None:
    """Phase 14 PB-11 default: UUID4Strategy."""
    kl = KnowledgeLayer()
    # _id_strategy is internal but the default behaviour is observable
    # — UUID4 strategy minted metagraphs have random metagraph_ids.
    assert isinstance(kl._id_strategy, UUID4Strategy)


def test_kl_repr_shape() -> None:
    """``__repr__`` shows global metagraph id + installed-local count."""
    kl = KnowledgeLayer.bootstrap()
    r = repr(kl)
    assert "KnowledgeLayer(" in r
    assert "global_metagraph_id=" in r
    assert "installed_local_count=0" in r


def test_kl_repr_empty_global() -> None:
    """``__repr__`` shows ``global_metagraph_id=None`` for empty KL."""
    r = repr(KnowledgeLayer())
    assert "global_metagraph_id=None" in r
