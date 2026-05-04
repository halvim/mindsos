---
last_confirmed_phase: 01
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
