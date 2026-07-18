---
title: Skill-bundle and install-lifecycle contract
status: Accepted
date: 2026-06-10
accepted_date: 2026-06-10
layer: server
related: [0010, 0150, 0151, 0153, 0159, 0180, 0182]
---

# ADR-0183: Skill-bundle and install-lifecycle contract

**Status:** Accepted (Phase 50 / SA-1 — drafted at ship R0 per the
SKILL_ACQUISITION design-log §5 reservation; design settled at
SKILL_ACQUISITION_PROCESS_CHAT closure 2026-06-09)

**Date:** 2026-06-10

**Related:** ADR-0010 (Server imports downward — the install driver is
server-side), ADR-0150 §am-6 (`installed-skills` role-graph; closed set
12 → 13), ADR-0151 (storage tiers), ADR-0153 (`append_only`
discipline), ADR-0159 (capacity registration contract v2 — bundle
bodies are CapacityContext-native), ADR-0180 (`make_writeable` — the
only write gate; installs add no write path), ADR-0182 (node-value
serialization — the install record is its first production consumer).

Design authority: `confirmation_docs/SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md`
(S1–S13 + R2). This ADR fixes the contract durably; the log holds the
option analysis.

## Context

The 2026-05-28 charter framed a skill as "L1+L2+L3+L4+L5 artifacts as
an installable bundle". Probing the shipped system (design log §0.1)
found: nothing bundle-shaped exists; CapacityLayer has no deregister
surface; the closed role-set is runtime-enforced; the only write path
is the ADR-0180 gate; L4 registries are static skeletons. WSD/FOL/
code-skill installations all need one install lifecycle to inherit.

## Decision

### 1. What a bundle is (S1, R1 PB-1)

A **skill bundle** is a versioned **TOML manifest + data files**. Code
(capacity bodies, importers, schemas) arrives via a normal MindsOS
release; the manifest references **installer entry points by import
path**, resolved via `importlib` over release-shipped modules only
(R2-3). No bundle-path code loading exists anywhere. Full-plugin
(bundle-shipped code) is a recorded v2 trigger requiring the L0-5
sandbox first.

### 2. Per-layer slots (S2, R1 PB-2)

| Layer | v1 slot |
|---|---|
| L1 | None. |
| L2 | Role-graph **content** into existing role-graphs + importer invocations. NOT role-graph creation (closed set; ADR-0150). |
| L3 | DataStates + capacities + monitors via installer entry points; CapacityContext-native bodies only (S9 = L3-59(a)); new realm only via a manifest-declared `allow_new_realm`. |
| L4 | **Opaque key-value slots** — named in the manifest, uninterpreted by the v1 driver; WSD defines the real shapes by amendment. |
| L5 | None. Episodes/Memories are runtime products. |

The five-layer charter survives as the manifest's *contract sections*,
not as an artifact list.

### 3. Tier + authorization (S3, S6)

Installs are **Global-only and admin-gated** at v1: `CAN_INSTALL_SKILL`
/ `CAN_UNINSTALL_SKILL` (in `ADMIN_CAPS`), with `CAN_WRITE_GLOBAL`
co-held — every graph write travels through ADR-0180 `make_writeable`;
there is **no install-specific write path**. The manifest schema
carries a per-artifact `tier` field from day one (promotion-loop
forward-compatibility) but the v1 driver accepts `tier = "global"`
only. Audit events: `EVT_SKILL_INSTALLED`, `EVT_SKILL_UNINSTALLED`,
`EVT_SKILL_INSTALL_REJECTED` — payload carries `bundle_name`,
`bundle_version`, `bundle_digest`. Provenance split (L0-23 precedent):
audit row = who/when; install record = what/state.

### 4. Preflight + atomicity (S4)

Install runs a read-only **preflight** over every declared artifact.
Any collision aborts the whole bundle with a structured report +
`EVT_SKILL_INSTALL_REJECTED`: existing capacity/DataState IRI not owned
by a prior version of the same bundle; unknown role; realm conflict
absent `allow_new_realm`; missing `requires_bundles`; unsatisfied
`requires_mindsos_phase`. No merge/rename heuristics. Role-set
expansion is a non-goal: bundles cannot request it.

### 5. Install record (S5, R2-2; ADR-0150 §am-6)

Install state lives in the Global **`installed-skills`** role-graph as
**append-only action records** (`Discipline.APPEND_ONLY`): one
`SkillInstallRecord` per install / uninstall / failure; current state =
latest record per `bundle_name`. The record `value` is a structured
dict (manifest digest, artifact roster, installer outcomes) — the
first production consumer of ADR-0182 `_value_json`. Queryable fields
lifted flat by the writer per ADR-0182 rule 5: `bundle_name`,
`bundle_version`, `status` (`installed` / `uninstalled` / `failed`),
`action`, `recorded_at`. IRI: `installed-skills-<v>:record:
<bundle_name>:<record_id>` (`record_id` = `<bundle_version>:<seq>`).

