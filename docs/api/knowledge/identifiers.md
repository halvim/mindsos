---
last_confirmed_phase: 12
---

# `mindsos_knowledge.identifiers`

Phase 12 ships the L2 IRI vocabulary: 14 builders covering ADR-0045,
a graph-name helper for alignment metagraphs, a table-driven parser,
role constants, and ref-key helpers. The module is **pure library** —
no L1 mutation, no metagraph, no persistence. KL writes are relocated
to L3 capacities per the L2 redesign locks 2026-04-27.

## Version-qualified IRI shape

Every L2 node IRI is **version-qualified**:

```
<source>-<version>:<rest>
```

The version is part of the prefix so multiple versions of the same
source can coexist in one Global Metagraph. Examples:

| Builder | Output |
|---|---|
| `dolce_iri("4.0", "PhysicalObject")` | `dolce-dul-4.0:PhysicalObject` |
| `oewn_synset_iri("2024", "01234567", "n")` | `oewn-2024:synset:01234567-n` |
| `framenet_frame_iri("1.7", "139")` | `framenet-1.7:frame:139` |
| `pipeline_iri("1", "abc")` | `promoted-pipelines-1:pipeline:abc` |
| `memory_iri("1", "alice", "m-001")` | `memories-1:memory:alice:m-001` |
| `capacity_snapshot_iri("1", "u", "capacity:cat:n", "2026-05-16")` | `capacity-state-1:snapshot:u:capacity:cat:n:2026-05-16` |

`alignment_role(role_a, role_b)` is the only non-IRI helper — it
returns a **graph name** like `alignment:lexicon<->concepts`. The
parser rejects it.

## Roles

| Role | Constant | Tier | Source prefix |
|---|---|---|---|
| `ontology` | `ROLE_ONTOLOGY` | seed | `dolce-dul-` |
| `lexicon` | `ROLE_LEXICON` | seed | `oewn-` |
| `concepts` | `ROLE_CONCEPTS` | seed | `framenet-` |
| `promoted-pipelines` | `ROLE_PROMOTED_PIPELINES` | upper | `promoted-pipelines-` |
| `task-patterns` | `ROLE_TASK_PATTERNS` | upper | `task-patterns-` |
| `memories` | `ROLE_MEMORIES` | upper | `memories-` |
| `problem-trace` | `ROLE_PROBLEM_TRACE` | upper | `problem-trace-` |
| `capacity-state` | `ROLE_CAPACITY_STATE` | upper | `capacity-state-` |

Three frozensets group the roles:

```python
SEED_ROLES        = {ROLE_ONTOLOGY, ROLE_LEXICON, ROLE_CONCEPTS}
UPPER_LAYER_ROLES = {ROLE_PROMOTED_PIPELINES, ROLE_TASK_PATTERNS,
                     ROLE_MEMORIES, ROLE_PROBLEM_TRACE,
                     ROLE_CAPACITY_STATE}
ALL_ROLES         = SEED_ROLES | UPPER_LAYER_ROLES
```

## Charset contracts

* **Version** matches `^[A-Za-z0-9][A-Za-z0-9._-]*$`.
* **Fragment** matches `^[^\s]+$` (non-whitespace; colons allowed —
  see `capacity_snapshot_iri`'s opaque body).
* **`user_id`** matches `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$` (PB-11 +
  ADR-0044 §amendment-1). Phase 18 server user-store inherits this
  invariant.

All builders raise `RefFormatError` on violation.

## Parser

`parse_iri(iri) -> ParsedIri` decomposes a version-qualified IRI into:

```python
@dataclass(frozen=True)
class ParsedIri:
    role:    str            # one of ALL_ROLES
    source:  str            # e.g. "dolce-dul" / "memories"
    version: str            # e.g. "4.0" / "1"
    kind:    Optional[str]  # e.g. "synset" / "memory" / None (DOLCE)
    body:    str            # remainder
    full:    str            # the original IRI
```

Kind extraction is driven by `_KINDS_PER_ROLE`. Roles absent from the
table (currently `ROLE_ONTOLOGY` only) get `kind=None` and `body=rest`.

`capacity_snapshot_iri` bodies hold embedded colons (the inner
`capacity_iri` per ADR-0066 plus the ISO8601 `taken_at`). The parser
leaves the post-`snapshot:` body opaque; field-level decomposition is
deferred to the first consumer (Phase 28+).

`is_version_qualified_iri(value) -> bool` is a no-raise probe over the
same parser.

## Ref-key helpers + REF_TYPES

```python
global_ref_key("lexicon")   == "ref:global_lexicon"
local_ref_key("ontology")   == "ref:ontology"
REF_TYPE_KEY                == "ref_type"
```

`REF_TYPES` is the starter open vocabulary from ADR-0047:

```
{SPECIALISES, INSTANCE_OF, RENAMES, EXTENDS, CONTRADICTS, PROXY, PROMOTED}
```

L3 ships a duplicate frozenset and a parity test in Phase 27
(ADR-0067 deferred per PB-3).

## Carry-forward owed

* **REF_TYPES parity test against L3** → Phase 27.
* **Per-edge alignment IRI builder** (if Phase 14 needs one) → Phase 14.
* **Per-builder inverse field helpers** (capacity_snapshot, pipeline,
  task_pattern, memory, problem_trace) → per-consumer phase.

See `confirmation_docs/PHASE_12_DESIGN_LOG.md` §4 for the full list.
