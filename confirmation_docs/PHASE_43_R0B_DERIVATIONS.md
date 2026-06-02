# Phase 43 — R0b Derivations

> **Source:** Phase 43 pre-R0 chat 2026-06-02 (continuation post seed).
> **Status:** R0b derivations produced ahead of fresh-chat Phase 43 R0b kickoff, while context was hot.
> **Companion:** `PHASE_43_R0_PICKS_SEED.md` (locked picks); `PHASE_43_NEXT_CHAT_PROMPT.md` (spec).
> **Note:** ADR-0094 §am-1 is already drafted on disk (R0a missed it; verified at R0b — scope matches seed). Three derivations remain: `applies_after` edges, ADR-0150 §am-5 draft text, L2Schema subclass sketch.

The fresh Phase 43 chat lifts these into PR1/PR2 directly. Re-validate against any drift between this chat (2026-06-02) and Phase 39 ship state.

---

## §1. `applies_after` edge set

### §1.1 Source

D-L2-19 enumerates the 14-step v1 bootstrap order verbatim. `applies_after` is the dependency representation that yields a topological sort compatible with that order (or better, if parallelism is added later).

### §1.2 Hard edges (declared, definitionally required)

| Role-graph | `applies_after` (frozenset) | Reason |
|---|---|---|
| `ontology` | `∅` | Foundational. |
| `lexicon` | `∅` | Foundational (D-L2-19 lists no dep on ontology). |
| `concepts` | `{ontology, lexicon}` | FrameNet concepts reference both. |
| `alignment:lexicon:ontology` | `{lexicon, ontology}` | Definitional — aligns the two named roles. |
| `task-patterns` | `∅` | Admin-authored seed; no other role-graph required at bootstrap. |
| `promoted-pipelines` | `{task-patterns}` | Seed pipelines' `paired_pipelines` references seed task-patterns (D-L2-19 step 6 after step 5 + Chat A R3 D51 reachability invariant). |
| `learned-parameters` | `∅` (L2-side) | Step 7 in D-L2-19; per-subsystem v0 entries. **L3-side constraint** (hint-extractor seeds bootstrap before step 7) is **not** an L2 dependency — surfaced by D-L2-19 to L1/L3 reframe chat. |
| `capacity-gaps` | `∅` | Schema-only; empty queue at bootstrap. |
| `parameter-staging` | `{learned-parameters}` | Staging targets the promotion store; the destination must exist at the schema level for IRI prefix coherence (soft semantic, hard declaration). |
| `pending-promotions` | `{promoted-pipelines, learned-parameters}` | Shepherds candidates into both stores; targets must exist. |
| `episodic_memories` | `∅` | Schema-only bootstrap per Chat B D-B49; `memory_contains_episode` IntergraphEdge declares cross-graph type at schema time but doesn't require target role-graph to be populated at bootstrap. |
| `problem-trace` | `∅` | Schema-only; empty. |
| `capacity-state` | `∅` | Schema-only; empty. |

### §1.3 Out of L2 scope (do not declare here)

- `world-axioms` — WSD installation chat owns; not in §am-5.
- `training-runs`, `fol-rules`, `fol-ledger` — FOL installation chat owns.

### §1.4 Topological sort verification

Running Kahn's algorithm against these edges yields one valid order:

```
ontology → lexicon → concepts → alignment:lexicon:ontology →
task-patterns → promoted-pipelines → learned-parameters →
capacity-gaps → parameter-staging → pending-promotions →
episodic_memories → problem-trace → capacity-state
```

(13 named entries; matches D-L2-19's 14-step order minus `world-axioms` which is out of scope.)

Compatible with D-L2-19's enumerated order: yes (D-L2-19's step 8 `world-axioms` is absent here; everything else aligns).

### §1.5 Open question — soft edge for `episodic_memories`?