### 6. Two-stage lifecycle (S7, R1 PB-4)

1. **Install (once, admin):** preflight → L2 content (durable) → L3
   DataStates → L3 capacities → opaque L4 slots → install record +
   audit. Failure mid-sequence fails loud: record `status = "failed"`
   with the completed-step roster; no automatic rollback (idempotent
   re-run repairs, §7).
2. **Activation (every process start):** `apply_installed_skills(cl)` —
   a free function (Phase 44 CR-3/PB-38 precedent) — walks `installed`
   records in install order and re-runs the L3 installer entry points
   (idempotent). Cross-bundle order: install order + `requires_bundles`
   edges; cycles reuse the `kahn_sort` / `BootstrapCycleError` shape.
   v1 caller: a CLI activation flag mirroring `--install-builtins`; a
   server-startup hook lands when a server consumer exists.

### 7. Idempotency (S8)

The builtins triple at two granularities. **Artifact:** all-present →
no-op; partial → error naming the partials — except when re-running the
same bundle-version after a `failed` record, where completed steps
no-op and remaining steps run. **Bundle:** same name+version+digest →
no-op (audited); same name+version, different digest → reject;
higher version → reject (**upgrade is a v2 trigger**; manual path =
de-install + install).

### 8. De-installation (S11, R2-1, Phase 50 G1)

Narrow v1 semantics: (1) **refuse** if any installed bundle's
`requires_bundles` names the target (reverse-dependency check — the
whole v1 safety story; episode/MM references are NOT chased — D'1 pins
versions; dangling capacity IRIs in old episodes are tolerated, v2
trigger); (2) **deprecate** bundle-tagged L2 content (provenance tag:
flat `installed_by = "<bundle>@<version>"` node property) by stamping
`deprecated_at` via direct system write (the `retire_version`
precedent — `deprecated_at` is a reserved key). **Marker-only at v1
(G1):** no node-level read filter exists in shipped read paths;
deprecated content stays visible-but-marked. Node-level
`include_deprecated` filtering = v2 trigger. Hard delete = admin
escalation, v2 trigger (`CAN_HARD_DELETE_ARCHIVED` naming precedent);
(3) append an `uninstalled` record + `EVT_SKILL_UNINSTALLED`;
(4) **no in-process deregistration** — no CapacityLayer.deregister
surface exists; registrations expire at process end and activation
skips uninstalled records.

### 9. Promotion loop (S10)

The runtime promotion loop (`parameter-staging` → `pending-promotions`
→ `learned-parameters`) is a **second producer of the same artifacts**
under this same contract (tiers, audit-event family, provenance shape,
conflict preflight). Its mechanism ships in WSD
(`SKILL_ACQUISITION_PROCESS_PHASE_MAP.md` §3/§5).

## Rejected options

- **Full plugin at v1** — arbitrary-code-execution surface with no
  sandbox; zero v1 consumer; WSD ships as a release anyway.
- **SQLite install record** — orphans ADR-0182's slot-1 implementation;
  splits Global state across stores (the split ADR-0182 §Rejected
  rejected for Locals); invisible to KL/audit/mutation discipline.
- **Hard-delete de-install** — breaks D'1 reference-safety for episodes
  pinning bundle content.
- **CapacityLayer.deregister** — new L3 surface for a v1 with zero real
  consumers.

## Consequences

