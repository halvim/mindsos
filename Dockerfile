# syntax=docker/dockerfile:1.7

# ============================================================================
# mindsos Dockerfile — multi-stage.
#
# Stages:
#   base — pinned Python image + system deps (gosu) + non-root mindsos user.
#   prod — base + locked runtime deps + mindsos_cli source. Slim. No test deps.
#   test — base + locked test-stage deps + mindsos_cli source + tests/.
#
# Pins:
#   Python: python@sha256:afc139a0a640942491ec481ad8dda10f2c5b753f5c969393b12480155fe15a63
#           (== python:3.12.3-slim-bookworm at lock time; see mindsos_cli/manifest.toml)
#
# When updating the Python digest: edit manifest.toml FIRST, then this file.
# `mindsos doctor --self-test` will catch any drift.
# ============================================================================

ARG PYTHON_DIGEST=sha256:afc139a0a640942491ec481ad8dda10f2c5b753f5c969393b12480155fe15a63

# ----------------------------------------------------------------------------
# base — pinned Python, gosu, non-root user, entrypoint, mount points.
# ----------------------------------------------------------------------------
FROM python@${PYTHON_DIGEST} AS base

RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 mindsos \
    && useradd -u 1000 -g 1000 -m -s /bin/bash mindsos

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MINDSOS_REPO_ROOT=/app

# Pre-create volume mount points; entrypoint re-chowns at runtime in case the
# bind mount overrides the build-time owner.
RUN mkdir -p /var/lib/mindsos /var/log/mindsos \
    && chown -R mindsos:mindsos /var/lib/mindsos /var/log/mindsos

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# ----------------------------------------------------------------------------
# prod — slim runtime image. No pytest, no dev tools.
# ----------------------------------------------------------------------------
FROM base AS prod

ARG MINDSOS_GIT_SHA=unknown
ARG MINDSOS_IMAGE_HASH=unknown
ENV MINDSOS_GIT_SHA=${MINDSOS_GIT_SHA} \
    MINDSOS_IMAGE_HASH=${MINDSOS_IMAGE_HASH}

COPY requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY pyproject.toml README.md ./
COPY mindsos_cli ./mindsos_cli
# Phase 02: slim mindsos_core (identity primitives only).
# Phase 03: + mindsos_core/cypher/, mindsos_core/models/.
# Phase 04: + mindsos_core/schema/.
# Phase 04-v2: HyperEdgeType added to mindsos_core/schema/types.py (no new files).
# Phase 05a: + mindsos_core/models/metagraph.py (slim port: Metagraph,
#            MetaEdge, MetaHyperEdge); RESERVED_PROPERTY_KEYS extended
#            in mindsos_core/schema/validation.py (P13).
# Phase 05b: + mindsos_core/models/intergraph_edge.py (IntergraphEdge,
#            ADR-0148 first draft); + mindsos_core/schema/metagraph_schema.py
#            (MetagraphSchema container); IntergraphEdgeType added to
#            mindsos_core/schema/types.py (no new file there);
#            CompositionalImmutableError re-shipped in
#            mindsos_core/exceptions.py; RESERVED_PROPERTY_KEYS extended
#            in mindsos_core/schema/validation.py with intergraph_edges,
#            schema_name, _compositional (Pushbacks 18-A + 6).
# Phase 05c: + mindsos_core/models/intergraph_hyperedge.py
#            (IntergraphHyperEdge, ADR-0148 amended for n-ary);
#            IntergraphHyperEdgeType added to
#            mindsos_core/schema/types.py (no new file there);
#            mindsos_core/schema/metagraph_schema.py extended with
#            intergraph_hyperedge vocabulary + validators;
#            mindsos_core/models/metagraph.py extended with
#            add_intergraph_hyperedge / remove_intergraph_hyperedge /
#            update_intergraph_hyperedge / iter_intergraph_hyperedges
#            factory methods; remove_graph cascade extended (P17-A);
#            attach_schema eager-pass extended to walk hyperedges
#            (P6-A); RESERVED_PROPERTY_KEYS extended with
#            intergraph_hyperedges / intergraph_hyperedge_types /
#            anchors / members.
# Phase 05d: MetaEdgeType + MetaHyperEdgeType added to
#            mindsos_core/schema/types.py (no new file); MetagraphSchema
#            extended with meta_edge_types + meta_hyperedge_types vocabs
#            + matching validators (round-7 P31 A drops the
#            locked-design fingerprint mechanism — only schema
#            state-file v=2→v=3 ships in 05d); attach_schema
#            eager-pass extended to walk metaedges + metahyperedges
#            with empty-vocab pass-silently rule (round-7 P39 A);
#            add_metaedge / add_metahyperedge factories run vocab
#            validation per round-7 P44 A (mirrors actual 05b
#            precedent). New `mindsos metagraph-schema add-meta-edge-type`
#            + `add-meta-hyperedge-type` + read-only `validate` verbs.
COPY mindsos_core ./mindsos_core
# Phase 06: new sibling package — `mindsos_instances/` ships 8 element-
# instance subclasses + ElementRegistry + materialise machinery +
# cascade-observer wiring (round-7 P49 B Core/instances boundary
# preserved). Round-7 P62 A package-integration checklist requires the
# COPY directive in both prod + test stages.
COPY mindsos_instances ./mindsos_instances
# Phase 01: doctor --self-test (workflow + compose drift checks) and
# confirm-phase --init-notes need these static inputs at runtime.
# Phase 03 / 04 / 04-v2 / 05a / 05b: tests/test_image_completeness.py
# (root-level cumulative) asserts the same set is present at /app — keep
# this list aligned with the SENTINEL_PATHS list in
# tests/_shared/sentinel_paths.py.
# Phase 05a additions (sentinel-tracked): mindsos_cli/commands/metagraph.py
# + mindsos_cli/migrations/{__init__,graph,schema,metagraph}.py.
# Phase 05b additions (sentinel-tracked): mindsos_core/models/intergraph_edge.py
# + mindsos_core/schema/metagraph_schema.py
# + mindsos_cli/commands/metagraph_schema.py
# + mindsos_cli/migrations/metagraph_schema.py.
# Phase 05c additions (sentinel-tracked):
# mindsos_core/models/intergraph_hyperedge.py.
# Phase 05d adds NO new sentinel-tracked files (additive: extends
# existing types.py + metagraph_schema.py + metagraph.py + CLI).
COPY .github ./.github
COPY docker-compose.yml ./
COPY confirmation_docs ./confirmation_docs

