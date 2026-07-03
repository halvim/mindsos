# Skill-as-graph L3 reorganization — design seed (deferred "B")

Status: **not started.** Surfaced during the `skill verify` design chat. Own chat
when the time comes.

## Intent

A skill/bundle should be an **L3 graph** — e.g. an `arc-solver` graph in Local L3
holding that skill's own capacities. Functional category (perception,
comprehension, …) becomes a **per-capacity tag *inside* the skill graph**, not the
top-level organizing axis.

Example: Local L3 → `arc-solver` graph → capacities `read-task` (perception),
`extract-shapes-and-grid` (comprehension), etc.

## Current state (what changes)

Today L3 organizes by **category**: each metagraph (Global + Local) holds one
shared `capacity:datastates` graph + **one graph per functional category**
(`capacity:<category>`, 13 categories) — see `mindsos_capacity/identifiers.py` §3,
`ensure_category_graph`. A bundle's capacities scatter across category graphs; a
bundle owns no graph.

Target inverts this: top-level graph = skill; category = capacity attribute.

## Why it matters (payoff)

- **Bundle attribution becomes structural** — the capacity's containing graph *is*
  the skill. Today attribution is possible only via the manifest `[l3]` list
  (capacities are not bundle-prefixed: ref bundle's cap is
  `capacity:perception:text.ref_shout`, no `ref-skill` prefix).
- Enables **reverse-drift detection** (undeclared bundle capacity in state) and
  clean per-skill enumeration/uninstall.
- Simplifies `skill verify` (this tool): attribution + drift become
  graph-membership checks instead of manifest cross-reference.

## Scope of the change (non-exhaustive)

- Rework `category_role` / `ensure_category_graph` / the identifier scheme so the
  top-level graph key is the skill, category a node attribute.
- Capacity IRI convention (`capacity:<category>:<name>`) — decide whether the
  skill enters the IRI or stays a graph-membership fact.
- Bipartite edges + `CapacityLayerView` walks (`views.py`) that currently iterate
  `capacity:` role graphs.
- Bootstrap / builtins install (builtins are "graph-less" today — decide their
  home: a `core`/`builtins` graph?).
- The finders (`pipeline.py`) that walk category graphs.
- Migration of existing category-organized state.

## Interaction with `skill verify`

`skill verify` v1 (this chat) attributes via the manifest `[l3]` list ("A"). Once
skill-as-graph ("B") lands, `verify` should switch attribution to graph
membership and add reverse-drift. Keep the `verify` check engine taking a set of
views so this is a swap, not a rewrite.
