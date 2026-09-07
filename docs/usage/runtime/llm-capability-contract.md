# The `mindsos_llm` capability contract

**What this document is.** `mindsos_llm` is a cross-layer core capability
(ADR-0210), not a subsystem and not a demo's private code. "Complete" for a
capability offered to *any* project cannot mean "the CR's slice list is
exhausted" — it has to mean a new project can do a stated set of things with
`pip install mindsos-runtime` and no change to core.

This is that set. Every row is a claim about the tree, with the module that
answers it and the guard that pins it. **A row with no guard is not a
capability, it is a promise.**

⚠ **This table is checked, not recalled.** A ship that changes any row updates
it in the same commit.

## The contract

| # | A consuming project can… | Answered by | Pinned by | Status |
|---|---|---|---|---|
| 1 | Discover which vendors this core speaks to, and at which credential levels, without reading source | `adapters.vendors()`, `adapters.supported_levels()` | `tests/llm_seam/test_adapter_and_seam_guards.py` | **PASS** |
| 2 | Register its own adapter, and have a duplicate vendor id refused rather than overwritten | `adapters.register()` | same | **PASS** |
| 3 | Supply a level-1 credential and have it scrubbed from the composed request after the call, success or failure | `seam.build_headers`, `seam.scrub`, `seam.send` | `test_the_composed_request_retains_no_credential_after_a_SUCCESSFUL_call` / `…_FAILED_call` | **PASS** |
| 4 | Make a live call and get a classified refusal, never an exception carrying the customer's material | `live.LiveLLM`, `seam` exception family | `tests/llm_seam/test_llm_client.py` | **PASS** |
| 5 | Record what it called and replay it later with no credential and no network | `recording.RecordingStore`, `replay.RecordedLLM` | `tests/llm_seam/test_recording_and_replay.py` | **PASS** |
| 6 | Export a recorded set and have a third party replay it — including the refusal when the set holds two model identities | `recorded_sets` | `tests/llm_seam/test_recorded_set_export.py` | **PASS** |
| 7 | Verify its own transport against the contract, and be told **by name** which properties core cannot verify | `contract.verify_transport`, `contract.UNVERIFIABLE_PROPERTIES` | `tests/llm_seam/test_transport_contract.py`, `tests/llm_seam/test_contract_against_the_shipped_adapter.py` | **PASS** — `credential_not_retained_on_the_composed_request` is the fifth entry in the tuple per ADR-0210 §5 (`511b999`) |
| 8 | Do all of the above without core acquiring a network dependency, a credential, or a vendor SDK | `pyproject.toml` declares none; `adapters/anthropic.py` is `urllib` only | `tests/phase_28/test_import_isolation_phase_28.py`, `tests/llm_seam/test_import_isolation_mindsos_llm.py` | **PASS** |
| 9 | Trust that core proved **its own shipped adapter** against the contract it publishes | `contract.verify_transport` against `adapters.anthropic.build_transport` | `tests/llm_seam/test_contract_against_the_shipped_adapter.py` | **PASS** |

## Row 9, and how it was closed

`verify_transport` is the harness core hands a consumer to check *their*
transport. Until `511b999`, `tests/llm_seam/test_transport_contract.py` never
mentioned `adapters` or `build_transport`: core published a contract, shipped
one wire implementation, and pointed the first at the second nowhere. A project
adopting `mindsos_llm` inherited an adapter no contract check had been aimed at.

⚠ **The configuration mattered as much as the check.**
`tests/llm_seam/test_adapter_and_seam_guards.py` opens with *"Every guard
injects an opener, so none of them exercises the DEFAULT opener."* That is round
four of the credential review, and a check that closed row 9 by passing
`opener=` would have re-run it. So
`tests/llm_seam/test_contract_against_the_shipped_adapter.py` stubs
`urllib.request.urlopen` instead and calls `build_transport` with no `opener`,
which is the path a deployment actually takes.

⚠ **This did not close `dr-transport-never-watched-a-real-provider-failure`.**
The guard stubs the network. Nothing has watched a real provider fail.

## What this document does NOT claim

- It says nothing about extraction **quality**. Every row is structural. A
  model that returns a well-shaped wrong answer passes all nine.
- Rows 1–8 are about level 1. Levels 2 and 3 are adapter properties: core
  ships one adapter, `SUPPORTED_LEVELS = (LEVEL_NEVER_STORED,)`. A level is
  reachable when an adapter that serves it exists, not when core declares it.
- L0 credential custody (which user, which vendor, which mode) is **not**
  here, and gets no row. Every row above is something a consuming project can
  do with `pip install mindsos-runtime` and no change to core; custody is
  *deployment* configuration, owned by `mindsos_server` and guarded there
  (ADR-0210 slice 2). No row above depends on it.
