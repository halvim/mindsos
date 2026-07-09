# Resident-Brain REPL — Command & Man-Page Design

Status: DESIGN (not built). Extends the shipped resident-brain runtime v1 +
`invoke`. Additive; no version bump (server-layer readers, no versioned
domain surface) unless a decision below says otherwise.

## 1. Grammar standard (parser foundation)

- `dispatch(line) -> str` stays the contract: never raises, never `sys.exit`s.
- Tokenize with `shlex.split` (adds quoting: `"two words"`).
- A REPL-safe flag parser returns `(opts, positionals)` or an error string.
- `-h`/`--help` is pre-scanned before verb logic; prints the command's man
  page from a `MANPAGES` store.
- Global options on every command: `-h/--help`, `-l/--local`, `-g/--global`
  (scope; default = both). **List is the default action** (no positional =
  list all).

## 2. Command set

| cmd | purpose |
|---|---|
| `ls` | firehose overview — list all elements across every kind |
| `search <pattern>` | reverse-lookup a string across all registries (glob) |
| `ds [<iri>]` | list / inspect datastates (`--code` = schema) |
| `caps [<iri>]` | list / inspect capacities (`--code` = body + module) |
| `pl [<from> <to>]` | list / find / (SAP) build pipelines |
| `skills [<name>]` | list / inspect / (SAP) author skills |
| `episodes [<iri>]` | list / inspect episodic memory |
| `invoke <cap\|pl> [inputs]` | run one capacity or pipeline |
| `execute [input]` | run the skill's declared entry pipeline (replaces `task`) |
| `verify` | system report + health (absorbs `status`) |

## 3. Create standard (`--new` / `--seq` / `--sub` / `--prototype`)

All create/author options are a CLI front-end over the skill-acquisition
process (SAP). Until SAP ships they are PLACEHOLDERS: they print a
"not yet — pending skill-acquisition" notice. When SAP lands, every `--new`
routes through the one flow: name/IRI -> scope (Local default) -> spec ->
L1 schema validate + ADR-0180 write gate -> stage (logical -> prototype ->
commit -> package) -> persist. No REPL-local authoring model.

## 4. `invoke` ergonomics (decision)

Pick A+B, C fallback:
- Cap resolved by unique suffix/glob (A): `invoke space_split ...`.
- Single input bound positionally (B): `invoke space_split "the cat sat"`.
- Multi-input via `key=value` short ds names (C): `invoke cap a=1 b=2`.
- shlex supplies quoting. Positional multi-input is DEFERRED to
  composition-lifecycle Slice-2 (operand-arity); until then multi-input
  uses `key=value`.

## 5. Man pages

(Displayed by `<cmd> -h`. Bare `help` remains the index.)

### ls
```
NAME     ls — list every element in the brain
SYNOPSIS ls [-l | -g] [-h]
DESCRIPTION
  Firehose overview. Lists all elements across every kind — knowledge roles,
  datastates, capacities, pipelines, skills, episodes — grouped by kind.
  Per-kind detail belongs to the specific command. No scope flag = both.
OPTIONS
  -l, --local    Restrict to this user's Local elements.
  -g, --global   Restrict to shared Global elements.
  -h, --help     Print this page.
EXAMPLES
  ls
  ls -l
SEE ALSO  ds, caps, pl, skills, episodes
```

### search
```
NAME     search — find every place a string is registered
SYNOPSIS search [-i] [-l | -g] [-h] <pattern>
DESCRIPTION
  Reverse lookup. Matches <pattern> against IRIs and labels of every registry
  and reports each hit with its kind. Glob matching:
    bare  exact   |  *  any run  |  ?  one char  |  [Aa]  char class
OPTIONS
  -i, --ignore-case   Case-insensitive match.
  -l, --local         Search only Local.
  -g, --global        Search only Global.
  -h, --help          Print this page.
EXAMPLES
  search cell
  search *cell*
  search -i colour
  search [Cc]olor
```

### ds
```
NAME     ds — inspect and list datastates
SYNOPSIS ds [-l | -g] [--code] [--new] [-h] [<iri>]
DESCRIPTION
  No positional: list datastates. With <iri>: inspect (producers/consumers).
  A datastate is a typed data slot, not code — --code shows its schema.
OPTIONS
  <iri>          Inspect this datastate (producers / consumers).
  --code         Show the datastate's schema. Requires <iri>.
  --new          Author a new datastate. PLACEHOLDER — routes to SAP.
  -l, --local    Scope to Local.
  -g, --global   Scope to Global.
  -h, --help     Print this page.
EXAMPLES
  ds
  ds -g
  ds capacity:datastate:tokens
  ds --code capacity:datastate:tokens
SEE ALSO  caps, pl
```

