# Phase 03 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

L1 Graph elements (Graph / Node / Edge / HyperEdge + Cypher rel-type validation)

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

Tester run on 2026-05-04 from Linux box. Final cumulative result:
**189 passed, 1 skipped** in-container (`docker compose run --rm
mindsos-test pytest tests/`). The 1 skip is `test_mkdocs_buildable.py`
— mkdocs is not in the test image (CI installs ad-hoc).

### Manual exploration outcomes

- `mindsos graph create --name demo --role ontology` → state file
  written to `~/.mindsos/graph-demo.json`; `_state_version: 1`
  + sorted node/edge/hyperedge lists confirmed by `cat`.
- 3-node × 2-edge × 1-hyperedge build via `add-node` / `add-edge` /
  `add-hyperedge`; `inspect --json` reports the right counts.
- `--prop k=v` JSON parsing: int (`age=42`), list
  (`tags='["staff","remote"]'`), bool (`active=true`), string fallback
  (`nick=Carrie`) — all round-trip correctly.
- HyperEdge `member_ids` canonicalised to sorted list regardless of
  insertion order (verified by reordering `--member` flags and diffing
  state file).
- ADR-0021 rejections: `--type works_at` (lowercase) and
  `--type Works_At` (mixed-case) both exit 1 with structured
  `CypherError` message.
- IdentityError on duplicate `--node-id` exits 1 with structured
  message.
- SchemaError on `add-hyperedge` with no `--member` flags exits 1.
- Path-traversal protection: `--name "foo/bar"` exits 2 with regex
  diagnostic.
- `_state_version: 99` (hand-injected) → load refuses with "this CLI
  supports v1" exit 1 — strict-version contract works.
- `mindsos graph list` enumerates state files sorted by name.
- `reset --name X` + `reset --all` + `reset` (no flag, exit 2) +
  `reset --name <missing>` (exit 1) all behave per spec.
- Phase 02 carry-over (`mindsos identity strategies / mint / registry`,
  `doctor --self-test`) still functional.

### Process snags worth recording

1. **Docker shell-debug needs `--entrypoint` override.** Phase 02's
   entrypoint rework prepends `mindsos` to whatever follows
   `compose run --rm mindsos`, so `docker compose run --rm mindsos sh
   -c '...'` fails with `No such command 'sh'`. Correct form for
   shell access:
   `docker compose run --rm --entrypoint /bin/sh mindsos -c '...'`.
   Already documented in `docs/dev/conventions.md` (Phase 02);
   tester first hit confirms the doc is load-bearing.

### Phase 04 chat — open question surfaced during sign-off

2. **No CLI path to update a single node property in Phase 03.**
   `update_node_properties` is deferred to Phase 04 per the row's
   slim-port deferral list. Phase 03 workarounds: `reset --name X`
   + rebuild, or hand-edit the state file (JSON schema is documented).
   Phase 04 chat should ship a proper `mindsos graph set-prop` (or
   equivalent) — flagged so it's not rediscovered as a gap.

### Phase 05 chat — load-bearing reminder (already filed)

3. **Q13 — intergraph edge primitive** is filed in PHASE_MAP §7 Q13
   with full analysis at `confirmation_docs/INTERGRAPH_EDGE_DESIGN_NOTE.md`.
   The Phase 05 row has been amended to require adjudication before
   implementing Metagraph elements. Default = defer indefinitely.
   Six pushbacks recorded; four concrete asks if greenlit.

### Host venv

Python 3.12.3 on Linux box. `pip install -e .` clean (no requirement
delta vs Phase 02 — all stdlib). `which mindsos` resolves to
`~/halvim_mindsos/.venv/bin/mindsos`. `confirm-phase` preflight
(`doctor --self-test --static-only`) ran cleanly before this doc was
written.
