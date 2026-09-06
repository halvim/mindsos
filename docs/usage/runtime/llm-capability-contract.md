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
| 7 | Verify its own transport against the contract, and be told **by name** which properties core cannot verify | `contract.verify_transport`, `contract.UNVERIFIABLE_PROPERTIES` | `tests/llm_seam/test_transport_contract.py` | **PARTIAL** — ADR-0210 §5 names `credential_not_retained_on_the_composed_request` as unverifiable; it is not in the tuple |
| 8 | Do all of the above without core acquiring a network dependency, a credential, or a vendor SDK | `pyproject.toml` declares none; `adapters/anthropic.py` is `urllib` only | `tests/phase_28/test_import_isolation_phase_28.py`, `tests/llm_seam/test_import_isolation_mindsos_llm.py` | **PASS** |
| 9 | Trust that core proved **its own shipped adapter** against the contract it publishes | — | — | **FAIL** |

## Row 9, which is the one that matters

`verify_transport` is the harness core hands a consumer to check *their*
transport. `tests/llm_seam/test_transport_contract.py` never mentions
`adapters` or `build_transport`: core publishes a contract and has only ever
pointed it at test doubles. A project adopting `mindsos_llm` inherits an
adapter no contract check has been aimed at.

⚠ **And the guards that do cover the adapter say so themselves.**
`tests/llm_seam/test_adapter_and_seam_guards.py` opens with *"Every guard
injects an opener, so none of them exercises the DEFAULT opener."* That is
round four of the credential review, recorded in the file and still standing:
a property asserted only in the configuration where it holds.

Closing row 9 means running `verify_transport` against
`adapters.anthropic.build_transport(...)` with the network stubbed at the
default opener — the configuration every existing guard steps around.

## What this document does NOT claim

- It says nothing about extraction **quality**. Every row is structural. A
  model that returns a well-shaped wrong answer passes all nine.
- Rows 1–8 are about level 1. Levels 2 and 3 are adapter properties: core
  ships one adapter, `SUPPORTED_LEVELS = (LEVEL_NEVER_STORED,)`. A level is
  reachable when an adapter that serves it exists, not when core declares it.
- L0 credential custody (which user, which vendor, which mode) is **not**
  here. It is the next slice, and no row above depends on it.
