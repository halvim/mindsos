"""Metagraph state-file v=2 round-trip + migration tests.

Pushback 18-A (Phase 05b) — adds intergraph_edges + schema_name; v=1→v=2
cumulative one-way migration via mindsos_cli/migrations/metagraph.py.

Phase 05c P26 audit: this file's constants and forward-version-refusal
fixtures are now dynamic (``state_mod.METAGRAPH_STATE_VERSION`` /
``mg_migrations.CURRENT_VERSION + 1``) so 05c's bump 2→3 doesn't
invalidate the assertions. Test names retain "_v1_to_v2" / "_v2"
shape since they verify the 05b-introduced migration step specifically;
the 05c row's separate ``test_metagraph_migration_v2_to_v3.py`` covers
the new step.
"""

from __future__ import annotations

import json

import pytest

from mindsos_cli import state as state_mod
from mindsos_cli.migrations import metagraph as mg_migrations
from mindsos_cli.migrations import metagraph_schema as ms_migrations


class TestStateVersionConstants:
    def test_metagraph_state_version_at_current(self):
        # P26 audit — dynamic check; 05b shipped at 2, 05c bumps to 3.
        assert state_mod.METAGRAPH_STATE_VERSION == mg_migrations.CURRENT_VERSION

    def test_metagraph_schema_state_version_at_current(self):
        # P26 audit — dynamic check; 05b shipped at 1, 05c bumps to 2.
        assert (
            state_mod.METAGRAPH_SCHEMA_STATE_VERSION
            == ms_migrations.CURRENT_VERSION
        )

    def test_graph_state_version_at_current(self):
        """Phase 10 B-10-T3 — dynamic check; Phase 05b/05c left graph
        state files at v=4, Phase 10 bumps to v=5 for soft-delete fields
        (audit-class feedback_phase_baseline_literal_audit.md).
        """
        from mindsos_cli.migrations import graph as graph_migrations
        assert state_mod.GRAPH_STATE_VERSION == graph_migrations.CURRENT_VERSION

    def test_schema_state_version_unchanged_at_2(self):
        # Phase 04-v2 schema state files unaffected by 05b/05c.
        assert state_mod.SCHEMA_STATE_VERSION == 2


class TestMigrationV1ToV2:
    def test_v1_to_v2_populates_defaults(self):
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
        # P26 — chain may flow v=1 → v=2 → v=3 under 05c. Dynamic CURRENT_VERSION.
        assert result["_state_version"] == mg_migrations.CURRENT_VERSION
        # The v=1→v=2 step's payload defaults (ie + schema_name) survive
        # any subsequent migration steps.
        assert result["intergraph_edges"] == []
        assert result["schema_name"] is None

    def test_v1_to_v2_preserves_existing_fields(self):
        """Phase 10 B-10-T3 — chain runs v=1 → CURRENT (=5 in P10) which adds
        soft-delete fields per element. Assertion narrowed to fields that
        existed in v=1 (audit-class feedback_phase_baseline_literal_audit.md).
        """
        v1 = {
            "_state_version": 1,
            "metagraph_id": "mg-id",
            "name": "test",
            "properties": {"k": "v"},
            "contained_graphs": ["g1"],
            "metaedges": [{"edge_id": "e1"}],
            "metahyperedges": [{"edge_id": "h1"}],
        }
        result = mg_migrations.migrate(v1)
        assert result["properties"] == {"k": "v"}
        assert result["contained_graphs"] == ["g1"]
        # Check edge_id survived; subsequent migrations (P10 v=5) add
        # deprecated_at + disputed_at as default-None fields.
        assert result["metaedges"][0]["edge_id"] == "e1"
        assert result["metahyperedges"][0]["edge_id"] == "h1"

    def test_v2_advances_to_current(self):
        """A v=2 input migrates forward to CURRENT_VERSION (idempotent at v=2 in 05b; advances to v=3 under 05c)."""
        v2 = {
            "_state_version": 2,
            "metagraph_id": "mg-id",
            "name": "test",
            "properties": {},
            "schema_name": "ms1",
            "contained_graphs": [],
            "metaedges": [],
            "metahyperedges": [],
            "intergraph_edges": [{"edge_id": "ie1"}],
        }
        result = mg_migrations.migrate(v2)
        # P26 — under 05b this asserted == 2 (idempotent). Under 05c the
        # chain advances to v=3. Dynamic CURRENT_VERSION future-proofs.
        assert result["_state_version"] == mg_migrations.CURRENT_VERSION
        assert result["intergraph_edges"] == [{"edge_id": "ie1"}]
        assert result["schema_name"] == "ms1"

    def test_forward_version_refused(self):
        # P26 — fixture uses CURRENT_VERSION + 1 dynamically (was hard-coded v=3).
        forward = mg_migrations.CURRENT_VERSION + 1
        with pytest.raises(ValueError) as exc:
            mg_migrations.migrate({"_state_version": forward, "name": "test"})
        # Error message mentions current supported version dynamically.
        assert f"v{mg_migrations.CURRENT_VERSION}" in str(exc.value)

    def test_missing_state_version_refused(self):
        with pytest.raises(ValueError, match="missing required field"):
            mg_migrations.migrate({"name": "test"})

    def test_non_int_state_version_refused(self):
        with pytest.raises(ValueError):
            mg_migrations.migrate({"_state_version": "1", "name": "test"})


