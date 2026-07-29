# Gate flake: phase_05c/06 CLI SIGSEGV — CPython vfork root cause (fix)

Date: 2026-07-22. Scope: standalone test-infra fix (NOT L5 build work).

## Symptom
`tests/phase_05c/test_cli_intergraph_hyperedge.py` and
`tests/phase_06/test_cli_instances.py` were intermittently red in the FULL
gate (`docker compose ... pytest tests/ -q`), never when run alone. Three
signatures, all the SAME underlying event:
- `assert -11 == 0` — a subprocess returncode of -11 = SIGSEGV.
- phase_06 setup `ERROR`s — `populated_mg` asserts return codes, so a crash
  there raises AssertionError at setup.
- `IdentityError: Graph 'word'/'letter' not in metagraph 'mg'` — the phase_05c
  `hyperedge_metagraph` fixture does NOT check return codes, so a crashed
  setup step (`metagraph add-graph`) is swallowed and the metagraph is left
  half-built; the next command fails downstream.

## Root cause (confirmed to mechanism)
A rare SIGSEGV in the `mindsos` CLI subprocess, not in MindsOS logic.
`tests/_shared/cli.py::_run_cli` spawns `mindsos` with capture_output=True
(pipes) + default close_fds=True + a bare `"mindsos"` argv[0] (no dir). On
CPython 3.12 those conditions DISQUALIFY the posix_spawn fast path, so the
spawn takes `fork_exec`, and with `subprocess._USE_VFORK` True (verified on the
container: `posix_spawn True vfork True`) that means `vfork()`. vfork shares
the parent address space until exec; spawning from the heavyweight pytest
interpreter (~8k `mindsos` forks per full gate) intermittently faults the
child -> SIGSEGV. Well-known CPython/vfork fragility, not a graph bug.

## Ruled out (with evidence)
- FalkorDB: 3 ways (zero refs in graph/metagraph/instances cmds; 43/43 green
  with NO FalkorDB; FALKORDB_HOST=dead -> no connect).
- ~/.mindsos HOME fallback: state stays in per-test MINDSOS_STATE_DIR.
- Hash-seed / serialization: counts stable across PYTHONHASHSEED.
- Lost-update / logic: gate is serial (no xdist/addopts); add-graph is a
  correct read-modify-write; audited clean.
- CLI import fault: 50k shell-spawned startups -> 0 crashes.
- Thread leak (feat_subminds worker pools): 0 threads leaked after the suite.
- Reproduction: ~200k synthetic spawns (shell + single-threaded Python parents,
  sandbox AND container) -> 0 crashes; needs the real heavyweight pytest
  parent. 20 instrumented full gates (~10.5h) -> 0 recurrence. Pre-fix rate
  ~1 in ~23 gates.

## Fix
`tests/_shared/cli.py`: `subprocess._USE_VFORK = False` at module import ->
plain `fork()` (isolated COW address space) for CLI subprocess spawns. Not a
mask: no skip/xfail, no graph renames, no suite serialization, no
returncode-swallowing teardown. Removes the fragile syscall the crash rode on.

## Validation
- No regression: sandbox re-run of phase_05c + phase_06 slices green; the flag
  is observed False after the harness imports.
- Positive proof is inherently NEGATIVE/long-term: pre-fix event is ~1-in-23
  gates, so "fixed" = the -11 SIGSEGV never recurs. If it ever returns,
  escalate to core-dump + gdb backtrace on a caught crash.
- If any NON-`_run_cli` subprocess spawn ever shows the same -11, broaden the
  flag to `tests/conftest.py` (process-wide).

## Separate finding (OUT OF SCOPE — deferred)
`tests/phase_48/test_step5_solve_execution.py::test_execution_run_grounds_capacity_mm_on_solve`
is also flaky: passes 30/30 in isolation, intermittently fails in the full
gate with capacity_mm DataStateInstance nodes missing
PROP_DATASTATE_INSTANCE_TYPE (`{None}`). NEW L5 Step 5 work
(execution.run->execute_pipeline), different root cause (global-state
contamination). Left untouched; recommend a separate full-gate bisect.
