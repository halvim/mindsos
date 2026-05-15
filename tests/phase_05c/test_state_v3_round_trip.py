"""Phase 05c — metagraph state-file v=3 round-trip + migration tests.

Phase 05d round-7 P43 audit: schema-side ``_state_version`` constants
in this file were hard-coded to ``2`` under the 05c shipped baseline.
Phase 05d bumps the metagraph-schema state file v=2 → v=3 (round-7
P31 A — only state-file bump that ships in 05d). Schema-side
assertions migrated to dynamic ``ms_migrations.CURRENT_VERSION`` so
the 05c step-coverage in this file survives the 05d bump unchanged.
Metagraph-side assertions (``state_mod.METAGRAPH_STATE_VERSION ==
3``) remain hard-coded to 3 because the metagraph state file is
NOT bumped in 05d (P31 A removed the fingerprint mechanism).
"""

from __future__ import annotations

import json

import pytest

from mindsos_cli import state as state_mod
from mindsos_cli.migrations import metagraph as mg_migrations
from mindsos_cli.migrations import metagraph_schema as ms_migrations


class TestStateVersionConstants:
    def test_metagraph_state_version_is_3(self):
        # Phase 05d: metagraph state file stays at v=3 (P31 A —
        # fingerprint mechanism dropped, no bump). This assertion
        # therefore remains valid under 05d.
        assert state_mod.METAGRAPH_STATE_VERSION == mg_migrations.CURRENT_VERSION

    def test_metagraph_schema_state_version_at_current(self):
        # Phase 05d (round-7 P43): dynamic — schema bumps v=2 → v=3
        # under 05d's only state-file bump.
        assert (
            state_mod.METAGRAPH_SCHEMA_STATE_VERSION
            == ms_migrations.CURRENT_VERSION
        )


class TestMetagraphMigrationV2ToV3:
    def test_v2_to_v3_populates_default_intergraph_hyperedges(self):
        v2 = {
            "_state_version": 2,
            "metagraph_id": "mg-id",
            "name": "test",
            "properties": {},
            "schema_name": None,
            "contained_graphs": [],
            "metaedges": [],
            "metahyperedges": [],
            "intergraph_edges": [],
        }
        result = mg_migrations.migrate(v2)
        # Phase 09 RR-12 — chain advances to current; v=2 input now
        # walks v=2→v=3→v=4 picking up xrefs[] default in step 4.
        assert result["_state_version"] == mg_migrations.CURRENT_VERSION
        assert result["intergraph_hyperedges"] == []

    def test_v1_chain_through_to_current(self):
        v1 = {
            "_state_version": 1,
            "metagraph_id": "mg-id",
            "name": "test",
            "properties": {},
            "contained_graphs": [],
            "metaedges": [],
            "metahyperedges": [],
        }
        result = mg_migrations.migrate(v1)
        # Phase 09 RR-12 — chain advances v=1→v=current.
        assert result["_state_version"] == mg_migrations.CURRENT_VERSION
        # v=2 step adds intergraph_edges + schema_name defaults.
        assert result["intergraph_edges"] == []
        assert result["schema_name"] is None
        # v=3 step adds intergraph_hyperedges default.
        assert result["intergraph_hyperedges"] == []
        # v=4 step adds xrefs default (Phase 09).
        assert result["xrefs"] == []

    def test_v3_migrates_to_current(self):
        """Phase 09 RR-12 — v=3 input is no longer idempotent; migrates
        forward to current adding ``xrefs`` default. Replaces the
        Phase 05c-era ``test_v3_idempotent`` with the post-bump shape.
        """
        v3 = {
            "_state_version": 3,
            "metagraph_id": "mg-id",
            "name": "test",
            "properties": {},
            "schema_name": None,
            "contained_graphs": [],
            "metaedges": [],
            "metahyperedges": [],
            "intergraph_edges": [],
            "intergraph_hyperedges": [{"edge_id": "ihe1"}],
        }
        result = mg_migrations.migrate(v3)
        assert result["_state_version"] == mg_migrations.CURRENT_VERSION
        # Pre-existing intergraph_hyperedges preserved.
        assert result["intergraph_hyperedges"] == [{"edge_id": "ihe1"}]
        # v=3→v=4 step adds xrefs default.
        assert result["xrefs"] == []

    def test_forward_version_refused(self):
        """Phase 09 RR-12 — forward fixture uses dynamic CURRENT_VERSION + 1
        so the test moves with future bumps without literal-version edits.
        """
        forward = mg_migrations.CURRENT_VERSION + 1
        with pytest.raises(ValueError) as exc:
            mg_migrations.migrate({"_state_version": forward, "name": "test"})
        assert f"v{mg_migrations.CURRENT_VERSION}" in str(exc.value)


