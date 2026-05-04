# Phase 02 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

L1 Identity (UUID / IdStrategy / IdentityRegistry)

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

## tester_notes

Tester run on 2026-05-04 from Linux box. Final cumulative result:
**117 passed, 1 skipped** in-container (`docker compose run --rm
mindsos-test pytest tests/`). The 1 skip is `test_mkdocs_buildable.py`
— mkdocs is not in the test image (CI installs ad-hoc).

### Mid-run corrections committed onto phase-02

1. **Phase 01 test_confirm_phase.py was hardcoded to `--phase 01`.**
   With Phase 02 bumping `[mindsos] phase` to `02`, four tests in that
   file failed with "manifest mismatch" errors. Fixed by making the
   tests phase-agnostic — they now read `[mindsos] phase` from
   `manifest.toml` at run time. Bumped to one extra commit on
   phase-02 ("make Phase 01 confirm-phase tests phase-agnostic").

2. **Doc fix: legacy doubled `mindsos mindsos <subcommand>` form is
   broken in Phase 02, not preserved.** The Phase 02 row + conventions
   doc + this implementation log originally claimed the doubled form
   still worked. It doesn't — the compose entrypoint prepends
   `mindsos`, so the doubled invocation becomes `mindsos mindsos
   <subcommand>` to the binary, and Typer reads the second `mindsos`
   as a subcommand and fails with `No such command 'mindsos'`. Treat
   this as a deliberate breaking change vs Phase 01. Three docs
   corrected ("docs: legacy doubled mindsos form is a breaking change,
   not preserved").

### Process snags worth recording

3. **Tester checklist step 8 (`identity registry --register a` twice
   across two `compose run --rm` invocations) does NOT demonstrate
   duplicate rejection** — the `--rm` flag destroys the container
   filesystem on exit, so the JSON state file at
   `~/.mindsos/identity-registry-<scope>.json` vanishes between
   invocations. Reproduced the duplicate-rejection path within a
   single invocation instead: `identity registry --scope demo
   --register a --register a` exits 1 with `Duplicate id: 'a'` as
   expected. The state file persists across invocations on the host
   venv (no `--rm`), but not in the compose-run path.

4. **Tester walked steps from `main`, not `phase-02`, on first
   attempt.** Initial `pytest tests/` reported only 62 + 1 skipped (=
   the Phase 01 cumulative count). Root cause: Linux box never
   pulled / checked out `phase-02`. Implementation log §8 should make
   the `git checkout phase-02` step on Linux explicit (it's currently
   implicit in step 5 "Pull, build images"). Recommend the Phase 03
   chat fold this into PHASE_MAP §1's per-phase workflow row.

### Doc bugs to fix in next phase chat (non-blocking for Phase 02)

5. **Phase 02 row pass-criterion bullet "IRI-passthrough strategy
   rejects `--seed '{}'` (no `iri` key)" is wrong.** Empty content
   falls back to UUID4 by design (so KL importers can pass mixed
   content). Rejection only fires for `{"iri": ""}` (empty string) or
   `{"iri": 123}` (non-string `iri` value). Update the row to reflect
   actual behaviour.

### Manual exploration outcomes

- `doctor` (in-container): FalkorDB ping OK, all pins reported.
- `doctor --self-test` (in-container): exits 0.
- `doctor --self-test --static-only --json` (host venv): `"ok": true`.
- `identity strategies` lists uuid4 / uuid5 / iri with descriptions.
- `identity mint --strategy uuid4 --json`: returns a UUID4.
- `identity mint --strategy uuid5 --seed '{"v":"x"}' --json` × 2:
  bit-identical ids across two invocations (deterministic ✓).
- `identity mint --strategy iri --seed '{"iri":"oewn-2024:synset:01-n"}'
  --json`: returns the IRI verbatim.
- `identity registry --scope demo --register a --register b --list
  --json`: writes both ids to the state file, lists them; the
  registry primitive itself behaves as Phase 02 row specifies.

### Host venv

Python 3.12.3 on Linux box. `pip install -e .` clean. `which mindsos`
resolves to `~/halvim_mindsos/.venv/bin/mindsos`. `confirm-phase`
preflight (`doctor --self-test --static-only`) ran cleanly before
this doc was written.
