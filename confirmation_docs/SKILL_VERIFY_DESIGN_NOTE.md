# `skill verify` — design note (read-only cross-layer component verifier)

Status: **design settled** (this chat). Not yet built.
Placement: **maintenance / downstream — no numbered phase, no version bump** (D10).
Companion doc: `SKILL_AS_GRAPH_L3_DESIGN_SEED.md` (deferred "B").

---

## 1. Purpose

Report how an installed intelligence — a capacity, seen through its bundle — sits
in the MindsOS layered architecture, by checking the links MindsOS actually
stores. **Read-only; stores nothing new.** Requires FalkorDB (reads persisted
state); refuses cleanly when it is down.

This is **not `doctor`** (release-pin / reachability parity vs `manifest.toml`).
`verify` reads *instance content* — the actual capacities, bipartite edges, L2
nodes, and their wiring in the persisted metagraphs.

## 2. Command (D2, D10)

`mindsos skill verify <bundle-name> [--json] [--all]`

Under the existing `skill` Typer group (bundle-keyed; sits beside
install/uninstall/list/activate). The check engine takes a **set of capacities**,
so `--all` (catalog-wide, incl. builtins) is a thin wrapper, not a rewrite.

---

## 3. Corrected architecture model (the core output of this chat)

Prior anchors were stale; the settled model:

1. **A capacity IS its atomic pipeline.** `ds1 —CONSUMES→ cap —PRODUCES→ ds2` is
   emitted at registration from the declaration's inputs/outputs (ADR-0156).
   Registration always emits these edges, so the **"no capacity without a
   pipeline" invariant holds by construction** — and is checked directly (check 1).
2. **Composition (`pipeline → pipeline`)** is computed at dispatch by the L3
   finders (`BFSFinder` / `ConjunctionFinder`, `mindsos_capacity/pipeline.py`)
   walking the bipartite edges. Not stored.
3. **`promoted-pipelines` (L2) is writer-less / empty** at current main (verified
   in `pipeline.py` + grep). **Not checked** — traversing it would flag 100% of
   capacities as false orphans. Dropped (see Decision Log D1).
4. **L3 is persistent.** F9 (2026-06-21, ADR-0185/0186) shipped
   `FalkorDBLocalPersister` — native Global + Local metagraph round-trip. The
   capacity graph (nodes + `PRODUCES`/`CONSUMES` edges) persists to FalkorDB.
   Only the Python `implementation` callable is re-minted per process (via
   reactivation factory / installer re-run) — the verifier does not need it.
5. **Single Local.** v1 is single-tenant (HANDOFF §893, Chat A R5 D35). Per-user
   machinery exists in code but there is **one** Local. No tenant selection.
6. **L3 is organized by category graphs today**, not skill graphs
   (`identifiers.py` §3: one `capacity:<category>` graph per functional category
   + one shared `capacity:datastates`). Skill-as-graph is the intended target →
   **deferred "B"** (`SKILL_AS_GRAPH_L3_DESIGN_SEED.md`).
7. **Task → capacity mapping** ("a capacity exists because a task needed it") is
   intended architecture but **not stored today** (registration captures no task;
   `task-patterns.paired_pipelines` unpopulated, points at the empty pipeline
   store). This tool implements the *chain query* now (check 5); building the
   mapping is **deferred "A"** (its own chat).

## 4. State source — how the verifier reads state (D3)

Approach **C: read the persisted graph directly, no reactivation.** Reflects real
installed state; avoids the reactivation-factory problem (Local composites use
factories that close over runtime handles a standalone CLI lacks).

- Boot: reuse `mindsos_server/persistence/bootstrap.py` (load Global from
  FalkorDB) + `local_boot.load_or_mint_local` for the single Local.
- **Read Global + the single Local** — `global_view()` and `local_view(uid)`.
  `local_view` does **not** fall through to Global, so the engine reads **both
  views and reconciles by IRI**.
- **A2′ mirror dedup**: Global DataStates are mirrored into the Local (F9), so a
  DataState IRI can appear in both — dedupe, Global canonical. A Local capacity
  consuming a Global DataState whose mirror is **missing** → a real dangling
  defect (check 2).
- **Scope-aware resolution**: a Local capacity's edges resolve against Local ∪
  Global.

