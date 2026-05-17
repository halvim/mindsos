# Phase 12 — Design Log

> Captured at chat opening (2026-05-16). Records all design pushbacks
> (PB-1..22) and the locks each produced. Future amendments to
> ADRs 0044 / 0045 / 0047 / 0067 should consult this file for rationale.

## 0. Scope at chat-open

PHASE_MAP §12 (pre-correction) read: "L2-aware IRI parse (extends Phase 02);
IRI build by role; REF_TYPES list. Tests: dolce / oewn / framenet /
alignment IRI builders round-trip; REF_TYPES parity test against L3
(ADR-0067). Risks: REF_TYPES extension recipe (ADR-0047) must not be
loosened. Docs: docs/api/knowledge/identifiers.md, ref-types.md,
ADRs 0045/0047/0067." Deps: 02. Layer: L2. Net-new: No.

Pre-design inventory revealed five mismatches:

* PHASE_MAP §12 scope undershoots ADR-0045 (which declares 7 upper-layer
  builders never shipped in v3).
* `mindsos_knowledge` package does not exist in `halvim_mindsos/` —
  Phase 12 is the first L2 phase; package creation is implicit but
  unnamed in the row.
* "REF_TYPES parity test against L3" cannot run in Phase 12 — L3 ships
  Phase 27.
* "alignment IRI builders" is ambiguous: v3 `alignment_role()` returns
  a graph name, not a version-qualified IRI.
* Phase 11 carry-forward (MetagraphSchema scanner / ADR-0134
  Proposed → Accepted flip / migration playbook) does NOT fire in
  Phase 12 — no metagraph, no schema, no importer.

These mismatches drive PB-1 / PB-2 / PB-3 / PB-4 / PB-5.

## 1. Design pushbacks (PB-1..22)

Four rounds of pushbacks. Each lists the question, the options
considered, and the lock. User agreed all picks (option A on every
shaper PB; specific picks called out below).

### PB-1 — `mindsos_knowledge` package creation missing from PHASE_MAP §12

Phase 12 is the first L2 phase. No `mindsos_knowledge` package exists
in `halvim_mindsos/` today. PHASE_MAP §12 row + Phase 11 carry-forward
silent on this. Per `feedback_new_top_level_package.md` this is a
5-site checklist (pyproject + Dockerfile prod+test + sentinel paths +
doctor parity + host pip refresh) plus a 6th site
(`feedback_dockerfile_test_stage_file_reads.md`). Doctor flips from
3-pkg to 4-pkg version-string parity.

**Lock: A — package creation is Phase 12 net-new infra.** Sequenced
first in step list, before any IRI code.

### PB-2 — PHASE_MAP §12 scope undershoots ADR-0045 (Accepted)

ADR-0045 declares 14 IRI builders total: 7 v3-shipped (seed roles) +
7 upper-layer (`pipeline_iri`, `pipeline_step_iri`, `task_pattern_iri`,
`subgoal_template_iri`, `memory_iri`, `problem_trace_iri`,
`capacity_snapshot_iri`). PHASE_MAP §12 Tests only names "dolce /
oewn / framenet / alignment." Upper-layer builders exist only in
`_source_backup/docs_legacy_full/DESIGN_UPPER_LAYER_ROLES.md` —
never shipped. ADR-0045 is Accepted and partially implemented.

**Lock: A — ship all 14 builders in Phase 12.** Honors ADR-0045 as
written. `memory_iri` includes `user_id` per ADR-0044. ~30 extra
tests; cost is small (1-line builders + 1 round-trip test each).
Pre-builds the parser kind-table for Phase 14+ consumers.

### PB-3 — REF_TYPES parity test against L3 cannot run in Phase 12

L3 ships Phase 27. ADR-0067 says L3 imports REF_TYPES from L2
"where feasible, or duplicates the frozenset verbatim with a parity
test when layer isolation forbids the import." ADR-0010 forbids the
import. Parity test is a Phase 27 obligation, not a Phase 12 one.

**Lock: A — defer parity test to Phase 27.** Phase 12 ships REF_TYPES
+ self-consistency test only. Note in the Phase 12 row that Phase 27
owes the parity test.

### PB-4 — "alignment IRI builders" wording ambiguous

v3 `alignment_role(a, b)` returns `"alignment:lexicon<->concepts"` —
a graph name, not a version-qualified IRI. `parse_iri` rejects it
(no recognised source prefix, no version).

