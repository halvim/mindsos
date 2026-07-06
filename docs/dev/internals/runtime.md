---
title: Internals — Resident-brain runtime
last_confirmed_phase: 50
---

# Internals — Resident-brain runtime

The resident-brain runtime is a thin, generic layer over the shipped stack: a
long-lived process that holds one live instance you can task and probe. It adds
no domain surface and no version bump — it composes L0–L5 and exposes them
through a REPL. This page documents how it is built and why.

Design record: `confirmation_docs/RESIDENT_BRAIN_RUNTIME_DESIGN_NOTE.md` +
`RESIDENT_BRAIN_RUNTIME_CONFIRMED.md`. There is **no ADR** — the runtime is not a
numbered phase, so the design/confirmation notes are the authoritative record.

## Three pieces

| Piece | Home | Role |
|-------|------|------|
| `boot_brain` | `mindsos_server/boot.py` | compose one `Stack` (L2/L3/L4/L5 + session) |
| `catalog_check` | `mindsos_capacity/catalog_check.py` | record-less structural x-ray of the L3 catalog |
| `mindsos brain` | `mindsos_cli/commands/brain.py` | the REPL: one held `Stack`, pure verb dispatch |

## `boot_brain`

```python
def boot_brain(client=None, *, user, install_builtins=True, session=None) -> Stack
```

`Stack` is a dataclass holding `kl`, `cl`, `mm`, `dispatcher`, `orch`, `session`,
`persister`, `user`, plus `global_view()` and `save()`.

**Durable path** (`client` supplied) composes existing server functions:

1. `bootstrap_kl_from_falkordb(client)` — load-or-mint the Global.
2. install the v0 builtins (`planning_v0` + `phase1_v0` + `orchestration_v0` +
   `consolidate` + `text` + `dream`, then `reset_v0_verdicts()`) — the same set
   the Phase-49 `build_stack` recipe uses.
3. `apply_installed_skills(cl, kl)` — re-run installed bundles' L3 installer
   entry points from the `installed-skills` ledger.
4. `boot_local(cl, kl, persister, user, session=...)` — load-or-mint the user's
   Local and reactivate its learned capacities.

**Ephemeral path** (`client=None`) swaps step 1 for `KnowledgeLayer.bootstrap()`
and uses `InMemoryLocalPersister`; there is no ledger, so `apply_installed_skills`
is a no-op. Deterministic and Falkor-free — the unit-test path.

`boot_brain` is the product-code promotion of the test-only
`tests/phase_49/integration_c.py::build_stack` (which the ARC prototype had
copy-pasted). It lives in `mindsos_server` because it composes L0–L5 and the
server already owns `bootstrap_kl_from_falkordb`, `boot_local`, and the
persisters — Server imports downward into the stack (ADR-0010).

### Installed-skill reactivation

The durable boot reactivates installed skills by re-running their L3 installer
entry points (`apply_installed_skills`), which the skill packages must therefore
be **importable** to provide — so the brain runs in an environment where every
installed skill's package is on the path. The source of truth is the durable
`installed-skills` ledger record written at install time; the CLI `skill install`
that writes it is **operator-trusted** (not session-gated — the ADR-0183
capability gate engages only on the server-session path, per the
`mindsos_cli/commands/skill.py` header), so reactivation depends on the persisted
record, never on any live session or token.

### Session

`boot_brain` builds a permissive single-user `_BrainSession` (`has()` → `True`)
by default. A resident brain v1 is single-user and only writes its **own** Local,
so the ADR-0180 scope-aware write gate — which fires on **Global** writes — is
never tripped. Same shape as the Phase-49 integration `_Session`.

### Persistence

`Stack.save()` calls `persister.save(user, kl.local_metagraph(user))` — the whole
Local, **including `episodic_memories`**. `reset_run_state` (which wipes
episodes) is explicit-only; it is **not** on the boot or save path, so accrued
episodes survive a clean exit. Durable Episode persistence works because Phase
50's ADR-0182 `_value_json` codec serializes the Episode's structured dict value
(the runtime is its first end-to-end consumer — see `tests/resident_brain/
test_durable_roundtrip.py`, which closes the paper-open L0-25/L0-26
carry-forwards by exercising them).

## Why a synchronous `Stack`, not a started `IntelligenceLayer`

The tempting move is to hold an L4 `IntelligenceLayer` (Phase 46) alive. The
runtime deliberately does **not**, at v1:

- `IntelligenceLayer.start()` spins background threads — dream-cycle timer,
  signal triage, SubMind scheduler — that fire unpredictably under an
  interactive REPL and force read-lock discipline on every probe.
- Its tasking API is `enqueue(callable)`; it does **not** drive
  `Orchestrator.run_lifecycle` directly. A REPL wants synchronous
  `run_lifecycle`.
- It builds its own three-sub-MM container, distinct from the `Stack.mm` the
  orchestrator uses.

So the REPL holds a plain synchronous `Stack` (`KL + CL + MM + L4Dispatcher +
Orchestrator + Session`) and runs each verb inline. Background cognition is the
job of the **deferred daemon stage**, where an `IntelligenceLayer` re-enters —
constructed over the same `KL`/`CL`, enqueuing closures that call
`orch.run_lifecycle`. No rework of `boot_brain` is implied.

