"""Phase 05d — metagraph-schema state-file v=2 → v=3 migration tests.

Locks the migration step per round-7 P31 A row §F: ``_v2_to_v3``
adds ``meta_edge_types: []`` + ``meta_hyperedge_types: []`` defaults
on append; defensive null→[] normalization. Metagraph state file
stays at v=3 (no fingerprint mechanism per P31 A).
"""

from __future__ import annotations

import pytest

from mindsos_cli import state as state_mod
from mindsos_cli.migrations import metagraph as mg_migrations
from mindsos_cli.migrations import metagraph_schema as ms_migrations


class TestVersionConstants:
    def test_metagraph_state_version_at_current(self):
        """Phase 09 RR-12 — metagraph state file bumps from v=3 → v=4.

        Originally Phase 05d this asserted ``== 3`` (no bump in 05d
        per P31 A). Phase 09 bumps to 4 adding ``xrefs[]`` per M10 +
        RR-7. Dynamic check future-proofs subsequent bumps.
        """
        assert (
            state_mod.METAGRAPH_STATE_VERSION
            == mg_migrations.CURRENT_VERSION
        )

    def test_metagraph_schema_state_version_at_3(self):
        """Phase 09 — schema state file unchanged at v=3 (no schema bump in 09)."""
        assert state_mod.METAGRAPH_SCHEMA_STATE_VERSION == 3
        assert ms_migrations.CURRENT_VERSION == 3


class TestSchemaMigrationV2ToV3:
    def test_v2_to_v3_adds_default_arrays(self):
        v2 = {
            "_state_version": 2,
            "name": "ms",
            "strict": False,
            "intergraph_edge_types": [],
            "intergraph_hyperedge_types": [],
        }
        result = ms_migrations.migrate(v2)
        assert result["_state_version"] == 3
        assert result["meta_edge_types"] == []
        assert result["meta_hyperedge_types"] == []

    def test_v2_chain_preserves_pre_existing_vocab(self):
        v2 = {
            "_state_version": 2,
            "name": "ms",
            "strict": True,
            "intergraph_edge_types": [{"name": "EVOKES"}],
            "intergraph_hyperedge_types": [{"name": "COMPOSED_OF"}],
        }
        result = ms_migrations.migrate(v2)
        assert result["intergraph_edge_types"] == [{"name": "EVOKES"}]
        assert result["intergraph_hyperedge_types"] == [{"name": "COMPOSED_OF"}]
        assert result["strict"] is True
        assert result["meta_edge_types"] == []
        assert result["meta_hyperedge_types"] == []

    def test_v1_chain_through_to_v3(self):
        """Phase 05b v=1 schema state file → 05d v=3."""
        v1 = {
            "_state_version": 1,
            "name": "ms",
            "strict": False,
            "intergraph_edge_types": [],
        }
        result = ms_migrations.migrate(v1)
        assert result["_state_version"] == 3
        # All three additive fields populated as defaults.
        assert result["intergraph_hyperedge_types"] == []
        assert result["meta_edge_types"] == []
        assert result["meta_hyperedge_types"] == []

    def test_v3_idempotent(self):
        v3 = {
            "_state_version": 3,
            "name": "ms",
            "strict": False,
            "intergraph_edge_types": [],
            "intergraph_hyperedge_types": [],
            "meta_edge_types": [{"name": "X"}],
            "meta_hyperedge_types": [{"name": "Y"}],
        }
        result = ms_migrations.migrate(v3)
        assert result["_state_version"] == 3
        assert result["meta_edge_types"] == [{"name": "X"}]
        assert result["meta_hyperedge_types"] == [{"name": "Y"}]

    def test_v4_forward_refused(self):
        """Forward versions rejected with structured error."""
        forward = ms_migrations.CURRENT_VERSION + 1
        with pytest.raises(ValueError) as exc:
            ms_migrations.migrate({"_state_version": forward, "name": "test"})
        assert f"v{ms_migrations.CURRENT_VERSION}" in str(exc.value)

    def test_defensive_null_to_empty_list_meta_edge_types(self):
        """P31 A row §F: defensive null→[] normalization for malformed
        v=2 state files (e.g., explicit ``"meta_edge_types": null``).
        """
        v2_malformed = {
            "_state_version": 2,
            "name": "ms",
            "strict": False,
            "intergraph_edge_types": [],
            "intergraph_hyperedge_types": [],
            "meta_edge_types": None,  # malformed; treated as missing.
            "meta_hyperedge_types": None,
        }
        result = ms_migrations.migrate(v2_malformed)
        assert result["meta_edge_types"] == []
        assert result["meta_hyperedge_types"] == []
