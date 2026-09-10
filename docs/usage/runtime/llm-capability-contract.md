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
| 10 | Route its calls through a **broker it runs**, so core never holds the credential at all — and run the broker core ships rather than writing one | `broker`, `adapters.build_brokered_transport`, `mindsos_broker` | `tests/llm_seam/test_broker_contract.py`, `tests/llm_seam/test_reference_broker.py` | **PASS** |
| 11 | Read **off any answer** which mode produced it and at which credential level, without knowing how the client was built — and never be handed a replayed answer that claims to be live | `live.LiveLLM`, `live.CapturingLLM`, `replay.RecordedLLM`, `client.MODES` | `tests/llm_seam/test_answer_provenance.py` | **PASS** — ADR-0210 decisions 5 and 6, amendment 2 |

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

## Row 10, and the configuration it is checked in

⚠ **Slice 4's guards are the first in this package to run over a real socket
through the DEFAULT opener.** `test_adapter_and_seam_guards.py` opens with
*"Every guard injects an opener, so none of them exercises the DEFAULT
opener"*; the level-2 round trip makes a genuine loopback HTTP call to the
reference broker with no `opener=` anywhere on the MindsOS side. The opener
that IS injected is the **broker's upstream** one — the hop *after* the
credential is added, which is the far side of the property being claimed.

The level-2 claim itself is asserted **structurally**, not by observation:
`build_brokered_transport` has no `resolve_credential` parameter and
`broker_headers` has no credential parameter, so there is no argument a caller
could pass and no branch a maintainer could forget. A guard that only observed
*"no credential header was sent this time"* would assert the property in the
one configuration it happened to run, which is round four restated.

⚠ It still does **not** close `dr-transport-never-watched-a-real-provider-failure`:
the upstream is a stub. What is real is the hop MindsOS makes.

## Row 11, and why it took a separate ship

ADR-0210 has said since 2026-09-02 that *"mode and credential level are stamped
on every answer"*. Slice 4 measured that **neither was**, and filed it rather
than riding it: `LiveLLM.read` stamped seven fields, and `credential_level`
existed in this package only as an *optional supplied* manifest key on
`recorded_sets.export_set` — in the module whose own rule is that a manifest is
derived. So `credential_kinds`' argument for its level/kind pairing check
(*"the level is stamped on answers, so an unchecked pairing corrupts
provenance"*) rested on a property the payload did not have. Amendment 2 closes
it.

⚠ **The two fields are stamped by different mechanisms, and the difference is
the design.** Mode comes from the **class** — the rule `recorded` has followed
since slice 1 — because a mode a caller can pass is a mode a caller can forge.
The credential level is **pushed in from L0** with **no default**, because no
class can know it and a default would let a level nobody chose reach an answer.
A replayed answer reports `credential_level: null`, which is the true value: it
reached no provider.

⚠ **This row does not reach a consumer's own records.** `mindsos_llm` may not
import `mindsos_capacity` (`FORBIDDEN_ROOTS`), so whether a layer above declares
these fields as outputs of its records is that layer's decision, not core's
(`core-llm-l3-may-declare-answer-mode-and-level`). The row is what a consumer
can read **off the answer**.

## What this document does NOT claim

- It says nothing about extraction **quality**. Every row is structural. A
  model that returns a well-shaped wrong answer passes all eleven.
- ⚠ **Row 7's harness is weaker than the guard beside it.**
  `verify_transport`'s `identity_is_stamped_above_the_transport` asks
  **presence**, not **override**: a consumer's transport returning its own
  `model_id` is in fact overridden, but the shipped harness never tries it and
  reports PASS. The in-repo guard does try it. Filed as
  `core-llm-contract-identity-check-asks-presence-not-override`; named here
  because a row that reads PASS while its check is narrower than its name is
  exactly what this table exists to prevent.
- Rows 1–9 are about level 1; **row 10 is level 2** (ADR-0210 slice 4); **row
  11 is about every mode and every level**.
  Level 3 remains an adapter property core cannot honestly offer: the shipped
  adapter keeps `SUPPORTED_LEVELS = (LEVEL_NEVER_STORED,)` because the Messages
  API has no expiring credential, and level 3 arrives with a hosted adapter
  (`core-llm-level-3-awaits-a-hosted-adapter`).
- ⚠ **Level 2 is declared separately from the wire's levels**, in
  `BROKERED_LEVELS`, because it is a fact about the adapter's code rather than
  about the provider — the provider never learns a broker exists. A picker
  reads `adapters.offerable_levels`, the union.
- Row 10 is what a consuming project can DO. **Storing a level-2 configuration
  in `mindsos_server` is deliberately not part of it** and has no row, on the
  same ruling that keeps L0 custody off this table: every row is what a
  consumer can do with `pip install mindsos-runtime` and no change to core, and
  custody is deployment configuration (`core-llm-level-2-l0-custody`).
- L0 credential custody (which user, which vendor, which mode) is **not**
  here, and gets no row. Every row above is something a consuming project can
  do with `pip install mindsos-runtime` and no change to core; custody is
  *deployment* configuration, owned by `mindsos_server` and guarded there
  (ADR-0210 slice 2). No row above depends on it.
