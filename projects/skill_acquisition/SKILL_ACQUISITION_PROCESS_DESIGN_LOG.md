# SKILL_ACQUISITION_PROCESS — Design Log

**Status:** CLOSED 2026-06-09 (R1 accepted + R2 reversal-free; see §5). Phase-map on disk.
**Chat type:** downstream design-authoring (PB-A); deliverable = this log + `SKILL_ACQUISITION_PROCESS_PHASE_MAP.md`. No product code ships from this chat except as routed by the phase-map.
**Prereqs verified:** tags `phase-49-confirmed` + `maintenance-2026-06-09` present; `main`-tip `a13aaac` (post-MAINTENANCE gate record `8256299`). Untracked robot-demo/prototype corpus noted — selective staging only.
**Inputs:** `projects/ANALYSIS_DELTA_2026-06.md` (read FIRST; originals historical), ADR-0182 (L0-26 contract — impl owned by slot 1), L3-59 (CapacityContext contract authority here), HANDOFF §5/§6/§9, POST_PHASE_38_PHASE_MAP §6 q9, WSD/FOL FUTURE_CHAT_PROMPTs.

---

## §0 — Process discipline (inherited)

Per HANDOFF §9: probe-first (done — 3 probe passes over L0/L2-L3/L4-L5 shipped surfaces); saturation = consecutive reversal-free rounds; pair-execution + gate-host discipline apply to whatever the phase-map ships. Per project instructions: pushbacks > agreement.

## §0.1 — Probe findings R0 rests on (grounded, file-level)

1. **Nothing bundle/skill-shaped exists in production code.** Greenfield. The closest precedents: `manifest.toml` (version/phase/digest truth file), the ImporterProtocol bootstrap pattern, and the `mindsos_capacity/builtins/` idempotent installer pattern (all-present → no-op; partial → error; none → install).
2. **CapacityLayer has no deregister/remove surface.** Capacities are in-memory, per-process; they exist only because an installer ran in this process. Nothing dynamic survives restart except L2 content in Falkor.
3. **Closed role-set (12) is runtime-enforced** (`UnknownRoleError` in `schema_for_role` + bootstrap scope checks). A bundle cannot create a role-graph without a code release + ADR-0150 §am.
4. **`parameter-staging` + `pending-promotions` have zero production writers/consumers** (schema-only since Phase 43). Confirms the R0-SA-1 routing gap.
5. **The only write path is ADR-0180 `make_writeable`** (scope-aware; Global writes require `CAN_WRITE_GLOBAL`); both L4 dispatch and `capacity_layer.invoke` build it. Installs reuse it — no new gate.
6. **L4 registries are static skeletons** (11 ALS subsystems, 10 signal-source slots, S7 reserved; registration at `IntelligenceLayer.start()`; v0 catalogs install opt-in). Rich L4 bundle slots now = spec-against-fiction (confirms R0-SA-3).
7. **ADR-0182 assumed graph-node storage** for bundle-manifest + install-provenance records ("durable round-trips through the same persister") — but named no role-graph. The closed set has no natural home for install records (S5 fork below).

---

## §1 — R0 surfaces

Each: **Q** · options · **Pick** · **Status**.

### S1 — What a bundle physically IS (framing — biggest fork)

**Q:** Is a skill bundle a self-contained code+data plugin the host imports, or a data+manifest artifact referencing code that arrived via normal release?

- **A — Full plugin** (bundle ships Python code; host imports from bundle path).
  Pros: true "install a skill" UX; no release coupling.
  Cons: arbitrary-code-execution surface with no sandbox (L0-5 capacity sandbox is WSD-routed, unshipped); import-path/packaging machinery net-new; nothing in the shipped system loads code dynamically; zero v1 consumer needs it — WSD ships as a MindsOS code release anyway (new role-graphs, schemas, importers are code).