### caps
```
NAME     caps — inspect and list capacities
SYNOPSIS caps [-l | -g] [--code] [--new] [-h] [<iri>]
DESCRIPTION
  No positional: list capacities. With <iri>: inspect consumes/produces
  wiring. Capacities carry executable bodies — --code reveals body + module.
OPTIONS
  <iri>          Inspect this capacity (consumes / produces).
  --code         Show the capacity's body and __module__. Requires <iri>.
  --new          Author a new capacity. PLACEHOLDER — routes to SAP.
  -l, --local    Scope to Local.
  -g, --global   Scope to Global.
  -h, --help     Print this page.
EXAMPLES
  caps
  caps capacity:perception:text.space_split
  caps --code capacity:perception:text.space_split
SEE ALSO  ds, pl, invoke
```

### pl
```
NAME     pl — inspect and build pipelines
SYNOPSIS pl [-l | -g] [--transitions] [--seq <cap>...] [--sub <pl>...]
            [--new] [-h] [<from> <to>]
DESCRIPTION
  No argument: list pipelines. Two datastate IRIs: find a chain from <from>
  to <to>. Build options (--seq/--sub/--new) author+persist and are SAP-gated;
  only listing, path-finding, and --transitions are live today.
OPTIONS
  <from> <to>     Find a chain between two datastates.
  --transitions   Print the datastate hops (state in -> cap -> state out).
  --seq <cap>...  Build a pipeline from a capacity sequence. PLACEHOLDER SAP.
  --sub <pl>...   Compose from existing sub-pipelines. PLACEHOLDER SAP.
  --new           Author a pipeline. PLACEHOLDER SAP.
  -l, --local     Scope to Local.
  -g, --global    Scope to Global.
  -h, --help      Print this page.
EXAMPLES
  pl
  pl capacity:datastate:raw_text capacity:datastate:tokens
  pl --transitions capacity:datastate:raw_text capacity:datastate:tokens
NOTES
  Path-finding is BFS (single-source, linear). Targets needing a conjunction
  of two inputs are not found and report "no pipeline".
SEE ALSO  ds, caps, invoke, execute
```

### skills
```
NAME     skills — inspect and list installed skills
SYNOPSIS skills [-l | -g] [--new] [--prototype] [-h] [<name>]
DESCRIPTION
  No positional: list install-ledger records. With <name>: inspect that skill.
  Authoring options are SAP-gated.
OPTIONS
  <name>         Inspect one skill's record and contents.
  --new          Author a new skill. PLACEHOLDER — routes to SAP.
  --prototype    Build a candidate skill and diff vs an existing one.
                 PLACEHOLDER — routes to SAP.
  -l, --local    Scope to Local.
  -g, --global   Scope to Global.
  -h, --help     Print this page.
EXAMPLES
  skills
  skills arc-solver
SEE ALSO  execute, verify
```

### episodes
```
NAME     episodes — inspect episodic memory
SYNOPSIS episodes [-l | -g] [-h] [<iri>]
DESCRIPTION
  No positional: list this user's Episodes. With <iri>: print the Episode's
  recorded content. Data lives in the L2 episodic_memories role-graph; the
  retain-on-completion decision is L4/L5.
OPTIONS
  <iri>          Inspect one Episode's content.
  -l, --local    Scope to Local (Episodes are Local by nature).
  -g, --global   Scope to Global.
  -h, --help     Print this page.
EXAMPLES
  episodes
  episodes episode:v50:alice:ep-0001
SEE ALSO  verify, execute
```

### invoke
```
NAME     invoke — run one capacity or pipeline
SYNOPSIS invoke [-h] <cap|pl-iri|suffix> [inputs]
DESCRIPTION
  Dispatches a single capacity or a named pipeline against the live merged
  catalog, driving the real body. Resolution spans both scopes, so invoke
  takes no -l/-g. The cap may be given as a unique suffix. Single input binds
  positionally; multiple inputs use key=value with short datastate names.
OPTIONS
  <cap|pl|suffix>  The capacity/pipeline to run (unique suffix accepted).
  [inputs]         Either one positional value (single-input cap) OR
                   key=value pairs (short datastate name = value). Defaults
                   to no inputs.
  -h, --help       Print this page.
EXAMPLES
  invoke space_split "the cat sat"
  invoke some_cap a=1 b=2
SEE ALSO  execute, caps, pl
```

### execute
```
NAME     execute — run the skill's entry pipeline
SYNOPSIS execute [-h] [input]
DESCRIPTION
  Runs the skill's declared main pipeline over [input] — e.g. an ARC brain's
  "solve task". Replaces the former `task` verb.
OPTIONS
  [input]        The task input handed to the entry pipeline.
  -h, --help     Print this page.
NOTES
  Depends on a skill-manifest entrypoint field. If none exists, execute is
  net-new scope, not a `task` rename — UNRESOLVED (open decision #3).
SEE ALSO  invoke, skills
```

### verify
```
NAME     verify — system report and health check
SYNOPSIS verify [--ds | --caps | --pl] [--diff] [-h]
DESCRIPTION
  Prints the structural x-ray of the loaded brain: counts, sources, sinks,
  orphans, load status. Absorbs the former `status` verb.
OPTIONS
  --ds           Restrict the report to datastates.
  --caps         Restrict the report to capacities.
  --pl           Restrict the report to pipelines.
  --diff         Show what changed vs the last snapshot. See NOTES.
  -h, --help     Print this page.
EXAMPLES
  verify
  verify --caps
  verify --diff
NOTES
  --diff requires a persisted prior snapshot; storage location UNRESOLVED
  (open decision #4).
SEE ALSO  ls, ds, caps, pl
```