D-B47's `memory_contains_episode` IntergraphEdge references task-patterns runtime data. Declaring `episodic_memories ← {task-patterns}` would be defensible if the schema-load validator wants to assert target role-graph existence at IntergraphEdgeType registration. **Recommendation for Phase 43 R1:** declare. Cheap; gives the partition-invariant validator a complete dependency closure. If R1 surfaces concrete cost, revert to `∅`.

### §1.6 Registration shape

Per D-L2-19 cascade:

```python
# mindsos_knowledge/bootstrap.py — registration contract amendment
def ensure_<role>_role_graph(
    metagraph: Metagraph,
    *,
    extra_edge_types: Tuple[str, ...] = (),
    applies_after: frozenset[str] = frozenset(),  # NEW (Phase 43)
) -> Graph: ...
```

`applies_after` accepts role-string IRIs (not full IRIs at registration time — bootstrap is per-role-graph, not per-node). Type clarification: `frozenset[str]` where each `str` is a role name (`"ontology"`, `"lexicon"`, etc.) or an alignment-prefix form (`"alignment:lexicon:ontology"`).

---

## §2. ADR-0150 §am-5 draft

### §2.1 Scope

Per Phase 39 PB-R2-B + Chat C IL-3:

1. Add 4 new role-graphs (the row content originally in §am-4 v1).
2. Migrate the "Explicitly NOT added" exclusion list from §am-4 to §am-5.

§am-4 (post Phase 39 surgery) holds rename-only. §am-5 holds expansion + exclusion.

### §2.2 Draft text (lift into `docs/decisions/adr/0150-l2-knowledge-lifecycle.md` Revisions section)

```markdown
### amendment-5 (Phase 43 — 2026-XX-XX) — 4 new role-graph rows + exclusion list

**Trigger:** Phase 39 PB-R2-B + Chat C IL-3 (`POST_PHASE_38_PHASE_MAP.md §1` IL-3 row) split the original L2-chat single-bulk §am-4 into two surgical amendments — §am-4 holds the `memories` → `episodic_memories` rename row only (Phase 39 ship); §am-5 holds the 4-new-role-graph expansion + the exclusion list (Phase 43 ship). This split matches the §am-1 / §am-2 / §am-3 precedent of one event per amendment. See `_workbench/L2_CHAT_DECISIONS.md` D-L2-26 + `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §1` IL-3 + `confirmation_docs/PHASE_39_DESIGN_LOG.md` PB-R2-B.

**Amended behavior.**

The §Decision closed role-set expands by 4 named entries. Combined with §am-4's rename row, the post-§am-5 closed role-set is 12 named entries + alignment-prefix.

**New rows added:**

| Scope | Role | Schema builder |
|---|---|---|
| Local | `parameter-staging` | `build_parameter_staging_schema(strict)` |
| Local + Global | `pending-promotions` | `build_pending_promotions_schema(strict)` |
| Global | `capacity-gaps` | `build_capacity_gaps_schema(strict)` |
| Local + Global | `learned-parameters` | `build_learned_parameters_schema(strict)` |

Concrete schema contents per ADR-0152 §3-§6.

**Per-role-graph mutation discipline** for the 4 new roles per ADR-0153 §1:

| Role | Discipline |
|---|---|
| `parameter-staging` | `mutable_with_retention` |
| `pending-promotions` | `audit_only_after_settled` |
| `capacity-gaps` | `mutable_with_retention` |
| `learned-parameters` (Local) | `mutable_with_retention` |
| `learned-parameters` (Global) | `admin_authored` |

**Per-role-graph storage tier** per ADR-0151:

| Role | Storage mode | Notes |
|---|---|---|
| `parameter-staging` | `inline` | Small payload; staging records. |
| `pending-promotions` | `inline` | Audit chain; small. |
| `capacity-gaps` | `inline` | Observation records; small. |
| `learned-parameters` | `falkor_large_property` | `LearnedParameter.value` may be substantial (per-subsystem state). Per ADR-0151. |

**Explicitly NOT added in this amendment (migrated from §am-4):**

- `sense-correlations` — withdrawn; data lives in lexicon empirical layer per `_workbench/L2_CHAT_DECISIONS.md` D-L2-2. ALS subsystem #8 retains the name as a parameter-set label pointing at lexicon-empirical parameter key.
- `world-axioms` — WSD installation chat owns; future amendment row when WSD ships.
- `training-runs` — FOL installation chat owns per Chat A R5 D29; future amendment if FOL accepts.
- `fol-rules`, `fol-ledger` — FOL installation chat owns.

These items were originally listed in §am-4's "Explicitly NOT added" section; they migrate here per Phase 39 PB-R2-B to keep §am-4 narrowed to the rename-only surgical scope.

**Rationale.** The 4 new role-graphs are a single architectural event authored by Chat A + Chat B and closed by the L2 chat. Bulk amendment matches the per-amendment pattern. Splitting from §am-4 (rather than authoring 4 separate §am-5/6/7/8 rows) preserves the event coherence; the §am-4 / §am-5 split is between **rename** (one mechanical change touching identifiers + KL surface) and **expansion** (four schema-shape additions touching the closed role-set bound).

**Out-of-scope for amendment-5:**

* Schema field contents for each new role-graph (locked in ADR-0152 §3-§6).
* Bootstrap topological order (locked in `_workbench/L2_CHAT_DECISIONS.md` D-L2-19; Phase 43 ships the `applies_after` field per L2-37).
* `mutation_discipline` field implementation on the Schema surface — locked in ADR-0153 + Phase 43 PR1 `L2Schema(Schema)` subclass per Phase 43 R0 pick PB-43-6.
* `storage_mode` field implementation on the Schema surface — locked in ADR-0151 + same PR1 surface.

**Escape clause** (preserved from §am-4): Future role additions require new §Revisions entries citing the consumer requirement + schema builder + mutation discipline. Phase 13 sentinel test enforces.

See `confirmation_docs/PHASE_43_R0_PICKS_SEED.md` for the Phase 43 R0 pick chain + cross-references to ADR-0151, ADR-0152, ADR-0153, ADR-0094 §am-1.
```