RUN pip install --no-cache-dir --no-deps .

RUN chown -R mindsos:mindsos /app
CMD ["mindsos", "--help"]

# ----------------------------------------------------------------------------
# test — base + pytest + tests/. Used by `docker compose run mindsos-test`.
# ----------------------------------------------------------------------------
FROM base AS test

ARG MINDSOS_GIT_SHA=unknown
ARG MINDSOS_IMAGE_HASH=unknown
ENV MINDSOS_GIT_SHA=${MINDSOS_GIT_SHA} \
    MINDSOS_IMAGE_HASH=${MINDSOS_IMAGE_HASH}

COPY requirements.txt requirements-test.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements-test.txt

COPY pyproject.toml README.md ./
COPY mindsos_cli ./mindsos_cli
COPY mindsos_core ./mindsos_core
COPY mindsos_instances ./mindsos_instances
COPY tests ./tests
# Phase 01: tests/phase_01/test_workflows_present.py and
# test_doctor_workflow_check.py read these from the host repo at /app/.
# tests/phase_01/test_init_notes.py invokes confirm-phase --init-notes which
# reads confirmation_docs/_template_notes.md.
# Phase 03 / 04 / 04-v2 / 05a / 05b: tests/test_image_completeness.py
# (root-level cumulative) asserts these sentinel files exist at /app/.
# Sentinel list lives at tests/_shared/sentinel_paths.py — append there
# when adding new static inputs (Phase 04 added 5 entries:
# mindsos_core/schema/{...}.py + mindsos_cli/commands/schema.py).
# Phase 04-v2 adds NO new entries.
# Phase 05a adds 5 entries: mindsos_cli/commands/metagraph.py +
# mindsos_core/models/metagraph.py +
# mindsos_cli/migrations/{__init__,graph,schema,metagraph}.py.
# Phase 05b adds 4 entries: mindsos_core/models/intergraph_edge.py +
# mindsos_core/schema/metagraph_schema.py +
# mindsos_cli/commands/metagraph_schema.py +
# mindsos_cli/migrations/metagraph_schema.py.
# Phase 05c adds 1 entry: mindsos_core/models/intergraph_hyperedge.py.
# Phase 05d adds NO new sentinel-tracked test inputs (additive).
COPY .github ./.github
COPY docker-compose.yml ./
COPY confirmation_docs ./confirmation_docs

RUN pip install --no-cache-dir --no-deps .

RUN chown -R mindsos:mindsos /app
CMD ["pytest", "tests/", "-v"]
