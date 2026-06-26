# Bongard demo — proposed core changes (implementation log)

**Status:** log · 2026-06-20 · the separate file RULES requires for any `mindsos_*` alteration this demo motivates.

## Discipline

This demo is a forcing-function (§0 of PLAN.md). When it surfaces a missing/weak core capability:

1. **Prefer a demo-side shim** (subclass / extension / Local registration) that proves the shape without touching core. The shim *is* the proof-of-shape for the core chat.
2. **If core code must change, ship it as a patch** (Henrique 2026-06-20): a patch file under `projects/bongard_demo/core_patches/` applied to **this demo's instance only** — **never committed to `demo/bongard`'s `mindsos_*`** (keeps CI green + the phase50 pin honest). The patch is the upstream candidate.
3. **Log the native core design + the patch here** (this file) for later implementation into core, if approved.

Bar for inclusion (point 3 of the 2026-06-20 directive): **"a better general way to do things, reusable in future"** — *not* "Bongard needs it to run." Instance-specific needs stay demo-side and are out of scope for this log.

Rationale for each item lives in PLAN.md §13; this file tracks **implementation state**.

## Log

| ID | Change | Native-core? | Demo-side shim? | Prototype status | Approved for core? |
|---|---|---|---|---|---|
| **CC-1** | Capacity-node persistence (`bootstrap_capacity_from_falkordb` round-trip of `_capacity_index`) | yes | yes — persist composite **structure** to `promoted-pipelines`, rehydrate at boot | **LANDED on `main` 2026-06-22 (reshaped, better)** — F9 (`1be3a70`) + composition-lifecycle (`b56e0ac`): `FalkorDBLocalPersister`+`load_or_mint_local`/`boot_local`/`reactivate_local_capacities`, composite DAG→`learned-parameters` descriptor + `COMPOSITE_DAG`+`composite_dependencies` + `kahn_sort` dep-order in `local_boot.py` | **YES (in core, non-phase feat)** |
| **CC-2** | Composite capacity `node_kind` + generic composite-runner (declarative pipeline-over-seeds body) — **linchpin** | yes | yes — `CompositeCapacity(_CapacityBase)` whose Python body runs the stored pipeline via `cl.invoke` | **SUBSTRATE LANDED (`b56e0ac`)** — `PipelineDAG`/`DAGStep`/`DAGEdge`+`Finder`/`BFSFinder`/`ConjunctionFinder`+typed `input_group`. Composite `node_kind` **deferred** (KIND_REACTIVE suffices). **RUNNER = demo-side by design** (F9: factory + executor closure re-supplied at boot) → **D-M2-a** | **partial — substrate in core; kind deferred; runner is consumer's** |
| **CC-3** | `promote_capacity` (Local→Global) verb — node + backing pipeline + params, atomic, via `pending-promotions`, admin-gated | yes | **build against the ADR-0184 seam (m5)** — NOT a verb. Two halves: (1) descriptor via `PromotionItemKind.PIPELINE` propose/release pivot (`mindsos_admin.promotion`/`mindsos_server.release`, currently `NotImplementedError`); (2) Global-scoped `reactivate_from_descriptors` to make the promoted node runnable. Do NOT route via skill-install (ADR-0183). Open dep: Part 5 operand-arity | **design-only (ADR-0184 written, no code); m5 is the writer** |
| **CC-4** | L4 substrate auto-loads `learned-parameters` into `CapacityContext.learned_parameters_snapshot` at dispatch | yes | yes — demo dispatcher pre-loads the snapshot | **UNCHANGED** — `capacity_layer.invoke` still `{}`; out-of-scope per core log §6 (consumes the mechanism). Remains the G4 demo-wiring item | not in core; demo-side |

**WSD-decouple asks (D1–D5):** RESOLVED **architecturally** by COMPOSITION_LIFECYCLE_DESIGN_LOG §0 ("subsystems consume, core owns; promotion lands in core, WSD = producer not owner") — not as lifted code. Mechanisms (promotion loop, ALS, index, real L4 catalog flip) ship when a consumer forces them. The outcome wanted (no text-chat gating non-text consumers) is secured by the placement principle.

**Deferred (not proposed now):** CC-5 runtime alignment-dedup consumer (admin gate covers v1); CC-6 generalized backtracking lifecycle (let the demo prove the shape first).

**Part 5 (DataState operand-arity / role axis) — ROUTED AROUND by m3, not forced (2026-06-25).** m3 relations would be the natural consumer that justifies the deferred composition-lifecycle-s2 Part 5 (STATE.json `pending_designs`: "hits every comparator same_object/same_shape/moved/touching"; "real executing consumer = TBD"; reopens ADR-0156 edge model **+ invoke inputs keying**). m3 **does not force it.** A role-labeled multi-shape *input* hyperedge IS Part 5 by another name — the body gets `**inputs` keyed by DataState IRI, so two `SHAPE`s collide regardless of the topology edge; the real change is invoke-keying-by-role. Part 5's payoff (auto-wiring a binary capacity into a pipeline from topology alone) is for **WSD/L4, which auto-wire**; Bongard demo control assembles the scene by hand and never auto-wires → the topological role axis is dead weight here. **m3 decision (PLAN D-M3-1):** relations consume ONE `bongard.scene` collection (one CONSUMES, no collision) and emit role-labeled relation hyperedges as *output data* (subj/obj explicit + auditable, no core change). Part 5 stays a real WSD/L4 core need; the Scene-collection worked example informs it later (CC-6 "demo proves the shape first" pattern). **Owner: none in this demo — demo-side route.**

**The CC-1/2/3 triad — landed status (2026-06-22 final):** CC-1 done; CC-2 substrate done + runner demo-side (D-M2-a); **Part 6 done + tagged** (`composition-lifecycle-s2-confirmed` = `2676b9d`) → **D-M2-b RETIRED** (core `invoke` validates input presence; runner drops its self-check, lets `InputContractError` surface); CC-3 = ADR-0184 design-only seam, built at m5. **Milestone 2 (Local mint + restart) is fully core-unblocked** — remaining gate is the Mac-side pin-bump to `composition-lifecycle-s2-confirmed`; only the Global-promotion tail (m5) waits on the ADR-0184 seam + Part 5.

**m4 (concept search + held-out verify) — NO core dependency (2026-06-26).** SHIPPED entirely demo-side and in-memory on the pinned core (`evaluate_concept` rides the lazy `CATEGORY_PREDICATE`; `Capacity` + `register_datastate(allow_new_realm=True)` only; search/verify = demo control). Pin unchanged. **m5 (concept-mint) reopens the core surface:** the concluded concept becomes a *minted* artifact → it needs the m2 mint machinery (learned-parameters descriptor + reactivation) for a concept predicate, and Global promotion = the **CC-3 / ADR-0184 seam** (still design-only) with the **Part-5 operand-arity** dependency to confirm before sizing the promotion descriptor. Verify both against the tree at m5 R0.
