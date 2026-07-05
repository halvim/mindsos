# Resident-brain runtime v1 — design note (2026-07-04)

Follows `RESIDENT_BRAIN_DIRECTION_2026-07-04.md`. Scope: minimal durable REPL.
Not a numbered phase; feature branch → Linux gate → confirmation doc.

## Decisions (converged)

- **PB-1** — REPL holds a synchronous `Stack` (KL+CL+MM+`L4Dispatcher`+`Orchestrator`+Session),
  no started `IntelligenceLayer`. Background cognition (dream/submind threads) waits for the daemon stage.
- **PB-2** — new `boot_brain()` helper in `mindsos_server`; replaces the test-only `build_stack` copy.
- **PB-3=B** — Falkor-durable from v1. Episode dict-value persist is unblocked (ADR-0182 codec);
  `save` persists `episodic_memories`.
- **PB-4** — lightweight `catalog_check(view)` in `mindsos_capacity` (dangling/orphan/terminal-write);
  full engine-verify deferred to the skill-verify chat.
- **PB-5** — homes: `boot_brain`→`mindsos_server`, `catalog_check`→`mindsos_capacity`,
  REPL→`mindsos brain` in `mindsos_cli`. No version bump.
- **PB-6=A** — episodes are durable memory; `reset` is explicit-only.

## Surfaces

**`mindsos_server/boot.py`**
```
def boot_brain(client, *, user, install_builtins=True, session=None) -> Stack
```
Durable path: `bootstrap_kl_from_falkordb(client)` → install builtins →
`apply_installed_skills(cl, kl)` → `boot_local(cl, kl, persister, user, session)`.
`client=None` → in-memory ephemeral (test mode). Returns a `Stack` dataclass
(kl, cl, mm, dispatcher, orch, session, persister, user).

**`mindsos_capacity/catalog_check.py`**
```
def catalog_check(view: CapacityLayerView) -> CatalogReport
```
Structural x-ray from the bipartite view: **sources** (consumed-no-producer
= entry points), **sinks** (produced-no-consumer = terminal writes),
**orphans** (wired to nothing). `ok = no orphans`. No engine dependency.
Note (build correction): a consumed-but-unproduced DataState is a
legitimate input, NOT a defect — flagging it would false-positive on the
real builtins catalog (raw-text entry point). Manifest-aware defect
detection stays with the skill-verify engine.

**`mindsos_cli/commands/brain.py`** — `mindsos brain [--user U] [--ephemeral]`
Holds one `Stack`, synchronous loop:

| verb | action |
|---|---|
| `ls [category]` | `iter_capacities` |
| `datastate [iri]` | `iter_datastates`; with IRI → `producers_of`/`consumers_of` |
| `caps` | all caps + `inputs_of`/`outputs_of` wiring |
| `verify` | `catalog_check` |
| `invoke <iri> [json]` | `dispatcher.dispatch(iri, inputs)` — one capability, generic (any installed skill) |
| `task <text>` | `orch.run_lifecycle` |
| `save` | `persister.save(user, kl.local_metagraph(user))` |
| `reset` | `persister.reset_run_state(user)` (explicit) |
| `quit` | `save` then exit |

Session = permissive single-user Local (`has()`→True). REPL writes Local only;
Global persisted by install ops.

## Risks

- v1 is the first live end-to-end consumer of Episode save→load (closes L0-25/L0-26
  by exercising them; may surface a latent bug on the gate).
- Requires live FalkorDB in the loop; install-path demo needs a prior
  `mindsos skill install <ref bundle>`.

## Build order

runtime v1 (this) → daemon+client → ARC-as-bundle (separate chat).