**Lock: A — `alignment_role()` is a graph-name helper.** Port verbatim.
Round-trip test = `parse(format(args)) == args` for the role tuple,
NOT through `parse_iri`. Separate from the version-qualified IRI
surface. Per-edge alignment-IRI builder deferred to the phase that
needs it (Phase 14 alignment metagraph bootstrap, if any).

### PB-5 — Phase 11 carry-forward mostly does NOT fire in Phase 12

* **MetagraphSchema scanner** (Phase 11 PB-7 C): fires when L2 first
  bumps a `MetagraphSchema`. Phase 12 ships zero metagraphs / zero
  schemas. First candidate: Phase 13 (L2 Schemas) or Phase 14 (KL
  bootstrap).
* **ADR-0134 Proposed → Accepted flip**: needs a KL importer
  consuming scanner output. Phase 12 has no importer. First
  candidate: Phase 15 (Importers).
* **Migration playbook fill**: same trigger as the flip.

**Lock: explicitly re-carry-forward all three to the next eligible
phase in this design log.** Do not pretend Phase 12 closes them.

### PB-6 — CLI surface unspecified

Every prior phase ships at least one `mindsos <verb>` subcommand for
tester smoke-testing. PHASE_MAP §12 row names zero CLI surface.

**Lock: A — ship `mindsos knowledge iri build|parse|validate` +
`mindsos knowledge ref-types --list`.** Pure debug verbs over the
L2 library. Maintains the testability invariant. ~150 LoC + Typer
wiring. (Sub-subgroup shape locked in PB-16; `roles --list` added
in PB-22.)

### PB-7 — `RefFormatError` exception-class placement

v3 `identifiers.py` does `from .exceptions import RefFormatError`.
Phase 12 must ship `mindsos_knowledge/exceptions.py`.

**Lock: A — ship full slim exceptions module.** `KnowledgeError`
(base) + `RefFormatError`. Parallel to `mindsos_core.CoreError`
discipline from Phase 02. Inheritance pinned in PB-21.

### PB-8 — `capacity_snapshot_iri` embeds colon-bearing inner IRI

Legacy signature: `capacity_snapshot_iri(version, user_id,
capacity_iri, taken_at)` returns `capacity-state-<v>:snapshot:<uid>:
<capacity_iri>:<taken_at>`. `capacity_iri` is `capacity:<category>:
<name>` (ADR-0066) and `taken_at` is ISO8601 with colons. `parse_iri`
first-colon split survives, but the `body` becomes an opaque blob.

**Lock: A — port verbatim; full-string round-trip only.** Declare
round-trip = `parse_iri(build(...)).full == build(...)`. No
`parse_inverse_capacity_snapshot_iri` helper in Phase 12. Defer
field-level decomposition until first consumer (Phase 28+ —
capacity-snapshot). Body-after-`snapshot:` is opaque to the parser.

### PB-9 — Role constants + `_PREFIXES` + kind-table concrete locks

v3 ships 3 role constants, 3 prefixes, 6 lexicon/concepts kinds.
Phase 12 adds 5 new roles. Locking now prevents Phase 13–17 churn.

**Lock (concrete):**

