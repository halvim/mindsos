# `skill verify` — confirmation

Status: **built, awaiting Linux gate.** Design: `SKILL_VERIFY_DESIGN_NOTE.md`.
Placement: **maintenance — no numbered phase, no version bump, no new ADR** (D10).

## What shipped

- `mindsos_server/skills/verify.py` — read-only cross-layer engine + 7-check
  catalog + human/JSON renderers. Takes an already-booted `(kl, cl)`; stores
  nothing.
- `mindsos_cli/commands/skill.py` — `skill verify <bundle> [--json] [--all]`
  added to the existing `skill` Typer group; Falkor-unreachable → refuse
  whole-command (exit 1).
- `tests/skill_verify/test_verify.py` — engine unit tests per check + two
  install→verify e2e paths (in-memory and persist/reload) + CLI refuse-path
  tests.

## State source — approach C′ (probe-resolved)

Gating probe (`skill_verify_probe.py`, Linux gate, 2026-07-02):
`PRODUCES`/`CONSUMES` **round-trip through `FalkorDBLocalPersister` = PASS**
(6/5 survived; `CapacityLayerView.outputs_of` non-empty on reload);
`Schema.validate_node_properties` reachable standalone = PASS (`UnknownTypeError`,
not `WriteHandleNotWiredError`).

Decision: edges are persist-*capable* but **not persisted at rest** — the standard
boot reactivates L3. So the verifier boots the real stack read-only and reads:
`_build_kl_and_client()` (L2 Global from Falkor) + `_build_cl()` +
`apply_installed_skills(cl, kl)` (Global L3 reactivated), then reads L2 checks vs
KL role-graphs and L3 checks vs `CapacityLayerView`. No writes; the boot is the
same one `skill activate` uses.

## Check catalog as built

1. **Atomic-pipeline integrity** (per present capacity) — capacity has ≥1
   `PRODUCES` edge. MALFORMED → DEFECT.
2. **Dangling bipartite edge** — any `CONSUMES`/`PRODUCES` target DataState
   unregistered. DEFECT.
3. **Manifest↔state drift** — forward L3 (declared capacity/DataState absent) →
   DEFECT; forward L2 (declared node absent) → DEFECT; reverse-L2
   (bundle-prefixed node present but undeclared) → WARN; reverse-L3 undetectable.
4. **Broken ref** — task-pattern `sufficient_predicate_iri` / pipeline
   `capacity_iri` → absent capacity. DEFECT. (Catalog-wide; `promoted-pipelines`
   is empty.)
5. **Task→capacity chain** — NEUTRAL; `mapped: none` for all today (deferred "A").
6. **Schema nonconformance** — declared L2 node vs its role-graph schema via
   `schema_for_role(role, strict=True).validate_node_properties`. DEFECT.
7. **Capacity→L2 role** (code-derived) — AST scan of installer modules for
   `ROLE_*` references; function-local = high / module-scope = low confidence.
   INFO.

Rollup metrics: `broken_atomic`, `task_unmapped`/`task_total`, `code_scan_hits`.

## Deviations from the design note (v1 scoping)

- **Global-scope v1.** Skill installs are Global-only (Phase 50), so the engine
  reads Global only; the note's Global+Local reconciliation (§4) is an extension
  point (the engine already takes booted views — a Local view can be added
  without a rewrite). The **no-mint** rule (§4) holds trivially: the Local is
  never touched.
- **`--all` = all recorded bundles**, not builtins. Builtins carry no install
  record; covering them needs a separate capacity-set path (deferred). Note §2's
  "incl. builtins" is not met in v1.
- **Check 1 / 3 overlap under C′.** Check 1 runs only on capacities *present* in
  reactivated state; a *missing* declared capacity is caught by check 3
  (drift-forward-l3), not check 1.
- **Refuse exit code = 1** (skill.py convention: 1 = rejected/refused/failed),
  vs `persistence.py::_refuse_with` code 2. Same "refuse whole command" behavior.

## Watch-items at the gate

- **Check 6 strictness (canary: `test_ref_bundle_l2_conforms_to_schema`).**
  Strict property-type validation may over-flag if a persisted node's properties
  don't match the role schema's declared types even though install accepted them.
  If this test reddens, downgrade property-type mismatches to WARN (keep
  unknown-node-type as DEFECT) rather than loosening the whole check.
- Check 7 AST scan is best-effort; a scan failure is reported INFO, never fails
  the command.

## Tests — results (Linux gate)

- `tests/skill_verify/test_verify.py`: first run **9 passed / 1 failed** — the
  failure was a test-only plumbing bug (`find_by_name` → `None` on
  `InMemoryClient`); fixed to load by `metagraph_id`. **Check-6 canary
  `test_ref_bundle_l2_conforms_to_schema` PASSED** — strict schema validation does
  not over-flag the ref bundle, so no check-6 loosening needed. Rerun pending.
- Full cumulative gate: _pending_.
- `skill_verify_probe.py`: temp probe removed at the build commit.

## Deferred (hooks only, per the note)

A (task→capacity mapping), B (skill-as-graph L3 reorg,
`SKILL_AS_GRAPH_L3_DESIGN_SEED.md`), B-provenance (DataState→L2 provenance).
