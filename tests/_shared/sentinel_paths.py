"""Cumulative sentinel-paths list driving the image-completeness test.

The test at ``tests/test_image_completeness.py`` parametrises over this
list. Each phase that adds a new static input the CLI reads at runtime
appends to the list here AND adds a Dockerfile ``COPY`` line in both prod
and test stages.

History: Phase 01 §10.1 surfaced a Dockerfile drift where ``.github/``,
``docker-compose.yml``, and ``confirmation_docs/`` were not COPYed into
the prod / test image. The result: 10 in-container test failures
including a Phase 00 regression. Phase 02 introduced this guard at
``tests/phase_02/test_image_completeness.py``; Phase 03 promotes it to
the root-level test (no longer phase-scoped) with this shared list.
"""

from __future__ import annotations

#: Sentinel files that MUST be reachable from MINDSOS_REPO_ROOT.
#: Cumulative — each phase appends.
SENTINEL_PATHS: tuple[str, ...] = (
    # Phase 00
    "pyproject.toml",
    "docker-compose.yml",
    "mindsos_cli/manifest.toml",
    "mindsos_cli/app.py",
    "mindsos_cli/commands/doctor.py",
    # Phase 01
    "mindsos_cli/commands/confirm_phase.py",
    ".github/workflows/phase-ci.yml",
    ".github/workflows/release.yml",
    "confirmation_docs/_template_notes.md",
    "confirmation_docs/PHASE_MAP.md",
    # Phase 02
    "mindsos_cli/commands/identity.py",
    "mindsos_core/__init__.py",
    "mindsos_core/exceptions.py",
    "mindsos_core/models/__init__.py",
    "mindsos_core/models/identity.py",
    # Phase 03
    "mindsos_cli/commands/graph.py",
    "mindsos_cli/state.py",
    "mindsos_core/models/node.py",
    "mindsos_core/models/edge.py",
    "mindsos_core/models/graph.py",
    "mindsos_core/cypher/__init__.py",
    "mindsos_core/cypher/identifiers.py",
    # Phase 04
    "mindsos_cli/commands/schema.py",
    "mindsos_core/schema/__init__.py",
    "mindsos_core/schema/types.py",
    "mindsos_core/schema/schema.py",
    "mindsos_core/schema/validation.py",
    # Phase 05a (P14 + slim metagraph port)
    "mindsos_cli/commands/metagraph.py",
    "mindsos_core/models/metagraph.py",
    "mindsos_cli/migrations/__init__.py",
    "mindsos_cli/migrations/graph.py",
    "mindsos_cli/migrations/schema.py",
    "mindsos_cli/migrations/metagraph.py",
    # Phase 05b (IntergraphEdge + IntergraphEdgeType + MetagraphSchema +
    # new metagraph-schema subapp + metagraph-schema state-file kind)
    "mindsos_core/models/intergraph_edge.py",
    "mindsos_core/schema/metagraph_schema.py",
    "mindsos_cli/commands/metagraph_schema.py",
    "mindsos_cli/migrations/metagraph_schema.py",
    # Phase 05c (IntergraphHyperEdge n-ary primitive + IntergraphHyperEdgeType
    # vocab + replace-only update verb; metagraph state-file v=2→v=3 +
    # metagraph-schema state-file v=1→v=2)
    "mindsos_core/models/intergraph_hyperedge.py",
    # Phase 06 (mindsos_instances sibling package + Core observer plumbing
    # + new instances CLI subapp). Round-7 P62 A package-integration
    # checklist enforces these new sentinel paths.
    "mindsos_core/_observers.py",
    "mindsos_instances/__init__.py",
    "mindsos_instances/exceptions.py",
    "mindsos_instances/_resolve.py",
    "mindsos_instances/materialise.py",
    "mindsos_instances/registry.py",
    "mindsos_instances/utils/__init__.py",
    "mindsos_instances/utils/canonicalize.py",
    "mindsos_instances/models/__init__.py",
    "mindsos_instances/models/_overrides.py",
    "mindsos_instances/models/element_instance.py",
    "mindsos_cli/commands/instances.py",
    # Phase 07 (L1 Persistence — P25 A + P36 A eager-add at impl time).
    "mindsos_core/config.py",
    "mindsos_core/persistence/__init__.py",
    "mindsos_core/persistence/client.py",
    "mindsos_core/persistence/async_client.py",
    "mindsos_core/persistence/bootstrap.py",
    "mindsos_core/persistence/graph_repository.py",
    "mindsos_core/persistence/metagraph_repository.py",
    "mindsos_core/persistence/wal.py",
    "mindsos_core/persistence/integrity.py",
    "mindsos_core/reconstruction/__init__.py",
    "mindsos_core/reconstruction/graph_loader.py",
    "mindsos_core/cypher/builders.py",
    "mindsos_instances/persistence/__init__.py",
    "mindsos_instances/persistence/instance_repository.py",
    "mindsos_cli/commands/persistence.py",
    "tests/conftest.py",
    "tests/_shared/falkordb_fixture.py",
    "tests/_shared/graph_equality.py",
    "tests/_shared/raises_on_nth_call.py",
)
