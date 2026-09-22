---
last_confirmed_phase: 00
verified_at: f50f079
---

# Install

MindsOS ships as a Docker Compose stack: one slim `mindsos` CLI image plus a
pinned `falkordb` sidecar. That envelope shipped at Phase 00 and every layer
since runs inside the same stack.

## Prerequisites

- A Linux box with Docker and Compose v2 (`docker compose …`, not the legacy
  `docker-compose`).
- Git, plus a SSH key on GitHub (or a `repo`-scoped PAT for HTTPS).

## First-time setup

```sh
git clone git@github.com:halvim/mindsos.git
cd mindsos

# Generate locked Python deps (one-time per requirements.in change):
./tools/lock.sh
# Paste the printed sha256 into mindsos_cli/manifest.toml under
# [lockfile] requirements_txt_sha256, then commit the result.

# Bring the FalkorDB sidecar up:
docker compose up -d
```

## Smoke check

```sh
docker compose run --rm mindsos doctor
docker compose run --rm mindsos doctor --self-test
```

`doctor` prints the pinned FalkorDB / Python digests, the lockfile sha256,
the runtime Python version, and the FalkorDB ping result. `doctor --self-test`
exits non-zero on any drift between runtime state and `mindsos_cli/manifest.toml`.

## Run the test suite

```sh
docker compose run --rm mindsos-test pytest -q
```

In-container tests are the canonical gate; `tests/phase_00` alone checks the
envelope this page sets up.

## Note on volume ownership

The stack writes to `./.mindsos/falkordb-data/` (FalkorDB persistence) and
`./.mindsos/logs/` (CLI logs). Inside the container these are owned by the
non-root `mindsos` user (UID/GID 1000). On the host they may appear owned
by a numeric UID 1000 if your host user has a different UID. To reset state:

```sh
sudo rm -rf .mindsos/
```

(`sudo` only if your host UID isn't 1000.)
