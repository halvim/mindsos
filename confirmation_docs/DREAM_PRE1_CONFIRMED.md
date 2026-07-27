# DREAM PRE-1 — Request-input persistence (CONFIRMED)

**Status:** SHIPPED (gate-green). Linux gate **4343 passed / 12 skipped / 1 xpassed / 0 failed**
(containerized full, live FalkorDB, 2026-07-27, 33m04s) — baseline 4335 (main `856f465`) + 8 new; 0 regressions.
Branch `feat/dream-build` @ `ea49356`. Tag: `dream-pre1-confirmed`.

## What
First Dream prerequisite (`DREAM_BUILD_PLAN.md` PRE-1). Gives the Request input a durable backing
store — until now `request_input_ref` was a bare `requestinput:<id>` label with nothing behind it,
so a Request could not be reloaded/replayed (the Dream's necessity / alternative-map replay was
impossible).

- **NEW** `mindsos_intelligence/request_input_persister.py`
  - `persist_request_input(persister, intelligence_metagraph, *, scope, value, modality, encode=None)`
    builds a one-node `RequestInput` graph (value + `modality` prop), persists it via the narrow
    `MMPersister`, returns its `graph_id` = the Episode's `request_input_root_ref`.
  - `load_request_input(client, root_ref) -> (value, modality)` — the Dream's reload anchor.
  - Codec-safe encode discipline mirrors `capacity_persister` (primitive/dict/list, or a supplied
    `encode`, else `PersistenceError`).
- `Orchestrator.run_lifecycle` — persists the input at Request **start** via `self._mm_persister`
  (the Episode "open", D1) and threads `request_input_root_ref` onto the `RequestRun` artifact.
- `chain_artifacts.RequestRun` gains `request_input_root_ref`; `emit_request_run` param added.
- `consolidation.consolidate_request` — Episode gains `request_input_root_ref` (8th field).
- ADR-0176 Amendment 2.

## Behaviour (design calls, this chat)
- **Best-effort + inert.** `request_input_root_ref = None` in simplified mode, with no persister
  wired, or when a non-codec-safe input has no `encode` (swallowed — a non-persistable input must
  NOT fail the solve; the Dream simply lacks that anchor until an encoder is supplied).
- **Live (non-inert)** the moment a persister is wired — unlike `capacity_root_ref` (inert until
  Step 5). Every real Request now writes its raw input to Falkor at start.
- **Reader ships now** (unlike `capacity_root_ref`, PB-5 write-only) — the anchor is proven to
  round-trip against live Falkor.

## Tests
`tests/phase_48/test_request_input_persist.py` — 6 unit (graph shape + modality; modality omitted
when None; non-codec-safe raises; `encode` reduces; encoder result re-checked; empty-scope guard) +
2 integration (`@pytest.mark.integration`, live Falkor: value+modality round-trip; missing-node
raises).

## Regression basis (additive)
No positional `RequestRun(...)` constructions; Episode assertions are subset-key (no exact-set/len);
the seam test builds the orchestrator with no persister (inert there); step5 capture uses
`any(startswith(...))` not exact counts. 0 regressions.

## Next
PRE-0 — streaming / incremental Episode persistence (D1: build now). PRE-1 is its first sub-step
(the raw input recorded at Episode "open").