```python
# Role constants
ROLE_ONTOLOGY            = "ontology"            # v3
ROLE_LEXICON             = "lexicon"             # v3
ROLE_CONCEPTS            = "concepts"            # v3
ROLE_PROMOTED_PIPELINES  = "promoted-pipelines"  # new
ROLE_TASK_PATTERNS       = "task-patterns"       # new
ROLE_MEMORIES            = "memories"            # new
ROLE_PROBLEM_TRACE       = "problem-trace"       # new
ROLE_CAPACITY_STATE      = "capacity-state"      # new

# Frozensets
SEED_ROLES        = frozenset({ROLE_ONTOLOGY, ROLE_LEXICON, ROLE_CONCEPTS})
UPPER_LAYER_ROLES = frozenset({ROLE_PROMOTED_PIPELINES, ROLE_TASK_PATTERNS,
                               ROLE_MEMORIES, ROLE_PROBLEM_TRACE,
                               ROLE_CAPACITY_STATE})
ALL_ROLES         = SEED_ROLES | UPPER_LAYER_ROLES

# Source prefixes (first match wins)
_PREFIXES = (
    ("dolce-dul-",          ROLE_ONTOLOGY),
    ("oewn-",               ROLE_LEXICON),
    ("framenet-",           ROLE_CONCEPTS),
    ("promoted-pipelines-", ROLE_PROMOTED_PIPELINES),
    ("task-patterns-",      ROLE_TASK_PATTERNS),
    ("memories-",           ROLE_MEMORIES),
    ("problem-trace-",      ROLE_PROBLEM_TRACE),
    ("capacity-state-",     ROLE_CAPACITY_STATE),
)

# Kind detection table (data-driven, replaces v3's hard-coded
# `if role in (LEXICON, CONCEPTS)` block)
_KINDS_PER_ROLE = {
    ROLE_LEXICON:            frozenset({"synset", "sense", "lemma"}),
    ROLE_CONCEPTS:           frozenset({"frame", "lu", "fe"}),
    ROLE_PROMOTED_PIPELINES: frozenset({"pipeline", "step"}),
    ROLE_TASK_PATTERNS:      frozenset({"pattern", "subgoal"}),
    ROLE_MEMORIES:           frozenset({"memory"}),
    ROLE_PROBLEM_TRACE:      frozenset({"entry"}),
    ROLE_CAPACITY_STATE:     frozenset({"snapshot"}),
}
```

Parser becomes table-driven; adding a role in Phase 27 is a 2-line
edit, not a control-flow change.

### PB-10 — Round-trip contract

PHASE_MAP §12 said "builders round-trip" without pinning equality.

**Lock: A — string round-trip.** `parse_iri(build(*args)).full ==
build(*args)` for every builder; plus assertions on parser-derived
fields (`.role`, `.source`, `.version`, `.kind`). No per-builder
inverse field helpers in Phase 12 — those ship per-consumer
(Phase 28 capacity-snapshot, Phase 16 pipeline, etc.).

### PB-11 — `user_id` charset contract for `memory_iri` /
`capacity_snapshot_iri`

ADR-0044 doesn't pin `user_id` charset. Server (Phase 18) is first
user-store consumer.

**Lock: A — `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`.** Parity with
state-file name regex from Phase 03 §3. Enforced in builder; raises
`RefFormatError` on violation. Phase 18 inherits the constraint as
a free invariant. Documented in ADR-0044 §Revisions amendment-1
(see PB-17).

### PB-12 — Port `global_ref_key` / `local_ref_key` / `REF_TYPE_KEY`
and SEED_ROLES now or defer?

First consumer is Phase 14 (KL bootstrap) at earliest. They're
1-line helpers but no Phase 12 caller tests them end-to-end.

**Lock: A — port everything in v3 `identifiers.py` verbatim now.**
Avoids a Phase 14 chat re-grepping "where do ref-keys live." Trivial
surface; ships in the same file. 4 trivial unit tests for the helpers.

### PB-13 — PHASE_MAP §12 row rewrite required

Current row no longer matches scope. Per PHASE_MAP §0
("PHASE_MAP itself is the durable contract"), Phase 12 must rewrite
its own row in the same commit it ships, otherwise Phase 13 reads
stale scope.

**Lock: rewrite at impl step (mirrors Phase 11 §6 PHASE_MAP edit).**
Specifically:

* Net-new: NEW (`mindsos_knowledge` package — first L2 phase ships
  the slim skeleton).
* Features: 14 IRI builders + `alignment_role` + `parse_iri` +
  `is_version_qualified_iri` + REF_TYPES + ref-key helpers + role
  constants + `mindsos knowledge iri` + `ref-types` + `roles` CLI.
* Tests: scale from 4 to ~85.
* Risks: ADR-0045 closes; ADR-0047 untouched; ADR-0067 parity test
  deferred to Phase 27.
* Carry-forward repeated: MetagraphSchema scanner → Phase 13/14;
  ADR-0134 flip → Phase 15; migration playbook → Phase 15.

### PB-14 — Close Phase 02 forward-ref to L2 identity docs

Phase 02 §"Doc sections this phase confirms" says: *"the IRI section
explicitly notes IRI parsing is L2 / Phase 12."* Phase 12 must close
the loop.

**Lock: A — amend `docs/concepts/identity.md` to swap the
deferred-to-Phase-12 note for a cross-link, plus create new
`docs/concepts/identifiers.md` (L2 concept page covering
version-qualified IRI shape, role table, parse contract).**
Concept-doc-per-layer keeps the layer boundary visible in the docs
tree; gives Phase 13/14 a hook page to amend without touching L1
docs.