### §2.3 Cross-reference cascade

After §am-5 lands, the following docs need verification (suggest as Phase 43 R1 grep checklist):

- `HANDOFF.md §2.2` — already states "12 → 13 after Phase 43 ships ADR-0150 §am-5." Verify.
- `CLAUDE.md` Layer 2 paragraph — verify "8 → 12 after Phase 43" matches §am-5 closed-role-set arithmetic.
- `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §4 Phase 43 row` — should already reference §am-5; verify wording.
- Phase 13 sentinel test `tests/phase_13/test_dispatch.py` — Phase 43 extends the assertion with 4 new roles + the rename row.

---

## §3. L2Schema subclass sketch

### §3.1 Module placement

**File:** `mindsos_knowledge/schemas/_base.py` (NEW)

Per Phase 43 R0 pick PB-43-6 + R0a-10 probe (zero `isinstance(.., Schema)` / `_SCHEMA_REGISTRY` / `Schema.__name__` hits across all packages). N4 pre-commit ≤20 LOC consumer-fix threshold resolves cleanly to subclass — no consumer fixes needed.

### §3.2 Enums

```python
# mindsos_knowledge/schemas/_base.py
from __future__ import annotations
from enum import Enum
from typing import FrozenSet, Optional

from mindsos_core import Schema


class Discipline(str, Enum):
    """Per-role-graph mutation discipline per ADR-0153 §1.
    
    String-valued for serialization compatibility (FalkorDB property
    storage; JSON round-trip).
    """
    IMMUTABLE_SUCCESSOR = "immutable_successor"
    APPEND_ONLY_WITH_LAZY_INLINE = "append_only_with_lazy_inline"
    MUTABLE_WITH_RETENTION = "mutable_with_retention"
    AUDIT_ONLY_AFTER_SETTLED = "audit_only_after_settled"
    ADMIN_AUTHORED = "admin_authored"
    APPEND_ONLY = "append_only"


class StorageMode(str, Enum):
    """Per-role-graph storage tier per ADR-0151.
    
    `inline` — Falkor node property storage; default.
    `falkor_large_property` — Falkor node property with chunked storage
        (e.g., LearnedParameter.value, Episode.task_input_ref large blobs).
    `blob_ref` — IRI-referenced external storage; node holds ref only.
    """
    INLINE = "inline"
    FALKOR_LARGE_PROPERTY = "falkor_large_property"
    BLOB_REF = "blob_ref"
```

