# Phase 00 — Confirmation

> Template for `confirmation_docs/PHASE_NN_CONFIRMED.md`. Fill in every field
> below, then commit. Phase 00 is hand-filled (no `confirm-phase` wrapper yet);
> Phase 01+ generate this file via `mindsos confirm-phase --phase NN --notes-file …`
> and the tester reviews + edits before commit.
>
> Schema field order is fixed per `confirmation_docs/PHASE_MAP.md` §1. Do not
> rename fields — CI's smoke check (Phase 01+) verifies "exists and non-empty",
> not field structure, but downstream tooling parses these field names.

---

## phase_number
*The integer phase number, zero-padded if needed (e.g., `00`, `12`, `38`).*

00

## phase_title
*The phase title as it appears in PHASE_MAP §3 / §4 / §5.*

Runtime infrastructure

## git_sha
*Full 40-char git SHA of the commit on the `phase-NN` branch that the tester
verified. Run `git rev-parse HEAD` on the branch.*

3c81aa12e21d26fd5ee4fcbe2d1d5095ca383790

## image_build_hash
*The `mindsos:phaseNN-prod` image's content hash, taken from
`docker inspect --format='{{.Id}}' mindsos:phase00-prod` (or the relevant tag
for the phase). Format: `sha256:<hex>`.*

sha256:a0db2ffc8df988979883dc85232d5c3845e8f65a933d5c2ae040fdf07811a19b

## falkordb_version
*The FalkorDB pin in effect for this phase, taken from
`mindsos_cli/manifest.toml [runtime.falkordb]`. Include both tag and digest.*

falkordb/falkordb:v4.18.3@sha256:30c530c193ac48cb6ea8c6cae745f793d2c098a0a138f7b3e46c1d90848845ba

## automated_test_summary
*Number of tests run, number passed, number skipped, number failed, plus the
suite hash. Suite hash = `sha256sum tests/phase_NN/**/*.py | sha256sum` (or
equivalent). Example:*

- count: 6
- passed: 6
- skipped: 0
- failed: 0
- suite_hash: e37812e23dbe657f2bcb44fe14cb27d089cb6b94c43de3656ede8669f3f84409  -

## tester_notes
*Free-form. What the tester observed. Anything surprising, any deviations from
the pass criterion in PHASE_MAP, any open questions for the next phase chat.
This is the load-bearing field — read by future phase chats per PHASE_MAP §0.*

1. Port 6379 conflict. Existing onto-tutor_falkordb_1 was binding host 6379. Resolved by docker compose down on the onto-tutor stack. Phase 01 chat may want to consider a non-default host port for FalkorDB to coexist with other Redis-based projects.
2. Test image missing requirements.txt. Initial Dockerfile only copied requirements-test.txt into the test stage, so doctor --self-test failed with "requirements.txt missing on disk" inside the test container. Fixed in commit 3c81aa1 by combining the COPY and adding chown -R mindsos:mindsos /app to both stages.
3. Entrypoint UX. Selected option (a) — docker compose run --rm mindsos doctor requires typing mindsos twice (docker compose run --rm mindsos mindsos doctor). docs/getting-started/install.md not yet updated to reflect this; tracked as a follow-up.
4. HTTPS push auth on Linux. Linux clone was via HTTPS; GitHub doesn't accept password auth for git. Switched remote to SSH. Future repos: clone via SSH from the start.

## timestamp_utc
*ISO 8601, UTC, second-precision. Example: `2026-05-03T14:32:01Z`.*

2026-05-03T22:30:01Z

## mkdocs_pages_updated
*Bulleted list of `docs/…` paths this phase touched (added, edited, or
amended). Phase 38 reviews these to find pages whose `last_confirmed_phase`
front-matter never advanced.*

- docs/index.md
- docs/getting-started/install.md
- docs/dev/repo-layout.md