class TestMetagraphSchemaMigrationV1ToV2:
    def test_v1_to_v2_populates_default_intergraph_hyperedge_types(self):
        v1 = {
            "_state_version": 1,
            "name": "ms",
            "strict": False,
            "intergraph_edge_types": [],
        }
        result = ms_migrations.migrate(v1)
        # Phase 05d round-7 P43: dynamic — under 05d the chain advances
        # v=1 → v=3. The v=1→v=2 step's payload (intergraph_hyperedge_types)
        # survives subsequent steps.
        assert result["_state_version"] == ms_migrations.CURRENT_VERSION
        assert result["intergraph_hyperedge_types"] == []

    def test_v1_preserves_existing_intergraph_edge_types(self):
        v1 = {
            "_state_version": 1,
            "name": "ms",
            "strict": True,
            "intergraph_edge_types": [{"name": "EVOKES"}],
        }
        result = ms_migrations.migrate(v1)
        assert result["intergraph_edge_types"] == [{"name": "EVOKES"}]
        assert result["strict"] is True

    def test_v2_advances_to_current(self):
        """Phase 05d round-7 P43: under 05c, v=2 was idempotent. Under 05d
        the chain advances v=2 → v=3 (adding meta_edge_types +
        meta_hyperedge_types defaults). Dynamic CURRENT_VERSION
        future-proofs.
        """
        v2 = {
            "_state_version": 2,
            "name": "ms",
            "strict": False,
            "intergraph_edge_types": [],
            "intergraph_hyperedge_types": [{"name": "COMPOSED_OF"}],
        }
        result = ms_migrations.migrate(v2)
        assert result["_state_version"] == ms_migrations.CURRENT_VERSION
        assert result["intergraph_hyperedge_types"] == [{"name": "COMPOSED_OF"}]

    def test_forward_version_refused(self):
        # Phase 05d round-7 P43: dynamic — fixture uses
        # CURRENT_VERSION + 1 so the test moves with future bumps.
        forward = ms_migrations.CURRENT_VERSION + 1
        with pytest.raises(ValueError) as exc:
            ms_migrations.migrate({"_state_version": forward, "name": "test"})
        assert f"v{ms_migrations.CURRENT_VERSION}" in str(exc.value)


class TestRoundTripMetagraphV3:
    def test_serialize_and_reload(self, tmp_path, monkeypatch):
        from mindsos_core import Graph, Metagraph
        from mindsos_cli.commands.metagraph import (
            _metagraph_to_state, _state_to_metagraph,
        )
        monkeypatch.setenv("MINDSOS_STATE_DIR", str(tmp_path))
        # Build a metagraph with a hyperedge.
        mg = Metagraph(name="rt")
        g_w = Graph(name="word", role="word")
        g_l = Graph(name="letter", role="letter")
        mg.add_graph(g_w)
        mg.add_graph(g_l)
        g_w.add_node("cat", type_name="Word", node_id="cat")
        g_l.add_node("c", type_name="Letter", node_id="c")
        g_l.add_node("a", type_name="Letter", node_id="a")
        ihe = mg.add_intergraph_hyperedge(
            anchors=[(g_w.graph_id, "cat")],
            members=[(g_l.graph_id, "c"), (g_l.graph_id, "a")],
            type_name="COMPOSED_OF",
            compositional=True,
            label="cat composition",
            properties={"weight": 0.5},
        )
        # Save graphs first (rehydration walks them).
        from mindsos_cli.commands.graph import _save_or_die as _g_save
        _g_save("word", g_w, schema_name=None, metagraph_name="rt")
        _g_save("letter", g_l, schema_name=None, metagraph_name="rt")
        # Serialize + persist metagraph.
        state = _metagraph_to_state(mg)
        # Phase 09 RR-12 — serialized state is at CURRENT_VERSION (4 in P09).
        assert state["_state_version"] == mg_migrations.CURRENT_VERSION
        assert len(state["intergraph_hyperedges"]) == 1
        ihe_dict = state["intergraph_hyperedges"][0]
        assert ihe_dict["edge_id"] == ihe.edge_id
        assert ihe_dict["type_name"] == "COMPOSED_OF"
        assert ihe_dict["compositional"] is True
        assert ihe_dict["label"] == "cat composition"
        assert ihe_dict["properties"] == {"weight": 0.5}
        # anchors / members serialize as [[gname, node_id], ...].
        assert ihe_dict["anchors"] == [["word", "cat"]]
        assert ihe_dict["members"] == [["letter", "c"], ["letter", "a"]]
        # Round-trip through save + load.
        state_mod.save_metagraph_state("rt", state)
        loaded = state_mod.load_metagraph_state("rt")
        assert loaded["_state_version"] == mg_migrations.CURRENT_VERSION
        mg2 = _state_to_metagraph(loaded)
        assert len(mg2.intergraph_hyperedges) == 1
        loaded_ihe = next(iter(mg2.intergraph_hyperedges.values()))
        assert loaded_ihe.edge_id == ihe.edge_id
        assert loaded_ihe.compositional is True
        assert loaded_ihe.type_name == "COMPOSED_OF"


