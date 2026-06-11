# PHASE_45_DESIGN_LOG — Rail D: L3 dream family ratification

**Chat:** DREAM_FAMILY_CHAT (design) + Phase 45 (ship), combined under the
Phase 44 option-C precedent (`PHASE_44_DESIGN_LOG.md §0`): saturate the
dream-family design first, then implement + ship.

**Status:** R0 open (design saturation). Pre-impl pushback rounds + a
buildability scan precede branching `phase-45`. **No code written yet.**

**Rail context:** Rails A (39/43), B (40/41/42), C (44) all SHIPPED. Rail D
is the only remaining slot before Phase 46 (L4 substrate) convergence.

**Prereq check (run 2026-06-07):**
- `git tag --list | grep -E "phase-4[0-4]-confirmed"` → 40/41/42/43/44 all
  present. (39 also present.) ✔
- `main`-tip `4e79ff0`; working tree has `M HANDOFF.md`,
  `M docs/future_work/L3_FUTURE_WORK.md` + the untracked Robot Demo
  workstream files. **Leave Robot Demo files alone; never `git add -A`;
  stage selectively.** ✔
- Phase 45 depends on Phase 38 + DREAM_FAMILY_CHAT closure (this chat). ✔
- **VERSION BUMP REQUIRED:** slot 45 > high-water mark 44 → full 9-surface
  manifest bump 44→45 (PHASE_MAP §1 high-water rule). First slot to exceed
  the high-water mark. Contrast 40/41/42 (≤44, no bump). ✔

---

## §0. Required-reading acknowledgement

- HANDOFF §1, §3.1.17 (Phase 42 ship — most recent precedent + ceremony
  lessons), §4/§4.1 (L5 settled — dream-as-live), §9 (process discipline).
- POST_PHASE_38_PHASE_MAP §0, §1 (DAG + high-water rule + 9-surface
  checklist), Phase 45 detail block, §6 downstream sequencing.
- PHASE_42_DESIGN_LOG (process: S-surface saturation, pre-impl pushback
  rounds, gate-driven follow-up budget, ADR transcription-parity probe,
  ground-first consumer discipline).
- PHASE_44_DESIGN_LOG §0 + §5–§12 (option-C combined design+ship;
  consumer-discipline — ground every surface against its real consumer;
  defer absent-consumer surfaces).
- CHAT_B_DECISIONS D-B5/B6/B7/B8/B9; l5_mental_model_design_notes §5.2–§5.3.
- L1_L3_REFRAME_DECISIONS §L3-36→L3-51 batch (L3-51 dream family contract).

---

## §1. Design ground truth (what DREAM_FAMILY_CHAT inherits, not re-litigates)

From Chat B + the L3-51 family contract + the Phase 45 PHASE_MAP row:

- **3 v1 dream capacities** (D-B6): `dream.maintenance`, `dream.exploration`,
  `dream.retry`. All operate at **TaskRun level** (re-execute whole task from
  selected chain entry). Cross-level variants are v2+.
- **Execution policy per capacity** (D-B8): `dream.maintenance` =
  `replay_recorded`; `dream.exploration` = `re_execute_capacities`;
  `dream.retry` = `re_execute_capacities` **with replan-injection**.
  (`hybrid` is named in D-B8 but has no v1 assignee.)
- **Entry-point** (D-B7): declared at registration. v1 = "latest-active
  TaskRun state" for all three. v2 adds specific PipelineRun / Milestone /
  replan-point.
- **Dont-know contract** (L3-51): **OPTIONAL_RETURN**; `concurrent=True`.
  Already shipped in `family_rules.FAMILY_RULES["dream"]` (Phase 42 L3-57).
- **Dream-as-live** (D-B5): dream = load episode → fresh MM by deep-copy →
  re-execute; ALS signals fire per normal mechanics; no separate dream-
  learning track. **The MM deep-copy + re-execution + ALS firing are L4/L5
  (Phase 46 substrate / Phase 48 hookup) — NOT this phase.**
- **Privacy** (D-B9): dream runs under the owning user's session;
  Local-staging only; no PII path to Global.
- **Signal provenance**: signals emitted during dream re-execution carry
  `dream_source_episode_iri`. (Live emission is Phase 48; see S8.)

