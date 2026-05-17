---
last_confirmed_phase: 12
---

# `mindsos_knowledge.REF_TYPES`

Open vocabulary for the `ref_type` property on cross-graph references.
Defined as a `frozenset` in `mindsos_knowledge/identifiers.py`. Per
ADR-0047, extension is a one-PR operation via a five-step recipe.

## Starter vocabulary

| Verb | Meaning |
|---|---|
| `SPECIALISES` | Local node is a more-specific case of the target. |
| `INSTANCE_OF` | Local node is an instance of a Global type. |
| `RENAMES` | Local node renames a Global node (alias). |
| `EXTENDS` | Local node extends a Global node with additional properties / shape. |
| `CONTRADICTS` | Local node contradicts a Global assertion. |
| `PROXY` | Local node stands in for a Global node (e.g. before promotion). |
| `PROMOTED` | Stamped on a Local draft after promotion copies it into the Global metagraph. The draft remains as a breadcrumb pointing at its new Global IRI. Added 2026-04-22 via the ADR-0047 recipe. |

## Extension recipe (ADR-0047)

1. Add to the `REF_TYPES` frozenset in
   `mindsos_knowledge/identifiers.py`.
2. Add to this page.
3. Add a test in `tests/phase_12/test_ref_types_and_roles.py` (or a
   later phase's tier).
4. Optionally update any downstream classifier.
5. Run the parity test (Phase 27+ when L3 ships its mirror per
   ADR-0067).

## L3 parity (deferred to Phase 27)

L3 imports `REF_TYPES` from L2 where feasible; ADR-0010 forbids the
import in the SessionProtocol seam case, so L3 duplicates the
frozenset verbatim and a parity test ensures the two sets stay in
sync. The parity test ships in Phase 27 (L3 DataStates + capacity
primitives), not Phase 12 — L3 doesn't exist yet to compare against.
