# Phase 30 — Design Log

**Phase:** 30 — L3 Pipeline finder + invoke runtime + ProblemTraceRecord
**Layer:** L3
**Net-new code?** No (repackage + slim port from parent)
**Designed:** 2026-05-25 (single chat; 5 rounds R0-R4 + R5 ship-lock)
**Total picks:** ~56 across 6 rounds (R0=13, R1=12, R2=9, R3=10, R4=6, R5=5)
**Probe-driven obsolescence:** 0 (4 R4 sub-cases tightened R3 picks)

See `notes-phase-30.md` for ship state + §7 13-step ship checklist
+ §9 carry-forwards. This log captures the design rounds in order.

---

## Round 0 (R0) — core scope locks

PB roster + picks:

| PB | Subject | Pick |
|----|---------|------|
| 1 | InvocationResult shape: ADR text vs shipped code field names | (a) Ship existing `success:bool`+`error`; ADR-0072 §Impl footer locks divergence (LATER STRENGTHENED by R3 PB-35 to amendment) |
| 2 | runtime.py location: new module vs extend capacity.py | (a) NEW `runtime.py` mirroring parent |
| 3 | Residents at Phase 30 or Phase 31? | (a) Defer to Phase 31 per PHASE_MAP §31 + exceptions.py docstring |
| 4 | Pipeline finder location: new pipeline.py vs builtins/pathfinding.py | (a) NEW `pipeline.py`; Phase 31 wraps as builtin |
| 5 | `find_pipeline` signature: `user_id` vs `session` | (a) `session: SessionArg = None` (halvim Phase 28 R1 PB-14 lock) |
| 6 | CLI verb roster | (a) `find` + `invoke` + `problem-trace tail` (LATER REDUCED by R3 PB-36 to drop `invoke`) |
| 7 | Docs scope — building.md / retrieval.md / both | (c) Both at Phase 30 |
| 8 | ProblemTraceSink persistence model | (a) In-memory per ADR-0074 (no PB substance) |
| 9 | Sentinel flip form: in-place vs delete-and-add | (a) In-place rewrite (LATER REFINED by R3 PB-37 + R4 PB-45 to include rename) |
| 10 | Test count baseline: anchor vs trust memory vs no literals | (a) Step-0 docker rerun at phase-29-confirmed (REVISITED to (ii) per process question — trust memory + mid-ship reconcile) |
| 11 | Brief's Phase 28 = 3079 — wrong vs CONFIRMED.md 3073 | (a) PHASE_28_CONFIRMED.md authoritative; correct memory at ship |
| 12 | `include_deprecated` discipline on BFS finder | (a) Defer further (carry-forward #9 stays open) |
| 13 | `find_pipeline` raise vs envelope on no path | (a) Raise `PipelineNotFoundError` per ADR-0072 §Decision carve-out |

**Open process question** answered (ii) by user: trust memory's
3115/40 baseline; reconcile mid-ship.

---

## Round 1 (R1) — substrate sub-cases

| PB | Subject | Pick |
|----|---------|------|
| 14 | `find_pipeline` first arg: CapacityLayer / CapacityLayerView / Metagraph | (a) `capacity_layer: CapacityLayer` parent-mirror |
| 15 | `CapacityLayer.find_pipeline()` method as alias | (a) Free function only |
| 16 | `task_id`/`step_id` on invoke: both optional vs task_id required | (a) Both optional parent-verbatim; foot-gun documented |
| 17 | ProblemTraceRecord.mm_ref field: keep vs drop at Phase 30 | (a) Keep `Optional[str]=None` forward-compat |
| 18 | `emit_problem_trace` free function vs sink.emit only | (a) Ship both parent-verbatim |
| 19 | CLI invoke input-passing protocol | (d) `--input-json <str>` + `--input-file <path>` (LATER MOOTED by R3 PB-36 invoke drop) |
| 20 | CLI `problem-trace tail` peek vs drain | (b) Peek-only at Phase 30; drain via Python API |
| 21 | `tests/phase_30/` file enumeration | (a) Full ~21-file layout |
| 22 | ADR-0066 footer form: append new vs amend existing | (a) Append new Phase 30 footer |
| 23 | Sentinel-paths additions (+pipeline.py + runtime.py = +2) | (a) +2; CLI file NOT added (precedent) |
| 24 | Shortest-by-capacity-count invariant | (a)+(b) Parent BFS verbatim + add sentinel test |
| 25 | Pre-impl probe scope at R4 | (a) Full 7-probe checklist |

---

## Round 2 (R2) — scope tightenings

| PB | Subject | Pick |
|----|---------|------|
| 26 | CLI invoke exit code on `success=False` envelope | (b) Exit 3 (LATER MOOTED by R5 PB-61) |
| 27 | CLI source-of-CapacityLayer: fresh in-memory / Falkor / state-file / fixture | (a) Fresh in-memory per invocation; Phase 30 CLI is programmer-facing |
| 28 | `pipeline.py` circular-import risk | (a) `TYPE_CHECKING` guard |
| 29 | ProblemTraceSink scope: per-layer (parent) vs per-Local vs single+filter | (a) Single sink per ADR-0074; multi-tenant via payload |
| 30 | CLI session-passing: Global-only vs --session-token vs --user-id | (a) Global-only at Phase 30; --session-token deferred |
| 31 | __init__.py export count audit | (a)+(c) +11 → 95; reconcile at impl Step-0 |
| 32 | Hotfix slot count | (a) 1 slot |
| 33 | CLI find JSON output shape | (a) Verbose verbatim Pipeline/PipelineStep dict |
| 34 | Shortest-by-capacity-count concrete fixture | (a) Branching-capacity fixture in `_fixtures.py` |

---

## Round 3 (R3) — ADR + scope drop + fixtures

| PB | Subject | Pick |
|----|---------|------|
| 35 | ADR-0072: §amendment-1 vs §Impl footer for field rename | (b) Both — §amendment-1 + §Impl |
| 36 | Drop CLI `invoke` verb at Phase 30? | (b) DROP — no real users without registration verbs; defer to Phase 31 |
| 37 | Sentinel-flip — rename file/function for clarity? | (a) Rename (LATER SUB-CASED by R4 PB-45 — file rename for whole-file sentinel; function rename for mixed-content file) |
| 38 | ADR roster confirm | (a) 4 ADRs / 5 touches (0066+0071+0072×2+0074) |
| 39 | Cumulative test count estimate | (a) ~3180/44 estimate; reconcile at Step-0 (refined down to ~3160-3170/~45 after R3 PB-36 invoke-CLI-drop) |
| 40 | `_fixtures.py` content | (a) 7 helpers + 3 layer builders |
| 41 | mkdocs.yml — both docs in nav vs one | (a) Both in Capacity nav |
| 42 | docstring rewrite (mechanical) | — skipped |
| 43 | CLI tests fixture: fresh-per-invocation? | (a) Fresh-per-invocation; structural test surface only |
| 44 | `find_pipeline` session resolution: `_resolve_session_arg` vs inline | (a) Inline; net-new API has no legacy |

---

## Round 4 (R4) — pre-impl probe execution

7 probes per R1 PB-25(a):

| Probe | Subject | Outcome |
|-------|---------|---------|
| 1 | `pytest.raises(Import/Module/AttrError)` referencing Phase 30 surface | PASS — exactly 2 Phase 28 sentinels; no third hit |
| 2+3 | `mindsos_capacity.pipeline` / `.runtime` imports in halvim | PASS — zero pre-existing references |
| 4 | Phase 29 walks API stability (`consumers_of` returns `List[Node]` with `.properties.get(inputs/outputs)`) | PASS — matches parent BFS contract |
| 5 | Parent `runtime.py` import-closure | PASS — imports only from `capacity` + `exceptions`; no builtins leakage |
| 6 | Halvim `pipeline.py` import-closure | PASS — trims to `deque + dataclass + typing + PipelineNotFoundError + TYPE_CHECKING/CapacityLayer + types.SessionArg` |
| 7 | `_resolve_declaration(capacity_iri, *, user_id)` stability since Phase 28 | PASS — unchanged |

Probe sub-cases (PBs from probe findings):

| PB | Subject | Pick |
|----|---------|------|
| 45 | Sentinel-flip pattern — whole-file rename + function-only rename | (a) Sub-case the rename per file |
| 46 | `runtime.py` imports: trim `Capacity`+`Monitor`+`ResidentError` | (a) Trim; consumers (residents) deferred to Phase 31 |
| 47 | `pipeline.py` drops parent's `build_bfs_capacity_declaration` scaffolding | (a) Drop; Phase 31 ships registered builtin form directly |
| 48 | `pipeline.py` imports: drop `SuccessorHop`+`View`+`CATEGORY_PATH_FINDING`+`capacity_iri` | (a) Trim |
| 49 | R4 design-pick obsolescence confirm | (a) Zero design picks obsoleted; design stable |
| 50 | __init__.py export count post-trim | (a) +11 / 95 stands |

---

## Round 5 (R5) — ship-lock

| PB | Subject | Pick |
|----|---------|------|
| 51 | Self-reversal audit on R4 picks (parent-divergence) | (a) R4 picks 46/47/48 stand; reversal not warranted |
| 55 | ADR-0071 §Impl footer wording — clarify datastate-keyed BFS | (a) Explicit clarification footer; not an amendment |
| 61 | Exit code 3 — moot per R3 PB-36(b)? | (a) Drop from Phase 30 CLI; deferred to Phase 31 |
| 62 | ADR-0072 §am1 + §Impl block ordering | (a) Amendment above footer; separate blocks |
| 63 | Design saturation declaration | (a) Saturate; await "proceed" cue |

---

## Picks summary cross-table (locks at ship)

* `mindsos_capacity/runtime.py` — NEW: `invoke` free function +
  `ProblemTraceRecord`/`Sink`/`emit_problem_trace`. Trimmed imports
  (no `Capacity`/`Monitor`/`ResidentError`).
* `mindsos_capacity/pipeline.py` — NEW: `Pipeline`/`PipelineStep`/
  `find_pipeline` (datastate-keyed BFS via `consumers_of`).
  `TYPE_CHECKING`-guarded `CapacityLayer` hint; trimmed imports;
  NO parent scaffolding factory.
* `mindsos_capacity/exceptions.py` — +2 raisers (`PipelineNotFoundError`,
  `ProblemTraceError`); 5→7 classes.
* `mindsos_capacity/capacity_layer.py` — +`self.problem_trace` attr
  +`invoke` method; new imports (`InvocationResult`, `ProblemTraceSink`,
  `_runtime_invoke`).
* `mindsos_capacity/__init__.py` — +11 exports (95 total); docstring
  rewrite; `__version__ = "0.0.0+phase30"`.
* `mindsos_cli/commands/capacity.py` — NEW: `find` verb + `problem-
  trace tail` verb. NO `invoke` verb. Exit codes 0/1/2 only (no exit 3
  at Phase 30).
* `mindsos_cli/app.py` — register_capacity_app wired.
* `tests/phase_28/test_invocation_not_exported.py` → renamed file
  `test_invocation_exported_phase_30.py` with body flipped (positive
  imports).
* `tests/phase_28/test_capacity_layer_init.py::test_problem_trace_attribute_not_present_at_phase_28`
  → renamed function `test_problem_trace_attribute_present_at_phase_30`
  with body flipped (assert hasattr).
* `tests/phase_30/` — 21 new files (`__init__` + `_fixtures` + 19
  test files); ~50-60 cases pre-parametrize.
* `tests/_shared/sentinel_paths.py` — +2 paths (`runtime.py`,
  `pipeline.py`).
* 12-site version bump complete.
* `docs/usage/capacity/building.md` — NEW.
* `docs/usage/capacity/retrieval.md` — NEW.
* `mkdocs.yml` — Capacity nav `(Phase 27, 28, 29)` →
  `(Phase 27, 28, 29, 30)`; both new docs added.
* PHASE_MAP §30 — Status `In progress`; expanded Features /
  Tests / Risks / Docs lines.
* Parent ADRs: 0066 §Impl + 0071 §Impl + 0072 §am1 + 0072 §Impl +
  0074 §Impl = 5 touches across 4 ADRs.

---

## Hotfix ledger preamble

* **B-30-T1** (reserved) — generic contingency. R4 7-probe checklist
  closed every concrete gap pre-impl; 1 slot suffices.
