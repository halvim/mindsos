---
last_confirmed_phase: 01
verified_at: 5172b3c
---

# Testing

## In-container is canonical

```sh
docker compose run --rm mindsos-test pytest tests/ -v
```

This is the **canonical** pass criterion for every phase. CI runs the same
command. Host-side runs (`pytest tests/` on your laptop) are allowed for
dev iteration — but a phase is not "green" until it passes in-container.

## Test layout

```
tests/
├── phase_00/    # Runtime infrastructure (Phase 00).
├── phase_01/    # Tooling infrastructure (Phase 01).
└── phase_NN/    # one directory per phase.
```

Pre-existing tests **must continue to pass** on every phase (PHASE_MAP §1
"Test layout"). Phase-NN tests under `tests/phase_NN/` are additive.

## Cumulative pytest

Both `phase-ci.yml` and the release workflow run `pytest tests/`
cumulatively — every shipped phase's tests run on every push.

## What `phase-ci.yml` runs

1. `docker compose --profile test build mindsos-test` — pulls pinned
   images, installs locked deps.
2. `docker compose up -d --wait falkordb` — `--wait` blocks until the
   healthcheck passes (`redis-cli ping`, 5s interval, 10 retries after a
   10s start period).
3. `docker compose run --rm mindsos-test pytest tests/ -v` — cumulative
   suite.
4. `python3 -m pip install --user mkdocs==<pin>` — the workflow reads the
   pin from `mindsos_cli/manifest.toml` `[ci] mkdocs_version`; it is not
   hardcoded in the workflow.
5. `python3 -m mkdocs build --quiet` — verifies the docs tree.

## What the release workflow adds

After the same test run, the release workflow:

- `docker save | gzip` the prod image to `mindsos-phaseNN.tar.gz`.
- Snapshots `Dockerfile`, `requirements.txt`, `requirements-test.txt`.
- Computes SHA256s, creates the GitHub Release, attaches all assets.
- Runs the retention prune (replaces tarball assets older than the 5-phase
  window with a placeholder file — never deletes a Release).

## Why mkdocs isn't in the test image

To keep the `mindsos:phaseNN-test` image lean. mkdocs has a sizable
dependency tree (Markdown, Jinja2, watchdog, ghp-import, ...) and is only
needed for the docs build step in CI. It's installed ad-hoc in the
workflow. If you want to run `tests/phase_01/test_mkdocs_buildable.py`
locally on the host, install the version pinned at
`mindsos_cli/manifest.toml` `[ci] mkdocs_version`.
