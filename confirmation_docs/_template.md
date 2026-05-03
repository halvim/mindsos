# Phase NN — Confirmation

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

NN

## phase_title
*The phase title as it appears in PHASE_MAP §3 / §4 / §5.*

…

## git_sha
*Full 40-char git SHA of the commit on the `phase-NN` branch that the tester
verified. Run `git rev-parse HEAD` on the branch.*

…

## image_build_hash
*The `mindsos:phaseNN-prod` image's content hash, taken from
`docker inspect --format='{{.Id}}' mindsos:phase00-prod` (or the relevant tag
for the phase). Format: `sha256:<hex>`.*

…

## falkordb_version
*The FalkorDB pin in effect for this phase, taken from
`mindsos_cli/manifest.toml [runtime.falkordb]`. Include both tag and digest.*

`falkordb/falkordb:vX.Y.Z@sha256:…`

## automated_test_summary
*Number of tests run, number passed, number skipped, number failed, plus the
suite hash. Suite hash = `sha256sum tests/phase_NN/**/*.py | sha256sum` (or
equivalent). Example:*

- count: 4
- passed: 4
- skipped: 0
- failed: 0
- suite_hash: `sha256:…`

## tester_notes
*Free-form. What the tester observed. Anything surprising, any deviations from
the pass criterion in PHASE_MAP, any open questions for the next phase chat.
This is the load-bearing field — read by future phase chats per PHASE_MAP §0.*

…

## timestamp_utc
*ISO 8601, UTC, second-precision. Example: `2026-05-03T14:32:01Z`.*

…

## mkdocs_pages_updated
*Bulleted list of `docs/…` paths this phase touched (added, edited, or
amended). Phase 38 reviews these to find pages whose `last_confirmed_phase`
front-matter never advanced.*

- docs/…
- docs/…
