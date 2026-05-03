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

RUN pip install --no-cache-dir --no-deps .

CMD ["mindsos", "--help"]

# ----------------------------------------------------------------------------
# test — base + pytest + tests/. Used by `docker compose run mindsos-test`.
# ----------------------------------------------------------------------------
FROM base AS test

ARG MINDSOS_GIT_SHA=unknown
ARG MINDSOS_IMAGE_HASH=unknown
ENV MINDSOS_GIT_SHA=${MINDSOS_GIT_SHA} \
    MINDSOS_IMAGE_HASH=${MINDSOS_IMAGE_HASH}

COPY requirements-test.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements-test.txt

COPY pyproject.toml README.md ./
COPY mindsos_cli ./mindsos_cli
COPY tests ./tests

RUN pip install --no-cache-dir --no-deps .

CMD ["pytest", "tests/phase_00", "-v"]
