# Phase 07 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`.

## phase_title

L1 Persistence — ships the FalkorDB-side persistence layer for `mindsos_core` + sibling-package `mindsos_instances/persistence`. `Client` Protocol (ADR-0030) + `FalkorClient` + `InMemoryClient` + `AsyncClient` (ADR-0126) + `bootstrap` with **14-index** `DEFAULT_INDEXES` (ADR-0123 amended per P89 A relationship-index syntax + P95 B final count: 10 node-label + 3 relationship + 1 hot-path `:Node {graph_id}`) + `GraphRepository` (persist with persist-time check per ADR-0123 §2 + always-bump `_version` + opt-in OCC predicate per ADR-0127 + per-(graph, element) tombstones per P69 A) + `MetagraphRepository` with **4-step lifecycle P96 A** (Core → WAL commit → `after_persist` observer → return; programmatic-only at 07 per P60 A; metagraph CLI verbs defer to Phase 08 per M14/P12 D) + `WriteAheadLog` (ADR-0122) with **primary context-manager API** per P50 B (raw `begin`/`commit`/`recover` accessible) + 5-bucket `verify_invariants` integrity scanner (ADR-0123 §3) + 3-bucket sibling `verify_invariants_graph` (P98 A) for `verify --source=db --graph G` + single-Graph `load_graph(client, gid)` (M14) + `_props_json` encoding on `:Metagraph` anchor (ADR-0130 + P62 A canonical JSON) with no size cap (P83 C) + narrow chained driver-exception catch (P97 B) + `schema_name` plain Cypher property on `:Metagraph` row using existing dataclass field (P100 A) + `_version: int = 1` on **9 dataclasses** (7 core + 2 instance per P11 A) + `mindsos persistence` **5-verb CLI subapp** (sync / load / diagnose / verify / inspect-state) with Rich tables per P99 A + `--to-json` writes sibling `~/.mindsos/graph-<name>.fromdb.json` per P85 B + `sync --replace` WAL-refusal per P91 A + new `[falkordb]` manifest section (host/port/graph; no username per P86 B; password env-only per P15 A) + doctor self-test extension per P59 A 5-cell matrix + `_CONFIRM_PHASE_TIMEOUT_SECONDS` bump 600 → 900 (M12 + P93 pre-build recipe) + 4 ADRs flipped Proposed → Accepted inline per M3 A (0122 / 0123 / 0126 / 0127; acceptance-criteria amended per P27 C; ADR-0127 §Repository API amended per P28 B; `MissingExpectedVersionError` ships at L0/L2 not L1 per P84 B).

## tester_notes

Free-form. What you observed, anything surprising, deviations from
PHASE_MAP's pass criterion, open questions for the next phase chat.

---

### Recipe (Linux test box; canonical baseline)

Step 0 — **bring up FalkorDB + pre-build the test image BEFORE confirm-phase**
per `feedback_confirm_phase_timeout.md` + P93. The wrapper's 900s budget
starts at invocation; pre-building keeps the budget reserved for pytest.

```
[Linux] cd ~/work/mindsos          # or wherever halvim_mindsos is checked out
[Linux] git fetch origin
[Linux] git checkout phase-07
[Linux] git pull --ff-only origin phase-07
[Linux] docker compose up -d falkordb
[Linux] docker compose --profile test build mindsos-test
```

Step 1 — **probe FalkorDB v4.18.3 `CREATE INDEX IF NOT EXISTS` support**
in BOTH node-form and relationship-form per P68 A + P89 A. Run once,
record output for the confirmation doc.

```
[Linux] docker compose exec falkordb redis-cli GRAPH.QUERY phase07_probe \
        'CREATE INDEX IF NOT EXISTS FOR (n:_Probe) ON (n.id)'
[Linux] docker compose exec falkordb redis-cli GRAPH.QUERY phase07_probe \
        'CREATE INDEX IF NOT EXISTS FOR ()-[r:_PROBE_REL]-() ON (r.id)'
[Linux] docker compose exec falkordb redis-cli GRAPH.DELETE phase07_probe
```

Expected outcome (Step 0 audit, P68 A): both forms accepted. If either
fails, the bootstrap module's try/except on "already exists" patterns
needs to relax further; surface in tester_notes.

Step 2 — **probe driver-exception class on oversized `_props_json`**
write per P97 B. Capture the actual exception type the falkordb-py
driver raises so the narrow chained catch tuple in
`metagraph_repository.py:_safe_run` is grounded in observed behaviour.

```
[Linux] docker compose --profile test run --rm mindsos-test python -c "
from mindsos_core.config import FalkorConfig
from mindsos_core.persistence import FalkorClient
import os
c = FalkorClient(FalkorConfig(host=os.environ['FALKORDB_HOST'], port=int(os.environ['FALKORDB_PORT']), graph='phase07_probe'))
big = 'x' * (10 * 1024 * 1024)  # 10 MB
try:
    c.run_query('CREATE (n:_PropProbe {prop: \$p})', {'p': big})
    print('NO ERROR — driver accepted 10 MB write')
except Exception as e:
    print(f'{type(e).__module__}.{type(e).__name__}: {e!r}')
"
```

Record the exception class output verbatim. If it differs from
`redis.exceptions.ResponseError` or `falkordb.exceptions.FalkorDBError`,
amend the narrow catch tuple in `mindsos_core/persistence/metagraph_repository.py`.

Step 3 — **confirm-phase wrapper**.

```
[Linux] mindsos confirm-phase --phase 07 --notes-file notes-phase-07.md
```

Expected: 30-90s pytest run inside the pre-built image, then the
wrapper writes `confirmation_docs/PHASE_07_CONFIRMED.md`. Cumulative
test count should hit ≥ 1127 + 2 skipped (Phase 06 baseline) +
~110-140 Phase 07 added = ~1237-1267 + 2 skipped.

---

### Operational reminders (carry-forward from prior phases)

- **`~/.mindsos/` path literally** — when authoring recipe commands
  that reference state files, use the literal path `~/.mindsos/...`,
  NEVER `$MINDSOS_STATE_DIR/...` per `feedback_state_dir_env_var.md`
  (hit twice in 05b + 05c).
- **Squash-merge order** — per `feedback_release_workflow_ordering.md`:
  `gh pr create` → `gh pr merge --squash --delete-branch` → pull main
  → verify `confirmation_docs/PHASE_07_CONFIRMED.md` exists → tag
  `phase-07-confirmed` → push tag. The release.yml workflow refuses to
  ship if the confirmation doc isn't on the tagged commit.
- **Pre-build first** — Phase 07 bumps the confirm-phase timeout to
  900s but `docker compose --profile test build mindsos-test` outside
  the wrapper protects the budget per P93.

### Hotfix expectations

- **B-07-T-likely-1** (timeout): `_CONFIRM_PHASE_TIMEOUT_SECONDS = 900`
  ships in this branch's binary. If tester invokes a pre-built image
  with the 600s value still inside, force-rebuild
  (`docker compose --profile test build --no-cache mindsos-test`).
- **B-07-T-likely-2** (`[falkordb]` manifest section missing):
  surfaces in doctor self-test as a warning, not a fail per P59 A.
- **B-07-T-likely-4** (`pytest.mark.integration` marker not registered):
  `tests/conftest.py` exists per P55 A; verify pytest discovers it.
