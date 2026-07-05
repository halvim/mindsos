---
title: Resident brain — mindsos brain
last_confirmed_phase: 50
---

# Resident brain — `mindsos brain`

`mindsos brain` is a long-lived process that holds **one live MindsOS instance**
you can both **task** and **probe** interactively. Unlike every other `mindsos`
subcommand — which boots a fresh stack, runs one verb, and exits — the brain
keeps a single `KnowledgeLayer` + `CapacityLayer` + `Orchestrator` alive across
commands, so in-process state (episodes, the mental model) accrues as you work.

It is a **REPL**, not a one-shot verb, so it is the one CLI surface that does
**not** follow the `--json`-universal convention ([CLI
conventions](../../dev/conventions.md)): verbs print human-readable text.

## Running it

```
mindsos brain --user alice          # durable: boots from FalkorDB, persists on exit
mindsos brain --user alice --ephemeral   # in-memory: no Falkor, nothing persisted
```

You land in a prompt:

```
MindsOS resident brain. Type 'help', 'quit' to exit.
brain>
```

**Durable mode (default)** needs a running `falkordb` sidecar. It loads the
Global from Falkor, reactivates installed skills from the `installed-skills`
ledger, and load-or-mints the user's Local. `save` (and `quit`) persist the
Local — including accrued episodes — back to Falkor.

**Ephemeral mode** (`--ephemeral`) boots an in-memory stack with builtins only,
no Falkor and no persistence. Use it for a quick look or a scripted trial.

## Verbs

| verb | what it does |
|------|--------------|
| `ls [category]` | list capabilities, optionally one functional category |
| `datastate [iri]` | list DataStates; with an IRI, show its producers / consumers |
| `caps` | list every capability with its `consumes` / `produces` wiring |
| `verify` | structural catalog check — sources / sinks / orphans |
| `invoke <iri> [json]` | dispatch **one** capability; the JSON maps DataState-IRI → value |
| `task <text>` | run the six-phase task lifecycle over `<text>` |
| `save` | persist this user's Local to Falkor |
| `reset` | wipe run-state (episodic memory), keep learned parameters |
| `help` | show the verb list |
| `quit` | `save` then exit |

## Probing (the payoff)

The probe verbs read the bipartite `PRODUCES` / `CONSUMES` graph
([capacity views](../capacity/overview.md)) of the *live* instance, so they
reflect builtins **plus** any installed skills:

```
brain> ls perception
brain> datastate datastate:text.tokens
brain> caps
brain> verify
```

`verify` reports three structural categories and is **OK** unless a DataState is
orphaned (wired to nothing):

- **sources** — consumed but produced by nothing = pipeline entry points (e.g.
  raw text). Informational, not a defect.
- **sinks** — produced but consumed by nothing = terminal writes (e.g.
  `consolidate:mm`). Informational.
- **orphans** — neither produced nor consumed. The one verdict that flips `ok`.

Manifest-aware defect detection (schema drift, code-scan) is out of scope here —
that is the `skill verify` engine.

## Interacting

Two ways to drive work, with very different fidelity today:

**`invoke` — real, single-capability.** `invoke` dispatches one capability body
directly. This is the honest "interact" surface: it runs real bodies for any
builtin or installed capability.

```
brain> invoke capacity:perception:text.space_split {"datastate:text.raw": "the cat sat"}
outputs:
  datastate:text.tokens = ['the', 'cat', 'sat']
```

**`task` — full lifecycle, but v0-hollow.** `task` runs the L4 six-phase
lifecycle. **It reports `succeeded` but performs no real reasoning at v1:** the
lifecycle dispatches over the `planning` / `phase1` / `orchestration` **v0
placeholder catalogs**, whose execution step is notional and dispatches no real
L3 capability (see [end-to-end cookbook](../cookbook/end-to-end.md)). A
`task`-driven solve for an installed skill becomes real only when the **WSD**
installation replaces the v0 catalogs with real ones. Until then, use `invoke`
to drive real capability bodies.

## Installing a skill, then probing it

The resident brain is generic — ARC (or any skill) is just a consumer. A fresh
brain shows only builtins; install a skill first, then boot and probe:

```
mindsos skill install -m <manifest.toml> --persist   # durable ledger; needs Falkor
mindsos brain --user alice
brain> ls        # builtins + the installed skill's capabilities
brain> caps      # the installed wiring
brain> verify    # orphan-free
brain> invoke <installed-cap-iri> {...}   # drive a real installed body
```

`--persist` is required — without it the install record is in-memory and a fresh
`brain` process finds nothing. The skill's Python package must also be
importable in the `brain` process (the boot re-runs its installer entry point).

## Prerequisites

- **Durable mode:** a running `falkordb` sidecar (docker-compose default).
- **Ephemeral mode:** none.
- To probe an installed skill: install it first with `--persist` and keep its
  package importable where `brain` runs.

## Limitations (read honestly)

- **REPL only.** A daemon + socket client (so background dreaming / SubMinds run
  while you interact) is designed but not shipped.
- **`task` is v0-hollow** (above). Real `task`-driven solves are WSD-gated.
- **No retention policy.** In durable mode the Local grows unbounded across
  sessions; `reset` is the only trim, and it is explicit.
- **Single-user.** One Local per brain at v1.

## See also

- [End-to-end cookbook](../cookbook/end-to-end.md) — the same L0→L5 stack the
  brain holds, walked step by step.
- [Capacity overview](../capacity/overview.md) — the probe surface.
- [Runtime internals](../../dev/internals/runtime.md) — how the brain is built.
