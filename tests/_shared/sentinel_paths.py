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
    # Phase 07 B-07-T3 — requirements.in is now COPYed into the test
    # image so test_lockfile_falkordb_pin.py can verify the falkordb
    # pin syntax (P46 A).
    "requirements.in",
    # Phase 08 (L1 Reconstruction — R4-14 A eager-add at impl time).
    "mindsos_core/reconstruction/metagraph_loader.py",
    "mindsos_instances/reconstruction/__init__.py",
    "mindsos_instances/reconstruction/instance_loader.py",
    "tests/_shared/metagraph_equality.py",
    "tests/_shared/large_graph_factory.py",
    # Phase 09 (L1 XRef — RR-10 4-entry sentinel addition).
    "mindsos_core/models/xref.py",
    "mindsos_core/persistence/xref_repository.py",
    "mindsos_core/persistence/xref_migration.py",
    "mindsos_core/reconstruction/xref_loader.py",
    # Phase 10 (L1 Snapshot + soft-delete + RemovalImpact + XRef setters —
    # RPB-8 sentinel addition reduced to RUNTIME inputs only per B-10-T7).
    # The 4 doc pages (docs/concepts/soft-delete.md, docs/api/core/soft-delete.md,
    # docs/api/core/metagraph-snapshot.md, docs/dev/internals/snapshots.md) live
    # in this repo but are NOT static inputs the CLI reads at runtime — they
    # are mkdocs sources consumed at doc-build time only, and Dockerfile does
    # NOT COPY docs/ into either prod or test stages. Including them caused 4
    # spurious failures in the in-container image-completeness test. The two
    # remaining entries below ARE Python modules imported at CLI runtime.
    "mindsos_core/metagraph_snapshot.py",
    "mindsos_core/persistence/soft_delete.py",
    # Phase 11 — ADR-0134 §scanner + §amendment-2 loader policy. Both
    # are runtime Python modules; the docs surfaces
    # (docs/dev/internals/core.md §"Phase 11 ..." +
    # docs/dev/migration-playbook.md) are intentionally NOT sentinelled
    # per feedback_sentinel_paths_runtime_only.md.
    "mindsos_core/schema/migration.py",
    "mindsos_core/reconstruction/load_report.py",
    # Phase 12 — NEW top-level package `mindsos_knowledge/`. 3 runtime
    # Python modules consumed by `mindsos_cli/commands/knowledge.py`
    # at CLI runtime. Docs (`docs/api/knowledge/*`,
    # `docs/concepts/identifiers.md`, `docs/usage/knowledge/iri-cli.md`)
    # intentionally NOT sentinelled per
    # `feedback_sentinel_paths_runtime_only.md`.
    "mindsos_knowledge/__init__.py",
    "mindsos_knowledge/identifiers.py",
    "mindsos_knowledge/exceptions.py",
    "mindsos_cli/commands/knowledge.py",
    # Phase 13 — NEW sub-package `mindsos_knowledge/schemas/` ships
    # 9 schema builders + dispatch __init__. Subpackage of an
    # existing top-level (mindsos_knowledge) — no new Dockerfile
    # COPY directive needed; existing `COPY mindsos_knowledge`
    # picks up the new tree automatically. Docs
    # (`docs/usage/knowledge/{overview,ontology,lexicon,concepts,
    # alignment,promoted-pipelines,task-patterns,memories,
    # problem-trace,capacity-state}.md`) intentionally NOT
    # sentinelled per `feedback_sentinel_paths_runtime_only.md`.
    "mindsos_knowledge/schemas/__init__.py",
    "mindsos_knowledge/schemas/ontology.py",
    "mindsos_knowledge/schemas/lexicon.py",
    "mindsos_knowledge/schemas/concepts.py",
    "mindsos_knowledge/schemas/alignment.py",
    "mindsos_knowledge/schemas/promoted_pipelines.py",
    "mindsos_knowledge/schemas/task_patterns.py",
    "mindsos_knowledge/schemas/memories.py",
    "mindsos_knowledge/schemas/problem_trace.py",
    "mindsos_knowledge/schemas/capacity_state.py",
    # Phase 14 — KnowledgeLayer class + MetagraphView + bootstrap module.
    # 3 NEW Python modules in the existing `mindsos_knowledge/` package;
    # no new Dockerfile COPY directive needed (existing
    # `COPY mindsos_knowledge` picks up the new files). Per
    # `feedback_sentinel_paths_runtime_only.md`, the 1 NEW concept doc
    # (`docs/concepts/global-local.md`) is intentionally NOT sentinelled
    # — it's an mkdocs source, not a CLI runtime input.
    "mindsos_knowledge/knowledge_layer.py",
    "mindsos_knowledge/metagraph_view.py",
    "mindsos_knowledge/bootstrap.py",
    # Phase 15a — NEW top-level package `mindsos_admin/`. Per the
    # 7-site new-top-level-package checklist
    # (`feedback_new_top_level_package.md` +
    # `feedback_host_pip_refresh_on_new_package.md` 7th site), the
    # package + bootstrap helper + 3 importer modules sentinelled.
    # Synthetic fixtures (tests/phase_15a/fixtures/*) are NOT
    # sentinelled — they're tests-only inputs, not CLI runtime.
    # Doc pages (docs/knowledge-sources/*.md) are NOT sentinelled per
    # `feedback_sentinel_paths_runtime_only.md` (mkdocs source only).
    "mindsos_admin/__init__.py",
    "mindsos_admin/bootstrap.py",
    "mindsos_admin/importers/__init__.py",
    "mindsos_admin/importers/dolce.py",
    "mindsos_admin/importers/oewn.py",
    "mindsos_admin/importers/framenet.py",
    # Phase 16 — 3 NEW modules in the existing `mindsos_admin/` package
    # (read-only similarity surface per ADR-0144 §amendment-1 partial
    # §Heuristic Accept). No new top-level; existing
    # `COPY mindsos_admin` in Dockerfile picks up the new files. Per
    # `feedback_sentinel_paths_runtime_only.md`, the design log
    # (`confirmation_docs/PHASE_16_DESIGN_LOG.md`) is NOT sentinelled —
    # it's a confirmation artifact, not a CLI runtime input.
    "mindsos_admin/similarity.py",
    "mindsos_admin/_content_hash.py",
    "mindsos_admin/exceptions.py",
    # Phase 18 — NEW top-level package `mindsos_server/`. Per the 7-site
    # new-top-level-package checklist (`feedback_new_top_level_package.md`
    # + `feedback_host_pip_refresh_on_new_package.md`), all runtime Python
    # modules are sentinelled. Per `feedback_sentinel_paths_runtime_only.md`,
    # docs (`docs/usage/server/auth.md`) + design log
    # (`confirmation_docs/PHASE_18_DESIGN_LOG.md`) are NOT sentinelled
    # (mkdocs source / confirmation artifact, not CLI runtime inputs).
    # Underscore-prefixed modules are runtime-consumed but private to the
    # package; they ship in the wheel and the test image alongside the
    # public ones, so they sentinel here.
    "mindsos_server/__init__.py",
    "mindsos_server/capabilities.py",
    "mindsos_server/errors.py",
    "mindsos_server/session.py",
    "mindsos_server/users.py",
    "mindsos_server/audit.py",
    "mindsos_server/_argon2.py",
    "mindsos_server/_db.py",
    "mindsos_server/_schema.py",
    "mindsos_cli/commands/server.py",
)
