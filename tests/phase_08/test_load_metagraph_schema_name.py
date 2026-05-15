"""PB-11 A — schema_name round-trips into mg.schema_name; vocab NOT auto-attached."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def test_schema_name_round_trips_when_set(falkor_client) -> None:
    """Persisted :Metagraph.schema_name reloads into mg.schema_name."""
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.reconstruction import load_metagraph

    mg = Metagraph(name="m-with-schema", identity=IdentityRegistry())
    mg.schema_name = "my-schema"

    MetagraphRepository(falkor_client).persist(mg)
    mg2 = load_metagraph(falkor_client, mg.metagraph_id)

    assert mg2.schema_name == "my-schema"


def test_schema_name_none_when_absent(falkor_client) -> None:
    """Persisted without schema_name → mg.schema_name reloads as None."""
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.reconstruction import load_metagraph

    mg = Metagraph(name="m-no-schema", identity=IdentityRegistry())
    # schema_name not set — defaults to None on the dataclass.
    MetagraphRepository(falkor_client).persist(mg)
    mg2 = load_metagraph(falkor_client, mg.metagraph_id)

    assert mg2.schema_name is None


def test_schema_vocab_not_auto_attached_per_pb_11_a(falkor_client) -> None:
    """PB-11 A — schema_name set; mg.schema (vocab) is NOT auto-attached."""
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.reconstruction import load_metagraph

    mg = Metagraph(name="m-name-only", identity=IdentityRegistry())
    mg.schema_name = "vocab-X"
    MetagraphRepository(falkor_client).persist(mg)

    mg2 = load_metagraph(falkor_client, mg.metagraph_id)
    assert mg2.schema_name == "vocab-X"
    # mg.schema is the actual vocab object — Phase 08 does NOT
    # auto-attach. L2 territory.
    assert getattr(mg2, "schema", None) is None