- **B — Data + manifest; code via release.** Bundle = versioned manifest (TOML; `manifest.toml` precedent) + data files. Code artifacts (capacity bodies, importers, schemas) live in released Python packages; the manifest references installer entry points by import path. Install = run referenced installers + write L2 content + write install record.
  Pros: zero new code-loading surface; reuses the builtins-installer pattern verbatim; integrity is a digest over manifest+data; matches how WSD will actually ship.
  Cons: "install" doesn't deliver code — two-step story (release, then install/activate).
- **C — B at v1, A recorded as v2 trigger** (trigger: a skill whose code cannot ship in a MindsOS release — e.g. third-party-authored skill).

**Pick: C.** The 2026-05-28 framing "skill = L1+L2+L3+L4+L5 artifacts as an installable bundle" survives as the *contract* (the manifest declares per-layer slots) but not as a code-delivery mechanism. **Status: open (PB-1).**

### S2 — Per-layer artifact slots (the manifest's layer sections)

**Q:** What may a bundle contribute per layer? Grounded against shipped surfaces, not the 2026-05-28 slogan:

| Layer | v1 slot | Grounding |
|---|---|---|
| L1 | **None.** | L1 has no skill-scoped artifacts; new node/edge types arrive via L2 schemas (code → release-side). WSD's L1 reframes are architecture changes, not bundle content. |
| L2 | Role-graph **content** (nodes/edges into existing role-graphs, incl. task-patterns); importer **invocations** (importer code is release-side). **NOT role-graph creation** (closed set; §0.1-3). | `UnknownRoleError`; ADR-0150 §am mechanism; ImporterProtocol. |
| L3 | DataStates + capacities + monitors via installer entry points (CapacityContext-native bodies only — S9); new realm only via `allow_new_realm` declared in manifest; lazy-installed category precedent (`CATEGORY_DREAM`). | ADR-0159 contract v2; builtins pattern. |
| L4 | **Opaque key-value slots only** (R0-SA-3): ALS-subsystem fills, signal-source payload contracts, catalog replacement — *named* in the manifest but uninterpreted by the v1 install driver; WSD forces the real shape; v2 trigger recorded. | §0.1-6. |
| L5 | **None.** Episodes/Memories are runtime products; Episode schema is fixed (D-B47). A skill influences L5 only through task-patterns (L2). | `episodic_memories.py` fixed 6-field contract. |

**Pick:** table above. **Status: open (PB-2 — the L1/L5-empty finding contradicts the charter's letter; needs Henrique's ratification).**

### S3 — Tier placement

**Q:** Local vs Global install at v1?

**Pick:** **Global-only, admin-gated.** WSD/FOL are Global skills; no Local-install consumer exists. Per-artifact `tier` field exists in the manifest schema from day one (so the promotion-loop producer can target Local staging tiers per S10) but the v1 install driver accepts `tier = "global"` only. Local skill installs = recorded v2 trigger. **Status: locked-pending-review.**

### S4 — Conflict resolution

**Q:** Collisions (capacity IRI, DataState IRI, realm, task-pattern IRI, bundle name) + version skew?

**Pick:** **Preflight scan + atomic abort.** Install runs a read-only preflight over every declared artifact; any collision (existing capacity/DataState IRI not owned by a prior version of the same bundle, unknown role, realm conflict absent `allow_new_realm`, missing `requires_bundles`, `requires_mindsos_phase` unsatisfied) aborts the whole bundle with a structured report + `EVT_SKILL_INSTALL_REJECTED`. No merge/rename heuristics at v1. Role-set expansion is **not a conflict to resolve but a non-goal**: bundles cannot request it (S2). Partial-install states are prevented by ordering (S7), not by rollback machinery. **Status: locked-pending-review.**

### S5 — Install record + provenance home (real fork)

**Q:** Where does "what is installed" durably live?

