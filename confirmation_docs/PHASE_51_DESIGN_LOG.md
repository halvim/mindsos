# PHASE 51 (WSD-1) — Design Log

**Status:** R0 CLOSED 2026-06-10 (two reanalysis rounds, all picks user-accepted, zero reversals of the WSD design closure). Implementation pending (PR1 → PR2).
**Scope authority:** `WSD_INSTALLATION_PHASE_MAP.md` §2 WSD-1 row (verbatim); decision record `WSD_INSTALLATION_DESIGN_LOG.md` §1 PB-W2 / §2 PB-W14-W15 / §4 PB-W21 / §5 R3.
**Prereqs verified:** tag `phase-50-confirmed` present; WSD closure docs on `main` (`379a46e`; tip `ac30642`); untracked robot-demo corpus noted (selective staging only); 51 > high-water 50 → **full 10-surface bump**.

---

## §1 — R0 round 1 (pushbacks PB-51-1…8; all picks ACCEPTED by Henrique 2026-06-10)

| # | Surface | Pick |
|---|---|---|
| PB-51-1 | EdgeType property sketch missing the argument-role dimension (Resnik triple = sense/role/class) | **(b) Per-role EdgeTypes** `SEL_ASSOC_NSUBJ`/`SEL_ASSOC_DOBJ`/`SEL_ASSOC_IOBJ` — rel-type-filtered traversal + index-friendly; obliques additive at v2. Retro-validated at round 2: `role` is in `RESERVED_PROPERTY_KEYS` — option (a) role-as-property would have been rejected by `validate_user_properties`. |
| PB-51-2 | MFS prior has no home (grounded: zero frequency/rank data in shipped lexicon; OEWN importer drops sense ordering) | **(a)** Per-Sense node property `corpus_frequency` (INT) named in ADR-0184 §5; Phase 52 populates from SemCor; absence semantics = Phase-53 contract. |
| PB-51-3 | "DOLCE stratum reserved" geometrically unreservable in lexicon (ontology nodes unreachable by intra-graph edges) | **(a)** Stratum reserved by *name only*; home undecided (likely alignment-anchor); settled at Phase 56 R0 with the DWF density number. ADR-0184 §8. |
| PB-51-4 | Edge identity per corpus + smoothed-score staleness | **(a)** One edge per (sense, role-type, class, source-corpus); promotion **appends** (`source="promotion"`), never mutates; scorer sums parallel edges, GlossTag down-weight applied at read from `learned-parameters`. `smoothed_score` recompute owner = Phase-55 promotion application. ADR-0184 §4. |
| PB-51-5 | L3-59(b) grounding corrections | **(a)** Drop the consumer-less public `context` kwarg from `invoke`; always build typed `CapacityContext` (parity with write branch, which already ignores caller context). Corpus correction: production dict accesses are docstring-only; test corpus = **3 files** (phase_30/33/34), not 1. ADR-0175 §amendment-3. |
| PB-51-6 | The xpassed orphan probe is structurally blind to inbound XRefs (keys on alice's own ids; sweep clears `source_metagraph_id` only) | **(a)** Extend the probe (inbound-XRef, tombstone variants, satellite coverage) + small in-slot Cypher fixes if confirmed; then promote xfail→contract. Fallback (b): document + keep xfail + ledger with evidence if inbound-ref semantics turn out load-bearing (cross-user read-grant may legitimately tolerate dangling refs — contract decision, escalate if hit). |
| PB-51-7 | PR split | **Keep 2-PR seam:** PR1 = L3-59(b) + L0-25 riders (behavior-neutral, isolates refactor gate-risk); PR2 = empirical-layer schema + ADR-0184. |
| PB-51-8 | Endpoint restriction on new EdgeTypes | **Restrict** `Sense→Synset` (deliberate deviation from lexicon any→any; membership enforced even at `strict=False` per Phase-50 I5). |

## §2 — R0 round 2 (deeper grounding; PB-51-9/10 ACCEPTED 2026-06-10; saturation declared)

**Retired risk:** edge persist is id-keyed MERGE with `e += row.props` (`cypher/builders.py:177`) — parallel co-typed edges round-trip safely, properties included. PB-51-4(a)'s R1 verification need is closed pre-impl.

| # | Surface | Pick |
|---|---|---|
| PB-51-9 | New types break two phase-13 pins (`test_seed_schemas` set-equality; `test_dimensional_snapshot` count) | **(a)** Separate `LEXICON_EMPIRICAL_EDGE_TYPES` tuple; builder registers both; pins update to union/new count (Phase-41 export-slate precedent). Structural tuple untouched. |
| PB-51-10 | Read-path `CapacityContext` ships empty `learned_parameters_snapshot`; Phase 53 would rediscover it | **(a)** ADR-0175 §amendment-3 clause 5 states it: CLI/direct-invoke = empty snapshot → static defaults; L4 dispatch = populated path. No KL-backed snapshot read in `invoke` (consumer-less forward-shape; CR-2/CR-3 discipline). |

**Impl-notes (recorded, no options):**
1. Edge property bags bypass the ADR-0182 codec (node-`value`-only) — empirical props Falkor-primitive only (ADR-0184 §6).
2. ADR-0146 §am-1 cl.2 read-path session injection dies with the dict path — no separate 0146 amendment (write consumers migrated Phase 48; grep-zero read consumers). Stated in ADR-0175 §am-3 cl.3.
3. All five property names (`count`/`smoothed_score`/`source`/`corpus_version`/`corpus_frequency`) verified clean against `RESERVED_PROPERTY_KEYS`.
4. **Amendment-home correction:** the L3-59(b) closure amendment belongs on **ADR-0175** (carrier of the §am-1/§am-2 staging trail + A1 deferral), not ADR-0159 as round 1 first stated.

## §3 — ADR roster (drafted at R0, pre-code, per HANDOFF §9 R1-step-0 parity discipline)

1. **ADR-0184** — `docs/decisions/adr/0184-lexicon-empirical-layer-edge-vocabulary.md` (new).
2. **ADR-0175 §amendment-3** — read-half migration executed; union retired; PB-23 fully closed.

## §4 — PR plan

- **PR1 (riders, behavior-neutral):** ADR-0175 §am-3 implementation — `capacity_layer.invoke` typed read context + `context` kwarg removal + union drop in `runtime.py`/`capacity.py` + docstring cleanup + phase_30/33/34 test migration. L0-25: probe extension (inbound-XRef/tombstone/satellite), sweep fixes if small, xfail promotion (or fallback (b) with evidence). `tests/phase_51/` sentinels.
- **PR2 (schema):** `lexicon.py` `LEXICON_EMPIRICAL_EDGE_TYPES` + endpoint-restricted registration + `property_types` declarations + phase-13 pin flips + ADR-0184 sentinel tests + ADR-0182-path round-trip test (unit `InMemoryClient`; live-marked Falkor variant).
- Then: 10-surface bump 50→51, squash, gate (Linux docker, cumulative), 6-step confirm, `PHASE_51_CONFIRMED.md`, tag `phase-51-confirmed`, closure edits (HANDOFF §3.1.x, CLAUDE.md downstream paragraph, WSD phase-map §2 row → SHIPPED).

## §5 — Scope discipline

Nothing pulled forward from `WSD_INSTALLATION_PHASE_MAP.md` §3 ledger. No ADR-0150 amendment (closed set stays 13). No runtime-writer surface (PB-W21). Phase-52+ surfaces (importers, indexes, scorer) named but not built.

## §6 — Implementation record (Cowork-side complete 2026-06-10; gate pending)

**PR1 (riders) as shipped:**
- `capacity_layer.py` `invoke`: unified typed-`CapacityContext` construction for read AND write bodies (one builder; `writeable` only when `declaration.outputs` is empty); `context` kwarg REMOVED; docstrings rewritten. `runtime.py` + `capacity.py`: union annotation → `Optional[CapacityContext]`; `Union` imports dropped; `call_capacity` docstring updated. Docstring stragglers cleaned (`context.py`, `builtins/consolidate.py`, `builtins/trace.py`) so the grep-zero sentinel is strict (no allow-list).
- Tests: `tests/phase_30/test_invoke_session_user_id_in_context.py` re-pinned to attribute form + placeholder-identity contract; `tests/phase_33/test_invoke_session_context_injection.py` re-pinned to the INVERSE contract (no `session` field on the context, by field roster — ADR-0170); `tests/phase_34` docstring only (its tests ride the write path, already typed). NEW `tests/phase_51/test_adr_0175_am3_read_context.py` (6 sentinels: typed read ctx, kwarg removal, union retirement via annotation introspection, source-level grep-zero walker, frozen-ctx, empty-snapshot).
- L0-25: audit complete (§7 table below); orphan test xfail REMOVED → contract + extended (seeds tombstone + outbound XRef via the real builders); NEW `test_live_delete_spares_inbound_xrefs_by_design` pins the survivor contract. `L0_FUTURE_WORK.md`: L0-25 closed, **L0-27 added** (stamp `target_stale` at referent-delete; trigger: first cross-user XRef consumer). `L3_FUTURE_WORK.md` L3-59(b) → CLOSED; **PB-23 closed in full.**

**PR2 (schema) as shipped:**
- `mindsos_knowledge/schemas/lexicon.py`: `EDGE_SEL_ASSOC_NSUBJ/DOBJ/IOBJ` + `LEXICON_EMPIRICAL_EDGE_TYPES` (separate tuple) + `EMPIRICAL_EDGE_PROPERTY_TYPES` (INT/FLOAT/STRING/STRING) + `SENSE_PROP_CORPUS_FREQUENCY`; builder registers the stratum endpoint-restricted `Sense→Synset` with declared `property_types`. Pins flipped: `test_dimensional_snapshot` lexicon edges 22→25; `test_seed_schemas` set-equality → structural ∪ empirical.
- NEW `tests/phase_51/test_adr_0184_empirical_layer.py` (8 hermetic sentinels incl. endpoint-violation rejection at `strict=False` + persist-statement shape) + `test_adr_0184_live_round_trip.py` (integration-marked: §3 property set + `corpus_frequency` + PARALLEL co-typed provenance edges through `MetagraphRepository`→`MetagraphLoader`; model assumptions pre-verified in-memory).

**10-surface bump 50→51** (first slot > high-water 50): 8 package `__version__` + `pyproject.toml` + `docker-compose.yml` tags + `manifest.toml` phase/version + 3 export-slate sentinel literals. Residual `phase50` grep-zero across all bump surfaces.

**Sandbox verification (py3.10; docker gate canonical):** capacity corpus 244 passed (phases 29/30/33/34/41/42/45 minus CLI-dep files); phase_13 relevant 123 passed; phase_14/39/43 281 passed; phase_51 13 passed + 1 live-skip; export slates green. Pre-existing sandbox-only failures (NOT this phase): `test_image_completeness_phase13` (`/app` docker path) + `test_knowledge_schema_cli` (no `typer`) — I9 pattern.

**I-findings:**
- **I1 (favorable, corpus smaller than mapped):** production dict-form context accesses were docstring-only; the phase-map's "phase_34 test updates" actually meant phase_30/33 (phase_34 rides the write path). Zero strict-signature capacity bodies anywhere in tests (AST census) — always-passing context is ripple-free.
- **I2 (L0-25 audit verdict):** sweep complete for owner-scoped rows; the PHASE_44 §7 metaedge/metahyperedge/XRef worry dissolves under per-kind grounding (§7). Inbound XRefs = by-design survivors (ADR-0135 `target_stale`); cross-metagraph sweeping would bypass the foreign mutex/WAL → L0-27.
- **I3 (env):** sandbox needed `pip install tomli pytest` (py3.10, no tomllib); recurring I9-class note.

## §7 — L0-25 per-kind sweep audit (grounded in `cypher/builders.py` + `local_persister.delete`)

| Element kind | Storage shape | Swept by | Verdict |
|---|---|---|---|
| Node | `:Node` + `IN_GRAPH` | stmt 1 (`DETACH DELETE el`) | ✓ |
| Edge | relationship Node→Node | dies with endpoints (stmt 1) | ✓ |
| HyperEdge | `:HyperEdge` + `IN_GRAPH` | stmt 1 | ✓ |
| MetaEdge | relationship Graph→Graph | dies with graphs (stmt 5) | ✓ |
| MetaHyperEdge | `:MetaHyperEdge` + `IN_METAGRAPH` | stmt 4 (anchor satellites) | ✓ |
| IntergraphEdge | relationship Node→Node | dies with endpoints (stmt 1) | ✓ |
| IntergraphHyperEdge | `:IntergraphHyperEdge` + `IN_METAGRAPH` | stmt 4 | ✓ |
| WALEntry | `:WALEntry` + `IN_METAGRAPH` | stmt 4 | ✓ |
| Tombstone | `:Tombstone {graph_id, element_id}` (graph-scoped by construction, P69 A; metagraph-level elements use property stamps, never tombstones) | stmt 2 | ✓ |
| XRef (outbound) | `:XRef {source_metagraph_id}` + `XREF_OF`→anchor | stmt 3 (+ stmt 4 redundantly) | ✓ |
| XRef (inbound) | foreign metagraph's row, `target_metagraph_id` = deleted mid | **not swept — correct** (foreign-owned; ADR-0135 dangling-target model) | pinned survivor → L0-27 |
