# ADR-0203 — Learned pipelines get a first-class Local persistence surface

**Status:** Accepted (built on branch `feat/learned-pipeline-persistence`; converged via cross-chat review in `confirmation_docs/CR_LEARNED_PIPELINE_PERSISTENCE_REVIEW.md`, pending Linux gate + merge).

Relates to: ADR-0071 (promoted-pipeline `Pipeline` + finder seam), ADR-0182 (node-value codec — reused, not amended), ADR-0150 §am-3 (one-graph-per-role; active-version routing vacated), ADR-0150 §am-5/6/7/9 (the sibling-role precedent), ADR-0152 §6 / ADR-0153 (per-role discipline + content/metadata partition), ADR-0159 §am-1 (`DAGStep`/`DAGEdge` converging DAG).

---

## Context

A brain composes a converging capacity DAG at runtime (`mindsos_capacity.pipeline.Pipeline`, the `ConjunctionFinder` output) and may teach it under a name. There was **no first-class place to persist a taught pipeline.** The only surface was `mindsos_server/pipelines.py:iter_learned_pipelines`, which read `LearnedParameter` nodes in the Local `learned-parameters` role and discriminated them by a *value-shape guess* — `"steps" in val and "target_datastate" in val`. That guess is a landmine (P3): it false-positives on any `LearnedParameter` whose value dict happens to carry those keys, and it **ignores `edges`** — so it silently degrades a converging DAG to a step bag. There was also **no writer at all** (verified: no production code writes such a node), so the reader shipped speculatively ahead of any writer, and nothing migrates.

Two brains (nilm energy-disaggregation, arc) need taught pipelines to survive a boot (F9) and appear in `mindsos brain pl`.

## Decision

**A new Local-only role `learned-pipelines` with a single NodeType `LearnedPipeline`,** mirroring the `learned_parameters` zero-edge single-type schema and the sibling-role extension mechanism the `dataset:` / subminds / installed-skills additions established. This is the native L2 extension; ADR-0152 §6 is per-role, so a sibling role does not revisit it, and A's migration cost is zero (no writer exists).

1. **Value contract — the full `Pipeline.to_dict()` as an OPAQUE ADR-0182 `_value_json` blob.** All four keys `{start_datastates, target_datastate, steps, edges}` are stored on `node.value`; the accessor is `Pipeline.from_dict(node.value)`. It is emphatically **not** an L2 per-field step schema — enumerating step internals would duplicate the shipped `DAGStep`/`DAGEdge` codec and re-expose the deferred D38 hyperedge shape. Validation is `from_dict` succeeds AND every `capacity_iri` resolves AND the DAG reaches `target_datastate`; the last two are the consumer's obligation (they need a `CapacityLayer`). The server writer additionally guards with a `from_dict` round-trip identity check before persist (refuses a lossy blob).

2. **Discipline — `immutable_successor`.** A taught pipeline is a structure, not a continuously re-estimated weight, so `mutable_with_retention` (learned-parameters' Local discipline) is wrong for it. `immutable_successor` fits with **zero new core Discipline**. Crucially, `immutable_successor` is *only a content-field immutability guard* (`validators.py`): it forbids in-place edits to content fields; it does **not** mint or link a successor, and there is **no** active-version routing to filter (vacated + locked, ADR-0150 §am-3). "Re-teach" therefore means the writer **appends** a new immutable node.

3. **Versioning — append + read-time `max(ordinal)`.** `pipeline_name` is content (frozen, set-once). A monotonic `taught_seq` is metadata (writable), stamped at write as `max(existing) + 1` over all the user's learned-pipeline nodes — the `installed-skills` append-ordinal precedent (`mindsos_server/skills/records.py`: `append_record` / `latest_records_by_bundle`) mirrored verbatim. **No `DERIVED_FROM` lineage edge** — the role stays a zero-edge mirror; cross-version provenance is deferred to a later CR. `task_patterns` exposes no factored last-active resolver to reuse (its `ordering_hint` prop is declared but unread), so the `installed-skills` records module is the pattern mirrored, not a fork of a nonexistent helper.

4. **Writer / reader.** `learn_pipeline(kl, user, name, pipeline)` appends a `LearnedPipeline` node (value = `to_dict()` blob; flat props `pipeline_name` / `taught_seq` / `recorded_at`). `iter_local_pipelines(kl, user)` scans the role, groups by `pipeline_name`, and yields the `max(taught_seq)` node per name. The writer reaches the user's Local via `kl.local_metagraph(user)` (lazy-ensures the role graph) and appends via `graph().add_node` — symmetric with the reader and matching `records.append_record`'s raw-append path (node creation is always permitted under `immutable_successor`; only in-place content edits are blocked).

5. **Reader supersession.** `iter_learned_pipelines` (the 2-key shape-guess) is **removed** — it had zero external importers; only `iter_pipelines` called it. The sole preserved contract is `iter_pipelines(scope=...)`'s `(source, node)` output (its real consumer is the CLI `brain.py pl`), which now sources the learned half from `iter_local_pipelines`.

## Consequences

- Closed role-set grows **14 → 15 named** (+ 2 prefixes unchanged). `ALL_ROLES` / `_ROLE_SCHEMA_BUILDERS` / `UPPER_LAYER_ROLES` / the `_IRI_BUILDERS` registry / the Local view count all grow by one; the count-sentinel tests are bumped accordingly.
- `learned-pipelines` is Local-only: `ensure_global_role_graph` rejects it; the Local metagraph auto-ensures it.
- Gives `pl` / persistence an unambiguous surface with a validation home at ~zero cost; kills the shape-guess structurally.
- A converging DAG round-trips losslessly through the ADR-0182 value codec (verified) — `edges` + `start_datastates` survive a save→reload (Falkor-gated integration test).
- **Follow-up (non-gated):** narrative "14 named" role counts in several `docs/**` concept/overview files remain to be bumped to 15; the CI ADR-status guard does not check these prose counts. `CLAUDE.md`'s status line is updated here.

## Alternatives considered

- **B — keep `LearnedParameter`, add a typed value schema + `kind` discriminant.** Smallest surface, and its discriminant also removes the shape-guess. Rejected: keeps two disciplines in one role and inherits `mutable_with_retention`; its "no migration" edge is null since A has none either.
- **C — extend the promoted `Pipeline` (ADR-0071) to Local.** Rejected now: couples the denormalized learned value to the normalized `HAS_STEP` graph partition whose shape is in flux pending the D38 capacities-as-hyperedges reframe.
