# CR — Learned Parameters: L3 write capacity + L4 snapshot

Status: DESIGN (approved in review chat 2026-07-28). Not yet gated.
Amends: ADR-0152 §6 (learned-parameters). NOT ADR-0203 (that is pipelines).

## Concept
`learned-parameters` is the current, per-parameter set of probabilistically
learned values (confidences / distributions / weights) the system uses as
arguments to capacities. Realm-dependent: Local (per-user) + Global. Updated,
not versioned — a re-learn overwrites in place. Every write records who/when/why.

## Layer map
- L2 (`mindsos_knowledge`): the `learned-parameters` role-graph. One node per
  parameter (data).
- L3 (`mindsos_capacity/builtins`): a WRITE capacity that learns/updates one
  parameter (mirrors `consolidate`/`dream`/`trace`).
- L4 (`mindsos_intelligence` dispatch): fills each request's
  `learned_parameters_snapshot` by reading L2 (plumbing, NOT a capacity — it
  builds the context capacities run inside, so it cannot be a capacity).

## Addressing (Option B — parameter-grained)
One node per `(parameter_set, target)`.
IRI: `learned_parameter_iri("v1", f"{parameter_set}:{target}")`
(`_FRAGMENT_RE = ^[^\s]+$` permits the colon). The IRI is opaque — never parse
it to recover set/target; the flat props are authoritative.

## Node shape (ADR-0152 §6 + provenance)
- `value`: the parameter payload (scalar or dict), `storage_mode="inline"`.
- properties: `parameter_set_iri`, `target_parameter_iri`, `confidence`,
  `applied_at`, and provenance `learned_by`, `recorded_at`, `reason`.
  `applied_from_promotion_iri` absent for direct saves (set by the future
  approval CR).

## Write capacity (L3, Local only)
Category `learning-methods`. Input DataState: record
`{parameter_set, target, value, confidence?, learned_by, reason?}`. `outputs=()`
(write terminator). Body (write-body per ADR-0180):
```
writeable = context.writeable            # None => raise (needs L4 dispatch)
h = writeable(role=ROLE_LEARNED_PARAMETERS, scope="local", version="v1")
iri = h.mint_iri("LearnedParameter", parameter_id=f"{pset}:{target}")
g = h.graph()
if iri in g.nodes: g.remove_node(iri)    # overwrite = remove + add
g.add_node(value=value, type_name=NODE_LEARNED_PARAMETER,
           properties={parameter_set_iri, target_parameter_iri, confidence,
                       storage_mode:"inline", learned_by, recorded_at, reason,
                       applied_at}, node_id=iri)
```
Rationale: `write_and_validate` cannot set properties nor overwrite (raises
IdentityError on a live id), so the body uses `graph()` directly. Overwrite is
delete+create (a fresh node at the same id), not an in-place field edit, so the
ADR-0153 §3 edit-time discipline machinery is not triggered.

## Discipline / realm
Local = `mutable_with_retention` (overwrite allowed; no retention field on this
role — "update, no history" per review). Global = `admin_authored`: L3/L4
cannot write it (`write_and_validate` blocks non-admin). System improvement of a
Global parameter => write Local + propose promotion (the SEPARATE approval CR).

## Reader (L4 plumbing) — Local overrides Global
`read_learned_parameter_snapshot(kl, user) -> {parameter_set_iri:{target: value}}`
in `mindsos_knowledge` (base layer; reachable by intelligence + server + brains).
Iterate Global metagraph then Local, keyed on `(set, target)` — Local (second)
overwrites Global per knob. Called at each `L4Dispatcher` construction
(intelligence_layer.py, boot.py) with `session.user_id`, passed as
`learned_parameters=`. Snapshot frozen per request (matches MappingProxyType).

## Reactivation invariant
These nodes carry no `reactivation_key`, so `reactivate_from_descriptors` skips
them (dict values are read as descriptors then skipped). Regression test asserts
a learned parameter is not re-activated.

## Out of scope
- Propose-to-Global + admin approval (next CR).
- nilm migration (after this CR): model its library+norm+cutoff bundle as ONE
  composite parameter (set `nilm.appliance_state`), overwrite-in-place, drop
  taught_seq, add provenance, invoke this capacity (satisfies "brain code runs
  via a capacity").
- ALS mechanism fill.

## Tests (run on Linux gate box)
overwrite=remove+add + latest-value-wins; Local-overrides-Global per knob;
provenance present; reader groups by set; snapshot-fill produces non-empty
context; reactivation walk skips a learned parameter; Global write via L3/L4
rejected (admin_authored).

## Open constraint
Gate must run on the Linux box (repo needs py3.11+; review session machine is
py3.10 + cannot reach the gate box). Deliverable lands on branch
`feat/learn-parameter`; gate is run by the maintainer.