class TestMetagraphSchemaStateV1:
    def test_initial_version_at_current(self):
        # P26 — dynamic check.
        assert (
            state_mod.METAGRAPH_SCHEMA_STATE_VERSION
            == ms_migrations.CURRENT_VERSION
        )

    def test_v1_advances_to_current_migration(self):
        v1 = {
            "_state_version": 1,
            "name": "test",
            "strict": False,
            "intergraph_edge_types": [],
        }
        result = ms_migrations.migrate(v1)
        # P26 — under 05b this was idempotent at v=1; under 05c the
        # chain advances to v=2. Dynamic CURRENT_VERSION future-proofs.
        assert result["_state_version"] == ms_migrations.CURRENT_VERSION

    def test_forward_version_refused(self):
        # P26 — fixture uses CURRENT_VERSION + 1 dynamically.
        forward = ms_migrations.CURRENT_VERSION + 1
        with pytest.raises(ValueError):
            ms_migrations.migrate({"_state_version": forward, "name": "test"})


class TestStateRoundTrip:
    def test_metagraph_v2_round_trip(self, _isolated_state_dir):
        from mindsos_core import Graph, Metagraph
        from mindsos_cli.commands.metagraph import (
            _metagraph_to_state, _state_to_metagraph,
        )

        mg = Metagraph(name="rt")
        g_lex = Graph(name="lex", role="lexicon")
        g_cpt = Graph(name="cpt", role="concepts")
        mg.add_graph(g_lex)
        mg.add_graph(g_cpt)
        n_lex = g_lex.add_node("v1", type_name="Word")
        n_cpt = g_cpt.add_node("v2", type_name="Concept")
        ie = mg.add_intergraph_edge(
            g_lex.graph_id, n_lex.node_id,
            g_cpt.graph_id, n_cpt.node_id, "EVOKES",
            compositional=True, label="x", properties={"weight": 0.5},
        )

        # Serialize.
        state = _metagraph_to_state(mg)
        # P26 — writers emit CURRENT_VERSION (was hard-coded 2; 05c writes 3).
        assert state["_state_version"] == state_mod.METAGRAPH_STATE_VERSION
        assert len(state["intergraph_edges"]) == 1
        ie_dict = state["intergraph_edges"][0]
        assert ie_dict["edge_id"] == ie.edge_id
        assert ie_dict["source_graph"] == "lex"
        assert ie_dict["source_node"] == n_lex.node_id
        assert ie_dict["target_graph"] == "cpt"
        assert ie_dict["target_node"] == n_cpt.node_id
        assert ie_dict["type_name"] == "EVOKES"
        assert ie_dict["compositional"] is True
        assert ie_dict["label"] == "x"
        assert ie_dict["properties"] == {"weight": 0.5}
        assert state["schema_name"] is None

    def test_byte_stable_sort_intergraph_edges(self, _isolated_state_dir):
        from mindsos_core import Graph, Metagraph
        from mindsos_cli.commands.metagraph import _metagraph_to_state

        mg = Metagraph(name="rt")
        g1 = Graph(name="g1", role="r1")
        g2 = Graph(name="g2", role="r2")
        mg.add_graph(g1)
        mg.add_graph(g2)
        n1 = g1.add_node("v1", type_name="N")
        n2 = g2.add_node("v2", type_name="N")
        # Add edges in reverse-id order.
        ie_b = mg.add_intergraph_edge(
            g1.graph_id, n1.node_id, g2.graph_id, n2.node_id, "X",
            edge_id="bbb",
        )
        ie_a = mg.add_intergraph_edge(
            g1.graph_id, n1.node_id, g2.graph_id, n2.node_id, "Y",
            edge_id="aaa",
        )
        state = _metagraph_to_state(mg)
        edge_ids_in_state = [e["edge_id"] for e in state["intergraph_edges"]]
        assert edge_ids_in_state == sorted(edge_ids_in_state)
        assert edge_ids_in_state == ["aaa", "bbb"]


class TestPersistenceCLI:
    def test_save_and_load_round_trip(self, _isolated_state_dir):
        from mindsos_core import Graph, Metagraph
        from mindsos_cli.commands.metagraph import (
            _metagraph_to_state, _state_to_metagraph,
        )

        mg = Metagraph(name="persist")
        g_lex = Graph(name="lex", role="lexicon")
        g_cpt = Graph(name="cpt", role="concepts")
        mg.add_graph(g_lex)
        mg.add_graph(g_cpt)
        n_lex = g_lex.add_node("v1", type_name="W")
        n_cpt = g_cpt.add_node("v2", type_name="C")
        # Save the contained graphs first (rehydration walks them).
        from mindsos_cli.commands.graph import _graph_to_state, _save_or_die
        _save_or_die("lex", g_lex, schema_name=None, metagraph_name="persist")
        _save_or_die("cpt", g_cpt, schema_name=None, metagraph_name="persist")
        ie = mg.add_intergraph_edge(
            g_lex.graph_id, n_lex.node_id,
            g_cpt.graph_id, n_cpt.node_id, "EVOKES",
        )
        # Save metagraph.
        state_mod.save_metagraph_state("persist", _metagraph_to_state(mg))
        # Reload.
        loaded_state = state_mod.load_metagraph_state("persist")
        # P26 — dynamic CURRENT_VERSION (loader migrates forward).
        assert (
            loaded_state["_state_version"]
            == state_mod.METAGRAPH_STATE_VERSION
        )
        assert len(loaded_state["intergraph_edges"]) == 1
        # Rehydrate.
        mg2 = _state_to_metagraph(loaded_state)
        assert len(mg2.intergraph_edges) == 1
        loaded_ie = next(iter(mg2.intergraph_edges.values()))
        assert loaded_ie.edge_id == ie.edge_id
        assert loaded_ie.type_name == "EVOKES"