- Phase 50 ships: `installed-skills` schema + bootstrap (ADR-0150
  §am-6), capabilities/audit constants, ADR-0182 implementation,
  manifest parser + preflight + install/de-install driver +
  `apply_installed_skills` + CLI surface, and a trivial reference
  bundle validating install / de-install / provenance / idempotency
  ONLY (no dispatch work — Phase 49 PB-1a is WSD's).
- WSD inherits per `SKILL_ACQUISITION_PROCESS_PHASE_MAP.md` §5;
  rich L4 slots and the L3-59(b) corpus migration land there.
- v2-trigger ledger (phase-map §3): bundle-shipped code; Local-tier
  installs; in-place upgrade; hard delete; node-level deprecation
  read-filtering; dangling-IRI chasing; rich L4 slots.
## Amendment §am-1 (2026-07-05) — runtime-entry declaration

**Context.** The resident-brain `execute` verb (REPL Slice 2) runs a skill's
declared runtime entry pipeline. No prior field carried it; `_resolve_entry_point`
(driver.py) is install-time only.

**Decision.** Add two optional flat advisory props to `SkillInstallRecord`:
`entry_start_datastate` and `entry_target_datastate`. When both are present on
a skill's latest (`status="installed"`) record, `execute` seeds the start
datastate with the caller input, builds a pipeline start→target via
`find_pipeline`, and runs it through the standalone step-runner
(`mindsos_server/pipeline_runner.py`).

**Scope / status.** Additive to the strict=False schema; append-only (fixed per
install record — changing an entry means a new record). Populated by the SAP
manifest installer when SAP ships; until then only test fixtures / ARC-packaging
set it, so `execute` is inert ("no entry declared") in a stock brain and `task`
is retained. Additive/optional on a strict=False schema — no release-train version bump (the label moves only at numbered phases; version_db node-versioning is deferred).

**Alternatives rejected.** (a) entry in the opaque record `value` — no bump but
untyped/unqueryable; (b) promoted-pipeline marker — needs a marker convention
and pre-promotion. Chose flat props for queryability (operator's call, bump
accepted).

## Amendment §am-2 (2026-07-16) — activation resilience

**Context.** §6 stage 2 says activation "re-runs the L3 installer entry points
(idempotent)" but specified no failure handling, and `apply_installed_skills` had
none: it imported and called every installer bare. Because `installed-skills` is
Global (§5), a single record whose `l3_installers` names a module absent from the
booting venv — the common cross-lane case, e.g. a bundle pip-installed only in
another checkout — raised `ModuleNotFoundError` out of `boot_brain` and bricked the
brain for **every** user. An absent skill is the textbook honest don't-know; a
traceback contradicts the system's stated posture. (Surfaced by `mindsos brain
--user arc1`: `No module named 'mindsos_arc'`.)

**Decision.** Per-process activation is **best-effort at boot and strict on explicit
invocation**. Each bundle is processed in two phases:

- **resolve** — import + `getattr` of every installer via the shared
  `mindsos_server/skills/entry_points.py::resolve_entry_point`, which raises a
  neutral `EntryPointError` for every "not resolvable here" cause (malformed spec,
  unimportable module, missing attribute, non-callable). No side effects on `cl`. A
  resolve failure ⇒ the bundle is absent in this process ⇒ skip it cleanly.
- **apply** — call each `fn(cl)`, outside the resolve `try`. A mid-apply failure may
  leave the bundle **partially registered**; there is no per-bundle rollback (no
  deregister surface exists — §8(4)), so the partial is repaired by the next
  process's idempotent `if_exists="upsert"` re-run (§7 grain). The bundle is skipped
  and reported, tagged as possibly partial.

With `strict=True` (the **default** — every pre-existing call site is byte-identical)
either failure re-raises: an explicit `mindsos skill activate` that cannot activate
fails loud. `boot_brain` passes `strict=False`. `apply_installed_skills` returns an
`ActivationReport(activated, skipped)` that **subclasses `tuple`** (so the historical
`Tuple[str, ...]` return is unchanged) with an additive `skipped` roster of
`(bundle_name, reason)`; `boot_brain` logs skips at WARNING and carries the report on
`Stack.activation`. The `skill activate` verb renders skips and gains `--best-effort`
(resilient diagnosis; default stays strict).

**Scope / status.** Additive-inert: no schema change, no role/category/count change,
no release-train version bump (stays `phase50`). Skips are **process-local and never
written back** to the durable Global record (§5) — its `status` stays `installed`; a
module missing in *this* venv says nothing about the bundle's validity elsewhere, so
no `failed` status is written at activation time (distinct from the install-time
`failed` of §6(1)). The same contract now also covers the **learned-capacity
reactivation** twin (`reactivate_from_descriptors`, ADR-0185/0186; reached via
`boot_local` on the durable path): `reactivate_from_descriptors`,
`reactivate_local_capacities`, `boot_local` and `_dep_order_descriptors` take an
additive-inert `strict` flag (default `True` — every pre-existing caller byte-identical);
`boot_brain` passes `strict=False`. A descriptor whose factory is not registered in this
process is skipped with a **loud** `log.warning` naming the `reactivation_key` (and a
dependency cycle degrades to unordered) — resilient but never silent, so the missing
factory registration is surfaced, not swallowed. The resident brain boots arbitrary
durable Locals out of Falkor, so this is the same cross-lane / foreign-persisted-state
failure class as the installed-skills case; production code does not yet write such a
descriptor, so it is defense-in-depth (no observed incident). Learned skips, too, are
process-local and never written back.

**Alternatives rejected.** (a) catch resolve only, keep `fn(cl)` fatal (the original
CR proposal) — re-introduces the Global brick-all for any importable-but-broken
installer, and its catch missed a malformed spec (`ValueError`); (b) per-bundle
rollback / staging overlay — no deregister surface exists and it fights the §7
upsert-repair grain; (c) write `failed` back to the record at activation — activation
is per-process and the record is durable + Global, so a process-local resolution
result must not mutate durable state.

## Amendment §am-3 (2026-07-17) — skill-declared brain verbs (`[l4].slots` consumed)

**Context.** `[l4].slots` (`SkillManifest.l4_slots`, `manifest.py:63`) is parsed from
`[l4.slots]` (`manifest.py:165-168`) and persisted into the install record
(`driver.py:143`: `"l4_slots": dict(manifest.l4_slots)`), but — before this amendment —
read by nothing (repo-wide grep). Meanwhile `BrainREPL` dispatched verbs by attribute
lookup (`getattr(self, f"_do_{verb}")`, `brain.py:70`), so an installed Skill could
contribute no verb: its only route to a lifecycle was the generic `task` verb, which
passes a bare `{"text": ...}` dict with `modality=None`. Since ADR-0197 am-1 an
unregistered modality no longer falls back to the construction-bound profile — so from
`mindsos brain` there was **no path to a Skill's lifecycle at all**.

**Decision.** `[l4].slots` is consumed at boot. `boot_brain` (via the new
`build_skill_l4_tables`) reads each installed (`status="installed"`) record's `l4_slots`
and, in one filtered pass, builds (a) the L4 dispatcher's `{modality → Phase1Profile}`
table (ADR-0197) and (b) the resident-brain verb table `{verb → slots}`, carried on
`Stack.skill_verbs`. A slot declares a brain `verb`, an ingress `modality` (DataState
IRI), and the Phase-1 capacity slots (`process`/`hint`/`derive_goal`/`map`/
`resolve_target_datastate`). `BrainREPL` checks its builtin `_do_*` handlers first, then
the skill-verb table; a skill verb builds a modality-stamped `InputEnvelope` and calls
`run_lifecycle`. The verb is **data, not a callable** — the Skill injects no code into the
REPL namespace; its behaviour is reached only through its registered L3 capacities via the
dispatcher. This also removes the brain's need to construct a dispatcher with a
construction-bound `phase1_profile=` (arc1 D1.13): the table is built from the manifests.

**Filtering + collisions.** The one pass applies: a bundle in `Stack.activation.skipped`
(§am-2) contributes nothing — its capacities are absent, so a profile bound to it would
raise at first use; it is skipped and reported in `help`. A slot with no `modality`
contributes no verb and no profile. Verb and modality collisions resolve **first-wins by
install `seq`** (never silent last-wins). **Builtins always win**: the REPL drops any
skill verb shadowed by a `_do_*` at construction — runtime-authoritative, which also
catches builtins added *after* a Skill was installed. A `pending_confirmation` outcome
(ADR-0196) is surfaced, not swallowed; a propagated `InterpretationError` is caught so a
mis-registered skill cannot crash the REPL.

**Deviation from the CR proposal.** The CR (D-1) proposed rejecting verb/builtin
collisions at install-time in `preflight.py`. That was **not adopted**: the builtin verb
set lives in `BrainREPL` (`mindsos_cli`), and `preflight` (`mindsos_server`) owning it
would force a `server→cli` dependency or a drifting duplicate list — the exact drift the
ADR-status gate exists to prevent. The runtime REPL shadow-guard is authoritative instead;
an optional CLI-side install pre-check is deferred (no `preflight` change shipped).

**Scope / status.** CLI + an L4 read of an already-persisted field. No new manifest field,
no schema change, no record migration, no release-train version bump (stays `phase50`).
Inert in a stock brain until a record declares `[l4.slots]` with a `modality`. Depends on
§am-2 (`Stack.activation.skipped`). Cross-ref ADR-0195 (`Phase1Profile`), ADR-0197 + am-1
(modality ingress), ADR-0196 (needs-input). Shipped on `mindsos_server/boot.py` +
`mindsos_cli/commands/brain.py`; covered by `tests/resident_brain/test_skill_verbs.py`
and `test_skill_verb_durable.py` (full gate 4237/0).

**Alternatives rejected.** (a) preflight verb-conflict (D-1) — `server→cli` coupling /
drift (above); (b) last-wins on collisions, mirroring `_declarations` — silently disables
an already-working verb, inconsistent with preflight's first-wins IRI-collision precedent;
(c) reach skills through `task` with a `{"text": ...}` dict — no `InputEnvelope`,
unroutable modality since ADR-0197 am-1.
