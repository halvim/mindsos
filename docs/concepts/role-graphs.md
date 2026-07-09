# Role-graphs

L2 Knowledge content is partitioned across **role-graphs** — each a typed graph with a fixed schema, registered in a Metagraph by its role name. ADR-0044 (Local-per-user invariant), ADR-0150 (closed role-set + lifecycle), ADR-0152 (schema-v2), and ADR-0153 (mutation discipline) define the contract.

## v2 closed role-set

**14 named role-graphs** + an alignment-prefix family (`alignment:<a>:<b>`). Each carries an `L2Schema(Schema)` instance declaring its `mutation_discipline` per ADR-0153 §1. The set grew 8 → 12 (Phase 43, ADR-0150 §am-5) → 13 (Phase 50, `installed-skills`, ADR-0150 §am-6) → 14 (`subminds`, ADR-0150 §am-7).

| Role | Scope | Discipline | NodeTypes | Purpose |
|---|---|---|---|---|
| `ontology` | Global | `admin_authored` | DOLCE + full-OWL hierarchy | Foundational categories. |
| `lexicon` | Global | `admin_authored` | OEWN three-level (Lemma / Sense / Synset) | Lexical knowledge. |
| `concepts` | Global | `admin_authored` | FrameNet (Frame / FE / LU / SemanticType) | Conceptual frames. |
| `alignment:<a>:<b>` | Global | `admin_authored` | `AlignmentAnchor` (parametric) | Cross-role mappings. |
| `promoted-pipelines` | Global | `immutable_successor` | Pipeline + PipelineStep | Promoted procedural skills. |
| `task-patterns` | Global | `immutable_successor` | TaskPattern + SubgoalTemplate | Task structure + paired-pipelines source-of-truth. |
| `problem-trace` | Global | `append_only` | ProblemTraceEntry | Failure records. |
| `capacity-state` | Local | `mutable_with_retention` | CapacitySnapshot | Per-user capacity state. |
| `episodic_memories` | Local | `append_only_with_lazy_inline` | Episode + Memory | Per-task entries + clustering composites. |

**Phase 43 additions (ADR-0150 §amendment-5):**

| Role | Scope | Discipline | NodeTypes | Purpose |
|---|---|---|---|---|
| `parameter-staging` | Local | `mutable_with_retention` | StagedEvidence | ALS evidence-staging buffer (D-L2-11). |
| `pending-promotions` | Local + Global | `audit_only_after_settled` | PendingPromotion | ALS promotion proposals + audit chain (D-L2-13). |
| `capacity-gaps` | Global | `mutable_with_retention` | CapacityGap | Unsolvable-task + promotion-candidate gaps (D-L2-14). |
| `learned-parameters` | Local + Global | Local: `mutable_with_retention` / Global: `admin_authored` | LearnedParameter | ALS parameter assignments (D-L2-15); `value` carries `storage_mode` per ADR-0151. |

`learned-parameters` is the sole Phase 43 dual-scope role with per-scope discipline split. Other dual-scope roles (`pending-promotions`) share the same discipline across scopes.

**Phase 50 + SubMind additions (ADR-0150 §am-6, §am-7):**

| Role | Scope | Discipline | NodeTypes | Purpose |
|---|---|---|---|---|
| `installed-skills` | Global | `append_only` | SkillInstallRecord | One action record per skill install/uninstall/failure (ADR-0183); current state = latest record per `bundle_name`. First production consumer of the ADR-0182 `_value_json` round-trip. |
| `subminds` | Global (Local designed, Slice 1 Global-only) | `admin_authored` | SubMindDefinition | Durable endowment record for an autonomous no-reasoning reflex (ADR-0188/0190); runtime lives in `mindsos_intelligence`. |

## Excluded names (NPB14-4 regression guard)

Five role names are explicitly NOT in the closed v1 role-set and MUST NOT be added without an ADR-0150 amendment:

- `sense-correlations` — withdrawn per D-L2-2; data lives in lexicon empirical layer; ALS subsystem #8 retains the name as a parameter-set label only.
- `world-axioms` — WSD installation chat owns; future amendment when WSD ships.
- `training-runs` — FOL installation chat owns per Chat A R5 D29.
- `fol-rules` + `fol-ledger` — FOL installation chat owns.

The Phase 13 sentinel test `tests/phase_13/test_dispatch.py` enforces closure (14-entry exact-set check on `_ROLE_SCHEMA_BUILDERS`).

## Cross-references

- Mutation discipline: see [`mutation-discipline.md`](mutation-discipline.md).
- Storage tiers: see [`storage-tiers.md`](storage-tiers.md).
- Role-graph schemas: `mindsos_knowledge/schemas/`.
- Role dispatch: `mindsos_knowledge.schemas.schema_for_role(role, strict=False)`.
- IRI builders: `mindsos_knowledge.identifiers` (one per role + the alignment graph-name helper).
