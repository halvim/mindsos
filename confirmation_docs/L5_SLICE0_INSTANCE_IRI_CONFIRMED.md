# L5 Slice 0 CONFIRMED — capacity_mm instance-IRI vocabulary (ADR-0201)

**Branch:** `feat/l5-slice0-instance-iri` (tip `ae49ed8`)
**Gate:** 4266 passed / 12 skipped / 1 xpassed / **0 failed** (containerized full, Linux, 32m29s, 2026-07-19)
**core_version:** stays `phase50` — additive vocabulary, no phase/role/category/count change.
**Sequences:** `confirmation_docs/CORE_WORKITEM_TASK_INTO_L5.md` Step 1 (Slice 0 of the L5 CR).

## What shipped
`mindsos_capacity/identifiers.py` only — additive:
- Three instance-IRI builders: `datastate_instance_iri(type_iri, task_id, pipeline_run_ref, seq)`,
  `capacity_instance_iri(cap_iri, task_id, pipeline_run_ref, seq)`,
  `datastate_instance_root_iri(type_iri, task_id)`. Form:
  `datastate:<type>#<task_id>.<run>.<seq>` / `capacity:<cat>:<name>#...` / `...#<task_id>.root`.
- `_sanitize_run_ref` (strip `pipelinerun:` prefix, remaining `:`→`-`) + `_require_nonempty`,
  `_datastate_type_name`, `_capacity_type_name` helpers; `_INSTANCE_SEP = "#"`.
- Type-name markers `NODE_TYPE_DATASTATE_INSTANCE` / `NODE_TYPE_CAPACITY_INSTANCE`.
- Property keys `PROP_DATASTATE_INSTANCE_TYPE` (`datastate_type`) / `PROP_CAPACITY_INSTANCE_TYPE`
  (`capacity`). `__all__` extended.

Tests: `tests/phase_47/test_instance_iri_builders.py` (26 items with phase_27) — form, run-ref
sanitization, prefix routing, and the structural type-vs-instance guard (instance IRIs must FAIL
`datastate_iri`/`capacity_iri`).

## Decisions (as built)
- **D-1 (ADR-0201):** no new `NodeInstance` subclasses — instances are plain typed nodes; Slice 0
  ships builders + markers only, no `NodeInstance` construction.
- **NODE_TYPES exclusion:** `NODE_TYPE_*_INSTANCE` are deliberately NOT members of the Core
  `NODE_TYPES` frozenset. Instances are live-only; `Graph.add_node` does not constrain node
  `type_name`; full gate green confirms no doctor/parity test requires membership.
- **Mint helper deferred to Slice 2:** a factory that constructs a typed `NodeInstance` needs a
  `template_id` + registry + metagraph (writer context) and the template-id source is an open
  Slice 2 question. Slice 0 stays pure builders + vocabulary.

## Inertness
Purely additive: zero callers today (`reads_mm` inert; no writer). The empty-room pin
(`tests/phase_47/test_chain_artifact_emit.py:79-80`) is untouched — it flips only when the Slice 2
writer lands.

## Next
Slice 1 (deep_copy independence, `mm.py`) — the first non-additive core change — must precede the
Slice 2 capacity writer. See `CORE_WORKITEM_TASK_INTO_L5.md` Steps 2-3.

**Merge sha:** _(fill after merge to main)_