## 6. Open decisions (must resolve before implementation)

1. Local probe surface — add `local_view()` + a per-element scope tag;
   today only `global_view()` exists. Blocks every `-l/-g` flag. Rec: build
   the Local view first; default both.
2. `invoke` operand order — positional multi-input needs stable input
   ordering (composition-lifecycle Slice-2 operand-arity). Rec: single-input
   positional now; multi-input via key=value until Slice-2.
3. `execute` entrypoint — confirm the skill manifest carries a main-pipeline
   field. If not, keep `task` until execute has something to call.
4. `verify --diff` snapshot store — Rec: a Local snapshot node written on
   `save`.
5. `--code` with no `<iri>` — Rec: error (listing is the dump-all path).
6. Parser foundation — shlex + REPL-safe parser + `-h` pre-scan + MANPAGES.

## 7. Corrections & layer map (probed 2026-07-05)

**Layer homes** (L0 = Server per HANDOFF §1; `mindsos_cli` is the CLI surface,
NOT a domain layer):
- CLI surface (`mindsos_cli`): verbs, flag parser, `-h` pre-scan, MANPAGES,
  man-page strings. **Not L0.**
- L0 / Server (`mindsos_server`): `episodes.py` reader; `Stack.local_view()`
  wrapper in `boot.py`.
- L3 (`mindsos_capacity`): `find_pipeline`, `CapacityLayerView`,
  `catalog_check` — already shipped, UNTOUCHED.

**Decision #1 update — `local_view` already exists.** `CapacityLayer.local_view
(user_id)` and the `self._global` + `self._locals[user]` partition already
ship. Only a one-line `Stack.local_view()` wrapper in `boot.py` (L0) is new.
No L3 change, no version bump. `caps -l` / `ds -l` resolve against the existing
Local partition (empty on a brain with no learned caps — correct).

**Decision #3 update — execute entrypoint is NOT declared.** Only
`skills/driver.py::_resolve_entry_point` exists, and it is install-time (Python
driver spec), not a runtime main-pipeline. So a skill runtime-entrypoint field
is IN SCOPE: a schema addition to the skill manifest (versioned domain surface
-> likely a real version bump). Split `execute` into its own slice; keep `task`
until execute has a declared pipeline to run. The read/probe verbs ship
version-neutral first.

**Parser is CLI-layer, not L0.** Promote to core only with an explicit reason;
default home is `mindsos_cli`.

## 8. As-built outcome (SHIPPED to main 2026-07-05)

Both slices shipped; full containerized gate 4175 passed / 12 skip / 1 xpass /
0 fail. Slice 1 = main `14efafc`, Slice 2 = main `e1b10d6`, closeout `2baa956`.

Decision changes vs the design above (reversals recorded):

- **NO version bump.** §7 anticipated a release-train bump for the schema
  props. A `phase50a` bump was implemented and then **fully reverted**: the
  MindsOS version scheme is integer-phase-locked (`0.0.0+phaseN`, a `phase`
  field in `mindsos_cli/manifest.toml`, enforced by ~5 doctor parity tests and
  a digit-only `preflight` regex). There is no representation for a sub-phase,
  and integers ≥51 are reserved for WSD. Additive/inter-phase changes stay at
  `phase50` (precedent: runtime v1, `invoke`, SubMind Slice 2). D1 stands
  (entry lives in two flat schema props) but it is additive on the
  `strict=False` schema and needs no bump.

- **`execute` uses `ConjunctionFinder` over the GLOBAL view, not BFS.** D2's
  `find_pipeline` was replaced by `ConjunctionFinder().find(..., session=None,
  start_datastates=(start,), target_datastate=target)`. Two reasons: (a) ARC's
  entry target is multi-input, which BFS is unsound for; (b) the finder's view
  is chosen by `session.user_id`, so a session-bearing call searches the empty
  Local partition — `session=None` is required to search the Global catalog.
  `ConjunctionFinder` also handles single-input caps (`input_group` defaults to
  `all_required`), so no BFS fallback is needed. `pl <from> <to>` was fixed the
  same way.

- **`invoke` JSON must be single-quoted** — `shlex` strips bare quotes.

- **ARC single-start boundary CONFIRMED by ARC-packaging:** ARC fits
  single-start (`arc.raw_task` bundles the task); its multi-input problem is
  target-side composition. ARC owns "Blocker 1" (register producers so a path
  to `arc.solve` exists) before `execute` returns a solved grid. The ARC
  coordination was a transient handoff (`.scratch/ARC_ENTRY_DECLARATION.md`),
  not a durable doc.

Deferred, unchanged: `verify --diff` + a prior-state snapshot store.