- **A — New Global role-graph `installed-skills`** (ADR-0150 §am authored at this chat's closure; closed set 12 → 13; ships at slot 1). Record node per bundle-version: structured `value` (manifest digest, artifact roster, installer outcomes, status installed/uninstalled) — **the first consumer of ADR-0182 `_value_json`**, exactly as the ADR anticipated. Queryable fields lifted flat per ADR-0182 rule 5 (`bundle_name`, `bundle_version`, `status`).
  Pros: one store (ADR-0160 one-metagraph property holds for Global too); ADR-0182's named consumer; audit/provenance/mutation-discipline machinery applies for free; startup re-registration (S7) reads it through the normal KL path.
  Cons: role-set amendment at slot 1 (schema + bootstrap + closed-set bump — contained but real); slot-1 scope grows beyond "trivial."
- **B — SQLite table** (`version_db` or a new `skills.db`).
  Pros: no role-set amendment; trivially queryable.
  Cons: contradicts ADR-0182's stated consumer (its impl then has *no* slot-1 consumer — the round-trip test loses its real payload); splits Global state across stores (the same split ADR-0182 §Rejected rejected for Locals); invisible to KL/audit/mutation discipline.
- **C — Nodes in `capacity-state`.**
  Pros: no amendment. Cons: semantic abuse — capacity-state is L3 runtime state, not admin inventory; mutation discipline mismatch.

**Pick: A.** B's "no amendment" saving is false economy: it orphans ADR-0182's slot-1 implementation. **Status: open (PB-3).**

### S6 — Capabilities + audit constants

**Pick:** Additive, Phase-44 S8 pattern: `CAN_INSTALL_SKILL` + `CAN_UNINSTALL_SKILL` in `mindsos_server/capabilities.py` → `ADMIN_CAPS` + `ALL_CAPABILITIES`; events `EVT_SKILL_INSTALLED`, `EVT_SKILL_UNINSTALLED`, `EVT_SKILL_INSTALL_REJECTED` in `mindsos_server/audit.py`. Install driver runs under an admin session holding these **plus** `CAN_WRITE_GLOBAL`; all graph writes through `make_writeable` (ADR-0180) — the gate travels with the capability; **no install-specific write path.** Audit event payload carries `bundle_name`, `bundle_version`, `bundle_digest`, session/user (provenance = audit log [who/when] + install record [what/state]; same split as L0-23 admin-verdict precedent). **Status: locked-pending-review.**

### S7 — Install/activation lifecycle + ordering (incl. restart semantics)

**Q:** Capacities are per-process in-memory (§0.1-2). How does an installed skill exist after restart?

**Pick:** Two-stage lifecycle, mirroring what already exists:

1. **Install (once, admin):** preflight → write L2 content (durable) → run L3 installer entry points (this process) → write opaque L4 slots → write install record + audit. Ordering *within* a bundle: L2 content → L3 DataStates → L3 capacities → L4 slots → record (the builtins DataStates-first discipline, extended). Failure mid-sequence: fail loud, record `status = "failed"` with the completed-step roster; no automatic rollback at v1 (idempotent re-run repairs — S8).
2. **Activation (every process start):** a free function `apply_installed_skills(cl)` walks `installed-skills` records with `status = "installed"` in install order and re-runs the L3 installer entry points (idempotent). Free function, NOT a `MindsOSServer` method — Phase 44 CR-3/PB-38 precedent. Cross-bundle ordering: install order + manifest `requires_bundles` edges; cycle → reuse `kahn_sort` + `BootstrapCycleError` shape.

**Status: open (PB-4 — who calls `apply_installed_skills` at v1, given login/logout don't bootstrap Locals and the CLI installs builtins via flag).**

### S8 — Idempotency

**Pick:** Builtins triple verbatim, at two granularities. Artifact level: all-present → no-op; partial → error naming the partials (no auto-repair *except* when re-running the same bundle-version after a `failed` record — then completed steps no-op and remaining steps run). Bundle level: same name+version+digest → no-op (audited); same name+version, different digest → reject; higher version → **upgrade is a v2 trigger** (v1 rejects; de-install + install is the manual path). **Status: locked-pending-review.**

### S9 — Bundle L3 bodies are CapacityContext-native (R0-SA-4; L3-59 contract authority)

**Pick (contract clause, no fork):** Capacity bodies referenced by any bundle manifest MUST be authored against typed `CapacityContext` (`context.kl`, `context.writeable(...)`) — never the dict form. The install driver does not accept dict-form bodies; no new dict-debt enters via installs. Mechanical migration of the existing corpus + union-drop stays at WSD slot 1 (L3-59(b)). **Status: locked.**

### S10 — Installation vs acquisition scope fork (R0-SA-1)

**Q:** Admin bundle install vs the runtime promotion loop (`parameter-staging` → `pending-promotions` → `learned-parameters`; schema-only, zero writers, no owner in PHASE_MAP §6).

- **A — Unify both lifecycles here.** Cons: promotion mechanism's consumer (ALS, dreams) is WSD-gated; designing it now = spec-against-fiction.
- **B — Split; route promotion closure to WSD.** Cons: two provenance/audit/conflict regimes for the same target role-graphs; the routing gap persists on paper until WSD.
- **C — Unify the *contract*; mechanism ships in WSD** [reanalysis default]. Promotion = a second *producer* of the same install artifacts: same tier rules (staging Local → promoted Global), same audit-event family, same provenance shape (record + audit), same conflict preflight. This log's S4/S5/S6 contracts are written producer-agnostic; the PHASE_MAP §6 routing amendment at closure gives the loop an owner (WSD) on paper.

**Pick: C.** No new evidence against the default; probe §0.1-4 confirms zero writers, so there is nothing to unify *mechanically* yet. **Status: locked-pending-review.**

### S11 — De-installation (R0-SA-3: design stub)

**Pick:** v1 semantics, narrow: (1) refuse if any installed bundle's `requires_bundles` names the target (reverse-dependency check — the *whole* v1 safety story; episode/MM references to a de-installed skill's capacities are NOT chased — D'1 pins versions, dangling capacity IRIs in old episodes are tolerated and recorded as a v2 trigger); (2) delete bundle-written L2 content via provenance tag (flat node property `installed_by = "<bundle>@<version>"` — primitive, validator-legal); (3) flip record to `uninstalled` + `EVT_SKILL_UNINSTALLED`; (4) **no in-process deregistration** — no CapacityLayer.deregister surface exists and we do not add one for a v1 with zero real consumers; registrations expire at process end and activation skips uninstalled records. **Status: locked-pending-review.**

### S12 — Slot 1: trivial-bundle reference install (R0-SA-2)

**Pick:** Package a minimal extension — 1 DataState + 1 CapacityContext-native `text.*` capacity (test-fixture package, not `mindsos_capacity` builtins) + ~3 L2 content nodes — as a bundle; install, verify, de-install, re-install. Pass criterion **exactly**: install / de-install / provenance / idempotency. NOT "installed skill runs" (v0 lifecycle dispatches no real L3 capacity — Phase 49 PB-1a); no dispatch fix pulled in. Slot 1 also implements ADR-0182 (`build_unwind_create_nodes` + loader decode + reserved-key roster + replace the M3 sentinel test with round-trip coverage) — the install record is its first consumer (S5-A). **Status: locked-pending-review.**

### S13 — `IntergraphEdge` naming (R0-SA-5)

**Finding:** already **CLOSED 2026-06-01** as L1-6 (`L1_FUTURE_WORK.md:24`) — shipped `IntergraphEdge` preserved; WSD docs adopt at authoring time. HANDOFF §2.1 + §5.3 still say "pending/open" — stale. **Action at closure:** ratify here (no re-litigation), edit the two HANDOFF lines. **Status: locked.**

---

## §2 — Pushbacks awaiting Henrique (the genuine forks)

| # | Surface | My pick | What would reverse it |
|---|---|---|---|
| PB-1 | S1 bundle = data+manifest, code via release (option C) | C | A concrete v1 need to load third-party code — none known |
| PB-2 | S2 layer-slot table: L1 + L5 slots are **empty** at v1; the charter's "L1+L2+L3+L4+L5 artifacts" is a contract framing, not an artifact list | table | Evidence of a real L1/L5 installable artifact WSD needs at install time |
| PB-3 | S5 install record = new `installed-skills` role-graph (ADR-0150 §am; 12→13) | A | If Henrique judges the role-set amendment too heavy for slot 1 → B (SQLite), accepting that ADR-0182's slot-1 impl loses its named consumer |
| PB-4 | S7 activation caller at v1 (CLI flag mirroring `--install-builtins` vs server-startup hook) | CLI flag at v1; server hook when a server consumer exists | Cheap to flip; consumer discipline says flag |

Minor/track (no discussion needed unless contested): S3 Global-only; S4 atomic preflight; S6 constant names; S8 upgrade-rejected; S11 no-deregister; S12 slot-1 scope.

## §3 — R1 disposition (2026-06-09)

Henrique reviewed round 1 and authorized proceed with no contested picks. PB-1 (data+manifest, code via release), PB-2 (L1/L5 slots empty; 5-layer framing = contract sections), PB-3 (`installed-skills` role-graph, ADR-0150 §am; 12→13), PB-4 (CLI-flag activation at v1) — **all locked as picked.**

## §4 — R2 reanalysis (2026-06-09) — refinements only, zero reversals

- **R2-1 (S11 refinement — content disposition).** Probe: node-level deprecation already exists (`deprecated_at` + ADR-0133 `include_deprecated` filter, `metagraph_view.py:213-282`), and `Graph.remove_node(cascade=True)` exists at L1 (`graph.py:483`). v1 de-install **deprecates** bundle-tagged L2 content rather than hard-deleting — reference-safe under D'1 (old episodes may pin content versions), zero new L2 surface. Hard delete of de-installed content = admin escalation, v2 trigger (naming precedent: `CAN_HARD_DELETE_ARCHIVED`). S11 step (2) amended accordingly.
- **R2-2 (S5 mutation discipline).** `installed-skills` records are **append-only action records** (one per install/uninstall/failure; current state = latest record per `bundle_name`). Avoids a mutable-status discipline exception; reads like provenance. Slot-1 R0 may flip to mutable-status if record-walk costs bite — flagged, not expected.
- **R2-3 (S7 mechanism note).** Activation entry points resolve via `importlib` over **release-shipped** modules already on the path — consistent with PB-1; no bundle-path code loading anywhere.
- **R2-4 (numbering convention).** SA-1 ships as **Phase 50** (tag `phase-50-confirmed`; 10-surface version bump 49→50 — slot > high-water 49 per Phase-40 PB-2). Rationale: manifest/release.yml/confirm-phase machinery all key on numbered phases; inventing a parallel tag scheme buys nothing. PHASE_MAP §6 "first `<phase>-confirmed` tag" wording anticipated this. Henrique can veto at SA-1 R0.

## §5 — Saturation declaration + closure

R1: 4 pushbacks, all accepted. R2: 4 refinements, 0 reversals. Scope is narrow greenfield over well-probed shipped surfaces; remaining unknowns (record-walk cost, deprecate-vs-delete edge cases, exact preflight roster) are impl-time items the SA-1 ship chat's §-tracking absorbs — diminishing returns per the Phase-43 saturation rationale. **Design CLOSED 2026-06-09.**

**Closure outputs:**
1. `confirmation_docs/SKILL_ACQUISITION_PROCESS_PHASE_MAP.md` — sequencing (SA-1 = Phase 50) + WSD inheritance contract + v2-trigger ledger.
2. `POST_PHASE_38_PHASE_MAP.md` §6 routing amendment — promotion-loop mechanism owner = WSD_INSTALLATION_CHAT; contract = this log S10 (closes the R0-SA-1 routing gap).
3. HANDOFF stale-line edits — §2.1 naming note + §5.3 blocker row (`IntergraphEdge` closed as L1-6 2026-06-01; ratified here per S13).
4. `docs/_workbench/L3_FUTURE_WORK.md` L3-59(a) closure marker — contract fixed at this log's S9.
5. `confirmation_docs/SA_1_NEXT_CHAT_PROMPT.md` — Phase 50 ship-chat seed.

**ADRs reserved for SA-1 (drafted at ship R0, per numbered-phase precedent):** ADR-0183 (skill-bundle + install-lifecycle contract — manifest schema, preflight, two-stage lifecycle, idempotency triple, de-install semantics), ADR-0150 §am-6 (`installed-skills` role-graph; closed set 12→13). ADR-0182 impl ships in the same slot (its §Consequences surface list governs).

---

## §6 — (bongard-solver) Producer-front + two-path generalization (proposed 2026-06-20, NOT ratified)

> **Tag: `bongard-solver`.** Suggestions for the future process; does not relitigate the closed install-tail (S1–S13). This log designed the **install/promote tail** and routed the **producer/acquisition front** to WSD (S10, producer-agnostic). The bongard-solver demo is the first concrete producer and surfaces (a) the front's shape and (b) a generalization the log doesn't cover: the leaf. Goal restated (Henrique 2026-06-20): a concise, proper, **user-facing** process to teach MindsOS *any* skill.

### §6.1 — Two intake paths, divided by one line

Skill-acquisition has **two** intake paths, sorted by the **composite/primitive = inspectable/opaque = mint/install** line:

1. **Autonomous mint** (OPEN — the producer front): a skill expressible as a **declarative composite over existing seed capacities**. Auditable parse; few-shot; no large training run. Flows producer → S10 staging (Local tier, S3) → S4 preflight → S5 record → S6 promote. The front (SA-1..4) is §6.3.
2. **Human-authored install** (SHIPPED — S1–S13): a skill that is an **opaque artifact** — arbitrary code, a trained model, a **neural leaf**. Not internally auditable; arrives as a bundle; admin-installed.

**"Add ANY skill" = the union of the two paths** — autonomous where inspectable, human-install where opaque. The process always offers *a* path; **autonomy varies, it is not promised for arbitrary skills** (preserves the auditability moat; matches §1's deliberate narrowing in PLAN.md).

### §6.2 — The neural leaf is path 2, quarantined by the grounding contract

A neural leaf (raw signal → features) is opaque weights → a **primitive** → un-mintable, un-inspectable → it **cannot** be autonomously acquired. It does not need to be: it is human-authored + installed via path 2 (model file as bundle data + a `CapacityContext`-native body that loads it — S2/S9 already permit this). The **grounding contract** (raw signal → normalized **typed** atoms; in bongard, point-set → ontology shape) **quarantines** the leaf's opacity: the leaf stays a black box, but its *output is typed*, so the composite structure above it stays mint-able and auditable.

> **Generalization (the requested neural-leaf part):** not "mint neural leaves," but **"an installed (path-2) neural leaf grounds an autonomously-minted (path-1) structure, with the typed grounding output as the quarantine seam."** Auditability lives **above** the leaf. "No-training-run / auditable-from-scratch" is a property of the mint path + a domain's symbolic-leaf *choice*, not a global guarantee.

### §6.3 — Producer front (SA-1..4) — the open part (detail in PLAN.md §14)

| Step | New/Reuse | Notes |
|---|---|---|
| SA-1 trigger/detection | New | watch L5 episodes for recurring composable structure or an uncomposable gap (⚠ heuristic under-specified) |
| SA-2 candidate construction | New (core CC-2) | assemble recurring sub-structure into a composite pipeline over seeds |
| SA-3 validation | New + oracle slot | domain-supplied verifier (bongard: held-out generator) + min support *k* |
| SA-4 provisional register | New (core CC-1) | composite registered Local, machine-named; backing → `promoted-pipelines`+`learned-parameters` |
| SA-5/6 present+name / promote | **Reuse S3/S4/S5/S6** | the producer is "a second producer of the same install artifacts" (S10-C) |
| SA-7 gap → human primitive | New consumer | uncomposable → `capacity-gaps`; **this is also where a neural leaf enters** (§6.2) |

Core dependencies CC-1/CC-2/CC-3 (capacity-node persistence, composite kind+runner, `promote_capacity`): `projects/bongard_demo/CORE_CHANGES.md`.

### §6.4 — Grounding-confidence caveat

bongard-solver uses a **symbolic** leaf (path 1 to the pixels), so it grounds the **mint front** but does **not** empirically exercise path 2 or the neural quarantine. §6.2 is principled but **untested by this demo** — a messy-image variant or another demo is needed before it is treated as validated.
