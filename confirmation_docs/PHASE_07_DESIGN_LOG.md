# Phase 07 Design Log

**Status:** Locked design (chat dated 2026-05-12).
**Target:** Phase 07 row text in `confirmation_docs/PHASE_MAP.md` §5 lines 1875+ (replaced the 7-line stub).
**Scope:** L1 Persistence — `Client` / `FalkorClient` / `InMemoryClient` / `AsyncClient` / repositories / WAL / indexes / OCC / 5-bucket integrity scanner / single-Graph round-trip / 5-verb CLI subapp.
**Cascade position:** `05a → 05b → 05c → 05d → 06 → 07`. CASC-1 unblocked 07 when Phase 06 shipped (tag `phase-06-confirmed` on main; 1127 + 2 skipped in-container).

---

## Pre-flight audit (resolved 2026-05-12)

The prompt's load-bearing claims were audited against on-disk truth:

| Claim | Verdict | Evidence |
|---|---|---|
| "ADR files don't exist on disk" | **FALSE** | All in-scope ADRs (0030 / 0121 / 0122 / 0123 / 0126 / 0127) present at `docs/decisions/adr/`. The Phase 06 P45 B claim "verified via Glob" was either stale or wrong-Glob (early Glob calls in this chat returned empty for paths that exist). |
| "Phase 07 introduces persistence" | **PARTIALLY MISLEADING** | v3 baseline at project-root `mindsos_core/persistence/` ships ~8 modules with substantial coded surface (Client + FalkorClient + InMemoryClient + AsyncClient + bootstrap + GraphRepository + MetagraphRepository + WAL + integrity). Phase 07 is the **slim port** of these into `halvim_mindsos/mindsos_core/persistence/` (which currently has no `persistence/` directory). |
| "Phase 06 IMPLEMENTATION_LOG references" | **FALSE** | `PHASE_06_IMPLEMENTATION_LOG.md` does not exist on disk; only `PHASE_06_CONFIRMED.md` (which itself contains the round-7 reshape ledger inline at lines 50-87). |
| InstanceRepository "doesn't exist in Phase 06" | **PARTIALLY TRUE** | v3 baseline has `mindsos_instances/persistence/instance_repository.py`; Phase 06 slim ships `mindsos_instances/` WITHOUT the persistence subpackage. Phase 07 ports it (P11 A; M9 boundary). |
| `_version` field on Node | **TRUE** | Already shipped per Phase 04 row Risks line; field exists in v3 baseline at `mindsos_core/models/node.py:37`. |

**Implication:** Phase 07 is a **slim port + glue + 5-verb CLI** phase, not a "build from scratch" phase. The v3 baseline is the source material; halvim_mindsos is the target.

---

## Meta-plan locks (M-series) — 4 passes, user agreement explicit

These govern the chat itself, not the row content. Each pick was challenged 4 times via "agree, push back again" — final state reflects converged decisions.

### M0 — JSON state-file disposition.
**Pick: B (backend-only).** Through 2 reversals: originally locked D (thin-manifest, state-file v=5); reverted to B after surfacing that thin-manifest forces a Phase 03-05a CLI rewrite. **Phase 07 ships pure backend addition; JSON files unchanged at v=4/v=2/v=1.** New `mindsos persistence sync` verb projects JSON → FalkorDB on demand.

### M1 — v3 baseline disposition.
**Pick: A (adopt-and-slim-port).** Matches PHASE_MAP §1 "Repackage existing code." Includes `cypher/builders.py` (~200 LOC) per round-3 P15.

### M2 — Phase split.
**Pick: B (single Phase 07).** Through 1 reversal: originally split 07a/07b; collapsed after M14 + M15 trimmed test budget to fit 110-160 added tests per single-phase 05a-06 precedent. CASC-1 cadence preserved (single 3-day cadence vs 6-day split).

### M3 — ADR re-litigation policy.
**Pick: A (status flips + write `core.md`).** Overrides Phase 06 P45 B precedent for the 4 specific ADRs (0122/0123/0126/0127). User instruction 2026-05-12: "ADR decisions can be changed if decided in this chat." Status flips Proposed → Accepted; ADR file edits land in 07 (not Phase 38).

### M4 — Round count target.
**Pick: C (open-ended; soft target 6).** Actual stop: 3 rounds + Round-3 §4 "well dry" honest acknowledgment. Total picks: M0-M15 + P-pre + P1-P25.