## `catalog_check`

```python
def catalog_check(view: CapacityLayerView) -> CatalogReport
```

A pure, read-only walk of the bipartite `PRODUCES` / `CONSUMES` edges via the
view's producer/consumer accessors. `CatalogReport` carries `capacities`,
`datastates`, and three lists:

- **sources** — `(cap, ds)` where `ds` is consumed but produced by nothing → a
  pipeline entry point. **Not** a defect: without a manifest it is
  indistinguishable from a missing producer.
- **sinks** — `(cap, ds)` produced but consumed by nothing → a terminal write.
  Informational.
- **orphans** — a `ds` with neither producer nor consumer. `ok = not orphans`.

An early version flagged sources as defects; that false-positives the real
builtins catalog (the raw-text entry point has no producer). The unit test
`test_ephemeral_builtins_catalog_is_orphan_free` caught it. Manifest-aware
checks (schema drift, code-scan via `__module__`) belong to the `skill verify`
engine and are not duplicated here; `catalog_check` is the record-less subset,
placed in `mindsos_capacity` (the engine's charter-destined home) so the
skill-verify chat can extend it.

## The REPL

`mindsos_cli/commands/brain.py` keeps verb dispatch pure — `BrainREPL.dispatch(
line) -> str` — so the whole verb surface is unit-testable without a TTY. `loop()`
is the thin stdin front end; `quit` calls `save` then exits. Being an interactive
REPL, `brain` is the documented exception to the `--json`-universal convention.

Verbs take Linux-style flags. Two support modules sit beside `brain.py`:
`_replparse.py` tokenizes with `shlex` (quoting works) and parses flags without
ever raising or `sys.exit`-ing — it returns an error *string*, honouring the
`dispatch` contract. `_manpages.py` holds a per-verb man page shown by
`<verb> -h`, pre-scanned before verb logic. Verbs: probes `ls` / `search` /
`ds` / `caps` / `pl` / `skills` / `episodes` / `verify`; actions `invoke` /
`execute` / `task` / `save` / `reset`. The read verbs' `-l/--local` /
`-g/--global` scope flags select `Stack.local_view()` (the Local L3 partition)
vs `global_view()`; datastates/pipelines/skills/episodes are read through the L0
readers `mindsos_server/episodes.py` and `pipelines.py`.

`invoke` routes through `Stack.dispatcher.dispatch(cap_iri, inputs)` — the same
`L4Dispatcher` path the lifecycle uses — so it drives real capability bodies for
any builtin or installed skill; the capacity may be named by a unique IRI
suffix, and inputs are a positional value, `key=value` pairs, or **single-quoted**
JSON (bare JSON is mangled because `shlex` strips its quotes). `task` routes
through `orch.run_lifecycle`, which at v1 runs the v0 placeholder catalogs (no
real L3 dispatch); the honest split is documented in the
[user guide](../../usage/runtime/resident-brain.md).

## `execute` and the standalone pipeline runner

`execute <input>` runs an installed skill's declared *entry* pipeline. A skill
declares its entry with two optional flat props on its `SkillInstallRecord` —
`entry_start_datastate` / `entry_target_datastate` (ADR-0183 §am-1; additive on
the `strict=False` schema), read by `records.py::skill_entries`. `execute` seeds
the start DataState with `<input>`, composes a chain to the target with
`ConjunctionFinder` (sound for multi-input; `input_group` defaults to
`all_required`, so single-input caps work too), and runs it through
`mindsos_server/pipeline_runner.py::run_pipeline` — a standalone step-runner that
walks the topo-ordered `Pipeline.steps` threading a `{datastate: value}` map via
the dispatcher, with **no** `ChainArtifactWriter`, TaskRun, or MM coupling. The
same runner backs `invoke <promoted-pipeline>`.

Two contract notes: the finder's view is chosen by `session.user_id`, so
`execute`/`pl` call it with **`session=None`** to search the Global catalog (a
session-bearing view resolves to the Local partition, which lacks the global
builtins). And `execute` is **inert** until some skill declares an entry — none
ship one yet; ARC-packaging is the first consumer, so `task` is retained.

## Tests

`tests/resident_brain/`: `test_replparse.py` (the flag parser, pure),
`test_catalog_check.py` (fake-view unit cases + an ephemeral orphan-free smoke),
`test_boot_brain.py` (ephemeral shape / task / save), `test_brain_repl.py`
(every verb, headless), `test_execute.py` (the step-runner + `execute` +
invoke-pipeline over synthetic install-record / promoted-pipeline fixtures), and
`test_durable_roundtrip.py` (`@pytest.mark.integration`, live-Falkor Episode
save→load). All but the last run without a sidecar.

## Deferred

Daemon + socket client (background cognition) · a retention policy for unbounded
Local growth · crash-autosave · full engine-backed `verify` · `verify --diff`
against a persisted prior-state snapshot · real `task`-driven solves (blocked on
the WSD v0→real orchestration flip, Phases 51–56).