Open build-time fact (does not change the design, confirm at build): whether
Global L3 capacity nodes persist as Falkor nodes or are reactivated-at-boot from
`installed-skills` records. If the latter, the Global half materializes via
installer-only reactivation (no runtime factories needed → no false-missing).

## 5. Check catalog

Exact stored links (graph-queried):

| # | Check | Reads | Verdict |
|---|-------|-------|---------|
| 1 | **Atomic-pipeline integrity** — every declared output has a `PRODUCES` edge, every declared input a `CONSUMES` edge, every referenced DataState registered | L3 (Global+Local) | **DEFECT** if broken. *This is the "capacity = pipeline" invariant.* |
| 2 | **Dangling bipartite edge** — a `CONSUMES`/`PRODUCES` edge to an unregistered DataState, incl. a missing A2′ mirror | L3 | **DEFECT** |
| 3 | **Manifest↔installer drift** — forward: declared `[l3]`/`[[l2.content]]` IRI absent from state | manifest + state | forward → **DEFECT**; reverse-L2 (undeclared bundle-prefixed node present) → **WARN**; reverse-L3 not detectable (see §6) |
| 4 | **Broken ref** — task-pattern `sufficient_predicate_iri` (or pipeline `capacity_iri`) → capacity absent from catalog | L2 + L3 | **DEFECT** |
| 5 | **Task→pipeline→capacity chain** — `task-pattern —paired_pipelines→ pipeline —HAS_STEP→ capacity` (+ direct `sufficient_predicate_iri`) | L2 (Global+Local) | **NEUTRAL** — "mapped: none/…" + rollup. Returns "none" for all today; same query lights up when "A" lands (zero rework) |

Code-derived link (labeled "static, code-derived, may be incomplete"):

| # | Check | Method | Verdict |
|---|-------|--------|---------|
| 6 | **Schema nonconformance** — bundle's declared L2 nodes vs their role-graph schema | core/L2 `Schema` structural validation (**NOT** `write_handle.validate_node` — role-gated, raises `WriteHandleNotWiredError` for `concepts`/`task-patterns`) | **DEFECT** |
| 7 | **Capacity → L2 role** — scan `writeable(role=ROLE_*)` + `ROLE_*` imports | AST, bundle modules (via manifest `[l3].installers`); function-local = high confidence, module-scope = low | **INFO** |

## 6. Bundle attribution (D4)

L3 capacities/datastates are **not** bundle-prefixed (ref bundle's cap is
`capacity:perception:text.ref_shout`) and live in shared category graphs, so a
bundle's L3 members are knowable **only from the manifest `[l3]` list** ("A").
Consequence: **forward drift works; reverse-L3 drift is undetectable**;
reverse-L2 works (L2 nodes carry the `<bundle>-<version>:` prefix). Skill-as-graph
("B") would make attribution structural and enable reverse-L3.

## 7. Output

Per capacity: a status per check — PRESENT / MISSING / MALFORMED / MIS-WIRED /
DEFECT — plus the neutral "mapped: none/…". Grouped: (1) exact stored links,
(2) code-derived links (labeled), (3) defects. Human table + `--json`.

Rollup metrics (D8): **broken-atomic** (expect ~0), **task-unmapped** (expect all,
today), **code-scan hit-rate** (M with a recoverable L2 role / total; K
function-local). **Dropped:** provenance-less-DataState count — trivially *all* by
design, not a (B) signal. The (B) signal is the catalog-wide code-scan hit-rate,
obtained via `--all`.

## 8. FalkorDB-down behavior (D5)

Every content check reads persisted state → **Falkor is required.** Unreachable →
**refuse the whole command** via `_refuse_with` (+ exit), mirroring
`persistence.py`/`doctor`. No per-check degrade, no `--reconstruct` fallback in v1
(a clean-room rebuild would check a rebuild, not reality — misleading).

## 9. Testing (D9)

- **Unit** (seeded in-memory metagraphs), one per check: atomic OK; dangling →
  defect; drift → defect; broken ref → defect; schema → defect; chain "none" +
  chain "found".
- **E2E** (`InMemoryClient`-backed, per `tests/phase_44`): install ref bundle →
  persist → reload → verify → assert happy path (`ref_shout` atomic OK, no drift,
  schema OK, task-mapped none). No shipped-fixture edit.

