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

## Set up and run (any skill)

A resident brain must run as a **long-lived native process** — not `docker exec`,
which starts a fresh process (and a fresh boot) on every call, so no state would
survive. Run it in a virtualenv next to a FalkorDB sidecar. The recipe is generic;
substitute any skill for `<skill-package>` / `<manifest>`.

```
# 1. FalkorDB sidecar (the compose file maps 6379 to the host)
docker compose up -d falkordb

# 2. venv + editable installs of MindsOS core and the skill package
python3 -m venv ~/.venvs/brain && source ~/.venvs/brain/bin/activate
pip install -e <path-to-mindsos>                    # provides the `mindsos` command
pip install -e <skill-package> --no-deps            # e.g. a `mindsos-<skill>` dist
#   --no-deps: the skill depends on `mindsos`, which is not on PyPI

# 3. point at the host-mapped FalkorDB
export FALKORDB_HOST=localhost FALKORDB_PORT=6379

# 4. install the skill into the durable ledger (no login required — see notes)
MANIFEST=<manifest.toml>                             # or resolve from package data, below
mindsos skill install -m "$MANIFEST" --persist

# 5. run the brain — same venv, so the skill package stays importable at boot
mindsos brain --user <you>
```

Notes:

- **No login is needed for `skill install`.** The CLI install path is
  operator-trusted (it runs on the admin's own machine); the ADR-0183 capability
  gate only engages on the server-session path. `--persist` writes the durable
  `installed-skills` ledger record — that record, not any session, is what a later
  brain reactivates. (A failed `mindsos server login` does **not** block the install.)
- **Same environment.** Boot re-imports the skill's installer entry point, so the
  skill package must be importable wherever `mindsos brain` runs — keep the venv
  from step 2 active for step 5.
- **Resolving a package-data manifest.** If the skill ships its manifest inside the
  package rather than as a loose file:
  ```
  MANIFEST=$(python3 -c "from importlib import resources; print(resources.files('<skill_pkg>').joinpath('bundle/manifest.toml'))")
  ```

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

## Probing an installed skill

The resident brain is generic — any skill is just a consumer. A fresh brain shows
only builtins; after the install in [Set up and run](#set-up-and-run-any-skill),
the skill's capabilities appear live:

```
brain> ls        # builtins + the installed skill's capabilities
brain> caps      # the installed wiring
brain> verify    # orphan-free
brain> invoke <installed-cap-iri> {...}   # drive a real installed body
```

If `ls` shows the skill's capabilities, `apply_installed_skills` reactivated them
from the ledger — the `fresh brain → install → probe` loop is closed. If they are
missing, the two usual causes are a missing `--persist` (nothing in the ledger) or
the skill package not being importable in the brain's environment.

## Prerequisites

- **Durable mode:** a running `falkordb` sidecar reachable via `FALKORDB_HOST` /
  `FALKORDB_PORT` (see [Set up and run](#set-up-and-run-any-skill)).
- **Ephemeral mode:** none.
- To probe an installed skill: install it with `--persist` and keep its package
  importable in the same environment where `brain` runs.

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