### §3.3 Class

```python
class L2Schema(Schema):
    """L2 role-graph Schema with mutation discipline + storage mode declarations.
    
    Adds two L2-private metadata fields to mindsos_core.Schema:
    
    * `mutation_discipline: Discipline` — required at construction.
       Drives write-path enforcement via validate_mutation_discipline
       (load-time) + KLWriteHandle write-path body (runtime).
    
    * `storage_mode: StorageMode` — required at construction.
       Drives FalkorDB persistence layer property-vs-blob-vs-chunked
       decisions per ADR-0151.
    
    Layering: L1 mindsos_core.Schema is the structural primitive (nodes,
    edges, hyperedges, strict mode). L2Schema adds knowledge-layer
    semantics (discipline, storage tier). L1 stays primitive; L2 owns
    its own vocabulary.
    
    Per Phase 43 PB-43-6 pick (N4 probe clean — zero consumer cascade).
    Per ADR-0010 (no upward imports): mindsos_core does not import
    L2Schema; only mindsos_knowledge (and downstream) does.
    """
    
    def __init__(
        self,
        *,
        mutation_discipline: Discipline,
        storage_mode: StorageMode,
        strict: bool = False,
    ) -> None:
        super().__init__(strict=strict)
        self.mutation_discipline = mutation_discipline
        self.storage_mode = storage_mode
```

### §3.4 Schema builder migration shape

All 12 schema builders in `mindsos_knowledge/schemas/*.py` return `L2Schema(...)` instead of `Schema(...)`. Pattern:

```python
# mindsos_knowledge/schemas/promoted_pipelines.py — POST PHASE 43

from ._base import L2Schema, Discipline, StorageMode

def build_promoted_pipelines_schema(strict: bool = False) -> L2Schema:
    """Construct the promoted-pipelines role L2Schema (post ADR-0152 §1)."""
    s = L2Schema(
        mutation_discipline=Discipline.IMMUTABLE_SUCCESSOR,
        storage_mode=StorageMode.INLINE,
        strict=strict,
    )
    # ... NodeType / EdgeType registration (unchanged from Phase 13 mechanics)
    return s
```

### §3.5 Discipline + storage mode transcription table

Per ADR-0153 §1 + ADR-0151. PR1 transcribes this verbatim into the 12 schema builders.

| Role-graph | Discipline | Storage mode |
|---|---|---|
| `ontology` | `admin_authored` | `inline` |
| `lexicon` | `admin_authored` | `inline` |
| `concepts` | `admin_authored` | `inline` |
| `alignment:*` | `admin_authored` | `inline` |
| `promoted-pipelines` | `immutable_successor` | `inline` |
| `task-patterns` | `immutable_successor` | `inline` |
| `episodic_memories` | `append_only_with_lazy_inline` | `falkor_large_property` (Episode.task_input_ref) |
| `problem-trace` | `append_only` | `inline` |
| `capacity-state` | `mutable_with_retention` | `inline` |
| `parameter-staging` | `mutable_with_retention` | `inline` |
| `pending-promotions` | `audit_only_after_settled` | `inline` |
| `capacity-gaps` | `mutable_with_retention` | `inline` |
| `learned-parameters` (Local) | `mutable_with_retention` | `falkor_large_property` |
| `learned-parameters` (Global) | `admin_authored` | `falkor_large_property` |

(14 rows = 12 named role-graphs + Local/Global split on `learned-parameters` per its dual-scope nature.)