class TestByteStableSort:
    def test_intergraph_hyperedges_sorted_by_edge_id(self, tmp_path, monkeypatch):
        from mindsos_core import Graph, Metagraph
        from mindsos_cli.commands.metagraph import _metagraph_to_state
        monkeypatch.setenv("MINDSOS_STATE_DIR", str(tmp_path))
        mg = Metagraph(name="rt")
        g_w = Graph(name="word", role="word")
        g_l = Graph(name="letter", role="letter")
        mg.add_graph(g_w)
        mg.add_graph(g_l)
        g_w.add_node("cat", type_name="Word", node_id="cat")
        g_l.add_node("c", type_name="Letter", node_id="c")
        g_l.add_node("a", type_name="Letter", node_id="a")
        # Add hyperedges in reverse-id order with explicit IDs.
        mg.add_intergraph_hyperedge(
            anchors=[(g_w.graph_id, "cat")],
            members=[(g_l.graph_id, "c"), (g_l.graph_id, "a")],
            type_name="X",
            intergraph_hyperedge_id="zzz",
        )
        mg.add_intergraph_hyperedge(
            anchors=[(g_w.graph_id, "cat")],
            members=[(g_l.graph_id, "c"), (g_l.graph_id, "a")],
            type_name="Y",
            intergraph_hyperedge_id="aaa",
        )
        state = _metagraph_to_state(mg)
        ids = [d["edge_id"] for d in state["intergraph_hyperedges"]]
        assert ids == sorted(ids)
        assert ids == ["aaa", "zzz"]


class TestReservedKeysExtension:
    """P14-A smaller-items fold — RESERVED_PROPERTY_KEYS extended with
    intergraph_hyperedges / intergraph_hyperedge_types / anchors / members."""

    @pytest.mark.parametrize(
        "key",
        [
            "intergraph_hyperedges",
            "intergraph_hyperedge_types",
            "anchors",
            "members",
        ],
    )
    def test_keys_are_reserved(self, key):
        from mindsos_core import RESERVED_PROPERTY_KEYS
        assert key in RESERVED_PROPERTY_KEYS

    def test_reserved_key_rejected_on_property_bag(self):
        from mindsos_core import (
            Graph, Metagraph, PropertyShapeError,
        )
        mg = Metagraph(name="m")
        g_w = Graph(name="word", role="word")
        g_l = Graph(name="letter", role="letter")
        mg.add_graph(g_w)
        mg.add_graph(g_l)
        g_w.add_node("cat", type_name="Word", node_id="cat")
        g_l.add_node("c", type_name="Letter", node_id="c")
        g_l.add_node("a", type_name="Letter", node_id="a")
        with pytest.raises(PropertyShapeError, match="reserved"):
            mg.add_intergraph_hyperedge(
                anchors=[(g_w.graph_id, "cat")],
                members=[(g_l.graph_id, "c"), (g_l.graph_id, "a")],
                type_name="T",
                properties={"anchors": "boom"},
            )