**Scope boundary (chat opener + PHASE_MAP):** DREAM_FAMILY_CHAT settles the
**L3 contract only** — 3 capacity bodies + execution-policy contracts +
replan-injection mechanism + dream entry-point contract. **L4
orchestration/scheduling (dream-cycle timer, MM deep-copy, live
re-execution, ALS wiring) is Phase 46/47/48 — OUT OF SCOPE.**

---

## §2. Grounding probes (consumer discipline — run before locking picks)

| Probe | Finding | Consequence |
|---|---|---|
| `builtins/` build pattern | `consolidate.py` = DataStates + `Capacity` factory + idempotent `install_*` (DataStates-first). | `builtins/dream.py` mirrors it. |
| Category graph | `register_capacity` → `ensure_category_graph(mg, declaration.category)` creates the role-graph **lazily**; no `FUNCTIONAL_CATEGORIES` membership check. | `category="dream"` works with **no bootstrap / FUNCTIONAL_CATEGORIES edit**. |
| `FAMILY_RULES["dream"]` | Already `OPTIONAL_RETURN` (shipped Phase 42 / L3-57). | **No `family_rules.py` edit.** |
| `REALM_DREAM` | `"dream"` already in `RESERVED_REALMS` (shipped Phase 40). | `datastate:dream.*` passes strict realm validation; **no realm edit, no `allow_new_realm`.** |
| `invoke` → context shape | `call_capacity` passes `context=<Mapping>` (dict). Bodies use `context.get("kl")` (consolidate). **`invoke`→typed `CapacityContext` plumbing is DEFERRED to Phase 46 (PB-23).** | Phase-45 dream bodies must follow the **shipped dict-context convention**, not `context.kl`. The MM/re-execution handles do not exist at v1. |
| `_CapacityBase` fields | post-Phase-42: +`concurrent`/`inline`/`max_latency_ms`/`precondition_iri`/`effect_iri`/`reads_mm`. No policy/entry-point field. | execution_policy + entry_point need a home (S2). |
| ADR-0162 on disk | Absent. | Author here; R1 step-0 parity probe is trivially clean. |
| `tests/phase_45/` | Absent. | New suite (5 files per PHASE_MAP). |

**Load-bearing inherited lesson (HANDOFF §3.1.17 PB-23 / §3.1.16 iter_monitors
/ §3.1.15 family_rules):** dream.* bodies have **no v1 L3 consumer** — their
consumer is the L4 dream loop at Phase 46/47/48. This is the legitimate "ship
the L3 contract ahead of its L4 consumer" pattern. **Ship the contract; do
not build the L4 hookup.**

---

## §3. Design forks — pushbacks with options + picks (R0)

### S1 — Dream body thickness / contract shape  **[central fork]**

The bodies have no v1 consumer; the MM deep-copy + re-execution mechanism is
L4 (Phase 46); `invoke`→CapacityContext is deferred to Phase 46. So what does
a Phase-45 dream body *do*?

- **Opt A — Directive-emitter (forward-shape).** Each dream capacity is a
  registered `Capacity` whose body validates its input and **emits a
  structured `DreamDirective`** describing the dream action (policy +
  entry-point + source-episode provenance; for retry, a replan-injection
  payload). No actual re-execution. The L4 dream loop (Phase 46/48) consumes
  the directive to drive deep-copy + re-execution. Bodies are pure,
  import-isolation-clean, unit-testable without L4.
  - Pros: matches consumer discipline + every prior reversal
    (family_rules/iter_monitors/bipartite/CapacityContext all shipped as
    forward contracts); zero L4 pre-commitment; satisfies "registered +
    invokable" and "replan-injection executes per spec" pass criteria via
    directive emission; isolation-test-safe.
    - Cons: the body is "thin" — the interesting re-execution logic lands
    Phase 46/48; risk of a contract-shape mismatch when Phase 46 designs the
    loop (mitigated: directive is L3-authored = the boundary L4 must honour).
- **Opt B — Thick body + injected execution Protocol.** Ship a
  `DreamExecutionContext` Protocol (`replay(chain)`, `re_execute(entry)`,
  `inject_replan(...)`) the L4 substrate must implement; bodies call it; ship
  a fake for tests.
  - Pros: bodies contain real policy-driven control flow at v1.
  - Cons: **pre-commits the L4 dream interface from L3 before Phase 46 R0
    designs the substrate** — exactly the "don't build the L4 hookup here"
    anti-pattern; high contract-mismatch risk; larger surface; the fake is
    dead weight once Phase 46 lands the real one.
