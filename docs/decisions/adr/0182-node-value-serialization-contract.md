---
title: Node-value serialization contract for structured values
status: Accepted
date: 2026-06-09
accepted_date: 2026-06-09
layer: L0
related: [0130, 0160, 0161, 0176, 0181]
---

# ADR-0182: Node-value serialization contract for structured values

**Status:** Accepted (decide-and-document — implementation lands with its first consumer; see §Consequences)

**Date:** 2026-06-09 (MAINTENANCE_CHAT M3; L0-26)

**Related:** ADR-0130 (`_props_json` property bag on Metagraph/Graph anchors — the encoding precedent this ADR extends to node values), ADR-0160 (FalkorDBLocalPersister native round-trip — the persister this contract binds), ADR-0161 (reserved property keys), ADR-0176 (consolidation — the 6-field Episode `value` dict that surfaced the gap), ADR-0181 (Falkor index strategy — the queryability rule below keeps its indexed fields flat).

## Context

The L0 node persister stores node `value` as a **primitive**:
`mindsos_core/cypher/builders.py::build_unwind_create_nodes` emits
`SET n.value = row.value` (docstring: *"value (any primitive)"*), and FalkorDB
node properties accept primitives/arrays only. ADR-0130's `_props_json`
JSON-encodes **metagraph** `.properties` onto the `:Metagraph` anchor only —
node values and node props pass through raw.

Phase 49 Integration C surfaced the consequence (**PB-RT**,
`PHASE_49_DESIGN_LOG.md` §9): the L5 **Episode** node's `value` is a structured
6-field dict (Chat B D-B47, assembled in `mindsos_intelligence/consolidation.py`),
so `FalkorDBLocalPersister.save` of an episode-bearing Local errors against
FalkorDB. **v1 Episodes are therefore not durably persisted** — they live in
the in-memory Local. Phase 49 descoped the live episode flush (PB-RT-a) and
routed the gap here as **L0-26**.

The same gap blocks the next consumers in line: **SKILL_ACQUISITION**'s
install-provenance and bundle-manifest records (structured, document-shaped,
written once, read whole) need durable round-trips through the same persister.
SKILL_ACQUISITION's R0 must design against a **fixed serialization contract**
— hence decide-and-document now (ADR-0181 precedent), implement with the first
consumer (consumer discipline, Phases 39–49; Phase 44 CR-2 precedent).

DWF installation ingests against the persister contract this ADR amends; it is
sequenced after this ADR lands (downstream-plan revision 2026-06-09).

## Decision

**Option 1 — extend the ADR-0130 JSON-encoding pattern to node values**, via a
node-level `_value_json` column. The contract:

1. **Primitive values are unchanged.** When `value` is a JSON primitive
   (`str | int | float | bool | None`), persist emits `n.value = row.value`
   exactly as today. No migration; existing rows are untouched; the loader's
   existing path is the fast path.
2. **Structured values JSON-encode.** When `value` is a `dict` or `list`,
   persist emits `n.value = NULL` + `n._value_json = json.dumps(value)`
   (the same encode discipline as `MetagraphRepository._encode_props_json`,
   including the narrow chained driver-exception wrap for oversized strings).
3. **Decode at load.** The node loader treats the presence of `_value_json`
   as the discriminator: decode and assign as `value`; otherwise read
   `n.value`. `_value_json` joins the loader's reserved-key filter
   (`graph_loader.py` reserved set) and `RESERVED_PROPERTY_KEYS`
   (ADR-0161) so user props can never collide with it.
4. **The contract bound is JSON-encodability.** A non-JSON-encodable `value`
   raises `PersistenceError` at the persist boundary — fail loud at save, not
   at load.
5. **Queryability rule (writer's obligation).** A JSON-encoded value is opaque
   to Cypher filtering and to the ADR-0181 index strategy. Any field that must
   be queryable/indexable MUST be lifted by the **writer** into a flat
   primitive node property (e.g. the Episode writer lifts `task_pattern_iri`
   so ADR-0181 index 1 — `(e:Episode) ON (e.task_pattern_iri)` — has a flat
   property to index). The serialization layer does no automatic lifting.
6. **Node props are out of scope.** The shipped node-prop validator
   (`validate_user_properties`) admits primitives only, so structured node
   *props* cannot occur today. If a future consumer needs them, extend this
   contract (node-level `_props_json`) by amendment — do not improvise a
   second encoding.

### Rejected options (per L0-26)

- **Decomposed primitive-valued nodes** — explode each structured value into a
  subgraph of primitive nodes + edges. *Reject:* bespoke encode/decode schema
  per record type (Episode now; bundle-manifest, install-provenance next — a
  new decomposition design each time); retroactively reshapes the shipped
  D-B47 Episode; turns a serialization question into an ontology question.
- **Dedicated blob store** — episodes/manifests to a SQLite or file blob store
  keyed by IRI. *Reject:* splits a user's Local across two stores, breaking
  ADR-0160's core property (the Local is ONE Falkor metagraph; native
  round-trip; scoped single-store delete — the M2/L0-25 live tests pin
  exactly this). Also drifts into the Phase-48-deferred durable checkpoint
  store, which is explicitly out of this ADR's scope.

## Rationale

- One generic mechanism covers every structured-value consumer (Episode,
  bundle manifest, install provenance, future L4/L5 records) with zero
  per-record design work — the marginal cost of the *next* structured value is
  nil.
- Symmetric with the codebase's own precedent (ADR-0130 `_props_json`):
  reviewers and the loader already know the pattern; the reserved-key
  machinery already exists.
- Backward-compatible by construction (rule 1): no data migration, no
  detector, no version bump pressure on the read path.
- The queryability cost is real but already paid: ADR-0181 chose named flat
  properties as the index surface; rule 5 makes the dependency explicit
  instead of accidental.

## Consequences

- **Implementation owner: SKILL_ACQUISITION phase-map slot 1** (trivial-bundle
  reference install — the first consumer that must durably round-trip a
  structured value). Surface: `build_unwind_create_nodes` (+ its row-assembly
  caller in `graph_repository.py`) + the node loader decode + reserved-key
  roster + unit/live tests (extend `tests/maintenance/
  test_l0_25_falkor_local_persister_live.py` with a structured-value
  round-trip case when the implementation lands).
- **Durable Episode persistence** (the PB-RT consequence) rides this contract
  but is driven by the v1.5 durable-retention work (Phase-48-deferred durable
  Falkor checkpoint store). This ADR fixes the *contract*, not the store.
- **L0-26 closure marker:** "ADR-0182 on disk; impl routed to
  skill-acquisition slot 1."
- **Reversal trigger.** If SKILL_ACQUISITION R0 finds bundle manifests need
  field-level Cypher queries over their interiors (not just lifted flat
  fields), re-open the decomposed-nodes option for that record type only —
  the `_value_json` mechanism remains for non-queried structured values.