### §3.6 Per-field CONTENT_FIELDS / METADATA_FIELDS partition (PB-43-3)

For schemas with `Discipline.IMMUTABLE_SUCCESSOR`, `Discipline.APPEND_ONLY_WITH_LAZY_INLINE`, or `Discipline.APPEND_ONLY` (per ADR-0153 §3), the schema module declares per-NodeType partition frozensets alongside `*_PROPS`:

```python
# mindsos_knowledge/schemas/promoted_pipelines.py — POST PHASE 43

# Existing (Phase 13):
PIPELINE_PROPS: frozenset[str] = frozenset({
    "pipeline_name", "edge_sequence", "start_ds", "end_ds",
    "expression_metadata", "status", "n_runs", "outcome_history",
    "provenance", "quarantine_threshold", "created_at",
    "tested_at", "activated_at", "quarantined_at",
    "quarantined_by", "retired_at",
})  # NOTE: confidence dropped (ADR-0094 §am-1)

# NEW (Phase 43, per ADR-0153 §3):
PIPELINE_CONTENT_FIELDS: frozenset[str] = frozenset({
    "pipeline_name", "edge_sequence", "start_ds", "end_ds",
    "expression_metadata",
})
PIPELINE_METADATA_FIELDS: frozenset[str] = frozenset({
    "status", "n_runs", "outcome_history", "provenance",
    "quarantine_threshold", "created_at", "tested_at",
    "activated_at", "quarantined_at", "quarantined_by",
    "retired_at",
})
# Partition invariant:
# PIPELINE_CONTENT_FIELDS ∪ PIPELINE_METADATA_FIELDS == PIPELINE_PROPS
# PIPELINE_CONTENT_FIELDS ∩ PIPELINE_METADATA_FIELDS == ∅
```

`validate_mutation_discipline` enforces both clauses at L2Schema load time.

### §3.7 Validator interface

```python
# mindsos_knowledge/validators.py — additions

from .schemas._base import L2Schema, Discipline


def validate_mutation_discipline(
    schema: L2Schema,
    *,
    content_fields: Optional[FrozenSet[str]] = None,
    metadata_fields: Optional[FrozenSet[str]] = None,
    all_props: Optional[FrozenSet[str]] = None,
) -> ValidationResult:
    """L2 validator — load-time well-formedness check per ADR-0153.
    
    For disciplines requiring partition (IMMUTABLE_SUCCESSOR /
    APPEND_ONLY_WITH_LAZY_INLINE / APPEND_ONLY): verify
    content_fields + metadata_fields are declared, partition is
    complete (∪ == all_props) and disjoint (∩ == ∅).
    
    For disciplines allowing free mutation (MUTABLE_WITH_RETENTION /
    AUDIT_ONLY_AFTER_SETTLED / ADMIN_AUTHORED): partition declaration
    optional; if declared, partition invariant still checked.
    
    Returns ValidationResult(ok=bool, errors=list[str]).
    """
    ...


# Write-path enforcement — KLWriteHandle gains:

def _check_write_against_discipline(
    handle: "KLWriteHandle",
    node_iri: str,
    field_writes: dict,  # {field_name: new_value}
) -> None:
    """Raise MutationDisciplineError if writes violate discipline.
    
    Dispatched per discipline per ADR-0153 §2 (5 enforcement clauses).
    """
    ...
```

### §3.8 Exception

```python
# mindsos_knowledge/exceptions.py — addition

class MutationDisciplineError(ValueError):
    """Raised when a write violates the role-graph's mutation discipline
    (ADR-0153 §5). Carries:
    
    * role: str — the role-graph
    * iri: str — the node IRI written against
    * discipline: Discipline — the discipline violated
    * field: str — the field that violated content-vs-metadata rule
    * detail: str — human-readable explanation
    """
    def __init__(
        self,
        *,
        role: str,
        iri: str,
        discipline: "Discipline",
        field: str,
        detail: str,
    ) -> None:
        super().__init__(detail)
        self.role = role
        self.iri = iri
        self.discipline = discipline
        self.field = field
        self.detail = detail
```