### PB-15 — Test count + cumulative target

Up-front number prevents Phase-11-PB-31-style mid-step recalibration.

Itemisation (revised after PB-20 builder-count correction and PB-22
roles verb add):

| Tier | Tests |
|---|---|
| Builder happy-path (14 builders × 1) | 14 |
| Builder parse round-trip (14 × 1) | 14 |
| alignment_role round-trip | 2 |
| parse_iri edge cases (bad prefix, missing version, NFC variants, kind detection × 7 roles) | 12 |
| is_version_qualified_iri truthy/falsey matrix | 4 |
| REF_TYPES self-consistency (frozenset; PROMOTED present; no L3 parity) | 3 |
| ref-key helpers (global / local / REF_TYPE_KEY) | 4 |
| role constants + SEED_ROLES / UPPER_LAYER_ROLES / ALL_ROLES | 3 |
| user_id charset enforcement (memory_iri + capacity_snapshot_iri) | 4 |
| capacity_snapshot embedded-colon round-trip | 2 |
| CLI: knowledge iri build / parse / validate (3 verbs × 3 each) | 9 |
| CLI: knowledge ref-types --list (happy + JSON + error) | 3 |
| CLI: knowledge roles --list (happy + JSON + filter) | 3 |
| doctor 4-pkg version-string parity | 2 |
| image-completeness sentinel (3 new module entries) | 3 |
| adversarial regex (lowercase prefix, leading dash version, etc.) | 4 |
| ADR-0067 parity-test-deferred sentinel | 1 |
| ADR-0045 closure sentinel (14 builders present in module + `__all__`) | 1 |
| ADR-0044 §amendment-1 sentinel (user_id charset documented) | 1 |
| Import isolation (mindsos_knowledge ⇏ mindsos_cli / mindsos_server) | 1 |

**Total isolated: ~90.** Cumulative target: 1780 (Phase 11) + 90 ≈
**~1870.**

### PB-16 — CLI verb structure: subgroup vs flat

PB-6 A said yes-to-CLI but didn't pin shape.

**Lock: A — sub-subgroup.** `mindsos knowledge iri {build|parse|
validate}` + `mindsos knowledge ref-types --list` +
`mindsos knowledge roles --list` (per PB-22). Anchors the
`mindsos knowledge <noun> <verb>` convention before Phase 13-17 fill
the noun column.

### PB-17 — ADR-0044 amendment for `user_id` charset

ADR-0044 (Accepted) doesn't pin `user_id` charset. PB-11 locks
`^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`. Phase 14 / 18 / 25 are downstream
consumers.

**Lock: B — add ADR-0044 §Revisions amendment-1.** Documents the
charset + cross-references Phase 18 as the next-consumer site.
Same pattern as ADR-0134 §amendment-1/2. Doesn't change Decision
text; prevents three later chats from re-litigating.

### PB-18 — Import-isolation regression test for `mindsos_knowledge`

ADR-0010 forbids L2 importing from L0; ADR-0014 keeps L1
Core-only-imports. Phase 25 (SessionProtocol seam) ships an explicit
parity test for `mindsos_knowledge ⇏ mindsos_server`. Phase 12
establishes the package surface; a 10-LoC AST-walk test enforces
discipline from day one.

**Lock: A — ship `tests/phase_12/test_import_isolation.py` now.**
Asserts `mindsos_knowledge.*` modules import nothing from
`mindsos_cli` or `mindsos_server` (latter doesn't exist yet — test
parametrises over a "forbidden roots" list). `mindsos_core` NOT
forbidden (downward import allowed). ~15 LoC + 1 test.

### PB-19 — Step-0 audit probe list (explicit pre-impl)

Phase 11 §3 ran six probes and predicted/confirmed zero cascade.
Phase 12 re-runs them plus three new ones.

(See §3 Step-0 audit outcomes table below.)

### PB-20 — Builder count correction: 14, not 10

I undercounted in PB-2. Actual ADR-0045 + v3 surface:

| Source | Builders |
|---|---|
| v3 DOLCE | `dolce_iri` |
| v3 OEWN | `oewn_synset_iri`, `oewn_sense_iri`, `oewn_lemma_iri` |
| v3 FrameNet | `framenet_frame_iri`, `framenet_lu_iri`, `framenet_fe_iri` |
| ADR-0045 upper-layer | `pipeline_iri`, `pipeline_step_iri`, `task_pattern_iri`, `subgoal_template_iri`, `memory_iri`, `problem_trace_iri`, `capacity_snapshot_iri` |
| **Total IRI builders** | **14** |

Plus `alignment_role` (graph-name helper, not an IRI builder per
PB-4).

**Lock: correct silently.** Updates PB-15 itemisation (~85 → ~90)
and cumulative target (~1865 → ~1870).

### PB-21 — `KnowledgeError` inheritance

PB-7 A locked module shape but not base class.

**Lock: A — `class KnowledgeError(Exception)`.** Separate hierarchy
root from `CoreError`. Two reasons: (1) `mindsos_instances.exceptions`
(Phase 06) follows this pattern — independent roots, no cross-layer
inheritance; (2) coupling L2's root to L1's via inheritance makes a
future "swap L1 implementation under L2" refactor harder. Consumers
wanting catch-all do `except (CoreError, KnowledgeError)`.

### PB-22 — `mindsos knowledge roles --list` CLI verb

