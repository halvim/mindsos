---
last_confirmed_phase: 01
---

# Release flow

Releases are tag-driven. Pushing a tag matching `phase-NN-confirmed` to
`origin` triggers `.github/workflows/release.yml`, which builds, tests,
exports a tarball, and creates a GitHub Release with the tarball + lockfile
snapshots + checksums.

## Trigger

```sh
# After Phase NN's PR is merged to main:
git fetch origin main
git checkout main
git tag phase-01-confirmed
git push origin phase-01-confirmed
```

The release workflow runs automatically.

## Release assets

Each `phase-NN-confirmed` Release ships:

| Asset                       | Notes                                                |
|-----------------------------|------------------------------------------------------|
| `mindsos-phaseNN.tar.gz`    | `docker save` of the prod image, gzipped.            |
| `Dockerfile`                | Snapshot of the Dockerfile at the tagged commit.     |
| `requirements.txt`          | Locked runtime deps with hashes.                     |
| `requirements-test.txt`     | Locked test-stage deps with hashes.                  |
| `checksums.txt`             | SHA256 of the four assets above.                     |

The release **body** is the verbatim content of
`confirmation_docs/PHASE_NN_CONFIRMED.md`.

## Tarball retention

Only the **5 most-recent** confirmed phases keep their tarball asset. Older
Releases are not deleted; their tarball asset is replaced with a 1-line
placeholder `mindsos-phaseNN.tar.gz` reading
`source-rebuild required — outside 5-phase retention window`.

To rebuild an evicted phase:

```sh
git checkout phase-NN-confirmed
docker compose build mindsos
```

## Confirmation flow (per-phase ritual)

```sh
# 1. On the phase-NN branch, after implementation + tests pass locally:
mindsos confirm-phase --init-notes phase-NN

# 2. Edit the resulting notes-phase-NN.md — fill in `phase_title` and
#    `tester_notes`. Save.

# 3. Generate the confirmation doc:
mindsos confirm-phase --phase NN --notes-file notes-phase-NN.md

# 4. Review confirmation_docs/PHASE_NN_CONFIRMED.md. Hand-edit if needed.

# 5. Commit, push, open PR, merge, tag, push tag.
```

## Fallback paths

- **`confirm-phase` produces a broken doc.** Hand-edit
  `confirmation_docs/PHASE_NN_CONFIRMED.md` directly. CI's structural check
  is "exists and non-empty" only — the doc remains tester-authoritative.
- **Compose stack down (can't run tests during confirmation).** Use
  `mindsos confirm-phase --phase NN --notes-file notes.md --skip-tests`.
  The doc records `tests skipped (--skip-tests)`; the tester still ran tests
  before invoking, just not via the wrapper.
- **Wrapper itself broken.** Copy `confirmation_docs/_template.md` to
  `confirmation_docs/PHASE_NN_CONFIRMED.md` and hand-fill every field.
  This is the Phase 00 path; it remains supported.

## Permissions

`release.yml` declares `permissions: contents: write` at the job level —
needed for `gh release create`/`upload`. `phase-ci.yml` runs at default
`contents: read`. No other scopes are requested.
