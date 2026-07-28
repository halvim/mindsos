# DREAM PRE-0 Slice 1b — Episode open/close lifecycle (CONFIRMED)

**Status:** BUILT — awaiting Linux gate. Branch `feat/dream-build` (accumulates Slice 1a + 1b).
Baseline to beat: Slice-1a gate **4348 passed / 0 failed**. Merge 1a+1b to `main` together and
RE-GATE the merged state (origin/main moved — HARD LESSON 1).

## What
Second Dream prerequisite step (`dream-episode-model.md` PRE-0 Slice 1b). The Episode becomes a
**streaming record**: opened `state=open` at Request START, flipped `suspended` on needs-input,
closed `state=closed` with the terminal content on any decision. A crash before the close leaves a
real partial Episode (`state=open`) that the startup scan recovers — subsuming the legacy
`InMemoryCheckpointStore`.

## Design decisions (agreed w/ HA this chat)
- **D1 — fields as node properties (not the opaque `value` blob).** Slice 1a's `update_and_validate`
  edits node **properties**; the old Episode stored everything in one opaque `value` dict it could not
  touch. So the Episode's fields are promoted to real L1 node properties. `state` is the sole
  **metadata** (mutable) field; the 8 **content** fields stay frozen except the retire-time
  lazy-inline. The node `value` is now the `episode_id` (a primitive).
- **D2 — open at Request START; mint a `request_id` when the caller supplies none.** The brain REPL
  passes no `request_id`, so minting is what gives every real request a durable Episode. The crash
  scan finds crashed Episodes by `state=open` (no id re-derivation needed). needs-input →
  `state=suspended` (resumes; the scan ignores it).
- **D3 — durable Local flush wired into the Orchestrator.** `open` / `suspend` / `close` each flush
  the user's Local to Falkor (whole-Local `save`; the cheap per-property targeted flush is a Slice-2
  follow-up). Best-effort — a failed flush never fails the solve.
- **D4 — failure vocab fixed.** A reached decision is a success; `failed` is reserved for a crash
  (`state=open`). New: `state ∈ {open, closed, suspended}`; `outcome_classification ∈ {succeeded,
  dont_know, conceded, failed}`. A reached abort is **conceded** (was the misleading
  `aborted→failed`). Runtime `RequestRun.status` and `RequestOutcome.status` renamed to match
  (`conceded`; the dont-know path no longer sets status `failed`).

## Changes
- **`mindsos_knowledge/schemas/episodic_memories.py`** — `EPISODE_METADATA_FIELDS = {state}`;
  `EPISODE_CONTENT_FIELDS` grows to 8 (adds `request_input_root_ref`, `capacity_root_ref`);
  `EPISODE_STATE_{OPEN,CLOSED,SUSPENDED}` + `EPISODE_STATES`.
- **`mindsos_knowledge/write_handle.py`** — `write_and_validate` gains an optional `properties=`
  kwarg (create a node with its property bag in one shot). Additive; `None` = byte-identical to before.
- **`mindsos_capacity/builtins/consolidate.py`** — `consolidate:mm` is now **dual-mode**: a legacy
  flat-`value`-blob record writes byte-identically (all pre-1b callers/tests unchanged); an
  `op`-tagged record (`open` / `suspend` / `close`) drives the streaming lifecycle with fields as
  properties. Non-primitive fields (`crash_marker` dict) are JSON-encoded (L1 props are
  primitives-only). Close is an **upsert** (update the open node, or create whole).
- **`mindsos_intelligence/consolidation.py`** — `open_episode` / `suspend_episode` helpers +
  `consolidate_request` (close) keyed on an explicit `episode_id`.
- **`mindsos_intelligence/orchestrator.py`** — mint `request_id`; open at start; suspend on
  needs-input; close on every terminal; `_OUTCOME_BY_STATUS` + statuses fixed (D4); `local_persister`
  wired; the legacy `_checkpoint` triggers removed (subsumed by the open Episode).
- **`mindsos_intelligence/crash_recovery.py`** — reworked to scan the Local for `state=open`
  Episodes and stamp each `closed` + `failed` + recovered `crash_marker` **in place** (preserving the
  partial content written at open — promotes ADR-0179 §3). `InMemoryCheckpointStore` /
  `CheckpointMarker` / `record_checkpoint` removed.
- **`mindsos_server/boot.py`** — passes `local_persister` to the Orchestrator (durable path) and runs
  the crash-recovery scan at boot.
- **`mindsos_intelligence/intelligence_layer.py`** — recovery call updated to the new signature; runs
  whenever a KL is wired.
- **`mindsos_intelligence/monitoring.py`** — the retention size histogram sizes over `properties`
  (streaming Episodes) or `value` (legacy), preserving the legacy metric.

## Durability note (bonus)
Node **properties** round-trip through Falkor (`graph_repository.persist` writes `props`;
`graph_loader._add_node_from_row` restores `properties=`). Because Slice 1b stores the Episode's
fields as **primitive** properties, Episodes are now fully durable and the crash scan finds
`state=open` after a real restart — this sidesteps the ADR-0182 structured-`value` gap that kept the
old dict-`value` Episode from persisting cleanly (the `phase_49/integration_c` PB-RT note).

## Tests
- `tests/phase_43/test_episodic_memories_completion.py` — content cardinality 6→8; `state` metadata;
  `EPISODE_STATES`.
- `tests/phase_48/test_episode_lifecycle_state.py` (NEW) — open/suspend/close state transitions;
  fields-as-properties; idempotent open; close upsert + Memory; close-without-open; `crash_marker`
  JSON-encoding.
- `tests/phase_48/test_crash_recovery.py` (REWRITTEN) — scan closes `state=open` as `failed`
  (partial content preserved); ignores closed/suspended; idempotent; no-op without the capacity;
  lifecycle-success leaves a closed Episode.
- `tests/phase_48/test_consolidation_seam.py` — reads Episode **properties** (state=closed,
  outcome, mm_root_ref).
- `tests/phase_47/test_six_phase_lifecycle.py` — abort verdict → `conceded`.
- Unchanged & relied upon (dual-mode legacy path): `test_consolidation_memory`,
  `test_retention_monitoring`, phase_33/34/36 consolidate-capacity suites,
  `resident_brain/test_durable_roundtrip` (Episode survives the Falkor round-trip).

## Gate ritual (per gate-hygiene)
`git fetch origin && git checkout feat/dream-build && git reset --hard origin/feat/dream-build &&
git rev-parse --short HEAD` (CONFIRM sha) →
`docker compose -p mindsos-core --profile test run --rm --build mindsos-test pytest -q`.
Pass-count == 4348 (baseline) ⇒ stale checkout (Slice 1a-only) — investigate before trusting green.

## Owed after green
Tag on merge to `main` (`dream-pre0-slice1b-confirmed`); STATE.json recent[] entry; refresh the
`dream-episode-model` memory (Slice 1b SHIPPED; open sub-question resolved = D1 restructure). Then
Slice 2 (stream per-run content) + Slice 3 (partial recovery + open-tolerant reader).
