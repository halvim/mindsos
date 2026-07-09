"""Man pages for ``mindsos brain`` verbs, shown by ``<verb> -h`` / ``--help``.

Slice 1 reality: ``invoke`` runs a single capacity (pipeline execution is
Slice 2); ``verify`` has no ``--diff`` yet (deferred); ``execute`` is Slice 2
so ``task`` is still present. Create options (``--new`` / ``--seq`` / ``--sub``
/ ``--prototype``) are placeholders pending the skill-acquisition process.
"""

from __future__ import annotations

MANPAGES = {
    "ls": """\
NAME     ls — list every element in the brain
SYNOPSIS ls [-l | -g] [-h]
DESCRIPTION
  Firehose overview: lists all elements across every kind — capacities,
  datastates, pipelines, skills, episodes — grouped by kind. Per-kind detail
  belongs to the specific command (ds, caps, pl, ...). No scope flag = both.
OPTIONS
  -l, --local    Restrict to this user's Local elements.
  -g, --global   Restrict to shared Global elements.
  -h, --help     Print this page.
SEE ALSO  ds, caps, pl, skills, episodes""",
    "search": """\
NAME     search — find every place a string is registered
SYNOPSIS search [-i] [-l | -g] [-h] <pattern>
DESCRIPTION
  Reverse lookup. Matches <pattern> against the IRIs of every registry
  (capacities, datastates, pipelines, skills, episodes) and reports each hit
  with its kind. Glob matching: bare = exact, * = any run, ? = one char,
  [Aa] = character class.
OPTIONS
  -i, --ignore-case   Case-insensitive match.
  -l, --local         Search only Local.
  -g, --global        Search only Global.
  -h, --help          Print this page.
EXAMPLES
  search cell
  search *cell*
  search -i colour
  search [Cc]olor""",
    "ds": """\
NAME     ds — inspect and list datastates
SYNOPSIS ds [-l | -g] [--code] [--new] [-h] [<iri>]
DESCRIPTION
  No positional: list datastates. With <iri>: inspect (producers/consumers).
  A datastate is a typed data slot, not code — --code shows its schema.
OPTIONS
  <iri>          Inspect this datastate (producers / consumers).
  --code         Show the datastate's schema/type. Requires <iri>.
  --new          Author a new datastate. PLACEHOLDER — pending SAP.
  -l, --local    Scope to Local.
  -g, --global   Scope to Global.
  -h, --help     Print this page.
SEE ALSO  caps, pl""",
    "caps": """\
NAME     caps — inspect and list capacities
SYNOPSIS caps [-l | -g] [--code] [--new] [-h] [<iri>]
DESCRIPTION
  No positional: list capacities. With <iri>: inspect consumes/produces
  wiring. Capacities carry executable bodies — --code shows the registered
  declaration and its source module.
OPTIONS
  <iri>          Inspect this capacity (consumes / produces).
  --code         Show the capacity's declaration + __module__. Requires <iri>.
  --new          Author a new capacity. PLACEHOLDER — pending SAP.
  -l, --local    Scope to Local.
  -g, --global   Scope to Global.
  -h, --help     Print this page.
SEE ALSO  ds, pl, invoke""",
    "pl": """\
NAME     pl — inspect and build pipelines
SYNOPSIS pl [-l | -g] [--transitions] [--seq] [--sub] [--new] [-h] [<from> <to>]
DESCRIPTION
  No argument: list pipelines (promoted + local learned). Two datastate IRIs:
  find a chain from <from> to <to>. Build options author+persist and are
  placeholders pending SAP; only listing, path-finding, and --transitions run.
OPTIONS
  <from> <to>     Find a chain between two datastates.
  --transitions   Print the datastate hops (state -> cap -> state) per step.
  --seq           Build a pipeline from a capacity sequence. PLACEHOLDER — SAP.
  --sub           Compose from existing sub-pipelines. PLACEHOLDER — SAP.
  --new           Author a pipeline. PLACEHOLDER — SAP.
  -l, --local     Scope to Local.
  -g, --global    Scope to Global.
  -h, --help      Print this page.
NOTES
  Path-finding is BFS (single-source, linear). Targets needing a conjunction
  of two inputs are not found and report "no pipeline".
SEE ALSO  ds, caps, invoke""",
    "skills": """\
NAME     skills — inspect and list installed skills
SYNOPSIS skills [-l | -g] [--new] [--prototype] [-h] [<name>]
DESCRIPTION
  No positional: list install-ledger records. With <name>: inspect that skill.
  Authoring options are placeholders pending SAP.
OPTIONS
  <name>         Inspect one skill's record.
  --new          Author a new skill. PLACEHOLDER — pending SAP.
  --prototype    Build a candidate skill and diff vs an existing one.
                 PLACEHOLDER — pending SAP.
  -l, --local    Scope to Local.
  -g, --global   Scope to Global.
  -h, --help     Print this page.
SEE ALSO  verify""",
    "episodes": """\
NAME     episodes — inspect episodic memory
SYNOPSIS episodes [-l | -g] [-h] [<iri>]
DESCRIPTION
  No positional: list this user's Episodes. With <iri>: print the Episode's
  recorded content. Data lives in the L2 episodic_memories role-graph; the
  retain-on-completion decision is L4/L5. Episodes are Local by nature.
OPTIONS
  <iri>          Inspect one Episode's content.
  -l, --local    Scope to Local.
  -g, --global   Scope to Global (Episodes do not live in Global).
  -h, --help     Print this page.
SEE ALSO  verify""",
    "invoke": """\
NAME     invoke — run one capacity or pipeline
SYNOPSIS invoke [-h] <cap|pipeline-iri|suffix> [inputs]
DESCRIPTION
  Dispatches a single capacity, or runs a named promoted pipeline, against the
  live merged catalog. The target may be a unique IRI suffix. A single-input
  capacity (or single-start pipeline) binds its input positionally; multiple
  inputs use key=value with short datastate names. JSON object also accepted.
  Resolution spans both scopes (no -l/-g).
OPTIONS
  <cap|pipeline|suffix>  The capacity or promoted pipeline to run.
  [inputs]               One positional value, key=value pairs, or a JSON object.
  -h, --help             Print this page.
EXAMPLES
  invoke space_split "the cat sat"
  invoke some_pipeline:1 "the cat sat"
SEE ALSO  execute, caps, pl""",
    "execute": """\
NAME     execute — run a skill's declared entry pipeline
SYNOPSIS execute [-h] <input>
DESCRIPTION
  Runs the installed skill's declared runtime entry: seeds its
  entry_start_datastate with <input>, composes a pipeline to its
  entry_target_datastate via the conjunction finder, and runs it standalone.
  If no installed skill declares an entry, execute is a no-op notice (task
  remains for the generic six-phase lifecycle). If several skills declare
  entries it reports the ambiguity.
OPTIONS
  <input>        The value seeded into the entry start datastate.
  -h, --help     Print this page.
EXAMPLES
  execute "the cat sat"
SEE ALSO  invoke, skills, pl""",
    "verify": """\
NAME     verify — system report and health check
SYNOPSIS verify [--ds | --caps | --pl] [-h]
DESCRIPTION
  Prints the brain's status + structural x-ray: user, mode, counts, sources,
  sinks, orphans. Absorbs the former `status`. (--diff vs a prior snapshot is
  a deferred item.)
OPTIONS
  --ds           Restrict the report to datastates.
  --caps         Restrict the report to capacities.
  --pl           Restrict the report to pipelines.
  -h, --help     Print this page.
SEE ALSO  ls, ds, caps, pl""",
    "task": """\
NAME     task — run the six-phase task lifecycle
SYNOPSIS task [-h] <text>
DESCRIPTION
  Runs the generic six-phase lifecycle over <text>. (Slice 2 replaces this
  with `execute`, which runs a skill's declared entry pipeline.)
OPTIONS
  <text>         The task input.
  -h, --help     Print this page.
SEE ALSO  invoke""",
    "save": """\
NAME     save — persist this user's Local to Falkor
SYNOPSIS save [-h]""",
    "reset": """\
NAME     reset — wipe run-state (episodic memory), keep learned parameters
SYNOPSIS reset [-h]""",
}

__all__ = ["MANPAGES"]
