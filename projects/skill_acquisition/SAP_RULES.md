# SAP Rule Catalog — v0.1 (from MindsOS code)

The ordering + obligation rules the SAP backend enforces. Extracted from shipped MindsOS invariants —
sources cited. **Backend = this catalog + a `kahn_sort` resolver** (reuse `mindsos_knowledge/bootstrap.py`).

## Classification (the entry rule)

- **CL1** — every ontology class must be classified as exactly one of: **datastate** | **capacity** |
  **relation** (edge/constraint) | **meta** (no node — e.g. Predicate, Transform, Abstain) | **param**
  (fixed — e.g. Connectivity). Each classification triggers the obligations below. *(Not "class → cap|datastate".)*

## DataState

| # | Rule | Source |
|---|---|---|
| DS1 | name = `<realm>.<name>`, single dot only | capacity_layer.py:234–244 |
| DS2 | realm ∈ RESERVED_REALMS unless `allow_new_realm` (admin) | :245–250 |
| DS3 | IRI unique per metagraph | :258–262 |
| DS4 | valid shape (DataState type · non-empty name · ShapeDescriptor) | datastate.py:153–159 |
| DS5 | every **derived** datastate needs ≥1 producing capacity (provenance); only the ground has none | grounding-invariant + ADR-0156 |

## Capacity  (registration order + contract)

| # | Rule | Source |
|---|---|---|
| **C1** | **its input + output datastates must be registered *first*** (else "unknown DataState IRIs") | capacity.py:121–125 · capacity_layer.py:345 |
| C2 | registration emits `PRODUCES` (cap→out) + `CONSUMES` (in→cap) edges | ADR-0156 · :402–422 |
| C3 | capacity IRI unique (`if_exists="raise"`) | :372–377 |
| C4 | IRI must not collide with a node id in its category graph | :388–392 |
| C5 | must belong to a **family/category**; the family fixes its don't-know shape | family_rules.py (FAMILY_RULES) |
| C6 | `inline=True` ⇒ `max_latency_ms` required | :434 |
| C7 | `input_group` ∈ INPUT_GROUPS; multi-input = `all_required` \| `any_of` | :440 · capacity.py:86 |
| C8 | `precondition_iri`/`effect_iri` must be capacity IRIs resolving to the `predicate` family | :446–463 |
| C9 | no reserved property keys in extras | :352 |
| C10 | a Local capacity may reference Global datastates (mirrored in) | ADR-0185 · :330–344 |

## Relations / constraints

| # | Rule | Source |
|---|---|---|
| RL1 | CONSTRAINT `kind` ∈ CONSTRAINT_KINDS; both endpoints registered; **same category** (no cross-category) | capacity_layer.py:483–503 |
| RL2 | **no higher-order dispatcher** — a capacity never selects/calls another capacity via the layer | GF-2 (ONTOLOGY §3) |

## Role-graph (L2)

| # | Rule | Source |
|---|---|---|
| L2-1 | role must be in the **closed set** (else `UnknownRoleError`); a new role = code release + ADR-0150 §am | knowledge/bootstrap.py:316 |

## Ordering / bootstrap

| # | Rule | Source |
|---|---|---|
| O1 | `applies_after` declares creation order; `kahn_sort` topo-orders; cycle → `BootstrapCycleError` | knowledge/bootstrap.py:175–211 |
| O2 | within a unit: L2 content → L3 datastates → L3 capacities → L4 | install log S7 |

## Net dependency chain (what the resolver enforces)

`ground datastate → (derived datastates ← their producer capacities, C1) → capacities (families C5, edges C2) → relations/constraints (RL1) → L4`. Everything topo-ordered by O1; RL2 + DS5 are global invariants checked after.