- **Opt C — `NotImplementedError` stubs.** Registered but raise on invoke.
  - Pros: minimal.
  - Cons: fails "invokable" + "replan-injection executes per spec" pass
    criteria. Reject.

**PICK: Opt A.** Directive-emitter. The directive is the L3→L4 contract; the
mechanism is L4's at Phase 46.

### S2 — Where execution_policy + entry_point live on the declaration

- **Opt A — `DreamCapacity(_CapacityBase)` subclass** with
  `execution_policy: str` + `entry_point: str` fields + `to_properties()`
  override (mirrors `Monitor`'s `subscribes_to`/`emits`). Typed, persisted on
  the Core node, introspectable by L4's dream loop.
  - Pros: idiomatic (Monitor/Adapter precedent); graph-as-truth; L4 reads
    policy off the registered node; serialises cleanly.
  - Cons: +1 dataclass + `__all__` entry + node_kind decision (stays
    REACTIVE — dream caps are invoked on demand, not resident).
- **Opt B — module-level `DREAM_POLICIES` dict** in `dream.py`.
  - Cons: a parallel out-of-graph registry L4 must separately know about;
    worse for graph-as-truth. Reject.
- **Opt C — plain `Capacity` + policy in description string.** Unparseable.
  Reject.

**PICK: Opt A.** `DreamCapacity` subclass; `node_kind` stays REACTIVE,
`node_type` stays CAPACITY.

### S3 — execution_policy value set

- **Opt A — 2-value `DreamExecutionPolicy` enum** (`replay_recorded`,
  `re_execute_capacities`); `hybrid` documented in ADR-0162 as v2 (no v1
  assignee).
  - Pros: consumer discipline (Phase 40 PB-1 precedent: don't ship enum
    members with no v1 consumer).
- **Opt B — 3-value enum** including `hybrid`.
  - Cons: `hybrid` has no v1 capacity → dead member.

**PICK: Opt A.** 2 values; `hybrid` is an ADR-documented v2 reservation.

### S4 — Replan-injection mechanism  **[load-bearing scope item]**

Actual replan (invalidate chain at/below level, spawn artifacts — Chat B
D-B30) is **L4 control flow**. The L3 contract is: what `dream.retry` emits
that *triggers* a replan.

- **Opt A — directive-field.** `dream.retry`'s `DreamDirective` carries an
  optional `replan_injection: ReplanInjectionDirective` (small frozen
  dataclass: `replan_level` + `source_episode_iri` + `reason`). On a
  failed-episode input the field is populated; on a non-failed input it is
  `None` (and retry may return dont-know `None`). The L4 dream loop consumes
  the field to perform the replan. **"Replan-injection executes per spec" =
  the retry body, given a failed-episode input, emits a directive whose
  `replan_injection` is populated** — fully testable in isolation.
  - Pros: pure L3 surface; no L4 pre-commitment; satisfies the pass
    criterion without an L4 substrate.
- **Opt B — reuse `context.ReplanVerdict`.** Conflates a `decision.*` verdict
  (Chat A R2 should-replan) with a dream directive; different family,
  different consumer. Reject (keep dream's own dataclass).

**PICK: Opt A.** `ReplanInjectionDirective` lives in `builtins/dream.py`
(consumer-local), carried on the retry directive.

### S5 — DataState surface

- Input: dream capacities consume a `DS_DREAM_TASK_REF` (record describing
  the episode/TaskRun to dream over — `{"source_episode_iri": str,
  "task_run_iri": str, "failed": bool}` for retry's failure check).
- Output: `DS_DREAM_DIRECTIVE` (the emitted directive; OPTIONAL_RETURN → body
  returns the directive value or `None`).
- Realm: `datastate:dream.task_ref` + `datastate:dream.directive`
  (`REALM_DREAM` reserved). Registered DataStates-first in the installer per
  the consolidate precedent.

**PICK:** 2 DataStates (`dream.task_ref` input, `dream.directive` output);
shared across all 3 capacities.

### S6 — `dream` in FUNCTIONAL_CATEGORIES + bootstrap?

- **Opt A — leave FUNCTIONAL_CATEGORIES untouched**; rely on lazy
  `ensure_category_graph` at register (the consolidate-installer path).
  - Pros: minimal; `create_global` default unchanged; dream is an
    installable family like text (text.* is also NOT in
    FUNCTIONAL_CATEGORIES and installs lazily).
- **Opt B — add `CATEGORY_DREAM` to FUNCTIONAL_CATEGORIES** so `create_global`
  pre-creates the graph.
  - Cons: changes the bootstrap-default contained-graph count (13→14) +
    every `create_global()` count assertion across the test corpus, for a
    family that installs lazily anyway. Scope creep.

**PICK: Opt A.** Lazy install (text-family precedent). `CATEGORY_DREAM`
string constant added to `identifiers.py` for symbol hygiene, but **not**
added to `FUNCTIONAL_CATEGORIES`.

### S7 — Dream entry-point hookup contract

D-B7 entry-point is declared at registration (S2 `entry_point` field). The
**L4 dream-cycle timer interface** (what the Phase-46 timer passes to invoke a
dream capacity) is documented in ADR-0162 §Invocation-contract as the
L3→L4 boundary — **no timer code ships here** (Phase 46/47).

**PICK:** entry_point = constant `"latest_active_taskrun"` on all 3 caps;
timer interface documented in ADR-0162, not coded.

### S8 — `dream_source_episode_iri` signal provenance

Live signal emission during re-execution is L4/L5 (Phase 48 —
`test_dream_pipeline_hookup.py` per PHASE_MAP line 877). At Phase 45 there is
no signal-emitting invoke path and no ALS.

- **PICK:** ship `source_episode_iri` as a **field on `DreamDirective`** (the
  provenance the L4 loop propagates onto signals at Phase 48).
  `test_dream_signal_provenance.py` asserts the **field is present on the
  directive contract** + documented in ADR-0162 — NOT a live signal tag.
  Phase 48 wires it onto emitted signals.

### S9 — ADR-0162 authorship

Author `docs/decisions/adr/0162-l3-dream-family.md` (status Accepted). R1
step-0 ADR transcription-parity probe: grep the draft's policy/entry-point/
dont-know tables against `family_rules.py` + CHAT_B_DECISIONS on disk
(nothing else to drift against — ADR is new). Sections: Context (dream-as-
live, D-B5..B9); Decision (3 caps + 2-policy enum + DreamCapacity fields +
DreamDirective/ReplanInjectionDirective shapes + OPTIONAL_RETURN + entry-
point); §Invocation-contract (L3→L4 boundary the Phase-46 timer honours);
§v2-reservations (hybrid policy + cross-level entry-points + live signal
tagging). Chain: amends nothing; sentinel-anchored as Rail D chain root.

---

## §4. Buildability scan (over the proposed surface)

- `builtins/dream.py` (NEW) — `DreamExecutionPolicy` enum,
  `ReplanInjectionDirective` + `DreamDirective` dataclasses, `DS_DREAM_*`,
  3 `build_dream_*()` factories returning `DreamCapacity`, idempotent
  `install_dream_capacities()`. Mirrors `consolidate.py`. ✔
- `capacity.py` — `DreamCapacity(_CapacityBase)` subclass + `__all__`. (Or
  house the subclass in `builtins/dream.py` — see Q1 below.) ✔
- `identifiers.py` — `CATEGORY_DREAM = "dream"` + `__all__` (NOT into
  FUNCTIONAL_CATEGORIES). ✔
- `builtins/__init__.py` — re-export the dream installer surface (text
  precedent). ✔
- `__init__.py` — top-level `__all__`: per the builtins R0 PB-5 lock, the
  top-level package does **not** re-export the builtins subpackage. So the
  dream family adds **0 entries** to `mindsos_capacity.__all__` UNLESS
  `DreamCapacity` lives in `capacity.py` (then +1). → **export-slate impact
  depends on Q1.**
- `docs/decisions/adr/0162-l3-dream-family.md` (NEW). ✔
- `docs/concepts/dream.md` (NEW; 3-pipeline catalog) + mkdocs nav. ✔
- **9-surface version bump 44→45** (S-bump): manifest.toml phase+version; 7
  `__version__`; pyproject; docker-compose phase45 tags; export-slate
  sentinel literals in phase_30/31/34 (`test_version_bumped_to_phase_*`). ✔
- `tests/phase_45/` 5 files (maintenance / exploration / retry /
  signal_provenance / adr_amendment_sentinels). ✔

**Open buildability questions for R1:**

- **Q1 — `DreamCapacity` home.** `capacity.py` (alongside Monitor/Adapter;
  +1 export-slate entry across phase_29/30/31/33/34 sentinels) **vs**
  `builtins/dream.py` (no top-level export change; but `_CapacityBase`
  subclassing from a builtin is slightly unusual). **Lean: `capacity.py`** —
  it is the canonical home for capacity-kind dataclasses; the export-slate
  flip is mechanical and the sentinel discipline already exists. Confirm at R1.
- **Q2 — export-slate magnitude.** If Q1=capacity.py, the slate goes
  117→118; flip the 5 sentinel files + membership. Mechanical; budget 1
  gate-driven follow-up (Phase 42 precedent: slate flips cascade at gate-1).
- **Q3 — `to_properties()` on DreamCapacity** must serialise
  `execution_policy` + `entry_point` (Monitor precedent serialises
  subscribes_to/emits). Core node schema for category graphs: confirm the
  `dream` category graph schema accepts these property keys (the lazy
  `ensure_category_graph` uses `schema_for_role`; check strict-mode shape at
  R1 — likely permissive like other category graphs).
- **Q4 — sentinel chain root.** `test_adr_amendment_sentinels.py` anchors
  ADR-0162 as the **Rail D chain root** (PHASE_MAP: "chain link from Phase 38
  (Rail D chain root)"). Confirm the closest-ancestor content pattern at R1.

---

## §5. Proposed commit boundaries (draft — finalised at R1)

Single-PR on `phase-45` (scope is one new builtins family + ADR + docs +
version bump; smaller than Phase 43's two-PR split). Tentative:

1. ADR-0162 + `docs/concepts/dream.md` + nav (design landing).
2. `identifiers.py` (`CATEGORY_DREAM`) + `capacity.py` (`DreamCapacity`) +
   `builtins/dream.py` + `builtins/__init__.py` re-export.
3. 9-surface version bump 44→45 (+ export-slate sentinel flips).
4. `tests/phase_45/` 5 files.
5. (reserve) gate-driven follow-ups.

Squash to `main` at confirm-phase; single `phase-45-confirmed` tag **at the
confirm-artifacts commit** (the `PHASE_NN_CONFIRMED.md`-bearing commit — Phase
42 release-gate lesson, §3.1.17). Fix the Linux `git config` identity before
the confirm commit.

---

## §6. Out-of-scope (defended)

- L4 dream-cycle timer + scheduling (Phase 46/47).
- MM deep-copy + live re-execution + ALS signal firing (Phase 46 substrate /
  Phase 48 hookup).
- `invoke`→`CapacityContext` plumbing for dream bodies (Phase 46 PB-23;
  bodies use shipped dict-context).
- `signal.plan_decomposition_outcome` + ALS subsystem #11 (WSD installation;
  L3-37 scope).
- `hybrid` execution policy; cross-level entry-points (v2).
- Live `dream_source_episode_iri` signal tagging (Phase 48).

---

## §R1 — impl-locks + ADR transcription-parity probe

**S1 resolved (user, 2026-06-07): Opt A — directive-emitter.**

**Parity probe (R1 step-0) — CLEAN.** Grepped draft tables vs disk:
- D-B8 policy names verbatim: `replay_recorded` / `re_execute_capacities` /
  `hybrid` (CHAT_B_DECISIONS:98-100). ✔
- Capacity↔policy map verbatim (CHAT_B_DECISIONS:103-105). ✔
- `FAMILY_RULES["dream"] = OPTIONAL_RETURN` (family_rules.py). ✔
- ADR-0162 is new — nothing else on disk to drift against.

**Version surfaces confirmed at `phase44` (9-surface bump 44→45):**
`manifest.toml` (phase="45", version="0.0.0+phase45"); pyproject
"0.0.0+phase45"; 7 `__version__`; `docker-compose.yml`
`phase45-prod`/`phase45-test`; export-slate version-string sentinels
(`test_phase_*_version_bumped` phase44→phase45 across phase_29/31/33/34).

**Q1 LOCKED — `DreamCapacity` home = `capacity.py`** (alongside
Monitor/Adapter; both are top-level exported despite Monitor having no live
consumer until Phase 46 — capacity-kind dataclasses are exported as
vocabulary by precedent). Cost: **export-count flip 117→118 across 4 files**
(`tests/phase_29/31/33/34/test_*_export_slate.py`). Mechanical; same files
Phase 42 flipped. Budget **1 gate-1 follow-up** (export-slate cascades at
gate-1 per Phase 42).

**Q3 LOCKED — `to_properties()` serialises `execution_policy` + `entry_point`.**
Monitor precedent (`subscribes_to`/`emits` persisted onto the category-graph
node) confirms category graphs accept extra declaration props. Verify
strict-mode shape at impl (low risk; `_strict` defaults permissive).

**Q4 LOCKED — sentinel chain.** `tests/phase_45/test_adr_amendment_sentinels.py`
mirrors the Phase 42 structure: asserts ADR-0162 `status: Accepted` +
`§Implementation (Phase 45` footer; chain-parent = the Phase 38 sentinel
(Rail D chain root per PHASE_MAP). Confirm exact parent filename at impl.

**Other R1 locks:**
- ADR-0162 carries `status: Accepted` + `§Implementation (Phase 45)` footer
  (sentinel requires it).
- `DreamDirective` / `ReplanInjectionDirective` / `DreamExecutionPolicy` live
  in `builtins/dream.py` (consumer-local, like `DS_MM_COMPOSITE_INSTANCE`) →
  **NOT** top-level exported → no further slate churn. Only `DreamCapacity`
  (capacity.py) hits the slate.
- Contract fields: dream caps ship `concurrent=True` (L3-51), `inline=False`,
  no `precondition_iri`/`effect_iri`/`max_latency_ms` (ADR-0159
  `_validate_contract_fields` only requires `max_latency_ms` when
  `inline=True`).
- CHANGELOG untouched (stops at Phase 38; 39–44 precedent).
- HANDOFF.md is uncommitted (`M` — Robot Demo §0 block). Edit §3.1.18 via the
  working tree; **user stages selectively (`git add -p`) — never `git add -A`.**

## §R2 — skeptical sweep (round 2 of 2–3 budget)

No new blockers. Items considered + dispositioned:
- **find_pipeline auto-chaining.** dream caps emit `produces`/`consumes`
  bipartite edges (`dream.task_ref`→cap→`dream.directive`). No v1 producer of
  `dream.task_ref` exists (L4 supplies it), so `find_pipeline` won't
  auto-discover them — correct: they are entry-point-invoked, not
  pipeline-discovered. ✔
- **`docs/concepts/dream.md`** — non-strict `mkdocs build` (Phase 42
  re-scope); nav entry is its own inbound link → no new warning. ✔
- **Privacy (D-B9)** — no Global write path in any dream body (directives are
  inert data); satisfied structurally. ✔

**Saturation call (revised after R3):** see §R3.

## §R3 — confirmation round (buildability probes against live code)

All crux surfaces probed directly:

- **`family_rule_for` resolution — CONFIRMED.** `capacity:dream:maintenance`
  → `name_prefix="maintenance"` (not in FAMILY_RULES) → **falls through to
  `category in FAMILY_RULES`** → `"dream"` → `OPTIONAL_RETURN`. Dream caps get
  the correct dont-know contract with **zero `family_rules.py` edits**. ✔
- **`_validate_contract_fields` — CONFIRMED.** dream caps `inline=False` →
  no `max_latency_ms` required; `precondition_iri`/`effect_iri` `None` →
  skipped. Passes clean. ✔
- **`_CAPACITY_NAME_RE = ^[a-z][a-z0-9_.\-]*$` — CONFIRMED.** bare names
  `maintenance`/`exploration`/`retry` match (consolidate `name="mm"`
  precedent). ✔
- **Q3 node-property persistence — CLOSED.** `CapacityLayer.__init__`
  `strict=False` **default**; category graphs created lazily at that strict
  level; `register_capacity` passes `declaration.to_properties()` straight to
  `category_graph.add_node(properties=...)`. Monitor's `subscribes_to`/`emits`
  is the shipped precedent for extra declaration props. `execution_policy` +
  `entry_point` persist safely. ✔
- **Q4 CORRECTION (real catch).** R1 lock said "chain-parent = the Phase 38
  sentinel." **`tests/phase_38/` has `test_phase_38_doc_sentinels.py`, NOT a
  `test_adr_amendment_sentinels.py`** — so a `test_chain_links_from_phase_38`
  assertion would target a nonexistent file. The Phase 42 glob-and-assert-
  parent pattern is for a **continuing** Rail B chain (40←41←42). **Rail D is
  a fresh single-phase rail — mirror Phase 44 (independent Rail C root)
  instead:** Phase 44's sentinel asserts **no** chain-parent file; it
  documents "Rail C chain link from Phase 38" in the docstring and reads each
  ADR by **full filename** (`0160-...md`). **Revised Q4 lock:** `phase_45`
  sentinel docstrings "Rail D chain link from Phase 38"; reads
  `0162-l3-dream-family.md` by full filename; asserts `status: Accepted` +
  `§Implementation (Phase 45`. No chain-parent assertion. ✔

**Saturation call (final):** R3 closed every open buildability risk and
corrected one concrete test-authoring error (Q4) before it could ship. R0→R3
= four rounds, last round one correction + confirmations, no design reversal.
**Design is saturated and ready to branch `phase-45`** pending authorization.

---

## §7. Impl-time amendments (filled during/after ship)

**Implementation landed (Cowork working tree, pre-git, 2026-06-07).** All
picks shipped as designed; no impl-time reversals. Files:

- `mindsos_capacity/capacity.py` — `DreamCapacity(_CapacityBase)` subclass
  (`execution_policy` + `entry_point` fields; `to_properties()` override;
  node_kind REACTIVE) + `__all__` +1.
- `mindsos_capacity/__init__.py` — re-export `DreamCapacity` (import + top
  `__all__`); 117→118.
- `mindsos_capacity/identifiers.py` — `CATEGORY_DREAM = "dream"` + `__all__`
  (NOT in `FUNCTIONAL_CATEGORIES`).
- `mindsos_capacity/builtins/dream.py` (NEW) — `DreamExecutionPolicy`
  (2-value), `ReplanInjectionDirective`, `DreamDirective`, `DS_DREAM_TASK_REF`
  + `DS_DREAM_DIRECTIVE`, 3 directive-emitter bodies, 3 `build_dream_*`
  factories, idempotent `install_dream_capacities`.
- `mindsos_capacity/builtins/__init__.py` — re-export dream surface.
- `docs/decisions/adr/0162-l3-dream-family.md` (NEW) — Accepted +
  §Implementation (Phase 45).
- `docs/concepts/dream.md` (NEW) + mkdocs nav entry.
- **9-surface version bump 44→45:** manifest.toml (phase+version), pyproject,
  7 `__version__`, docker-compose phase45-prod/test, + sentinel-flips:
  count 117→118 (phase_29/31/33/34) + version phase44→phase45
  (phase_30/31/34).
- `tests/phase_45/` (5 files + `__init__.py`).

**Sandbox smoke (Python 3.10; informational — canonical gate is Linux
docker 3.11):**
- `import mindsos_capacity` → `__all__` count **118**, `DreamCapacity`
  present.
- `pytest tests/phase_45 + 5 flipped export-slate files` → **56 passed**.
- `pytest tests/phase_27 + phase_40 + phase_41 + phase_42 + phase_45` →
  **149 passed** (no L3 regression from the new dataclass / category / family
  resolution / version bump).
- Server-importing suites (phase_28/34 fixtures) **cannot collect** under
  3.10 (`datetime.UTC` is 3.11+) — environment gap, unrelated to Phase 45
  (no L0 roster change this phase). The Linux docker gate (3.11) runs the
  full cumulative suite.

**Ceremony (COMPLETE 2026-06-07).** Branched `phase-45` off main-tip
`4e79ff0`; staged the 30 Phase-45 paths explicitly (HANDOFF + L3_FUTURE_WORK
+ Robot Demo left untouched); commit `a901212`; Linux gate **3694 passed / 9
skipped / 0 failed** (31:56); squash to `main` `ab32e3d`; confirm-phase
generated `PHASE_45_CONFIRMED.md` + notes. **Anomaly (Phase 40/42-class):**
confirm ran on the branch tip (`1e0fbf1`), so the confirm artifacts were
cherry-picked onto `main` (`e76a1a3`); tag `phase-45-confirmed` placed at the
confirm-artifacts commit `e76a1a3` (not the squash) per the Phase 42
release-gate lesson. HANDOFF §3.1.18 + header, PHASE_MAP Phase 45 row →
SHIPPED, CLAUDE.md status, this log all updated in the doc-closure commit.
