"""R4-7 A+C — refresh identity preservation tests."""

from __future__ import annotations

import weakref

import pytest

pytestmark = pytest.mark.integration


def test_refresh_preserves_metagraph_and_identity_object_identity(
    falkor_client,
) -> None:
    """R4-7 A — id(mg) and id(mg.identity) survive refresh."""
    from mindsos_core.models.graph import Graph
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.reconstruction import MetagraphLoader

    mg = Metagraph(name="m-refresh", identity=IdentityRegistry())
    g = Graph(name="g1", role="lex", identity=mg.identity)
    g.add_node(value="x", type_name="T", node_id="n1", _validate=False)
    mg.add_graph(g)

    MetagraphRepository(falkor_client).persist(mg)

    pre_id_mg = id(mg)
    pre_id_id = id(mg.identity)

    loader = MetagraphLoader(falkor_client)
    loader.refresh(mg, role="lex")

    assert id(mg) == pre_id_mg, "Metagraph object identity drifted"
    assert id(mg.identity) == pre_id_id, "IdentityRegistry identity drifted"


def test_refresh_preserves_weakref_proxy(falkor_client) -> None:
    """R4-7 C — external weakref.proxy(mg.identity) survives refresh."""
    from mindsos_core.models.graph import Graph
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.reconstruction import MetagraphLoader

    mg = Metagraph(name="m-refresh-weakref", identity=IdentityRegistry())
    g = Graph(name="g1", role="lex", identity=mg.identity)
    g.add_node(value="x", type_name="T", node_id="n1", _validate=False)
    mg.add_graph(g)

    MetagraphRepository(falkor_client).persist(mg)

    proxy = weakref.proxy(mg.identity)

    loader = MetagraphLoader(falkor_client)
    loader.refresh(mg, role="lex")

    # Proxy still resolves — downstream cached refs survive.
    # Touch a method via the proxy; any call confirms the referent is
    # alive. ``register`` is idempotent on a no-conflict id.
    try:
        proxy.register("smoke-test-id")
        proxy.unregister("smoke-test-id")
    except ReferenceError:
        pytest.fail(
            "weakref.proxy(mg.identity) became dangling after refresh"
        )
