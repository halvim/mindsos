# Skill-as-graph L3 reorganization — design seed (deferred "B")

Status: **KEPT-DEFERRED (ratified 2026-08-11).** Not on the active queue. Owned by
the main SAP lane from here.

> **2026-08-11 reanalysis vs current main — read this before acting on the body below.**
>
> Re-decided after re-checking the code. The conclusion is **keep-deferred, do not build**, on stronger grounds than "not started":
>
> - **L3 is reactivate-from-code, not persisted.** `boot_brain` rebuilds capacities each boot by re-running each installed bundle's installer (`apply_installed_skills`); the durable install fact is the L2 `installed-skills` ledger, which records each bundle's `l3_capacities` roster. A per-skill L3 graph would only be an in-memory copy each boot of what the ledger already states durably — **zero durable gain.**
> - **Attribution/enumeration/reverse-drift need no L3 change.** Build `{IRI → bundle}` from the ledger rosters; unrostered-registered (and non-builtin) = reverse drift. **Forward-drift already shipped** (`mindsos_server/skills/activation.py::_warn_missing_declared_capacities`, ADR-0183 §am-2) using exactly this substrate.
> - **The reorg is high blast-radius for no payoff:** it changes the registration contract (declarations carry no `bundle` today), the bootstrap (builtins have no skill → unsolved home graph), forces a state migration of every bipartite edge's source graph_id, and collides with the IRI/family-rule coupling — **category is baked into every capacity IRI** (`capacity:<category>:<name>`, parsed back by `family_rules.py`), so the seed's "category becomes just a tag" cannot be cleanly honored.
> - **Payoff #1 in the body ("attribution becomes structural — the containing graph IS the skill") rests on a false premise** (L3 as durable home) — disregard it. **Scope list below is overstated:** finders (`pipeline.py`) and views walk bipartite edges by node_id, so they're organization-agnostic; `catalog_check` is already bundle-agnostic.
> - **Sole reopen trigger:** L3 becoming persisted-at-rest **AND** a live in-process uninstall requirement (uninstall-without-restart). Neither exists. Absent both, do not open this.
>
> The original seed is retained below for history.

Original status: **not started.** Surfaced during the `skill verify` design chat.

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