**Gating probe (do first):** confirm `PRODUCES`/`CONSUMES` **IntergraphEdges
round-trip through `FalkorDBLocalPersister`**. Reading persisted bipartite state
(§4) depends on it. Precedent for a persistence gap exists (Phase 49 descoped
durable episode flush → L0-26). If IntergraphEdges do not reload, check 1 finds no
edges and every capacity is a false defect → **D3=C reopens** (fall back to
reactivation). This is a decision-reopener, not a test tweak.

## 10. Deferred work

- **A — task→capacity mapping in the architecture.** Registration (or the bundle
  manifest) records the task a capacity serves, so check 5 stops being "none" for
  all. Own chat; contract-adjacent. Hook: a `serves_task`/`task_iri` on the
  capacity declaration OR a manifest `[l3]` task binding → a stored
  `task-pattern → pipeline → capacity` chain.
- **B — skill-as-graph L3 reorganization.** See `SKILL_AS_GRAPH_L3_DESIGN_SEED.md`.
  Makes bundle attribution structural; simplifies checks 1–3 and enables
  reverse-L3 drift.
- **(B-provenance) — DataState→L2 provenance.** A knowledge-sourced realm +
  `source_role`/`source_iri` on DataState (or `DataState —DERIVED_FROM→ L2-node`),
  turning check 7 from a code-scan into a graph query. Touches ADR-0156/0158; own
  design pass. The write direction (writeable-gate role) is separate from the
  DataState/read direction.

## 11. Decision log

| ID | Decision | Notes / reversals |
|----|----------|-------------------|
| D1 | Orphan-against-`promoted-pipelines` **dropped**; the invariant is checked as **atomic-pipeline integrity** (check 1); task-mapping is the **neutral chain query** (check 5) | Reversed twice: "orphan = INFO" → then dropped entirely once the writer-less/empty table + capacity-as-bipartite-pipeline model was confirmed |
| D2 | Command = `skill verify <bundle>`; engine takes a capacity set (`--all` wrapper) | — |
| D3 | State source = **C** (read persisted Global + single Local directly, no reactivation); two views reconciled, A2′ dedup, scope-aware | Reversed from "reconstruct clean-room" after confirming L3 is persistent (F9). "Which Locals" collapsed after confirming single-tenant |
| D4 | Bundle attribution via **manifest `[l3]`** ("A"); forward drift L3+L2 → DEFECT, reverse-L2 → WARN, reverse-L3 undetectable | Skill-as-graph ("B") deferred to make attribution structural |
| D5 | Falkor-down → **refuse whole-command**; no fallback | Reversed from "per-check gating, mostly Falkor-free" once the core became persisted-read |
| D6 | Chain query = **neutral** severity, per-capacity line + rollup | — |
| D7 | Code-scan = **AST**, bundle modules, confidence-labeled | Schema-check surface corrected to core/L2 `Schema` (not `write_handle.validate_node`) |
| D8 | Metrics = broken-atomic + task-unmapped + code-scan hit-rate; **drop** provenance-less count | — |
| D9 | Unit-per-check + `InMemoryClient` e2e; **no fixture edit**; IntergraphEdge round-trip probe gates D3=C | Reversed from "seeded in-memory only" once D3 became persisted-read |
| D10 | Maintenance chat, **no numbered phase / no version bump**; persister fix forks out only if the D9 probe fails | No new ADR required |

## 12. Probe corrections (anchors that were wrong)

- `write_handle.validate_node` is **role-gated** (only `episodic_memories` /
  `problem-trace` adapters) → cannot validate bundle L2 roles. Use core/L2
  `Schema`.
- **L3 is persistent** (F9 `FalkorDBLocalPersister`); the stale in-tree notes
  ("no persisted Global capacity state" in `check_phase_42_bipartite_state.py`;
  "FalkorDBLocalPersister unshipped at Phase 36" in `mindsos_capacity/__init__.py`)
  lag F9 → worth a cleanup flag.
- Boot pattern: `KnowledgeLayer.bootstrap()` + `CapacityLayer(kl=kl)` +
  installers (from `capacity.py::_construct_invoke_layer`); real-state variant via
  `persistence/bootstrap.py` + `local_boot`.
- Refusal pattern: `persistence.py::_refuse_with` (red error + `typer.Exit`).
- `records.py`: `SkillRecordView` + `iter_skill_records(kl)` /
  `latest_records_by_bundle(kl)` confirmed.
- **`promoted-pipelines` has no live writer** → the original task's headline
  traversal was against an empty table.
