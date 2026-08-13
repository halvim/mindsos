# ADR-0201 — Amendment 4: the run manifest, and where it is minted

**Status:** Accepted (2026-08-13). Records `decision-records-run-manifest`
(shipped, PR #153) and `decision-records-map-manifest` (this CR), which corrects
where the node is minted and completes its contents.

## Context

ADR-0201 defines the capacity-MM instance vocabulary: `CapacityInstance`,
`DataStateInstance`, `PRODUCES`/`CONSUMES`, and (with the terminal-node CR)
`RunStopped`. A Decision Record is rendered **from that graph and nothing
else**, and probe D established by sketching a renderer over four real run
graphs that exactly three symbols cannot be turned into prose from it:

1. **Which values were given.** A parentless `DataStateInstance` is
   structurally identical to one whose producer was deleted. The mutation proof
   was a page printing *"Given: a return must be filed"* — a derived conclusion
   silently reclassified as a premise.
2. **What decided.** A `CapacityInstance` carries a capacity IRI and nothing
   else, and the criterion writes no origin record (ADR-0208 D3).
3. **Why a run stopped.** `RunStopped.value` is a token, and a renderer that
   translated a token itself would be a hand-maintained mirror of a closed set
   core can change.

PR #153 added a fourth node type, **`RunManifest`**, to carry those three — and
shipped it **without amending this ADR**, which is the vocabulary's home. This
amendment records the node, and corrects two things #153 got wrong.

## Decision

**A `RunManifest` node is part of the per-run capacity graph.** Exactly one per
run, at a deterministic IRI (`run_manifest_iri(request_id, run_ref)`), mirroring
`RunStopped` so *"one per run"* is a structural fact rather than a count that
could drift. Its contents live in the node's **value**, as a dict:
`Graph.add_node` routes `properties` through `validate_user_properties`, which
accepts primitives only, and every field is a collection.

It is deliberately **not** a `DataStateInstance`, so the parentless-set guard
(G7) does not count it.

### Contents

| field | meaning |
| --- | --- |
| `declared_starts` | DataState IRI → its **registered description**, for every value the run was given |
| `capacity_phrases` | capacity IRI → its registered `printable_phrase` (ADR-0207 am-1), for exactly the capacities this run composed |
| `stop_reason_phrases` | the closed run-stopped set, in full, always |
| `case_label` | optional, caller-supplied prose: what this run is **about** |

`declared_starts` maps to phrases, **not to nothing**. Bare IRIs were #153's
first version and they printed straight onto the no-route page — where the
starts are the only thing there is to say, so the leak lands on the one page
with nothing else to dilute it. The mapping is also what makes a parentless
`DataStateInstance` decidable: inside the set it is a premise the run was given;
outside it, a gap where a producer should have been.

**A start with no registered description maps to `None`, never to its own
IRI.** The IRI was this CR's own first fallback and it is wrong for the reason
the mapping exists at all: it re-inserts bare IRIs on exactly the runs that have
no prose to dilute them. `None` cannot leak and is unambiguous — a renderer
reads *"given, and we have no words for it"*, which it must say rather than
paper over. **The key is still present**, which is the structural half: the
start stays inside the declared set, so a parentless instance is still decidable
as a premise rather than as a gap.

`capacity_phrases` is a **snapshot**, deliberately. ADR-0207 amendment 1 rejects
reading the phrase from the catalog at render time: the catalog is mutable and
separately persisted, so an archived Episode would render prose that has since
changed, with no drift signal.

`stop_reason_phrases` is written unconditionally, because whether a run will
stop is not known when the manifest is minted.

`case_label` is **never invented by core.** Which of a consumer's cases a run is
belongs to the consumer. A request id or a member index is an identifier, not a
label a reader can be shown. Absent is recorded as `None` rather than as a
missing key, so a renderer can tell *"this run carried no label"* from *"I could
not read the label"*. It exists because several Records derived from one claim
are otherwise indistinguishable on the page.

### Correction 1 — minting moves into `execute_pipeline`

#153 minted the manifest in `execution._run_leaf_pipeline`. **That is one of two
run paths.** A map member runs through `_run_member_pipeline`, which minted
nothing, so every map member's grounding graph had no manifest at all — while
#153's ship note certified *"every run leaves a graph"*.

Minting moves into **`execute_pipeline`**, the one function both paths call, so
*"every graph carries a manifest"* is a property of the executor rather than of
whichever caller remembered. It is minted **before any other node**, which is
also what makes an unroutable run renderable (below).

`declared_starts` is keyed on what was actually **seeded**, not on
`pipeline.start_datastates`: a seeded value is exactly what becomes a parentless
`DataStateInstance`, and a declared start with no value mints no node, so naming
it would promise a renderer a premise that is not in the graph.

Found by **running** a three-member map and counting what came out — 3 graphs,
3 `CapacityInstance`s each, 0 manifests — not by reading the code.

### Correction 2 — the no-route graph, on both paths

`_compose_pipeline` raises `LeafPipelineNotFound` before anything is written, so
an unroutable request left **no graph at all** — not even a `RunStopped` — and
the only renderable artifact was a caught exception. #153 fixed that for the
leaf path by hoisting a writer above the find. The member path was left as it
was: an unroutable member left nothing, and the `MemberAbortError` that followed
took the whole request's Record with it.

Both paths now call one helper, `execution._mint_no_route_graph`, which leaves a
**manifest-only** graph and re-raises. The route really is unfindable and
pretending otherwise would be worse; what changes is that there is something to
render. On that page `capacity_phrases` is empty — a manifest that named a
capacity would be claiming an execution that did not happen — and
`declared_starts` is what the run was **asked** for, since no pipeline exists to
read starts from.

### Correction 3 — `runstopped:` and `runmanifest:` had no room

`MentalModel.sub_mm_for_iri` routes a node IRI to its sub-MM **by prefix**, and
instance IRIs keep the `datastate:` / `capacity:` prefix *only* so that routing
works (this ADR, §Instance-IRI vocabulary). The terminal node (`runstopped:`)
and the manifest (`runmanifest:`) each invented a new top-level prefix and
**joined no table**: `sub_mm_for_iri` raised `KeyError` on either — a node
sitting inside a capacity run graph that the router said belonged nowhere.

Neither had ever met the router. `RunStopped` is written only on a non-success,
and the guard that walks every node of a run graph
(`test_minted_instance_iris_route_to_capacity_mm`) only ever sees a **successful**
run. The manifest was minted a layer above `execute_pipeline`, so that guard
never saw one either. Moving the mint into the executor reddened it immediately,
and the sibling was one line away.

Both prefixes now belong to `CAPACITY_PREFIXES`, and both are driven — at the
table *and* over real graphs, because a prefix table agreeing with itself is not
evidence that anything routes.

## Scope / not in this amendment

- **No renderer.** The manifest is what a renderer will read; nothing in core
  renders anything, and a page shown to anyone remains out of core.
- **No persistence change.** The manifest is a node in the per-run graph that
  Amendment 2 made the persistence unit, so it travels with it.

## Consequences

- `execute_pipeline` gains one optional keyword, `case_label`. Every existing
  caller is unchanged and records `None`.
- `execution.run` threads `case_label` to every manifest it mints — leaf,
  member, and no-route alike.
- `CapacityMMWriter.manifest` takes `Mapping[str, str]` for `declared_starts`,
  not a sequence of IRIs. The two phrase snapshots (`capacity_phrases`,
  `start_phrases`) live beside the writer rather than in the executor, because
  both run paths and the no-route path need them — duplicating them in the
  executor is how the member path came to have no manifest in the first place.
- `core_version` unchanged — L5-side code, no core-package/role/category change.
