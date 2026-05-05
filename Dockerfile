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
COPY mindsos_core ./mindsos_core
# Phase 01: doctor --self-test (workflow + compose drift checks) and
# confirm-phase --init-notes need these static inputs at runtime.
# Phase 03 / 04 / 04-v2 / 05a: tests/test_image_completeness.py (root-level
# cumulative) asserts the same set is present at /app — keep this list
# aligned with the SENTINEL_PATHS list in tests/_shared/sentinel_paths.py.
# Phase 05a additions (sentinel-tracked): mindsos_cli/commands/metagraph.py
# + mindsos_cli/migrations/{__init__,graph,schema,metagraph}.py.
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
COPY tests ./tests
# Phase 01: tests/phase_01/test_workflows_present.py and
# test_doctor_workflow_check.py read these from the host repo at /app/.
# tests/phase_01/test_init_notes.py invokes confirm-phase --init-notes which
# reads confirmation_docs/_template_notes.md.
# Phase 03 / 04 / 04-v2 / 05a: tests/test_image_completeness.py (root-level
# cumulative) asserts these sentinel files exist at /app/. Sentinel list
# lives at tests/_shared/sentinel_paths.py — append there when adding new
# static inputs (Phase 04 added 5 entries: mindsos_core/schema/{...}.py +
# mindsos_cli/commands/schema.py). Phase 04-v2 adds NO new entries.
# Phase 05a adds 5 entries: mindsos_cli/commands/metagraph.py +
# mindsos_core/models/metagraph.py + mindsos_cli/migrations/{__init__,graph,schema,metagraph}.py.
COPY .github ./.github
COPY docker-compose.yml ./
COPY confirmation_docs ./confirmation_docs

RUN pip install --no-cache-dir --no-deps .

RUN chown -R mindsos:mindsos /app
CMD ["pytest", "tests/", "-v"]