PB-16 locked `iri {build,parse,validate}` + `ref-types --list`.
Symmetric verb for role enumeration would be `roles --list` (parallel
to Phase 02's `identity strategies`).

**Lock: A — ship `mindsos knowledge roles --list [--json] [--seed-only
| --upper-only]`.** Outputs 8 roles + which are SEED_ROLES vs
UPPER_LAYER_ROLES. ~15 LoC + 3 tests. Maintains `noun --list`
discoverability convention.

## 2. Step-list pushbacks (deferred to step-list sign-off)

Carry-forward standard locks from Phase 11 — no fresh decisions, just
folded into the step list:

* **PB-25-equiv (notes/CONFIRMED split into 4 sub-steps)** — apply.
* **PB-26-equiv (design-log step)** — this file.
* **PB-18-equiv (phase-bump cascade in ONE commit)** — apply with
  9 bump sites (8 known + `mindsos_knowledge/__init__.py:__version__`
  new).
* **PB-32-equiv (Dockerfile COPY probe + edit)** — NEW `COPY
  mindsos_knowledge/` in both prod + test stages (not just probe).
* **PB-33-equiv (confirm-phase pytest summary regex regression)** —
  intact post-B-10-T6; sentinel re-run only.
* **PB-34-equiv (host-native confirm-phase)** — apply.
* **PB-35-equiv (tag AFTER squash-merge to main)** — apply.

## 3. Step-0 audit outcomes (probe table)

| # | Probe | Predicted cascade |
|---|---|---|
| 1 | state-file version literals (`_state_version`, `CURRENT_VERSION`) | 0 (no persistence change) |
| 2 | phase-string literals (`"11"`, `"0.0.0+phase11"`, `mindsos:phase11-{prod,test}`) | 8 known bump sites + 1 NEW (`mindsos_knowledge/__init__.py:__version__`) |
| 3 | caplog/capsys assertions over loader paths | 0 (loader untouched) |
| 4 | Dockerfile COPY discipline | 1 NEW COPY block per stage (`COPY mindsos_knowledge/`) |
| 5 | confirm-phase pytest summary regex | 0 (B-10-T6 fix intact; sentinel re-run only) |
| 6 | doctor 3-pkg version-string parity | MUST flip to 4-pkg; `len(packages) == 3` literal → 4 |
| 7 | NEW: ref-key helper literals (`ref:global_<role>`, `ref:<role>`, `ref_type`) in existing tests | 0 expected |
| 8 | NEW: cumulative-count literal `== 1780` / `>= 1780` in any test | 0–1 patches max |
| 9 | NEW: ADR-0045 closure sentinel (does any prior-phase test assume only 3 builders exist?) | 0 expected |

**Total predicted cascade: 0–1 prior-phase test patches** (Probe 8
worst case). Re-run all 9 grep probes in Step 0 of impl; patch
enumerations in ONE commit per `feedback_batch_fix_dont_iterate.md`.

## 4. Carry-forward (deferred to later phases)

From Phase 11 — re-carried-forward per PB-5 (Phase 12 does not close
them):

* **MetagraphSchema scanner** (MetaEdge / IntergraphEdge / etc. types)
  → Phase 13 (L2 Schemas) or Phase 14 (KL bootstrap) — whichever first
  bumps a `MetagraphSchema`.
* **ADR-0134 Proposed → Accepted flip** → Phase 15 (Importers) — first
  KL consumer of scanner output.
* **`docs/dev/migration-playbook.md` full content** → Phase 15 — same
  trigger.
* **ADR-0134 §amendment-3** → reserved for first KL consumer's
  structural feedback (Phase 15).
* **Apply-style migration** (`apply(violations, *, dry_run=True)`) →
  Phase 14+ when first cross-layer consumer needs it.
* **Versioned schemas with named migrations** → Phase 12+ original
  target; pushed to Phase 13/14 with the schema-bump trigger.
* **`Schema.diff(old)` structural-diff helper** → defer until
  doc-generator consumer.
* **`mindsos persistence verify --repair` flag** (ADR-0123 v2) →
  Phase 14+.

New carry-forward owed by Phase 12 (this file):

* **REF_TYPES parity test with L3** → Phase 27 (L3 ships REF_TYPES
  duplicate frozenset).
* **Per-edge alignment IRI builder** (if needed) → Phase 14 alignment
  metagraph bootstrap.
* **Per-builder inverse field helpers** (capacity_snapshot, pipeline,
  task_pattern, memory, problem_trace) → per-consumer phase
  (Phase 16 / 28 / 30 etc.).
* **Server-side `user_id` charset enforcement** → Phase 18, inherits
  the regex locked in PB-11 + ADR-0044 §amendment-1.

## 5. Cross-chat dependencies

### Closed (Phase 11 → Phase 12)

* `phase-11-confirmed` tag (commit `2eca5c5`) is the Phase 12 branch
  point.
* All Phase 11 surfaces (loader policy, migration scanner, LoadReport,
  CLI verbs) unmutated by Phase 12.

### Forward (Phase 12 → Phase 13+)

* L2 Phase 13 (Schemas): consumer for role constants + role-graph
  schema vocabulary.
* L2 Phase 14 (KL bootstrap): consumer for ref-key helpers
  (`global_ref_key`, `local_ref_key`, `REF_TYPE_KEY`), `alignment_role`
  graph-name helper, REF_TYPES frozenset.
* L2 Phase 15 (Importers): consumer for IRI builders (DOLCE / OEWN /
  FrameNet) + drives ADR-0134 Proposed → Accepted flip when first
  importer consumes scanner output.
* L2 Phase 16 (Promotion): consumer for `pipeline_iri` /
  `pipeline_step_iri` + `task_pattern_iri` / `subgoal_template_iri`.
* L0 Phase 18 (Server user store): inherits `user_id` charset.
* L0 Phase 25 (SessionProtocol seam): consumes import-isolation
  invariant established in Phase 12.
* L3 Phase 27 (DataStates + capacity primitives): owes the REF_TYPES
  parity test deferred in PB-3.
* L3 Phase 28 (12 categories): consumer for `capacity_snapshot_iri`.
* L3 Phase 30 (Pipeline finder): consumer for `problem_trace_iri`.

## 6. ADR matrix (Phase 12 touches)

| ADR | Pre-Phase-12 | Phase 12 action |
|---|---|---|
| 0010 (no cross-layer L2 → L0 import) | Accepted | No edit; PB-18 isolation test enforces. |
| 0014 (L1 Core-only-imports) | Accepted | No edit; isolation test forbids reverse-direction. |
| 0044 (memories Local + user_id in IRI) | Accepted | + §amendment-1 (user_id charset `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`); STAYS Accepted (Revisions amendment per `feedback_docs_source_of_truth.md`). |
| 0045 (per-role IRI builders) | Accepted | No edit; 14 builders ship as ADR declares; closure sentinel test in Phase 12. |
| 0047 (REF_TYPES open vocabulary) | Accepted | No edit; 7-element frozenset ports verbatim. |
| 0066 (capacity IRI form) | Accepted (Phase 27 context) | No edit; `capacity_snapshot_iri` embeds capacity_iri as opaque body per PB-8. |
| 0067 (REF_TYPES shared with KL) | Accepted | No edit; L3 parity test deferred to Phase 27 (PB-3). |
| 0134 (schema migration scanner) | Proposed | No edit; STAYS Proposed (no Phase 12 KL consumer per PB-5). |

## 7. File ledger (Phase 12 modifications)

NEW:

* `mindsos_knowledge/__init__.py` — package init + `__version__` +
  `__all__`.
* `mindsos_knowledge/identifiers.py` — slim port of v3
  `mindsos_knowledge/identifiers.py` + 7 upper-layer builders + 5
  new prefixes + `_KINDS_PER_ROLE` table.
* `mindsos_knowledge/exceptions.py` — `KnowledgeError` (base) +
  `RefFormatError`.
* `mindsos_cli/commands/knowledge.py` — Typer subcommand group +
  `iri build / parse / validate` + `ref-types --list` + `roles --list`.
* `docs/api/knowledge/identifiers.md` — new (PHASE_MAP §12).
* `docs/api/knowledge/ref-types.md` — new (PHASE_MAP §12).
* `docs/concepts/identifiers.md` — new (L2 concept page; PB-14).
* `docs/usage/knowledge/iri-cli.md` — new (CLI verb reference).
* `confirmation_docs/PHASE_12_DESIGN_LOG.md` — this file.
* `tests/phase_12/` — ~90 tests across 11 tiers.

MODIFIED:

* `mindsos_cli/__init__.py` — bump `__version__` to `0.0.0+phase12`
  (phase-bump cascade).
* `mindsos_cli/manifest.toml` — bump `[mindsos] phase = "12"`,
  `version = "0.0.0+phase12"` (phase-bump cascade).
* `mindsos_cli/app.py` — register `knowledge` subcommand group.
* `mindsos_cli/commands/doctor.py` — extend `_check_version_strings`
  to 4-pkg parity (`mindsos_core` + `mindsos_cli` +
  `mindsos_instances` + `mindsos_knowledge`).
* `mindsos_core/__init__.py` — bump `__version__` (phase-bump cascade).
* `mindsos_instances/__init__.py` — bump `__version__` (phase-bump
  cascade).
* `pyproject.toml` — bump `[project] version` + add `"mindsos_knowledge*"`
  to `[tool.setuptools.packages.find].include`.
* `Dockerfile` — `COPY mindsos_knowledge/` in BOTH prod + test stages
  (PB-32-equiv).
* `docker-compose.yml` — bump image tags `phase11-*` → `phase12-*`.
* `docs/concepts/identity.md` — amend forward-ref to L2 identifiers
  doc (PB-14).
* `docs/dev/repo-layout.md` — mention new `mindsos_knowledge/` package.
* `docs/changelog/CHANGELOG.md` — append Phase 12 line.
* `mkdocs.yml` — add nav entries: `API > Knowledge > Identifiers /
  Ref types`; `Concepts > Identifiers`; `Usage > Knowledge > IRI CLI`.
* `tests/_shared/sentinel_paths.py` — append 3 new module entries
  (`mindsos_knowledge/__init__.py`, `identifiers.py`, `exceptions.py`).
* `confirmation_docs/PHASE_MAP.md` §Phase 12 row — full rewrite per
  PB-13 + PB-2 + PB-3 + PB-4 + PB-5 + PB-6 corrections.
* `/Users/.../Layered Intelligence/docs/decisions/adr/0044-memories-move-to-local-per-user.md`
  — add §Revisions amendment-1 per PB-17 (lives in parent project
  tree, not under `halvim_mindsos/`).

Phase-bump cascade (PB-18-equiv, ONE commit late in step list,
9 sites):

* `mindsos_core/__init__.py:__version__`
* `mindsos_cli/__init__.py:__version__`
* `mindsos_instances/__init__.py:__version__`
* `mindsos_knowledge/__init__.py:__version__` (NEW 9th site)
* `mindsos_cli/manifest.toml [mindsos] phase`
* `mindsos_cli/manifest.toml [mindsos] version`
* `pyproject.toml [project] version`
* `docker-compose.yml mindsos image tag` (prod + test)

## 8. Confirmation command

```
mindsos confirm-phase --phase 12 --notes-file notes-phase-12.md
```

Pre-build: `docker compose --profile test build mindsos-test` BEFORE
confirm-phase (timeout 1800s per `feedback_confirm_phase_timeout.md`).
Host-native invocation per PB-34-equiv (avoid docker COPY-notes
cascade that cost Phase 10 B-10-T5).

Release CI tags `phase-12-confirmed` AFTER squash-merge to main per
8-step procedure in `feedback_release_tag_after_squash_merge_only.md`
(PB-35-equiv).