### §3.9 Phase 39 interaction

Phase 39 schemas (post-rename `schemas/episodic_memories.py`) ship with `Schema` (not `L2Schema`) — they're Phase 39's deliverable. Phase 43 PR1 migrates all schema builders to `L2Schema`, including the rename target. This means Phase 43 PR1's "8 existing schema audit" includes `episodic_memories.py` (Phase 39's output) as the 8th audit row.

Bootstrap shipping order: Phase 39 (rename) → Phase 43 PR1 (L2Schema migration of all 8 schemas) → Phase 43 PR2 (4 new schemas use L2Schema from day one).

### §3.10 Sentinel test

`tests/phase_43/test_l2schema_subclass.py` asserts:

1. `L2Schema.__bases__ == (Schema,)`.
2. `L2Schema(...)` constructs only with explicit `mutation_discipline` + `storage_mode`.
3. `isinstance(L2Schema(...), Schema)` is True (subclass round-trip).
4. Each of the 12 schema builders returns `L2Schema`.
5. Each schema's declared discipline matches the §3.5 table verbatim.
6. Each schema's declared storage_mode matches the §3.5 table verbatim.

---

## §4. ADR-0094 §am-1 — already on disk

R0b verification: ADR-0094 §am-1 was authored at L2 chat closure 2026-06-01 (dated; full text on disk lines 36-94 of `docs/decisions/adr/0094-confidence-pipeline-level.md`).

Scope verification against this chat's seed picks:

| Claim | §am-1 text | Match? |
|---|---|---|
| Drop `confidence` from `promoted-pipelines` | "Pipeline-record `confidence` field DROPPED." | ✓ |
| `task-patterns.confidence` retained | (§am-1 silent on task-patterns; ADR-0152 §2 keeps it as metadata) | ✓ (silence consistent with N-now-C resolution; not a contradiction) |
| Migrator scope = promoted-pipelines only | "Any Local-Pipeline records carrying the old `confidence` property get the field stripped by a one-shot maintenance migrator" | ✓ |
| Per-run confidence on TaskRun unchanged | "Per-run output confidence remains on `TaskRun` composite in L5 intelligence-MM" | ✓ |

**No re-authoring needed.** Phase 43 PR1 reference: ADR-0094 §am-1 (already Accepted on disk).

The only Phase 43 action concerning ADR-0094 is:

- `tools/check_phase_43_confidence_state.py` detector — verify zero `confidence` properties on shipped Local-Pipeline records.

---

## §5. Phase 43 R0b status post-this-chat

| R0b item | Status |
|---|---|
| `applies_after` edge set | **Drafted (§1)**; R1 verifies §1.5 soft-edge recommendation. |
| ADR-0094 §am-1 draft | **Verified — already on disk (§4)**; no R1 action. |
| ADR-0150 §am-5 draft | **Drafted (§2)**; R1 lifts into ADR-0150 Revisions section. |
| L2Schema subclass sketch | **Drafted (§3)**; R1 implements `_base.py` + 8-schema audit + 4-new-schema authoring. |
| PR1/PR2 module-touch list | Locked in `PHASE_43_R0_PICKS_SEED.md §4`. |
| Test surface estimate | Per seed §3 step 7 (P5): ~14-18 files; parametric per-discipline test reduces nominal count. |
| Updated PHASE_43_NEXT_CHAT_PROMPT.md | Pending — seed file flags as Phase 43 R1 deliverable (alt: Stream A pre-Phase-43 edit). |

Phase 43 R1 starts from impl-locks. R0 + R0a + R0b are done.

---

*End of PHASE_43_R0B_DERIVATIONS.md. Last updated 2026-06-02 (this chat). Load alongside PHASE_43_R0_PICKS_SEED.md when opening the post-Phase-39-confirmed Phase 43 chat.*