### M5 — OCC `_version` wiring.
**Pick: 07.** OCC field already exists on Node per Phase 04 deferral; Phase 07 wires the `expected_version` parameter on `update_*_properties` per ADR-0127.

### M6 — `diagnose` + `verify` scope.
**Pick: minimum.** 5-bucket scanner unchanged from v3; 3 distinct CLI verbs (`diagnose` / `verify` / `inspect-state`). No `--repair` (Phase 11).

### M7 — Pivot/Global vs Local policy.
**Pick: mechanism only.** `expected_version` opt-in per call site; L1 has no Global/Local distinction. L0/L2 wire enforcement.

### M8 — Reading scope cadence.
**Pick: trimmed.** Drop `feedback_tag_regex_audit`, `feedback_release_workflow_ordering` for design rounds; bring back at handoff-prompt drafting.

### M9 — InstanceRepository carry-forward.
**Pick: C (observer-driven persist).** Single `after_persist(mg)` callback on `Metagraph`. Instances persist sibling-side via the observer. Preserves Phase 06 P49 B Core/instances boundary (Core doesn't import `mindsos_instances`).

### M10 — Test layout.
**Pick: existing `tests/phase_07/`.**

### M11 — InMemoryClient fidelity gap (NEW).
**Pick: A.** `pytest.mark.integration` marker for round-trip / FalkorDB tests; unit tests use call-recorder InMemoryClient unchanged.

### M12 — `confirm-phase` timeout (NEW).
**Pick: B.** 600s → 900s. Phase 06 ran 578s; Phase 07 adds integration tests; headroom needed.

### M13 — Rollback hazards (NEW).
**Pick: B (round 3).** `persistence reset --force` deferred to Phase 11 (where rich integrity scanner can verify-before-wipe). Phase 07 originally had `reset --dry-run`; renamed to `inspect-state` per round-2 P13 B.

### M14 — Test-scope split (NEW; pass 3).
**Pick: A → revised to graph-only in Round-2 P12 D.** Phase 07 ships single-Graph round-trip (save + load); Phase 08 ships metagraph save + load + streaming + refresh.

### M15 — FalkorDB per-test isolation (NEW; pass 3).
**Pick: A.** Per-test fresh FalkorDB graph named `test_<uuid_hex8>`. Compose sidecar already running; fixture in `tests/_shared/falkordb_fixture.py`.

### P16-pre — Tombstone-write scope.
**Pick: A.** Ship write-side tombstone primitives in 07 (`build_create_tombstone`, `remove_node`/`remove_edge`/`remove_hyperedge`). Soft-delete read-path filter deferred to Phase 10.

---

## Critical architectural distinction (load-bearing — read before any 07 decision)

Two persistence stories pre-existed:

1. **v3 baseline** (`/Layered Intelligence/mindsos_core/persistence/*`) — FalkorDB-backed; written but never reaches halvim_mindsos slim tree.
2. **Halvim_mindsos slim** (Phase 02-06 shipped) — JSON state files at `~/.mindsos/<kind>-<name>.json`. No FalkorDB integration; CLI verbs operate on JSON files directly.

**Phase 07 model (M0 B):** keep both. JSON stays authoritative for Phase 03-05a CLI verbs; FalkorDB becomes the queryable projection populated via the new `persistence sync` verb. Existing CLI surface unchanged. Phase 08 introduces FalkorDB-side reads via metagraph_loader + streaming; Phase 09+ may organically flip read paths.

**Architectural consequence:** the new `mindsos persistence` subapp is a SEPARATE CLI surface from the existing `mindsos graph` / `mindsos metagraph` / etc. verbs. Testers explicitly opt into FalkorDB by running `sync`. JSON files remain the single source of truth for tester ergonomics.

---

## Round 1 pushbacks (P1–P8) — LOCKED 2026-05-12

### P1 — CLI subapp shape.
**Pick: C.** 5 verbs (`sync` / `load` / `diagnose` / `verify` / `reset --dry-run`). Bootstrap implicit on Client construction. Smallest viable surface.
*Subsequent revision:* round-2 P13 B renamed `reset --dry-run` → `inspect-state`. Final 5 verbs: `sync` / `load` / `diagnose` / `verify` / `inspect-state`.

### P2 — Bootstrap invocation model.
**Pick: A (lazy).** Every `FalkorClient.__init__` calls `bootstrap(client)`. Idempotent; ~50ms cost in noise of any Cypher round-trip. Tester never sees a "you forgot to bootstrap" error.

### P3 — `persistence sync` scope.
**Pick: B (graph + metagraph).** Both graph-scoped and metagraph-scoped sync ship.
*Subsequent revision:* round-2 P12 D **REVERSED** to graph-only. Symmetric with M14's graph-only load.

### P4 — Connection lifecycle in CLI.
**Pick: A (per-command).** Open / run / close per CLI verb invocation. Matches Phase 02-06 stateless precedent. No `atexit` (B) fragility; no `--keepalive` (C) YAGNI.

### P5 — FalkorConfig source.
**Pick: C (env + manifest hybrid).** Env wins; manifest fallback for host-side `confirm-phase` runs.
*Subsequent revision:* round-2 P15 A clarified: manifest section holds connection meta (host/port/username/graph); password env-only.

### P6 — Repository instantiation.
**Pick: A (direct).** `GraphRepository(client)` per v3 pattern. Caller manages client lifecycle.

### P7 — `_version` propagation rule.
**Pick: C.** `_version` ALWAYS bumps on update path; OCC enforcement opt-in via `expected_version` parameter. `expected_version=None` skips OCC check but still bumps `_version`. Mechanism shipped; policy stays L0/L2.

### P8 — `_props_json` writer contract.
**Pick: A (writer 07; reader split per M14).**
*Subsequent revision:* round-2 P9 C narrowed scope — `_props_json` ships for Metagraph only; Graph .properties writer skipped per PHASE_MAP §7 Q4 deferral.

---

## Round 2 pushbacks (P9–P16) — LOCKED 2026-05-12

### P9 — Graph property-bag (BLOCKS P8 A).
**Pick: C.** Skip Graph .properties writer in 07; Metagraph .properties writer ships per ADR-0130. Asymmetric but bounded. Closes when PHASE_MAP §7 Q4 resolves (Phase 10 likely).
**Rationale:** Graph .properties not yet shipped in halvim_mindsos slim (deferred per §7 Q4). Pulling forward would break M0 B (state-file v=4 → v=5 bump). Skipping both would violate ADR-0130 for Metagraph.

### P10 — `_version` scope.
**Pick: A.** `_version: int = 1` field added to ALL six core element types (Node already has it; Edge, HyperEdge, MetaEdge, MetaHyperEdge, IntergraphEdge, IntergraphHyperEdge gain it). Avoids state-file ambiguity from backfilling later.

### P11 — Instance `_version`.
**Pick: A.** Adds `_version` field to `ElementInstance` + `CompositeInstance` (mindsos_instances side). Instances ARE persisted as labeled nodes — FalkorDB doesn't distinguish "real" Node from "ElementInstance." Skipping creates OCC blind spot. Cross-package coupling (mindsos_instances `__version__` bumps too).

### P12 — `load --metagraph` asymmetry with `sync --metagraph`.
**Pick: D.** **REVERSES Round-1 P3 B.** Phase 07 is now strictly graph-scoped for BOTH sync AND load. Metagraph sync + load both land in Phase 08. Symmetric scope beats partial functionality.

### P13 — `reset --dry-run` awkward name.
**Pick: B.** Rename to `inspect-state` (purely descriptive). `reset --force` lands Phase 11 with rich integrity scanner.

### P14 — `verify` vs `diagnose` overlap.
**Pick: A.** Keep 3 distinct verbs (`inspect-state` / `diagnose` / `verify`). Audience clarity > surface savings.

### P15 — Manifest password security smell (reconsiders P5).
**Pick: A.** Manifest `[falkordb]` holds connection meta (host/port/username/graph); password env-only. Split convention; matches other tools.

### P16 — `requirements.txt` + lockfile parity.
**Pick: A.** Standard workflow: `tools/lock.sh` regen; manifest sha256 bump; doctor self-test parity check fires until tester reruns.

---

## Round 3 pushbacks (P17–P25) — LOCKED 2026-05-12

### P17 — `load --graph X` authority inversion.
**Pick: C.** Default stdout summary; `--to-json` opt-in overwrites `~/.mindsos/graph-<name>.json`. Preserves M0 B JSON authority; opt-in flag for tester accepting FalkorDB-side state.

### P18 — `sync --graph X` re-sync semantics.
**Pick: D.** Additive default (MERGE-on-id); `--replace` opt-in for DETACH DELETE + rewrite. Matches MERGE semantics; explicit flag for destructive case.

### P19 — `verify` data source.
**Pick: C.** `verify --source=memory|db`; default `memory`. Both sources accessible; default matches Phase 02-06 JSON-driven expectations.

### P20 — WAL mid-batch crash simulation.
**Pick: B.** `RaisesOnNthCall(real_client, n=3)` test wrapper in `tests/_shared/raises_on_nth_call.py`. ~10 LOC. Tests real WAL flow without subprocess fragility.

### P21 — Exception hierarchy port scope.
**Pick: A.** Port 5 persistence-specific exceptions to `mindsos_core/exceptions.py`: `PersistenceError` / `IntegrityCheckError` / `OptimisticConcurrencyConflict` / `OptimisticConcurrencyExhausted` / `MissingExpectedVersionError`. Skip rest of v3's exceptions (Phase 09/10/11 territory).

### P22 — Round-trip test equality semantics.
**Pick: C.** Test-side `tests/_shared/graph_equality.py:assert_graphs_equal` helper. Equality belongs in tests, not production. Phase 07 doesn't commit to a `structurally_equal` contract for downstream.

### P23 — `falkordb` Python package version pin.
**Pick: A.** Latest as of Phase 07 implementation; tester runs `tools/lock.sh` to capture.

### P24 — `docs/dev/internals/core.md` section structure.
**Pick: B.** Single "Persistence layer" section with subsections per concept (Substrate / WAL / Indexes / AsyncClient / OCC). Reader-centric framing.

### P25 — Sentinel paths additions.
**Pick: A.** Eager 14 entries at row-implementation time. Per `feedback_new_top_level_package.md` 5-site checklist.

---

## Convergence note

Round 3 §4 honest acknowledgment: pushback well is dry. Round 1 produced 8 picks; Round 2 produced 8 (1 reversal — P12 D); Round 3 produced 9 (1 minor flag). Each round's reversals smaller. Remaining unknowns are row-text-internal (exact Cypher in bootstrap DDL, exact JSON output shape, exact test names). Those belong to implementation chat.

User confirmed convergence with "confirmed... proceed" 2026-05-12.

---

## User overrides

None at the M-pick level; none during P-series rounds. User agreed with each pass-3 pushback set.

**Implicit override:** the user's 2026-05-12 instruction "ADR decisions can be changed if decided in this chat" reversed the Phase 06 P45 B precedent for the 4 specific ADRs (M3 A). This is documented as Final Amendment item 45 in the row text.

---

## Cross-chat dependencies

**Forward (Phase 07 produces):**
- 6 new modules in `mindsos_core/persistence/`.
- 2 new modules in `mindsos_core/reconstruction/`.
- 1 new module in `mindsos_core/cypher/builders.py`.
- 1 new module in `mindsos_core/config.py`.
- 2 new modules in `mindsos_instances/persistence/`.
- 1 new CLI subapp in `mindsos_cli/commands/persistence.py`.
- 4 ADRs flipped Proposed → Accepted.
- 1 new doc section in `docs/dev/internals/core.md`.
- 6 new doc pages (`docs/usage/core/persistence.md`, `docs/api/core/client.md`, `docs/api/core/repositories.md`, `docs/api/core/wal.md`, `docs/api/core/integrity.md` + amend `core.md`).
- 14 sentinel-paths additions.

**Backward (Phase 07 consumes):**
- v3 baseline at `/Layered Intelligence/mindsos_core/persistence/` (slim-port source).
- Phase 06 `register_remove_observer` pattern (mirror for `register_persist_observer`).
- Phase 06 `attach_registry(mg)` idempotent helper (extends to subscribe persist observer).
- Phase 04 `_version` field on Node (extend to other element types).
- ADRs 0030 / 0121 / 0122 / 0123 / 0126 / 0127.

**Unblocks:** Phase 08 (metagraph loader + streaming + refresh) per CASC-1.

---

*End of PHASE_07_DESIGN_LOG.md. Implementation chat consumes this + the row text in PHASE_MAP.md §5 + the NEXT_CHAT_PROMPT.md handoff.*
