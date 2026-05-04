---
last_confirmed_phase: 02
---

# CLI conventions

Every `mindsos` subcommand (Phase 01 onward) follows these rules.

## Output streams

- **stdout** — structured success output (text or JSON; the human-friendly
  text goes to stdout too).
- **stderr** — error messages, warnings, deprecations. Never mix command
  output with diagnostics on the same stream.
- **JSON mode** — `--json` puts everything to stdout as a parsable object.
  This is the contract tests rely on.

## Exit codes

| Code | Meaning                                                          |
|------|------------------------------------------------------------------|
| `0`  | Command succeeded.                                               |
| `1`  | Command-level failure (e.g., `doctor --self-test` saw drift).    |
| `2`  | Usage error (bad arguments, missing required option).            |

## `--json` is universal

Every command exposes a `--json` flag that emits a JSON object on stdout:

```json
{
  "version": "0.0.0+phase01",
  "git_sha": "1457e46…",
  "image_hash": "sha256:a0db…"
}
```

Tests parse the JSON; humans read the text form. If a command's text and
JSON output diverge, the JSON is canonical.

## Required arguments are positional or kw-marked

Required values must be either positional or marked with a single `--name`
flag. Never accept a required value via env var alone — env vars are
optional overrides.

## Error messages are actionable

Errors include enough context to fix the problem. Bad:
`error: invalid argument`. Good: `error: --phase '02' mismatches manifest
[mindsos] phase = '01'. Bump the manifest first, or run from the correct branch.`

## Container invocation (Phase 02+)

`docker compose run --rm mindsos <subcommand>` works directly — the
compose `mindsos` service overrides the entrypoint to
`["/usr/local/bin/entrypoint.sh", "mindsos"]`, which still runs the gosu
privilege drop and bind-mount chown but then prefixes every invocation
with the `mindsos` binary.

The Phase 01 form `docker compose run --rm mindsos mindsos <subcommand>`
remains accepted (the prefix `mindsos` argument is passed through to the
binary as a no-op, since the binary recognises `mindsos` as its own
program name).

To get a shell inside the prod image (debug only — production code path
must never need this), override the entrypoint at the compose-run
boundary:

```sh
docker compose run --rm --entrypoint /bin/bash mindsos
```

The `mindsos-test` service keeps the bare entrypoint
(`/usr/local/bin/entrypoint.sh`) so that `docker compose run --rm
mindsos-test pytest tests/` works without a `mindsos` prefix.

## `--json` is universal: identity command examples

```json
$ docker compose run --rm mindsos identity strategies --json
{
  "strategies": [
    {"name": "uuid4", "class": "mindsos_core.UUID4Strategy", ...},
    {"name": "uuid5", "class": "mindsos_core.UUID5FromContentStrategy", ...},
    {"name": "iri",   "class": "mindsos_core.IRIPassthroughStrategy", ...}
  ]
}
```

