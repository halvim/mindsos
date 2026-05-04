---
last_confirmed_phase: 01
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

1. `docker compose build mindsos-test` — pulls pinned images, installs
   locked deps.
2. `docker compose up -d falkordb` — waits up to 30s for the healthcheck.
3. `docker compose run --rm mindsos-test pytest tests/ -v` — cumulative
   suite.
4. `pip install --user 'mkdocs==1.6.1'` (pinned in `manifest.toml [ci]
   mkdocs_version`).
5. `mkdocs build --quiet` — verifies the docs tree.

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
locally on the host, `pip install mkdocs==1.6.1`.
